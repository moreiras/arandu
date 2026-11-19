# SPDX-License-Identifier: AGPL-3.0-or-later
"""T1 — SICI (Anatel): leitura incremental de ZIP remoto por HTTP Range, fixo e móvel."""
import json

import httpx
import pytest
import respx

from sources.anatel_sici import collect as anatel_sici
from sources.anatel_sici_movel import collect as anatel_sici_movel
from tests.sources.conftest import mount_range_zip, read_gz, volatile

FIXA = {
    "Acessos_Banda_Larga_Fixa_Total.csv": ("anatel_sici", "Acessos_Banda_Larga_Fixa_Total.sample.csv"),
    "Acessos_Banda_Larga_Fixa_2026.csv": ("anatel_sici", "Acessos_Banda_Larga_Fixa_2026.sample.csv"),
}
MOVEL = {
    "Acessos_Telefonia_Movel_Total.csv": ("anatel_sici_movel", "Acessos_Telefonia_Movel_Total.sample.csv"),
    "Acessos_Telefonia_Movel_2026_2S.csv": ("anatel_sici_movel", "Acessos_Telefonia_Movel_2026_2S.sample.csv"),
}


def members(fx, spec):
    return {name: fx(*path).read_bytes() for name, path in spec.items()}


# ── banda larga fixa ───────────────────────────────────────────────────────

@respx.mock
def test_sici_fixa_primeira_execucao_agrega_ano_corrente(base, log, fx, date_str):
    mount_range_zip(respx, anatel_sici.ANATEL_URL, members(fx, FIXA))
    out = anatel_sici.run(date_str, base, log)
    assert out["mes_referencia"] == "2026-07" and out["meses_disponiveis"] == ["2026-06", "2026-07"]
    assert out["total_cnpjs"] == 3 and out["total_acessos"] == 608   # inclui a linha LINHA_DEDICADA (5)
    c = out["cnpjs"]["04492527000131"]
    assert c["empresa"] == "S R Lima Eireli" and c["pf"] == 189 and c["pj"] + c["pf"] == c["acessos"]
    assert c["tecnologia_predominante"] == "FTTH" and c["meio_predominante"] == "Fibra"
    assert c["por_municipio"]["3529708"]["nome"] == "Miguelópolis"
    mun = c["por_municipio"]["3529708"]
    assert 0 < mun["fibra"] <= mun["acessos"]   # meio "Fibra" por município (% de fibra)
    assert c["velocidade_media_mbps"] == pytest.approx(264.38, abs=0.01)


@respx.mock
def test_sici_fixa_filtra_produto_e_descarta_linhas_invalidas(base, log, fx, date_str):
    mount_range_zip(respx, anatel_sici.ANATEL_URL, members(fx, FIXA))
    out = anatel_sici.run(date_str, base, log)
    c = out["cnpjs"]["04492527000131"]
    # linha LINHA_DEDICADA conta em `acessos`, mas não em `acessos_internet`
    assert c["acessos"] == c["acessos_internet"] + 5
    assert c["por_produto"]["LINHA_DEDICADA"] == 5
    assert "123" not in out["cnpjs"] and all(len(k) == 14 for k in out["cnpjs"])   # CNPJ inválido descartado


@respx.mock
def test_sici_fixa_serie_historica_por_cnpj(base, log, fx, date_str):
    mount_range_zip(respx, anatel_sici.ANATEL_URL, members(fx, FIXA))
    out = anatel_sici.run(date_str, base, log)
    serie = out["serie_por_cnpj"]["04492527000131"]
    assert [s[0] for s in serie] == ["2026-06", "2026-07"] and serie == sorted(serie)
    assert [t["mes"] for t in out["serie_total"]] == ["2026-06", "2026-07"]


@respx.mock
def test_sici_fixa_cache_e_estado_persistidos(base, log, fx, date_str):
    mount_range_zip(respx, anatel_sici.ANATEL_URL, members(fx, FIXA), etag='"abc"')
    anatel_sici.run(date_str, base, log)
    cache = base / "normalized" / "sici_cache"
    assert (cache / "months" / "2026-07.json.gz").exists() and (cache / "months" / "2026-06.json.gz").exists()
    st = json.loads((cache / "state.json").read_text())
    assert st["ultimo_mes"] == "2026-07" and st["etag"] == '"abc"'
    assert "Acessos_Banda_Larga_Fixa_2026.csv" in st["membros"]
    assert read_gz(base / "normalized" / date_str / "summary" / "sici_acessos.json.gz")["mes_referencia"] == "2026-07"


@respx.mock
def test_sici_fixa_sem_mes_novo_nao_baixa_o_membro_anual(base, log, fx, date_str):
    calls = mount_range_zip(respx, anatel_sici.ANATEL_URL, members(fx, FIXA))
    a = anatel_sici.run(date_str, base, log)
    n_first = len(calls)
    calls.clear()
    b = anatel_sici.run("2026-09-27", base, log)
    assert len(calls) < n_first                       # só HEAD + cauda + sentinela
    assert volatile(a["cnpjs"]) == volatile(b["cnpjs"]) and a["mes_referencia"] == b["mes_referencia"]


@respx.mock
def test_sici_fixa_force_full_reprocessa(base, log, fx, date_str):
    calls = mount_range_zip(respx, anatel_sici.ANATEL_URL, members(fx, FIXA))
    anatel_sici.run(date_str, base, log)
    calls.clear()
    anatel_sici.run("2026-09-27", base, log, force_full=True)
    assert len(calls) >= 5


@respx.mock
def test_sici_fixa_sentinela_sem_dados_levanta(base, log, fx, date_str):
    m = members(fx, FIXA)
    m["Acessos_Banda_Larga_Fixa_Total.csv"] = b"Ano;M\xc3\xaas;Acessos\n"
    mount_range_zip(respx, anatel_sici.ANATEL_URL, m)
    with pytest.raises(RuntimeError, match="último mês"):
        anatel_sici.run(date_str, base, log)


@respx.mock
def test_sici_fixa_sem_membro_do_ano_levanta(base, log, fx, date_str):
    m = members(fx, FIXA)
    m.pop("Acessos_Banda_Larga_Fixa_2026.csv")
    mount_range_zip(respx, anatel_sici.ANATEL_URL, m)
    with pytest.raises(RuntimeError, match="membro do ano 2026"):
        anatel_sici.run(date_str, base, log)


@respx.mock
def test_sici_fixa_coluna_obrigatoria_ausente_levanta(base, log, fx, date_str):
    m = members(fx, FIXA)
    m["Acessos_Banda_Larga_Fixa_2026.csv"] = "Ano;Mês;Empresa\n2026;7;X\n".encode("utf-8")
    mount_range_zip(respx, anatel_sici.ANATEL_URL, m)
    with pytest.raises(RuntimeError, match="colunas obrigatórias"):
        anatel_sici.run(date_str, base, log)


@respx.mock
def test_sici_fixa_http_erro(base, log, date_str):
    respx.head(anatel_sici.ANATEL_URL).respond(503)
    with pytest.raises(httpx.HTTPStatusError):
        anatel_sici.run(date_str, base, log)


@pytest.mark.parametrize("nome, esperado", [
    ("Acessos_Banda_Larga_Fixa_2026.csv", True),
    ("Acessos_Banda_Larga_Fixa_2007-2010.csv", True),
    ("Acessos_Banda_Larga_Fixa_Colunas.csv", False),
    ("Acessos_Banda_Larga_Fixa_Total.csv", False),
])
def test_sici_fixa_regex_de_membro(nome, esperado):
    assert bool(anatel_sici._MEMBER_RE.match(nome)) is esperado


def test_sici_detail_window_cruza_ano():
    w = anatel_sici._detail_window("2026-02")
    assert len(w) == 12 and "2026-02" in w and "2025-03" in w and "2025-02" not in w


@pytest.mark.parametrize("pares, esperado", [
    ([], 0.0),
    ([(100.0, 1)], 100.0),
    ([(10.0, 1), (100.0, 1), (1000.0, 1)], 100.0),
    ([(10.0, 9), (1000.0, 1)], 10.0),
])
def test_sici_mediana_ponderada(pares, esperado):
    assert anatel_sici._weighted_median(pares) == esperado


# ── telefonia móvel ────────────────────────────────────────────────────────

@respx.mock
def test_sici_movel_exclui_m2m_e_ponto_de_servico_do_total(base, log, fx, date_str):
    mount_range_zip(respx, anatel_sici_movel.ANATEL_URL, members(fx, MOVEL))
    out = anatel_sici_movel.run(date_str, base, log)
    assert out["mes_referencia"] == "2026-07"
    c = out["cnpjs"]["51042993000103"]
    assert c["acessos"] == 873 and c["pf"] == 873 and c["pj"] == 0     # só VOZ+DADOS conta
    assert c["acessos_m2m"] == 160921 and c["por_produto"]["M2M"] == 160921
    assert c["geracao_predominante"] == "4G"
    infra = out["cnpjs"]["11111111000191"]
    assert infra["acessos"] == 0 and infra["acessos_outros"] == 7


@respx.mock
def test_sici_movel_distribuicao_por_modalidade_so_acesso_padrao(base, log, fx, date_str):
    mount_range_zip(respx, anatel_sici_movel.ANATEL_URL, members(fx, MOVEL))
    out = anatel_sici_movel.run(date_str, base, log)
    dist = out["distrib_modalidade"]
    assert dist["SP"]["pf"] == {"Pós-pago": 873}
    assert "MG" not in dist                            # só havia M2M


@respx.mock
def test_sici_movel_segunda_execucao_nao_reprocessa(base, log, fx, date_str):
    calls = mount_range_zip(respx, anatel_sici_movel.ANATEL_URL, members(fx, MOVEL))
    anatel_sici_movel.run(date_str, base, log)
    n = len(calls)
    calls.clear()
    anatel_sici_movel.run("2026-09-27", base, log)
    assert len(calls) < n


@pytest.mark.parametrize("nome, esperado", [
    ("Acessos_Telefonia_Movel_2026_2S.csv", True),
    ("Acessos_Telefonia_Movel_2019_1S.csv", True),
    ("Acessos_Telefonia_Movel_2005-2018_Modalidade.csv", False),
    ("Acessos_Telefonia_Movel_2026_2S_Colunas.csv", False),
])
def test_sici_movel_regex_de_membro(nome, esperado):
    assert bool(anatel_sici_movel._MEMBER_RE.match(nome)) is esperado
