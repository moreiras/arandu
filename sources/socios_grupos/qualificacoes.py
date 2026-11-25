# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Qualificação do sócio (tabela da Receita Federal) e a regra de quem liga empresas no agrupamento societário (decisão D5).

Fonte e conferência: tabela "Qualificações" dos dados abertos do CNPJ da Receita Federal, arquivo `Qualificacoes.zip` da pasta 2026-11 do compartilhamento
público (`collection.receita_federal.compartilhamento_url` em config/settings.yaml; coletor em `sources/receita_socios`), consultado em 2026-11-25 em
https://arquivos.receitafederal.gov.br/public.php/webdav/2026-11/Qualificacoes.zip (WebDAV público do compartilhamento https://arquivos.receitafederal.gov.br/index.php/s/YggdBLfdninEJX9).
O arquivo tem 68 códigos (00 e 05 a 79, com lacunas) e as descrições estão em `OFICIAL`, copiadas sem alteração. Resultado da comparação código a código:
  * os 67 códigos do arquivo além do 00 estão classificados abaixo, e a descrição de cada um é a oficial (`OFICIAL`); o 00 ("Não informada") e o 69 não ligam;
  * 12 códigos que esta tabela usava vindos de uma reprodução de terceiros (turicas/socios-brasil) **não existem no arquivo oficial** de 2026-11: 1 a 4 (acionistas), 6, 7, 27, 36, 44, 45, 76 e 77.
    Ficam por serem códigos históricos que quadros antigos podem ter; estão em `FORA_DO_ARQUIVO_OFICIAL`;
  * a classe de ligação (liga ou não liga) é decisão do projeto, **a confirmar pelo mantenedor**, para os códigos de `A_CONFIRMAR`: onde a descrição oficial não diz se há participação
    (titular, empresário, produtor rural, fundador, sociedades consorciada e filiada, cotas em tesouraria, beneficiário final, não informada) e os que só existiam fora do arquivo oficial.

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

#: Descrição oficial de cada código do `Qualificacoes.zip` de 2026-11 (código sem zero à esquerda), sem alteração.
OFICIAL: dict[int, str] = {
    0: 'Não informada',
    5: 'Administrador',
    8: 'Conselheiro de Administração',
    9: 'Curador',
    10: 'Diretor',
    11: 'Interventor',
    12: 'Inventariante',
    13: 'Liquidante',
    14: 'Mãe',
    15: 'Pai',
    16: 'Presidente',
    17: 'Procurador',
    18: 'Secretário',
    19: 'Síndico (Condomínio)',
    20: 'Sociedade Consorciada',
    21: 'Sociedade Filiada',
    22: 'Sócio',
    23: 'Sócio Capitalista',
    24: 'Sócio Comanditado',
    25: 'Sócio Comanditário',
    26: 'Sócio de Indústria',
    28: 'Sócio-Gerente',
    29: 'Sócio Incapaz ou Relat.Incapaz (exceto menor)',
    30: 'Sócio Menor (Assistido/Representado)',
    31: 'Sócio Ostensivo',
    32: 'Tabelião',
    33: 'Tesoureiro',
    34: 'Titular de Empresa Individual Imobiliária',
    35: 'Tutor',
    37: 'Sócio Pessoa Jurídica Domiciliado no Exterior',
    38: 'Sócio Pessoa Física Residente no Exterior',
    39: 'Diplomata',
    40: 'Cônsul',
    41: 'Representante de Organização Internacional',
    42: 'Oficial de Registro',
    43: 'Responsável',
    46: 'Ministro de Estado das Relações Exteriores',
    47: 'Sócio Pessoa Física Residente no Brasil',
    48: 'Sócio Pessoa Jurídica Domiciliado no Brasil',
    49: 'Sócio-Administrador',
    50: 'Empresário',
    51: 'Candidato a cargo Político Eletivo',
    52: 'Sócio com Capital',
    53: 'Sócio sem Capital',
    54: 'Fundador',
    55: 'Sócio Comanditado Residente no Exterior',
    56: 'Sócio Comanditário Pessoa Física Residente no Exterior',
    57: 'Sócio Comanditário Pessoa Jurídica Domiciliado no Exterior',
    58: 'Sócio Comanditário Incapaz',
    59: 'Produtor Rural',
    60: 'Cônsul Honorário',
    61: 'Responsável indígena',
    62: 'Representante da Instituição Extraterritorial',
    63: 'Cotas em Tesouraria',
    64: 'Administrador Judicial',
    65: 'Titular Pessoa Física Residente ou Domiciliado no Brasil',
    66: 'Titular Pessoa Física Residente ou Domiciliado no Exterior',
    67: 'Titular Pessoa Física Incapaz ou Relativamente Incapaz (exceto menor)',
    68: 'Titular Pessoa Física Menor (Assistido/Representado)',
    69: 'Beneficiário Final',
    70: 'Administrador Residente ou Domiciliado no Exterior',
    71: 'Conselheiro de Administração Residente ou Domiciliado no Exterior',
    72: 'Diretor Residente ou Domiciliado no Exterior',
    73: 'Presidente Residente ou Domiciliado no Exterior',
    74: 'Sócio-Administrador Residente ou Domiciliado no Exterior',
    75: 'Fundador Residente ou Domiciliado no Exterior',
    78: 'Titular Pessoa Jurídica Domiciliada no Brasil',
    79: 'Titular Pessoa Jurídica Domiciliada no Exterior',
}
#: Códigos desta tabela que não constam do arquivo oficial de 2026-11 (vieram de reprodução de terceiros).
FORA_DO_ARQUIVO_OFICIAL = frozenset({1, 2, 3, 4, 6, 7, 27, 36, 44, 45, 76, 77})
#: Classificação do projeto, a confirmar pelo mantenedor: a descrição oficial não decide se há participação societária.
A_CONFIRMAR = frozenset({0, 20, 21, 34, 50, 54, 59, 63, 65, 66, 67, 68, 69, 75, 78, 79}) | FORA_DO_ARQUIVO_OFICIAL

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
    return {"fonte": "Receita Federal, dados abertos do CNPJ, tabela de qualificação do sócio (Qualificacoes.zip, pasta 2026-11, consultada em 2026-11-25)",
            "a_confirmar": [f"{c:02d}" for c in sorted(A_CONFIRMAR)],
            "classes": {c: {"liga": liga, "descricao": d, "codigos": [f"{x:02d}" for x in cods]} for c, (liga, d, cods) in CLASSES.items()},
            "nao_classificada": {"liga": False, "descricao": "código ausente ou fora da tabela adotada", "codigos": []}}
