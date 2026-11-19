# SPDX-License-Identifier: AGPL-3.0-or-later
"""T1 — cadastro de telecom da Receita Federal (WebDAV do Nextcloud + ZIPs em fluxo)."""
import pytest
import respx

from sources.receita_cnpj import collect as rc
from sources.receita_socios import collect as rs
from tests.sources.conftest import make_zip, read_gz, write_gz
from tests.sources.test_t1_receita_socios import multistatus

PASTA = f"{rs.WEBDAV_ROOT}2026-10/"


@pytest.fixture(autouse=True)
def sem_pausa(monkeypatch):
    monkeypatch.setattr(rc, "PAUSA_S", 0)


@pytest.fixture()
def universo(base, date_str):
    """O CNPJ 11111111 está nas outorgas (SCM): entra com todos os estabelecimentos, mesmo os de outro CNAE."""
    write_gz(base / "normalized" / date_str / "summary" / "anatel_scm.json.gz", {"by_cnpj": {"11111111000191": []}})


def zip_de(fx, nome_zip, arquivo):
    return make_zip(nome_zip, fx("receita_cnpj", arquivo).read_bytes())


def montar(respx_mock, fx, partes=1):
    respx_mock.route(method="PROPFIND", url=rs.WEBDAV_ROOT).respond(207, text=multistatus(rs.WEBDAV_ROOT, [("2026-09", True), ("2026-10", True)]))
    arquivos = [f"Estabelecimentos{i}.zip" for i in range(partes)] + ["Empresas0.zip", "Simples.zip", "Municipios.zip", "Naturezas.zip", "Cnaes.zip", "Socios0.zip"]
    respx_mock.route(method="PROPFIND", url=PASTA).respond(207, text=multistatus(PASTA, [(a, False) for a in arquivos]))
    corpo = {"Estabelecimentos": zip_de(fx, "K.ESTABELE", "Estabelecimentos0.sample.csv"), "Empresas0.zip": zip_de(fx, "K.EMPRECSV", "Empresas0.sample.csv"),
             "Simples.zip": zip_de(fx, "K.SIMPLES.CSV", "Simples.sample.csv"), "Municipios.zip": zip_de(fx, "K.MUNICCSV", "Municipios.sample.csv"),
             "Naturezas.zip": zip_de(fx, "K.NATJUCSV", "Naturezas.sample.csv"), "Cnaes.zip": zip_de(fx, "K.CNAECSV", "Cnaes.sample.csv")}
    respx_mock.get(url__regex=rf"{PASTA}Estabelecimentos\d\.zip").respond(200, content=corpo["Estabelecimentos"])
    for nome in ("Empresas0.zip", "Simples.zip", "Municipios.zip", "Naturezas.zip", "Cnaes.zip"):
        respx_mock.get(url=PASTA + nome).respond(200, content=corpo[nome])


@respx.mock
def test_recorta_o_universo_e_o_cnae_61_e_descarta_o_resto(base, log, fx, universo, date_str):
    montar(respx, fx)
    r = rc.run(date_str, base, log)
    assert r["dump_reference"] == "2026-10" and r["linhas_lidas"] == 7
    assert sorted(r["estabelecimentos"]) == ["11111111", "22222222", "33333333", "55555555"]          # 44444444 (CEP/DDD 61) e 66666666 ficam de fora
    assert [e["c"] for e in r["estabelecimentos"]["11111111"]] == ["11111111000191", "11111111000272"]  # matriz e filial, mesmo a filial de CNAE 4321500
    assert r["estabelecimentos_guardados"] == 5


@respx.mock
def test_cnae_61_so_no_secundario_entra(base, log, fx, universo, date_str):
    montar(respx, fx)
    r = rc.run(date_str, base, log)
    est = r["estabelecimentos"]["33333333"][0]
    assert est["p"] == "4711301" and est["x"] == ["4321500", "6110803"] and est["s"] == "08" and est["m"] == 1


@respx.mock
def test_nao_guarda_contato_endereco_nem_cep(base, log, fx, universo, date_str):
    montar(respx, fx)
    r = rc.run(date_str, base, log)
    texto = str(r)
    for proibido in ("CONTATO@FIBRAUM", "RUA DAS FLORES", "30001000", "SALA 2", "01000000", "CENTRO"):
        assert proibido not in texto
    assert set(r["estabelecimentos"]["11111111"][0]) <= {"c", "m", "s", "d", "ds", "u", "mu", "p", "x", "n"}


@respx.mock
def test_empresario_individual_fica_sem_razao_social_e_sem_nome_fantasia(base, log, fx, universo, date_str):
    montar(respx, fx)
    r = rc.run(date_str, base, log)
    assert "razao" not in r["empresa"]["55555555"] and r["empresa"]["55555555"]["nat"] == "2135"
    assert "n" not in r["estabelecimentos"]["55555555"][0]
    assert "FULANO" not in str(r) and "JOSE DA SILVA" not in str(r)
    assert r["empresa"]["11111111"]["razao"] == "FIBRA UM TELECOM LTDA" and r["estabelecimentos"]["11111111"][0]["n"] == "FIBRA UM"


@respx.mock
def test_empresas_simples_e_tabelas_so_dos_cnpjs_guardados(base, log, fx, universo, date_str):
    montar(respx, fx)
    r = rc.run(date_str, base, log)
    assert sorted(r["empresa"]) == ["11111111", "22222222", "33333333", "55555555"] and "66666666" not in r["simples"]
    assert r["empresa"]["22222222"] == {"nat": "2062", "capital": 50000.0, "porte": "03", "razao": "NET DOIS SERVICOS DE INTERNET LTDA"}
    assert r["simples"]["22222222"]["simples"] is True and r["simples"]["22222222"]["simples_in"] == "2019-01-01" and r["simples"]["22222222"]["simples_out"] is None
    assert r["simples"]["55555555"]["mei"] is True and r["simples"]["11111111"]["simples"] is False
    assert r["municipios_rfb"]["7107"] == "SÃO PAULO"                                        # latin-1 decodificado
    assert r["cnaes"]["6110803"].startswith("Serviços de comunicação")


@respx.mock
def test_varias_partes_somam_e_uma_requisicao_por_vez_com_credencial(base, log, fx, universo, date_str):
    montar(respx, fx, partes=2)
    r = rc.run(date_str, base, log)
    assert r["linhas_lidas"] == 14 and r["estabelecimentos_guardados"] == 10                 # a mesma parte servida 2×: as linhas dobram
    assert all(c.request.headers.get("Authorization", "").startswith("Basic ") for c in respx.calls)
    assert all(c.request.headers.get("User-Agent", "").startswith("arandurape/") for c in respx.calls)


@respx.mock
def test_grava_o_normalizado_e_nao_repete_o_mes_sem_force(base, log, fx, universo, date_str):
    montar(respx, fx)
    rc.run(date_str, base, log)
    norm = read_gz(base / "normalized" / date_str / "summary" / "receita_cnpj.json.gz")
    assert norm["dump_reference"] and "decisao" not in norm
    antes = len([c for c in respx.calls if c.request.method == "GET"])
    rc.run(date_str, base, log)                                                              # mesmo mês: só o PROPFIND da raiz, nenhum download
    assert len([c for c in respx.calls if c.request.method == "GET"]) == antes
    rc.run(date_str, base, log, force=True)
    assert len([c for c in respx.calls if c.request.method == "GET"]) > antes


@respx.mock
def test_apaga_os_temporarios_depois_de_cada_parte(base, log, fx, universo, date_str):
    montar(respx, fx)
    rc.run(date_str, base, log)
    assert list((base / "raw" / "_receita_tmp").glob("*.zip")) == []


@respx.mock
def test_sem_estabelecimentos_levanta(base, log, fx, universo, date_str):
    respx.route(method="PROPFIND", url=rs.WEBDAV_ROOT).respond(207, text=multistatus(rs.WEBDAV_ROOT, [("2026-10", True)]))
    respx.route(method="PROPFIND", url=PASTA).respond(207, text=multistatus(PASTA, [("Socios0.zip", False)]))
    with pytest.raises(RuntimeError, match="Estabelecimentos ou Empresas ausentes"):
        rc.run(date_str, base, log)
