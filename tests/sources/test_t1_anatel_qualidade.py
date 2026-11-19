# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — Anatel, RQUAL e reclamações: amostras sintéticas no layout real, sem rede."""
import io
import zipfile

import httpx
import pytest
import respx

from core import reclamacoes, rqual
from core.common import read_json_gz
from sources.anatel_reclamacoes import collect as f_recl
from sources.anatel_rqual import collect as f_rq


class _Log:
    def info(self, *a, **k): pass
    warning = info


def _abrir(fx, fonte, arq, nome):
    with zipfile.ZipFile(fx(fonte, arq)) as z:
        return io.BytesIO(z.read(nome))


# ── RQUAL ───────────────────────────────────────────────────────────────────

def test_rqual_agrega_nacional_uf_e_ultimo_resultado_do_municipio(fx):
    d = rqual.consolidar(_abrir(fx, "anatel_rqual", "indicadores_rqual_sintetico.zip", "Tabela_CSV_Indicadores_RQUAL.csv"))
    r = d["resumo"]
    assert r["linhas"] == 10 and r["resultados_numericos"] == 7 and r["sem_valor"] == {"NO": 1, "NA": 1, "NI": 1} and r["municipios"] == 2
    assert (r["mes_inicial"], r["mes_final"], r["itens_municipais"]) == ("2025-05", "2025-06", 6)
    nac = {(x["servico"], x["prestadora"], x["indicador"], x["mes"]): x for x in d["nacional"]}
    jun = nac[("Banda Larga Fixa", "ALFA", "IND4", "2025-06")]
    assert jun["municipios"] == 2 and jun["medidas"] == 800 and jun["media"] == 80.0 and jun["media_ponderada"] == 85.0 and jun["mediana"] == 80.0
    assert nac[("Banda Larga Fixa", "ALFA", "IND4", "2025-05")]["municipios"] == 1
    assert nac[("Banda Larga Fixa", "BETA", "IND4", "2025-06")]["media_ponderada"] is None      # a Anatel não informou medidas: sem ponderação
    assert not any(x["prestadora"] == "BETA" and x["indicador"] == "INF4-DL" for x in d["nacional"])      # NA/NO/NI não entram na média
    uf = {(x["uf"], x["prestadora"], x["indicador"], x["ano"]): x for x in d["uf"]}
    assert uf[("RO", "ALFA", "IND4", 2025)]["resultados"] == 2 and uf[("AC", "ALFA", "IND4", 2025)]["media"] == 70.0 and "mediana" not in uf[("AC", "ALFA", "IND4", 2025)]
    alfa = {(i["servico"], i["prestadora"], i["indicador"]): i for i in d["municipios"]["1100015"]["itens"]}
    assert alfa[("Banda Larga Fixa", "ALFA", "IND4")]["resultado"] == 90.0 and alfa[("Banda Larga Fixa", "ALFA", "IND4")]["mes"] == "2025-06"      # o último mês, não a média
    assert alfa[("Banda Larga Fixa", "ALFA", "IND4")]["estatistica"] is True and alfa[("Banda Larga Fixa", "ALFA", "IND4")]["erro_amostral"] == 3.0
    assert d["municipios"]["1200013"]["itens"][0]["estatistica"] is False and d["municipios"]["1200013"]["uf"] == "AC"
    assert len(d["municipios"]["1200013"]["itens"]) == 1       # BETA (NO), INF4-DL (NA) e IND2 (NI) não têm resultado numérico


def test_rqual_indicadores_e_prestadoras(fx):
    d = rqual.consolidar(_abrir(fx, "anatel_rqual", "indicadores_rqual_sintetico.zip", "Tabela_CSV_Indicadores_RQUAL.csv"))
    ind = {(i["servico"], i["codigo"]): i for i in d["indicadores"]}
    assert ind[("Banda Larga Fixa", "IND4")]["referencia_superior"] == "90%" and ind[("Banda Larga Fixa", "IND4")]["referencia_inferior"] == "60%" and ind[("Banda Larga Fixa", "IND4")]["unidade"] == "%"
    assert ind[("Banda Larga Fixa", "INF4-DL")]["referencia_superior"] is None and ind[("Banda Larga Fixa", "INF4-DL")]["tipo"] == "Informativo"
    assert {(p["servico"], p["prestadora"]): p["municipios"] for p in d["prestadoras"]}[("Banda Larga Fixa", "ALFA")] == 2


def test_rqual_numero():
    assert rqual.numero("94,0199") == 94.0199 and rqual.numero("NA") is None and rqual.numero("") is None and rqual.numero("-1,5") == -1.5


def test_rqual_leiaute_mudou_falha_alto():
    with pytest.raises(RuntimeError, match="leiaute mudou"):
        rqual.consolidar(io.BytesIO("Ano;Mês\n2025;1\n".encode()))


@respx.mock
def test_rqual_run_grava_normalizado(fx, tmp_path, monkeypatch):
    respx.get(f_rq.URL).mock(return_value=httpx.Response(200, content=fx("anatel_rqual", "indicadores_rqual_sintetico.zip").read_bytes(), headers={"last-modified": "Fri, 06 Nov 2026 11:04:10 GMT"}))
    monkeypatch.setattr(f_rq, "MINIMO_LINHAS", 5)
    monkeypatch.setattr(f_rq, "MINIMO_MUNICIPIOS", 2)
    r = f_rq.run("2026-11-06", tmp_path, _Log())
    assert r["linhas"] == 10 and r["itens_municipais"] == 6
    doc = read_json_gz(tmp_path / "normalized" / "2026-11-06" / "summary" / "anatel_rqual.json.gz")
    assert len(doc["sha256"]) == 64 and doc["data_arquivo"].startswith("Fri, 06 Nov 2026") and (tmp_path / "raw" / "2026-11-06" / "summary" / "rqual-2026-11-06.zip").exists()


@respx.mock
def test_rqual_arquivo_pequeno_falha(fx, tmp_path):
    respx.get(f_rq.URL).mock(return_value=httpx.Response(200, content=fx("anatel_rqual", "indicadores_rqual_sintetico.zip").read_bytes()))
    with pytest.raises(RuntimeError, match="truncado"):
        f_rq.run("2026-11-06", tmp_path, _Log())


# ── reclamações ─────────────────────────────────────────────────────────────

def _recl(fx):
    with zipfile.ZipFile(fx("anatel_reclamacoes", "consumidor_reclamacoes_sintetico.zip")) as z:
        return reclamacoes.consolidar_zip(lambda n: io.BytesIO(z.read(n)))


def test_reclamacoes_corte_entre_contexto_e_legado_e_so_reclamacao(fx):
    d = _recl(fx)
    r = d["resumo"]
    ctx, leg = r["arquivos"]["reclamacoes_contexto.csv"], r["arquivos"]["reclamacoes.csv"]
    assert ctx["linhas"] == 6 and ctx["solicitacoes"] == 125 and ctx["mes_inicial"] == "2020-01" and ctx["data_extracao"] == "2026-10-12"
    assert leg["linhas"] == 3 and leg["linhas_usadas"] == 2 and leg["mes_final"] == "2019-12"      # 2020-01 do legado sobrepõe o contexto e é descartado
    assert r["corte_contexto"] == "2020-01" and r["reclamacoes"] == 128 and r["sem_marca"] == 60 and r["marcas"] == 3
    marcas = {(x["marca"], x["servico"], x["ano"]): x for x in d["marcas"]}
    assert marcas[("ALFA", "SCM", 2025)]["reclamacoes"] == 45 and marcas[("ALFA", "SCM", 2025)]["municipios"] == 2      # caixa unificada; pedido de informação fora
    assert marcas[("ALFA", "SCM", 2020)]["reclamacoes"] == 7 and marcas[("ALFA", "SCM", 2015)]["reclamacoes"] == 4 and marcas[("OI", "STFC", 2019)]["reclamacoes"] == 2
    assert {x["tipo"] for x in d["por_mes"]} == {"Reclamação", "Pedido de informação"}
    assert sum(x["total"] for x in d["por_mes"] if x["mes"] == "2025-07" and x["tipo"] == "Pedido de informação") == 3


def test_reclamacoes_assuntos_so_do_contexto_e_municipios_nos_ultimos_anos(fx):
    d = _recl(fx)
    assert {x["ano"] for x in d["assuntos"]} == {2020, 2025} and all(x["assunto"] != "Outro assunto" for x in d["assuntos"])
    itens = {(i["ano"], i["servico"], i["marca"]): i["reclamacoes"] for i in d["municipios"]["1100015"]["itens"]}
    assert itens == {(2025, "SCM", "ALFA"): 40, (2025, "SMP_Pós", "ALFA"): 10}      # só os 3 últimos anos da fonte (2023 a 2025)
    assert d["municipios"]["1200013"]["nome"] == "Município Beta" and d["uf"][0]["uf"] in ("AC", "RO")


def test_reclamacoes_leiaute_mudou_falha_alto():
    with pytest.raises(RuntimeError, match="leiaute mudou"):
        reclamacoes.consolidar_zip(lambda n: io.BytesIO("DataExtracao;X\n1;2\n".encode()))


@respx.mock
def test_reclamacoes_run_grava_normalizado(fx, tmp_path, monkeypatch):
    respx.get(f_recl.URL).mock(return_value=httpx.Response(200, content=fx("anatel_reclamacoes", "consumidor_reclamacoes_sintetico.zip").read_bytes(), headers={"last-modified": "Tue, 13 Oct 2026 10:42:29 GMT"}))
    monkeypatch.setattr(f_recl, "MINIMO_RECLAMACOES", 100)
    monkeypatch.setattr(f_recl, "MINIMO_MARCAS", 3)
    r = f_recl.run("2026-11-06", tmp_path, _Log())
    assert r["reclamacoes"] == 128
    doc = read_json_gz(tmp_path / "normalized" / "2026-11-06" / "summary" / "anatel_reclamacoes.json.gz")
    assert len(doc["marcas"]) == 6 and len(doc["sha256"]) == 64 and (tmp_path / "raw" / "2026-11-06" / "summary" / "reclamacoes-2026-11-06.zip").exists()


@respx.mock
def test_reclamacoes_arquivo_pequeno_falha(fx, tmp_path):
    respx.get(f_recl.URL).mock(return_value=httpx.Response(200, content=fx("anatel_reclamacoes", "consumidor_reclamacoes_sintetico.zip").read_bytes()))
    with pytest.raises(RuntimeError, match="truncado"):
        f_recl.run("2026-11-06", tmp_path, _Log())
