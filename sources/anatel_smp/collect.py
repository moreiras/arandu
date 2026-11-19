# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`anatel_smp` — Coleta de outorgas SMP (Serviço Móvel Pessoal) da Anatel.

Fonte: https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/
       prestadoras_servicos_telecomunicacoes.zip

Serviço filtrado: código 010 — Serviço Móvel Pessoal

Mesmo arquivo-fonte de sources/anatel_scm/collect.py (`anatel_scm`), só muda o código de serviço
filtrado. O universo é pequeno (~30 CNPJs: as grandes operadoras móveis mais
MVNOs/M2M), bem menor que o de SCM.

M13c — Rede virtual (MVNA/MVNO): cruza com o dataset
"Competição — Empresas Credenciadas de Rede Virtual" (mesma Anatel, mesmo assunto,
zip diferente: contratos.zip), que lista credenciamentos vigentes de operadoras
virtuais (MVNO puro, sem outorga SMP própria) a uma Prestadora Origem (host, que
detém a outorga/rede). Cada outorga SMP do host ganha `rede_virtual.papel = "host"`;
cada credenciada ganha `rede_virtual.papel = "credenciada"` — se a credenciada não
tiver outorga SMP própria (caso comum: MVNO puro opera só via contrato, sem
outorga), um registro sintético é adicionado para ela não ficar invisível no
universo SMP. Resolução Anatel 777/2025 também prevê a "Autorizada de Rede
Virtual" (MVNA — outorga própria que compartilha rede com um host), mas não há
dataset aberto que identifique isso distintamente dentro da outorga SMP geral;
fica de fora por falta de fonte estruturada.

Fonte da rede virtual: https://www.anatel.gov.br/dadosabertos/paineis_de_dados/
                        competicao/contratos.zip (arquivo contratos_mvno.csv)

Raw:         data/raw/{date}/summary/anatel-outorgas-{date}.csv.gz  (compartilhado pelos 4 serviços; ver sources/anatel_outorgas)
Normalizado: data/normalized/{date}/summary/anatel_smp.json.gz

Campos extraídos:
  cnpj, razao_social, nome_fantasia, data_outorga,
  cep, logradouro, numero, complemento, bairro, municipio, uf,
  codigo_ibge, telefone, email, situacao, rede_virtual

Uso:
    python -m sources.anatel_smp.collect
    python -m sources.anatel_smp.collect --date 2026-06-24
"""

from __future__ import annotations

import argparse
import sys
import csv
import io
import zipfile
from pathlib import Path

import httpx

from core.common import configure_logging, data_dir, today_str
from sources.anatel_outorgas.download import ANATEL_URL  # noqa: F401 — o teste e o catálogo citam a URL por aqui
from sources.anatel_outorgas.servicos import SERVICOS, _clean_cnpj, parse_csv, rodar  # noqa: F401

ANATEL_REDE_VIRTUAL_URL = (
    "https://www.anatel.gov.br/dadosabertos/paineis_de_dados/competicao/contratos.zip"
)


def _fetch_rede_virtual_contracts(log) -> list[dict]:
    """Baixa contratos.zip e devolve os credenciamentos de rede virtual VIGENTES.

    Cada item: {credenciada_cnpj, credenciada_nome, prestadora_origem_cnpj,
    prestadora_origem_nome}. Lista vazia (não exceção) em qualquer falha — é um
    enriquecimento secundário, não deve derrubar a coleta principal de SMP.
    """
    try:
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            resp = client.get(ANATEL_REDE_VIRTUAL_URL)
            resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            csv_bytes = zf.read("contratos_mvno.csv")
    except Exception:
        log.exception("failed to fetch rede virtual (MVNO) contracts, skipping enrichment")
        return []

    text = csv_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    contracts: dict[str, dict] = {}  # credenciada_cnpj -> contrato (último vigente vence)
    for row in reader:
        if (row.get("VIGENCIA_DATA_FIM") or "").strip().upper() != "VIGENTE":
            continue
        credenciada_cnpj = _clean_cnpj(row.get("CREDENCIADA_CNPJ", ""))
        origem_cnpj = _clean_cnpj(row.get("PRESTADORA_ORIGEM_CNPJ", ""))
        if not credenciada_cnpj or not origem_cnpj:
            continue
        contracts[credenciada_cnpj] = {
            "credenciada_cnpj": credenciada_cnpj,
            "credenciada_nome": (row.get("CREDENCIADA") or "").strip(),
            "prestadora_origem_cnpj": origem_cnpj,
            "prestadora_origem_nome": (row.get("PRESTADORA_ORIGEM") or "").strip(),
        }
    return list(contracts.values())


def _apply_rede_virtual(records: list[dict], log) -> list[dict]:
    """Marca outorgas SMP com `rede_virtual` (papel host/credenciada) e adiciona
    registros sintéticos para credenciadas sem outorga SMP própria (caso comum
    do MVNO puro)."""
    contracts = _fetch_rede_virtual_contracts(log)
    if not contracts:
        return records

    by_cnpj_existing = {rec["cnpj"] for rec in records}
    host_credenciadas_count: dict[str, int] = {}
    for c in contracts:
        host_credenciadas_count[c["prestadora_origem_cnpj"]] = (
            host_credenciadas_count.get(c["prestadora_origem_cnpj"], 0) + 1
        )

    credenciada_by_cnpj = {c["credenciada_cnpj"]: c for c in contracts}

    for rec in records:
        cnpj = rec["cnpj"]
        if cnpj in credenciada_by_cnpj:
            c = credenciada_by_cnpj[cnpj]
            rec["rede_virtual"] = {
                "papel": "credenciada",
                "prestadora_origem_cnpj": c["prestadora_origem_cnpj"],
                "prestadora_origem_nome": c["prestadora_origem_nome"],
            }
        elif cnpj in host_credenciadas_count:
            rec["rede_virtual"] = {
                "papel": "host",
                "credenciadas_count": host_credenciadas_count[cnpj],
            }

    added = 0
    for cnpj, c in credenciada_by_cnpj.items():
        if cnpj in by_cnpj_existing:
            continue
        records.append({
            "cnpj": cnpj,
            "razao_social": c["credenciada_nome"],
            "nome_fantasia": "",
            "data_outorga": "",
            "situacao": "Credenciada de Rede Virtual (sem outorga SMP própria)",
            "rede_virtual": {
                "papel": "credenciada",
                "prestadora_origem_cnpj": c["prestadora_origem_cnpj"],
                "prestadora_origem_nome": c["prestadora_origem_nome"],
            },
        })
        added += 1

    log.info(
        "rede virtual (MVNO) merged",
        contratos_vigentes=len(contracts),
        hosts=len(host_credenciadas_count),
        credenciadas_sem_outorga_propria=added,
    )
    return records


SERVICO = SERVICOS["smp"]


def _parse_csv(content: bytes) -> list[dict]:
    return parse_csv(content, SERVICO)


def run(date_str: str, base: Path, log) -> dict:
    return rodar(SERVICO, date_str, base, log)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="`anatel_smp` — coleta outorgas SMP da Anatel")
    parser.add_argument("--date", default=today_str(),
                        help="Data do snapshot (YYYY-MM-DD); padrão: hoje")
    args = parser.parse_args(argv)

    log = configure_logging()
    base = data_dir()

    try:
        run(date_str=args.date, base=base, log=log)
    except Exception as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status is not None:
            log.error("http error", status=status, url=str(getattr(getattr(exc, "request", None), "url", "")))
        else:
            log.exception("unexpected error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
