# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tabela de qualificações do sócio contra o arquivo oficial da Receita (PT-10 / GRUPOS-E1): código novo no arquivo oficial sem classe reprova."""
import pytest

from sources.socios_grupos import qualificacoes as q

# Cópia de código e descrição do `Qualificacoes.zip` de 2026-11 (https://arquivos.receitafederal.gov.br/public.php/webdav/2026-11/Qualificacoes.zip, consultado em 2026-11-25).
ARQUIVO_OFICIAL = {
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
SEM_CLASSE_POR_DECISAO = {0, 69}          # "Não informada" e "Beneficiário Final": não ligam e ficam em `nao_classificada`, explicitamente


def test_todo_codigo_do_arquivo_oficial_tem_classe_ou_esta_na_lista_de_nao_classificados():
    sem = [c for c in ARQUIVO_OFICIAL if q.classe_da_qualificacao(c) == q.NAO_CLASSIFICADA and c not in SEM_CLASSE_POR_DECISAO]
    assert not sem, f"código do arquivo oficial sem classe em qualificacoes.py: {sem}"


def test_descricoes_registradas_sao_as_do_arquivo_oficial():
    assert q.OFICIAL == ARQUIVO_OFICIAL


def test_codigos_fora_do_arquivo_oficial_estao_declarados_e_classificados():
    assert not (q.FORA_DO_ARQUIVO_OFICIAL & set(ARQUIVO_OFICIAL))
    classificados = {c for _liga, _d, cods in q.CLASSES.values() for c in cods}
    assert classificados == (set(ARQUIVO_OFICIAL) - SEM_CLASSE_POR_DECISAO) | q.FORA_DO_ARQUIVO_OFICIAL


def test_a_confirmar_so_tem_codigos_conhecidos_e_aparece_na_regra_publicada():
    assert q.A_CONFIRMAR <= set(ARQUIVO_OFICIAL) | q.FORA_DO_ARQUIVO_OFICIAL and q.FORA_DO_ARQUIVO_OFICIAL <= q.A_CONFIRMAR
    assert q.regra_publicada()["a_confirmar"] == [f"{c:02d}" for c in sorted(q.A_CONFIRMAR)]


@pytest.mark.parametrize("codigo, liga", [("49", True), ("22", True), ("05", False), ("10", False), ("16", False), ("00", False), ("", False), (None, False), ("99", False)])
def test_classe_de_codigos_conhecidos_e_formatos(codigo, liga):
    assert q.liga_empresas(codigo) is liga
