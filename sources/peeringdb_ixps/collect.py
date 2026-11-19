# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`peeringdb_ixps` — Coleta de listas de membros de IXPs via PeeringDB.

Consulta o endpoint /api/netixlan para dois conjuntos de IXPs:
  - IXPs externos (18 IXPs globais relevantes para redes BR)
  - IXPs do IX.br (40 IXPs — para identificar membros sem cadastro PDB)

Fonte:       https://www.peeringdb.com/api/netixlan?ixlan_id={id}
Raw:         data/raw/{date}/summary/peeringdb-ixps-{date}.json
Normalizado: data/normalized/{date}/summary/peeringdb_ixps.json.gz

Uso:
    python -m sources.peeringdb_ixps.collect
    python -m sources.peeringdb_ixps.collect --date 2026-06-09
    python -m sources.peeringdb_ixps.collect --date 2026-06-09 --do-bruto   # só refaz o normalizado do bruto salvo

Variável de ambiente opcional:
    PEERINGDB_API_KEY  — aumenta o limite de rate de 250 para 1000 req/h
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import httpx

from core.common import (
    configure_logging,
    data_dir,
    load_peeringdb_ixps_config,
    now_iso,
    normalized_path,
    raw_path,
    today_str,
    write_json_gz,
)
from core.site import USER_AGENT

PDB_BASE = "https://www.peeringdb.com/api"
_RETRY_WAIT = 65  # segundos após 429 sem Retry-After
_NET_WAIT = 15    # segundos × nº da tentativa após timeout/erro de rede
_MAX_ATTEMPTS = 4


def _make_client() -> httpx.Client:
    api_key = os.environ.get("PEERINGDB_API_KEY", "")
    headers = {"User-Agent": USER_AGENT}
    if api_key:
        headers["Authorization"] = f"Api-Key {api_key}"
    return httpx.Client(headers=headers, timeout=30, follow_redirects=True)


class RateLimitedError(RuntimeError):
    """O PeeringDB continuou limitando (429) ou sem responder depois de todas as retentativas."""


def _fetch_netixlan(client: httpx.Client, ixlan_id: int, log, attempts: int = _MAX_ATTEMPTS) -> list[dict]:
    """Retorna a lista de membros de um ixlan. Retenta em 429 e em erro de rede/timeout; esgotadas as tentativas, FALHA.

    Sem isso, um timeout derrubaria a coleta (e um pipeline de horas) e dois 429 devolveriam `[]` em silêncio (IXP sem
    membros no snapshot)."""
    url = f"{PDB_BASE}/netixlan"
    params = {"ixlan_id": ixlan_id, "depth": 0, "status": "ok"}
    ultimo = "429"
    for attempt in range(attempts):
        try:
            resp = client.get(url, params=params)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            ultimo = type(exc).__name__
            wait = _NET_WAIT * (attempt + 1)
            log.warning("erro de rede", ixlan_id=ixlan_id, erro=ultimo, wait=wait, attempt=attempt + 1, of=attempts)
            time.sleep(wait)
            continue
        if resp.status_code == 429:
            ultimo = "429"
            wait = int(resp.headers.get("Retry-After", _RETRY_WAIT))
            log.warning("rate limited", ixlan_id=ixlan_id, wait=wait, attempt=attempt + 1, of=attempts)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json().get("data", [])
    raise RateLimitedError(f"PeeringDB sem resposta útil em {attempts} tentativas (ixlan {ixlan_id}; último: {ultimo})")


def _collect_ixp(client: httpx.Client, ixp: dict, log) -> dict:
    """Coleta membros de um IXP via /api/netixlan?ixlan_id=.

    Returns:
        {"member_count": int, "members": [{"asn": int, "speed": int}]}
        Membros ordenados por ASN. Sem nome: o `name` do netixlan é o nome do PTT, não o da rede; o nome
        do membro vem de `asn_names` na publicação (`products.ixp_docs`).
    """
    ixlan_id = ixp["pdb_ix_id"]
    raw_members = _fetch_netixlan(client, ixlan_id, log)
    members = []
    for m in raw_members:
        asn = m.get("asn")
        if not asn:
            continue
        members.append({
            "asn":   int(asn),
            "speed": m.get("speed", 0),
        })
    members.sort(key=lambda x: x["asn"])
    log.info("fetched", ixp=ixp.get("code", ixlan_id), members=len(members))
    return {"member_count": len(members), "members": members}


def normalizar(raw_out: dict, cfg: dict, date_str: str) -> dict:
    """Normalizado a partir do bruto (também usado por `--do-bruto`, sem rede).

    Três seções:
      external_ixps — {code: {name, city, country, pdb_ix_id, member_count, members}}
      ixbr_ixps     — {code: {pdb_ix_id, member_count, asns, portas}}; `portas` = [[asn, velocidade em Mbps], ...], uma por porta (netixlan),
                      para a coluna "Porta (PeeringDB)" dos participantes
      per_asn       — {str(asn): {external: [...], ixbr: [...]}} índice invertido por ASN
    """
    external_out: dict = {}
    ixbr_out: dict = {}
    per_asn: dict[int, dict] = {}  # asn → {external: [...], ixbr: [...]}
    for ixp in cfg["external"]:
        code = ixp["code"]
        result = (raw_out.get("external") or {}).get(code)
        if result is None:
            continue
        membros = [{"asn": m["asn"], "speed": m.get("speed", 0)} for m in result["members"]]      # bruto antigo pode trazer o nome do PTT
        external_out[code] = {"name": ixp["name"], "city": ixp.get("city", ""), "country": ixp.get("country", ""), "pdb_ix_id": ixp["pdb_ix_id"],
                              **result, "members": membros}
        for m in result["members"]:
            per_asn.setdefault(m["asn"], {"external": [], "ixbr": []})["external"].append(code)
    for ixp in cfg["ixbr"]:
        code = ixp["code"]
        result = (raw_out.get("ixbr") or {}).get(code)
        if result is None:
            continue
        ixbr_out[code] = {
            "pdb_ix_id":    ixp["pdb_ix_id"],
            "member_count": result["member_count"],
            "asns":   [m["asn"] for m in result["members"]],
            "portas": [[m["asn"], m.get("speed") or 0] for m in result["members"]],
        }
        for m in result["members"]:
            per_asn.setdefault(m["asn"], {"external": [], "ixbr": []})["ixbr"].append(code)
    return {
        "snapshot_date": date_str,
        "generated_at":  now_iso(),
        "external_ixps": external_out,
        "ixbr_ixps":     ixbr_out,
        "per_asn": {str(asn): data for asn, data in sorted(per_asn.items())},
    }


def run(date_str: str, base, log) -> dict:
    """Coleta membros de todos os IXPs externos e do IX.br via PeeringDB.

    Gera dois artefatos:
      raw: peeringdb-ixps-{date}.json — resposta bruta por IXP
      normalizado: peeringdb_ixps.json.gz (ver `normalizar`)

    Returns:
        O dict normalizado gravado em disco.
    """
    raw_dir  = raw_path(base, date_str, "summary")
    norm_dir = normalized_path(base, date_str, "summary")
    raw_dir.mkdir(parents=True, exist_ok=True)
    norm_dir.mkdir(parents=True, exist_ok=True)

    cfg = load_peeringdb_ixps_config()
    raw_out: dict = {"date": date_str, "external": {}, "ixbr": {}}

    with _make_client() as client:
        for ixp in cfg["external"]:
            raw_out["external"][ixp["code"]] = _collect_ixp(client, ixp, log)
            time.sleep(0.4)
        for ixp in cfg["ixbr"]:
            raw_out["ixbr"][ixp["code"]] = _collect_ixp(client, ixp, log)
            time.sleep(0.4)

    raw_file = raw_dir / f"peeringdb-ixps-{date_str}.json"
    raw_file.write_text(json.dumps(raw_out, ensure_ascii=False), encoding="utf-8")
    log.info("raw saved", path=str(raw_file))
    return _gravar_normalizado(raw_out, cfg, date_str, norm_dir, log)


def _gravar_normalizado(raw_out: dict, cfg: dict, date_str: str, norm_dir, log) -> dict:
    normalized = normalizar(raw_out, cfg, date_str)
    write_json_gz(norm_dir / "peeringdb_ixps.json.gz", normalized)
    log.info(
        "peeringdb_ixps done",
        external_ixps=len(normalized["external_ixps"]),
        ixbr_ixps=len(normalized["ixbr_ixps"]),
        external_total_members=sum(v["member_count"] for v in normalized["external_ixps"].values()),
        ixbr_total_members=sum(v["member_count"] for v in normalized["ixbr_ixps"].values()),
        unique_asns=len(normalized["per_asn"]),
    )
    return normalized


def do_bruto(date_str: str, base, log) -> dict:
    """Refaz o normalizado a partir do bruto já salvo (sem rede): o bruto é imutável e guarda a velocidade das portas do IX.br."""
    raw_file = raw_path(base, date_str, "summary") / f"peeringdb-ixps-{date_str}.json"
    raw_out = json.loads(raw_file.read_text(encoding="utf-8"))
    norm_dir = normalized_path(base, date_str, "summary")
    norm_dir.mkdir(parents=True, exist_ok=True)
    return _gravar_normalizado(raw_out, load_peeringdb_ixps_config(), date_str, norm_dir, log)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="`peeringdb_ixps` — coleta listas de membros de IXPs via PeeringDB"
    )
    parser.add_argument("--date", default=today_str(),
                        help="Data do snapshot (YYYY-MM-DD); padrão: hoje")
    parser.add_argument("--do-bruto", action="store_true",
                        help="Refaz só o normalizado a partir do bruto já salvo da data (sem rede)")
    args = parser.parse_args(argv)

    log = configure_logging()
    base = data_dir()

    try:
        if args.do_bruto:
            do_bruto(date_str=args.date, base=base, log=log)
        else:
            run(date_str=args.date, base=base, log=log)
    except httpx.HTTPStatusError as exc:
        log.error("http error", status=exc.response.status_code, url=str(exc.request.url))
        return 1
    except httpx.RequestError as exc:
        log.error("connection error", error=str(exc))
        return 1
    except Exception:
        log.exception("unexpected error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
