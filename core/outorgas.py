# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Registro dos serviços de outorga da Anatel: a única lista de SCM, SMP, STFC e SeAC.

Coleta (`sources/anatel_outorgas`), geocodificação, publicação (`products/outorgas`), leitura na API (`api/outorgas_store`) e os
manifestos derivam daqui. **Um serviço novo começa por uma entrada em `SERVICOS`** (mais as fontes/etapas no catálogo).
Sem dependências pesadas: a API importa este módulo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class Servico:
    """O que distingue um serviço de outorga dos demais no CSV da Anatel."""
    sigla: str                                   # "scm" → anatel_scm.json.gz, scm.json.gz
    chave: str                                   # nome da lista no JSON ("scms"); o mapa é maps/<chave>.geojson
    codigo: str                                  # código do serviço sem zeros à esquerda ("45")
    reconhece_nome: Callable[[str], bool]        # recebe o texto em minúsculas; para valores sem código ("Multimídia")
    depois_ref: Optional[str] = None             # "modulo:funcao" — enriquecimento secundário (ex.: rede virtual do SMP)

    @property
    def mapa(self) -> str:
        return f"{self.chave}.geojson"

    def pertence(self, valor: str) -> bool:
        m = re.match(r"\s*0*(\d+)", valor)
        if m and m.group(1) == self.codigo:
            return True
        return self.reconhece_nome(valor.lower())


# Marca do registro sintético que `sources.anatel_smp.collect._apply_rede_virtual` cria para a credenciada de rede virtual sem
# outorga SMP própria: ele materializa o credenciamento (RGST, Res. Anatel 777/2025), não é outorga.
SEM_OUTORGA_PROPRIA = "sem outorga smp própria"


def eh_outorga(rec: dict) -> bool:
    """O registro é outorga do serviço (e não o registro sintético de credenciamento de rede virtual)."""
    return SEM_OUTORGA_PROPRIA not in (rec.get("situacao") or "").lower()


SERVICOS: dict[str, Servico] = {s.sigla: s for s in (
    Servico("scm", "scms", "45", lambda n: "multim" in n),
    Servico("smp", "smps", "10", lambda n: "movel pessoal" in n and "satelite" not in n and "especializado" not in n,
            depois_ref="sources.anatel_smp.collect:_apply_rede_virtual"),
    Servico("stfc", "stfcs", "171", lambda n: "telefonico fixo comutado" in n and "radiotelefonico" not in n),
    Servico("seac", "seacs", "750", lambda n: "acesso condicionado" in n),
)}
