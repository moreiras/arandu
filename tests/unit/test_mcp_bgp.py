# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tools de roteamento e RPKI do MCP, sobre um Store falso: o dataset sintético não tem routing_analysis nem bgp_stability."""
import asyncio
import gzip
import json

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from api.repos.rpki import RpkiRepo

D = "2026-10-30"
ANALISE = {"total_prefixes": 120, "bgp": {"x": 1}, "histograma": {f"/{i}": i for i in range(600)}, "has_path_data": False,
           "as_path_stats": {"top_communities": []}}
ESTAB = {"as_stability": [{"asn": 64500}], "period": {"dias": 7}}


class Loja:
    def __init__(self, tmp_path):
        vrps = tmp_path / D / "rpki"
        vrps.mkdir(parents=True)
        with gzip.open(vrps / "vrp_list.json.gz", "wt") as f:
            json.dump([{"asn": "AS64500", "prefix": "200.1.0.0/16", "maxLength": 24, "ta": "lacnic"}], f)
        self.rpki = RpkiRepo(lambda d: tmp_path / d)
        self.com_analise = True

    def resolve_date(self, d):
        return d or D

    def routing_analysis(self, d):
        return json.loads(json.dumps(ANALISE)) if self.com_analise else None

    def bgp_stability_visao_geral(self, d):
        return {"snapshot_date": d, "categorias": {"alto": 3}} if self.com_analise else None

    def bgp_stability_asn(self, d, asn, weeks):
        return {"stability": {"asn": asn}, "weeks": weeks} if self.com_analise else None

    def bgp_stability_resumo(self, d):
        return [{"asn": 1, "epppd": 0.5}, {"asn": 2, "epppd": 9.0}, {"asn": 3, "epppd": None}] if self.com_analise else None

    def bgp_stability_historico_resumo(self, d, weeks):
        return [{"hourly_global": []}] * weeks

    def bgp_stability_carga(self, d, weeks, top):
        return {"weeks": weeks, "top": top} if self.com_analise else None

    def geo_map(self, d, camada):
        return {"features": [{"properties": {"prefix": "200.1.2.0/24", "origin_asn": 64500}}]}

    def rpki_validate_prefixes(self, d, asn, prefixos):
        return self.rpki.validar_prefixos(d, asn, prefixos)

    def rpki_vrps_for_asn(self, d, asn):
        return self.rpki.vrps_do_asn(d, asn)

    def asn_index(self, d):
        return [{"asn": 1, "is_br": True, "has_rpki": True, "has_aspa": False, "space_v4": 256},
                {"asn": 2, "is_br": True, "has_rpki": False, "has_aspa": False, "space_v4": 512}]


@pytest.fixture()
def srv(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    import mcp_server.app as m
    loja = Loja(tmp_path)
    monkeypatch.setattr(m, "_store", loja)
    m._loja_teste = loja
    return m


def chamar(srv, nome, args):
    out = asyncio.run(srv.mcp.call_tool(nome, args))
    blocos = out[0] if isinstance(out, tuple) else out
    return json.loads("".join(b.text for b in blocos))


def test_routing_analysis_indice_secao_e_recusas(srv):
    idx = chamar(srv, "rota_analise", {})
    assert idx["total_prefixes"] == 120 and idx["has_path_data"] is False and "histograma" not in idx
    assert idx["secoes_grandes"]["histograma"]["itens"] == 600 and idx["secoes_grandes"]["histograma"]["bytes"] > 4000
    sec = chamar(srv, "rota_analise", {"secao": "histograma"})                           # 600 entradas, limite padrão 50
    assert sec["total"] == 600 and sec["truncado"] is True and len(sec["conteudo"]) == 50 and sec["conteudo"]["/7"] == 7
    pag = chamar(srv, "rota_analise", {"secao": "histograma", "limit": 100, "offset": 550})
    assert len(pag["conteudo"]) == 50 and pag["truncado"] is False and "/599" in pag["conteudo"]
    assert chamar(srv, "rota_analise", {"secao": "bgp"}) == {"snapshot_date": D, "secao": "bgp", "conteudo": {"x": 1}}   # pequena: inteira
    with pytest.raises(ToolError, match="seção inválida"):
        chamar(srv, "rota_analise", {"secao": "nao_existe"})
    srv._loja_teste.com_analise = False
    with pytest.raises(ToolError, match="indisponível"):
        chamar(srv, "rota_analise", {})


def test_bgp_stability_modos_e_por_as(srv):
    assert chamar(srv, "rota_estabilidade", {})["categorias"] == {"alto": 3}
    r = chamar(srv, "rota_estabilidade", {"modo": "resumo", "limit": 2})
    assert r["total"] == 3 and [i["asn"] for i in r["items"]] == [2, 1]                  # do mais ruidoso ao mais calmo
    assert len(chamar(srv, "rota_estabilidade", {"modo": "historico", "weeks": 3})["weeks"]) == 3
    carga = chamar(srv, "rota_estabilidade", {"modo": "carga", "weeks": 4, "limit": 50})
    assert (carga["weeks"], carga["top"]) == (4, 20)                                         # até 20 por família
    assert chamar(srv, "rota_estabilidade", {"asn": 64500, "weeks": 99})["weeks"] == 12      # semanas limitadas a 12
    with pytest.raises(ToolError, match="modo inválido"):
        chamar(srv, "rota_estabilidade", {"modo": "completo"})
    srv._loja_teste.com_analise = False
    with pytest.raises(ToolError, match="indisponível"):
        chamar(srv, "rota_estabilidade", {"asn": 1})


def test_rpki_summary_e_a_mesma_conta_da_rota(srv):
    r = chamar(srv, "rota_rpki", {})
    assert (r["br_asns_total"], r["br_asns_with_roa"], r["br_space_v4_total_24"], r["br_space_v4_roa_24"]) == (2, 1, 768, 256)


def test_rpki_prefix_estados_e_origem_do_asn(srv):
    ok = chamar(srv, "rota_rpki", {"prefix": "200.1.2.0/24"})                         # sem asn: origem geolocalizada do Registro.br
    assert ok["estado"] == "valid" and ok["asn"] == 64500 and ok["origem_do_asn"].startswith("prefixo geolocalizado")
    assert ok["roas_do_as_que_cobrem"][0]["prefix"] == "200.1.0.0/16"
    assert chamar(srv, "rota_rpki", {"prefix": "200.1.2.0/25", "asn": 64500})["estado"] == "invalid"     # excede o maxLength
    assert chamar(srv, "rota_rpki", {"prefix": "200.9.0.0/24", "asn": 64500})["estado"] == "not_found"
    assert chamar(srv, "rota_rpki", {"prefix": "200.1.2.0/24", "asn": 64999})["estado"] == "invalid"     # ROA de outro AS
    with pytest.raises(ToolError, match="informe o `asn`"):
        chamar(srv, "rota_rpki", {"prefix": "8.8.8.0/24"})
    with pytest.raises(ToolError, match="prefixo inválido"):
        chamar(srv, "rota_rpki", {"prefix": "isto não é cidr"})
