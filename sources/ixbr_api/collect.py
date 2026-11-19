# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Coletor da API do IX.br (dashboard.ix.br)

Para cada IXP configurado em config/ixps.yaml, busca a lista de membros via:

    https://dashboard.ix.br/generate_json?ixp={code}

Saída:
    data/raw/{date}/{ixp}/ixbr_members.json

O arquivo registra todos os ASNs membros cadastrados no IX.br para aquele IXP,
incluindo os que trocam tráfego apenas bilateral (sem usar Route Servers).
Esse número é sempre >= asn_direct coletado dos LGs, pois membros bilaterais
não aparecem na tabela BGP do Route Server mas estão registrados no dashboard.

Relação com outros módulos:
    - `lg_ixbr` (lg_ixbr): coleta o que os Route Servers veem (ASNs com sessão BGP ativa)
    - Este módulo: coleta o cadastro oficial do IX.br (inclui membros bilaterais)
    - `peeringdb_ixps` (peeringdb_ixps): coleta membros auto-declarados no PeeringDB

A diferença entre estes contadores é relevante: membros bilaterais são
"invisíveis" para análises de roteamento mas existem fisicamente no IXP.

Uso:
    python -m sources.ixbr_api.collect
    python -m sources.ixbr_api.collect --date 2026-06-08
    python -m sources.ixbr_api.collect --ixp sp rj ce
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

from core.common import (
    configure_logging,
    data_dir,
    load_ixps,
    now_iso,
    raw_path,
    today_str,
)

_IXBR_API = "https://dashboard.ix.br/generate_json?ixp={code}"
_TIMEOUT  = 30


def fetch_ixbr_members(code: str) -> dict:
    """Busca a lista de membros de um IXP via API do dashboard.ix.br.

    Args:
        code: Código do IXP (ex: "sp", "rj")

    Returns:
        Dict com "ixp", "fetched_at", "members_count", "members".
        Cada membro contém "asn" (int) e "name" (str).

    Raises:
        urllib.error.HTTPError: se a API retornar status de erro
        urllib.error.URLError:  se não conseguir conectar
    """
    url = _IXBR_API.format(code=code)
    with urllib.request.urlopen(url, timeout=_TIMEOUT) as r:
        data = json.loads(r.read())
    members = data.get("member_list", [])
    return {
        "ixp":           code,
        "fetched_at":    now_iso(),
        "members_count": len(members),
        "members": [
            {"asn": int(m["asnum"]), "name": m.get("name", "")}
            for m in members
            if "asnum" in m
        ],
    }


def collect_ixp(code: str, date_str: str, base: Path, log) -> dict:
    """Coleta membros de um IXP e salva em raw/{date}/{code}/ixbr_members.json.

    Returns:
        {"status": "ok", "members_count": int} ou {"status": "error", "error": str}
    """
    out_path = raw_path(base, date_str, code) / "ixbr_members.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = fetch_ixbr_members(code)
        out_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        log.info(
            "ixbr members fetched",
            ixp=code,
            members=result["members_count"],
            path=str(out_path),
        )
        return {"status": "ok", "members_count": result["members_count"]}
    except urllib.error.HTTPError as exc:
        log.warning("ixbr api http error", ixp=code, status=exc.code, url=exc.url)
        return {"status": "error", "error": str(exc)}
    except Exception as exc:
        log.warning("ixbr api error", ixp=code, error=str(exc))
        return {"status": "error", "error": str(exc)}


def run(
    date_str: str,
    base: Path,
    ixp_codes: list[str] | None = None,
    log=None,
) -> list[dict]:
    """Coleta membros de todos os IXPs (ou subconjunto filtrado).

    Args:
        date_str:  Data do snapshot (YYYY-MM-DD)
        base:      Diretório raiz dos dados
        ixp_codes: Lista de códigos; None = todos os IXPs do IX.br
        log:       Logger estruturado

    Returns:
        Lista de {"ixp": code, "status": ..., ...} por IXP processado.
    """
    all_ixps = load_ixps()
    if ixp_codes:
        all_ixps = [ix for ix in all_ixps if ix["code"] in ixp_codes]

    results = []
    for ixp in all_ixps:
        code = ixp["code"]
        log.info("fetching ixbr members", ixp=code)
        r = collect_ixp(code, date_str, base, log)
        results.append({"ixp": code, **r})

    ok = sum(1 for r in results if r["status"] == "ok")
    log.info("ixbr_api complete", ok=ok, total=len(results))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Coletor de membros IX.br via dashboard.ix.br/generate_json"
    )
    parser.add_argument("--date", default=today_str(),
                        help="Data do snapshot (YYYY-MM-DD); padrão: hoje")
    parser.add_argument("--ixp", nargs="+", metavar="CODE",
                        help="Coleta apenas estes IXPs (ex: --ixp sp rj)")
    args = parser.parse_args(argv)

    log  = configure_logging()
    base = data_dir()

    run(date_str=args.date, base=base, ixp_codes=args.ixp, log=log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
