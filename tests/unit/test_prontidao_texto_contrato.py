# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — o texto sobre a lista nominal de prontidão não pode contradizer `lista_nominal_habilitada()` (D2, SEG-E2).

A página, a docstring da rota, o catálogo do `/query` (`describe_schema(prontidao_asn)`) e o serviço falavam em "não há lista nominal" e
"DESLIGADA por padrão" com a lista ligada e aberta. Aqui as frases de negação só podem existir onde são condicionadas ao estado.
"""
import re
from pathlib import Path

import pytest

from api import query_catalogo
from api.services import prontidao as p

ROOT = Path(__file__).resolve().parents[2]
PAGINA = (ROOT / "frontend" / "src" / "pages" / "SegurancaRoteamentoPage.tsx").read_text(encoding="utf-8")
ROTA = (ROOT / "api" / "routes" / "prontidao.py").read_text(encoding="utf-8")
SERVICO = (ROOT / "api" / "services" / "prontidao.py").read_text(encoding="utf-8")
NEGACAO = re.compile(r"não há lista nominal|desligada por padr[ãa]o|aguarda a aprova[çc][ãa]o", re.I)


def test_padrao_e_lista_ligada(monkeypatch):
    monkeypatch.delenv("PRONTIDAO_LISTA_NOMINAL", raising=False)
    assert p.lista_nominal_habilitada() is True
    for valor, esperado in (("0", False), ("false", False), ("1", True), ("sim", True)):
        monkeypatch.setenv("PRONTIDAO_LISTA_NOMINAL", valor)
        assert p.lista_nominal_habilitada() is esperado


def test_textos_estaticos_nao_negam_a_lista_que_o_padrao_liga():
    """Rota, serviço e catálogo são estáticos: descrevem o padrão (ligada) e só citam o desligamento como opção."""
    desc = query_catalogo.SCHEMA["prontidao_asn"]["description"]
    for nome, texto in (("api/routes/prontidao.py", ROTA), ("api/services/prontidao.py", SERVICO), ("catálogo prontidao_asn", desc)):
        achou = NEGACAO.search(texto)
        assert not achou, f"{nome} contradiz lista_nominal_habilitada() (padrão ligado): {achou.group(0)!r}"
    assert "ligada por padrão" in desc and "não medido" in desc and "pilares_medidos" in desc
    assert "ordem de ASN" in desc


def test_pagina_so_nega_a_lista_condicionada_ao_estado_da_api():
    """A negação mora numa constante usada só quando `lista_nominal === false`; o resto da página não a repete."""
    m = re.search(r"export const TEXTO_SEM_LISTA_NOMINAL = '([^']*)'", PAGINA)
    assert m, "TEXTO_SEM_LISTA_NOMINAL não encontrado"
    fora = PAGINA.replace(m.group(0), "")
    assert not re.search(r"n[ãa]o publica a lista nominal|n[ãa]o h[áa] lista nominal", fora, re.I), "negação da lista fora do texto condicionado"
    assert re.search(r"r\.lista_nominal === false \? TEXTO_SEM_LISTA_NOMINAL : TEXTO_LISTA_NOMINAL_PUBLICA", PAGINA)
    pub = re.search(r"export const TEXTO_LISTA_NOMINAL_PUBLICA = '([^']*)'", PAGINA).group(1)
    assert "não medido" in pub and "ordem padrão é por ASN" in pub and "quantos pilares foram medidos" in pub


@pytest.mark.parametrize("ligada", [True, False])
def test_resumo_publica_o_estado_que_a_pagina_usa(ligada, monkeypatch):
    monkeypatch.setenv("PRONTIDAO_LISTA_NOMINAL", "1" if ligada else "0")
    doc = {"snapshot_date": "2026-11-15", "natureza": "indice_composto", "regras": {}, "fontes": {}, "limites": "", "brasil": {"asns": 0}, "por_uf": {}, "por_faixa_porte": {}}
    assert p.resumo(doc, None)["lista_nominal"] is ligada
    assert p.resumo({**doc, "por_uf": {"SP": {"asns": 1}}}, "sp")["lista_nominal"] is ligada
