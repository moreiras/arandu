# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Qualificação do sócio (tabela da Receita Federal) e a regra de quem liga empresas no agrupamento societário (decisão D5).

Fonte do código e da descrição: tabela "Qualificações" dos dados abertos do CNPJ da Receita Federal (arquivo `Qualificacoes.zip`, layout em
https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf). A transcrição abaixo foi conferida contra a reprodução da tabela em
`qualificacao-socio.csv` do repositório turicas/socios-brasil (terceiros), consultada em 2026-11-25, e **não** contra o arquivo da Receita: o
`Qualificacoes.zip` do mês deve ser comparado com esta lista a cada nova coleta.

Regra adotada: só quem tem **participação societária** gera aresta. Administrador, conselheiro, diretor, presidente e vice-presidente (cargos de
gestão), assim como procurador, tutor, inventariante e demais representantes, não ligam empresas: uma pessoa em comum na diretoria não prova
propriedade comum. Código ausente ou fora da tabela fica em `nao_classificada` e também não liga (a ausência de evidência não vira ligação).
Sócio-administrador (28, 49, 74) tem participação e liga.
"""
from __future__ import annotations

# classe -> (liga empresas?, descrição, códigos)
CLASSES: dict[str, tuple[bool, str, tuple[int, ...]]] = {
    "socio": (True, "Sócio ou sociedade consorciada/filiada, capitalista, comanditado/comanditário, ostensivo, participante, investidor, com ou sem capital, no país ou no exterior",
              (20, 21, 22, 23, 24, 25, 26, 27, 29, 30, 31, 37, 38, 44, 45, 47, 48, 52, 53, 55, 56, 57, 58)),
    "socio_administrador": (True, "Sócio-gerente e sócio-administrador (têm participação e gestão)", (28, 49, 74)),
    "acionista": (True, "Acionista, controlador, diretor ou presidente que consta como acionista", (1, 2, 3, 4)),
    "titular": (True, "Titular de empresa individual, empresário e produtor rural (dono único)", (34, 50, 59, 65, 66, 67, 68, 78, 79)),
    "administracao": (False, "Cargo de gestão sem participação societária: administrador, conselheiro de administração, diretor, presidente, vice-presidente e gerente-delegado",
                      (5, 8, 10, 16, 36, 70, 71, 72, 73, 77)),
    "representacao": (False, "Representação ou função sem participação: procurador, tutor, curador, inventariante, liquidante, interventor, síndico, secretário, tesoureiro, "
                      "pai e mãe de menor, tabelião, oficial de registro, responsável, administrador judicial, diplomata, cônsul, fundador, protetor, comissário, outros",
                      (6, 7, 9, 11, 12, 13, 14, 15, 17, 18, 19, 32, 33, 35, 39, 40, 41, 42, 43, 46, 51, 54, 60, 61, 62, 63, 64, 75, 76)),
}
NAO_CLASSIFICADA = "nao_classificada"

_POR_CODIGO = {cod: classe for classe, (_liga, _d, cods) in CLASSES.items() for cod in cods}
CLASSES_QUE_LIGAM = frozenset(c for c, (liga, _d, _c) in CLASSES.items() if liga)


def classe_da_qualificacao(codigo: str | int | None) -> str:
    """Classe de um código de qualificação ('49', '05', 10); `nao_classificada` se vazio, não numérico ou fora da tabela."""
    try:
        return _POR_CODIGO.get(int(str(codigo).strip()), NAO_CLASSIFICADA)
    except (TypeError, ValueError):
        return NAO_CLASSIFICADA


def liga_empresas(codigo: str | int | None) -> bool:
    return classe_da_qualificacao(codigo) in CLASSES_QUE_LIGAM


def regra_publicada() -> dict:
    """A regra em forma publicável (sem nomes): classes, se ligam, e os códigos."""
    return {"fonte": "Receita Federal, dados abertos do CNPJ, tabela de qualificação do sócio (Qualificacoes)",
            "classes": {c: {"liga": liga, "descricao": d, "codigos": [f"{x:02d}" for x in cods]} for c, (liga, d, cods) in CLASSES.items()},
            "nao_classificada": {"liga": False, "descricao": "código ausente ou fora da tabela adotada", "codigos": []}}
