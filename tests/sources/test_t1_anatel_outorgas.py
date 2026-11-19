# SPDX-License-Identifier: AGPL-3.0-or-later
"""T1 — outorgas da Anatel (SCM, SMP, STFC, SeAC): um CSV, quatro filtros por serviço."""
import gzip

import httpx
import pytest
import respx

from sources.anatel_outorgas import servicos
from sources.anatel_scm import collect as anatel_scm
from sources.anatel_seac import collect as anatel_seac
from sources.anatel_smp import collect as anatel_smp
from sources.anatel_stfc import collect as anatel_stfc
from tests.sources.conftest import make_zip, read_gz, volatile

CSV = "prestadoras_servicos_telecomunicacoes.sample.csv"
MEMBER = "prestadoras_servicos_telecomunicacoes.csv"


@pytest.fixture()
def zip_bytes(fx):
    return make_zip(MEMBER, fx("anatel_outorgas", CSV).read_bytes())


# módulo, chave da lista, CNPJs esperados (já filtrados por serviço), nº de registros
CASES = [
    (anatel_scm, "scms", {"19438160000145", "17131007000145", "18362941000130", "04422276000119"}, 4),
    (anatel_stfc, "stfcs", {"07764308000152"}, 2),
    (anatel_seac, "seacs", {"25535315000164", "42569060000170"}, 2),
]


@pytest.mark.parametrize("mod, key, cnpjs, total", CASES, ids=lambda x: getattr(x, "__name__", None) or None)
@respx.mock
def test_filtra_pelo_servico_e_normaliza(mod, key, cnpjs, total, base, log, zip_bytes, date_str):
    respx.get(mod.ANATEL_URL).respond(200, content=zip_bytes)
    r = mod.run(date_str, base, log)
    assert r["total"] == total and {x["cnpj"] for x in r[key]} == cnpjs
    assert r["unique_cnpjs"] == len(cnpjs) and set(r["by_cnpj"]) == cnpjs
    rec = r[key][0]
    assert len(rec["cnpj"]) == 14 and rec["razao_social"] and rec["uf"] and len(rec["cep"]) == 8
    assert rec["email"] == "contato@example.org"      # dado cadastral mascarado na amostra


@respx.mock
def test_smp_filtra_010_e_exclui_satelite(base, log, zip_bytes, date_str, monkeypatch):
    respx.get(anatel_smp.ANATEL_URL).respond(200, content=zip_bytes)
    respx.get(anatel_smp.ANATEL_REDE_VIRTUAL_URL).respond(404)   # enriquecimento é opcional
    r = anatel_smp.run(date_str, base, log)
    assert {x["cnpj"] for x in r["smps"]} == {"71208516000174"} and r["total"] == 2
    assert "53107768000125" not in r["by_cnpj"]       # 110 — SMP por satélite


@respx.mock
def test_smp_aplica_rede_virtual_vigente(base, log, zip_bytes, fx, date_str):
    respx.get(anatel_smp.ANATEL_URL).respond(200, content=zip_bytes)
    contratos = make_zip("contratos_mvno.csv", fx("anatel_outorgas", "contratos_mvno.sample.csv").read_bytes())
    respx.get(anatel_smp.ANATEL_REDE_VIRTUAL_URL).respond(200, content=contratos)
    r = anatel_smp.run(date_str, base, log)
    por = {x["cnpj"]: x for x in r["smps"]}
    # ALGAR tem outorga SMP própria e é credenciada do contrato vigente
    assert por["71208516000174"]["rede_virtual"]["papel"] == "credenciada"
    # credenciadas sem outorga própria entram como registros sintéticos
    sint = por["04601397000128"]
    assert sint["situacao"].startswith("Credenciada de Rede Virtual") and sint["data_outorga"] == ""
    # contrato encerrado não gera registro
    assert "11111111000111" not in por


@respx.mock
def test_smp_falha_da_rede_virtual_nao_derruba_coleta(base, log, zip_bytes, date_str):
    respx.get(anatel_smp.ANATEL_URL).respond(200, content=zip_bytes)
    respx.get(anatel_smp.ANATEL_REDE_VIRTUAL_URL).mock(side_effect=httpx.ConnectError("sem rede"))
    r = anatel_smp.run(date_str, base, log)
    assert r["total"] == 2 and "rede_virtual" not in r["smps"][0]


@pytest.mark.parametrize("mod", [anatel_scm, anatel_smp, anatel_stfc, anatel_seac], ids=lambda m: m.__name__)
@respx.mock
def test_grava_csv_bruto_e_normalizado(mod, base, log, zip_bytes, fx, date_str):
    respx.get(mod.ANATEL_URL).respond(200, content=zip_bytes)
    if mod is anatel_smp:
        respx.get(anatel_smp.ANATEL_REDE_VIRTUAL_URL).respond(404)
    mod.run(date_str, base, log)
    name = mod.__name__.split(".")[-2].replace("anatel_", "")      # sources.<id>.collect
    assert gzip.decompress((base / "raw" / date_str / "summary" / f"anatel-outorgas-{date_str}.csv.gz").read_bytes()) == fx("anatel_outorgas", CSV).read_bytes()
    assert read_gz(base / "normalized" / date_str / "summary" / f"anatel_{name}.json.gz")["snapshot_date"] == date_str


@pytest.mark.parametrize("mod", [anatel_scm, anatel_stfc, anatel_seac], ids=lambda m: m.__name__)
@respx.mock
def test_zip_sem_csv_levanta(mod, base, log, date_str):
    respx.get(mod.ANATEL_URL).respond(200, content=make_zip("leiame.txt", b"nada"))
    with pytest.raises(RuntimeError, match="Nenhum .csv"):
        mod.run(date_str, base, log)


@pytest.mark.parametrize("mod", [anatel_scm, anatel_stfc, anatel_seac], ids=lambda m: m.__name__)
@respx.mock
def test_http_503_levanta_e_nao_grava_normalizado(mod, base, log, date_str):
    respx.get(mod.ANATEL_URL).respond(503)
    with pytest.raises(httpx.HTTPStatusError):
        mod.run(date_str, base, log)
    assert not list(base.rglob("*.json.gz"))


@respx.mock
def test_execucao_repetida_e_deterministica(base, log, zip_bytes, date_str):
    respx.get(anatel_scm.ANATEL_URL).respond(200, content=zip_bytes)
    assert volatile(anatel_scm.run(date_str, base, log)) == volatile(anatel_scm.run(date_str, base, log))


# ── parsers (cabeçalhos e codificações) ────────────────────────────────────

def test_scm_aceita_latin1_e_delimitador_virgula():
    csv_bytes = ("CNPJ ou CPF,Nome Entidade Prestadora de Serviço,Código e Nome do Serviço da Notificação,UF do Endereço Sede\n"
                 "12.345.678/0001-95,Provedor Açu Ltda,045 - Serviço de Comunicação Multimídia,SP\n").encode("latin-1")
    r = anatel_scm._parse_csv(csv_bytes)
    assert len(r) == 1
    assert r[0]["cnpj"] == "12345678000195" and r[0]["razao_social"] == "Provedor Açu Ltda" and r[0]["uf"] == "SP"


def test_scm_descarta_cpf_e_linha_vazia():
    t = ("CNPJ ou CPF;Nome Entidade Prestadora de Serviço;Código e Nome do Serviço da Notificação\n"
         "12345678909;Pessoa;045 - SCM\n;;\n12345678000195;Empresa;045 - SCM\n")
    r = anatel_scm._parse_csv(t.encode())
    assert [x["cnpj"] for x in r] == ["12345678000195"]


@pytest.mark.parametrize("val, esperado", [
    ("045 - Serviço de Comunicação Multimídia", True),
    ("45", True),
    ("047 - Serviço de Comunicação Multimídia - Est. Terrena", True),   # casa por texto "multim"
    ("046 - Radioenlaces associados ao SCM", False),
    ("171 - STFC", False),
    ("", False),
])
def test_scm_is_scm_row(val, esperado):
    assert anatel_scm.SERVICO.pertence(val) is esperado


@pytest.mark.parametrize("val, esperado", [
    ("010 - SERVIÇO MOVEL PESSOAL", True),
    ("110 - Serviço Móvel Pessoal por Satélite", False),
    ("020 - SERVIÇO MOVEL ESPECIALIZADO", False),
])
def test_smp_is_smp_row(val, esperado):
    assert anatel_smp.SERVICO.pertence(val) is esperado


@pytest.mark.parametrize("val, esperado", [
    ("171 - SERVICO TELEFONICO FIXO COMUTADO", True),
    ("175 - STFC/RADIOTELEFONICO - ESTACOES TERRESTRES", False),
    ("176 - STFC/RADIOTELEFONICO - ESTACOES TERRENAS", False),
])
def test_stfc_is_stfc_row(val, esperado):
    assert anatel_stfc.SERVICO.pertence(val) is esperado


@pytest.mark.parametrize("val, esperado", [
    ("750 - Serviço de Acesso Condicionado", True),
    ("167 - ESPECIAL DE TELEVISAO POR ASSINATURA", False),
])
def test_seac_is_seac_row(val, esperado):
    assert anatel_seac.SERVICO.pertence(val) is esperado


@pytest.mark.parametrize("raw, esperado", [("12.345.678/0001-95", "12345678000195"), ("123", ""), ("", ""), ("12345678909", "")])
def test_clean_cnpj(raw, esperado):
    assert servicos._clean_cnpj(raw) == esperado


@pytest.mark.parametrize("raw, esperado", [("96506-630", "96506630"), ("123", ""), (None, "")])
def test_clean_cep(raw, esperado):
    assert servicos._clean_cep(raw) == esperado


@respx.mock
def test_as_quatro_fontes_baixam_o_zip_uma_so_vez_por_data(base, log, zip_bytes, date_str):
    """SCM, SMP, STFC e SeAC leem o mesmo arquivo; o download é um só e os filtros seguem por serviço."""
    from sources.anatel_outorgas.download import ANATEL_URL, arquivo_bruto
    rota = respx.get(ANATEL_URL).respond(200, content=zip_bytes)
    respx.get(anatel_smp.ANATEL_REDE_VIRTUAL_URL).respond(404)
    r = {m.__name__: m.run(date_str, base, log) for m in (anatel_scm, anatel_smp, anatel_stfc, anatel_seac)}
    assert rota.call_count == 1
    assert r["sources.anatel_scm.collect"]["total"] == 4 and r["sources.anatel_seac.collect"]["total"] == 2
    assert arquivo_bruto(base, date_str).stat().st_size < len(zip_bytes) * 2


@respx.mock
def test_download_com_falha_nao_deixa_bruto_parcial(base, log, date_str):
    from sources.anatel_outorgas.download import ANATEL_URL, arquivo_bruto
    respx.get(ANATEL_URL).respond(503)
    with pytest.raises(httpx.HTTPStatusError):
        anatel_scm.run(date_str, base, log)
    assert not arquivo_bruto(base, date_str).exists()
