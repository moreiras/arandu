# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — Contratos públicos (Compras.gov.br / PNCP): rodízio por fornecedor, janela incremental, herança com idade, enriquecimento e parada por bloqueio, sem rede (respx)."""
import datetime as _dt
import json

import httpx
import pytest
import respx

from core import siasg
from core.common import read_json_gz, write_json_gz
from sources.siasg_contratos import collect as fonte

F_A, F_VAZIO, F_B = "11222333", "44555666", "77888999"


@pytest.fixture(autouse=True)
def _sem_aprofundamento_por_padrao(monkeypatch):
    """Os testes de primeira leitura e rodízio medem uma coisa por vez; o aprofundamento tem testes próprios (`monkeypatch.setenv("SIASG_APROFUNDAR", "1")`)."""
    monkeypatch.setenv("SIASG_APROFUNDAR", "0")


def _cnpj(raiz):
    return siasg.cnpj_matriz(raiz)


def test_cnpj_da_matriz_tem_digitos_verificadores_validos():
    assert siasg.cnpj_matriz("02558157") == "02558157000162"      # Telefônica Brasil (CNPJ público)
    with pytest.raises(ValueError):
        siasg.cnpj_matriz("123")


@pytest.fixture
def entrada(base):
    """Universo: A = declara acessos no SICI; B = só outorga; 44555666 é A sem nenhum resultado."""
    def grava(d):
        norm = base / "normalized" / d / "summary"
        norm.mkdir(parents=True, exist_ok=True)
        write_json_gz(norm / "anatel_scm.json.gz", {"by_cnpj": {_cnpj(F_A): {}, _cnpj(F_VAZIO): {}, _cnpj(F_B): {}}})
        write_json_gz(norm / "sici_acessos.json.gz", {"cnpjs": {_cnpj(F_A): {"acessos": 10}, _cnpj(F_VAZIO): {"acessos": 3}, _cnpj(F_B): {"acessos": 0}}})
    return grava


@pytest.fixture
def api(fx):
    """Simula a API; devolve a lista de (caminho, parâmetros) pedidos. `api.modo` troca o comportamento (ok, 403, html, 500)."""
    class Pedidos(list):
        estado: dict

    pedidos = Pedidos()
    estado = {"modo": "ok"}

    def js(*partes):
        return json.loads(fx("siasg_contratos", *partes).read_text(encoding="utf-8"))

    def despachar(request: httpx.Request):
        p = dict(request.url.params)
        c = request.url.path
        pedidos.append((c, p))
        assert "arandurape" in request.headers["user-agent"]
        if estado["modo"] == "403":
            return httpx.Response(403, text="forbidden")
        if estado["modo"] == "html":
            return httpx.Response(200, text="<html>Verifique que você é humano</html>")
        if estado["modo"] == "500":
            return httpx.Response(503, text="indisponível")
        if c == siasg.ENDPOINT_RESULTADOS:
            ni = p["niFornecedor"]
            assert len(ni) == 14 and p["dataResultadoPncpInicial"] and p["dataResultadoPncpFinal"] and p["tamanhoPagina"] == "500"
            dias = (_dt.date.fromisoformat(p["dataResultadoPncpFinal"]) - _dt.date.fromisoformat(p["dataResultadoPncpInicial"])).days
            if dias > 365:      # limite real da API (HTTP 400): uma consulta desde 2021 nunca passaria
                return httpx.Response(400, json={"title": "Período inicial e final maior que 365 dias.", "status": 400, "maxPeriod": "365 dias"})
            if ni == _cnpj(F_A):
                return httpx.Response(200, json=js(f"resultados_{F_A}_{p['pagina']}.json"))
            if ni == _cnpj(F_B):
                return httpx.Response(200, json=js(f"resultados_{F_B}_1.json"))
            return httpx.Response(200, json=js("resultados_vazio.json"))
        if c == siasg.ENDPOINT_COMPRA:
            return httpx.Response(200, json=js("compras.json")[p["codigo"]])
        if c == "/modulo-uasg/1_consultarUasg":
            return httpx.Response(200, json=js(f"uasg_{p['pagina']}.json"))
        raise AssertionError(c)

    with respx.mock(base_url=siasg.BASE_URL, assert_all_called=False) as m:
        m.route().mock(side_effect=despachar)
        pedidos.estado = estado
        yield pedidos


def _doc(base, d):
    return read_json_gz(base / "normalized" / d / "summary" / "siasg_contratos.json.gz")


def _run(base, log, d, **kw):
    kw.setdefault("espera_s", 0)
    return fonte.run(d, base, log, **kw)


def test_universo_em_faixas(base, entrada, log):
    entrada("2026-11-10")
    assert fonte.universo(base, "2026-11-10") == {F_A: "A", F_VAZIO: "A", F_B: "B"}


def test_janelas_cobrem_o_periodo_sem_passar_de_360_dias_nem_sobrepor():
    js = siasg.janelas("2023-11-26", "2026-11-10")
    assert js[0][0] == "2023-11-26" and js[-1][1] == "2026-11-10"
    assert all((_dt.date.fromisoformat(b) - _dt.date.fromisoformat(a)).days <= 359 for a, b in js)
    assert all(_dt.date.fromisoformat(js[i + 1][0]) == _dt.date.fromisoformat(js[i][1]) + _dt.timedelta(days=1) for i in range(len(js) - 1))
    assert siasg.janelas("2026-11-10", "2026-11-10") == [("2026-11-10", "2026-11-10")]
    assert siasg.janelas("2026-11-11", "2026-11-10") == []
    assert siasg.inicio_primeira_leitura("2026-11-10") == "2025-11-16"                  # 1 janela de 360 dias (padrão)
    assert siasg.inicio_primeira_leitura("2026-11-10", 3) == "2023-11-27"               # 3 janelas
    assert siasg.inicio_primeira_leitura("2022-01-01") == siasg.JANELA_INICIO           # nunca antes da Lei 14.133


def test_universo_inclui_so_cnae_principal_ativa_da_receita_como_faixa_c(base, entrada, log, monkeypatch):
    """Com CNAE 61 em qualquer posição a Receita traz ~585 mil raízes (medido em 2026-11-06), inviável para uma consulta por raiz; a faixa C é só a atividade principal ativa (~44 mil além das outorgas e do SICI)."""
    entrada("2026-11-10")
    write_json_gz(base / "normalized" / "2026-11-10" / "summary" / "receita_cnpj.json.gz", {"estabelecimentos": {"99000111": [{"p": "6190601", "s": "02"}], "99000222": [{"p": "4711302", "x": ["6190601"]}]}})
    u = fonte.universo(base, "2026-11-10")
    assert set(u) == {F_A, F_VAZIO, F_B, "99000111"} and u["99000111"] == "C"                 # CNAE 61 principal e ativo, sem outorga nem SICI: faixa C
    assert "99000222" not in u                                                              # CNAE 61 só como atividade secundária: fora
    monkeypatch.setenv("SIASG_COM_CNAE_PRINCIPAL", "0")
    assert set(fonte.universo(base, "2026-11-10")) == {F_A, F_VAZIO, F_B}


def test_primeira_rodada_le_so_a_janela_mais_recente_e_so_pessoa_juridica(base, entrada, log, api):
    entrada("2026-11-10")
    m = _run(base, log, "2026-11-10")
    d = _doc(base, "2026-11-10")
    f = d["fornecedores"][F_A]
    assert f["cnpj"] == _cnpj(F_A) and f["lida_em"] == "2026-11-10" and f["desde"] == siasg.inicio_primeira_leitura("2026-11-10")
    assert [i["id"] for i in f["itens"]] == ["90000100001", "90000100002", "90000200001", "90000300001"]      # o item de pessoa física (CPF) ficou de fora
    assert all(len(i["cnpj"]) == 14 for i in f["itens"])
    assert d["fornecedores"][F_VAZIO]["itens"] == [] and d["fornecedores"][F_VAZIO]["lida_em"] == "2026-11-10"      # ausência registrada, não omitida
    inicios = {p["dataResultadoPncpInicial"] for c, p in api if c == siasg.ENDPOINT_RESULTADOS}
    assert inicios == {siasg.inicio_primeira_leitura("2026-11-10")}                                                   # só a janela mais recente (360 dias)
    assert sum(1 for c, p in api if c == siasg.ENDPOINT_RESULTADOS and p["niFornecedor"] == _cnpj(F_A)) == 2      # duas páginas
    assert m["fornecedores_lidos"] == 3 and m["raizes_sem_leitura"] == 0 and m["parada"] is None


def test_enriquece_contratacoes_em_ordem_de_valor_e_resume_o_objeto(base, entrada, log, api):
    entrada("2026-11-10")
    m = _run(base, log, "2026-11-10", compras_por_execucao=2)
    d = _doc(base, "2026-11-10")
    # maiores valores: 20.000 (000002/2026), 12.000 (000001/2025); o item cancelado não conta, o de 900 e o de 300 ficam para depois
    assert sorted(d["compras"]) == ["00000000000191-1-000001/2025", "00000000000272-1-000002/2026"]
    c = d["compras"]["00000000000272-1-000002/2026"]
    assert c["esfera"] == "estadual" and c["municipio"] == "SÃO PAULO" and c["ibge"] == "3550308" and c["modalidade"] == "Dispensa"
    assert "\n" not in c["objeto"] and "  " not in c["objeto"] and len(c["objeto"]) <= siasg.OBJETO_MAX + 1 and c["objeto"].endswith("…")
    assert m["contratacoes_enriquecidas"] == 2 and m["contratacoes_sem_detalhe"] == 2
    entrada("2026-11-11")
    _run(base, log, "2026-11-11", compras_por_execucao=10)
    assert len(_doc(base, "2026-11-11")["compras"]) == 4


def test_tabela_de_unidades_com_municipio_e_renovada_so_depois_de_30_dias(base, entrada, log, api):
    entrada("2026-11-10")
    _run(base, log, "2026-11-10", compras_por_execucao=0)
    d = _doc(base, "2026-11-10")
    assert d["uasg_em"] == "2026-11-10" and d["uasg"]["900003"]["ibge"] == "3106200" and d["uasg"]["900002"]["municipio"] == "SÃO PAULO"
    n = sum(1 for c, _ in api if c == "/modulo-uasg/1_consultarUasg")
    entrada("2026-11-11")
    _run(base, log, "2026-11-11", compras_por_execucao=0)
    assert sum(1 for c, _ in api if c == "/modulo-uasg/1_consultarUasg") == n
    entrada("2026-12-11")
    _run(base, log, "2026-12-11", compras_por_execucao=0)
    assert sum(1 for c, _ in api if c == "/modulo-uasg/1_consultarUasg") == 2 * n


def test_rodizio_respeita_o_limite_e_herda_com_a_data_da_leitura(base, entrada, log, api):
    entrada("2026-11-10")
    r1 = _run(base, log, "2026-11-10", fornecedores_por_execucao=2, compras_por_execucao=0)
    d1 = _doc(base, "2026-11-10")
    assert sorted(d1["fornecedores"]) == [F_A, F_VAZIO] and r1["raizes_sem_leitura"] == 1       # a faixa A vem antes da B
    entrada("2026-11-11")
    _run(base, log, "2026-11-11", fornecedores_por_execucao=2, compras_por_execucao=0)
    d2 = _doc(base, "2026-11-11")
    assert sorted(d2["fornecedores"]) == [F_A, F_VAZIO, F_B]
    assert d2["fornecedores"][F_B]["lida_em"] == "2026-11-11" and not d2["fornecedores"][F_B].get("herdado")
    assert d2["fornecedores"][F_A]["lida_em"] == "2026-11-10" and d2["fornecedores"][F_A]["herdado"] is True       # ainda não devida (intervalo de 7 dias): herdada, com a data original


def test_faixa_a_volta_depois_de_7_dias_com_janela_incremental(base, entrada, log, api):
    entrada("2026-11-10")
    _run(base, log, "2026-11-10", compras_por_execucao=0)
    api.clear()
    entrada("2026-11-17")
    m = _run(base, log, "2026-11-17", compras_por_execucao=0)
    lidos = {p["niFornecedor"]: p for c, p in api if c == siasg.ENDPOINT_RESULTADOS}
    assert set(lidos) == {_cnpj(F_A), _cnpj(F_VAZIO)}                     # B só volta em 56 dias
    assert lidos[_cnpj(F_A)]["dataResultadoPncpInicial"] == "2026-09-26"  # 45 dias antes da última leitura (2026-11-10)
    assert m["fornecedores_lidos_faixa_a"] == 2
    f = _doc(base, "2026-11-17")["fornecedores"][F_A]
    assert len(f["itens"]) == 4 and f["lida_em"] == "2026-11-17"          # mescla pela chave do item: sem duplicar o que a janela repete


def test_orcamento_de_requisicoes_para_a_rodada(base, entrada, log, api):
    entrada("2026-11-10")
    m = _run(base, log, "2026-11-10", orcamento_requisicoes=3, compras_por_execucao=0)
    assert m["requisicoes_gastas"] >= 3 and "orçamento" in m["parada"]
    assert m["raizes_sem_leitura"] >= 1                                    # o resto fica para a próxima rodada


def test_bloqueio_para_a_rodada_na_hora_mas_guarda_o_que_foi_lido(base, entrada, log, api):
    entrada("2026-11-10")
    _run(base, log, "2026-11-10", fornecedores_por_execucao=1, compras_por_execucao=0)
    api.estado["modo"] = "403"
    entrada("2026-11-17")
    m = _run(base, log, "2026-11-17", compras_por_execucao=0)
    assert m["bloqueio"] is True and "403" in m["parada"]
    assert sum(1 for c, _ in api if c == siasg.ENDPOINT_RESULTADOS) == 3       # 1 da primeira rodada (uma janela, duas páginas) e 1 tentativa que levou 403
    d = _doc(base, "2026-11-17")
    assert d["fornecedores"][F_A]["herdado"] is True                       # estado anterior intacto


def test_resposta_que_nao_e_json_conta_como_bloqueio(base, entrada, log, api):
    entrada("2026-11-10")
    api.estado["modo"] = "html"
    m = _run(base, log, "2026-11-10", compras_por_execucao=0)
    assert m["bloqueio"] is True and "JSON" in m["parada"]


def test_erro_5xx_nao_marca_leitura_e_aborta_depois_de_falhas_seguidas(base, entrada, log, api):
    entrada("2026-11-10")
    api.estado["modo"] = "500"
    m = _run(base, log, "2026-11-10", compras_por_execucao=0)
    d = _doc(base, "2026-11-10")
    assert d["fornecedores"] == {} and m["raizes_sem_leitura"] == 3 and m["falhas"] >= 1       # nada foi lido: continua devido na próxima rodada


def test_main_devolve_3_no_bloqueio(base, entrada, log, api, monkeypatch):
    entrada("2026-11-10")
    api.estado["modo"] = "403"
    monkeypatch.setenv("DATA_DIR", str(base))
    monkeypatch.setattr(fonte, "ESPERA_S", 0)
    assert fonte.main(["--date", "2026-11-10", "--compras", "0"]) == 3


def test_primeira_leitura_pode_voltar_varias_janelas(base, entrada, log, api, monkeypatch):
    monkeypatch.setenv("SIASG_JANELAS_INICIAIS", "3")
    entrada("2026-11-10")
    _run(base, log, "2026-11-10", fornecedores_por_execucao=1, compras_por_execucao=0)
    inicios = {p["dataResultadoPncpInicial"] for c, p in api if c == siasg.ENDPOINT_RESULTADOS}
    assert len(inicios) == 3 and min(inicios) == siasg.inicio_primeira_leitura("2026-11-10", 3)       # nenhuma janela acima de 365 dias: a API simulada recusaria


def test_aprofundamento_le_uma_janela_mais_antiga_por_visita_ate_a_lei_14133(base, entrada, log, api, monkeypatch):
    """Todas as raízes recebem primeiro a janela mais recente; com o orçamento que sobra, cada visita traz mais uma janela para trás, da faixa A para a C."""
    monkeypatch.setenv("SIASG_APROFUNDAR", "1")
    entrada("2026-11-10")
    m = _run(base, log, "2026-11-10", compras_por_execucao=0)
    d = _doc(base, "2026-11-10")
    primeira = siasg.inicio_primeira_leitura("2026-11-10")
    assert d["fornecedores"][F_A]["desde"] < primeira and m["raizes_aprofundadas"] == 3          # nesta mesma rodada: uma janela a mais para cada raiz lida
    desde = d["fornecedores"][F_A]["desde"]
    for dia in ("2026-11-11", "2026-11-12", "2026-11-13", "2026-11-14", "2026-11-15"):
        entrada(dia)
        _run(base, log, dia, compras_por_execucao=0)
        novo = _doc(base, dia)["fornecedores"][F_A]["desde"]
        assert novo <= desde
        desde = novo
    assert desde == siasg.JANELA_INICIO                                                        # chegou ao início da Lei 14.133 e para
    n = sum(1 for c, p in api if c == siasg.ENDPOINT_RESULTADOS)
    entrada("2026-11-16")
    _run(base, log, "2026-11-16", compras_por_execucao=0)
    assert sum(1 for c, p in api if c == siasg.ENDPOINT_RESULTADOS and p["dataResultadoPncpInicial"] < "2021-04-01") == 0
    assert all(p["dataResultadoPncpInicial"] >= siasg.JANELA_INICIO for c, p in api if c == siasg.ENDPOINT_RESULTADOS)
    assert n > 0


def test_candidatas_ao_aprofundamento_vao_da_faixa_a_para_a_c():
    regs = {"1": {"desde": "2025-01-01"}, "2": {"desde": "2025-01-01", "aprofundada_em": "2026-11-01"}, "3": {"desde": "2025-01-01"}, "4": {"desde": siasg.JANELA_INICIO}, "5": {"desde": "2025-01-01", "incompleto": True}}
    faixas = {"1": "C", "2": "A", "3": "A", "4": "A", "5": "A", "6": "A"}
    assert fonte.candidatas_ao_aprofundamento(faixas, regs) == ["3", "2", "1"]            # A primeiro (a nunca aprofundada antes), depois C; sem as que já chegaram à Lei, as incompletas e as sem leitura
