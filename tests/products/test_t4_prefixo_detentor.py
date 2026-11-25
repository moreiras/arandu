# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4/T5 — página de prefixo (PT-07): detentor × origem observada, RPKI só do par anunciado, CIDR canônico, rotas fora do
Registro.br, e o MCP `rota_prefixo`/`rota_rpki` com o mesmo código de leitura da REST.

Casos do dataset sintético (T1):
- cenário 6: o primeiro bloco de 64502 é alocado pelo Registro.br a 64502, mas a tabela global o vê originado por 64503, e só
  64502 tem ROA (é o formato do caso real `2801:80:3e80::/48`: detentor AS271640, origem AS1916, inválido);
- bloco alocado e não anunciado (`v4_idle` de 64496): RPKI não avaliado;
- prefixo de AS estrangeiro (100.64.0.0/10): está na tabela global e não no Registro.br.
"""
import ipaddress

import pytest

from tests.products.api_contract import ALLOWED
from tests.products.test_t4_api import ctx  # noqa: F401  (fixture reaproveitada)
from tests.products.test_t5_mcp import call, srv  # noqa: F401  (fixture reaproveitada)
from tests.synth.world import T1, build_world


@pytest.fixture(scope="module")
def mundo():
    return build_world(T1)


def _get(api, prefixo):
    return api.get(f"/api/v1/prefixes/{prefixo}", params={"date": T1}, headers=ALLOWED)


def test_detentor_diferente_da_origem_observada_e_rpki_do_anuncio(api, mundo):
    """PFX-E1/E2/E4: o AS do Registro.br não aparece como origem; o RPKI é o da origem observada, com o ROA de outro AS na tabela."""
    movido = mundo.ases[64502].v4[0]
    r = _get(api, movido)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["escopo"] == "alocacao_registro_br" and d["alocacao_registro_br"] == movido
    assert d["registro_asn"] == 64502 and d["origin_asn"] == 64502             # `origin_asn` depreciado = detentor
    assert d["observed_origin_asn"] == 64503 and d["observed_origin_fonte"] == "tabela_global"
    assert d["registro_asn_nome"] and d["observed_origin_nome"]
    rp = d["rpki_observado"]
    assert rp["estado"] == "invalid" and rp["motivo"] == "origem_diferente" and rp["asn"] == 64503
    assert rp["roas_que_cobrem"], "o ROA de 64502 tem de aparecer, com o AS dele (não o da origem observada)"
    assert {x["asn"] for x in rp["roas_que_cobrem"]} == {64502}
    assert all(x["autoriza_origem"] is False for x in rp["roas_que_cobrem"])


def test_bloco_alocado_sem_anuncio_nao_tem_rpki_avaliado(api, mundo):
    """PFX-E2: par não anunciado não é validado."""
    ocioso = mundo.ases[64496].v4_idle[0]
    assert ocioso not in mundo.full_table
    d = _get(api, ocioso).json()
    assert d["registro_asn"] == 64496 and d["observed_origin_asn"] is None and d["observed_origin_fonte"] is None
    assert d["rpki_observado"]["estado"] == "nao_avaliado" and d["rpki_observado"]["motivo"] == "sem_anuncio"
    assert all(x["autoriza_origem"] is None for x in d["rpki_observado"]["roas_que_cobrem"])


def test_grafia_nao_canonica_abre_na_forma_canonica(api, mundo):
    """PFX-E5: `2804:0000::/32` abria 404; bits de host zerados; grafia inválida é 422 com mensagem, não 404."""
    v6 = next(p for p in mundo.ases[64496].v6)
    rede = ipaddress.ip_network(v6)
    expandido = f"{rede.network_address.exploded}/{rede.prefixlen}"
    assert expandido != v6
    d = _get(api, expandido)
    assert d.status_code == 200, d.text
    assert d.json()["prefix"] == v6 and d.json()["prefixo_informado"] == expandido
    v4 = ipaddress.ip_network(mundo.ases[64502].v4[0])
    com_host = f"{v4.network_address + 1}/{v4.prefixlen}"
    assert _get(api, com_host).json()["prefix"] == str(v4)
    ruim = _get(api, "300.1.2.0/24")
    assert ruim.status_code == 422 and "Grafia não reconhecida" in ruim.text


def test_rota_observada_fora_do_registro_br_abre(api, mundo):
    """PFX-E5: prefixo da tabela global sem alocação do Registro.br abre, sem detentor; o ausente dá 404 que explica o limite."""
    estrangeiro = mundo.ases[4200000100].v4[0]
    d = _get(api, estrangeiro)
    assert d.status_code == 200, d.text
    d = d.json()
    assert d["escopo"] == "fora_do_registro_br" and d["registro_asn"] is None and d["alocacao_registro_br"] is None
    assert d["observed_origin_asn"] == 4200000100 and d["geo_org"] is None and d["uf"] is None
    ausente = _get(api, "203.0.113.0/24")
    assert ausente.status_code == 404 and "não prova que não seja anunciado" in ausente.text


def test_lookup_traz_detentor_e_origem(api, mundo):
    movido = ipaddress.ip_network(mundo.ases[64502].v4[0])
    r = api.get("/api/v1/prefixes/lookup", params={"ip": str(movido.network_address + 5), "date": T1}, headers=ALLOWED).json()
    assert r["prefix"] == str(movido) and r["registro_asn"] == 64502 and r["observed_origin_asn"] == 64503


def test_mcp_rota_prefixo_e_rota_rpki_seguem_a_rest(srv, api, mundo):  # noqa: F811
    """O MCP lê pelo mesmo código: mesmo corpo da REST; `rota_rpki` sem `asn` usa a origem observada."""
    movido = mundo.ases[64502].v4[0]
    rest = _get(api, movido).json()
    tool = call(srv, "rota_prefixo", {"prefix": movido, "date": T1})
    assert tool == rest
    rpki = call(srv, "rota_rpki", {"prefix": movido, "date": T1})
    assert rpki["asn"] == 64503 and rpki["estado"] == "invalid" and rpki["motivo"] == "origem_diferente"
    assert "observada" in rpki["origem_do_asn"] and rpki["roas_do_as_que_cobrem"] == []
    assert [r["asn"] for r in rpki["roas_que_cobrem"]] == [64502]
    informado = call(srv, "rota_rpki", {"prefix": movido, "asn": 64502, "date": T1})
    assert informado["estado"] == "valid" and informado["origem_do_asn"] == "informado"
    ocioso = call(srv, "rota_rpki", {"prefix": mundo.ases[64496].v4_idle[0], "date": T1})
    assert ocioso["estado"] == "nao_avaliado" and ocioso["asn"] is None
