# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — Cetic.br (tabelas da TIC Domicílios e da TIC Provedores): arquivos reais → formato longo, sem rede."""
import httpx
import pytest
import respx

from core import cetic
from core.common import read_json_gz
from core.xlsx_leve import ler_xlsx
from sources.cetic_tic_domicilios_tabelas import collect as dom
from sources.cetic_tic_provedores_tabelas import collect as prov

ZIP_DOM = "tic_domicilios_2025_domicilios_tabelas_xlsx_v1.0.zip"
ZIP_PROV = "tic_provedores_2024_tabela_xlsx_v1.0.zip"


def _zip(fx, nome):
    return fx("cetic", nome).read_bytes()


def test_descobre_a_edicao_mais_recente_so_do_zip_de_xlsx_em_portugues(fx):
    html = fx("cetic", "pagina_domicilios.html").read_text(encoding="utf-8")
    url, ano, nome = cetic.descobrir(html, "tic_domicilios")
    assert (ano, nome) == (2025, ZIP_DOM) and url == "https://cetic.br/media/microdados/982/" + ZIP_DOM
    url, ano, nome = cetic.descobrir(fx("cetic", "pagina_provedores.html").read_text(encoding="utf-8"), "tic_provedores")
    assert (ano, nome) == (2024, ZIP_PROV)


def test_pagina_sem_o_padrao_do_nome_falha_alto():
    with pytest.raises(RuntimeError, match="padrão do nome"):
        cetic.descobrir("<html>sem links</html>", "tic_domicilios")


def test_leitor_xlsx_devolve_abas_e_celulas(fx):
    z = cetic.planilhas(_zip(fx, ZIP_DOM))
    assert set(z) == set(cetic.PLANILHAS) and len(z["proporcao"]) == 15
    aba = z["proporcao"]["A1"]
    assert aba[0][0].startswith("A1 - DOMICÍLIOS COM COMPUTADOR") and aba[4][:2] == ["TOTAL", "Total"]


def test_domicilios_formato_longo_com_proporcao_total_e_margens(fx):
    tabelas, linhas = cetic.normalizar(_zip(fx, ZIP_DOM), 10)
    assert len(tabelas) == 15 and tabelas["A1"]["titulo"] == "Domicílios com computador" and tabelas["A1"]["universo"] == "Total de domicílios"
    a1 = {(l["recorte"], l["resposta"]): l for l in linhas if l["tabela"] == "A1"}
    br = a1[("Total", "Sim")]
    assert br["dimensao"] == "Total" and br["item"] == ""
    assert br["proporcao"] == pytest.approx(31.68, abs=0.01) and br["total"] == 24981993 and br["margem_proporcao"] == pytest.approx(1.338, abs=0.001)
    assert br["proporcao"] + a1[("Total", "Não")]["proporcao"] == pytest.approx(100, abs=0.01)
    assert a1[("Urbana", "Sim")]["total"] == 23668826 and a1[("Urbana", "Sim")]["dimensao"] == "Área"
    a2 = [l for l in linhas if l["tabela"] == "A2" and l["recorte"] == "Total" and l["resposta"] == "Sim"]
    assert {l["item"] for l in a2} >= {"Computador de mesa", "Notebook"}                  # pergunta com vários itens


def test_provedores_recortes_por_porte_e_regiao(fx):
    tabelas, linhas = cetic.normalizar(_zip(fx, ZIP_PROV), 30)
    assert len(tabelas) == 42 and {l["dimensao"] for l in linhas} >= {"Total", "Região", "Porte do provedor", "Classe de número médio de acessos"}
    assert all(l["proporcao"] is None or 0 <= l["proporcao"] <= 100 for l in linhas)


def test_menos_tabelas_que_o_minimo_falha_alto(fx):
    with pytest.raises(RuntimeError, match="só 15 tabelas"):
        cetic.normalizar(_zip(fx, ZIP_DOM), 30)


def test_zip_sem_uma_das_planilhas_falha(fx, tmp_path):
    import io
    import zipfile
    src = zipfile.ZipFile(io.BytesIO(_zip(fx, ZIP_DOM)))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n in src.namelist():
            if "margem_de_erro_total" not in n:
                z.writestr(n, src.read(n))
    with pytest.raises(RuntimeError, match="não traz as planilhas"):
        cetic.planilhas(buf.getvalue())


@respx.mock
def test_run_grava_bruto_byte_a_byte_e_normalizado(fx, tmp_path):
    import hashlib
    corpo = _zip(fx, ZIP_DOM)
    respx.get("https://cetic.br/pt/pesquisa/domicilios/microdados/").mock(return_value=httpx.Response(200, text=fx("cetic", "pagina_domicilios.html").read_text(encoding="utf-8")))
    respx.get("https://cetic.br/media/microdados/982/" + ZIP_DOM).mock(return_value=httpx.Response(200, content=corpo))

    class Log:
        def info(self, *a, **k): pass

    r = dom.run("2026-11-01", tmp_path, Log(), dormir=lambda s: None)
    assert r["edicao"] == 2025 and r["tabelas"] == 15
    assert (tmp_path / "raw" / "2026-11-01" / "summary" / ZIP_DOM).read_bytes() == corpo
    doc = read_json_gz(tmp_path / "normalized" / "2026-11-01" / "summary" / "cetic_tic_domicilios.json.gz")
    assert doc["edicao"] == 2025 and doc["licenca"] == "CC BY 4.0" and doc["sha256"] == hashlib.sha256(corpo).hexdigest()
    assert doc["total_linhas"] == len(doc["linhas"]) and doc["fonte"].startswith("Cetic.br|NIC.br, TIC Domicílios 2025")


@respx.mock
def test_site_fora_do_ar_falha_depois_das_tentativas(tmp_path):
    respx.get("https://cetic.br/pt/pesquisa/provedores/microdados/").mock(return_value=httpx.Response(503))

    class Log:
        def info(self, *a, **k): pass

    with pytest.raises(RuntimeError, match="cetic https://cetic.br/pt/pesquisa/provedores"):
        prov.run("2026-11-01", tmp_path, Log(), dormir=lambda s: None)
