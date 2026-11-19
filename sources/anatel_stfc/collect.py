# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`anatel_stfc` — Coleta de outorgas STFC (Serviço Telefônico Fixo Comutado) da Anatel.

Fonte: https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/
       prestadoras_servicos_telecomunicacoes.zip

Serviço filtrado: código 171 — Serviço Telefônico Fixo Comutado

Mesmo arquivo-fonte de sources/anatel_scm/collect.py (`anatel_scm`) e sources/anatel_smp/collect.py
(`anatel_smp`), só muda o código de serviço filtrado.

Nota: o mesmo arquivo também lista códigos 175/176 ("STFC/RADIOTELEFONICO —
ESTACOES TERRESTRES/TERRENAS"), que são modalidades técnicas específicas
(radioenlace/satélite) do STFC, não o serviço telefônico fixo comutado geral.
Ficam de fora do filtro — se algum dia forem necessários, tratar como extensão
separada.

Raw:         data/raw/{date}/summary/anatel-outorgas-{date}.csv.gz  (compartilhado pelos 4 serviços; ver sources/anatel_outorgas)
Normalizado: data/normalized/{date}/summary/anatel_stfc.json.gz

Campos extraídos:
  cnpj, razao_social, nome_fantasia, data_outorga,
  cep, logradouro, numero, complemento, bairro, municipio, uf,
  codigo_ibge, telefone, email, situacao

Uso:
    python -m sources.anatel_stfc.collect
    python -m sources.anatel_stfc.collect --date 2026-06-24
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.common import configure_logging, data_dir, today_str
from sources.anatel_outorgas.download import ANATEL_URL  # noqa: F401 — o teste e o catálogo citam a URL por aqui
from sources.anatel_outorgas.servicos import SERVICOS, _clean_cnpj, parse_csv, rodar  # noqa: F401

SERVICO = SERVICOS["stfc"]


def _parse_csv(content: bytes) -> list[dict]:
    return parse_csv(content, SERVICO)


def run(date_str: str, base: Path, log) -> dict:
    return rodar(SERVICO, date_str, base, log)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="`anatel_stfc` — coleta outorgas STFC da Anatel")
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
