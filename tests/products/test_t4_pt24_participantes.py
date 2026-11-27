# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 (PT-24 / IXP-E5.5): `GET /ixps/{code}/participantes` sobre o dataset sintético (zc: IPv6 sem coleta, 2 sessões sem cadastro; zb: 1 cadastrado sem sessão)."""
import re

import pytest

from tests.products.api_contract import ALLOWED

URL = "/api/v1/ixps/{}/participantes"


def _get(api, code, **params):
    r = api.get(URL.format(code), headers=ALLOWED, params=params)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _todas(api, code, **params):
    itens, pag = [], 1
    while True:
        j = _get(api, code, limit=200, page=pag, **params)
        itens += j["items"]
        if len(itens) >= j["total"]:
            return j, itens
        pag += 1


def _resumo_rs(api, code):
    perfil = api.get(f"/api/v1/ixps/{code}", headers=ALLOWED, params={"include": "route_servers"}).json()
    return perfil, (perfil.get("route_servers") or {}).get("resumo") or {}


@pytest.fixture(scope="module")
def codigos(api):
    return [i["code"] for i in api.get("/api/v1/ixps", headers=ALLOWED).json()["ixps"]]


def test_linhas_sao_o_cadastro_mais_as_sessoes_sem_cadastro_em_todo_ptt(api, codigos):
    for code in codigos:
        perfil, resumo = _resumo_rs(api, code)
        j, itens = _todas(api, code)
        assert j["total_participantes"] == j["total"] == len(itens) == len({l["asn"] for l in itens}), code
        assert j["total"] == perfil["ixbr_members_count"] + resumo.get("sessao_sem_cadastro", 0), code
        assert j["contagens"]["todos"] == j["total"]


def test_os_contadores_dos_filtros_batem_com_o_total_de_cada_filtro(api, codigos):
    for code in codigos:
        base = _get(api, code)
        for filtro, n in base["contagens"].items():
            assert _get(api, code, filtro=filtro)["total"] == n, (code, filtro)


def test_familia_sem_coleta_vem_nula_e_fora_dos_filtros(api, codigos):
    zc = next(c for c in codigos if _get(api, c)["fontes"]["looking_glass"]["coleta"]["v6"] != "ok")
    j, itens = _todas(api, zc)
    assert itens and all(l["direto"]["v6"] is None and l["originador"]["v6"] is None for l in itens)
    assert j["contagens"]["sem-v6"] == 0                                        # IPv6 sem coleta não vira "sem IPv6"
    assert all(isinstance(l["direto"]["v4"], bool) for l in itens)


def test_cadastrado_sem_sessao_e_sessao_sem_cadastro_batem_com_o_route_server(api, codigos):
    achou = {"sem_sessao": False, "sem_cadastro": False}
    for code in codigos:
        _, resumo = _resumo_rs(api, code)
        j = _get(api, code)
        assert j["contagens"]["membro-sem-sessao-rs"] == resumo.get("cadastrados_sem_sessao", 0), code
        assert j["contagens"]["sessao-sem-cadastro"] == resumo.get("sessao_sem_cadastro", 0), code
        for l in _get(api, code, filtro="membro-sem-sessao-rs")["items"]:
            assert l["membro"] is True and l["sessao_rs"]["sessoes"] == 0
            achou["sem_sessao"] = True
        for l in _get(api, code, filtro="sessao-sem-cadastro")["items"]:
            assert l["membro"] is False and l["sessao_rs"]["sessoes"] >= 1
            achou["sem_cadastro"] = True
    assert all(achou.values()), achou                                           # o dataset sintético planta os dois casos


def test_rejeicao_tem_denominador_e_o_detalhe_traz_a_idade_da_coleta(api, codigos):
    vistos = detalhes = 0
    for code in codigos:
        _, itens = _todas(api, code)
        for l in itens:
            r = l["rejeicao"]
            if r:
                vistos += 1
                assert r["recebidas"] >= r["filtradas"] >= 0
                assert r["pct"] is None if r["recebidas"] == 0 else r["pct"] == round(100 * r["filtradas"] / r["recebidas"], 2)
            d = l["rejeicao_detalhe"]
            if d:
                detalhes += 1
                assert d["rotas"] > 0 and isinstance(d["herdado"], bool) and (d["idade_dias"] is None or d["idade_dias"] >= 0)
    assert vistos and detalhes


def test_paginacao_cobre_o_total_sem_repetir_linhas(api, codigos):
    code = codigos[0]
    total = _get(api, code)["total"]
    p1 = _get(api, code, limit=10, page=1)["items"]
    p2 = _get(api, code, limit=10, page=2)["items"]
    assert len(p1) == 10 and total > 10
    assert not {l["asn"] for l in p1} & {l["asn"] for l in p2}
    assert [l["asn"] for l in p1] == sorted(l["asn"] for l in p1)               # ordem padrão neutra: ASN crescente
    assert _get(api, code, limit=10, page=1, desc=True)["items"][0]["asn"] > p1[-1]["asn"]


def test_busca_por_asn_e_por_nome_e_filtro_por_uf(api, codigos):
    code = codigos[0]
    _, itens = _todas(api, code)
    alvo = itens[3]
    assert [l["asn"] for l in _get(api, code, q=f"AS{alvo['asn']}")["items"]] == [alvo["asn"]]
    assert alvo["asn"] in [l["asn"] for l in _get(api, code, q=alvo["nome"][:12])["items"]]
    uf = next(l["uf"] for l in itens if l["uf"])
    assert {l["uf"] for l in _get(api, code, uf=uf)["items"]} == {uf}


def test_erros_e_privacidade(api, codigos):
    assert api.get(URL.format("nao-existe"), headers=ALLOWED).status_code == 404
    assert api.get(URL.format(codigos[0]), headers=ALLOWED, params={"filtro": "x"}).status_code == 400
    assert api.get(URL.format(codigos[0]), headers=ALLOWED, params={"ordem": "x"}).status_code == 400
    texto = api.get(URL.format(codigos[0]), headers=ALLOWED, params={"limit": 200}).text
    assert not re.search(r'"(email|e-mail|phone|telefone|contato|contacts?)"', texto)       # `empresa.cnpj` entra para o link à operadora (já é público em /assinantes)
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", texto)                     # nenhum e-mail em lugar nenhum da resposta


def test_soma_da_coluna_de_usuarios_via_ptt_e_o_estimated_users_do_ptt(api, codigos):
    """As duas colunas de usuários (PT-24): a estimativa por ASN sai da mesma função do total do PTT, então a soma da coluna fecha com `/estimated-users`."""
    com_valor = 0
    for code in codigos:
        _, itens = _todas(api, code)
        est = api.get(f"/api/v1/ixps/{code}/estimated-users", headers=ALLOWED).json()
        v4_ok = _get(api, code)["fontes"]["looking_glass"]["coleta"]["v4"] == "ok"
        soma = sum(l["usuarios_ptt"] for l in itens if l["usuarios_ptt"] is not None)
        resumo = _get(api, code)["usuarios_ptt_resumo"]
        if v4_ok:
            # linhas = participantes; quem origina prefixos no PTT sem ser participante fica fora da tabela e o resumo diz quanto
            assert resumo["na_tabela"] == pytest.approx(soma) and resumo["total_do_ptt"] == est["estimated_users"], code
            assert round(soma + resumo["fora_da_tabela"]["usuarios"]) == est["estimated_users"], code
            assert sum(1 for l in itens if l["usuarios_ptt"]) + resumo["fora_da_tabela"]["asns"] <= est["contributing_asns"]
        else:
            assert resumo is None
        com_valor += bool(soma)
        for l in itens:
            if l["usuarios_ptt"] is not None:
                assert l["usuarios_apnic"] is not None and 0 <= l["usuarios_ptt"] <= l["usuarios_apnic"] + 1e-6, (code, l["asn"])
            if l["is_br"] is False:
                assert l["usuarios_apnic"] is None and l["usuarios_ptt"] is None
    assert com_valor, "o dataset sintético tem originador brasileiro com usuários APNIC"


def test_colunas_de_usuarios_ordenam_sem_virar_ordem_padrao(api, codigos):
    code = codigos[0]
    assert _get(api, code)["ordem"].startswith("ASN")
    for campo in ("usuarios_apnic", "usuarios_ptt"):
        itens = _get(api, code, ordem=campo, desc=True, limit=200)["items"]
        vals = [l[campo] if l[campo] is not None else -1 for l in itens]
        assert vals == sorted(vals, reverse=True), campo


def test_empresa_nunca_e_o_cnpj_e_politica_peering_vem_do_peeringdb(api, codigos):
    empresas = politicas = prefixos = 0
    for code in codigos:
        _, itens = _todas(api, code)
        for l in itens:
            e = l["empresa"]
            if e:
                empresas += 1
                assert re.fullmatch(r"\d{14}", e["cnpj"]) and e["nome"] != e["cnpj"] and (e["nome"] is None or not re.fullmatch(r"[\d./-]+", e["nome"])), (code, l["asn"])
            if l["politica_peering"]:
                politicas += 1
                assert l["politica_peering"] == "Open"                       # `policy_general` do PeeringDB sintético
            assert set(l["prefixos"]) == {"v6", "v4"}
            for st in l["prefixos"].values():
                if st:
                    prefixos += 1
                    assert st["own_prefixes"] >= 0 and st["third_prefixes"] >= 0
    assert empresas and politicas and prefixos
    f = _get(api, codigos[0])["fontes"]
    assert f["peeringdb"]["fonte"] and f["apnic"]["limites"] and "uniforme" in f["apnic"]["limites"]


def test_prefixos_da_linha_batem_com_a_rota_peers(api, codigos):
    for code in codigos:
        _, itens = _todas(api, code)
        for afi in ("v6", "v4"):
            peers = (api.get(f"/api/v1/ixps/{code}/peers", headers=ALLOWED, params={"afi": afi}).json() or {}).get("peers") or {}
            por_asn = {l["asn"]: l["prefixos"][afi] for l in itens}
            for asn, st in peers.items():
                assert por_asn.get(int(asn)) == st, (code, afi, asn)


def test_lista_de_ptts_traz_sessoes_por_familia_e_cdns_com_fonte_e_data(api, codigos):
    j = api.get("/api/v1/ixps", headers=ALLOWED).json()
    assert j["interligacao"]["route_servers"]["coletado_em"] and j["interligacao"]["cdns"]["cdns_na_lista"] >= 0
    por_codigo = {i["code"]: i for i in j["ixps"]}
    assert set(por_codigo) == set(codigos)
    achou_rs = False
    for code, e in por_codigo.items():
        _, resumo = _resumo_rs(api, code)
        rs = e["route_servers"]
        assert "cdns_curados" in e and (e["cdns_curados"] is None or e["cdns_curados"] >= 0)
        if rs is None:
            continue
        achou_rs = True
        for fam in ("v6", "v4"):
            f = rs[fam]
            assert f is None or (f["up"] + f["down"] == f["sessoes"] and f["up"] >= 0 and f["down"] >= 0)
        if rs["rs_sem_vizinhos_atuais"] == 0:                                   # sem route server de vizinhos velhos, as famílias somam as sessões do resumo do PTT
            assert sum(rs[f]["sessoes"] for f in ("v6", "v4") if rs[f]) == resumo["sessoes"], code
    assert achou_rs


def test_route_server_com_vizinhos_velhos_fica_fora_da_contagem_do_ptt(api):
    j = {i["code"]: i for i in api.get("/api/v1/ixps", headers=ALLOWED).json()["ixps"]}
    velho = [c for c, e in j.items() if (e["route_servers"] or {}).get("rs_sem_vizinhos_atuais")]
    assert velho, "o dataset sintético planta um route server com cache de vizinhos velho (zc)"
    for c in velho:
        _, resumo = _resumo_rs(api, c)
        total = sum(j[c]["route_servers"][f]["sessoes"] for f in ("v6", "v4") if j[c]["route_servers"][f])
        assert total < resumo["sessoes"]


def _instalacoes_do_brasil(api):
    itens = api.get("/api/v1/facilities", headers=ALLOWED, params={"limit": 100}).json()["items"]
    return [f["id"] for f in itens if f.get("pais") == "BR"]


def test_redes_do_predio_resumo_fecha_e_confere_com_a_tabela_de_participantes(api):
    vistos = 0
    for fid in _instalacoes_do_brasil(api):
        base = api.get(f"/api/v1/facilities/{fid}", headers=ALLOWED).json()
        r = api.get(f"/api/v1/facilities/{fid}", headers=ALLOWED, params={"include": "redes_perfil"})
        assert r.status_code == 200, r.text[:200]
        j = r.json()
        assert {k: v for k, v in j.items() if k not in ("redes", "redes_perfil")} == {k: v for k, v in base.items() if k != "redes"}      # o resto do detalhe não muda
        assert [x["asn"] for x in j["redes"]] == [x["asn"] for x in base["redes"]]
        br = [x for x in j["redes"] if x.get("is_br")]
        for res in j["redes_perfil"]["resumo"]:
            assert res["redes_do_brasil"] == len(br) == sum(res[k] for k in j["redes_perfil"]["situacoes"])
            for x in br:
                assert set(x["situacao"]) >= {res["ixp"]}
                if x["situacao"][res["ixp"]] == "sessao_rs":
                    vistos += 1
                    linha = _get(api, res["ixp"], q=f"AS{x['asn']}")["items"]
                    assert linha and linha[0]["asn"] == x["asn"] and any(linha[0]["direto"].values())
                if x["situacao"][res["ixp"]] == "membro_sem_sessao_rs":
                    linha = _get(api, res["ixp"], q=f"AS{x['asn']}")["items"][0]
                    assert linha["membro"] is True and not any(linha["direto"].values())
        assert all("situacao" not in x for x in j["redes"] if not x.get("is_br"))
    assert vistos, "o dataset sintético tem rede do prédio com sessão no route server do PTT local"


def test_redes_do_predio_include_invalido_e_instalacao_fora_do_brasil(api):
    fid = _instalacoes_do_brasil(api)[0]
    assert api.get(f"/api/v1/facilities/{fid}", headers=ALLOWED, params={"include": "x"}).status_code == 400
    texto = api.get(f"/api/v1/facilities/{fid}", headers=ALLOWED, params={"include": "redes_perfil"}).text
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", texto) and not re.search(r'"(email|phone|telefone)"', texto)


def test_lista_de_ases_traz_membro_do_cadastro_separado_da_sessao_com_o_route_server(api, codigos):
    pres = api.get("/api/v1/asns/ix-presence", headers=ALLOWED).json()["asns"]
    j = api.get("/api/v1/asns", headers=ALLOWED, params={"limit": 100}).json()
    assert j["items"]
    for a in j["items"]:
        esperado = len((pres.get(str(a["asn"])) or {}).get("m") or [])
        assert a["ixps_membro_count"] == esperado, a["asn"]
        assert a["ixps_direct_count"] >= 0                                          # a sessão com o route server segue sendo outro número
    # a soma de "membro" por PTT confere com o cadastro de cada PTT
    for code in codigos:
        cadastro = api.get(f"/api/v1/ixps/{code}", headers=ALLOWED).json()["ixbr_members_count"]
        assert sum(1 for v in pres.values() if code in (v.get("m") or [])) == cadastro, code
    desc = api.get("/api/v1/asns", headers=ALLOWED, params={"limit": 100, "sort_by": "ixps_membro_count", "sort_desc": True}).json()["items"]
    assert [a["ixps_membro_count"] for a in desc] == sorted((a["ixps_membro_count"] for a in desc), reverse=True)
    assert desc[0]["ixps_membro_count"] == max(len(v.get("m") or []) for v in pres.values())


def test_matriz_de_cdns_separa_membro_com_sessao_membro_sem_sessao_e_so_via_outro_as(api):
    j = api.get("/api/v1/cdns/presence", headers=ALLOWED).json()
    assert "bilaterais" in j["estados_limites"] and set(j["estados"]) == {"ixbr_rs", "ixbr_sem_rs", "ixbr_origem"}
    assert j["cdns"]
    for c in j["cdns"]:
        membros = set(c["ixbr"])
        assert set(c["ixbr_rs"]) <= membros and not set(c["ixbr_origem"]) & membros, c["name"]
        assert set(c["ixbr_rs"]) | set(c["ixbr_sem_rs"]) | set(c["ixbr_sem_coleta"]) == membros, c["name"]
        assert isinstance(c["sem_rs_em_nenhum_ptt"], bool) and isinstance(c["asns_sem_documento"], list)
        assert c["ixbr_count"] == len(c["ixbr"])                                  # os campos de antes seguem como estavam


def test_sici_por_participante_vem_do_cnpj_do_asn_com_mes_de_referencia(api, codigos):
    achou = False
    for code in codigos:
        j, itens = _todas(api, code)
        assert j["fontes"]["sici"]["fonte"].startswith("Anatel")
        for l in itens:
            assert "sici" in l
            if l["sici"] is not None:
                assert set(l["sici"]) == {"acessos", "compartilhado"} and isinstance(l["sici"]["acessos"], int)
                achou = True
        ordenada = _get(api, code, ordem="assinantes", desc=True, limit=200)["items"]
        valores = [(l["sici"] or {}).get("acessos", -1) for l in ordenada]
        assert valores == sorted(valores, reverse=True), code
    assert achou
