# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cruzamento de quadro societário publicado: `grupos_societarios.json.gz`."""
from __future__ import annotations

from pathlib import Path

from core.common import normalized_path, published_path
from core.cpf import sem_socios_pessoa_fisica
from core.jsonio import carregar_json_gz, gravar_json_gz


def publicar_grupos_societarios(base: Path, date_str: str, log) -> dict:
    """
    Publica o cruzamento de quadro societário (`receita_socios` e `socios_grupos`).

    Lê grupos_societarios.json.gz (sources.socios_grupos.enrich) e apenas o publica —
    não há cruzamento adicional a fazer aqui, isso já foi feito no enrich.
    Saída: published/{date}/grupos_societarios.json.gz
    """
    norm_dir = normalized_path(base, date_str, "summary")
    path = norm_dir / "grupos_societarios.json.gz"
    if not path.exists():
        log.info("grupos_societarios not found, skipping build")
        return {}

    data = carregar_json_gz(path)
    if not data:
        return {}
    sem_socios_pessoa_fisica(data)      # normalizado pode trazer nomes de sócio pessoa física

    pub_dir = published_path(base, date_str)
    pub_dir.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(pub_dir / "grupos_societarios.json.gz", data)
    log.info("grupos_societarios.json.gz written",
             total_grupos=data.get("total_grupos", 0),
             total_cnpjs=len(data.get("by_cnpj", {})))

    return {
        "grupos_societarios_total": data.get("total_grupos", 0),
        "grupos_societarios_cnpjs": len(data.get("by_cnpj", {})),
    }
