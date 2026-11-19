# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — Cloudflare Radar: rodízio de IPv6 por ASN, topos, eventos de BGP e quedas, sem rede (API simulada com respx)."""
import json

import httpx
import pytest
import respx

from core import radar
from core.common import read_json_gz
from sources.cloudflare_radar import collect as fonte

TOKEN = "token-de-teste"


@pytest.fixture
def api(fx, monkeypatch):
    """Simula a API; devolve a lista de (caminho, parâmetros) pedidos, para conferir o rodízio."""
    monkeypatch.setattr(radar, "MAX_ENTIDADES", 3)
    pedidos: list[tuple[str, dict]] = []

    def resposta(nome):
        return httpx.Response(200, json=json.loads(fx("cloudflare_radar", nome).read_text(encoding="utf-8")))

    def despachar(request: httpx.Request):
        p = dict(request.url.params)
        c = request.url.path.replace("/client/v4", "")
        pedidos.append((c, p))
        assert request.headers["authorization"] == f"Bearer {TOKEN}"
        if c == "/radar/entities/asns":
            return resposta("entities_0.json" if p["offset"] == "0" else "entities_1.json")
        if c == "/radar/http/summary/ip_version":
            assert p["botClass"] == "LIKELY_HUMAN" and p["dateRange"] == "28d"
            return resposta(f"ipv6_{p['asn']}.json")
        return resposta({"/radar/http/top/ases": "topo_trafego.json", "/radar/quality/speed/top/ases": "topo_velocidade.json",
                         "/radar/bgp/leaks/events": "vazamentos.json", "/radar/bgp/hijacks/events": "sequestros.json",
                         "/radar/traffic_anomalies": "anomalias.json", "/radar/annotations/outages": "quedas.json"}[c])

    with respx.mock(base_url=radar.BASE_URL, assert_all_called=False) as m:
        m.route().mock(side_effect=despachar)
        yield pedidos


def _doc(tmp_path, d):
    return read_json_gz(tmp_path / "normalized" / d / "summary" / "cloudflare_radar.json.gz")


def test_rodizio_cobre_todos_os_asns_e_prioriza_o_mais_antigo(tmp_path, log, api):
    r1 = fonte.run("2026-11-09", tmp_path, log, token=TOKEN, asns_por_execucao=2, espera_s=0)
    assert r1["asns_lidos"] == 2 and r1["asns_na_lista"] == 4 and r1["dias_ate_cobrir"] == 2
    d1 = _doc(tmp_path, "2026-11-09")
    assert sorted(d1["ipv6"]) == ["64496", "64497"]                       # sem leitura nenhuma: pela ordem do ASN
    assert d1["ipv6"]["64496"] == {"v6": 70.5, "em": "2026-11-09"} and d1["ipv6"]["64497"]["v6"] == 0.0
    r2 = fonte.run("2026-11-10", tmp_path, log, token=TOKEN, asns_por_execucao=2, espera_s=0)
    d2 = _doc(tmp_path, "2026-11-10")
    assert sorted(d2["ipv6"]) == ["64496", "64497", "64498", "64499"]     # os dois que faltavam entraram
    assert d2["ipv6"]["64498"] == {"v6": None, "em": "2026-11-10"}        # resposta sem dado fica registrada, não vira zero
    assert d2["ipv6"]["64496"]["em"] == "2026-11-09"                       # a leitura antiga mantém a sua data
    assert r2["asns_com_dado_ipv6"] == 3
    fonte.run("2026-11-11", tmp_path, log, token=TOKEN, asns_por_execucao=2, espera_s=0)
    d3 = _doc(tmp_path, "2026-11-11")
    assert {a for a, v in d3["ipv6"].items() if v["em"] == "2026-11-11"} == {"64496", "64497"}      # a vez volta aos de leitura mais antiga


def test_lista_de_asns_so_e_renovada_depois_de_7_dias(tmp_path, log, api):
    fonte.run("2026-11-09", tmp_path, log, token=TOKEN, asns_por_execucao=1, espera_s=0)
    n = sum(1 for c, _ in api if c == "/radar/entities/asns")
    fonte.run("2026-11-10", tmp_path, log, token=TOKEN, asns_por_execucao=1, espera_s=0)
    assert sum(1 for c, _ in api if c == "/radar/entities/asns") == n          # reaproveita a lista
    fonte.run("2026-11-16", tmp_path, log, token=TOKEN, asns_por_execucao=1, espera_s=0)
    assert sum(1 for c, _ in api if c == "/radar/entities/asns") == 2 * n      # 7 dias depois, renova


def test_topos_bgp_e_quedas(tmp_path, log, api):
    fonte.run("2026-11-09", tmp_path, log, token=TOKEN, asns_por_execucao=1, espera_s=0)
    d = _doc(tmp_path, "2026-11-09")
    assert d["licenca"] == "CC BY-NC 4.0" and "Cloudflare Radar" in d["atribuicao"]
    assert d["trafego"]["topo"][0] == {"asn": 64496, "pct": 9.9}
    v = d["velocidade"]["topo"][0]
    assert v["asn"] == 64496 and v["download_mbps"] == 250.1 and v["testes"] == 321
    vaz = d["bgp"]["vazamentos"]
    assert vaz["total_informado"] == 1 and vaz["eventos"][0]["vazador"] == 64497 and vaz["eventos"][0]["caminho"] == [64499, 64497, 64496]
    seq = d["bgp"]["sequestros"]["eventos"][0]
    assert seq["sequestrador"] == 64498 and seq["vitimas"] == [64496] and seq["prefixos"] == 2 and seq["rpki_invalido"] is True
    assert d["quedas"]["anomalias"] == 0 and d["quedas"]["anotacoes"] == 0 and d["quedas"]["consultado"] is True


def test_nada_sensivel_e_gravado(tmp_path, log, api):
    fonte.run("2026-11-09", tmp_path, log, token=TOKEN, asns_por_execucao=1, espera_s=0)
    bruto = (tmp_path / "normalized" / "2026-11-09" / "summary" / "cloudflare_radar.json.gz")
    import gzip
    texto = gzip.open(bruto, "rt", encoding="utf-8").read()
    assert TOKEN not in texto and "192.0.2.0/24" not in texto and "Authorization" not in texto     # prefixos só em contagem, token nunca


def test_token_ausente_e_token_sem_permissao_falham_alto(tmp_path, log, monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    with pytest.raises(fonte.TokenInvalido):
        fonte.run("2026-11-09", tmp_path, log, espera_s=0)
    with respx.mock(base_url=radar.BASE_URL) as m:
        m.route().mock(return_value=httpx.Response(401, json={"success": False, "errors": [{"code": 10000, "message": "Authentication error"}]}))
        with pytest.raises(fonte.TokenInvalido):
            fonte.run("2026-11-09", tmp_path, log, token="x", espera_s=0)
    assert fonte.main(["--date", "2026-11-09"]) == 1
