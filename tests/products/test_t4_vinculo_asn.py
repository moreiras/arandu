# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4/T5 (PT-09, decisão D5): vínculo ASN ↔ CNPJ com `asn_vinculo` ∈ {cnpj, raiz, marca, estrangeiro, nenhum}, uma regra por teste e uma
superfície por teste (operadora, grupo, grupos, /ases, Home, MCP), sobre o cenário 10 do dataset sintético (GRUPO-E2, GRUPO-E7, HOME-E2,
GRUPOS 5.1, ASES 5.3)."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.products.api_contract import ALLOWED
from tests.products.conftest import fake_pix
from tests.synth import market
from tests.synth.world import AS_FILIAL, SEM_ASN_FILIAL, T1, build_world, make_cnpj

MUNDO = build_world(T1)
OPS = {o["cnpj"]: o for o in market.operators(MUNDO)}
RAIZ = make_cnpj(SEM_ASN_FILIAL)                 # matriz que declara ao SICI sem ASN no próprio CNPJ; o AS está na filial 0002
MARCA = make_cnpj(203)                           # "Provedor Sem ASN 4": marca curada DELTA com a raiz de 64499
ESTRANGEIRO = make_cnpj(204)                     # "Provedor Sem ASN 5": EPSILON → AS 4200000100 (US)
NENHUM = make_cnpj(200)                          # "Provedor Sem ASN 1": nenhum vínculo
DOIS_ASNS = MUNDO.ases[64500].cnpj               # cenário 3: o mesmo CNPJ com 64500 e 64501
ROOT = Path(__file__).resolve().parents[2]


def _get(api, caminho, **params):
    r = api.get(f"/api/v1{caminho}", params={"date": T1, **params}, headers=ALLOWED)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _operadora(api, cnpj):
    return _get(api, f"/acessos/operadora/{cnpj}")


# ── regras do vínculo (na resposta da operadora, que é a forma mais direta de ver o índice) ──

def test_regra_cnpj_e_fato_e_soma_nao_duplica(api):
    d = _operadora(api, DOIS_ASNS)
    assert d["asn_vinculo"] == "cnpj" and d["asns"] == [64500, 64501]
    assert [(v["asn"], v["vinculo"], v["selo"]) for v in d["asns_vinculados"]] == [(64500, "cnpj", "fato"), (64501, "cnpj", "fato")]
    assert d["rede"]["asn_count"] == 2 and d["rede"]["total_apnic_users"] == MUNDO.ases[64500].users + MUNDO.ases[64501].users


def test_regra_raiz_liga_o_as_da_filial_com_selo_inferido(api):
    """GRUPO-E2/HOME-E2 (padrão Hughes): o SICI é da matriz e o AS está registrado na filial da mesma raiz."""
    filial = MUNDO.ases[AS_FILIAL].cnpj
    assert filial[:8] == RAIZ[:8] and filial != RAIZ
    d = _operadora(api, RAIZ)
    assert d["asns"] == []                                              # o mesmo CNPJ continua sem ASN (fato)
    assert d["asn_vinculo"] == "raiz"
    assert d["asns_vinculados"] == [{"asn": AS_FILIAL, "vinculo": "raiz", "selo": "inferido", "cnpj_registro": filial}]
    assert d["rede"]["total_apnic_users"] == MUNDO.ases[AS_FILIAL].users and d["rede"]["asns"][0]["vinculo"] == "raiz"
    assert "raiz" in d["regra_vinculo"]


def test_regra_marca_curada_com_base_e_data_fora_da_soma(api):
    d = _operadora(api, MARCA)
    assert d["asns"] == [] and d["asn_vinculo"] == "marca"
    v = d["asns_vinculados"]
    assert [x["asn"] for x in v] == OPS[MUNDO.ases[64499].cnpj]["asns"]
    assert all(x["vinculo"] == "marca" and x["selo"] == "inferido" and x["marca"] == "DELTA" and x["base"] and x["data"] == "2026-11-24" for x in v)
    assert d["rede"] is None                                            # marca liga outra empresa: listada, não somada


def test_regra_estrangeiro_tem_rotulo_proprio(api):
    d = _operadora(api, ESTRANGEIRO)
    assert d["asn_vinculo"] == "estrangeiro" and d["rede"] is None
    assert d["asns_vinculados"] == [{"asn": 4200000100, "vinculo": "estrangeiro", "selo": "inferido", "cnpj_registro": None,
                                     "marca": "EPSILON", "base": d["asns_vinculados"][0]["base"], "data": "2026-11-24"}]


def test_regra_nenhum(api):
    d = _operadora(api, NENHUM)
    assert d["asn_vinculo"] == "nenhum" and d["asns_vinculados"] == [] and d["rede"] is None


def test_tabela_curada_rejeita_estrangeiro_sem_data(tmp_path):
    from core import marcas
    p = tmp_path / "c.yaml"
    p.write_text('versao: 1\ncurada_em: 2026-11-24\nfonte_da_curadoria: teste\nmarcas: []\n'
                 'asns_estrangeiros:\n  - {marca: X, raizes: ["12345678"], asns: [1], base: "b"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="data"):
        marcas.carregar_curada(p)


# ── superfícies ──

def test_superficie_operadora_perfil(api):
    """`/operadoras/{cnpj}` (página da operadora e `operadora_detalhe` do MCP) leva o vínculo no bloco SCM e a rede pela raiz."""
    d = _get(api, f"/operadoras/{RAIZ}")
    assert d["scm"]["asn_vinculo"] == "raiz" and d["rede"]["total_apnic_users"] == MUNDO.ases[AS_FILIAL].users


def test_superficie_grupo_inclui_as_da_filial(api):
    """GRUPO-E2: o grupo da empresa recebe o AS da filial; usuários e visibilidade BGP deixam de ser zero e falso."""
    g = _get(api, f"/grupos/ind_{RAIZ[:8]}")
    assert g["asns"] == [AS_FILIAL]
    assert g["asns_vinculados"] == [{"asn": AS_FILIAL, "vinculo": "raiz", "selo": "inferido", "cnpj_registro": MUNDO.ases[AS_FILIAL].cnpj}]
    assert g["usuarios_apnic"] == MUNDO.ases[AS_FILIAL].users and g["visibilidade_bgp"] is True
    # cenário 3: dois ASNs do mesmo CNPJ somam uma vez cada
    g3 = _get(api, f"/grupos/empresa/{DOIS_ASNS}")
    grupo = _get(api, f"/grupos/{g3['grupo_id']}")
    assert {64500, 64501} <= set(grupo["asns"])
    assert grupo["usuarios_apnic"] == sum(MUNDO.ases[a].users for a in grupo["asns"])


def test_superficie_grupos_sem_asn_em_dois_grupos(api):
    grupos = _get(api, "/grupos")["grupos"]
    g = next(x for x in grupos if x["grupo_id"] == f"ind_{RAIZ[:8]}")
    assert g["asns"] == [AS_FILIAL] and g["asns_raiz"] == [AS_FILIAL] and g["usuarios_apnic"] == MUNDO.ases[AS_FILIAL].users
    vistos: dict[int, str] = {}
    for x in grupos:
        for a in x["asns"]:
            assert a not in vistos, f"AS{a} em {vistos.get(a)} e {x['grupo_id']}"
            vistos[a] = x["grupo_id"]
        assert x["usuarios_apnic"] == sum(MUNDO.ases[a].users for a in x["asns"] if a in MUNDO.ases)
    # a marca não liga ASN a grupo: a operadora DELTA continua sem ASN no grupo
    assert next(x for x in grupos if x["grupo_id"] == f"ind_{MARCA[:8]}")["asns"] == []


def test_superficie_ases_por_raiz(api):
    """ASES 5.3: `/asns/by-organization?chave=raiz` agrupa matriz e filiais; o padrão segue por CNPJ."""
    por_cnpj = _get(api, "/asns/by-organization", limit=200)
    por_raiz = _get(api, "/asns/by-organization", limit=200, chave="raiz")
    assert por_cnpj["chave"] == "cnpj" and por_raiz["chave"] == "raiz"
    o = next(x for x in por_raiz["groups"] if x["raiz"] == DOIS_ASNS[:8])
    assert o["cnpj"] == DOIS_ASNS and o["cnpjs"] == 1 and {a["vinculo"] for a in o["asns"]} == {"cnpj"}
    r = api.get("/api/v1/asns/by-organization", params={"chave": "grupo"}, headers=ALLOWED)
    assert r.status_code == 422


def test_ases_por_raiz_junta_filial_na_mesma_linha():
    """Regra do modo raiz com matriz e filial: a linha fica com o CNPJ da matriz e a filial sai com `vinculo` = `raiz`."""
    from api.routes.asns import asns_por_organizacao
    linhas = [{"asn": 1, "cnpj": "12345678000195", "apnic_users": 10}, {"asn": 2, "cnpj": "12345678000276", "apnic_users": 30},
              {"asn": 3, "cnpj": "87654321000100", "apnic_users": 5}]
    store = SimpleNamespace(resolve_date=lambda d: "2026-01-01", query_table=lambda d, c: linhas)
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(store=store)))
    assert asns_por_organizacao(req, None, 30, "cnpj")["total"] == 0
    out = asns_por_organizacao(req, None, 30, "raiz")
    g = out["groups"][0]
    assert out["total"] == 1 and g["raiz"] == "12345678" and g["cnpj"] == "12345678000195" and g["cnpjs"] == 2
    assert [(a["asn"], a["vinculo"]) for a in g["asns"]] == [(2, "raiz"), (1, "cnpj")] and g["total_apnic_users"] == 40


def test_superficie_home_destaque_sem_asn(api):
    """HOME-E2: o destaque conta só `com_asn` falso (nenhum ou estrangeiro); raiz e marca saem; o estrangeiro fica, com rótulo."""
    cartao = next(c for c in json.loads((ROOT / "frontend/src/features/home/cartoes.json").read_text(encoding="utf-8"))["cartoes"]
                  if c["id"] == "grandes-sem-asn")
    corpo = json.loads(json.dumps(cartao["consulta"]["corpo"]))
    assert "asn_vinculo" in corpo["select"]
    corpo["filter"]["and"][0]["value"] = 1                                # no sintético as operadoras sem ASN têm 600 acessos
    corpo["limit"] = 200
    r = api.post("/api/v1/query/operadoras", json=corpo, params={"date": T1}, headers=ALLOWED)
    assert r.status_code == 200, r.text[:300]
    itens = {i["cnpj"]: i["asn_vinculo"] for i in r.json()["items"]}
    assert RAIZ not in itens and MARCA not in itens
    assert itens[ESTRANGEIRO] == "estrangeiro" and itens[NENHUM] == "nenhum"
    assert set(itens.values()) <= {"nenhum", "estrangeiro"}


def test_superficie_listas_com_asn_seguem_o_vinculo(api):
    """`/acessos/operadoras` e `/outorgas` filtram `com_asn` pela mesma regra (fonte única)."""
    sem = {r["cnpj"] for r in _get(api, "/acessos/operadoras", com_asn="false", limit=500)["items"]}
    assert RAIZ not in sem and MARCA not in sem and ESTRANGEIRO in sem
    out = _get(api, "/outorgas", com_asn="false", limit=500)["items"]
    assert {r["cnpj"] for r in out} >= {ESTRANGEIRO, NENHUM} and RAIZ not in {r["cnpj"] for r in out}
    assert next(r for r in out if r["cnpj"] == ESTRANGEIRO)["asn_vinculo"] == "estrangeiro"


def test_superficie_asn_mostra_irmao_da_mesma_raiz(api):
    d = _get(api, f"/asns/{AS_FILIAL}")
    assert d["same_cnpj_asns"] == [] and d["same_raiz_asns"] == []          # a matriz não tem AS: nenhum irmão
    d = _get(api, "/asns/64500")
    assert [a["asn"] for a in d["same_cnpj_asns"]] == [64501] and d["same_raiz_asns"] == []


# ── MCP ──

@pytest.fixture(scope="module")
def srv(pipeline, api):
    base, _ = pipeline
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATA_DIR", str(base))
        from api.store import Store
        from mcp_server import app as m

        mp.setattr(m, "_store", Store(base))
        mp.setattr(Store, "_load_pix_config", lambda self: fake_pix())
        yield m


def _call(srv, nome, args):
    out = asyncio.run(srv.mcp.call_tool(nome, args))
    blocos = out[0] if isinstance(out, tuple) else out
    return json.loads("".join(getattr(b, "text", "") for b in blocos))


def test_superficie_mcp(srv):
    ranking = _call(srv, "operadora_ranking", {"com_asn": False, "limit": 200})
    vinc = {i["cnpj"]: i["asn_vinculo"] for i in ranking["items"]}
    assert RAIZ not in vinc and MARCA not in vinc and vinc[ESTRANGEIRO] == "estrangeiro"
    assert _call(srv, "operadora_detalhe", {"cnpj": RAIZ})["scm"]["asn_vinculo"] == "raiz"
    g = _call(srv, "operadora_grupo", {"cnpj": RAIZ})
    assert g["asns"] == [AS_FILIAL] and g["asns_raiz"] == [AS_FILIAL] and g["usuarios_apnic"] == MUNDO.ases[AS_FILIAL].users
    r = _call(srv, "operadora_resolver", {"name": "Epsilon"})
    assert r["metodo"] == "curada" and r["asns"] == [4200000100] and r["asns_estrangeiros"] == [4200000100]
    q = _call(srv, "query", {"collection": "operadoras", "filter": {"field": "asn_vinculo", "op": "eq", "value": "marca"}, "select": ["cnpj", "asns_vinculados"]})
    assert [i["cnpj"] for i in q["items"]] == [MARCA] and q["items"][0]["asns_vinculados"] == OPS[MUNDO.ases[64499].cnpj]["asns"]
