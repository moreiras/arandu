# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""CAIDA AS-to-Organization: organização de cada ASN do Brasil, pela API pública do CAIDA AS Rank (GraphQL).

Por que a API e não o arquivo `publicdata.caida.org/datasets/as-organizations/`: o `robots.txt` daquele host tem `Disallow: /` para todo agente, e o
Arandurapé respeita o robots.txt. O AS Rank expõe o mesmo mapeamento (a organização do AS Rank vem do as2org do CAIDA) em `organization { orgId orgName
country members }`; a consulta é por lote de ASNs (≈ 60 requisições para ~9 mil ASNs do Brasil). A organização é **a do AS Rank**: pode juntar filiais sob uma "Parent"
(ex.: "Level 3 Parent, LLC") e usa um `orgId` próprio (hash), diferente do `org_id` WHOIS cru do arquivo trimestral.

Entrada:     data/normalized/{date}/summary/caida_asrank.json.gz (ASNs do Brasil já coletados por `caida_asrank`)
Normalizado: data/normalized/{date}/summary/caida_as2org.json.gz
             {snapshot_date, fetched_at, fonte, citacao, consultados, requisicoes, asns: {asn: {org_id, org_nome, org_pais, membros_total}}}
Licença:     dados públicos do CAIDA (Public AUA): citar "The CAIDA UCSD AS Rank, https://asrank.caida.org" e "The CAIDA AS Organizations Dataset".

Uso:
    python -m sources.caida_as2org.collect --date 2026-11-05
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

from core.common import configure_logging, data_dir, normalized_path, now_iso, read_json_gz, today_str, write_json_gz
from core.site import USER_AGENT

URL = "https://api.asrank.caida.org/v2/graphql"
HEADERS = {"User-Agent": USER_AGENT}
LOTE = 150
ESPERA_S = 1.0
MINIMO_COBERTURA = 0.9               # fração dos ASNs consultados que precisa voltar com organização
CITACAO = ("The CAIDA UCSD AS Rank, https://asrank.caida.org; The CAIDA AS Organizations Dataset, "
           "https://www.caida.org/catalog/datasets/as-organizations (organização do AS Rank, derivada do as2org)")
_CONSULTA = "{ asns(asns:%s) { edges { node { asn organization { orgId orgName country { iso } members { asns(first:1) { totalCount } } } } } } }"


def consulta(asns: list[str]) -> str:
    return _CONSULTA % json.dumps(asns)


def extrair(resposta: dict) -> dict[str, dict]:
    """`{asn: {org_id, org_nome, org_pais, membros_total}}` de uma resposta do GraphQL; ASN sem organização é omitido."""
    if resposta.get("errors"):
        raise RuntimeError(f"caida_as2org: erro do GraphQL: {str(resposta['errors'])[:200]}")
    out = {}
    for e in resposta["data"]["asns"]["edges"]:
        n = e["node"]
        o = n.get("organization") or {}
        if not o.get("orgId"):
            continue
        out[str(n["asn"])] = {"org_id": o["orgId"], "org_nome": (o.get("orgName") or "").strip() or None, "org_pais": (o.get("country") or {}).get("iso"),
                              "membros_total": ((o.get("members") or {}).get("asns") or {}).get("totalCount")}
    return out


def baixar_lote(client: httpx.Client, asns: list[str], tentativas: int = 3, espera_s: float = ESPERA_S) -> dict:
    for t in range(1, tentativas + 1):
        try:
            r = client.post(URL, json={"query": consulta(asns)})
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError):
            if t == tentativas:
                raise
            time.sleep(espera_s * 5 * t)
    raise AssertionError("inalcançável")


def run(date_str: str, base: Path, log, espera_s: float = ESPERA_S) -> dict:
    entrada = normalized_path(base, date_str, "summary") / "caida_asrank.json.gz"
    if not entrada.exists():
        raise RuntimeError("caida_as2org: caida_asrank.json.gz ausente (a lista de ASNs do Brasil vem do passo 1.5.6)")
    asns = sorted(read_json_gz(entrada)["asns"], key=int)
    achados: dict[str, dict] = {}
    requisicoes = 0
    with httpx.Client(timeout=120, follow_redirects=True, headers=HEADERS) as client:
        for i in range(0, len(asns), LOTE):
            achados.update(extrair(baixar_lote(client, asns[i:i + LOTE], espera_s=espera_s)))
            requisicoes += 1
            time.sleep(espera_s)
    if not asns or len(achados) < MINIMO_COBERTURA * len(asns):
        raise RuntimeError(f"caida_as2org: só {len(achados)} de {len(asns)} ASNs voltaram com organização (mínimo {MINIMO_COBERTURA:.0%})")
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / "caida_as2org.json.gz", {"snapshot_date": date_str, "fetched_at": now_iso(), "fonte": URL, "citacao": CITACAO,
                                                     "consultados": len(asns), "requisicoes": requisicoes, "asns": achados})
    log.info("caida_as2org written", asns=len(achados), consultados=len(asns), requisicoes=requisicoes)
    return {"asns": len(achados), "consultados": len(asns), "requisicoes": requisicoes}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="CAIDA AS-to-Organization (ASNs do Brasil, via AS Rank)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre refeita")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        run(a.date, data_dir(), log)
    except Exception:
        log.exception("falha na coleta de caida_as2org")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
