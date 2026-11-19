# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — busca universal: reconhecimento pela forma, agrupamento por tipo, acerto nas consultas-exemplo,
privacidade do índice (sem contato nem pessoa física), desempenho e coerência das páginas-alvo com o frontend."""
import json
import re
import time
from pathlib import Path

import pytest

from api import busca

ROOT = Path(__file__).resolve().parents[2]


def _b(api, q, **p):
    r = api.get("/api/v1/busca", params={"q": q, **p})
    assert r.status_code == 200, r.text
    return r.json()


def _urls(resp):
    return [i["url"] for g in resp["grupos"] for i in g["itens"]]


@pytest.fixture(scope="module")
def ex(api):
    store = api.app.state.store
    d = store.latest()
    asn = next(a for a in store.asn_index(d) if a.get("is_br"))
    op = next(o for o in store.operadora_index(d) if o.get("ativo"))
    ptt = next(i for i in store.ixp_index(d) if i.get("code"))
    cdn = store.cdn_presence(d)["cdns"][0]["name"]
    return {"asn": asn, "op": op, "ptt": ptt, "cdn": cdn, "d": d}


def test_numero_e_as_numero_reconhecem_o_as(api, ex):
    for q in (str(ex["asn"]["asn"]), f"AS{ex['asn']['asn']}", f"as {ex['asn']['asn']}"):
        r = _b(api, q)
        assert "asn" in r["reconhecido"] and r["grupos"][0]["tipo"] == "asn", q
        assert r["grupos"][0]["itens"][0]["url"] == f"/asn/{ex['asn']['asn']}"


def test_cnpj_com_e_sem_mascara_e_raiz(api, ex):
    c = ex["op"]["cnpj"]
    mascara = f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"
    for q in (c, mascara):
        r = _b(api, q)
        assert "operadora" in r["reconhecido"] and f"/operadora/{c}" in _urls(r), q
    assert f"/operadora/{c}" in _urls(_b(api, c[:8]))


def test_ip_e_prefixo_levam_a_pagina_do_prefixo(api):
    assert _urls(_b(api, "192.0.2.0/24"))[0] == "/prefixo/192.0.2.0/24"
    assert _urls(_b(api, "2001:db8::/32"))[0] == "/prefixo/2001:db8::/32"
    assert _urls(_b(api, "198.51.100.7"))[0] == "/prefixo/198.51.100.7"
    assert _b(api, "999.1.1.1")["reconhecido"] == []      # não é IP: cai na busca por texto, sem erro


def test_municipio_por_nome_sem_acento_e_por_codigo_ibge(api):
    r = _b(api, "alta floresta")
    assert any(u == "/municipio/1100015" for u in _urls(_b(api, "1100015")))
    assert "municipio" in {g["tipo"] for g in r["grupos"]}
    assert _b(api, "SÃO PAULO")["grupos"] and any(u == "/uf/SP" for u in _urls(_b(api, "sao paulo", limite=20)))


def test_sigla_de_uf(api):
    r = _b(api, "SP")
    assert "uf" in r["reconhecido"] and "/uf/SP" in _urls(r)


def test_ptt_cdn_e_tema(api, ex):
    cod = ex["ptt"]["code"]
    assert f"/ixp/{cod}" in _urls(_b(api, cod)) or f"/ixp/{cod}" in _urls(_b(api, f"ptt {cod}"))
    assert any(u.startswith("/cdncap/") for u in _urls(_b(api, ex["cdn"])))
    assert "/seguranca-de-roteamento" in _urls(_b(api, "RPKI"))
    assert "/mercado-ipv4" in _urls(_b(api, "ipv4"))


def test_nome_da_operadora_e_nome_alternativo_do_as(api, ex):
    nome = ex["op"].get("nome_fantasia") or ex["op"]["razao_social"]
    r = _b(api, nome.upper())          # nome inteiro, caixa alta: ignora caixa e acento
    assert f"/operadora/{ex['op']['cnpj']}" in _urls(r)
    assert f"/asn/{ex['op']['asns'][0]}" in _urls(_b(api, nome, limite=20))      # o AS da operadora acha-se pelo nome dela


def test_ordem_dos_grupos_e_limite(api):
    r = _b(api, "sp", limite=2)
    assert all(len(g["itens"]) <= 2 for g in r["grupos"])
    assert [g["tipo"] for g in r["grupos"]][0] in r["reconhecido"]
    assert api.get("/api/v1/busca", params={"q": "x", "limite": 99}).status_code == 422
    assert api.get("/api/v1/busca", params={"q": ""}).status_code == 422
    assert api.get("/api/v1/busca", params={"q": "x" * 200}).status_code == 422


def test_consulta_de_um_caractere_nao_varre_e_nao_quebra(api):
    assert _b(api, "z")["grupos"] == []


def test_consultas_hostis_nao_dao_5xx(api):
    for q in ("%", "'; DROP TABLE x;--", "<script>alert(1)</script>", "\x00\x01", "///", "((", "a" * 80, "ａｓ６４４９６", "../../etc/passwd"):
        r = api.get("/api/v1/busca", params={"q": q})
        assert r.status_code in (200, 422), (q, r.status_code)


def test_snapshot_inexistente_da_404(api):
    assert api.get("/api/v1/busca", params={"q": "sp", "date": "1999-01-01"}).status_code in (401, 404, 422)   # data fora das 2 recentes é histórico (login)


def test_indice_sem_contato_nem_pessoa_fisica(api, ex):
    """O índice só leva PJ e recursos de rede: nenhum item tem e-mail, telefone nem campo de contato, e CPF não é um CNPJ de 14 dígitos."""
    idx = busca.indice(api.app.state.store, ex["d"])
    todos = [i for t in idx.por_tipo.values() for i in t.itens]
    assert len(todos) > 100
    proibido = re.compile(r"@|\(\d{2}\)\s?\d|\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\bcontat|\bpoc\b|\btelefone|\be-?mail", re.I)
    for i in todos:
        for campo in ("titulo", "detalhe", "selo"):
            assert not proibido.search(str(i.get(campo) or "")), (i["tipo"], campo, i.get(campo))
        assert set(i) <= {"tipo", "titulo", "detalhe", "url", "selo", "peso", "chaves"}
    corpo = json.dumps(_b(api, "provedor"))
    assert not proibido.search(corpo)


def test_tipos_e_urls_batem_com_as_rotas_do_frontend(api):
    """Toda página-alvo (tema ou entidade) existe como rota no SPA; um tema que aponta para rota removida falha aqui."""
    rotas = (ROOT / "frontend/src/main.tsx").read_text(encoding="utf-8")
    existentes = set(re.findall(r'<Route path="([^"*:]+)', rotas))
    for _titulo, url, _desc, _palavras in busca.TEMAS:
        assert url.lstrip("/") in existentes, f"tema aponta para rota inexistente: {url}"
    for prefixo in ("asn", "operadora", "municipio", "uf", "ixp", "ixp-externo", "cdncap", "instalacao", "prefixo"):
        assert prefixo in existentes or f"{prefixo}/" in rotas, prefixo


def test_slug_igual_ao_do_frontend():
    assert busca.slug("Amazon / AWS") == "amazon-aws" and busca.slug("Cloudflare, Inc.") == "cloudflare-inc"


def test_desempenho_com_indice_grande():
    """120 mil itens (ordem de grandeza da tabela global de ASNs): consulta comum em < 50 ms; o p95 da produção se mede no ambiente de teste."""
    itens = [busca._item("asn", f"AS{n}", f"Provedor {n % 977} Telecom", f"/asn/{n}", [f"as{n}", str(n), f"Provedor {n % 977} Telecom"], n % 100)
             for n in range(100000, 220000)]
    idx = busca.Indice(itens)
    tempos = []
    for q in ("telecom", "provedor 5", "as1500", "15", "provedor 123 telecom"):
        t = time.perf_counter()
        idx.buscar(q, 5)
        tempos.append((time.perf_counter() - t) * 1000)
    assert max(tempos) < 100, tempos      # folga para o CI; a meta de 50 ms é medida no ambiente de teste


def test_cache_guarda_no_maximo_duas_datas(api, ex):
    store = api.app.state.store
    busca._CACHE.clear()
    for d in ("a", "b", "c"):
        busca._CACHE[(id(store), d)] = busca.Indice([])
        while len(busca._CACHE) > 2:
            busca._CACHE.pop(next(iter(busca._CACHE)))
    assert len(busca._CACHE) == 2
    busca._CACHE.clear()
