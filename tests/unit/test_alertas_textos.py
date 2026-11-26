# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Guarda de linguagem dos pontos de atenção (PT-30): sem travessão, sem "(s)" e com singular e plural pelo número."""
import ast
import re
from pathlib import Path

import pytest

from core import alerta_textos
from products.alerts import registro
from tests.unit.test_alerts_regras import ASN, CENARIOS, FakeStore
from products.alerts.base import Contexto

RAIZ = Path(__file__).resolve().parents[2]
ARQUIVOS = sorted((RAIZ / "products/alerts/regras").glob("*.py")) + [RAIZ / "core/alerta_textos.py", RAIZ / "core/alerta_ptt_proximo.py", RAIZ / "api/asn_health.py"]
FORMAS = r"[—–]|\(s\)|\(ões\)|\(ns\)|\(es\)"
PROIBIDO = re.compile(FORMAS + r"|\bdown\b|single-homed")      # nos alertas gerados, também o inglês dos títulos


def _literais(caminho: Path):
    """Strings do código que não são docstring nem comentário (o que pode chegar à tela)."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    docstrings = set()
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Module, ast.FunctionDef, ast.ClassDef)) and no.body and isinstance(no.body[0], ast.Expr) and isinstance(getattr(no.body[0], "value", None), ast.Constant):
            docstrings.add(id(no.body[0].value))
    for no in ast.walk(arvore):
        if isinstance(no, ast.Constant) and isinstance(no.value, str) and id(no) not in docstrings:
            yield no.lineno, no.value


@pytest.mark.parametrize("caminho", ARQUIVOS, ids=lambda p: p.name)
def test_codigo_dos_alertas_nao_tem_travessao_nem_formas_como_bloco_s(caminho):
    ruins = [(n, t) for n, t in _literais(caminho) if re.search(FORMAS, t)]
    assert ruins == [], f"{caminho.name}: {ruins}"


def test_alertas_gerados_pelos_cenarios_sem_travessao_e_sem_formas_como_bloco_s():
    n = 0
    for regra_id, (dispara, _, _) in CENARIOS.items():
        ctx = Contexto(store=dispara.get("store") or FakeStore(), date_str="2026-10-23", asn=ASN, doc=dispara["doc"])
        mod = next(m for m in registro.MODULOS if m.REGRA.id == regra_id)
        for a in mod.avaliar(ctx):
            n += 1
            assert not PROIBIDO.search(a["title"] + " " + a["detail"]), (regra_id, a["title"], a["detail"])
    assert n >= 20


@pytest.mark.parametrize("q", [1, 2])
def test_singular_e_plural_pelo_numero(q):
    textos = [alerta_textos.blocos_inalcancaveis(q), alerta_textos.anuncio_por_outro_as(q), alerta_textos.fora_da_alocacao(q), alerta_textos.rpki_invalido(q),
              alerta_textos.cobertura_rpki_parcial(q), alerta_textos.roa_maxlength_folgado(q), alerta_textos.membro_sem_sessao(q),
              alerta_textos.prefixos_filtraveis(q), alerta_textos.as_loop(q), alerta_textos.sem_peeringdb(q), alerta_textos.politica_v4v6(q, q),
              alerta_textos.sessoes_inativas("2026-01-01", q, ["IX.br São Paulo (SP): 1 dia"]), alerta_textos.desagregacao(40, "IPv4", q)]
    for t in textos:
        assert not PROIBIDO.search(t), t
    if q == 1:
        assert alerta_textos.cobertura_rpki_parcial(1) == "1 bloco alocado não tem ROA que o cubra. Parte do espaço fica sem proteção de origem."
        assert alerta_textos.rpki_invalido(1).startswith("1 prefixo anunciado está inválido")
        assert "1 PTT com peering só IPv6" in alerta_textos.politica_v4v6(1, 0)
        assert alerta_textos.sessoes_inativas("2026-01-01", 1, ["x"]).count("1 dia ") == 1
    else:
        assert alerta_textos.cobertura_rpki_parcial(2).startswith("2 blocos alocados não têm ROA que os cubra")
        assert alerta_textos.rpki_invalido(2).startswith("2 prefixos anunciados estão inválidos")


def test_nome_do_ptt_aparece_com_o_codigo():
    assert alerta_textos.nome_ptt("sp", {"sp": "IX.br São Paulo"}) == "IX.br São Paulo (SP)"
    assert alerta_textos.nome_ptt("za", {}) == "ZA"


def test_upstream_unico_inferido_sem_jargao():
    """Classificação com acento e confiança em porcentagem, em vez de "nível provavel, p = 1.0"."""
    from core import alerta_textos as t
    txt = t.single_homed_inferido("IPv6 e IPv4", 264490, "provavel", 1.0)
    assert "classificação provável; confiança estimada de 100%" in txt
    assert "p = " not in txt and "nível" not in txt
    assert "confiança" not in t.single_homed_inferido("IPv4", 1, "possivel", None)
