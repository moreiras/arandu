# SPDX-License-Identifier: AGPL-3.0-or-later
"""T1 — operações do BNDES e sanções CEIS/CNEP a empresas de telecom, sem rede."""
import io
import zipfile

import httpx
import pytest
import respx

from core import financiamento as fin
from sources.bndes_operacoes import collect as bn
from sources.cgu_ceis_cnep import collect as cg
from tests.sources.conftest import read_gz, write_gz


@pytest.fixture()
def universo(base, date_str):
    """11111111 está nas outorgas (SCM)."""
    write_gz(base / "normalized" / date_str / "summary" / "anatel_scm.json.gz", {"by_cnpj": {"11111111000191": []}})


def test_regras_de_leitura():
    assert fin.numero("9090000,0") == 9090000.0 and fin.numero("") is None
    assert fin.data_iso("07/04/2026") == "2026-04-07" and fin.data_iso("2002-01-02") == "2002-01-02" and fin.data_iso("") is None
    assert fin.digitos("56.024.581/0001-56") == "56024581000156"
    assert len(fin.texto("x" * 500)) == fin.MAX_TEXTO


@respx.mock
def test_bndes_so_cnpj_do_universo(respx_mock, base, date_str, log, fx, universo):
    respx_mock.get(bn.CKAN).respond(200, content=fx("bndes_operacoes", "ckan_package_show.sample.json").read_bytes())
    respx_mock.get("https://dadosabertos.bndes.gov.br/x/nao_automaticas.csv").respond(200, content=fx("bndes_operacoes", "operacoes_nao_automaticas.sample.csv").read_bytes())
    s = bn.run(date_str, base, log)
    assert s["dump_reference"] == "2026-10-24" and s["linhas_lidas"] == 4 and s["cnpjs"] == 2 and s["operacoes_guardadas"] == 2
    assert set(s["operacoes"]) == {"11111111000191", "11111111000272"}
    op = s["operacoes"]["11111111000191"][0]
    assert op["contratado"] == 1500000.5 and op["data"] == "2022-03-10" and op["ibge"] == "3550308" and op["cnae"] == "J6110801"
    assert read_gz(base / "normalized" / date_str / "summary" / "bndes_operacoes.json.gz")["licenca"] == "ODbL"
    assert not list((base / "raw" / "_bndes_tmp").glob("*.csv"))


@respx.mock
def test_bndes_idempotente_e_recurso_ausente(respx_mock, base, date_str, log, fx, universo):
    respx_mock.get(bn.CKAN).respond(200, content=fx("bndes_operacoes", "ckan_package_show.sample.json").read_bytes())
    rota = respx_mock.get("https://dadosabertos.bndes.gov.br/x/nao_automaticas.csv").respond(200, content=fx("bndes_operacoes", "operacoes_nao_automaticas.sample.csv").read_bytes())
    bn.run(date_str, base, log)
    bn.run(date_str, base, log)
    assert rota.call_count == 1
    respx_mock.get(bn.CKAN).respond(200, json={"result": {"resources": []}})
    with pytest.raises(RuntimeError, match="recurso"):
        bn.run(date_str, base, log, force=True)


def _zip(nome, conteudo):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr(nome, conteudo)
    return b.getvalue()


@respx.mock
def test_sancoes_descarta_pessoa_fisica_e_volta_dias(respx_mock, base, date_str, log, fx, universo):
    ceis, cnep = fx("cgu_ceis_cnep", "CEIS.sample.csv").read_bytes(), fx("cgu_ceis_cnep", "CNEP.sample.csv").read_bytes()
    respx_mock.get(cg.URL.format(cad="ceis", dia="20260920")).respond(403, text="AccessDenied")    
    respx_mock.get(cg.URL.format(cad="ceis", dia="20260919")).respond(200, content=_zip("20260919_CEIS.csv", ceis))
    respx_mock.get(cg.URL.format(cad="cnep", dia="20260920")).respond(200, content=_zip("20260920_CNEP.csv", cnep))
    s = cg.run(date_str, base, log)
    assert s["arquivos"] == {"CEIS": "2026-09-19", "CNEP": "2026-09-20"}
    assert s["linhas_lidas"] == 4 and s["linhas_pessoa_juridica"] == 3 and s["cnpjs"] == 2 and s["sancoes_guardadas"] == 2
    ceis_pj = s["sancoes"]["11111111000191"][0]
    assert ceis_pj["cadastro"] == "CEIS" and ceis_pj["inicio"] == "2024-01-10" and ceis_pj["fim"] == "2027-01-10" and "multa" not in ceis_pj
    assert s["sancoes"]["11111111000272"][0]["multa"] == 36680.49
    bruto = str(s)
    assert "12345678901" not in bruto and "PESSOA FISICA" not in bruto            # CPF e nome da pessoa física nunca são guardados
    assert "99999999000199" not in bruto


@respx.mock
def test_sancoes_sem_arquivo_falha_alto(respx_mock, base, date_str, log, universo):
    respx_mock.get(url__regex=r".*download-de-dados/ceis/.*").respond(403, text="AccessDenied")
    with pytest.raises(RuntimeError, match="nenhum arquivo"):
        cg.run(date_str, base, log)
