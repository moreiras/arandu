# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Sanidade de coleta: `checks` e `coleta_ok` no manifesto do snapshot.

Uma coleta pode "terminar com sucesso" e ainda assim estar ruim (rate limit que devolve lista vazia, fonte
que mudou de formato, LG fora do ar). Estas verificações comparam o snapshot com o anterior e com limites
fixos, e marcam o snapshot como `parcial` quando algo foge — sem bloquear a publicação.

Regras (plano):
  ptt_coletados      PTTs coletados = PTTs configurados
  asns_br            nº de ASNs BR dentro de ±1% do snapshot anterior
  prefixos_v4/v6     prefixos alocados ao BR (Registro.br) dentro de ±3% do anterior
  vrps               VRPs do RPKI dentro de ±5% do anterior (só existe depois da coleta de RPKI → `saude_asn`)
  pdb_registrados    ASNs BR cadastrados no PeeringDB > 20% dos ASNs BR

Estados de cada check: `ok`, `falha`, `sem_base` (não há snapshot anterior) e `pendente` (dado ainda não
coletado quando o manifesto foi escrito; é completado em `refresh_manifest`).
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Optional

from core.chaves_registro import com_os_dois_nomes

ASNS_BR_TOL = 0.01
PREFIXOS_TOL = 0.03
VRPS_TOL = 0.05
PDB_MIN_PCT = 20.0
ASN_NAMES_TOL = 0.03          # variação do nº de nomes entre coletas
ASN_NAMES_HIFEN_PTS = 15.0    # queda/alta máxima, em pontos percentuais, da fração de nomes no formato 'HANDLE - Descrição'


def _variacao(atual: Optional[float], anterior: Optional[float], tol: float, nome: str) -> dict:
    if atual is None:
        return {"status": "pendente", "motivo": f"{nome} ainda não coletado"}
    if not anterior:
        return {"status": "sem_base", "valor": atual}
    delta = (atual - anterior) / anterior
    return {"status": "ok" if abs(delta) <= tol else "falha", "valor": atual, "anterior": anterior,
            "variacao_pct": round(delta * 100, 2), "limite_pct": round(tol * 100, 2)}


def asn_names_stats(names: Optional[dict]) -> Optional[dict]:
    """{total, pct_hifen}: quantos nomes e que % está no formato 'HANDLE - Descrição, CC' (68% nos dados normais)."""
    if not isinstance(names, dict) or not names:
        return None
    return {"total": len(names), "pct_hifen": round(100 * sum(1 for v in names.values() if " - " in str(v)) / len(names), 1)}


def _check_asn_names(atual: Optional[dict], anterior: Optional[dict]) -> dict:
    """Detecta o dia em que o RIPE serviu o asn.txt em outro formato (2026-10-11: 32% com ' - ' contra 68%)."""
    if atual is None:
        return {"status": "pendente", "motivo": "asn_names ausente"}
    if anterior is None:
        return {"status": "sem_base", **atual}
    delta = (atual["total"] - anterior["total"]) / anterior["total"]
    pts = atual["pct_hifen"] - anterior["pct_hifen"]
    ok = abs(delta) <= ASN_NAMES_TOL and abs(pts) <= ASN_NAMES_HIFEN_PTS
    return {"status": "ok" if ok else "falha", **atual, "anterior_total": anterior["total"],
            "variacao_pct": round(delta * 100, 2), "anterior_pct_hifen": anterior["pct_hifen"],
            "variacao_pontos_hifen": round(pts, 1), "limite_pct": round(ASN_NAMES_TOL * 100, 2),
            "limite_pontos_hifen": ASN_NAMES_HIFEN_PTS}


def evaluate(manifest: dict, previous: Optional[dict], vrps: Optional[int], vrps_prev: Optional[int],
             pdb_registered: Optional[int], names: Optional[dict] = None, names_prev: Optional[dict] = None) -> dict:
    """Devolve `{"checks": {...}, "coleta_ok": bool, "coleta": "completa"|"parcial"|"pendente"}`."""
    prev = com_os_dois_nomes(previous or {})          # manifesto anterior pode ter só os nomes `m3_`
    manifest = com_os_dois_nomes(manifest)
    conf, coll = set(manifest.get("ixps_configured") or []), set(manifest.get("ixps_collected") or [])
    faltam = sorted(conf - coll)
    checks = {
        "ptt_coletados": {"status": "ok" if not faltam else "falha", "configurados": len(conf),
                          "coletados": len(coll & conf), **({"faltam": faltam} if faltam else {})},
        "asns_br": _variacao(manifest.get("total_asns_br"), prev.get("total_asns_br"), ASNS_BR_TOL, "asns_br"),
        "prefixos_v4": _variacao(manifest.get("registro_br_prefixes_v4"), prev.get("registro_br_prefixes_v4"), PREFIXOS_TOL, "prefixos_v4"),
        "prefixos_v6": _variacao(manifest.get("registro_br_prefixes_v6"), prev.get("registro_br_prefixes_v6"), PREFIXOS_TOL, "prefixos_v6"),
        "vrps": _variacao(vrps, vrps_prev, VRPS_TOL, "vrps"),
    }
    if names is not None:                       # sem o arquivo (snapshots antigos, testes) o check não existe
        checks["asn_names"] = _check_asn_names(names, names_prev)
    total = manifest.get("total_asns_br") or 0
    if pdb_registered is None or not total:
        checks["pdb_registrados"] = {"status": "pendente", "motivo": "peeringdb_networks ausente"}
    else:
        pct = round(pdb_registered / total * 100, 1)
        checks["pdb_registrados"] = {"status": "ok" if pct > PDB_MIN_PCT else "falha", "valor": pdb_registered,
                                     "pct_dos_asns_br": pct, "limite_pct": PDB_MIN_PCT}
    estados = [c["status"] for c in checks.values()]
    coleta = "parcial" if "falha" in estados else ("pendente" if "pendente" in estados else "completa")
    return {"checks": checks, "coleta_ok": "falha" not in estados, "coleta": coleta}


# ── leitura do que existe em disco ─────────────────────────────────────────

def _read_json(path: Path):
    try:
        if path.name.endswith(".gz"):
            with gzip.open(path, "rt", encoding="utf-8") as f:
                return json.load(f)
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def previous_snapshot(base: Path, date_str: str) -> Optional[str]:
    pub = base / "published"
    if not pub.exists():
        return None
    cands = sorted(p.name for p in pub.iterdir()
                   if p.is_dir() and p.name < date_str and (p / "manifest.json").exists()
                   and len(p.name) == 10 and p.name[4] == "-")
    return cands[-1] if cands else None


def _count_vrps(base: Path, date_str: str) -> Optional[int]:
    data = _read_json(base / "published" / date_str / "rpki" / "vrp_list.json.gz")
    return len(data) if isinstance(data, list) else None


def _count_pdb(base: Path, date_str: str) -> Optional[int]:
    data = _read_json(base / "normalized" / date_str / "summary" / "peeringdb_networks.json.gz")
    return len(data.get("networks", {})) if isinstance(data, dict) else None


def _names(base: Path, date_str: str) -> Optional[dict]:
    return asn_names_stats(_read_json(base / "normalized" / date_str / "summary" / "asn_names.json.gz"))


def checks_for(base: Path, date_str: str, manifest: dict) -> dict:
    prev_date = previous_snapshot(base, date_str)
    prev = _read_json(base / "published" / prev_date / "manifest.json") if prev_date else None
    out = evaluate(manifest, prev, _count_vrps(base, date_str),
                   _count_vrps(base, prev_date) if prev_date else None, _count_pdb(base, date_str),
                   _names(base, date_str), _names(base, prev_date) if prev_date else None)
    out["comparado_com"] = prev_date
    return out


def _acrescentar_fontes(base: Path, date_str: str, manifest: dict, log=None) -> None:
    """`layout_version` e `sources[]`: aditivos; erro aqui nunca impede a publicação."""
    try:
        from core.catalog.loader import load_catalog
        from core.store import LAYOUT_VERSION, compor_fontes

        manifest["layout_version"] = LAYOUT_VERSION
        manifest["sources"] = compor_fontes(load_catalog(), base, date_str)
    except Exception as exc:  # noqa: BLE001
        if log:
            log.warning("sources[] do manifesto não gerado", erro=str(exc))


def _acrescentar_regras(manifest: dict) -> None:
    """`rules_version` e `rules` (id → versão) das regras de alerta em vigor: séries de alertas só se comparam com a mesma versão."""
    from products.alerts.registro import regras_publicadas, rules_version

    manifest["rules_version"] = rules_version()
    manifest["rules"] = regras_publicadas()


def refresh_manifest(base: Path, date_str: str, log=None, checksums: bool = False) -> Optional[dict]:
    """Recalcula `checks`/`coleta_ok` no manifesto já escrito (depois do RPKI, o check de VRPs deixa de
    estar pendente). Reescreve de forma atômica; os demais campos não mudam. Com `checksums=True` (fim do pipeline, depois do
    compose, do BGP e da estabilidade) recalcula os checksums de TODOS os arquivos publicados."""
    path = base / "published" / date_str / "manifest.json"
    manifest = _read_json(path)
    if not isinstance(manifest, dict):
        return None
    manifest.update(checks_for(base, date_str, manifest))
    _acrescentar_fontes(base, date_str, manifest, log)
    _acrescentar_regras(manifest)
    if checksums:
        from core.integridade import calcular_checksums

        manifest["checksums"] = calcular_checksums(path.parent)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    try:                        # o detalhe de /snapshots/{date} carrega os metadados do manifesto: mantém em dia
        from api import snapshot_detail

        snapshot_detail.refresh_manifest_meta(base, date_str)
    except Exception:  # noqa: BLE001
        pass
    if log:
        log.info("manifest checks", coleta=manifest["coleta"], coleta_ok=manifest["coleta_ok"],
                 falhas=[k for k, v in manifest["checks"].items() if v["status"] == "falha"])
    return manifest
