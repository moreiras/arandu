# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Sociedade anônima no agrupamento societário (decisão P8, opção A): o quadro da Receita de S.A. não traz acionistas, então não infere grupo.

Fato medido em 2026-11-25 sobre o snapshot 2026-11-22: das 161 S.A. do universo de outorgas, 161 tinham quadro só com gestão (diretoria e conselho),
nenhuma com sócio de participação. Ligar S.A. por diretor ou conselheiro em comum reintroduziria o erro que a regra "só participação liga" corrigiu.

Critério: natureza jurídica da Receita (tabela de naturezas jurídicas do CNPJ, campo `nat` por raiz em `receita_cnpj.json.gz`). Lista adotada:
  * 2046, Sociedade Anônima Aberta;
  * 2054, Sociedade Anônima Fechada.
As descrições de 2046 e 2054 foram conferidas só contra a tabela `naturezas` presente no dado `receita_cnpj` de 2026-11 (a tabela oficial de naturezas não foi
reconferida em 2026-11-25: o site da Concla/IBGE bloqueou a consulta automática).

Pendências registradas: 2097 (Sociedade Empresária em Comandita por Ações) fica fora da lista até o mantenedor decidir; não há caso no universo de outorgas
(medição de 2026-11-25). Sociedade de economia mista e empresa pública (outros códigos) não foram medidas e também ficam fora.

Efeito: o quadro da S.A. não gera aresta (nem por participação, porque o quadro de S.A. traz gestão). A ligação que nasce do quadro de OUTRA empresa em que a S.A.
figura como sócia PJ com participação continua valendo.
"""
from __future__ import annotations

NATUREZAS_SA: dict[str, str] = {
    "2046": "Sociedade Anônima Aberta",
    "2054": "Sociedade Anônima Fechada",
}
PENDENTES: dict[str, str] = {"2097": "Sociedade Empresária em Comandita por Ações (sem caso no universo; decisão do mantenedor pendente)"}
MOTIVO = "sa_quadro_sem_acionistas"
ROTULO = "grupo não inferível pelo quadro societário (S.A.)"
COMO_LER = ("O quadro da Receita de uma sociedade anônima traz diretoria e conselho, não acionistas. O agrupamento por quadro societário não alcança esta empresa: "
            "ela pode pertencer a um grupo que esta página não mostra. A ligação que vem do quadro de outra empresa em que ela é sócia continua valendo.")


def marca_do_cnpj(row: dict | None) -> dict:
    """Campos de `grupo_inferivel` de uma linha de `by_cnpj` de `grupos_societarios` (vazio se a empresa não é S.A.); para a API e o MCP."""
    if (row or {}).get("grupo_inferivel") is False:
        return {"grupo_inferivel": False, "grupo_inferivel_motivo": row.get("motivo") or MOTIVO, "grupo_inferivel_rotulo": ROTULO, "como_ler": COMO_LER}
    return {}


def e_sociedade_anonima(natureza: object) -> bool:
    return str(natureza or "").strip() in NATUREZAS_SA


def regra_publicada() -> dict:
    return {"motivo": MOTIVO, "rotulo": ROTULO, "criterio": "natureza jurídica da Receita Federal (receita_cnpj, campo `nat` por raiz de CNPJ)",
            "naturezas": dict(NATUREZAS_SA), "pendentes": dict(PENDENTES), "como_ler": COMO_LER}
