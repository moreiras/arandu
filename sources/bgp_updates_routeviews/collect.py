# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Coleta e análise de arquivos de update BGP do RouteViews para os 7 dias anteriores ao snapshot.

Coletor: route-views.saopaulo (IPv4 + IPv6 em arquivos únicos, peers latino-americanos).

Cache em disco: arquivos .bz2 são mantidos em data/raw/{date}/route-views.saopaulo/
e apagados apenas ao final do processamento bem-sucedido do snapshot seguinte (date + 7 dias).

Inputs:
  normalized/{date}/summary/origin-prefixes-v4.json.gz  — estado inicial de prefix→AS (v4)
  normalized/{date}/summary/origin-prefixes-v6.json.gz  — estado inicial de prefix→AS (v6)
  normalized/{date}/summary/registro_br.json.gz         — conjunto de ASNs BR

Output:
  normalized/{date}/summary/bgp_stability.json.gz       — dados brutos por (AS, prefixo)

Uso:
  python -m sources.bgp_updates_routeviews.collect
  python -m sources.bgp_updates_routeviews.collect --date 2026-06-28
  python -m sources.bgp_updates_routeviews.collect --force
"""

from __future__ import annotations

import argparse
import bz2
import datetime
import io
import json
import shutil
import sys
import tempfile
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, median
from typing import Optional
import urllib.request

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
    read_json_gz,
    today_str,
    write_json_gz,
    ignorar_sigpipe,
)
from core.site import USER_AGENT

# O mrtparse zera o tratamento de SIGPIPE ao ser importado (ver ignorar_sigpipe)
ignorar_sigpipe()

# ---------------------------------------------------------------------------
# Constantes MRT/BGP
# ---------------------------------------------------------------------------
_BGP4MP              = 16
_BGP4MP_ET           = 17
_BGP4MP_MESSAGE      = 1
_BGP4MP_MESSAGE_AS4  = 4

_BGP_AS_PATH         = 2
_MP_REACH_NLRI       = 14
_MP_UNREACH_NLRI     = 15

_COLLECTOR           = "route-views.saopaulo"
_RV_BASE             = "http://archive.routeviews.org/route-views.saopaulo/bgpdata"
_DAYS                = 7
_PARALLEL_DOWNLOADS  = 8

# Deduplicação temporal: eventos do mesmo tipo para o mesmo (asn, prefix)
# dentro dessas janelas são considerados ruído multi-peer, não eventos reais.
_DEDUP_ANN_WD_SEC    = 90   # anúncios e retiradas
_DEDUP_ATTR_SEC      = 30   # attribute updates (mudanças mais rápidas são legítimas)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _first_key(d: dict):
    return next(iter(d), None)


def _afi(prefix: str) -> str:
    return "v6" if ":" in prefix else "v4"


def _extract_aspath(path_attributes: list) -> Optional[list[int]]:
    for attr in path_attributes:
        if _first_key(attr.get("type", {})) == _BGP_AS_PATH:
            asns: list[int] = []
            for seg in attr.get("value", []):
                for asn in seg.get("value", []):
                    try:
                        asns.append(int(asn))
                    except (ValueError, TypeError):
                        pass
            return asns if asns else None
    return None


# ---------------------------------------------------------------------------
# Geração de URLs e paths de cache
# ---------------------------------------------------------------------------

def _update_urls(date_str: str) -> list[tuple[datetime.datetime, str]]:
    """Retorna lista de (datetime_utc, url) para os 7 dias anteriores ao snapshot."""
    end   = datetime.date.fromisoformat(date_str)
    start = end - datetime.timedelta(days=_DAYS)
    urls: list[tuple[datetime.datetime, str]] = []
    d = start
    while d < end:
        ym = d.strftime("%Y.%m")
        ds = d.strftime("%Y%m%d")
        for h in range(24):
            for m in (0, 15, 30, 45):
                ts  = datetime.datetime(d.year, d.month, d.day, h, m)
                url = f"{_RV_BASE}/{ym}/UPDATES/updates.{ds}.{h:02d}{m:02d}.bz2"
                urls.append((ts, url))
        d += datetime.timedelta(days=1)
    return urls


def _cache_path(base: Path, date_str: str, url: str) -> Path:
    fname = url.rsplit("/", 1)[-1]
    return base / "raw" / date_str / _COLLECTOR / fname


# ---------------------------------------------------------------------------
# Download com cache em disco
# ---------------------------------------------------------------------------

def _download_one(url: str, dest: Path, log) -> bool:
    """Baixa url para dest. Retorna True se ok (inclusive cache hit)."""
    if dest.exists():
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        tmp.write_bytes(data)
        tmp.rename(dest)
        return True
    except Exception as exc:
        log.debug("download falhou", file=dest.name, error=str(exc))
        tmp.unlink(missing_ok=True)
        return False


def _download_parallel(urls: list[tuple[datetime.datetime, str]], base: Path,
                        date_str: str, log) -> dict[str, bool]:
    """Baixa todos os arquivos em paralelo. Retorna url→ok."""
    results: dict[str, bool] = {}
    cache_hits = already = 0

    # Conta cache hits antes de baixar
    for _, url in urls:
        if _cache_path(base, date_str, url).exists():
            already += 1

    if already:
        log.info("cache hit", cached=already, total=len(urls))

    to_download = [(ts, url) for ts, url in urls
                   if not _cache_path(base, date_str, url).exists()]

    if to_download:
        log.info("iniciando downloads", files=len(to_download), parallel=_PARALLEL_DOWNLOADS)

    with ThreadPoolExecutor(max_workers=_PARALLEL_DOWNLOADS) as ex:
        futures = {
            ex.submit(_download_one, url, _cache_path(base, date_str, url), log): url
            for _, url in to_download
        }
        done = 0
        for fut in as_completed(futures):
            url = futures[fut]
            ok  = fut.result()
            results[url] = ok
            done += 1
            if done % 96 == 0:
                log.info("downloads", done=done, total=len(to_download))

    # Marca como ok os que já estavam em cache
    for _, url in urls:
        if url not in results:
            results[url] = True

    return results


# ---------------------------------------------------------------------------
# Acumulador streaming com deduplicação estado-ciente
# ---------------------------------------------------------------------------

@dataclass
class PrefixStats:
    afi:              str
    # Contagens diárias (7 dias)
    ann_by_day:       list[int]   = field(default_factory=lambda: [0] * _DAYS)
    wd_by_day:        list[int]   = field(default_factory=lambda: [0] * _DAYS)
    attr_upd_by_day:  list[int]   = field(default_factory=lambda: [0] * _DAYS)
    # Séries horárias por tipo (7 * 24 = 168 slots)
    ann_hourly:       list[int]   = field(default_factory=lambda: [0] * (_DAYS * 24))
    wd_hourly:        list[int]   = field(default_factory=lambda: [0] * (_DAYS * 24))
    attr_upd_hourly:  list[int]   = field(default_factory=lambda: [0] * (_DAYS * 24))
    # Estado para deduplicação e flap detection
    current_state:    str | None  = None
    last_evt_type:    str | None  = None
    last_evt_ts:      int         = 0
    flap_cycles:      int         = 0
    hold_times:       list[int]   = field(default_factory=list)
    last_announce_ts: int         = 0
    last_change_ts:   int         = 0


class UpdateAccumulator:
    def __init__(self, start_ts: int) -> None:
        self._start   = start_ts
        self._data:   dict[tuple[int, str], PrefixStats] = {}
        self.raw_seen = 0   # mensagens recebidas antes da dedup
        self.counted  = 0   # eventos efetivamente contados

    def _get(self, asn: int, prefix: str) -> PrefixStats:
        key = (asn, prefix)
        if key not in self._data:
            self._data[key] = PrefixStats(afi=_afi(prefix))
        return self._data[key]

    def record(self, ts: int, evt_type: str, prefix: str, asn: int) -> None:
        self.raw_seen += 1
        day_idx  = min(max((ts - self._start) // 86400, 0), _DAYS - 1)
        hour_idx = min(max((ts - self._start) // 3600,  0), _DAYS * 24 - 1)
        ps = self._get(asn, prefix)

        # Deduplicação estado-ciente:
        # Mesmo tipo de evento dentro da janela → ruído multi-peer, ignora.
        # Mudança de tipo → conta sempre (transição de estado real).
        if evt_type == ps.last_evt_type:
            window = _DEDUP_ATTR_SEC if evt_type == "X" else _DEDUP_ANN_WD_SEC
            if (ts - ps.last_evt_ts) < window:
                return

        self.counted += 1
        ps.last_evt_type = evt_type
        ps.last_evt_ts   = ts

        if evt_type == "A":
            if ps.current_state == "A":
                # Prefix já anunciado com atributos diferentes → attribute update
                ps.attr_upd_by_day[day_idx]  += 1
                ps.attr_upd_hourly[hour_idx] += 1
            else:
                ps.ann_by_day[day_idx]  += 1
                ps.ann_hourly[hour_idx] += 1
                if ps.current_state == "W":
                    ps.flap_cycles += 1
            ps.last_announce_ts = ts
        else:  # "W"
            ps.wd_by_day[day_idx]  += 1
            ps.wd_hourly[hour_idx] += 1
            if ps.current_state == "A":
                hold = ts - ps.last_announce_ts
                if hold > 0:
                    ps.hold_times.append(hold)

        ps.current_state  = evt_type
        ps.last_change_ts = ts

    @property
    def data(self) -> dict[tuple[int, str], PrefixStats]:
        return self._data


# ---------------------------------------------------------------------------
# Inicialização do prefix_origin
# ---------------------------------------------------------------------------

def _init_prefix_origin(base: Path, date_str: str, log) -> dict[str, int]:
    origin: dict[str, int] = {}
    target = datetime.date.fromisoformat(date_str) - datetime.timedelta(days=_DAYS)
    norm_root = base / "normalized"

    for afi in ("v4", "v6"):
        candidates: list[Path] = []
        if norm_root.exists():
            for d in sorted(norm_root.iterdir()):
                if not d.is_dir():
                    continue
                try:
                    snap_date = datetime.date.fromisoformat(d.name)
                except ValueError:
                    continue
                if snap_date <= target:
                    candidates.append(d / "summary" / f"origin-prefixes-{afi}.json.gz")
        candidates.append(normalized_path(base, date_str, "summary") / f"origin-prefixes-{afi}.json.gz")

        for path in reversed(candidates):
            if path.exists():
                try:
                    data = read_json_gz(path)
                    for asn_str, prefixes in data.items():
                        asn_int = int(asn_str)
                        for pfx in prefixes:
                            origin[pfx] = asn_int
                    log.info("origin prefixes carregados", afi=afi, count=len(data), source=str(path))
                    break
                except Exception as exc:
                    log.warning("falha ao carregar origin-prefixes", afi=afi, path=str(path), error=str(exc))

    log.info("prefix_origin inicializado", total_prefixes=len(origin))
    return origin


# ---------------------------------------------------------------------------
# Carregamento de BR ASNs
# ---------------------------------------------------------------------------

def _load_br_asns(base: Path, date_str: str, log) -> set[int]:
    norm = normalized_path(base, date_str, "summary")
    candidates = [norm / "registro_br.json.gz"]
    norm_root = base / "normalized"
    if norm_root.exists():
        for d in sorted(norm_root.iterdir(), reverse=True):
            if d.name != date_str and d.is_dir():
                candidates.append(d / "summary" / "registro_br.json.gz")
                break
    for path in candidates:
        if path.exists():
            try:
                data = read_json_gz(path)
                asns = {a["asn"] for a in data.get("asns", [])}
                log.info("br_asns carregados", count=len(asns), source=str(path))
                return asns
            except Exception as exc:
                log.warning("falha ao carregar registro_br", path=str(path), error=str(exc))
    log.warning("br_asns não disponível")
    return set()


# ---------------------------------------------------------------------------
# Parse de um arquivo de update BGP4MP
# ---------------------------------------------------------------------------

def _parse_updates(
    data_bz2: bytes,
    br_asns: set[int],
    prefix_origin: dict[str, int],
    accumulator: UpdateAccumulator,
    log,
) -> tuple[int, int]:
    """Parseia um arquivo bz2 de update BGP4MP em memória.

    Retorna (eventos_br_v4, eventos_br_v6) — contagem ANTES da deduplicação.
    """
    ev_v4 = ev_v6 = 0
    try:
        raw = bz2.decompress(data_bz2)
    except Exception as exc:
        log.debug("falha ao descomprimir arquivo", error=str(exc))
        return 0, 0

    try:
        reader = mrtparse.Reader(io.BytesIO(raw))
    except Exception as exc:
        log.debug("falha ao criar reader MRT", error=str(exc))
        return 0, 0

    for m in reader:
        if m.err:
            continue
        d = m.data
        mrt_type = _first_key(d.get("type", {}))
        if mrt_type not in (_BGP4MP, _BGP4MP_ET):
            continue

        ts_raw = d.get("timestamp", 0)
        ts = _first_key(ts_raw) if isinstance(ts_raw, dict) else int(ts_raw)
        body = d.get("bgp_message", {})
        if not body:
            continue

        path_attrs = body.get("path_attributes", [])
        aspath     = _extract_aspath(path_attrs)
        origin_as  = aspath[-1] if aspath else None

        # ---- IPv4: NLRI padrão ----
        for nlri in body.get("nlri", []):
            prefix = f"{nlri['prefix']}/{nlri['length']}"
            if origin_as and origin_as in br_asns:
                prefix_origin[prefix] = origin_as
                accumulator.record(ts, "A", prefix, origin_as)
                ev_v4 += 1

        # ---- IPv4: withdrawals padrão ----
        for wr in body.get("withdrawn_routes", []):
            prefix = f"{wr['prefix']}/{wr['length']}"
            oas = prefix_origin.get(prefix)
            if oas and oas in br_asns:
                accumulator.record(ts, "W", prefix, oas)
                ev_v4 += 1

        # ---- IPv6: MP_REACH_NLRI e MP_UNREACH_NLRI ----
        for attr in path_attrs:
            attr_type = _first_key(attr.get("type", {}))
            val       = attr.get("value", {})

            if attr_type == _MP_REACH_NLRI:
                for nlri in val.get("nlri", []):
                    prefix = f"{nlri['prefix']}/{nlri['length']}"
                    if origin_as and origin_as in br_asns:
                        prefix_origin[prefix] = origin_as
                        accumulator.record(ts, "A", prefix, origin_as)
                        ev_v6 += 1

            elif attr_type == _MP_UNREACH_NLRI:
                for wr in val.get("withdrawn_routes", []):
                    prefix = f"{wr['prefix']}/{wr['length']}"
                    oas = prefix_origin.get(prefix)
                    if oas and oas in br_asns:
                        accumulator.record(ts, "W", prefix, oas)
                        ev_v6 += 1

    return ev_v4, ev_v6


# ---------------------------------------------------------------------------
# Computação de métricas finais
# ---------------------------------------------------------------------------

_BINS = [0, 0.5, 1, 2, 5, 10, 20, 50, 100, 1000, float("inf")]


def _distribution(epppd_values: list[float]) -> dict:
    counts = [0] * (len(_BINS) - 1)
    for v in epppd_values:
        for i in range(len(_BINS) - 1):
            if _BINS[i] <= v < _BINS[i + 1]:
                counts[i] += 1
                break
    buckets = [
        {
            "min":       _BINS[i],
            "max":       _BINS[i + 1] if _BINS[i + 1] != float("inf") else None,
            "label":     f"{_BINS[i]}–{_BINS[i+1]}" if _BINS[i + 1] != float("inf") else f">{_BINS[i]}",
            "asn_count": counts[i],
        }
        for i in range(len(counts))
    ]
    arr = sorted(epppd_values)
    n   = len(arr)
    return {
        "buckets":         buckets,
        "p50":             round(arr[int(n * 0.50)], 2) if n else 0,
        "p90":             round(arr[int(n * 0.90)], 2) if n else 0,
        "p95":             round(arr[int(n * 0.95)], 2) if n else 0,
        "p99":             round(arr[int(n * 0.99)], 2) if n else 0,
        "max":             round(arr[-1], 2) if n else 0,
        "asn_count_total": n,
    }


def _classify(
    epppd: float, max_flap: int, burst_conc: float, hold_sec: int,
    ann: int, wd: int, attr_upd: int,
) -> tuple[str, str]:
    if   epppd > 50: severity = "critical"
    elif epppd > 10: severity = "high"
    elif epppd > 3:  severity = "medium"
    else:            severity = "low"

    total = ann + wd + attr_upd

    if max_flap > 5 and hold_sec > 0 and hold_sec < 300 and burst_conc < 0.3:
        return "chronic_flapper", severity

    if burst_conc >= 0.5 and epppd > 5:
        return "burst_event", severity

    if attr_upd > 0 and total > 0 and attr_upd / total > 0.5:
        return "attribute_oscillator", severity

    if ann > 0 and total > 0 and ann / total > 0.7 and wd / max(total, 1) < 0.1 and epppd > 3:
        return "more_specific_injection", severity

    return "noisy", severity


def _compute_stability(
    accumulator: UpdateAccumulator,
    start_date: datetime.date,
    br_asns: set[int],
) -> dict:
    """Agrega estatísticas do acumulador e computa o JSON de estabilidade."""

    by_asn: dict[int, dict[str, PrefixStats]] = defaultdict(dict)
    for (asn, prefix), ps in accumulator.data.items():
        if asn in br_asns:
            by_asn[asn][prefix] = ps

    as_stability:   list[dict]  = []
    epppd_v4_list:  list[float] = []
    epppd_v6_list:  list[float] = []
    total_br_v4 = total_br_v6 = 0

    # Agregado global horário (todos os ASes BR)
    hourly_global_ann      = [0] * (_DAYS * 24)
    hourly_global_wd       = [0] * (_DAYS * 24)
    hourly_global_attr_upd = [0] * (_DAYS * 24)

    for asn, prefix_map in by_asn.items():
        pfxs_v4 = {p: ps for p, ps in prefix_map.items() if ps.afi == "v4"}
        pfxs_v6 = {p: ps for p, ps in prefix_map.items() if ps.afi == "v6"}
        cnt_v4  = max(len(pfxs_v4), 1)
        cnt_v6  = max(len(pfxs_v6), 1)
        cnt_tot = max(len(prefix_map), 1)

        # Totais do período
        tot_ann      = sum(sum(ps.ann_by_day)      for ps in prefix_map.values())
        tot_wd       = sum(sum(ps.wd_by_day)       for ps in prefix_map.values())
        tot_attr_upd = sum(sum(ps.attr_upd_by_day) for ps in prefix_map.values())
        tot_ev       = tot_ann + tot_wd + tot_attr_upd

        # Totais por AFI
        tot_ann_v4      = sum(sum(ps.ann_by_day)      for ps in pfxs_v4.values())
        tot_wd_v4       = sum(sum(ps.wd_by_day)       for ps in pfxs_v4.values())
        tot_attr_upd_v4 = sum(sum(ps.attr_upd_by_day) for ps in pfxs_v4.values())
        tot_ann_v6      = sum(sum(ps.ann_by_day)      for ps in pfxs_v6.values())
        tot_wd_v6       = sum(sum(ps.wd_by_day)       for ps in pfxs_v6.values())
        tot_attr_upd_v6 = sum(sum(ps.attr_upd_by_day) for ps in pfxs_v6.values())

        total_br_v4 += tot_ann_v4 + tot_wd_v4 + tot_attr_upd_v4
        total_br_v6 += tot_ann_v6 + tot_wd_v6 + tot_attr_upd_v6

        epppd    = tot_ev / cnt_tot / _DAYS
        epppd_v4 = (tot_ann_v4 + tot_wd_v4 + tot_attr_upd_v4) / cnt_v4 / _DAYS if pfxs_v4 else 0.0
        epppd_v6 = (tot_ann_v6 + tot_wd_v6 + tot_attr_upd_v6) / cnt_v6 / _DAYS if pfxs_v6 else 0.0

        if pfxs_v4:
            epppd_v4_list.append(epppd_v4)
        if pfxs_v6:
            epppd_v6_list.append(epppd_v6)

        # Flap metrics
        max_flap  = max((ps.flap_cycles for ps in prefix_map.values()), default=0)
        flapping  = sum(1 for ps in prefix_map.values() if ps.flap_cycles > 2)
        hold_flat = [h for ps in prefix_map.values() for h in ps.hold_times]
        mean_hold = int(mean(hold_flat)) if hold_flat else 0

        # Burst concentration (hora mais movimentada do AS)
        hourly_agg = [0] * (_DAYS * 24)
        for ps in prefix_map.values():
            for i in range(_DAYS * 24):
                v = ps.ann_hourly[i] + ps.wd_hourly[i] + ps.attr_upd_hourly[i]
                hourly_agg[i] += v
        agg_tot  = sum(hourly_agg)
        max_hour = max(hourly_agg) if hourly_agg else 0
        max_burst = max_hour / agg_tot if agg_tot > 0 else 0.0

        # Série horária por tipo deste AS
        as_ann_hourly      = [0] * (_DAYS * 24)
        as_wd_hourly       = [0] * (_DAYS * 24)
        as_attr_upd_hourly = [0] * (_DAYS * 24)
        for ps in prefix_map.values():
            for i in range(_DAYS * 24):
                as_ann_hourly[i]      += ps.ann_hourly[i]
                as_wd_hourly[i]       += ps.wd_hourly[i]
                as_attr_upd_hourly[i] += ps.attr_upd_hourly[i]

        # Acumula no global
        for i in range(_DAYS * 24):
            hourly_global_ann[i]      += as_ann_hourly[i]
            hourly_global_wd[i]       += as_wd_hourly[i]
            hourly_global_attr_upd[i] += as_attr_upd_hourly[i]

        classification, severity = _classify(
            epppd, max_flap, max_burst, mean_hold, tot_ann, tot_wd, tot_attr_upd,
        )

        # Daily breakdown por AFI
        daily: list[dict] = []
        for i in range(_DAYS):
            day_ann_v4      = sum(ps.ann_by_day[i]      for ps in pfxs_v4.values())
            day_wd_v4       = sum(ps.wd_by_day[i]       for ps in pfxs_v4.values())
            day_attr_upd_v4 = sum(ps.attr_upd_by_day[i] for ps in pfxs_v4.values())
            day_ann_v6      = sum(ps.ann_by_day[i]      for ps in pfxs_v6.values())
            day_wd_v6       = sum(ps.wd_by_day[i]       for ps in pfxs_v6.values())
            day_attr_upd_v6 = sum(ps.attr_upd_by_day[i] for ps in pfxs_v6.values())
            day_tot = (day_ann_v4 + day_wd_v4 + day_attr_upd_v4 +
                       day_ann_v6 + day_wd_v6 + day_attr_upd_v6)
            active = sum(1 for ps in prefix_map.values()
                         if ps.ann_by_day[i] + ps.wd_by_day[i] + ps.attr_upd_by_day[i] > 0)
            daily.append({
                "date":              (start_date + datetime.timedelta(days=i)).isoformat(),
                "total_events":      day_tot,
                "announcements_v4":  day_ann_v4,
                "withdrawals_v4":    day_wd_v4,
                "attr_updates_v4":   day_attr_upd_v4,
                "announcements_v6":  day_ann_v6,
                "withdrawals_v6":    day_wd_v6,
                "attr_updates_v6":   day_attr_upd_v6,
                "active_prefixes":   active,
            })

        # Top prefixos (max 10)
        sorted_pfx = sorted(
            prefix_map.items(),
            key=lambda kv: sum(kv[1].ann_by_day) + sum(kv[1].wd_by_day),
            reverse=True,
        )[:10]
        top_prefixes: list[dict] = []
        for pfx, ps in sorted_pfx:
            ps_ann      = sum(ps.ann_by_day)
            ps_wd       = sum(ps.wd_by_day)
            ps_attr_upd = sum(ps.attr_upd_by_day)
            ps_tot      = ps_ann + ps_wd + ps_attr_upd
            if ps_tot == 0:
                continue
            max_bucket = max(ps.ann_hourly[i] + ps.wd_hourly[i] + ps.attr_upd_hourly[i]
                             for i in range(_DAYS * 24))
            bc      = max_bucket / ps_tot if ps_tot else 0.0
            pph     = int(mean(ps.hold_times)) if ps.hold_times else 0
            peak_idx = max(range(_DAYS * 24),
                           key=lambda i: ps.ann_hourly[i] + ps.wd_hourly[i] + ps.attr_upd_hourly[i])
            peak_dt = (
                datetime.datetime(start_date.year, start_date.month, start_date.day)
                + datetime.timedelta(hours=peak_idx)
            ).isoformat() + "Z"
            top_prefixes.append({
                "prefix":                 pfx,
                "afi":                    ps.afi,
                "total_events":           ps_tot,
                "announcements":          ps_ann,
                "withdrawals":            ps_wd,
                "attribute_updates":      ps_attr_upd,
                "flap_cycles":            ps.flap_cycles,
                "mean_hold_time_sec":     pph,
                "burst_concentration_1h": round(bc, 3),
                "burst_peak_utc":         peak_dt,
                "daily_events":           [ps.ann_by_day[i] + ps.wd_by_day[i] for i in range(_DAYS)],
            })

        as_stability.append({
            "asn":             asn,
            "name":            "",
            "rank":            0,
            "classification":  classification,
            "severity":        severity,
            "prefix_count_v4": len(pfxs_v4),
            "prefix_count_v6": len(pfxs_v6),
            "period": {
                "total_events":                 tot_ev,
                "announcements":                tot_ann,
                "withdrawals":                  tot_wd,
                "attribute_updates":            tot_attr_upd,
                "announcements_v4":             tot_ann_v4,
                "withdrawals_v4":               tot_wd_v4,
                "attribute_updates_v4":         tot_attr_upd_v4,
                "announcements_v6":             tot_ann_v6,
                "withdrawals_v6":               tot_wd_v6,
                "attribute_updates_v6":         tot_attr_upd_v6,
                "events_per_prefix_per_day":    round(epppd, 2),
                "events_per_prefix_per_day_v4": round(epppd_v4, 2),
                "events_per_prefix_per_day_v6": round(epppd_v6, 2),
                "flapping_prefixes":            flapping,
                "max_flap_cycles":              max_flap,
                "mean_hold_time_sec":           mean_hold,
                "burst_concentration_1h":       round(max_burst, 3),
            },
            "daily":        daily,
            "hourly":       {
                "ann":      as_ann_hourly,
                "wd":       as_wd_hourly,
                "attr_upd": as_attr_upd_hourly,
            },
            "top_prefixes": top_prefixes,
        })

    # Ordenar por epppd descendente e atribuir rank
    as_stability.sort(key=lambda x: x["period"]["events_per_prefix_per_day"], reverse=True)
    for i, entry in enumerate(as_stability, 1):
        entry["rank"] = i

    # Calcular estatísticas de epppd e classificar categorias de ruído
    _epppd_all = [e["period"]["events_per_prefix_per_day"] for e in as_stability]
    if _epppd_all:
        _epppd_median = round(median(_epppd_all), 2)
        _epppd_mean   = round(mean(_epppd_all), 2)
        _epppd_max    = round(max(_epppd_all), 2)
    else:
        _epppd_median = _epppd_mean = _epppd_max = 0.0

    def _noise_cat(v: float) -> str:
        if v < _epppd_median:              return "estavel"
        if v < _epppd_mean:               return "inquieto"
        if v < 100 * _epppd_median:       return "barulhento"
        return "critico"

    for entry in as_stability:
        entry["noise_category"] = _noise_cat(entry["period"]["events_per_prefix_per_day"])

    epppd_stats = {
        "median": _epppd_median,
        "mean":   _epppd_mean,
        "max":    _epppd_max,
    }

    # Remover série horária por AS de entradas com severity "low"
    # (reduz tamanho do JSON; a série global cobre a visão geral)
    for entry in as_stability:
        if entry["severity"] == "low":
            del entry["hourly"]

    # Timestamps para o eixo X do gráfico horário
    hourly_timestamps = [
        (datetime.datetime(start_date.year, start_date.month, start_date.day,
                           tzinfo=datetime.timezone.utc)
         + datetime.timedelta(hours=i)).isoformat()
        for i in range(_DAYS * 24)
    ]

    return {
        "distribution": {
            "v4": _distribution(epppd_v4_list),
            "v6": _distribution(epppd_v6_list),
        },
        "epppd_stats":    epppd_stats,
        "br_events_v4":   total_br_v4,
        "br_events_v6":   total_br_v6,
        "hourly_global": {
            "timestamps": hourly_timestamps,
            "ann":        hourly_global_ann,
            "wd":         hourly_global_wd,
            "attr_upd":   hourly_global_attr_upd,
        },
        "as_stability":   as_stability,
    }


# ---------------------------------------------------------------------------
# Limpeza de cache antigo
# ---------------------------------------------------------------------------

def _cleanup_old_cache(base: Path, date_str: str, log) -> None:
    """Apaga o cache raw do snapshot que caiu fora da janela (date − 7 dias)."""
    old_date = (datetime.date.fromisoformat(date_str) - datetime.timedelta(days=_DAYS)).isoformat()
    old_cache = base / "raw" / old_date
    if old_cache.exists():
        try:
            shutil.rmtree(old_cache)
            log.info("cache antigo removido", path=str(old_cache))
        except Exception as exc:
            log.warning("falha ao remover cache antigo", path=str(old_cache), error=str(exc))


# ---------------------------------------------------------------------------
# Ponto de entrada principal
# ---------------------------------------------------------------------------

def run(date_str: str, base: Path, log, force: bool = False) -> bool:
    norm = normalized_path(base, date_str, "summary")
    norm.mkdir(parents=True, exist_ok=True)
    manifest_path = norm / "bgp_stability_manifest.json"

    if not force and manifest_path.exists():
        log.info("bgp_stability já processado; use --force para reprocessar", date=date_str)
        return True

    br_asns = _load_br_asns(base, date_str, log)
    if not br_asns:
        log.error("br_asns vazio — abortando")
        return False

    prefix_origin = _init_prefix_origin(base, date_str, log)

    end_date   = datetime.date.fromisoformat(date_str)
    start_date = end_date - datetime.timedelta(days=_DAYS)
    start_ts   = int(datetime.datetime(start_date.year, start_date.month, start_date.day,
                                       tzinfo=datetime.timezone.utc).timestamp())

    urls = _update_urls(date_str)
    log.info("iniciando coleta de updates", date=date_str, collector=_COLLECTOR,
             files=len(urls), period=f"{start_date}→{end_date}")

    # Download paralelo com cache
    dl_results = _download_parallel(urls, base, date_str, log)
    files_ok      = sum(1 for ok in dl_results.values() if ok)
    files_missing = len(urls) - files_ok
    log.info("downloads concluídos", ok=files_ok, missing=files_missing)

    # Parse sequencial dos arquivos em cache
    accumulator = UpdateAccumulator(start_ts)
    t0 = time.monotonic()

    for idx, (ts_dt, url) in enumerate(urls, 1):
        if not dl_results.get(url):
            continue
        cache = _cache_path(base, date_str, url)
        try:
            data_bz2 = cache.read_bytes()
        except Exception as exc:
            log.debug("falha ao ler cache", file=cache.name, error=str(exc))
            continue

        _parse_updates(data_bz2, br_asns, prefix_origin, accumulator, log)

        if idx % 96 == 0:
            elapsed = time.monotonic() - t0
            dedup_pct = (1 - accumulator.counted / max(accumulator.raw_seen, 1)) * 100
            log.info("progresso", files_done=idx, total=len(urls),
                     raw_events=accumulator.raw_seen, counted=accumulator.counted,
                     dedup_pct=f"{dedup_pct:.1f}%",
                     elapsed_min=round(elapsed / 60, 1))

    elapsed = time.monotonic() - t0
    dedup_pct = (1 - accumulator.counted / max(accumulator.raw_seen, 1)) * 100
    log.info("coleta concluída", files_ok=files_ok, files_missing=files_missing,
             raw_events=accumulator.raw_seen, counted=accumulator.counted,
             dedup_pct=f"{dedup_pct:.1f}%",
             elapsed_min=round(elapsed / 60, 1))

    log.info("computando métricas de estabilidade")
    stability = _compute_stability(accumulator, start_date, br_asns)

    out = {
        "period": {
            "start":              start_date.isoformat(),
            "end":                end_date.isoformat(),
            "days":               _DAYS,
            "collector":          _COLLECTOR,
            "generated_at":       now_iso(),
            "files_processed":    files_ok,
            "files_missing":      files_missing,
            "raw_events_seen":    accumulator.raw_seen,
            "events_counted":     accumulator.counted,
            "dedup_rate_pct":     round(dedup_pct, 1),
            "br_events_v4":       stability["br_events_v4"],
            "br_events_v6":       stability["br_events_v6"],
        },
        "distribution":  stability["distribution"],
        "epppd_stats":   stability["epppd_stats"],
        "hourly_global": stability["hourly_global"],
        "as_stability":  stability["as_stability"],
    }

    out_path = norm / "bgp_stability.json.gz"
    write_json_gz(out_path, out)
    log.info("bgp_stability.json.gz gravado", path=str(out_path),
             asns=len(stability["as_stability"]))

    manifest = {
        "date":            date_str,
        "generated_at":    now_iso(),
        "collector":       _COLLECTOR,
        "files_processed": files_ok,
        "files_missing":   files_missing,
        "raw_events_seen": accumulator.raw_seen,
        "events_counted":  accumulator.counted,
        "dedup_rate_pct":  round(dedup_pct, 1),
        "asns_analyzed":   len(stability["as_stability"]),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    # Limpa cache do snapshot anterior apenas após gravação bem-sucedida
    _cleanup_old_cache(base, date_str, log)

    return True


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Coleta e análise de updates BGP do RouteViews para ASes BR"
    )
    p.add_argument("--date",      default=today_str(), help="Data do snapshot (YYYY-MM-DD)")
    p.add_argument("--force",     action="store_true", help="Reprocessa mesmo com manifesto existente")
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args(argv)

    log  = configure_logging(args.log_level)
    base = data_dir()

    ok = run(args.date, base, log, force=args.force)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
