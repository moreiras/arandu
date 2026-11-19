# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Análise aprofundada de estabilidade BGP — etapa 2.

Relê os arquivos MRT em cache para os N ASes mais ruidosos identificados na
etapa 1, mantendo o AS_PATH completo dos eventos de flap. Produz diagnóstico
de causa raiz por AS: o ruído vem do próprio AS, de um prefixo específico, ou
de um upstream instável?

Inputs:
  normalized/{date}/summary/bgp_stability.json.gz   — saída da etapa 1 (top N)
  normalized/{date}/summary/origin-prefixes-v4.json.gz
  normalized/{date}/summary/origin-prefixes-v6.json.gz
  data/raw/{date}/route-views.saopaulo/*.bz2         — cache em disco

Output:
  normalized/{date}/summary/bgp_stability_deep.json.gz

Uso:
  python -m sources.bgp_stability_deep.collect
  python -m sources.bgp_stability_deep.collect --date 2026-06-28
  python -m sources.bgp_stability_deep.collect --top 30 --force
"""

from __future__ import annotations

import argparse
import bz2
import datetime
import io
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

try:
    import mrtparse
except ImportError:
    print("ERROR: mrtparse não instalado. Execute: pip install mrtparse==2.2.0", file=sys.stderr)
    sys.exit(1)

from core.common import (
    configure_logging,
    data_dir,
    normalized_path,
    now_iso,
    raw_path,
    read_json_gz,
    today_str,
    write_json_gz,
    ignorar_sigpipe,
)

# O mrtparse zera o tratamento de SIGPIPE ao ser importado (ver ignorar_sigpipe)
ignorar_sigpipe()

# ---------------------------------------------------------------------------
# Constantes MRT/BGP (mesmas da etapa 1)
# ---------------------------------------------------------------------------
_BGP4MP    = 16
_BGP4MP_ET = 17
_BGP_AS_PATH = 2
_MP_REACH_NLRI   = 14
_MP_UNREACH_NLRI = 15

# Janela de sincronismo: dois prefixos são "sincronizados" na mesma hora se
# ambos têm pelo menos um evento naquele bucket de 1h.
_HOURS = 7 * 24  # 168 buckets

# Limites para veredicto (da spec)
_SYNC_UPSTREAM    = 0.8   # prefix_sync_score mínimo para upstream_instability
_CONC_UPSTREAM    = 70.0  # upstream_concentration_pct mínimo para upstream_instability
_SYNC_PREFIX      = 0.4   # prefix_sync_score máximo para prefix_specific


# ---------------------------------------------------------------------------
# Helpers de parse (replicados da etapa 1 para não criar dependência circular)
# ---------------------------------------------------------------------------

def _first_key(d: dict):
    return next(iter(d)) if d else None


def _extract_aspath(path_attributes: list) -> Optional[list[int]]:
    for attr in path_attributes:
        if _first_key(attr.get("type", {})) == _BGP_AS_PATH:
            val = attr.get("value", [])
            asns: list[int] = []
            for seg in val:
                asns.extend(int(a) for a in seg.get("value", []) if isinstance(a, (int, str)))
            return asns if asns else None
    return None


# ---------------------------------------------------------------------------
# Carregamento de dados base
# ---------------------------------------------------------------------------

def _load_top_n(norm: Path, top_n: int, log) -> list[dict]:
    src = norm / "bgp_stability.json.gz"
    if not src.exists():
        log.error("bgp_stability.json.gz não encontrado — execute primeiro a etapa 1",
                  path=str(src))
        return []
    data = read_json_gz(src)
    entries = data.get("as_stability", [])
    return entries[:top_n]


def _build_prefix_to_asn(norm: Path, target_asns: set[int], log) -> dict[str, int]:
    """Constrói mapa {prefixo: asn} para os ASes alvo (v4 e v6)."""
    result: dict[str, int] = {}
    for afi in ("v4", "v6"):
        gz = norm / f"origin-prefixes-{afi}.json.gz"
        if not gz.exists():
            log.warning("origin-prefixes não encontrado", afi=afi)
            continue
        try:
            data = read_json_gz(gz)
        except Exception as exc:
            log.warning("falha ao ler origin-prefixes", afi=afi, error=str(exc))
            continue
        for asn_str, prefixes in data.items():
            asn = int(asn_str)
            if asn in target_asns:
                for pfx in prefixes:
                    result[pfx] = asn
    log.info("prefixos mapeados para top ASes", count=len(result), asns=len(target_asns))
    return result


# ---------------------------------------------------------------------------
# Estrutura de acumulação de eventos com AS_PATH
# ---------------------------------------------------------------------------

class DeepAccumulator:
    """
    Acumula eventos de announce e withdraw com AS_PATH para prefixos dos top-N ASes.
    Mantém prefix_origin para atribuir withdrawals (sem AS_PATH) ao ASN correto.
    """

    def __init__(self, prefix_to_asn: dict[str, int], start_ts: int):
        self._pfx2asn  = prefix_to_asn
        self._start    = start_ts
        # {asn: {prefix: [(ts, evt_type, aspath_or_None)]}}
        self._events: dict[int, dict[str, list[tuple[int, str, Optional[list[int]]]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        # estado de prefixo → último AS anunciante (para atribuir withdrawals)
        self._pfx_state: dict[str, int] = {}

    def record(self, ts: int, evt_type: str, prefix: str,
               aspath: Optional[list[int]]) -> None:
        asn = self._pfx2asn.get(prefix)
        if asn is None and evt_type == "W":
            # tenta recuperar pelo estado acumulado
            asn = self._pfx_state.get(prefix)
        if asn is None:
            return
        if evt_type == "A":
            self._pfx_state[prefix] = asn
        self._events[asn][prefix].append((ts, evt_type, aspath))

    def as_data(self) -> dict[int, dict[str, list[tuple[int, str, Optional[list[int]]]]]]:
        return dict(self._events)


# ---------------------------------------------------------------------------
# Parse dos arquivos MRT
# ---------------------------------------------------------------------------

def _parse_file(raw_bz2: bytes, acc: DeepAccumulator) -> None:
    """Parseia um arquivo bz2 em memória, acumulando eventos com AS_PATH."""
    try:
        data_raw = bz2.decompress(raw_bz2)
    except Exception:
        return
    for m in mrtparse.Reader(io.BytesIO(data_raw)):
        if m.err:
            continue
        d = m.data
        mrt_type = _first_key(d.get("type", {}))
        if mrt_type not in (_BGP4MP, _BGP4MP_ET):
            continue
        ts_raw = d.get("timestamp", 0)
        ts = _first_key(ts_raw) if isinstance(ts_raw, dict) else int(ts_raw)

        body       = d.get("bgp_message", {})
        path_attrs = body.get("path_attributes", [])
        aspath     = _extract_aspath(path_attrs)
        origin_as  = aspath[-1] if aspath else None

        # IPv4 announces
        for nlri in body.get("nlri", []):
            pfx = f"{nlri['prefix']}/{nlri['length']}"
            if pfx in acc._pfx2asn:
                acc.record(ts, "A", pfx, aspath)

        # IPv4 withdrawals
        for wr in body.get("withdrawn_routes", []):
            pfx = f"{wr['prefix']}/{wr['length']}"
            if pfx in acc._pfx2asn or pfx in acc._pfx_state:
                acc.record(ts, "W", pfx, None)

        # IPv6 via path attributes
        for attr in path_attrs:
            attr_type = _first_key(attr.get("type", {}))
            val       = attr.get("value", {})
            if attr_type == _MP_REACH_NLRI:
                for nlri in val.get("nlri", []):
                    pfx = f"{nlri['prefix']}/{nlri['length']}"
                    if pfx in acc._pfx2asn:
                        acc.record(ts, "A", pfx, aspath)
            elif attr_type == _MP_UNREACH_NLRI:
                for wr in val.get("withdrawn_routes", []):
                    pfx = f"{wr['prefix']}/{wr['length']}"
                    if pfx in acc._pfx2asn or pfx in acc._pfx_state:
                        acc.record(ts, "W", pfx, None)


# ---------------------------------------------------------------------------
# Cálculo de métricas de diagnóstico
# ---------------------------------------------------------------------------

def _hourly_vector(events: list[tuple[int, str, Optional[list[int]]]], start_ts: int) -> list[bool]:
    vec = [False] * _HOURS
    for ts, evt_type, _ in events:
        idx = (ts - start_ts) // 3600
        if 0 <= idx < _HOURS:
            vec[idx] = True
    return vec


def _jaccard(a: list[bool], b: list[bool]) -> float:
    inter = sum(x and y for x, y in zip(a, b))
    union = sum(x or y for x, y in zip(a, b))
    return inter / union if union > 0 else 0.0


def _prefix_sync_score(
    prefix_events: dict[str, list[tuple[int, str, Optional[list[int]]]]],
    start_ts: int,
) -> float:
    """Jaccard médio entre vetores horárias de todos os pares de prefixos."""
    vecs = [_hourly_vector(evts, start_ts) for evts in prefix_events.values()]
    if len(vecs) < 2:
        return 1.0  # um único prefixo → definido como sincronizado

    total, pairs = 0.0, 0
    for i in range(len(vecs)):
        for j in range(i + 1, len(vecs)):
            total += _jaccard(vecs[i], vecs[j])
            pairs += 1
    return round(total / pairs, 3) if pairs > 0 else 0.0


def _upstream_analysis(
    prefix_events: dict[str, list[tuple[int, str, Optional[list[int]]]]],
) -> tuple[Optional[int], float, dict[int, int]]:
    """
    Analisa o upstream dominante nos eventos de announce.
    Retorna (suspected_upstream_asn, upstream_concentration_pct, {asn: count}).
    """
    counts: dict[int, int] = defaultdict(int)
    total = 0
    for evts in prefix_events.values():
        for ts, evt_type, aspath in evts:
            if evt_type == "A" and aspath and len(aspath) >= 2:
                upstream = aspath[-2]
                counts[upstream] += 1
                total += 1

    if not counts:
        return None, 0.0, {}

    top_asn = max(counts, key=lambda k: counts[k])
    conc    = counts[top_asn] / total * 100
    return top_asn, round(conc, 1), dict(counts)


def _hot_prefixes(
    prefix_events: dict[str, list[tuple[int, str, Optional[list[int]]]]],
    start_ts: int,
    max_prefixes: int = 10,
) -> list[dict]:
    """Top prefixos por volume de eventos, com upstream dominante por prefixo."""
    rows = []
    for pfx, evts in prefix_events.items():
        flap_events = len([e for e in evts if e[1] == "W"])
        if flap_events == 0:
            continue
        # upstream dominante específico do prefixo
        up_counts: dict[int, int] = defaultdict(int)
        up_total = 0
        for ts, et, aspath in evts:
            if et == "A" and aspath and len(aspath) >= 2:
                up_counts[aspath[-2]] += 1
                up_total += 1
        if up_counts:
            dom_up  = max(up_counts, key=lambda k: up_counts[k])
            dom_pct = round(up_counts[dom_up] / up_total * 100, 1)
        else:
            dom_up, dom_pct = None, 0.0

        rows.append({
            "prefix":                pfx,
            "flap_events":           flap_events,
            "dominant_upstream_asn": dom_up,
            "dominant_upstream_pct": dom_pct,
        })

    rows.sort(key=lambda r: -r["flap_events"])
    return rows[:max_prefixes]


def _verdict(sync_score: float, upstream_conc: float) -> str:
    if sync_score > _SYNC_UPSTREAM and upstream_conc > _CONC_UPSTREAM:
        return "upstream_instability"
    if sync_score < _SYNC_PREFIX:
        return "prefix_specific"
    return "origin_instability"


# ---------------------------------------------------------------------------
# Correlação cross-AS (upstreams suspeitos compartilhados)
# ---------------------------------------------------------------------------

def _cross_as_suspected_upstreams(
    diagnoses: list[dict],
    all_prefix_events: dict[int, dict[str, list]],
    start_ts: int,
) -> list[dict]:
    """
    Para cada upstream que aparece como suspeito em ≥2 ASes com
    upstream_instability, calcula sobreposição temporal e atribui eventos.
    """
    # upstream → lista de (asn, upstream_conc, hourly_vec_AS)
    upstream_map: dict[int, list] = defaultdict(list)
    for d in diagnoses:
        sup = d.get("suspected_upstream_asn")
        if sup is None:
            continue
        asn  = d["asn"]
        vec  = [False] * _HOURS
        for evts in all_prefix_events.get(asn, {}).values():
            for ts, et, _ in evts:
                idx = (ts - start_ts) // 3600
                if 0 <= idx < _HOURS:
                    vec[idx] = True
        upstream_map[sup].append({"asn": asn, "vec": vec, "conc": d["upstream_concentration_pct"]})

    results = []
    for up_asn, affected in upstream_map.items():
        if len(affected) < 2:
            continue
        # contar eventos atribuídos a este upstream
        events_attributed = 0
        for d in diagnoses:
            if d.get("suspected_upstream_asn") == up_asn:
                asn = d["asn"]
                for evts in all_prefix_events.get(asn, {}).values():
                    events_attributed += len([e for e in evts if e[1] == "A"
                                              and e[2] and len(e[2]) >= 2
                                              and e[2][-2] == up_asn])
        # hora de pico
        combined = [False] * _HOURS
        for a in affected:
            for i, v in enumerate(a["vec"]):
                if v:
                    combined[i] = True
        # encontrar a hora com mais eventos
        hourly_counts: list[int] = [0] * _HOURS
        for a in affected:
            asn = a["asn"]
            for evts in all_prefix_events.get(asn, {}).values():
                for ts, et, aspath in evts:
                    if et == "A" and aspath and len(aspath) >= 2 and aspath[-2] == up_asn:
                        idx = (ts - start_ts) // 3600
                        if 0 <= idx < _HOURS:
                            hourly_counts[idx] += 1
        peak_idx = hourly_counts.index(max(hourly_counts)) if hourly_counts else 0
        peak_utc = (
            datetime.datetime.utcfromtimestamp(start_ts + peak_idx * 3600)
            .strftime("%Y-%m-%dT%H:00Z")
        )

        results.append({
            "asn":                  up_asn,
            "name":                 "",  # preenchido na etapa de publicação
            "affected_origin_ases": [a["asn"] for a in affected],
            "events_attributed":    events_attributed,
            "peak_hour_utc":        peak_utc,
        })

    results.sort(key=lambda r: -r["events_attributed"])
    return results


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

def run(date_str: str, base: Path, top_n: int, force: bool, log) -> bool:
    norm     = normalized_path(base, date_str, "summary")
    raw_dir  = raw_path(base, date_str, "route-views.saopaulo")
    out_path = norm / "bgp_stability_deep.json.gz"

    if out_path.exists() and not force:
        log.info("bgp_stability_deep.json.gz já existe — use --force para reprocessar",
                 path=str(out_path))
        return True

    # 1. Carregar top N da etapa 1
    top_entries = _load_top_n(norm, top_n, log)
    if not top_entries:
        return False

    target_asns = {e["asn"] for e in top_entries}
    log.info("top ASes carregados", top_n=len(top_entries), asns=sorted(target_asns))

    # 2. Mapear prefixos dos top ASes
    prefix_to_asn = _build_prefix_to_asn(norm, target_asns, log)
    if not prefix_to_asn:
        log.error("nenhum prefixo encontrado para os ASes alvo")
        return False

    # 3. Determinar start_ts a partir do período da etapa 1
    stab_data  = read_json_gz(norm / "bgp_stability.json.gz")
    start_date = stab_data.get("period", {}).get("start", "")
    if not start_date:
        log.error("campo 'period.start' ausente em bgp_stability.json.gz")
        return False
    start_ts = int(datetime.datetime.strptime(start_date, "%Y-%m-%d")
                   .replace(tzinfo=datetime.timezone.utc).timestamp())

    # 4. Verificar cache
    mrt_files = sorted(raw_dir.glob("updates.*.bz2"))
    if not mrt_files:
        log.error("cache MRT não encontrado — execute primeiro bgp_updates_routeviews",
                  path=str(raw_dir))
        return False
    log.info("arquivos MRT em cache", count=len(mrt_files))

    # 5. Parsear todos os arquivos, acumulando eventos com AS_PATH
    acc = DeepAccumulator(prefix_to_asn, start_ts)
    for i, mrt_path in enumerate(mrt_files, 1):
        if i % 100 == 0:
            log.info("progresso parse", done=i, total=len(mrt_files))
        try:
            raw_bytes = mrt_path.read_bytes()
        except Exception as exc:
            log.warning("falha ao ler arquivo", path=str(mrt_path), error=str(exc))
            continue
        _parse_file(raw_bytes, acc)

    all_prefix_events = acc.as_data()
    log.info("parse concluído", asns_com_eventos=len(all_prefix_events))

    # 6. Diagnóstico por AS
    diagnoses = []
    for entry in top_entries:
        asn            = entry["asn"]
        prefix_events  = all_prefix_events.get(asn, {})
        sync_score     = _prefix_sync_score(prefix_events, start_ts)
        sup_asn, sup_conc, _ = _upstream_analysis(prefix_events)
        verdict        = _verdict(sync_score, sup_conc if sup_asn else 0.0)
        hot            = _hot_prefixes(prefix_events, start_ts)

        diagnoses.append({
            "asn":                       asn,
            "verdict":                   verdict,
            "prefix_sync_score":         sync_score,
            "suspected_upstream_asn":    sup_asn,
            "upstream_concentration_pct": sup_conc,
            "hot_prefixes":              hot,
        })

    # 7. Upstreams suspeitos cross-AS
    suspected = _cross_as_suspected_upstreams(diagnoses, all_prefix_events, start_ts)

    # 8. Escrever resultado
    out = {
        "generated_at":       now_iso(),
        "date":               date_str,
        "top_n":              top_n,
        "suspected_upstreams": suspected,
        "as_diagnosis":       diagnoses,
    }
    norm.mkdir(parents=True, exist_ok=True)
    write_json_gz(out_path, out)
    log.info("bgp_stability_deep.json.gz gravado", path=str(out_path),
             asns=len(diagnoses), suspected_upstreams=len(suspected))
    return True


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Análise aprofundada de estabilidade BGP (etapa 2)"
    )
    p.add_argument("--date",      default=today_str())
    p.add_argument("--top",       type=int, default=30)
    p.add_argument("--force",     action="store_true")
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args(argv)

    log  = configure_logging(args.log_level)
    base = data_dir()

    ok = run(args.date, base, args.top, args.force, log)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
