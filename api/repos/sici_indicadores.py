# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Indicadores do SICI e outorgas sem declaração publicados: `sici_indicadores.json.gz` e `sem_declaracao_sici.json.gz`."""
from __future__ import annotations

from typing import Optional

from api.repos.base import ArtifactRepo


#: nome do arquivo de `sem_declaracao_sici` nos snapshots publicados antes da renomeação (D12); alias de leitura
ARQUIVO_ANTIGO = "omissao_sici.json.gz"


class SiciIndicadoresRepo(ArtifactRepo):
    def indicadores(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "sici_indicadores.json.gz")

    def mercado_grupos(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "mercado_grupos.json.gz")

    def sem_declaracao(self, date_str: str) -> Optional[dict]:
        # snapshots publicados antes de 2026-11 (D12) gravaram o mesmo documento com o nome antigo; são imutáveis, então a leitura aceita os dois
        return self.ler(date_str, "sem_declaracao_sici.json.gz") or self.ler(date_str, ARQUIVO_ANTIGO)

    def serie_municipio(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "sici_serie_municipio.json.gz")
