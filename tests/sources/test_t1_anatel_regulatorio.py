# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — Anatel, multas, faixas (PDFF) e satélites: amostras sintéticas no layout real, sem rede."""
import io
import zipfile

import httpx
import pytest
import respx

from core import multas, pdff, satelites
from core.common import read_json_gz
from sources.anatel_multas import collect as f_multas
from sources.anatel_pdff import collect as f_pdff
from sources.anatel_satelites import collect as f_sat


class _Log:
    def info(self, *a, **k): pass
    warning = info


def _abrir(fx, fonte, arq, nome):
    with zipfile.ZipFile(fx(fonte, arq)) as z:
        return io.BytesIO(z.read(nome))


# ── multas ──────────────────────────────────────────────────────────────────

def test_multas_agrega_por_raiz_e_grupo_e_descarta_pf_e_fora_do_escopo(fx):
    emp, resumo = multas.consolidar(_abrir(fx, "anatel_multas", "arrecadacao_sintetico.zip", "multas_constituidas.csv"))
    assert resumo["linhas"] == 10 and resumo["pessoa_fisica"] == 1 and resumo["fora_do_escopo"] == 2 and resumo["sem_servico"] == 1 and resumo["empresas"] == 4 and resumo["multas"] == 7
    por = {(e["raiz"], e["grupo"]): e for e in emp}
    scm = por[("11111111", "SCM")]
    assert scm["multas"] == 3 and scm["cnpjs"] == ["11111111000111", "11111111000292"] and scm["entidade"] == "PROVEDOR UM LTDA" and scm["uf"] == "SP"
    assert scm["original"] == pytest.approx(8000.0) and scm["pago"] == pytest.approx(1700.5) and scm["saldo"] == pytest.approx(9050.75)
    assert scm["situacoes"] == {"Quitado": 1, "Devedor": 1, "Parcial": 1} and scm["anos"] == {"2019": 1, "2021": 2}
    assert por[("44444444", "SeAC")]["multas"] == 2 and por[("44444444", "SeAC")]["anos"] == {"2012": 1, "2014": 1}      # data de aplicação em branco usa o ano de referência
    assert ("55555555", "SCM") not in por and not any(e["raiz"] in ("55555555", "66666666") for e in emp)


def test_multas_grupo_de_servico():
    assert multas.grupo_servico("Serviço de Comunicação Multimídia - Est. Terrena") == "SCM"
    assert multas.grupo_servico("SERVIÇO MOVEL PESSOAL") == "SMP" and multas.grupo_servico("STFC/RADIOTELEFONICO - ESTACOES TERRESTRES") == "STFC"
    assert multas.grupo_servico("Radioamador") is None and multas.grupo_servico("") is None


def test_multas_leiaute_mudou_falha_alto():
    with pytest.raises(RuntimeError, match="leiaute mudou"):
        multas.consolidar(io.BytesIO("NU_CNPJ;X\n1;2\n".encode()))


@respx.mock
def test_multas_run_grava_normalizado(fx, tmp_path, monkeypatch):
    respx.get(f_multas.URL).mock(return_value=httpx.Response(200, content=fx("anatel_multas", "arrecadacao_sintetico.zip").read_bytes(), headers={"last-modified": "Mon, 02 Nov 2026 10:30:08 GMT"}))
    monkeypatch.setattr(f_multas, "MINIMO_EMPRESAS", 2)
    r = f_multas.run("2026-11-02", tmp_path, _Log())
    assert r["empresas"] == 4
    doc = read_json_gz(tmp_path / "normalized" / "2026-11-02" / "summary" / "anatel_multas.json.gz")
    assert len(doc["empresas"]) == 4 and len(doc["sha256"]) == 64 and (tmp_path / "raw" / "2026-11-02" / "summary" / "multas-2026-11-02.zip").exists()


@respx.mock
def test_multas_arquivo_pequeno_falha(fx, tmp_path):
    respx.get(f_multas.URL).mock(return_value=httpx.Response(200, content=fx("anatel_multas", "arrecadacao_sintetico.zip").read_bytes()))
    with pytest.raises(RuntimeError, match="truncado"):
        f_multas.run("2026-11-02", tmp_path, _Log())


# ── PDFF ────────────────────────────────────────────────────────────────────

def _faixas(fx):
    return pdff.consolidar(_abrir(fx, "anatel_pdff", "pdff_sintetico.zip", "Destinacao.csv"), _abrir(fx, "anatel_pdff", "pdff_sintetico.zip", "Atribuicao_BR.csv"))


def test_pdff_chave_e_o_par_em_mhz_e_nao_o_id(fx):
    faixas, resumo = _faixas(fx)
    por = {(f["ini_mhz"], f["fim_mhz"]): f for f in faixas}
    assert resumo == {"faixas": 5, "com_destinacao": 5, "com_atribuicao": 3}
    f33 = por[(3300.0, 3400.0)]
    assert [d["servico"] for d in f33["destinacao"]] == ["COMUNICAÇÃO MULTIMÍDIA", "MÓVEL PESSOAL", "Radioamador"] and f33["destinacao"][2]["carater"] == "Secundário"
    assert [a["servico"] for a in f33["atribuicao"]] == ["FIXO", "MÓVEL"]
    assert por[(2400.0, 2483.5)]["destinacao"][0]["servico"] == "COMUNICAÇÃO MULTIMÍDIA"      # vírgula decimal


def test_pdff_leiaute_mudou_falha_alto():
    with pytest.raises(RuntimeError, match="leiaute mudou"):
        pdff.consolidar(io.BytesIO("A;B\n1;2\n".encode()), io.BytesIO("A;B\n1;2\n".encode()))


@respx.mock
def test_pdff_run_grava_normalizado(fx, tmp_path, monkeypatch):
    respx.get(f_pdff.URL).mock(return_value=httpx.Response(200, content=fx("anatel_pdff", "pdff_sintetico.zip").read_bytes()))
    monkeypatch.setattr(f_pdff, "MINIMO_FAIXAS", 3)
    assert f_pdff.run("2026-11-02", tmp_path, _Log())["faixas"] == 5
    assert len(read_json_gz(tmp_path / "normalized" / "2026-11-02" / "summary" / "anatel_pdff.json.gz")["faixas"]) == 5


# ── satélites ───────────────────────────────────────────────────────────────

def _sat(fx):
    z = "satelites_sintetico.zip"
    return satelites.consolidar(_abrir(fx, "anatel_satelites", z, "direitos_satelites_ordenado_por_operadora.csv"), _abrir(fx, "anatel_satelites", z, "constelacoes_ngeo_portal.csv"),
                                _abrir(fx, "anatel_satelites", z, "satelites_operando_comercialmente.csv"))


def test_satelites_datas_cnpj_e_n_a(fx):
    t, resumo = _sat(fx)
    assert resumo == {"direitos": 4, "ngeo": 2, "operando": 2}
    d = {(x["satelite"], x["banda"]): x for x in t["direitos"]}
    assert d[("ALFA-1", "C (não planejada)")]["lancamento"] == "2015-01-03" and d[("ALFA-1", "C (não planejada)")]["validade"] == "2030-12-24" and d[("ALFA-1", "C (não planejada)")]["prorrogado"] is True
    assert d[("Sistema Novo", "Q/V")]["lancamento"] is None and d[("BR-SAT 2", "Ka")]["prorrogado"] is False
    n = {x["objeto"]: x for x in t["ngeo"]}
    assert n["Iridium"]["cnpj"] == "04399863000134" and n["Iridium"]["planos"] == 6 and n["Iridium"]["constelacao"] == 66 and n["Nova"]["planos"] is None and n["Nova"]["lancamento"] is None


@respx.mock
def test_satelites_run_grava_normalizado(fx, tmp_path, monkeypatch):
    respx.get(f_sat.URL).mock(return_value=httpx.Response(200, content=fx("anatel_satelites", "satelites_sintetico.zip").read_bytes()))
    monkeypatch.setattr(f_sat, "MINIMO_DIREITOS", 2)
    assert f_sat.run("2026-11-02", tmp_path, _Log())["direitos"] == 4
    doc = read_json_gz(tmp_path / "normalized" / "2026-11-02" / "summary" / "anatel_satelites.json.gz")
    assert len(doc["direitos"]) == 4 and len(doc["ngeo"]) == 2 and len(doc["operando"]) == 2
