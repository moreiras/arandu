# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — Shodan, exposição por ASN: consultas A/B/C, rodízio, plano sem `vuln`, 401, 429 e rede, sem rede (respx, respostas sintéticas) e sem vazar a chave."""
import json
import logging

import httpx
import pytest
import respx

from core import shodan
from core.common import read_json_gz, write_json_gz
from sources.shodan_exposicao import collect as fonte

CHAVE = "chave-sintetica-de-teste-0123456789"


@pytest.fixture
def resp(fx):
    def _r(nome, status=200):
        return httpx.Response(status, json=json.loads(fx("shodan_exposicao", nome).read_text(encoding="utf-8")))
    return _r


def _universo(tmp_path, asns, data="2026-11-10"):
    write_json_gz(tmp_path / "normalized" / data / "summary" / "orgs.json.gz", {"orgs": {str(a): {"name": "x"} for a in asns}})


def _doc(tmp_path, d):
    return read_json_gz(tmp_path / "normalized" / d / "summary" / "shodan_exposicao.json.gz")


def _run(tmp_path, log, d, **kw):
    kw.setdefault("intervalo_s", 0)
    kw.setdefault("dormir", lambda s: None)
    kw.setdefault("chave", CHAVE)
    return fonte.run(d, tmp_path, log, **kw)


def _mock(resp, vuln=None, vazio=(64497,), extra=None, creditos=None):
    """Simula o Shodan; `vuln`: None = permite, ou um status (ex.: 403) para a faceta vuln; `extra(asn, kind)` pode devolver Response/Exception."""
    pedidos: list[tuple[int, str]] = []

    def despachar(request: httpx.Request):
        p = dict(request.url.params)
        assert p["key"] == CHAVE
        if request.url.path == "/api-info":
            if creditos:
                return httpx.Response(200, json={"plan": "exemplo", "query_credits": creditos.pop(0), "scan_credits": 1})
            return resp("api_info.json")
        asn = int(p["query"].split("asn:AS")[1].split()[0])
        kind = "risco" if " port:" in p["query"] else ("vuln" if p.get("facets", "").startswith("vuln") else "geral")
        pedidos.append((asn, kind))
        if extra and (r := extra(asn, kind)) is not None:
            if isinstance(r, Exception):
                raise r
            return r
        if kind == "geral":
            return resp("geral_vazio.json") if asn in vazio else resp("geral_64496.json")
        if kind == "risco":
            return resp("risco_64496.json")
        return resp("erro_plano.json", vuln) if vuln else resp("vuln_64496.json")

    m = respx.mock(base_url=shodan.BASE_URL, assert_all_called=False)
    m.route().mock(side_effect=despachar)
    return m, pedidos


def test_rodada_guarda_so_contagens_e_nao_vaza_a_chave(tmp_path, log, resp, caplog):
    _universo(tmp_path, [64496, 64497])
    m, pedidos = _mock(resp)
    with caplog.at_level(logging.DEBUG), m:
        med = _run(tmp_path, log, "2026-11-10")
    assert pedidos == [(64496, "geral"), (64496, "risco"), (64496, "vuln"), (64497, "geral")]      # ASN sem serviço não gasta B nem C
    assert med["asns_lidos"] == 2 and med["requisicoes"] == 4 and med["parou"] is None and med["vuln"] == "ok"
    d = _doc(tmp_path, "2026-11-10")
    a = d["asns"]["64496"]
    assert a["total"] == 400 and a["em"] == "2026-11-10" and a["portas"][:3] == [[80, 220], [443, 120], [23, 40]]
    assert a["risco"] == {"23": 40, "7547": 9, "3389": 2} and a["risco_total"] == 51 and a["vulns"] == [["CVE-2099-0001", 12], ["CVE-2099-0002", 5]]
    assert d["asns"]["64497"]["total"] == 0 and d["asns"]["64497"]["vulns"] is None
    assert d["cobertura"] == {"com_leitura": 2, "com_servicos": 1, "leitura_mais_antiga": "2026-11-10", "leitura_mais_recente": "2026-11-10"}
    texto = json.dumps(d) + caplog.text
    assert CHAVE not in texto and "key=" not in texto and "matches" not in texto            # a chave nunca vai a arquivo nem a log; nenhum host


def test_plano_sem_vuln_e_registrado_e_so_reexperimentado_depois_de_30_dias(tmp_path, log, resp):
    _universo(tmp_path, [64496, 64498])
    m, pedidos = _mock(resp, vuln=403)
    with m:
        med = _run(tmp_path, log, "2026-11-10")
        assert med["vuln"] == "indisponivel"
        d = _doc(tmp_path, "2026-11-10")
        assert d["plano"]["facetas"]["vuln"] == "indisponivel" and d["plano"]["facetas"]["vuln_testada_em"] == "2026-11-10"
        assert d["asns"]["64496"]["vulns"] is None and sum(1 for _, k in pedidos if k == "vuln") == 1      # tentou uma vez e desistiu
        _universo(tmp_path, [64496, 64498], "2026-11-20")
        _run(tmp_path, log, "2026-11-20")
        assert sum(1 for _, k in pedidos if k == "vuln") == 1                                         # 10 dias depois: não reexperimenta
        _universo(tmp_path, [64496, 64498], "2026-12-11")
        _run(tmp_path, log, "2026-12-11")
        assert sum(1 for _, k in pedidos if k == "vuln") == 2                                         # 31 dias depois: reexperimenta (uma vez)


def test_rodizio_prioriza_nunca_lidos_e_depois_o_mais_antigo(tmp_path, log, resp):
    _universo(tmp_path, [64496, 64498, 64499])
    m, pedidos = _mock(resp)
    with m:
        _run(tmp_path, log, "2026-11-10", asns_por_execucao=2)
        assert sorted(_doc(tmp_path, "2026-11-10")["asns"]) == ["64496", "64498"]
        _run(tmp_path, log, "2026-11-11", asns_por_execucao=2)
        d = _doc(tmp_path, "2026-11-11")
    assert sorted(d["asns"]) == ["64496", "64498", "64499"] and d["asns"]["64499"]["em"] == "2026-11-11"      # o nunca lido entra primeiro
    assert d["asns"]["64496"]["em"] == "2026-11-11" and d["asns"]["64498"]["em"] == "2026-11-10"            # depois o mais antigo (empate pela ordem do ASN); cada leitura mantém a sua data


def test_chave_recusada_para_na_hora(tmp_path, log, resp):
    _universo(tmp_path, [64496, 64498])
    m, pedidos = _mock(resp, extra=lambda a, k: resp("erro_chave.json", 401))
    with m:
        med = _run(tmp_path, log, "2026-11-10")
    assert len(pedidos) == 1 and "chave recusada" in med["parou"] and _doc(tmp_path, "2026-11-10")["asns"] == {}
    assert CHAVE not in med["parou"]


def test_consulta_principal_recusada_por_plano_encerra_a_rodada(tmp_path, log, resp):
    _universo(tmp_path, [64496, 64498])
    m, pedidos = _mock(resp, extra=lambda a, k: resp("erro_plano.json", 403) if k == "risco" else None)
    with m:
        med = _run(tmp_path, log, "2026-11-10")
    assert "plano da conta não permite" in med["parou"] and len(pedidos) == 2 and _doc(tmp_path, "2026-11-10")["asns"] == {}      # não grava leitura pela metade


def test_429_persistente_encerra_com_recuo_e_guarda_o_que_leu(tmp_path, log, resp):
    _universo(tmp_path, [64496, 64498])
    dormiu = []
    m, pedidos = _mock(resp, extra=lambda a, k: httpx.Response(429, headers={"Retry-After": "2"}) if a == 64498 else None)
    with m:
        med = _run(tmp_path, log, "2026-11-10", dormir=dormiu.append)
    assert "limite de taxa" in med["parou"] and dormiu == [2, 4] and list(_doc(tmp_path, "2026-11-10")["asns"]) == ["64496"]     # recuo crescente a cada 429


def test_falhas_de_rede_seguidas_encerram_sem_registrar_a_url(tmp_path, log, resp, caplog):
    _universo(tmp_path, [64496, 64498, 64499, 64500])
    m, pedidos = _mock(resp, extra=lambda a, k: httpx.ConnectError("conexão recusada"))
    with caplog.at_level(logging.DEBUG), m:
        med = _run(tmp_path, log, "2026-11-10")
    assert "3 falhas seguidas" in med["parou"] and len(pedidos) == 3 and med["falhas"] == 3
    assert CHAVE not in caplog.text and "api.shodan.io" not in caplog.text


def test_sem_chave_no_ambiente_falha_alto(tmp_path, log, monkeypatch):
    monkeypatch.delenv("SHODAN_API_KEY", raising=False)
    _universo(tmp_path, [64496])
    with pytest.raises(fonte.ChaveInvalida):
        fonte.run("2026-11-10", tmp_path, log, chave=None)


def test_sondagem_mede_facetas_filtros_cobertura_e_creditos_sem_imprimir_a_chave(tmp_path, log, resp, monkeypatch):
    monkeypatch.setattr(fonte, "today_str", lambda: "2026-11-10")
    _universo(tmp_path, [64496, 64497, 64498])
    m, _ = _mock(resp, vuln=403)
    saida = tmp_path / "sondagem.json"
    with m:
        rel = fonte.sondar(tmp_path, 3, CHAVE, intervalo=0, saida=saida)
    assert rel["facetas"]["port"]["ok"] and rel["facetas"]["vuln"]["ok"] is False and "plano" in rel["facetas"]["vuln"]["erro"].lower() or rel["facetas"]["vuln"]["erro"]
    assert rel["cobertura"]["consultados"] == 3 and rel["cobertura"]["com_servicos"] == 2 and rel["cobertura"]["pct_com_servicos"] == 66.7
    assert rel["api_info_antes"]["query_credits"] == 100 == rel["api_info_depois"]["query_credits"]
    assert set(rel["tempo_por_asn_ms"]) >= {"mediana", "maximo"}
    assert CHAVE not in json.dumps(rel) and CHAVE not in saida.read_text(encoding="utf-8")


def test_para_se_a_consulta_gastar_creditos(tmp_path, log, resp, monkeypatch):
    monkeypatch.setattr(fonte, "CONFERE_CREDITOS_APOS", 2)
    _universo(tmp_path, [64496, 64498, 64499, 64500])
    m, pedidos = _mock(resp, creditos=[100, 97])
    with m:
        med = _run(tmp_path, log, "2026-11-10")
    assert "gasta créditos" in med["parou"] and med["asns_lidos"] == 2 and len([1 for _, k in pedidos if k == "geral"]) == 2


def test_intervalo_minimo_vale_para_cada_requisicao_e_nao_so_entre_asns(tmp_path, log, resp):
    """O Limitador entra em toda requisição (1 req/s é a prática conhecida da API): esperar só entre ASNs faria as 3 consultas de um ASN
    saírem em rajada (~2,2 req/s), com 429 persistente depois de poucas dezenas de ASNs."""
    _universo(tmp_path, [64496, 64497])
    m, pedidos = _mock(resp)
    t = [0.0]
    marcas: list[float] = []

    def dormir(s):
        t[0] += s

    def relogio():
        return t[0]

    with m:
        _run(tmp_path, log, "2026-11-10", intervalo_s=1.1, dormir=dormir, relogio=relogio, tempo_max_s=0)
    n_requisicoes = len(pedidos)
    assert n_requisicoes == 4                                           # ASN com serviço: A, B e C; ASN sem serviço: só A
    assert t[0] >= 1.1 * (n_requisicoes - 1) - 0.01                     # ao menos 1,1 s entre quaisquer duas requisições (inclui a de /api-info)
