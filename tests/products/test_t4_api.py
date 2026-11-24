# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — contrato da API real sobre o dataset sintético.

Uma requisição válida por operação (`tests/products/api_contract.py`), conferida contra o arquivo de
contrato `tests/contracts/api_contract.json`: rota nova sem entrada falha; rota removida, mudança de status
ou remoção de campo de topo falha. Campo novo é permitido. Atualizar: `--update-golden` e REVISAR o diff.
"""
import json
import math
from pathlib import Path

import pytest

from api.privacidade import e_chave_de_contato
from tests.products.api_contract import ALLOWED, ANON, discover, request_for

CONTRACT = Path(__file__).resolve().parents[1] / "contracts" / "api_contract.json"
PII_KEYS = {"email", "telefone", "phone"}                       # nunca em resposta pública
ADDRESS_KEYS = {"logradouro", "cep"}                            # endereço de pessoa jurídica (cadastro público)


def _golden() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8")) if CONTRACT.exists() else {"operacoes": {}}


def _call(api, key: str, ctx: dict, headers=ALLOWED):
    method, path = key.split(" ", 1)
    url, query, body = request_for(path, method, ctx)
    return api.request(method, url, params=query, json=body, headers=headers)


def _operations(api) -> list[str]:
    spec = api.get("/api/v1/openapi.json").json()
    return sorted(f"{m.upper()} {p}" for p, ops in spec["paths"].items() for m in ops)


def _shape(r) -> dict:
    ctype = r.headers.get("content-type", "")
    out = {"status": r.status_code}
    if "json" in ctype:
        j = r.json()
        out["tipo"] = "objeto" if isinstance(j, dict) else "lista"
        if isinstance(j, dict):
            out["chaves"] = sorted(j)
    return out


@pytest.fixture(scope="module")
def ctx(api):
    return discover(api)


def test_contrato_cobre_todas_as_operacoes_e_se_mantem(api, ctx, request, monkeypatch):
    # O contrato chama tudo com o IP da allowlist; contatos exigem conta, então aqui a opção da allowlist fica
    # ligada só para conferir o formato das três rotas (a exigência de conta é testada em test_contatos_exigem_conta_e_a_allowlist_nao_basta).
    monkeypatch.setenv("CONTATOS_ALLOWLIST", "1")
    ops = _operations(api)
    current = {k: _shape(_call(api, k, ctx)) for k in ops}
    if request.config.getoption("--update-golden"):
        CONTRACT.parent.mkdir(parents=True, exist_ok=True)
        CONTRACT.write_text(json.dumps({"_doc": __doc__.strip().splitlines()[0], "operacoes": current},
                                       ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return
    gold = _golden()["operacoes"]
    assert set(current) == set(gold), (
        f"operações novas sem contrato: {sorted(set(current) - set(gold))}; "
        f"removidas: {sorted(set(gold) - set(current))} (rode com --update-golden e revise)")
    for key in ops:
        g, c = gold[key], current[key]
        assert c["status"] == g["status"], f"{key}: status {c['status']} ≠ {g['status']}"
        assert c.get("tipo") == g.get("tipo"), f"{key}: tipo {c.get('tipo')} ≠ {g.get('tipo')}"
        faltam = sorted(set(g.get("chaves", [])) - set(c.get("chaves", [])))
        assert not faltam, f"{key}: campos removidos da resposta: {faltam}"


def test_cobertura_de_operacoes(api):
    # métrica do passo: operações com contrato / operações da API
    ops, gold = _operations(api), _golden()["operacoes"]
    assert len(ops) >= 90                       # ≈ 90 rotas
    assert sum(1 for k in ops if k in gold) / len(ops) == 1.0


# ── privacidade ────────────────────────────────────────────────────────────

def _keys(x, found=None):
    found = set() if found is None else found
    if isinstance(x, dict):
        for k, v in x.items():
            found.add(k.lower())
            _keys(v, found)
    elif isinstance(x, list):
        for v in x[:500]:
            _keys(v, found)
    return found


@pytest.fixture()
def logado(api):
    """Sessão com conta de verdade (cookie `auth_token`): contatos exigem conta, não basta o IP da allowlist."""
    from api.auth import contas, sessao
    from api.auth.jwt_utils import create_token
    sessao.limpar_cache()
    cfg = api.app.state.auth_config
    conta = contas.registrar_login(cfg.data_dir, "contatos@example.org", "Teste", "google")
    api.cookies.set("auth_token", create_token(conta.email, conta.nome, "google", cfg.jwt_secret, conta.conta_id))
    yield conta
    api.cookies.clear()
    contas.apagar(cfg.data_dir, conta.conta_id)


def test_contatos_exigem_conta_e_a_allowlist_nao_basta(api, ctx, logado, monkeypatch):
    contacts = [k for k in _operations(api) if k.endswith("/contacts")]
    assert len(contacts) == 3
    for k in contacts:
        r = _call(api, k, ctx, ANON)
        assert r.status_code == 200 and "cota" in r.json(), k                          # com cookie de conta (fixture `logado`)
    api.cookies.clear()
    for k in contacts:
        assert _call(api, k, ctx, ANON).status_code == 401, k
        assert _call(api, k, ctx, ALLOWED).status_code == 401, k                         # allowlist sem conta: não vê contatos
    monkeypatch.setenv("CONTATOS_ALLOWLIST", "1")
    for k in contacts:
        assert _call(api, k, ctx, ALLOWED).status_code == 200, k                         # opção do mantenedor


def test_peeringdb_users_nao_e_servido(api, pipeline, logado):
    """POC de visibilidade `Users` (restrito pelo dono da rede a usuários do PeeringDB) nunca sai; o sintético tem um no primeiro ASN."""
    import gzip
    from tests.synth.world import T1

    base, _ = pipeline
    doc = json.load(gzip.open(base / "normalized" / T1 / "summary" / "peeringdb_contacts.json.gz", "rt"))
    asn, pocs = next((a, v) for a, v in doc["contacts"].items() if any(p.get("visible") == "Users" for p in v))
    j = api.get(f"/api/v1/asns/{asn}/contacts", headers=ANON).json()
    emails = {c.get("email") for c in j["contacts"]}
    assert all(p["email"] in emails for p in pocs if p["visible"] == "Public")
    assert not any(p["email"] in emails for p in pocs if p["visible"] == "Users")


def test_cota_de_contatos_responde_429_sem_cache(api, ctx, logado, monkeypatch):
    monkeypatch.setenv("CONTATOS_CONTA_RAJADA", "2")
    url = f"/api/v1/asns/{ctx['asn']}/contacts"
    assert [api.get(url, headers=ANON).status_code for _ in range(2)] == [200, 200]
    r = api.get(url, headers=ANON)
    assert r.status_code == 429 and int(r.headers["retry-after"]) >= 1 and r.headers["cache-control"] == "private, no-store"
    assert "limite de consultas de contato" in r.json()["detail"]


def _rdap_sintetico(pipeline):
    import gzip

    base, _ = pipeline
    from tests.synth.world import T1

    doc = json.load(gzip.open(base / "normalized" / T1 / "summary" / "rdap_contatos.json.gz", "rt"))
    return doc, {a: v for a, v in doc["contatos"].items() if v["em"]}, [a for a, v in doc["contatos"].items() if not v["em"]]


def test_contatos_rdap_so_na_rota_protegida_e_com_cobertura(api, pipeline):
    """O e-mail do RDAP do Registro.br sai SÓ em /asns/{asn}/contacts com login (ou allowlist); a rota diz a data e a cobertura."""
    doc, lidos, so_incompletos = _rdap_sintetico(pipeline)
    asn = next(iter(lidos))
    url = f"/api/v1/asns/{asn}/contacts"
    assert api.get(url, headers=ANON).status_code == 401
    from api.auth import contas
    from api.auth.jwt_utils import create_token
    cfg = api.app.state.auth_config
    conta = contas.registrar_login(cfg.data_dir, "rdap@example.org", "Teste", "google")
    api.cookies.set("auth_token", create_token(conta.email, conta.nome, "google", cfg.jwt_secret, conta.conta_id))
    r = api.get(url, headers=ANON)
    assert r.status_code == 200 and r.headers["cache-control"] == "private, no-store"
    j = r.json()
    rdap = [c for c in j["contacts"] if c["source"] == "RDAP (Registro.br)"]
    assert {c["role"] for c in rdap} == {"administrativo", "abuso"} and all(c["email"].endswith("@rdap.example.org") and c["name"] is None and c["phone"] is None for c in rdap)
    assert j["rdap"]["status"] == "completo" and j["rdap"]["leitura_em"] and j["rdap"]["cobertura"]["asns_no_universo"] == doc["cobertura"]["asns_no_universo"]
    # ASN com só resposta incompleta: nenhum contato RDAP e a rota diz que não houve leitura (não que o ASN não tem contato)
    j2 = api.get(f"/api/v1/asns/{so_incompletos[0]}/contacts", headers=ANON).json()
    api.cookies.clear()
    assert not [c for c in j2["contacts"] if c["source"].startswith("RDAP")] and j2["rdap"]["leitura_em"] is None and j2["rdap"]["status"] == "incompleto"


def test_nenhuma_rota_publica_expoe_o_valor_dos_contatos_rdap(api, ctx, pipeline):
    """Varre o TEXTO de toda resposta pública (anônima) atrás dos e-mails sintéticos do RDAP e do PeeringDB: só a rota /contacts pode tê-los."""
    _, lidos, _ = _rdap_sintetico(pipeline)
    asn = next(iter(lidos))
    publico = api.get(f"/api/v1/asns/{asn}", headers=ALLOWED)
    assert publico.status_code == 200 and "rdap.example.org" not in publico.text          # o documento do ASN só traz a CONTAGEM
    assert publico.json()["contacts_available"]["rdap"] == 2
    vazou = []
    for k in _operations(api):
        if k.endswith("/contacts") or not k.startswith("GET "):
            continue
        r = _call(api, k, ctx, ALLOWED)
        if r.status_code == 200 and ("rdap.example.org" in r.text or "peeringdb.example.org" in r.text):
            vazou.append(k)
    assert vazou == []


def test_exposicao_shodan_so_contagens_com_atribuicao_e_ausencia_nao_e_zero(api, ctx):
    """Por ASN e UF, só contagens, atribuição ao Shodan, data da leitura; ASN sem leitura é 404 (não zero); nunca host individual."""
    asn = ctx["asn_exposicao"]
    r = api.get(f"/api/v1/asns/{asn}/exposicao", headers=ALLOWED)
    assert r.status_code == 200
    j = r.json()
    assert "Shodan" in j["fonte"]["atribuicao"] and "NÃO é prova de vulnerabilidade" in j["aviso"] and j["lido_em"] and j["cobertura"]["asns_com_leitura"] >= 1
    assert j["servicos_observados"] >= 0 and "classes_de_risco" in j
    texto = r.text
    assert "matches" not in texto and "ip_str" not in texto and "hostnames" not in texto                  # nunca host individual
    assert api.get("/api/v1/asns/4294967295/exposicao", headers=ALLOWED).status_code == 404               # sem leitura: 404, não um bloco zerado
    com_extra = api.get(f"/api/v1/asns/{asn}", params={"include": "exposicao"}, headers=ALLOWED).json()
    assert com_extra["exposicao"]["lido_em"] == j["lido_em"]
    uf = next(u for u in ("SP", "RJ", "MG", "PR", "RS", "BA", "SC", "AM", "PE", "CE") if api.get(f"/api/v1/exposicao/ufs/{u}", headers=ALLOWED).status_code == 200)
    ju = api.get(f"/api/v1/exposicao/ufs/{uf}", headers=ALLOWED).json()
    assert ju["derivado"] is True and ju["asns_com_leitura"] <= ju["asns_do_cadastro"] and "Shodan" in ju["fonte"]["atribuicao"]
    assert api.get("/api/v1/exposicao/ufs/XX", headers=ALLOWED).status_code == 404


def test_nenhuma_rota_publica_expoe_email_ou_telefone(api, ctx, pipeline):
    import gzip

    base, _ = pipeline
    from tests.synth.world import T1

    scm = json.load(gzip.open(base / "published" / T1 / "scm.json.gz", "rt"))
    # o dataset tem os campos (senão o teste seria vazio): é a API que os remove
    assert PII_KEYS & set(scm["scms"][0]), "dataset sintético deveria ter e-mail/telefone no scm.json.gz"
    expostas = {}
    for k in _operations(api):
        if k.endswith("/contacts"):
            continue
        r = _call(api, k, ctx, ANON)
        if r.status_code == 200 and "json" in r.headers.get("content-type", ""):
            hit = {k for k in _keys(r.json()) if e_chave_de_contato(k)}      # `ddd_telefone_1` escapava da lista exata
            if hit:
                expostas[k] = sorted(hit)
    assert expostas == {}


def test_rotas_que_expoem_endereco_de_pessoa_juridica_sao_conhecidas(api, ctx):
    """Endereço (logradouro/CEP) sai do cadastro público de outorgas/CNPJ e pode ser exposto nas rotas
    abaixo. A lista é fixa: rota nova que exponha endereço falha aqui
    e exige decisão consciente."""
    expostas = []
    for k in _operations(api):
        if k.endswith("/contacts"):
            continue
        r = _call(api, k, ctx, ANON)
        if r.status_code == 200 and "json" in r.headers.get("content-type", "") and ADDRESS_KEYS & _keys(r.json()):
            expostas.append(k)
    assert sorted(expostas) == sorted([
        "GET /api/v1/acessos/operadora/{cnpj}", "GET /api/v1/asns/{asn}", "GET /api/v1/scms",
        "GET /api/v1/scms/{cnpj}", "GET /api/v1/seacs", "GET /api/v1/seacs/{cnpj}", "GET /api/v1/smps",
        "GET /api/v1/smps/{cnpj}", "GET /api/v1/stfcs", "GET /api/v1/stfcs/{cnpj}",
        "GET /api/v1/outorgas/{cnpj}",      # as mesmas outorgas de /scms/{cnpj} etc., num contrato só
        "GET /api/v1/operadoras/{cnpj}",    # consolida as outorgas das rotas acima; mesmo dado, nenhum endereço novo
    ])


# ── cache e paginação ──────────────────────────────────────────────────────

def test_cabecalhos_de_cache(api, ctx):
    sem_cache = []
    for k in _operations(api):
        method, path = k.split(" ", 1)
        if method != "GET" or not path.startswith("/api/v1/"):
            continue
        r = _call(api, k, ctx, ALLOWED)
        cc = r.headers.get("cache-control")
        if path.endswith("/contacts"):
            assert cc == "private, no-store", k       # resposta autenticada e sensível
        elif r.status_code == 200 and not cc:
            sem_cache.append(k)
    # ao menos o grosso das rotas públicas declara Cache-Control; as exceções são conhecidas
    assert len(sem_cache) <= 6, sem_cache


def test_data_existente_e_imutavel_e_inexistente_nao(api, ctx):
    """`?date=` de snapshot publicado → imutável por 1 ano; data inventada não fica no navegador."""
    existente = api.get("/health").json()["latest_snapshot"]
    r = api.get("/api/v1/ixps", params={"date": existente}, headers=ALLOWED)
    assert r.status_code == 200
    assert r.headers["cache-control"] == "public, max-age=31536000, immutable"
    r = api.get("/api/v1/ixps", params={"date": "1999-01-01"}, headers=ALLOWED)
    assert "immutable" not in r.headers.get("cache-control", "")


def test_busca_com_data_nao_e_imutavel(api):
    """O índice da busca muda com o código, não só com o snapshot: com `immutable` o navegador guardaria o resultado de uma versão antiga por um ano."""
    existente = api.get("/health").json()["latest_snapshot"]
    r = api.get("/api/v1/busca", params={"q": "rede", "date": existente, "esquema": "2"}, headers=ALLOWED)
    assert r.status_code == 200
    assert r.headers["cache-control"] == "public, max-age=300"


def test_etag_sem_data_e_304(api):
    """Sem `date` a resposta resolve o latest: ETag derivado do latest+versão, 304 em If-None-Match."""
    r = api.get("/api/v1/ixps", headers=ALLOWED)
    assert r.status_code == 200
    etag = r.headers["etag"]
    r2 = api.get("/api/v1/ixps", headers={**ALLOWED, "If-None-Match": etag})
    assert r2.status_code == 304 and r2.headers["etag"] == etag
    r3 = api.get("/api/v1/ixps", headers={**ALLOWED, "If-None-Match": 'W/"outro"'})
    assert r3.status_code == 200


def test_camadas_estaticas_por_hash_de_conteudo(api):
    """`/map/layers` dá o hash; `?v=` serve a camada sem data, imutável; hash desconhecido = 404."""
    camadas = api.get("/api/v1/map/layers", headers=ALLOWED).json()["camadas"]
    assert camadas, "o dataset sintético publica ao menos uma camada estática"
    for layer, info in camadas.items():
        r = api.get(info["url"], headers=ALLOWED)
        assert r.status_code == 200, (layer, r.status_code)
        assert r.headers["cache-control"] == "public, max-age=31536000, immutable"
    nome = next(iter(camadas))
    url_base = camadas[nome]["url"].split("?")[0]
    assert api.get(url_base, params={"v": "0" * 16}, headers=ALLOWED).status_code == 404
    assert api.get(url_base, params={"v": "xyz"}, headers=ALLOWED).status_code == 422


def test_hash_de_camada_desconhecido_nao_retem_nem_relê_manifestos(api):
    """Procurar um hash inexistente percorre todas as datas: não pode reter manifestos inteiros nem relê-los a cada pedido."""
    store = api.app.state.store
    antes = {d for d, a in store._docs._cache if a == 'manifest.json'}
    url = "/api/v1/map/submarine-cables"
    assert api.get(url, params={"v": "0" * 16}, headers=ALLOWED).status_code == 404
    assert {d for d, a in store._docs._cache if a == 'manifest.json'} == antes
    lidos = []
    original = store._read_json
    store._read_json = lambda p, *a, **k: (lidos.append(p), original(p, *a, **k))[1]
    try:
        assert api.get(url, params={"v": "f" * 16}, headers=ALLOWED).status_code == 404
    finally:
        store._read_json = original
    assert lidos == []


def test_paginacao_do_indice_de_asns(api):
    r = api.get("/api/v1/asns", params={"page": 1, "limit": 20}, headers=ALLOWED).json()
    assert r["limit"] == 20 and r["page"] == 1 and len(r["items"]) <= 20
    assert r["pages"] == math.ceil(r["total"] / 20)
    last = api.get("/api/v1/asns", params={"page": r["pages"], "limit": 20}, headers=ALLOWED).json()
    assert 0 < len(last["items"]) <= 20
    # fora do intervalo: o contrato é uma resposta definida (não erro 5xx)
    assert api.get("/api/v1/asns", params={"limit": 100000}, headers=ALLOWED).status_code in (200, 422)
    assert api.get("/api/v1/asns", params={"page": 0}, headers=ALLOWED).status_code in (200, 422)


def test_paginar_alem_da_primeira_pagina_exige_login_para_anonimo(api):
    assert api.get("/api/v1/asns", params={"page": 2, "limit": 10}, headers=ANON).status_code == 401
    assert api.get("/api/v1/asns", params={"page": 2, "limit": 10}, headers=ALLOWED).status_code == 200


def test_parametro_absurdo_vira_422_e_nao_500(api):
    """Caso do fuzz (schemathesis): k_pf=1e308 não pode estourar o JSON da resposta (500)."""
    r = api.get("/api/v1/acessos/divergencias/scm", params={"k_pf": 1.17e308}, headers=ALLOWED)
    assert r.status_code == 422


def test_divergencias_scm_ordena_a_lista_inteira_antes_do_corte(api):
    """A versão reduzida (limit pequeno) ordenada por outra coluna traz o primeiro da lista inteira, não reordena o top N."""
    base = {"min_razao": 1, "limit": 2000}
    todos = api.get("/api/v1/acessos/divergencias/scm", params=base, headers=ALLOWED).json()["items"]
    assert len(todos) >= 2
    for campo in ("razao", "esperado", "acessos_pf", "asn"):
        for asc in (False, True):
            cheios = [r[campo] for r in todos if r.get(campo) is not None]
            if not cheios:
                continue
            r = api.get("/api/v1/acessos/divergencias/scm", params={**base, "limit": 1, "ordem": campo, "asc": asc}, headers=ALLOWED)
            assert r.status_code == 200
            assert r.json()["items"][0][campo] == (min(cheios) if asc else max(cheios))
    assert api.get("/api/v1/acessos/divergencias/scm", params={"ordem": "nada"}, headers=ALLOWED).status_code == 422


def test_rota_interna_de_diagnostico_e_restrita_e_fora_do_openapi(api, monkeypatch):
    import api.main as main

    paths = api.get("/api/v1/openapi.json").json()["paths"]
    assert "/api/v1/internal/diag" not in paths and "/api/v1/warmup" not in paths
    # sem token e sem loopback (o cliente de teste não é 127.0.0.1): 403
    assert api.get("/api/v1/internal/diag").status_code == 403
    monkeypatch.setattr(main, "_INTERNAL_TOKEN", "tok-interno-de-teste")
    assert api.get("/api/v1/internal/diag", headers={"X-Internal-Token": "errado"}).status_code == 403
    r = api.get("/api/v1/internal/diag", headers={"X-Internal-Token": "tok-interno-de-teste"})
    assert r.status_code == 200
    j = r.json()
    assert j["processo"]["pid"] > 0 and j["store"]["datas_residentes"] and j["profundo"] is False
    deep = api.get("/api/v1/internal/diag?deep=1&sample=16", headers={"X-Internal-Token": "tok-interno-de-teste"}).json()
    assert deep["store"]["total_bytes_estimados"] > 0 and deep["store"]["caches"][0]["bytes_estimados"] > 0


def test_detalhe_de_snapshot_vem_do_arquivo_do_pipeline_e_nao_recalcula(api, ctx, monkeypatch):
    """`/snapshots/{date}` lia índices grandes por data (centenas de MiB). O pipeline grava
    `snapshot_detail.json`; com ele, a rota não toca em nenhum dos cálculos pesados do Store."""
    from api import snapshot_detail
    from api.routes import snapshots as rota
    from tests.synth.world import T1

    store = api.app.state.store
    esperado = snapshot_detail.compute_detail(store, T1)          # cálculo "antigo", sobre o mesmo dado
    assert esperado and esperado["summary"].get("br_asns_ft_v4") is not None

    rota._DETAIL_CACHE.clear()
    pesados = ("asn_index", "ixp_br_origin_sets", "ixp_estimated_users_aggregate", "external_ixps_br_asn_union",
               "operadora_index", "operadora_movel_index", "manifest")
    for nome in pesados:
        monkeypatch.setattr(store, nome, lambda *a, _n=nome, **k: (_ for _ in ()).throw(AssertionError(f"{_n} chamado")))
    r = api.get(f"/api/v1/snapshots/{T1}", headers=ALLOWED)
    assert r.status_code == 200
    assert r.json()["summary"] == esperado["summary"]
    assert r.json()["manifest"]["ixps_configured"] == esperado["manifest"]["ixps_configured"]
    rota._DETAIL_CACHE.clear()


def test_detalhe_recalcula_quando_nao_ha_arquivo(api, ctx, pipeline):
    """Snapshots publicados antes do 1.1.5.6 não têm o arquivo: a rota recalcula e devolve o mesmo conteúdo."""
    import shutil

    from api.routes import snapshots as rota
    from tests.synth.world import T0

    base, _ = pipeline
    side = base / "published" / T0 / "snapshot_detail.json"
    guardado = side.read_bytes()
    side.unlink()
    try:
        rota._DETAIL_CACHE.clear()
        sem = api.get(f"/api/v1/snapshots/{T0}", headers=ALLOWED).json()
        rota._DETAIL_CACHE.clear()
    finally:
        side.write_bytes(guardado)
    com = api.get(f"/api/v1/snapshots/{T0}", headers=ALLOWED).json()
    rota._DETAIL_CACHE.clear()
    assert sem["summary"] == com["summary"] and sem["manifest"] == com["manifest"]


def test_opcional_transforma_o_404_de_servico_ausente_em_204(api):
    """As páginas pedem `?opcional=1` nos serviços que a entidade pode não ter, para não gerar 4xx no console."""
    for rota in ("/api/v1/seacs/00000000000191", "/api/v1/stfcs/00000000000191", "/api/v1/acessos-movel/operadora/00000000000191",
                 "/api/v1/acessos-movel/municipio/0000000", "/api/v1/asns/4199999999/acessos"):
        assert api.get(rota).status_code == 404, rota
        r = api.get(rota + "?opcional=1")
        assert r.status_code == 204 and r.content == b"", rota


def test_prefixes_lookup_acha_o_prefixo_mais_especifico(api):
    client = api
    """IP solto → prefixo que o contém (longest-prefix match); IP inválido 422; sem cobertura 404."""
    h = {"X-Forwarded-For": "203.0.113.129"}
    lista = client.get("/api/v1/prefixes", params={"limit": 50}, headers=h).json()["items"]
    v4 = next(i["prefix"] for i in lista if ":" not in i["prefix"])
    ip = v4.split("/")[0]
    r = client.get("/api/v1/prefixes/lookup", params={"ip": ip}, headers=h)
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["consulta"] == ip
    assert corpo["prefix"].split("/")[0] == ip or corpo["prefix"] in {i["prefix"] for i in lista}
    assert client.get("/api/v1/prefixes/lookup", params={"ip": "não-é-ip"}, headers=h).status_code == 422
    assert client.get("/api/v1/prefixes/lookup", params={"ip": "10.255.255.254"}, headers=h).status_code == 404


def test_sitemap_das_entidades_lista_asns_br_ptts_e_operadoras(api):
    import xml.etree.ElementTree as ET

    r = api.get("/sitemap-entidades.xml")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/xml")
    locs = [e.text for e in ET.fromstring(r.text).findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    assert len(locs) == len(set(locs)) <= 50_000
    assert any("/asn/" in u for u in locs) and any("/ixp/" in u for u in locs)
    from core.site import SITE
    assert all(u.startswith(SITE.url + "/") for u in locs)


def test_perfil_do_municipio_tem_os_mesmos_numeros_das_rotas_antigas(api, ctx):
    """Uma chamada devolve fixo, móvel e PTTs; fixo/móvel iguais às rotas antigas; blocos e fields recortam."""
    ibge = ctx["ibge"]
    store = api.app.state.store
    # o sintético usa IBGE fictício (99…), fora dos centróides reais: sem eles o perfil sai com centroide nulo
    sem = api.get(f"/api/v1/municipios/{ibge}", headers=ALLOWED).json()
    assert sem["centroide"] is None and sem["ptts_proximos"] == []
    original = store._perfis._centroides
    store._perfis._centroides = {ibge: [-46.6, -23.5]}
    try:
        perfil = api.get(f"/api/v1/municipios/{ibge}", headers=ALLOWED).json()
    finally:
        store._perfis._centroides = original
    antigo = api.get(f"/api/v1/acessos/municipio/{ibge}", headers=ALLOWED).json()
    fixo = perfil["fixo"]
    assert fixo["acessos"] == antigo["acessos"] and fixo["operadores"] == antigo["operadores"]
    assert fixo["mes_referencia"] == antigo["mes_referencia"] and perfil["nome"] == antigo["nome"]
    assert fixo["fibra_pct"] == 80.0                        # o sintético declara 80% de fibra (tests/synth/market.py)
    assert perfil["centroide"] and perfil["ptts_proximos"]
    km = [p["km"] for p in perfil["ptts_proximos"]]
    assert km == sorted(km) and len(km) <= 5
    codigos = [p["codigo"] for p in perfil["ptts_proximos"]]
    assert len(codigos) == len(set(codigos))                # PTT com vários locais (vix) aparece uma vez
    movel_antigo = api.get(f"/api/v1/acessos-movel/municipio/{ibge}", headers=ALLOWED)
    if movel_antigo.status_code == 200:
        assert perfil["movel"]["acessos"] == movel_antigo.json()["acessos"]
    else:
        assert perfil["movel"] is None
    so_fixo = api.get(f"/api/v1/municipios/{ibge}", params={"blocos": "fixo"}, headers=ALLOWED).json()
    assert "fixo" in so_fixo and "movel" not in so_fixo and "ptts_proximos" not in so_fixo
    enxuto = api.get(f"/api/v1/municipios/{ibge}", params={"fields": "fixo"}, headers=ALLOWED).json()
    assert set(enxuto) == {"snapshot_date", "ibge", "uf", "fixo"}
    assert api.get(f"/api/v1/municipios/{ibge}", params={"blocos": "x"}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/municipios/0000000", headers=ALLOWED).status_code == 404


def test_perfil_da_operadora_tem_os_mesmos_numeros_das_rotas_antigas(api, ctx):
    """Scm/smp/stfc/seac numa resposta, iguais às 4 rotas antigas; rede uma vez; sem contatos; blocos e fields recortam."""
    cnpj = ctx["cnpj"]
    perfil = api.get(f"/api/v1/operadoras/{cnpj}", headers=ALLOWED).json()
    scm = api.get(f"/api/v1/acessos/operadora/{cnpj}", headers=ALLOWED).json()
    assert perfil["cnpj"] == cnpj
    assert perfil["scm"]["acessos"] == scm["acessos"] and perfil["scm"]["outorgas_scm"] == scm["outorgas_scm"]
    assert perfil["scm"]["asns"] == scm["asns"] and perfil["rede"] == scm["rede"]
    assert "rede" not in perfil["scm"] and "snapshot_date" not in perfil["scm"]
    for chave, rota in (("smp", "acessos-movel/operadora"), ("stfc", "stfcs"), ("seac", "seacs")):
        antigo = api.get(f"/api/v1/{rota}/{cnpj}", headers=ALLOWED)
        if antigo.status_code == 200:
            assert perfil[chave]["outorgas_smp" if chave == "smp" else "outorgas"] == antigo.json()["outorgas_smp" if chave == "smp" else "outorgas"]
        else:
            assert perfil[chave] is None
    assert perfil["scm"]["contacts_available"] is not None
    so_scm = api.get(f"/api/v1/operadoras/{cnpj}", params={"blocos": "scm"}, headers=ALLOWED).json()
    assert "scm" in so_scm and "smp" not in so_scm and "stfc" not in so_scm
    enxuto = api.get(f"/api/v1/operadoras/{cnpj}", params={"fields": "scm"}, headers=ALLOWED).json()
    assert set(enxuto) <= {"snapshot_date", "cnpj", "scm"} and "scm" in enxuto
    assert api.get(f"/api/v1/operadoras/{cnpj}", params={"blocos": "x"}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/operadoras/123", headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/operadoras/00000000000000", headers=ALLOWED).status_code == 404


def test_perfil_e_resumo_das_ufs_batem_com_as_rotas_antigas(api, ctx):
    """/ufs/{uf} traz o que a página de UF pedia em 5 chamadas; /ufs resume as 27 para /estados."""
    store = api.app.state.store
    mun = api.get("/api/v1/acessos/municipios", params={"limit": 6000}, headers=ALLOWED).json()["items"]
    uf = mun[0]["uf"]
    original = store._perfis._centroides
    store._perfis._centroides = {m["ibge"]: [-40.3 - i, -20.3 - i] for i, m in enumerate(mun)}   # IBGE fictício: sem centróide real
    store._perfis._ptts_pontos.clear(); store._perfis._resumo_ufs.clear()
    try:
        perfil = api.get(f"/api/v1/ufs/{uf.lower()}", headers=ALLOWED).json()
        resumo = api.get("/api/v1/ufs", headers=ALLOWED).json()
    finally:
        store._perfis._centroides = original
        store._perfis._ptts_pontos.clear(); store._perfis._resumo_ufs.clear()
    da_uf = [m for m in mun if m["uf"] == uf]
    assert perfil["uf"] == uf and perfil["totais"]["municipios"] == len(da_uf)
    assert perfil["totais"]["acessos"] == sum(m["acessos"] for m in da_uf)
    assert {m["ibge"] for m in perfil["municipios"]} == {m["ibge"] for m in da_uf}
    assert all(m["km_ptt"] is not None and m["ptt"] for m in perfil["municipios"])
    assert perfil["totais"]["fibra_pct"] == 80.0
    antigo_ixps = api.get("/api/v1/ixps", params={"uf": uf}, headers=ALLOWED).json()["ixps"]
    assert [i["code"] for i in perfil["ixps"]] == [i["code"] for i in antigo_ixps]
    ops = api.get("/api/v1/acessos/operadoras", params={"uf": uf, "ativo": "true", "limit": 10}, headers=ALLOWED).json()
    assert perfil["operadoras"]["total"] == ops["total"]
    assert [o["cnpj"] for o in perfil["operadoras"]["items"]] == [o["cnpj"] for o in ops["items"]]
    linha = next(r for r in resumo["items"] if r["uf"] == uf)
    assert linha["acessos"] == perfil["totais"]["acessos"] and linha["usuarios"] == perfil["totais"]["usuarios"]
    assert linha["ptts"] == len([i for i in antigo_ixps if i.get("status") != "missing"])
    assert linha["municipios_sem_ptt"] == perfil["totais"]["municipios_sem_ptt"]
    so = api.get(f"/api/v1/ufs/{uf}", params={"blocos": "municipios"}, headers=ALLOWED).json()
    assert "municipios" in so and "ixps" not in so and "operadoras" not in so and "totais" in so
    assert api.get("/api/v1/ufs/XX", headers=ALLOWED).status_code == 404
    assert api.get(f"/api/v1/ufs/{uf}", params={"blocos": "x"}, headers=ALLOWED).status_code == 400


def test_lote_de_asns_igual_aos_documentos_individuais_e_projeta(api, ctx):
    """`/asns?asns=` devolve os mesmos documentos de `/asns/{asn}`; `fields` projeta; `include` acrescenta; limite de 100."""
    asns = [int(x) for x in ctx["asns"].split(",")]
    r = api.get("/api/v1/asns", params={"asns": ",".join(map(str, asns + [4000000000]))}, headers=ALLOWED).json()
    assert [d["asn"] for d in r["items"]] == asns and r["not_found"] == [4000000000] and r["total"] == len(asns)
    for d in r["items"]:
        assert d == api.get(f"/api/v1/asns/{d['asn']}", headers=ALLOWED).json()
    enxuto = api.get("/api/v1/asns", params={"asns": ctx["asns"], "fields": "name,is_br"}, headers=ALLOWED).json()["items"]
    assert all(set(d) == {"asn", "name", "is_br"} for d in enxuto)
    extra = api.get("/api/v1/asns", params={"asns": ctx["asn"], "fields": "name", "include": "bgp_stability,paths"}, headers=ALLOWED).json()["items"][0]
    assert {"epppd", "epppd_v4", "epppd_v6", "paths"} <= set(extra)
    assert extra["paths"] == api.get(f"/api/v1/asns/{ctx['asn']}/paths", headers=ALLOWED).json()
    unico = api.get(f"/api/v1/asns/{ctx['asn']}", params={"fields": "name"}, headers=ALLOWED).json()
    assert set(unico) == {"asn", "name"}
    assert api.get("/api/v1/asns", params={"asns": ",".join(str(i) for i in range(101))}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/asns", params={"asns": "x"}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/asns", params={"include": "zz"}, headers=ALLOWED).status_code == 400


def test_perfil_consolidado_do_asn_traz_os_blocos_das_rotas_separadas(api, ctx):
    """`/asns/{asn}?include=` devolve o documento de sempre mais os corpos de paths, ixp-peers e estabilidade."""
    asn = ctx["asn"]
    base = api.get(f"/api/v1/asns/{asn}", headers=ALLOWED).json()
    perfil = api.get(f"/api/v1/asns/{asn}", params={"include": "paths,ixp_peers,estabilidade"}, headers=ALLOWED)
    assert perfil.status_code == 200
    p = perfil.json()
    assert {k: v for k, v in p.items() if k not in ("paths", "ixp_peers", "estabilidade")} == base
    assert p["paths"] == api.get(f"/api/v1/asns/{asn}/paths", headers=ALLOWED).json()
    assert p["ixp_peers"] == api.get(f"/api/v1/asns/{asn}/ixp-peers", headers=ALLOWED).json()["peers"]
    est = api.get(f"/api/v1/bgp-stability/asn/{asn}", headers=ALLOWED)
    assert p["estabilidade"] == (est.json() if est.status_code == 200 else None)     # o sintético pode não ter a análise
    so = api.get(f"/api/v1/asns/{asn}", params={"include": "paths", "fields": "name"}, headers=ALLOWED).json()
    assert set(so) == {"asn", "name", "paths"}
    assert api.get(f"/api/v1/asns/{asn}", params={"include": "zz"}, headers=ALLOWED).status_code == 400


def test_perfil_consolidado_do_ptt_traz_os_blocos_das_rotas_separadas(api, ctx):
    """`/ixps/{code}?include=` devolve o documento de sempre mais membros (com nomes), usuários, potencial e assinantes."""
    code = ctx["code"]
    base = api.get(f"/api/v1/ixps/{code}", headers=ALLOWED).json()
    r = api.get(f"/api/v1/ixps/{code}", params={"include": "membros,usuarios_estimados,potencial,assinantes"}, headers=ALLOWED)
    assert r.status_code == 200
    p = r.json()
    assert {k: v for k, v in p.items() if k not in ("membros", "usuarios_estimados", "potencial", "assinantes")} == base
    sep = api.get(f"/api/v1/ixps/{code}/members", params={"nomes": "true"}, headers=ALLOWED).json()
    assert {k: v for k, v in p["membros"].items() if k != "nomes"} == {k: v for k, v in sep.items() if k != "nomes"}
    assert sep["nomes"].items() <= p["membros"]["nomes"].items()                  # o perfil acrescenta o nome dos membros cadastrados sem par direto
    assert {str(a) for a in base.get("asn_members", [])} & set(api.get("/api/v1/asns/names", headers=ALLOWED).json()["names"]) <= set(p["membros"]["nomes"])
    assert p["usuarios_estimados"] == api.get(f"/api/v1/ixps/{code}/estimated-users", headers=ALLOWED).json()
    assert p["potencial"] == api.get(f"/api/v1/ixps/{code}/potential", headers=ALLOWED).json()
    assert p["assinantes"] == api.get(f"/api/v1/ixps/{code}/assinantes", headers=ALLOWED).json()
    assert set(api.get(f"/api/v1/ixps/{code}", params={"include": "potencial"}, headers=ALLOWED).json()) == set(base) | {"potencial"}
    assert api.get(f"/api/v1/ixps/{code}", params={"include": "zz"}, headers=ALLOWED).status_code == 400
    ext = api.get(f"/api/v1/ixps/{code}", params={"include": "indice,totais"}, headers=ALLOWED).json()
    linha = next(e for e in api.get("/api/v1/ixps", headers=ALLOWED).json()["ixps"] if e["code"] == code)
    assert {k: ext["indice"][k] for k in linha} == linha                            # a rota de lista filtra pelo modelo; o índice traz tudo
    resumo = api.get(f"/api/v1/snapshots/{base['snapshot_date']}", headers=ALLOWED).json()["summary"]
    assert ext["totais"] == {"total_asns_br": resumo.get("total_asns_br"), "total_asns_global": (resumo.get("global_table") or {}).get("total_asns"),
                             "br_apnic_users_total": resumo.get("br_apnic_users_total")}


def test_historico_series_eventos_e_diferenca(api, ctx):
    """Séries por entidade, eventos com estado e a diferença entre duas datas (dataset sintético T0 → T1)."""
    from tests.synth.world import T0, T1

    s = api.get("/api/v1/history/asns/64503", headers=ALLOWED).json()
    assert [p["date"] for p in s["snapshots"]] == [T0, T1] and s["total"] == 2 and s["asn"] == 64503
    assert "hash_pfx" not in s["snapshots"][0]                                      # hashes não saem
    so = api.get("/api/v1/history/asns/64503", params={"metrics": "roa,rpki,prefixes_v4", "from": T1}, headers=ALLOWED).json()
    assert [p["date"] for p in so["snapshots"]] == [T1] and set(so["snapshots"][0]) >= {"n_roa", "rpki_invalid", "p4"} and "users" not in so["snapshots"][0]
    assert api.get("/api/v1/history/asns/64503", params={"metrics": "zz"}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/history/asns/4000000000", headers=ALLOWED).status_code == 404
    assert api.get("/api/v1/history/asns/64503", params={"from": "ontem"}, headers=ALLOWED).status_code == 400
    ixp = api.get(f"/api/v1/history/ixps/{ctx['code']}", headers=ALLOWED).json()
    assert ixp["ixp"] == ctx["code"] and ixp["snapshots"][0]["status"]
    op = api.get(f"/api/v1/history/operadoras/{ctx['cnpj']}", headers=ALLOWED)
    assert op.status_code in (200, 404) and api.get("/api/v1/history/operadoras/123", headers=ALLOWED).status_code == 400
    uf = api.get("/api/v1/history/uf/pr", headers=ALLOWED).json()
    assert uf["uf"] == "PR" and uf["snapshots"][-1]["n_ma4"] == 2

    todos = api.get("/api/v1/changes", params={"estado": "todos"}, headers=ALLOWED).json()
    assert todos["total"] == len(todos["items"]) > 0 and {e["estado"] for e in todos["items"]} <= {"pendente", "confirmado", "revertido"}
    assert all(e["estado"] == "confirmado" for e in api.get("/api/v1/changes", headers=ALLOWED).json()["items"])
    origem = api.get("/api/v1/changes", params={"tipo": "mudanca_origem", "estado": "todos"}, headers=ALLOWED).json()["items"]
    assert origem and origem[0]["destaque"] is True and origem[0]["natureza"] == "observado"
    assert api.get("/api/v1/changes", params={"estado": "x"}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/changes", params={"asn": 64503, "estado": "todos"}, headers=ALLOWED).json()["total"] >= 1
    assert api.get("/api/v1/changes", params={"limit": 1, "estado": "todos"}, headers=ALLOWED).json()["items"].__len__() == 1
    # filtro por PTT (entradas e saídas): todo evento devolvido é do PTT pedido, e um código inexistente não devolve nada
    tipos = "ixp_entrada,ixp_saida,ixp_entrada_observada,ixp_saida_observada"
    todos_ixp = api.get("/api/v1/changes", params={"tipo": tipos, "estado": "todos", "limit": 500}, headers=ALLOWED).json()["items"]
    if todos_ixp:
        cod = todos_ixp[0]["detalhe"]["ixp"]
        do_ptt = api.get("/api/v1/changes", params={"tipo": tipos, "estado": "todos", "ixp": cod, "limit": 500}, headers=ALLOWED).json()["items"]
        assert do_ptt and all(e["detalhe"]["ixp"] == cod for e in do_ptt)
    assert api.get("/api/v1/changes", params={"tipo": tipos, "estado": "todos", "ixp": "zz-inexistente"}, headers=ALLOWED).json()["total"] == 0
    resumo = api.get("/api/v1/changes/summary", headers=ALLOWED).json()
    assert resumo["total"] == todos["total"] and resumo["por_tipo"]["mudanca_origem"]["pendente"] >= 1 and resumo["snapshots_com_historico"] == 2

    d = api.get("/api/v1/snapshots/diff", params={"a": T0, "b": T1}, headers=ALLOWED).json()
    assert d["totais"]["n_asns"]["variacao"] == d["totais"]["n_asns"]["b"] - d["totais"]["n_asns"]["a"] and d["eventos"]["entre"] == [T0, T1]
    assert d["eventos"]["total"] == todos["total"]
    assert api.get("/api/v1/snapshots/diff", params={"a": "2000-01-01", "b": T1}, headers=ALLOWED).status_code == 404


def test_perfis_consolidados_trazem_o_bloco_historico(api, ctx):
    """`include=historico` nos perfis de ASN, PTT, operadora e UF; sem ele a resposta é a de sempre."""
    from tests.synth.world import T0, T1

    p = api.get("/api/v1/asns/64503", params={"include": "historico_completo"}, headers=ALLOWED).json()
    h = p["historico"]
    assert h["completo"] is True and [x["date"] for x in h["serie"]] == [T0, T1] and h["snapshots_com_historico"] == 2
    assert api.get("/api/v1/asns/64503", params={"include": "historico"}, headers=ALLOWED).json()["historico"]["completo"] is False
    assert "n_provedores" not in h["colunas"] and all(e["tipo"] not in ("provedor_novo", "provedor_perdido") for e in h["eventos"])
    assert any(e["tipo"] == "mudanca_origem" and e["destaque"] for e in h["eventos"])        # a origem do 198.18.24.0/21 passou para o 64503
    assert "historico" not in api.get("/api/v1/asns/64503", params={"include": "paths"}, headers=ALLOWED).json()
    assert api.get("/api/v1/asns/4000000000", params={"include": "historico"}, headers=ALLOWED).status_code == 404

    ixp = api.get(f"/api/v1/ixps/{ctx['code']}", params={"include": "historico"}, headers=ALLOWED).json()["historico"]
    assert [x["date"] for x in ixp["serie"]] == [T0, T1] and "status" in ixp["colunas"]
    assert all(e["tipo"].startswith("ixp_") and e["chave"] == ctx["code"] for e in ixp["eventos"])

    uf = api.get("/api/v1/ufs/PR", params={"include": "historico"}, headers=ALLOWED).json()
    assert uf["historico"]["serie"][-1]["n_ma4"] == 2 and "totais" in uf
    assert "historico" not in api.get("/api/v1/ufs/PR", headers=ALLOWED).json()

    cnpj = api.get("/api/v1/asns/64503", headers=ALLOWED).json().get("cnpj")
    if cnpj and api.get(f"/api/v1/operadoras/{cnpj}", headers=ALLOWED).status_code == 200:
        op = api.get(f"/api/v1/operadoras/{cnpj}", params={"include": "historico"}, headers=ALLOWED).json()
        assert op["historico"] is None or op["historico"]["serie"]
    assert api.get("/api/v1/ufs/PR", params={"include": "x"}, headers=ALLOWED).status_code == 400


def test_bloco_historico_depende_so_da_url(api, ctx):
    """O nginx e o cache da API guardam por URL: `include=historico` (datas atuais) é o mesmo corpo para anônimo e logado, e a série
    inteira é outra URL (`historico_completo`), da classe `login`: 401 ao anônimo e `private, no-store` a quem tem acesso."""
    rotas = [("/api/v1/asns/64503", "paths"), (f"/api/v1/ixps/{ctx['code']}", "indice"), ("/api/v1/ufs/PR", "territorio")]
    for rota, outro in rotas:
        params = {"include": f"{outro},historico"}
        anon, logado = api.get(rota, params=params, headers=ANON), api.get(rota, params=params, headers=ALLOWED)
        assert anon.status_code == logado.status_code == 200, rota
        assert anon.json()["historico"] == logado.json()["historico"] and anon.json()["historico"]["completo"] is False, rota
        completo = {"include": f"{outro},historico_completo"}
        negado = api.get(rota, params=completo, headers=ANON)
        assert negado.status_code == 401 and negado.json().get("login_required") is True, rota
        r = api.get(rota, params=completo, headers=ALLOWED)
        assert r.status_code == 200 and r.json()["historico"]["completo"] is True, rota
        assert r.headers["cache-control"] == "private, no-store", rota


def test_bloco_historico_do_anonimo_so_tem_as_datas_atuais(tmp_path):
    """O bloco do perfil respeita a política de acesso: `completo=False` limita às datas atuais, mesmo que a série tenha mais."""
    import gzip

    from api.repos.historico import HistoricoRepo
    from api.services import historico as h

    for d, users in (("2026-09-01", 1), ("2026-09-08", 2), ("2026-09-15", 3)):
        pasta = tmp_path / "history" / "weekly" / d
        pasta.mkdir(parents=True)
        (pasta / "asn.jsonl.gz").write_bytes(gzip.compress(('{"asn":7,"is_br":true,"users":%d}\n' % users).encode()))
    (tmp_path / "history" / "index.json").write_text('{"snapshots":[{"date":"2026-09-01"},{"date":"2026-09-08"},{"date":"2026-09-15"}]}')
    repo = HistoricoRepo(tmp_path)
    assert [p["users"] for p in h.perfil(repo, "asn", "7", True, ["2026-09-08", "2026-09-15"])["serie"]] == [1, 2, 3]
    anon = h.perfil(repo, "asn", "7", False, ["2026-09-08", "2026-09-15"])
    assert anon["completo"] is False and [p["users"] for p in anon["serie"]] == [2, 3] and anon["snapshots_com_historico"] == 3
    assert h.perfil(repo, "asn", "8", True, []) is None


def test_query_tem_as_colecoes_eventos_e_series_asn(api):
    """`/query` ganha `eventos` (todas as datas) e `series_asn` (ASN BR × datas), com os mesmos números das rotas de histórico."""
    from tests.synth.world import T0, T1

    ev = api.post("/api/v1/query/eventos", json={"filter": {"field": "tipo", "op": "eq", "value": "mudanca_origem"}, "limit": 10}, headers=ALLOWED)
    assert ev.status_code == 200
    linhas = ev.json()["items"] if "items" in ev.json() else ev.json()["rows"]
    assert linhas and linhas[0]["destaque"] is True and linhas[0]["natureza"] == "observado"
    todos = api.post("/api/v1/query/eventos", json={"limit": 500}, headers=ALLOWED).json()
    assert (todos.get("total") or todos.get("count")) == api.get("/api/v1/changes", params={"estado": "todos"}, headers=ALLOWED).json()["total"]
    sr = api.post("/api/v1/query/series_asn", json={"filter": {"field": "asn", "op": "eq", "value": 64503}, "sort": [{"field": "data", "dir": "asc"}]},
                  headers=ALLOWED).json()
    rows = sr["items"] if "items" in sr else sr["rows"]
    assert [r["data"] for r in rows] == [T0, T1]
    assert rows[1]["rpki_invalid"] == api.get("/api/v1/history/asns/64503", headers=ALLOWED).json()["snapshots"][1]["rpki_invalid"]
    assert "hash_pfx" not in rows[0] and "is_br" not in rows[0]


def test_feed_atom_das_mudancas_so_confirmadas_sem_provedor_e_aberto(api):
    """O feed é Atom válido, aberto, só com eventos confirmados e sem eventos de provedor nem contato/nome de empresa."""
    import xml.etree.ElementTree as ET

    r = api.get("/api/v1/feed/mudancas.atom", headers=ANON)
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/atom+xml")
    raiz = ET.fromstring(r.content)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    from core.site import SITE
    assert raiz.find("a:title", ns).text.startswith(SITE.nome)
    entradas = raiz.findall("a:entry", ns)
    assert entradas and len({e.find("a:id", ns).text for e in entradas}) == len(entradas)
    texto = r.text.lower()
    assert "provedor" not in texto and "@" not in texto and "não indica causa" in texto
    conf = api.get("/api/v1/changes", params={"limit": 500, "from": "2000-01-01"}, headers=ALLOWED).json()["items"]
    esperadas = {(e["data"], e["tipo"]) for e in conf if not e["tipo"].startswith("provedor")}
    assert len(entradas) == len(esperadas) > 0                                   # uma entrada por (data, tipo) confirmado


def test_historico_para_anonimo_so_a_partir_dos_snapshots_atuais(api):
    """A política de acesso vale na API real: série inteira (sem `from`) exige login; começando num snapshot atual, não."""
    from tests.synth.world import T0, T1

    r = api.get("/api/v1/history/asns/64503", headers=ANON)
    assert r.status_code == 401 and r.json()["reason"] == "historico"
    assert api.get("/api/v1/changes", headers=ANON).status_code == 401
    assert api.get("/api/v1/history/asns/64503", params={"from": T0}, headers=ANON).status_code == 200     # T0 e T1 são os 2 atuais


def test_lista_de_asns_com_uf_estabilidade_e_ordenacao_por_epppd(api):
    """A lista traz `uf`; `include=bgp_stability` junta o epppd (a página não baixa mais o resumo); `sort_by=epppd` ordena."""
    itens = api.get("/api/v1/asns", params={"br_only": "true", "limit": 100, "include": "bgp_stability", "sort_by": "epppd", "sort_desc": "true"},
                    headers=ALLOWED).json()["items"]
    assert itens and all("uf" in i and "epppd" in i for i in itens)
    valores = [i["epppd"] for i in itens if i["epppd"] is not None]
    assert valores == sorted(valores, reverse=True)
    r = api.get("/api/v1/bgp-stability/summary", headers=ALLOWED)
    resumo = {i["asn"]: i for i in r.json()["items"]} if r.status_code == 200 else {}   # o sintético pode não ter a análise
    for i in itens:
        if i["asn"] in resumo:
            assert i["epppd"] == resumo[i["asn"]]["epppd"]


def test_nomes_em_lote_so_br_e_embutidos_em_membros_e_peers(api, ctx):
    """`/asns/names?asns=`, `br_only`, `detalhe`; `nomes=true` em membros e peers cobre todos os ASNs da resposta."""
    todos = api.get("/api/v1/asns/names", headers=ALLOWED).json()["names"]
    um = next(iter(todos))
    lote = api.get("/api/v1/asns/names", params={"asns": f"{um},4000000000"}, headers=ALLOWED).json()["names"]
    assert lote == {um: todos[um]}
    br = api.get("/api/v1/asns/names", params={"br_only": "true"}, headers=ALLOWED).json()["names"]
    assert 0 < len(br) <= len(todos) and set(br) <= set(todos)
    det = api.get("/api/v1/asns/names", params={"asns": um, "detalhe": "true"}, headers=ALLOWED).json()["names"]
    assert det[um]["name"] == todos[um] and "uf" in det[um]
    assert api.get("/api/v1/asns/names", params={"asns": "a"}, headers=ALLOWED).status_code == 400
    m = api.get(f"/api/v1/ixps/{ctx['code']}/members", params={"nomes": "true"}, headers=ALLOWED).json()
    asns = {a for afi in ("v4", "v6") for lst in m[afi].values() if isinstance(lst, list) for a in lst if isinstance(a, int)}
    assert asns and set(m["nomes"]) == {str(a) for a in asns if str(a) in todos}
    assert "nomes" not in api.get(f"/api/v1/ixps/{ctx['code']}/members", headers=ALLOWED).json()
    p = api.get(f"/api/v1/ixps/{ctx['code']}/peers", params={"afi": "v4", "nomes": "true"}, headers=ALLOWED).json()
    assert set(p["nomes"]) == {a for a in p["peers"] if a in todos}


def test_estabilidade_bgp_de_um_as_traz_o_que_a_pagina_usa_sem_o_documento_inteiro(tmp_path):
    """`Store.bgp_stability_asn` entrega o AS, o diagnóstico e as séries horárias das semanas, sem reter o JSON antigo."""
    from api.store import Store

    def hora(n):
        return {"ann": [n] * 168, "wd": [n + 1] * 168, "attr_upd": [n + 2] * 168}

    def snap(d, asns):
        pub = tmp_path / "published" / d
        pub.mkdir(parents=True)
        (pub / "manifest.json").write_text("{}")
        doc = {"epppd_stats": {"median": 1.0}, "hourly_global": {"timestamps": [f"{d}T{h:02d}" for h in range(168)]},
               "as_stability": [{"asn": a, "name": f"AS{a}", "period": {"events_per_prefix_per_day": 1.0},
                                "hourly": hora(a)} for a in asns] + [{"asn": 999, "name": "sem série", "period": {}}]}
        (pub / "bgp_stability.json").write_text(json.dumps(doc))
        return pub

    snap("2026-09-06", [10, 20])
    snap("2026-09-07", [10, 20])                                              # coleta diária: o dia seguinte repete a semana
    snap("2026-09-13", [10])
    pub = snap("2026-09-20", [10, 20])
    snap("2026-07-01", [10])                                                  # fora da janela de 6 semanas
    (pub / "bgp_stability_deep.json").write_text(json.dumps({"as_diagnosis": [{"asn": 10, "diagnosis": "x"}]}))
    store = Store(tmp_path)
    r = store.bgp_stability_asn("2026-09-20", 10, 6)
    assert [w["date"] for w in r["weeks"]] == ["2026-09-06", "2026-09-13", "2026-09-20"]
    assert r["weeks"][0]["series"]["ann"] == [10] * 168 and len(r["weeks"][0]["timestamps"]) == 168
    assert r["stability"]["asn"] == 10 and r["diagnosis"] == {"asn": 10, "diagnosis": "x"} and r["epppd_stats"] == {"median": 1.0}
    assert len(r["timestamps"]) == 168
    r20 = store.bgp_stability_asn("2026-09-20", 20, 6)
    assert [w["date"] for w in r20["weeks"]] == ["2026-09-06", "2026-09-20"] and r20["diagnosis"] is None
    sem = store.bgp_stability_asn("2026-09-20", 999, 6)
    assert sem["stability"]["asn"] == 999 and sem["weeks"] == []
    assert store.bgp_stability_asn("2026-09-20", 12345, 6)["stability"] is None
    assert store.bgp_stability_asn("2026-01-01", 10, 6) is None
    # as semanas antigas ficam só na forma compacta: o JSON completo delas não é retido
    assert "2026-09-06" not in store._docs.bgp_stability_datas_em_memoria() and "2026-09-06" in store._bgp._bgp_horaria_cache
    # um snapshot por semana (−7k dias); falta no dia → o mais recente até 3 dias antes
    assert store.bgp_stability_datas_semanais("2026-09-20", 6) == ["2026-09-06", "2026-09-13", "2026-09-20"]
    assert store.bgp_stability_datas_semanais("2026-09-21", 3) == ["2026-09-07", "2026-09-13", "2026-09-20"]   # recua até 3 dias
    assert store.aquecer_estabilidade("2026-09-20", 6) == 3
    resumo = store.bgp_stability_historico_resumo("2026-09-20", 6)
    assert [w["date"] for w in resumo] == ["2026-09-06", "2026-09-13", "2026-09-20"]
    assert set(resumo[0]["data"]) == {"hourly_global"} and len(resumo[0]["data"]["hourly_global"]["timestamps"]) == 168


def test_visao_geral_da_estabilidade_bgp_traz_o_resumo_sem_as_series_pesadas(tmp_path):
    """`Store.bgp_stability_visao_geral` = o que a seção da página usa, sem `hourly`/`top_prefixes` e só com o top N."""
    from api.store import Store
    pub = tmp_path / "published" / "2026-09-20"
    pub.mkdir(parents=True)
    (pub / "manifest.json").write_text("{}")
    sev = ["critical", "high", "medium", "medium", "low"]
    cat = ["critico", "barulhento", "inquieto", "estavel", None]
    ases = [{"asn": 100 + i, "name": f"AS{i}", "rank": 5 - i, "severity": sev[i], "noise_category": cat[i], "period": {"events_per_prefix_per_day": 5.0 - i},
             "daily": [{"total_events": 1}], "hourly": {"ann": [1] * 168}, "top_prefixes": [{"prefix": "10.0.0.0/24"}]} for i in range(5)]
    doc = {"period": {"start": "a"}, "distribution": {"v4": {}}, "epppd_stats": {"median": 1}, "hourly_global": {"timestamps": ["t"]},
           "published_at": "x", "as_stability": ases}
    (pub / "bgp_stability.json").write_text(json.dumps(doc))
    store = Store(tmp_path)
    r = store.bgp_stability_visao_geral("2026-09-20", top=3)
    assert [a["rank"] for a in r["as_stability"]] == [1, 2, 3]                       # ordenado por rank, só o top N
    assert all("hourly" not in a and "top_prefixes" not in a and "daily" in a for a in r["as_stability"])
    assert r["categorias"] == {"estavel": 2, "inquieto": 1, "barulhento": 1, "critico": 1, "total": 5}   # sem categoria conta como estável
    assert r["severidades"] == {"critical": 1, "high": 1, "medium": 2, "low": 1} and r["medio_ou_maior"] == 4
    assert r["period"] == {"start": "a"} and r["hourly_global"] == {"timestamps": ["t"]} and r["snapshot_date"] == "2026-09-20"
    assert len(json.dumps(r)) < len(json.dumps(doc))
    assert store.bgp_stability_visao_geral("2026-01-01") is None


def test_visao_geral_da_estabilidade_bgp_traz_o_topo_de_cada_ordem_da_lista_inteira(tmp_path):
    """A tabela recolhida ordenada por v4 mostra os mais instáveis em v4 da lista inteira (severidade média ou maior), não as 10 linhas do
    top por rank reordenadas: o AS 7, 7º no rank e 1º em v4, entra; o de severidade baixa, mesmo com v4 alto, não."""
    from api.store import Store
    pub = tmp_path / "published" / "2026-09-20"
    pub.mkdir(parents=True)
    (pub / "manifest.json").write_text("{}")
    ases = [{"asn": i, "rank": i, "severity": "medium", "period": {"events_per_prefix_per_day": 10 - i, "events_per_prefix_per_day_v4": 0.1,
             "events_per_prefix_per_day_v6": 0.1, "flapping_prefixes": 0}, "hourly": {}} for i in range(1, 9)]
    ases[6]["period"]["events_per_prefix_per_day_v4"] = 50                     # AS 7
    ases.append({"asn": 99, "rank": 9, "severity": "low", "period": {"events_per_prefix_per_day_v4": 99}})
    doc = {"period": {}, "distribution": {}, "as_stability": ases}
    (pub / "bgp_stability.json").write_text(json.dumps(doc))
    r = Store(tmp_path).bgp_stability_visao_geral("2026-09-20", top=3)
    assert [a["asn"] for a in r["as_stability"]] == [1, 2, 3]
    assert r["ordens"]["epppd_v4"]["desc"][0] == 7 and 99 not in r["ordens"]["epppd_v4"]["desc"]
    assert r["ordens"]["rank"] == {"asc": [1, 2, 3], "desc": [8, 7, 6]}
    extras = {a["asn"] for a in r["as_stability_ordens"]}
    assert 7 in extras and not extras & {1, 2, 3} and all("hourly" not in a for a in r["as_stability_ordens"])


def test_carga_bgp_soma_updates_por_familia_nas_semanas_do_grafico(tmp_path):
    """`Store.bgp_stability_carga`: volume absoluto por família somado nas semanas (as de `bgp_stability_datas_semanais`), top N pela soma,
    0 para o AS sem update numa semana, parcela do total e a janela real de cada semana (sobreposição e lacuna, com `end` exclusivo)."""
    from api.store import Store

    def per(v6, v4):
        return {"announcements_v6": v6, "withdrawals_v6": 0, "attribute_updates_v6": 0,
                "announcements_v4": v4 // 2, "withdrawals_v4": v4 - v4 // 2, "attribute_updates_v4": 0}

    def snap(d, inicio, fim, ases):
        pub = tmp_path / "published" / d
        pub.mkdir(parents=True)
        (pub / "manifest.json").write_text("{}")
        doc = {"period": {"start": inicio, "end": fim, "days": 7, "collector": "rrc-x", "files_missing": 0},
               "hourly_global": {"timestamps": []},
               "as_stability": [{"asn": a, "name": f"Rede {a}", "prefix_count_v6": 1, "prefix_count_v4": 2, "period": per(v6, v4)}
                                for a, v6, v4 in ases]}
        (pub / "bgp_stability.json").write_text(json.dumps(doc))

    snap("2026-09-06", "2026-08-30", "2026-09-06", [(1, 100, 10), (2, 5, 500)])
    snap("2026-09-13", "2026-09-06", "2026-09-13", [(1, 100, 10), (3, 900, 0)])                 # pico isolado do AS 3 em v6
    snap("2026-09-18", "2026-09-11", "2026-09-18", [(1, 100, 10), (2, 5, 400), (4, 1, 1)])      # sem o dia 20: recua; 2 dias sobrepostos
    store = Store(tmp_path)
    r = store.bgp_stability_carga("2026-09-20", 6, 2)
    assert [s["date"] for s in r["semanas"]] == ["2026-09-06", "2026-09-13", "2026-09-18"]
    assert [(s["sobreposicao_dias"], s["lacuna_dias"]) for s in r["semanas"]] == [(0, 0), (0, 0), (2, 0)]
    assert r["semanas"][0]["ultimo_dia"] == "2026-09-05" and r["coletor"] == "rrc-x"
    assert [a["asn"] for a in r["v6"]["ases"]] == [3, 1]                                         # soma: 900 > 300 > 10
    assert r["v6"]["ases"][0]["semanas"] == [0, 900, 0] and r["v6"]["ases"][1]["semanas"] == [100, 100, 100]
    assert [a["asn"] for a in r["v4"]["ases"]] == [2, 1] and r["v4"]["ases"][0]["semanas"] == [500, 0, 400]
    assert r["v4"]["ases"][0]["nome"] == "Rede 2" and r["v4"]["ases"][0]["prefixos"] == [2, 0, 2]
    assert [s["total_v6"] for s in r["semanas"]] == [105, 1000, 106] and r["v6"]["total"] == 1211
    assert r["v6"]["parcela_top_pct"] == round(100 * 1200 / 1211, 1)
    assert r["v6"]["parcela_top_semana_pct"] == [round(100 * 100 / 105, 1), 100.0, round(100 * 100 / 106, 1)]
    assert store.bgp_stability_carga("2026-09-20", 1, 10)["semanas"][0]["date"] == "2026-09-18"
    assert store.bgp_stability_carga("2026-01-01", 6, 10) is None


def test_outorgas_unificadas_batem_com_as_rotas_por_servico(api, ctx):
    """`/outorgas` tem uma linha por CNPJ com os serviços; stats, mapa e `/outorgas/{cnpj}` iguais às rotas por serviço."""
    todos = api.get("/api/v1/outorgas", params={"limit": 1000}, headers=ALLOWED).json()
    assert todos["total"] == len(todos["items"]) and todos["items"]
    por_cnpj = {r["cnpj"]: r for r in todos["items"]}
    assert len(por_cnpj) == todos["total"]                                       # uma linha por CNPJ
    for sigla, rota in (("SCM", "scms"), ("SMP", "smps"), ("STFC", "stfcs"), ("SeAC", "seacs")):
        antigos = api.get(f"/api/v1/{rota}", params={"limit": 1000}, headers=ALLOWED).json()
        so = api.get("/api/v1/outorgas", params={"servico": sigla.lower(), "limit": 1000}, headers=ALLOWED).json()
        assert {r["cnpj"] for r in so["items"]} == {r["cnpj"] for r in antigos["items"]}, sigla
        assert all(sigla in r["servicos"] for r in so["items"])
        st = api.get("/api/v1/outorgas/stats", params={"servico": sigla}, headers=ALLOWED)
        assert st.json() == api.get(f"/api/v1/{rota}/stats", headers=ALLOWED).json()
        mp = api.get("/api/v1/outorgas/map", params={"servico": sigla}, headers=ALLOWED).json()
        assert mp == api.get(f"/api/v1/map/{rota}", headers=ALLOWED).json()
    # combinável: OU (padrão) e E (todos=true); filtros se combinam
    ou = api.get("/api/v1/outorgas", params={"servico": "SCM,SMP", "limit": 1000}, headers=ALLOWED).json()
    e = api.get("/api/v1/outorgas", params={"servico": "SCM,SMP", "todos": "true", "limit": 1000}, headers=ALLOWED).json()
    assert {r["cnpj"] for r in e["items"]} <= {r["cnpj"] for r in ou["items"]}
    assert all({"SCM", "SMP"} <= set(r["servicos"]) for r in e["items"])
    ordenado = api.get("/api/v1/outorgas", params={"sort_by": "acessos", "sort_desc": "true", "limit": 1000}, headers=ALLOWED).json()["items"]
    assert [r["acessos"] for r in ordenado] == sorted((r["acessos"] for r in ordenado), reverse=True)
    ativos = api.get("/api/v1/outorgas", params={"ativo": "true", "limit": 1000}, headers=ALLOWED).json()["items"]
    assert ativos and all(r["acessos"] > 0 for r in ativos)
    # por CNPJ: as outorgas de cada serviço, sem contatos
    cnpj = ctx["cnpj"]
    d = api.get(f"/api/v1/outorgas/{cnpj}", headers=ALLOWED).json()
    assert d["servicos"]["SCM"] == api.get(f"/api/v1/scms/{cnpj}", headers=ALLOWED).json()["outorgas"]
    assert not ({"email", "telefone"} & _keys(d))
    assert set(por_cnpj[cnpj]["servicos"]) == set(d["servicos"])
    assert api.get("/api/v1/outorgas", params={"servico": "XYZ"}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/outorgas", params={"sort_by": "x"}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/outorgas/123", headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/outorgas/00000000000000", headers=ALLOWED).status_code == 404


def test_acessos_com_servico_movel_igual_as_rotas_acessos_movel(api, ctx):
    """`/acessos/*?servico=movel` devolve o mesmo corpo de `/acessos-movel/*`; sem `servico` (ou `fixa`) nada muda."""
    h = ALLOWED
    pares = [
        ("/api/v1/acessos/stats", "/api/v1/acessos-movel/stats", {}),
        ("/api/v1/acessos/operadoras", "/api/v1/acessos-movel/operadoras", {"ativo": "true", "limit": 50}),
        ("/api/v1/acessos/municipios", "/api/v1/acessos-movel/municipios", {"limit": 50}),
        (f"/api/v1/acessos/operadora/{ctx['cnpj_smp']}", f"/api/v1/acessos-movel/operadora/{ctx['cnpj_smp']}", {}),
        (f"/api/v1/acessos/municipio/{ctx['ibge_movel']}", f"/api/v1/acessos-movel/municipio/{ctx['ibge_movel']}", {}),
    ]
    for novo, antigo, params in pares:
        r_novo = api.get(novo, params={**params, "servico": "movel"}, headers=h)
        r_antigo = api.get(antigo, params=params, headers=h)
        assert r_novo.status_code == r_antigo.status_code, novo
        assert r_novo.json() == r_antigo.json(), novo
    fixa = api.get("/api/v1/acessos/stats", headers=h).json()
    assert api.get("/api/v1/acessos/stats", params={"servico": "fixa"}, headers=h).json() == fixa
    assert api.get("/api/v1/acessos/stats", params={"servico": "x"}, headers=h).status_code == 422
    # contatos seguem exigindo login nos dois serviços
    assert api.get(f"/api/v1/acessos/operadora/{ctx['cnpj_smp']}/contacts", params={"servico": "movel"}, headers=ANON).status_code in (401, 403)


def test_rotas_substituidas_avisam_com_deprecation_e_apontam_o_sucessor(api, ctx):
    """Aliases respondem como antes e ganham `Deprecation` + `Link: rel=successor-version`; os contratos novos não."""
    h = ALLOWED
    cnpj = ctx["cnpj"]
    casos = {
        "/api/v1/scms": "/api/v1/outorgas?servico=SCM",
        "/api/v1/smps/stats": "/api/v1/outorgas/stats?servico=SMP",
        "/api/v1/map/seacs": "/api/v1/outorgas/map?servico=SeAC",
        f"/api/v1/scms/{cnpj}": f"/api/v1/outorgas/{cnpj}?servico=SCM",
        "/api/v1/acessos-movel/stats": "/api/v1/acessos/stats?servico=movel",
        f"/api/v1/acessos-movel/municipio/{ctx['ibge_movel']}": f"/api/v1/acessos/municipio/{ctx['ibge_movel']}?servico=movel",
        f"/api/v1/analytics/ixps/{ctx['code']}/nearby": f"/api/v1/ixps/{ctx['code']}/nearby",
    }
    for rota, sucessor in casos.items():
        r = api.get(rota, headers=h)
        assert r.status_code in (200, 404), rota
        assert r.headers.get("deprecation") == "true", rota
        assert r.headers.get("link") == f'<{sucessor}>; rel="successor-version"', rota
    for rota in ("/api/v1/outorgas", "/api/v1/acessos/stats", f"/api/v1/ixps/{ctx['code']}/nearby", f"/api/v1/outorgas/{cnpj}", f"/api/v1/operadoras/{cnpj}"):
        assert "deprecation" not in {k.lower() for k in api.get(rota, headers=h).headers}, rota
    # o novo detalhamento por PTT é o mesmo corpo do alias
    novo = api.get(f"/api/v1/ixps/{ctx['code']}/nearby", headers=h).json()
    assert novo == api.get(f"/api/v1/analytics/ixps/{ctx['code']}/nearby", headers=h).json()


def test_ranking_e_omissao_do_sici_trazem_criterio_mes_e_fato(api):
    """Rankings de dado declarado, com critério e mês; a omissão descreve fato, com classe e usuários APNIC (cenário 2 plantado)."""
    r = api.get("/api/v1/ranking/operadoras", params={"limit": 5}, headers=ALLOWED).json()
    assert r["mes_referencia"] and r["criterio"].startswith("Acessos declarados") and r["metodologia"]
    ac = [x["acessos"] for x in r["items"]]
    assert ac == sorted(ac, reverse=True) and r["items"][0]["posicao"] == 1
    asc = api.get("/api/v1/ranking/operadoras", params={"limit": 3, "asc": "true", "ordem": "share"}, headers=ALLOWED).json()["items"]
    assert [x["share"] for x in asc] == sorted(x["share"] for x in asc)
    assert api.get("/api/v1/ranking/operadoras", params={"ordem": "inventada"}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/ranking/operadoras", params={"uf": "ZZ"}, headers=ALLOWED).status_code == 404
    uf = r["items"][0]["uf_sede"]
    na_uf = api.get("/api/v1/ranking/operadoras", params={"uf": uf, "limit": 50}, headers=ALLOWED).json()
    assert na_uf["escopo"] == {"uf": uf} and all("var_aa_pct" not in x for x in na_uf["items"])
    m = api.get("/api/v1/ranking/municipios", params={"ordem": "hhi", "limit": 5}, headers=ALLOWED).json()
    assert m["items"] and all(0 < x["hhi"] <= 10000 and x["lider"]["share"] > 0 for x in m["items"])

    o = api.get("/api/v1/omissao-sici", params={"limit": 200}, headers=ALLOWED).json()
    assert o["tipo"] == "outorga_sem_declaracao" and o["mes_referencia"] and o["parametros"]["usuarios_min"] == 100
    classes = {x["classe"] for x in o["items"]}
    assert classes <= {"com_usuarios_apnic", "sem_usuarios", "nao_comparavel"}
    com = [x for x in o["items"] if x["classe"] == "com_usuarios_apnic"]
    assert com and all(x["usuarios_apnic"] >= 100 and x["asns"] for x in com)
    assert o["total"] == len(o["items"]) and sum(v["cnpjs_sem_declaracao"] for v in o["por_uf"].values()) == o["total"]
    classe = sorted(classes)[0]
    filtrado = api.get("/api/v1/omissao-sici", params={"classe": classe, "limit": 200}, headers=ALLOWED).json()
    assert filtrado["items"] and all(x["classe"] == classe for x in filtrado["items"]) and filtrado["total"] <= o["total"]
    assert api.get("/api/v1/omissao-sici", params={"tipo": "x"}, headers=ALLOWED).status_code == 400
    texto = str(o).lower()
    assert "sonegou" not in texto and "omitiu" not in texto and "@" not in texto


def test_perfis_com_include_indicadores_e_query_das_novas_colecoes(api, ctx):
    cnpj = api.get("/api/v1/ranking/operadoras", params={"limit": 1}, headers=ALLOWED).json()["items"][0]["cnpj"]
    p = api.get(f"/api/v1/operadoras/{cnpj}", params={"include": "indicadores"}, headers=ALLOWED).json()
    assert p["indicadores"]["posicao_br"] == 1 and p["indicadores"]["metodologia"] and "ufs" not in p["indicadores"]
    assert "indicadores" not in api.get(f"/api/v1/operadoras/{cnpj}", headers=ALLOWED).json()
    mun = api.get("/api/v1/ranking/municipios", params={"limit": 1}, headers=ALLOWED).json()["items"][0]["ibge"]
    pm = api.get(f"/api/v1/municipios/{mun}", params={"include": "indicadores"}, headers=ALLOWED).json()
    assert pm["indicadores"]["hhi"] > 0 and pm["indicadores"]["mes_referencia"]
    uf = api.get("/api/v1/ranking/operadoras", params={"limit": 1}, headers=ALLOWED).json()["items"][0]["uf_sede"]
    pu = api.get(f"/api/v1/ufs/{uf}", params={"include": "indicadores"}, headers=ALLOWED).json()
    assert pu["indicadores"]["acessos"] > 0 and "sem_declaracao" in pu["indicadores"]
    for c, campo in (("indicadores_operadora", "share_br"), ("omissao_sici", "classe")):
        q = api.post(f"/api/v1/query/{c}", json={"limit": 3}, headers=ALLOWED)
        assert q.status_code == 200 and q.json()["items"] and campo in q.json()["items"][0], c


def test_territorio_ranking_penetracao_nao_visto_e_cidades_sem_ptt(api):
    """Penetração e não visto vêm com fórmula e limites; ranking ordenado; sem_ptt_proximo filtra pela distância; município sem domicílios fica de fora."""
    r = api.get("/api/v1/territorio/ranking", params={"limit": 50}, headers=ALLOWED).json()
    assert r["censo_ano"] == "2022" and r["formulas"]["nao_visto"].startswith("max(0") and "celular" in r["limites"]
    p = [x["penetracao"] for x in r["items"]]
    assert p == sorted(p, reverse=True) and r["items"][0]["posicao"] == 1
    assert all("domicilios" in x for x in r["items"])                        # o município sem domicílios (SIDRA "...") não entra em ranking por razão
    for x in r["items"]:
        assert x["nao_visto"] >= 0 and x["acessos"] >= 0
        if "km_ptt" in x:
            assert x["sem_ptt_proximo"] is (x["km_ptt"] > 100)
    asc = api.get("/api/v1/territorio/ranking", params={"campo": "nao_visto", "asc": "true", "limit": 5}, headers=ALLOWED).json()["items"]
    assert [x["nao_visto"] for x in asc] == sorted(x["nao_visto"] for x in asc)
    longe = api.get("/api/v1/territorio/ranking", params={"sem_ptt_proximo": "true", "limit": 100}, headers=ALLOWED).json()
    assert all(x["sem_ptt_proximo"] for x in longe["items"]) and longe["total"] <= r["total"]
    assert api.get("/api/v1/territorio/ranking", params={"campo": "x"}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/territorio/ranking", params={"uf": "ZZ"}, headers=ALLOWED).status_code == 404


def test_perfis_com_include_territorio_e_colecao_municipios(api):
    top = api.get("/api/v1/territorio/ranking", params={"limit": 1}, headers=ALLOWED).json()["items"][0]
    pm = api.get(f"/api/v1/municipios/{top['ibge']}", params={"include": "territorio"}, headers=ALLOWED).json()
    assert pm["territorio"]["populacao"] == top["populacao"] and pm["territorio"]["penetracao"] == top["penetracao"] and pm["territorio"]["formulas"]
    assert "territorio" not in api.get(f"/api/v1/municipios/{top['ibge']}", headers=ALLOWED).json()
    pu = api.get(f"/api/v1/ufs/{top['uf']}", params={"include": "territorio"}, headers=ALLOWED).json()
    assert pu["territorio"]["domicilios"] > 0 and pu["territorio"]["taxa_internet_pnad"] == 0.9 and pu["territorio"]["nao_visto"] >= 0
    q = api.post("/api/v1/query/municipios", json={"limit": 3, "filter": {"field": "uf", "op": "eq", "value": top["uf"]}}, headers=ALLOWED)
    assert q.status_code == 200 and q.json()["items"] and "penetracao" in q.json()["items"][0]


def test_seguranca_resumo_agrega_com_fontes_e_sem_ranking_nominal(api):
    """O resumo traz fontes com data, limites e faixas neutras; ASN com poucas amostras fica fora das contagens (cenário plantado)."""
    r = api.get("/api/v1/seguranca/resumo", headers=ALLOWED).json()
    assert r["fontes"]["rov"]["as_of"] == "2026-09-19" and "Spamhaus" in r["limites"]
    assert r["parametros"]["min_amostras"] == 100 and r["escopo"] == {"pais": "BR"}
    b = r["agregado"]
    assert b["rov"]["asns"] == b["asns"] - 1 and b["rov"]["faixas"]["acima_de_90"] == 1       # 64503 valida (97%); 64505 tem 40 amostras e sai das contagens
    assert b["asns_com_prefixo_bogon"] == 2 and set(r["por_uf"]) and set(r["por_faixa_porte"]) <= {"sem_usuarios", "ate_1000", "de_1000_a_10000", "de_10000_a_100000", "de_100000_a_1000000", "acima_de_1000000"}
    uf = next(iter(r["por_uf"]))
    u = api.get("/api/v1/seguranca/resumo", params={"uf": uf}, headers=ALLOWED).json()
    assert u["escopo"] == {"uf": uf} and u["agregado"] == r["por_uf"][uf] and "por_uf" not in u
    assert api.get("/api/v1/seguranca/resumo", params={"uf": "ZZ"}, headers=ALLOWED).status_code == 404


def test_asn_com_include_seguranca_e_colecao_seguranca_asn(api):
    p = api.get("/api/v1/asns/64503", params={"include": "seguranca"}, headers=ALLOWED).json()
    assert p["seguranca"]["rov"] == {"validates_pct": 97.0, "amostras": 5000} and p["seguranca"]["asrank"]["rank"] and p["seguranca"]["fontes"]["asrank"]["citacao"]
    assert "uf" not in p["seguranca"] and "faixa_porte" not in p["seguranca"] and "faixa_acessos_sici" not in p["seguranca"]
    assert "seguranca" not in api.get("/api/v1/asns/64503", headers=ALLOWED).json()
    bog = api.get("/api/v1/asns/64500", params={"include": "seguranca"}, headers=ALLOWED).json()["seguranca"]
    assert bog["n_prefixos_bogon"] == 1 and bog["prefixos_em_bogon"][0]["lista"] == "cymru" and bog["asn_reservado"]
    q = api.post("/api/v1/query/seguranca_asn", json={"limit": 200, "filter": {"field": "rov_amostras", "op": "gte", "value": 100}}, headers=ALLOWED).json()["items"]
    assert q and all(x["rov_amostras"] >= 100 for x in q) and 64505 not in {x["asn"] for x in q} and 64503 in {x["asn"] for x in q}
    assert any(x.get("n_prefixos_bogon") for x in q)


def test_route_servers_ptt_asn_ranking_e_colecao(api):
    """Cenário plantado — za: 1º membro down há 12 dias e o 2º a 90% do limite; zb: cadastrado sem sessão; zc: sessão sem cadastro."""
    za = api.get("/api/v1/ixps/za/route-servers", headers=ALLOWED).json()
    assert za["coletado_em"] and za["versao_alice"] == "6.1.0" and "peering bilateral" in za["limites"] and za["parametros"]["dias_down"] == 7
    r = za["resumo"]
    assert (r["membros_down"], r["membros_perto_do_limite"], r["sessoes_down"]) == (1, 1, 1) and r["rs"] == 1
    assert (r["rs_rotas_prontas"], r["rs_vizinhos_atuais"]) == (0, 1)          # cache de ROTAS em BUSY não torna as sessões incertas: o frescor é o do neighbors
    assert za["rs"][0]["estado_rotas"] == "BUSY" and za["rs"][0]["vizinhos_em"] and za["parametros"]["idade_max_vizinhos_h"] == 24
    membro = next(m for m in za["membros"] if m["membro_down"])
    assert membro["max_dias_down"] == 12 and membro["cadastrado"] is True
    zb = api.get("/api/v1/ixps/zb/route-servers", headers=ALLOWED).json()["resumo"]
    assert zb["cadastrados_sem_sessao"] == 1 and zb["cadastrados_com_sessao"] == zb["cadastrados"] - 1
    zc = api.get("/api/v1/ixps/zc/route-servers", headers=ALLOWED).json()
    assert zc["resumo"]["rs"] == 2 and zc["resumo"]["rs_vizinhos_atuais"] == 1 and zc["resumo"]["membros_down"] == 0 and zc["resumo"]["membros_com_rs_incerto"] == 1
    incerto = next(m for m in zc["membros"] if m["asn"] == 4200000101) if any(m["asn"] == 4200000101 for m in zc["membros"]) else next(m for m in api.get("/api/v1/ixps/zc/route-servers", params={"membros": "todos"}, headers=ALLOWED).json()["membros"] if m["asn"] == 4200000101)
    assert incerto["todas_down"] is True and incerto["membro_down"] is False and incerto["rs_incerto"] == 1 and incerto["down_certo"] == 0
    assert zc["resumo"]["sessao_sem_cadastro"] == 2 and next(m for m in zc["membros"] if m["asn"] == 4200000100)["cadastrado"] is False
    assert api.get("/api/v1/ixps/xx/route-servers", headers=ALLOWED).status_code == 404
    assert za["membros_listados"] == "destaque" and za["membros_total"] > len(za["membros"]) and {m["asn"] for m in za["membros"]} == {m["asn"] for m in za["membros"] if m["membro_down"] or m["perto_do_limite"]}
    todos = api.get("/api/v1/ixps/za/route-servers", params={"membros": "todos"}, headers=ALLOWED).json()
    assert todos["membros_listados"] == "todos" and len(todos["membros"]) == todos["membros_total"] and todos["resumo"] == za["resumo"]
    assert api.get("/api/v1/ixps/za/route-servers", params={"membros": "x"}, headers=ALLOWED).status_code == 422

    a = api.get(f"/api/v1/asns/{membro['asn']}/route-servers", headers=ALLOWED).json()
    lista = a["ixps"]["za"]["lista"]
    assert a["ixps"]["za"]["membro_down"] is True and lista[0]["estado"] == "down" and lista[0]["dias"] == 12 and lista[0]["erro"].startswith("BGP Error")
    assert a["total"]["ixps_down"] == 1
    perfil = api.get(f"/api/v1/asns/{membro['asn']}", params={"include": "route_servers"}, headers=ALLOWED).json()
    assert perfil["route_servers"]["ixps"]["za"]["down"] == 1 and "route_servers" not in api.get(f"/api/v1/asns/{membro['asn']}", headers=ALLOWED).json()
    ptt = api.get("/api/v1/ixps/za", params={"include": "route_servers"}, headers=ALLOWED).json()
    assert ptt["route_servers"]["resumo"] == za["resumo"]

    rk = api.get("/api/v1/ranking/route-servers", params={"ixp": "za"}, headers=ALLOWED).json()
    assert rk["items"][0]["asn"] == membro["asn"] and rk["items"][0]["posicao"] == 1 and rk["items"][0]["down"] == 1 and rk["items"][0]["down_certo"] == 1 and rk["items"][0]["sessoes"] == 1
    assert "melhor" not in rk["criterio"] and "pior" not in rk["criterio"].lower()
    uso = api.get("/api/v1/ranking/route-servers", params={"ixp": "za", "criterio": "uso_limite"}, headers=ALLOWED).json()["items"]
    assert uso[0]["max_uso_limite"] == 0.9
    assert [x["asn"] for x in api.get("/api/v1/ranking/route-servers", params={"apenas_down": "true"}, headers=ALLOWED).json()["items"]] == [membro["asn"]]
    assert [x["asn"] for x in api.get("/api/v1/ranking/route-servers", params={"apenas_derrubados": "true"}, headers=ALLOWED).json()["items"]] == [membro["asn"]]      # alias antigo
    assert api.get("/api/v1/ranking/route-servers", params={"criterio": "x"}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/ranking/route-servers", params={"ixp": "xx"}, headers=ALLOWED).status_code == 404

    q = api.post("/api/v1/query/rs_sessoes", json={"limit": 50, "filter": {"field": "estado", "op": "eq", "value": "down"}}, headers=ALLOWED).json()["items"]
    assert {x["asn"] for x in q} == {membro["asn"], 4200000101} and {x["asn"]: x["rs_incerto"] for x in q} == {membro["asn"]: False, 4200000101: True}
    assert next(x for x in q if x["asn"] == membro["asn"])["dias_no_estado"] == 12


def test_politica_rejeicoes_e_communities_dos_route_servers(api):
    """Cenário plantado — za: 2º membro com 40 rotas rejeitadas e política restritiva, 3º com blackhole e política seletiva, 4º aberto; zb: estendida e por PTT."""
    za = api.get("/api/v1/ixps/za/rejeicoes", headers=ALLOWED).json()
    assert za["coletado_nivel2"] and "inferido" in za["limites"] and za["parametros"]["min_rotas_perfil"] == 10
    rej = za["rejeicoes"]
    assert rej["rotas_rejeitadas"] == 43 and rej["asns_com_rejeicao"] == 2 and rej["asns_total"] == 2 and rej["cobertura"]["coletados"] == 2 and rej["cobertura"]["elegiveis"] > 2
    assert [(m["codigo"], m["rotulo"], m["rotas"]) for m in rej["por_motivo"]][:2] == [("26162:300:0", "Invalid on RPKI", 25), ("26162:190:1", "Bogon prefix", 10)]
    assert za["politica"]["perfis"] == {"aberto": 1, "restritivo": 1, "seletivo": 1} and za["politica"]["blackhole"] == {"asns": 1, "rotas": 2}
    pag = api.get("/api/v1/ixps/za/rejeicoes", params={"limit": 1, "page": 2}, headers=ALLOWED).json()["rejeicoes"]
    assert pag["asns_total"] == 2 and len(pag["asns"]) == 1 and pag["asns"][0]["rotas"] == 3
    assert [a["asn"] for a in api.get("/api/v1/ixps/za/rejeicoes", params={"motivo": "26162:616:666"}, headers=ALLOWED).json()["rejeicoes"]["asns"]] == [rej["asns"][1]["asn"]]
    assert api.get("/api/v1/ixps/xx/rejeicoes", headers=ALLOWED).status_code == 404 and api.get("/api/v1/ixps/za/rejeicoes", params={"limit": 0}, headers=ALLOWED).status_code == 422
    a1, a2 = (x["asn"] for x in rej["asns"])          # 40 rotas rejeitadas (restritivo) e 3 (blackhole, seletivo)
    r = api.get(f"/api/v1/asns/{a1}/politica", headers=ALLOWED).json()
    z = r["ixps"]["za"]
    assert z["rejeicoes"]["rotas"] == 40 and len(z["rejeicoes"]["motivos"][0]["amostra"]) <= 5 and r["evidencia_rs"]["rpki_invalido"] == 25
    assert z["politica"]["perfil"] == "restritivo" and z["politica"]["perfil_inferido"] is True and "exportar somente para" in z["politica"]["perfil_criterio"]
    sel = api.get(f"/api/v1/asns/{a2}/politica", params={"ixp": "za"}, headers=ALLOWED).json()
    assert sel["ixps"]["za"]["politica"]["perfil"] == "seletivo" and sel["ixps"]["za"]["politica"]["acoes"]["nao_exportar_para"]["alvos_total"] == 3
    assert api.get(f"/api/v1/asns/{a1}/politica", params={"ixp": "zc"}, headers=ALLOWED).status_code == 404 and api.get("/api/v1/asns/1/politica", headers=ALLOWED).status_code == 404
    perfil = api.get(f"/api/v1/asns/{a1}", params={"include": "politica_rs"}, headers=ALLOWED).json()
    assert perfil["politica_rs"]["ixps"]["za"]["politica"]["perfil"] == "restritivo" and "politica_rs" not in api.get(f"/api/v1/asns/{a1}", headers=ALLOWED).json()
    ptt = api.get("/api/v1/ixps/za", params={"include": "rejeicoes"}, headers=ALLOWED).json()
    assert ptt["rejeicoes"]["rejeicoes"]["rotas_rejeitadas"] == 43 and "rejeicoes" not in api.get("/api/v1/ixps/za", headers=ALLOWED).json()

    c = api.get("/api/v1/communities", params={"q": "64510"}, headers=ALLOWED).json()
    assert {x["community"] for x in c["items"]} >= {"65000:0:64510", "65000:64510"}
    assert c["por_classe"]["nao_exportar_para"] >= 2 and c["items"][0]["ixps"]["za"]["top"][0]["asn"] == a2
    g = api.get("/api/v1/communities", params={"classe": "blackhole", "ixp": "za"}, headers=ALLOWED).json()
    assert [x["community"] for x in g["items"]] == ["65535:666"] and g["items"][0]["rotas_total"] == 2
    assert api.get("/api/v1/communities", params={"classe": "XX!"}, headers=ALLOWED).status_code == 422 and api.get("/api/v1/communities", params={"limit": 501}, headers=ALLOWED).status_code == 422
    assert api.get("/api/v1/communities", params={"q": "zzzz-inexistente"}, headers=ALLOWED).json()["total"] == 0

    f = api.post("/api/v1/query/rs_filtradas", json={"limit": 50, "filter": {"field": "motivo", "op": "eq", "value": "26162:300:0"}}, headers=ALLOWED).json()["items"]
    assert {(x["ixp"], x["rotas"]) for x in f} == {("za", 25), ("zb", 6)}
    q = api.post("/api/v1/query/rs_communities", json={"limit": 50, "filter": {"and": [{"field": "classe", "op": "eq", "value": "exportar_somente_para"}]}}, headers=ALLOWED).json()["items"]
    assert len(q) == 1 and q[0]["fracao"] == 1.0 and q[0]["alvo_asn"] and q[0]["asn"] == a1


def test_cetic_tabelas_indicadores_e_colecao(api):
    """Tabelas reais do Cetic.br (fixtures) servidas em formato longo, com edição, licença e margem de erro."""
    t = api.get("/api/v1/cetic/tabelas", headers=ALLOWED).json()
    assert t["edicao"] == 2025 and t["licenca"] == "CC BY 4.0" and "Cetic.br|NIC.br" in t["fonte"] and t["total"] == 15 and "estimativas amostrais" in t["aviso"].lower()
    assert api.get("/api/v1/cetic/tabelas", params={"pesquisa": "provedores"}, headers=ALLOWED).json()["total"] == 42
    r = api.get("/api/v1/cetic/indicadores", params={"tabela": "A1", "recorte": "total", "resposta": "sim"}, headers=ALLOWED).json()
    assert r["total"] == 1 and r["items"][0]["proporcao"] == pytest.approx(31.68, abs=0.01) and r["items"][0]["margem_proporcao"] > 0 and r["items"][0]["titulo_tabela"]
    reg = api.get("/api/v1/cetic/indicadores", params={"tabela": "A1", "dimensao": "região", "resposta": "Sim", "limit": 2, "page": 2}, headers=ALLOWED).json()
    assert reg["total"] == 5 and len(reg["items"]) == 2
    assert api.get("/api/v1/cetic/indicadores", params={"tabela": "ZZ"}, headers=ALLOWED).status_code == 404
    assert api.get("/api/v1/cetic/indicadores", params={"pesquisa": "x"}, headers=ALLOWED).status_code == 400
    q = api.post("/api/v1/query/cetic_indicadores", json={"limit": 5, "filter": {"and": [{"field": "pesquisa", "op": "eq", "value": "provedores"},
                                                                                       {"field": "dimensao", "op": "eq", "value": "Porte do provedor"}]}}, headers=ALLOWED).json()
    assert q["total"] > 0 and all(x["pesquisa"] == "provedores" and x["edicao"] == 2024 for x in q["items"])
    assert not any("email" in x or "telefone" in x for x in q["items"])


def test_cetic_estimativas_por_uf_com_erro_padrao_e_supressao(api):
    """Estimativas do Arandurapé sobre microdados sintéticos (layout real): rotuladas, com erro-padrão, validação e UF pequena suprimida."""
    r = api.get("/api/v1/cetic/estimativas", headers=ALLOWED).json()
    assert r["natureza"] == "estimativa_arandurape" and r["edicao"] == 2025 and r["total"] == 33 and "não é número publicado pelo Cetic.br" in r["aviso"]
    assert r["metodo"]["replicas"] == 200 and r["validacao"]["comparados"] == 12 and r["validacao"]["diferenca_max_proporcao_pp"] >= 0
    ufs = api.get("/api/v1/cetic/estimativas", params={"tipo": "uf", "indicador": "internet"}, headers=ALLOWED).json()
    assert ufs["total"] == 27 and all(set(i["indicadores"]) == {"internet"} for i in ufs["items"])
    sp = api.get("/api/v1/cetic/estimativas/uf/sp", headers=ALLOWED).json()
    e = sp["estimativas"]["indicadores"]["internet"]
    assert sp["uf"] == "SP" and sp["regiao"] == "Sudeste" and sp["estimativas"]["n"] == 36 and e["margem"] == pytest.approx(1.96 * e["erro_padrao"], abs=0.002)
    assert sp["comparacao"]["regiao"]["nome"] == "Sudeste" and sp["comparacao"]["brasil"]["nome"] == "BR"
    ap = api.get("/api/v1/cetic/estimativas/uf/AP", headers=ALLOWED).json()["estimativas"]["indicadores"]["internet"]
    assert set(ap) == {"suprimido"}
    assert api.get("/api/v1/cetic/estimativas/uf/XX", headers=ALLOWED).status_code == 404
    assert api.get("/api/v1/cetic/estimativas", params={"tipo": "x"}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/cetic/estimativas", params={"indicador": "x"}, headers=ALLOWED).status_code == 400
    perfil = api.get("/api/v1/ufs/SP", params={"include": "cetic"}, headers=ALLOWED).json()
    assert perfil["cetic"]["uf"] == "SP" and "cetic" not in api.get("/api/v1/ufs/SP", headers=ALLOWED).json()
    q = api.post("/api/v1/query/cetic_estimativas_uf", json={"limit": 100, "filter": {"field": "tipo", "op": "eq", "value": "uf"}}, headers=ALLOWED).json()
    assert q["total"] == 27 * 3 and next(x for x in q["items"] if x["uf"] == "AP" and x["indicador"] == "internet")["suprimido"]
    assert not any("quest" in str(x).lower() or "id_domicilio" in str(x).lower() for x in q["items"])           # nenhuma linha de domicílio


def test_demanda_oferta_por_uf_rotulada_com_intervalo(api):
    """Demanda × oferta sobre o sintético: rótulo de estimativa, intervalo coerente, soma das UFs e coleção do /query."""
    r = api.get("/api/v1/mercado/demanda-oferta", headers=ALLOWED).json()
    assert r["natureza"] == "estimativa_arandurape" and r["tic_edicao"] == 2025 and "acesso não é domicílio" in r["limites"]
    assert len(r["ufs"]) == 9 and set(r["regioes"]) == {"Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"}      # o sintético tem 9 UFs no território
    assert r["brasil"]["domicilios_projetados"] == sum(u["domicilios_projetados"] for u in r["ufs"].values())
    assert r["brasil"]["oferta_acessos_pf"] == sum(u["oferta_acessos_pf"] for u in r["ufs"].values())
    for u in r["ufs"].values():
        assert u["classe"] in ("oferta_abaixo_da_demanda", "compativel", "oferta_acima_da_demanda", "indeterminado")
        if "razao" in u:
            assert u["razao_min"] <= u["razao"] <= u["razao_max"] and u["nao_visto_min"] <= u["nao_visto"] <= u["nao_visto_max"]
    sp = api.get("/api/v1/mercado/demanda-oferta", params={"uf": "sp"}, headers=ALLOWED).json()
    assert sp["uf"] == "SP" and sp["regiao"] == "Sudeste" and sp["demanda_oferta"] == r["ufs"]["SP"] and sp["comparacao"]["brasil"] == r["brasil"]
    assert api.get("/api/v1/mercado/demanda-oferta", params={"uf": "XX"}, headers=ALLOWED).status_code == 404
    perfil = api.get("/api/v1/ufs/SP", params={"include": "cetic"}, headers=ALLOWED).json()
    assert perfil["demanda_oferta"]["uf"] == "SP" and "demanda_oferta" not in api.get("/api/v1/ufs/SP", headers=ALLOWED).json()
    q = api.post("/api/v1/query/demanda_oferta", json={"limit": 100}, headers=ALLOWED).json()
    assert q["total"] == 1 + 5 + 9 and {x["tipo"] for x in q["items"]} == {"brasil", "regiao", "uf"}


def test_erbs_resumo_municipios_perfis_e_colecao(api):
    """Estações do SMP licenciadas sobre o sintético: rotuladas como cadastro, filtro por geração, blocos nos perfis e coleção do /query."""
    r = api.get("/api/v1/erbs/resumo", headers=ALLOWED).json()
    assert r["natureza"] == "cadastro_licenciamento" and "não é cobertura" in r["limites"] and r["brasil"]["estacoes"] == 45 and len(r["operadoras"]) == 3
    assert r["casamento"]["com_municipio_no_ibge"] == 44 and r["casamento"]["sem_cnpj_apos_razao_social"] == 0
    sp = api.get("/api/v1/erbs/resumo", params={"uf": "sp"}, headers=ALLOWED).json()
    assert sp["uf"] == "SP" and sp["resumo"]["estacoes"] == r["ufs"]["SP"]["estacoes"] and api.get("/api/v1/erbs/resumo", params={"uf": "XX"}, headers=ALLOWED).status_code == 404
    todos = api.get("/api/v1/erbs/municipios", params={"limit": 100}, headers=ALLOWED).json()
    assert todos["total"] == 11 and todos["items"][0]["estacoes"] >= todos["items"][-1]["estacoes"]
    g5 = api.get("/api/v1/erbs/municipios", params={"geracao": "5G", "limit": 100}, headers=ALLOWED).json()
    assert g5["total"] == 8 and all(x["estacoes_5g"] > 0 for x in g5["items"]) and g5["ordem"] == "estacoes_5g"
    assert api.get("/api/v1/erbs/municipios", params={"geracao": "6G"}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/erbs/municipios", params={"ordem": "x"}, headers=ALLOWED).status_code == 400
    m = api.get("/api/v1/municipios/9900001", params={"include": "erbs"}, headers=ALLOWED).json()["erbs"]
    assert m["estacoes"] == 4 and m["geracoes"]["5G"] == 1 and {o["marca"] for o in m["operadoras"]} and m["comparacao_uf"]["estacoes"] >= m["estacoes"]
    assert "erbs" not in api.get("/api/v1/municipios/9900001", headers=ALLOWED).json()
    assert api.get("/api/v1/ufs/SP", params={"include": "erbs"}, headers=ALLOWED).json()["erbs"]["uf"] == "SP"
    cnpj = r["operadoras"][0]["cnpj"]
    op = api.get(f"/api/v1/operadoras/{cnpj}", params={"include": "erbs"}, headers=ALLOWED)
    assert op.status_code == 200 and op.json()["erbs"]["estacoes"] == r["operadoras"][0]["estacoes"]
    q = api.post("/api/v1/query/erbs_municipio", json={"limit": 100}, headers=ALLOWED).json()
    assert q["total"] == 11 and not any("lat" in x or "lon" in x for x in q["items"])


def test_mapa_erbs_grade_por_geracao_e_agregada(api):
    """A camada Antenas do mapa vem em células (não em pontos de estação), com filtro por geração."""
    r = api.get("/api/v1/map/erbs", headers=ALLOWED).json()
    assert r["natureza"] == "cadastro_licenciamento" and r["passo_graus"] == 0.02 and r["geracao"] is None
    assert sum(f["properties"]["estacoes"] for f in r["features"]) == 45 and all(f["geometry"]["type"] == "Point" for f in r["features"])
    assert all(f["properties"]["n"] == f["properties"]["estacoes"] for f in r["features"])
    g5 = api.get("/api/v1/map/erbs", params={"geracao": "5G"}, headers=ALLOWED).json()
    assert 0 < len(g5["features"]) < len(r["features"]) and all(f["properties"]["n"] == f["properties"]["g5"] > 0 for f in g5["features"])
    assert api.get("/api/v1/map/erbs", params={"geracao": "9G"}, headers=ALLOWED).status_code == 400


def test_ipv4_mercado_transferencias_resumo_recuperacao_e_ciclo_de_vida(api):
    """Operações (lote = 1), pessoa física mascarada, filtros, casamento com ASN, recuperação e ciclo de vida de um bloco; coleções do /query."""
    r = api.get("/api/v1/ipv4/transferencias", params={"limit": 100}, headers=ALLOWED).json()
    assert r["natureza"] == "observado" and "causa nem intenção" in r["limites"] and r["total"] == 4
    por_data = {o["data"]: o for o in r["items"]}
    assert por_data["2026-03-01"]["n_blocos"] == 2 and por_data["2026-08-20"]["origem"]["nome"] == "Pessoa física" and por_data["2026-09-10"]["fontes"] == ["registrobr", "lacnic"]
    assert "JOAO DA SILVA" not in str(r)                                                          # a máscara vale em toda a resposta
    assert api.get("/api/v1/ipv4/transferencias", params={"direcao": "br_exterior"}, headers=ALLOWED).json()["total"] == 1
    assert api.get("/api/v1/ipv4/transferencias", params={"ano": "2025"}, headers=ALLOWED).json()["total"] == 0
    assert api.get("/api/v1/ipv4/transferencias", params={"prefixo": "198.18.4.0/24"}, headers=ALLOWED).json()["total"] == 1
    assert api.get("/api/v1/ipv4/transferencias", params={"q": "delta"}, headers=ALLOWED).json()["total"] == 1
    assert api.get("/api/v1/ipv4/transferencias", params={"direcao": "x"}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/ipv4/transferencias", params={"prefixo": "2001:db8::/32"}, headers=ALLOWED).status_code == 400
    m = api.get("/api/v1/ipv4/transferencias/resumo", headers=ALLOWED).json()
    assert m["operacoes"] == 4 and m["por_ano"]["2026"]["operacoes"] == 4 and m["casamento"]["destino_br"] == 3 and m["periodo"][0] == "2026-03-01"
    rc = api.get("/api/v1/ipv4/recuperacao", headers=ALLOWED).json()
    assert rc["em_recuperacao"]["por_tipo"] == {"bloco": 1, "asn": 1} and rc["eventos_por_mes"]["2026-09"]["recuperacao"] == 256 and rc["em_recuperacao"]["itens"][0]["status_delegated"] == "reserved"
    cv = api.get("/api/v1/ipv4/blocos/198.18.2.0/24/ciclo-de-vida", headers=ALLOWED).json()
    assert cv["bloco"] == "198.18.2.0/24" and {x["tipo"] for x in cv["linha_do_tempo"]} == {"titularidade", "transferencia"} and cv["atual"][0]["status"] == "allocated"
    assert "sem causa nem intenção" in cv["aviso"] and all(not k.startswith("_") for x in cv["linha_do_tempo"] for k in x["detalhe"])
    assert api.get("/api/v1/ipv4/blocos/10.99.0.0/24/ciclo-de-vida", headers=ALLOWED).status_code == 404
    assert api.get("/api/v1/ipv4/blocos/xyz/ciclo-de-vida", headers=ALLOWED).status_code == 400
    q = api.post("/api/v1/query/transferencias_ipv4", json={"limit": 10, "filter": {"field": "direcao", "op": "eq", "value": "br_br"}}, headers=ALLOWED).json()
    assert q["total"] == 2 and all(x["destino_pais"] == "BR" for x in q["items"])
    ev = api.post("/api/v1/query/eventos_bloco", json={"limit": 10}, headers=ALLOWED).json()
    assert ev["total"] == 2 and {x["tipo"] for x in ev["items"]} == {"titularidade", "recuperacao"}
    assert api.post("/api/v1/query/recuperacao_ipv4", json={"limit": 10}, headers=ALLOWED).json()["total"] == 2


def test_ipv4_espaco_sem_uso_e_uso_por_terceiros_sao_hipotese_com_regra_visivel(api):
    """Classes pela tabela de origens, filtros, sinais com evidência e falsos positivos, S5 a S7 declarados não avaliados; blocos do ASN e coleções do /query."""
    e = api.get("/api/v1/ipv4/espaco", params={"limit": 100}, headers=ALLOWED).json()
    assert e["natureza"] == "inferido" and "Não anunciado não é sem uso" in e["limites"] and e["resumo"]["total_blocos"] > 0
    assert set(e["resumo"]["por_classe"]) <= {"anunciado", "parcial", "roa_sem_anuncio", "nao_anunciado", "em_recuperacao"} and all(x["classe"] != "anunciado" for x in e["items"])
    for c in ("nao_anunciado", "parcial", "em_recuperacao"):
        assert api.get("/api/v1/ipv4/espaco", params={"classe": c}, headers=ALLOWED).status_code == 200
    assert api.get("/api/v1/ipv4/espaco", params={"classe": "x"}, headers=ALLOWED).status_code == 400
    u = api.get("/api/v1/ipv4/uso-por-terceiros", params={"limit": 100}, headers=ALLOWED).json()
    assert u["rotulo"] == "hipótese de uso por terceiros" and "aluguel" not in u["rotulo"].lower() and set(u["sinais"]) == {"S1", "S2", "S3", "S4", "S5", "S6", "S7"}
    assert [k for k, v in u["sinais"].items() if not v["avaliado"]] == ["S5", "S6", "S7"] and all(v["falsos_positivos"] for k, v in u["sinais"].items() if v["avaliado"])
    assert all(i["sinais"] and i["confianca"] in ("baixa", "media", "alta") and all(s["evidencia"] for s in i["sinais"]) for i in u["items"])
    assert api.get("/api/v1/ipv4/uso-por-terceiros", params={"sinal": "S9"}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/ipv4/uso-por-terceiros", params={"confianca": "x"}, headers=ALLOWED).status_code == 400
    q = api.post("/api/v1/query/uso_por_terceiros_ipv4", json={"limit": 5}, headers=ALLOWED).json()
    assert q["total"] == u["total"] and api.post("/api/v1/query/espaco_ipv4", json={"limit": 5}, headers=ALLOWED).json()["total"] == e["total"]
    assert api.get("/api/v1/ipv4/asns/1", headers=ALLOWED).status_code == 404


def test_ipv4_subasignacoes_aguardando_a_publicacao_oficial_com_vigia(api):
    """Sem a bitácora oficial a rota diz que aguarda, não inventa registro e traz o estado do vigia; coleção vazia."""
    r = api.get("/api/v1/ipv4/subasignacoes", headers=ALLOWED).json()
    assert r["ativa"] is False and r["aguardando"] is True and "Aguardando a publicação oficial" in r["aviso"] and r["total"] == 0 and r["items"] == [] and r["esquema_hipotetico"] is True
    assert r["politica"]["nome"] == "LAC-2025-5" and set(r["validacoes"]) >= {"receptor_origina", "tem_roa", "tamanho", "receptor_ipv6", "prazo_3_anos", "nao_infra_critica"} and "vigia" in r
    assert r["indicador_terceiros"]["com_registro"] is None
    assert api.post("/api/v1/query/subasignacoes_ipv4", json={"limit": 5}, headers=ALLOWED).json()["total"] == 0


def test_fust_resumo_municipios_perfis_e_colecao(api):
    r = api.get("/api/v1/fust/resumo", headers=ALLOWED).json()
    assert r["natureza"] == "cadastro_regulatorio" and "executora" in r["limites"] and r["brasil"]["compromissos"] > 0 and r["casamento"]["sem_municipio_no_ibge"] == 1
    soma = sum(u["compromissos"] for u in r["ufs"].values())
    assert soma == r["brasil"]["compromissos"] and {p["codigo"] for p in r["programas"]} == {"1.1", "2.2", "2.6"}
    sp = api.get("/api/v1/fust/resumo", params={"uf": "sp"}, headers=ALLOWED).json()
    assert sp["uf"] == "SP" and sp["resumo"]["compromissos"] == r["ufs"]["SP"]["compromissos"]
    assert api.get("/api/v1/fust/resumo", params={"uf": "XX"}, headers=ALLOWED).status_code == 404
    todos = api.get("/api/v1/fust/municipios", params={"limit": 100}, headers=ALLOWED).json()
    assert todos["total"] == r["brasil"]["municipios_com_compromisso"] and all(x["compromissos"] > 0 for x in todos["items"])
    ubs = api.get("/api/v1/fust/municipios", params={"programa": "2.6", "limit": 100}, headers=ALLOWED).json()
    assert 0 < ubs["total"] < todos["total"] and all("2.6" in x["programas"] for x in ubs["items"])
    assert api.get("/api/v1/fust/municipios", params={"programa": "9.9"}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/fust/municipios", params={"ordem": "x"}, headers=ALLOWED).status_code == 400
    ibge = todos["items"][0]["ibge"]
    m = api.get(f"/api/v1/municipios/{ibge}", params={"include": "fust"}, headers=ALLOWED).json()["fust"]
    assert m["compromissos"] == todos["items"][0]["compromissos"] and m["natureza"] == "cadastro_regulatorio" and "1.1" in m["programas_nomes"]
    assert "fust" not in api.get(f"/api/v1/municipios/{ibge}", headers=ALLOWED).json()
    assert api.get("/api/v1/ufs/SP", params={"include": "fust"}, headers=ALLOWED).json()["fust"]["uf"] == "SP"
    q = api.post("/api/v1/query/fust_municipio", json={"limit": 100}, headers=ALLOWED).json()
    assert q["total"] == todos["total"]
    assert not ({"cnpj", "email", "telefone"} & _keys(r))



def test_multas_espectro_e_satelites(api):
    r = api.get("/api/v1/multas/resumo", headers=ALLOWED).json()
    assert r["natureza"] == "cadastro_regulatorio" and "não é condenação definitiva" in r["limites"] and r["brasil"]["empresas"] == 5 and r["brasil"]["multas"] == 13
    assert set(r["por_grupo"]) == {"SCM", "SMP"} and r["por_grupo"]["SMP"]["multas"] == 10 and [a["ano"] for a in r["por_ano"]] == [2012, 2015, 2018, 2019, 2020, 2021]
    todas = api.get("/api/v1/multas/empresas", params={"limit": 100}, headers=ALLOWED).json()
    assert todas["total"] == 5 and todas["items"][0]["saldo"] == 9000.0 and all(len(x["raiz"]) == 8 for x in todas["items"])
    scm = api.get("/api/v1/multas/empresas", params={"grupo": "SCM"}, headers=ALLOWED).json()
    assert scm["total"] == 2 and api.get("/api/v1/multas/empresas", params={"grupo": "XX"}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/multas/empresas", params={"ordem": "x"}, headers=ALLOWED).status_code == 400
    raiz = todas["items"][0]["raiz"]
    assert api.get("/api/v1/multas/empresas", params={"q": raiz}, headers=ALLOWED).json()["total"] >= 1
    cnpj = next(x["cnpj_matriz"] for x in todas["items"] if x["cnpj_matriz"] and x["raiz"] != "99999999")
    op = api.get(f"/api/v1/operadoras/{cnpj}", params={"include": "multas"}, headers=ALLOWED)
    assert op.status_code == 200 and op.json()["multas"]["multas"] >= 1 and "multas" not in api.get(f"/api/v1/operadoras/{cnpj}", headers=ALLOWED).json()
    assert api.post("/api/v1/query/multas_empresa", json={"limit": 100}, headers=ALLOWED).json()["total"] == 5
    assert not ({"cpf", "email", "telefone"} & _keys(r)) and not ({"cpf", "email", "telefone"} & _keys(todas))
    # CNPJ que só tem multa (sem ASN, outorga nem SICI): perfil mínimo com `include=multas`; sem o include continua 404
    so = api.get("/api/v1/operadoras/99999999000191", params={"include": "multas"}, headers=ALLOWED)
    assert so.status_code == 200 and set(so.json()) == {"snapshot_date", "cnpj", "multas"} and so.json()["multas"]["multas"] == 1
    assert api.get("/api/v1/operadoras/99999999000191", headers=ALLOWED).status_code == 404
    assert api.get("/api/v1/operadoras/88888888000191", params={"include": "multas"}, headers=ALLOWED).status_code == 404

    e = api.get("/api/v1/espectro/resumo", headers=ALLOWED).json()
    ref = {x["nome"]: x for x in e["referencias"]}
    assert e["natureza"] == "norma" and "É norma, não licença" in e["limites"]
    assert ref["3,5 GHz"]["faixas"] == 2 and ref["700 MHz"]["destinacao"][0]["servico"] == "MÓVEL PESSOAL"
    f = api.get("/api/v1/espectro/faixas", params={"de": 3300, "ate": 3500}, headers=ALLOWED).json()
    assert f["total"] == 2 and f["referencias"] is None
    assert api.get("/api/v1/espectro/faixas", params={"servico": "móvel pessoal"}, headers=ALLOWED).json()["total"] == 3
    assert api.get("/api/v1/espectro/faixas", params={"servico": "radioamador", "carater": "Primário"}, headers=ALLOWED).json()["total"] == 0
    assert api.get("/api/v1/espectro/faixas", params={"de": 5, "ate": 1}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/espectro/faixas", params={"carater": "x"}, headers=ALLOWED).status_code == 400
    assert api.post("/api/v1/query/faixas_espectro", json={"limit": 100}, headers=ALLOWED).json()["total"] == 5

    s = api.get("/api/v1/satelites/resumo", headers=ALLOWED).json()
    assert s["resumo"]["direitos"] == 4 and s["resumo"]["vencidos_na_data"] == 1 and s["resumo"]["por_tipo"] == {"Estrangeiro": 3, "Brasileiro": 1} and len(s["ngeo"]) == 4 and len(s["ngeo_sistemas"]) == 2
    d = api.get("/api/v1/satelites/direitos", params={"tipo": "Brasileiro"}, headers=ALLOWED).json()
    assert d["total"] == 1 and d["items"][0]["vencido"] is True
    assert api.get("/api/v1/satelites/direitos", params={"operadora": "alfa"}, headers=ALLOWED).json()["total"] == 2
    assert api.get("/api/v1/satelites/direitos", params={"tipo": "x"}, headers=ALLOWED).status_code == 400
    assert api.post("/api/v1/query/satelites_direitos", json={"limit": 100}, headers=ALLOWED).json()["total"] == 4


def test_prontidao_resumo_blocos_e_colecao_sem_lista_nominal(api):
    r = api.get("/api/v1/prontidao/resumo", headers=ALLOWED).json()
    assert r["natureza"] == "indice_composto" and r["regras"]["versao"] == 1 and set(r["regras"]["pilares"]) == {"filtragem", "anti_spoofing", "coordenacao", "validacao_global"}
    assert "Não é veredito" in r["limites"] and r["agregado"]["asns"] == sum(r["agregado"]["classes"].values()) and "SP" in r["por_uf"]
    sp = api.get("/api/v1/prontidao/resumo", params={"uf": "sp"}, headers=ALLOWED).json()
    assert sp["escopo"] == {"uf": "SP"} and sp["agregado"] == r["por_uf"]["SP"] and api.get("/api/v1/prontidao/resumo", params={"uf": "XX"}, headers=ALLOWED).status_code == 404
    a = api.get("/api/v1/asns/64500", params={"include": "prontidao"}, headers=ALLOWED).json()["prontidao"]
    assert a["classe"] in ("pronto", "em_progresso", "atrasado") and a["total"] is not None and "anti_spoofing" in a["pilares"] and a["pilares"]["anti_spoofing"]["componentes"]["spoofer"]["valor"] == 100.0
    assert a["pilares"]["validacao_global"]["componentes"]["irr"]["valor"] == 100.0 and a["regras"]["hash"] and a["brasil"]["asns"] == r["agregado"]["asns"]
    b = api.get("/api/v1/asns/64501", params={"include": "prontidao"}, headers=ALLOWED).json()["prontidao"]
    assert b["pilares"]["anti_spoofing"]["componentes"]["spoofer"]["valor"] == 40.0 and b["pilares"]["validacao_global"]["componentes"]["irr"]["valor"] < 100.0
    c = api.get("/api/v1/asns/64502", params={"include": "prontidao"}, headers=ALLOWED).json()["prontidao"]
    assert "anti_spoofing" in c["pilares_sem_dado"]                            # Spoofer com poucas sessões conclusivas não pontua
    assert a["faixa_porte"] in ("sem_usuarios", "ate_1000", "de_1000_a_10000", "de_10000_a_100000", "de_100000_a_1000000", "acima_de_1000000") and "faixa_acessos_sici" in a
    assert set(r["por_faixa_porte"]) <= {"sem_usuarios", "ate_1000", "de_1000_a_10000", "de_10000_a_100000", "de_100000_a_1000000", "acima_de_1000000"}
    assert "prontidao" not in api.get("/api/v1/asns/64500", headers=ALLOWED).json()
    uf = api.get("/api/v1/ufs/SP", params={"include": "prontidao"}, headers=ALLOWED).json()["prontidao"]
    assert uf["uf"] == "SP" and uf["agregado"]["asns"] > 0
    q = api.post("/api/v1/query/prontidao_agregado", json={"limit": 100}, headers=ALLOWED).json()
    assert {x["tipo"] for x in q["items"]} == {"brasil", "uf", "porte"} and q["total"] == 1 + len(r["por_uf"]) + len(r["por_faixa_porte"])
    assert not any(k in x for x in q["items"] for k in ("asn", "cnpj", "operadora"))              # sem lista nominal
    assert not ({"cnpj", "email", "telefone"} & _keys(r))


def test_prontidao_lista_nominal_desligada_e_ligada(api, monkeypatch):
    # desligada (PRONTIDAO_LISTA_NOMINAL=0; o padrão é ligada): rota e coleção respondem com mensagem, a coluna da lista é ignorada
    monkeypatch.setenv("PRONTIDAO_LISTA_NOMINAL", "0")
    r = api.get("/api/v1/prontidao/asns", headers=ALLOWED)
    assert r.status_code == 404 and "metodologia" in r.json()["detail"]
    assert api.post("/api/v1/query/prontidao_asn", json={"limit": 10}, headers=ALLOWED).status_code == 400
    off = api.get("/api/v1/asns", params={"br_only": "true", "include": "prontidao"}, headers=ALLOWED).json()["items"]
    assert off and not any("prontidao_indice" in i and i["prontidao_indice"] is not None for i in off)
    # ligada
    monkeypatch.setenv("PRONTIDAO_LISTA_NOMINAL", "1")
    todos = api.get("/api/v1/prontidao/asns", params={"limit": 1000}, headers=ALLOWED).json()
    assert todos["total"] == len(todos["items"]) > 0 and todos["regras"]["hash"] and "Não é veredito" in todos["limites"]
    com = [i for i in todos["items"] if i["indice"] is not None]
    assert [i["indice"] for i in com] == sorted(i["indice"] for i in com)               # do menor ao maior
    assert all(i["indice"] is None for i in todos["items"][len(com):])                  # sem índice vai ao fim
    um = next(i for i in todos["items"] if i["asn"] == 64500)
    assert um["classe"] in ("pronto", "em_progresso", "atrasado") and um["pilar_anti_spoofing"] is not None and "cnpj" not in um
    por_classe = api.get("/api/v1/prontidao/asns", params={"classe": um["classe"]}, headers=ALLOWED).json()
    assert 0 < por_classe["total"] <= todos["total"] and all(i["classe"] == um["classe"] for i in por_classe["items"])
    assert api.get("/api/v1/prontidao/asns", params={"min": 101}, headers=ALLOWED).status_code == 422
    assert api.get("/api/v1/prontidao/asns", params={"classe": "x"}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/prontidao/asns", params={"uf": "XX"}, headers=ALLOWED).status_code == 404
    desc = api.get("/api/v1/prontidao/asns", params={"ordem": "usuarios", "desc": "true"}, headers=ALLOWED).json()["items"]
    assert [i["usuarios"] for i in desc] == sorted((i["usuarios"] for i in desc), reverse=True)
    q = api.post("/api/v1/query/prontidao_asn", json={"limit": 1000}, headers=ALLOWED).json()
    assert q["total"] == todos["total"] and not any(k in x for x in q["items"] for k in ("cnpj", "email", "telefone"))
    col = api.get("/api/v1/asns", params={"br_only": "true", "include": "prontidao", "sort_by": "prontidao_indice"}, headers=ALLOWED).json()["items"]
    ind = [i["prontidao_indice"] for i in col if i.get("prontidao_indice") is not None]
    assert ind and ind == sorted(ind) and next(i for i in col if i["asn"] == 64500)["prontidao_classe"] == um["classe"]


def test_manrs_so_agregado_e_nao_vaza_organizacao_nem_asn(api, pipeline):
    """Termos do MANRS (cláusula 2.1): dado de outra rede só agregado. Falha se qualquer artefato publicado, rota ou coleção trouxer registro por organização/ASN vindo da fonte."""
    import gzip

    base, _ = pipeline
    marcadores = ("MANRS-ORG-",)                                             # nome de organização participante (o manifesto cita o id da fonte, que não é dado)
    from tests.synth.generate import T1
    pub = base / "published" / T1
    achados = []
    for f in pub.rglob("*"):
        if f.is_file() and f.suffix in (".json", ".gz", ".atom", ".txt", ".csv"):
            try:
                txt = (gzip.open(f, "rt", encoding="utf-8").read() if f.suffix == ".gz" else f.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                continue
            if any(m in txt for m in marcadores):
                achados.append(str(f.relative_to(pub)))
    assert achados == []                                                    # nenhum artefato publicado cita organização participante
    assert not (pub / "manrs" / "participantes.json.gz").exists()
    # resumo: só agregados, com a atribuição exigida
    r = api.get("/api/v1/seguranca/resumo", headers=ALLOWED).json()["manrs"]
    assert r["atribuicao"] == "Provided by the MANRS with support from the Global Cyber Alliance" and r["natureza"] == "agregado"
    assert r["brasil"]["asns_participantes"] == 13 and r["brasil"]["organizacoes_com_asn_br"] == 7           # 6 orgs × 2 ASNs + a mista (1 ASN BR)
    assert r["brasil"]["pct_asns"] == round(100 * 13 / r["brasil"]["asns"], 1)
    def chaves(o):
        if isinstance(o, dict):
            return set(o) | set().union(*[chaves(v) for v in o.values()])
        return set().union(*[chaves(v) for v in o]) if isinstance(o, list) else set()
    assert not ({"org", "asns_lista", "cnpj", "nome"} & chaves(r)) and "participantes" not in r         # "participantes" só aparece dentro da comparação agregada
    assert any(c.get("suprimido") for c in r["por_uf"].values()) or all(c["asns_participantes"] >= 5 for c in r["por_uf"].values())
    assert api.get("/api/v1/prontidao/resumo", headers=ALLOWED).json()["manrs"] == r
    # nenhuma rota por ASN, operadora ou UF ganha marca de participação
    for url in ("/api/v1/asns/64500?include=prontidao", "/api/v1/asns/64500", "/api/v1/ufs/SP?include=prontidao", "/api/v1/asns?br_only=true&include=prontidao&limit=50"):
        corpo = api.get(url, headers=ALLOWED).text
        assert "manrs" not in corpo.lower() and "MANRS-ORG" not in corpo, url
    for col in ("asns", "seguranca_asn", "prontidao_agregado", "operadoras"):
        corpo = api.post(f"/api/v1/query/{col}", json={"limit": 1000}, headers=ALLOWED).text
        assert "manrs" not in corpo.lower(), col


def test_regiao_artefato_e_rota_sem_prefixo_nem_posicao(api, pipeline):
    """Nenhuma posição de prefixo sai por aqui, só a contagem por município; a rota agrega ASNs dos três vínculos e respeita o teto de municípios."""
    import gzip
    import re

    from tests.synth.generate import T1

    base, _ = pipeline
    arq = base / "published" / T1 / "territorio" / "regiao.json.gz"
    assert arq.exists()
    txt = gzip.open(arq, "rt", encoding="utf-8").read()
    assert not re.search(r"\d+\.\d+\.\d+\.\d+/\d+|[0-9a-f:]{4,}::?/\d+", txt)             # nenhum prefixo IPv4/IPv6
    assert not re.search(r'"(lat|lon|latitude|longitude|city)"', txt)                      # nenhuma posição
    doc = __import__("json").loads(txt)
    assert doc["natureza"] == "inferido" and doc["municipios"] and doc["asns"]
    ibge = next(iter(doc["municipios"]))
    r = api.get("/api/v1/regiao", params={"ibges": ibge}, headers=ALLOWED).json()
    assert r["natureza"] == "inferido" and r["asns"]["total"] == len(r["provedores"]) > 0
    assert set(r["asns"]["por_vinculo"]) == {"sici", "sede", "geo"}
    pt = r["participacao_ptts"]
    assert pt["com_ptt_direto"] + pt["so_indireto"] + pt["sem_ptt"] == r["asns"]["total"]
    assert api.get("/api/v1/regiao", params={"ibges": ""}, headers=ALLOWED).status_code in (400, 422)
    assert api.get("/api/v1/regiao", params={"ibges": ",".join(f"{3200000 + i}" for i in range(51))}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/regiao", params={"ibges": "abc"}, headers=ALLOWED).status_code == 400


def test_organizacao_e_abuso_do_asn_blocos_rotas_e_colecao(api):
    """Organização (CAIDA) com irmãos do Brasil, abuso do Feodo só como contagem (sem IP) e a coleção `organizacoes_asn` do /query."""
    org = api.get("/api/v1/asns/64496/organizacao", headers=ALLOWED).json()
    assert org["org_nome"] and org["fonte"]["citacao"] and org["limites"] and org["snapshot_date"]
    assert api.get("/api/v1/asns/99999999/organizacao", headers=ALLOWED).status_code == 404
    perfil = api.get("/api/v1/asns/64496", params={"include": "organizacao,abuso"}, headers=ALLOWED).json()
    assert perfil["organizacao"]["org_id"] == org["org_id"] and perfil["abuso"]["registrado"] in (True, False)
    assert "abuso" not in api.get("/api/v1/asns/64496", headers=ALLOWED).json()
    q = api.post("/api/v1/query/organizacoes_asn", json={"limit": 50, "filter": {"field": "n_irmaos_br", "op": "gte", "value": 1}}, headers=ALLOWED).json()["items"]
    assert q and all(x["n_irmaos_br"] >= 1 and "feodo_c2" in x for x in q)
    ab = [x for x in api.post("/api/v1/query/organizacoes_asn", json={"limit": 200}, headers=ALLOWED).json()["items"] if x["feodo_c2"]]
    assert len(ab) == 1                                                  # o C2 estrangeiro do Feodo sintético não entra
    r = api.get(f"/api/v1/asns/{ab[0]['asn']}/abuso", headers=ALLOWED).json()
    assert r["registrado"] is True and r["feodo_c2"] == 1 and r["urlhaus"]["estado"] == "indisponivel"
    assert not any(k in str(r) for k in ("ip_address", "203.0.113", "198.51.100"))
def test_qualidade_rqual_rotas_blocos_e_colecao(api):
    """RQUAL por prestadora (sem ranking), série, município, perfis com include e coleção `qualidade_uf`."""
    r = api.get("/api/v1/qualidade/resumo", headers=ALLOWED).json()
    assert r["natureza"] == "medido_ou_apurado" and "não diz nada sobre a qualidade dela" in r["limites"] and r["leitura"]["municipios_com_resultado"] == 3 and r["leitura"]["sem_valor"] == {"NA": 1, "NO": 1}
    assert r["casamento"]["com_cnpj"] == 4 and r["casamento"]["pct_resultados_com_cnpj"] == 100.0 and {i["codigo"] for i in r["indicadores"]} == {"IND4", "INF4-DL", "IND8", "IND2"}
    p = api.get("/api/v1/qualidade/prestadoras", params={"servico": "Banda Larga Fixa", "indicador": "IND4"}, headers=ALLOWED).json()
    assert [x["prestadora"] for x in p["items"]] == ["ALFA", "BETA"] and "sem ranking" in p["ordem"] and p["periodo"] == {"mes": "2026-08"}      # alfabética, não por valor
    assert p["items"][0]["media_ponderada"] == 80.3846 and p["items"][0]["raizes_cnpj"] == ["90000007"] and p["items"][1]["media_ponderada"] is None
    pu = api.get("/api/v1/qualidade/prestadoras", params={"servico": "Banda Larga Fixa", "indicador": "IND4", "uf": "sp"}, headers=ALLOWED).json()
    assert [x["prestadora"] for x in pu["items"]] == ["ALFA"] and pu["periodo"] == {"ano": 2026} and pu["items"][0]["media"] == 62.5
    s = api.get("/api/v1/qualidade/serie", params={"servico": "Banda Larga Fixa", "indicador": "IND4", "prestadora": "alfa"}, headers=ALLOWED).json()
    assert [x["mes"] for x in s["items"]] == ["2026-07", "2026-08"] and s["granularidade"] == "mensal nacional"
    assert api.get("/api/v1/qualidade/prestadoras", params={"servico": "X", "indicador": "IND4"}, headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/qualidade/serie", params={"servico": "Banda Larga Fixa", "indicador": "IND99"}, headers=ALLOWED).status_code == 400
    m = api.get("/api/v1/qualidade/municipios/9900007", headers=ALLOWED).json()
    assert m["nome"] == "Mbaracayú Novo" and m["uf"] == "PR" and {(x["servico"], x["prestadora"]) for x in m["prestadoras"]} == {("Banda Larga Fixa", "ALFA"), ("Telefonia Móvel", "GAMA")}
    alfa = next(x for x in m["prestadoras"] if x["prestadora"] == "ALFA")["itens"][0]
    assert alfa["mes"] == "2026-08" and alfa["resultado"] == 85.0 and alfa["medidas"] == 400 and alfa["erro_amostral"] == 4.0 and alfa["estatistica"] is True      # o último mês, não a média
    assert api.get("/api/v1/qualidade/municipios/9900001", headers=ALLOWED).status_code == 404 and api.get("/api/v1/qualidade/municipios/abc", headers=ALLOWED).status_code == 404
    assert api.get("/api/v1/qualidade/municipios/9900001", params={"opcional": 1}, headers=ALLOWED).status_code == 204
    # blocos nos perfis (só com include)
    uf = api.get("/api/v1/ufs/PR", params={"include": "qualidade,reclamacoes"}, headers=ALLOWED).json()
    assert uf["qualidade"]["itens"][0]["prestadora"] == "ALFA" and uf["reclamacoes"]["anos"][-1]["ano"] == 2026 and "qualidade" not in api.get("/api/v1/ufs/PR", headers=ALLOWED).json()
    mp = api.get("/api/v1/municipios/9900007", params={"include": "qualidade,reclamacoes"}, headers=ALLOWED)
    if mp.status_code == 200:
        assert mp.json()["qualidade"]["nome"] == "Mbaracayú Novo" and mp.json()["reclamacoes"]["anos"][-1]["ano"] == 2026
    op = api.get("/api/v1/operadoras/90000007000104", params={"include": "qualidade,reclamacoes"}, headers=ALLOWED)
    assert op.status_code == 200
    q = op.json()["qualidade"]
    assert q["raiz"] == "90000007" and [p_["prestadora"] for p_ in q["prestadoras"]] == ["ALFA"] and {i["indicador"] for i in q["itens"]} == {"IND4"}
    assert op.json()["reclamacoes"]["marcas"] == [{"marca": "ALFA", "casamento": "curada"}]
    assert api.post("/api/v1/query/qualidade_uf", json={"limit": 50}, headers=ALLOWED).json()["total"] == 4
    assert not ({"cpf", "email", "telefone"} & _keys(r)) and not ({"cpf", "email", "telefone"} & _keys(m))


def test_reclamacoes_rotas_taxa_so_curada_sem_ranking_e_agregados(api):
    """Reclamações agregadas, ligação marca → CNPJ (curada, automática validada por UF, sem CNPJ), taxa por mil acessos e nenhuma ordenação por volume."""
    r = api.get("/api/v1/reclamacoes/resumo", headers=ALLOWED).json()
    assert r["natureza"] == "declarado_por_consumidores" and "não é prova de falha" in r["limites"] and r["leitura"]["corte_contexto"] == "2024-03" and r["leitura"]["reclamacoes"] == 444
    c = r["casamento"]
    assert c["por_metodo"] == {"curada": 294, "sem_marca": 75, "sem_cnpj": 45, "automatico": 30} and c["pct_com_cnpj"] == 72.97 and c["automaticas_descartadas_por_uf"] == ["SEMASN2"]
    assert r["taxas"]["janela"] == {"de": "2025-10", "ate": "2026-09"} and "itens" not in r["taxas"] and r["assuntos_ano"]["ano"] == 2026
    m = api.get("/api/v1/reclamacoes/marcas", params={"ano": 2025, "limit": 100}, headers=ALLOWED).json()
    assert [x["marca"] for x in m["items"]] == sorted(x["marca"] for x in m["items"]) and "sem ranking" in m["ordem"]       # ordem alfabética: o volume não ordena
    por = {x["marca"]: x for x in m["items"]}
    assert por["ALFA"]["reclamacoes"] == 68 and por["ALFA"]["por_servico"] == {"SCM": 52, "SMP_Pós": 16} and por["ALFA"]["casamento"] == "curada" and por["ALFA"]["cnpjs_matriz"] == ["90000007000104"]
    assert por["SEMASN1"]["casamento"] == "automatico" and por["SEMASN2"]["raizes"] == [] and por["NÃO LOCALIZEI A MINHA EMPRESA"]["raizes"] == []
    taxas = {(t["marca"], t["grupo"]): t for x in m["items"] for t in x["taxas"]}
    assert taxas[("ALFA", "SCM")]["por_mil_acessos"] == 23.6873 and taxas[("ALFA", "SCM")]["acessos"] == 6037
    assert taxas[("SEMASN1", "SCM")]["por_mil_acessos"] is None and "tabela curada" in taxas[("SEMASN1", "SCM")]["motivo_sem_taxa"]      # a automática não ganha taxa
    assert taxas[("BETA", "SCM")]["por_mil_acessos"] is None and taxas[("ALFA", "SMP")]["por_mil_acessos"] is None
    assert api.get("/api/v1/reclamacoes/marcas", params={"q": "sem", "com_cnpj": "false", "ano": 2025}, headers=ALLOWED).json()["total"] == 2
    assert api.get("/api/v1/reclamacoes/marcas", params={"servico": "SMP_Pós", "ano": 2025}, headers=ALLOWED).json()["total"] == 1
    assert api.get("/api/v1/reclamacoes/marcas", params={"ano": 1999}, headers=ALLOWED).status_code in (400, 422)
    assert api.get("/api/v1/reclamacoes/marcas", params={"servico": "XYZ"}, headers=ALLOWED).status_code == 400
    mun = api.get("/api/v1/reclamacoes/municipios/9900007", headers=ALLOWED).json()
    assert mun["nome"] == "Mbaracayú Novo" and mun["populacao"] == 147000 and [a["ano"] for a in mun["anos"]] == [2024, 2025, 2026]
    a25 = mun["anos"][1]
    assert a25["reclamacoes"] == 40 + 16 + 20 + 8 and a25["por_servico"] == {"SCM": 68, "SMP_Pós": 16} and a25["por_100mil_hab"] == round(84 * 100000 / 147000, 2)
    assert api.get("/api/v1/reclamacoes/municipios/9900001", headers=ALLOWED).status_code == 404
    op = api.get("/api/v1/operadoras/90000007000104", params={"include": "reclamacoes"}, headers=ALLOWED).json()["reclamacoes"]
    assert [a["ano"] for a in op["anos"]] == [2018, 2019, 2024, 2025, 2026] and op["taxas"]["itens"][0]["marca"] == "ALFA" and "pode agrupar" in op["aviso"]
    assert api.post("/api/v1/query/reclamacoes_marca", json={"limit": 100}, headers=ALLOWED).json()["total"] == 23
    # privacidade: só agregados — nenhuma chave de texto livre, pessoa ou contato
    proibidas = {"cpf", "email", "telefone", "texto", "descricao_reclamacao", "reclamante", "consumidor", "nome_consumidor"}
    assert not (proibidas & _keys(r)) and not (proibidas & _keys(m)) and not (proibidas & _keys(mun)) and not (proibidas & _keys(op))


def test_instalacoes_peeringdb_rotas_blocos_colecoes_e_sem_contato(api):
    """Instalações do PeeringDB (lista, detalhe, PTT, ASN, portas externas), indicador de cadastro inferido, coleções do /query e nenhum contato em nenhuma resposta."""
    import re
    h = ALLOWED
    lista = api.get("/api/v1/facilities", headers=h).json()
    assert lista["total"] == 3 and {x["id"] for x in lista["items"]} == {9101, 9102, 9103} and lista["fonte"]["citacao"] and lista["limites"] and lista["snapshot_date"]
    por_id = {x["id"]: x for x in lista["items"]}
    assert [por_id[i]["cadastro"]["classe"] for i in (9101, 9102, 9103)] == ["recente", "parado", "antigo"] and all(x["cadastro"]["inferido"] for x in lista["items"])
    assert api.get("/api/v1/facilities", params={"pais": "todos"}, headers=h).json()["total"] == 4
    assert {x["id"] for x in api.get("/api/v1/facilities", params={"ptt": "za"}, headers=h).json()["items"]} == {9101, 9102}
    assert [x["id"] for x in api.get("/api/v1/facilities", params={"cadastro": "antigo"}, headers=h).json()["items"]] == [9103]
    assert [x["id"] for x in api.get("/api/v1/facilities", params={"q": "colo", "uf": "rj"}, headers=h).json()["items"]] == [9102]
    assert api.get("/api/v1/facilities", params={"ordem": "x"}, headers=h).status_code == 400
    assert api.get("/api/v1/facilities", params={"cadastro": "x"}, headers=h).status_code == 400
    assert [x["id"] for x in api.get("/api/v1/facilities", params={"ordem": "nome"}, headers=h).json()["items"]] == sorted(por_id, key=lambda i: por_id[i]["nome"].lower())
    d = api.get("/api/v1/facilities/9101", headers=h).json()
    assert d["redes_total"] == 6 and d["campus"]["nome"] == "Campus Exemplo SP" and {c["nome"] for c in d["carriers"]} == {"Carrier Exemplo", "Backbone Exemplo"}
    assert {x.get("code") for x in d["ixps"]} == {"za", "zb"} and d["cadastro"]["inferido"] is True and d["redes"][0]["asn"] and d["lat"]
    assert api.get("/api/v1/facilities/1", headers=h).status_code == 404
    ptt = api.get("/api/v1/ixps/za/facilities", headers=h).json()
    assert ptt["total"] == 2 and api.get("/api/v1/ixps/zc/facilities", headers=h).status_code == 404
    assert [x["id"] for x in api.get("/api/v1/ixps/zx/facilities", headers=h).json()["items"]] == [9201]       # instalação do PTT externo, fora do Brasil
    por = api.get("/api/v1/ixps/zx/portas", headers=h).json()
    assert por["portas"] == 5 and por["capacidade_mbps"] == 50000 and por["por_velocidade"] == {"10000": 5} and por["fonte"] and "não tráfego" in por["limites"]
    assert api.get("/api/v1/ixps/za/portas", headers=h).status_code == 404
    asn = d["redes"][0]["asn"]
    af = api.get(f"/api/v1/asns/{asn}/facilities", headers=h).json()
    assert af["total"] == 2 and {x["id"] for x in af["items"]} == {9101, 9102} and all("no_vinculo_desde" in x for x in af["items"])
    pe = api.get(f"/api/v1/asns/{asn}/peering", headers=h).json()
    assert pe["escopo"] in ("Regional", "Global") and pe["cadastro"]["inferido"] is True and pe["instalacoes_br_observadas"] == 2 and pe["fonte"]
    assert api.get("/api/v1/asns/99999999/peering", headers=h).status_code == 404 and api.get("/api/v1/asns/99999999/facilities", headers=h).status_code == 404
    perfil = api.get(f"/api/v1/asns/{asn}", params={"include": "facilities,peering"}, headers=h).json()
    assert perfil["facilities"]["total"] == 2 and perfil["peering"]["asn"] == asn and "facilities" not in api.get(f"/api/v1/asns/{asn}", headers=h).json()
    pp = api.get("/api/v1/ixps/za", params={"include": "facilities,portas"}, headers=h).json()
    assert pp["facilities"]["total"] == 2 and pp["portas"] is None
    q = api.post("/api/v1/query/facilities", json={"limit": 10, "filter": {"field": "ptts", "op": "contains", "value": "za"}}, headers=h).json()["items"]
    assert {x["id"] for x in q} == {9101, 9102} and all("cadastro_classe" in x for x in q)
    fr = api.post("/api/v1/query/facilidades_rede", json={"limit": 50}, headers=h).json()["items"]
    assert len(fr) == 8 and {x["facility_id"] for x in fr} == {9101, 9102}
    rp = api.post("/api/v1/query/redes_peering", json={"limit": 50}, headers=h).json()["items"]
    assert rp and all("tem_looking_glass" in x for x in rp) and not any("lg.example.org" in str(x) for x in rp)         # a coleção não traz as URLs
    tudo = json.dumps([lista, d, ptt, por, af, pe, perfil["facilities"], perfil["peering"], q, fr, rp], ensure_ascii=False)
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", tudo) and not re.search(r"tech_|sales_|policy_(email|phone)|\"notes\"|\+55", tudo)


def test_consumidor_gov_rotas_agregados_sem_ranking_e_bases_minimas(api):
    """Reclamações finalizadas do Consumidor.gov.br por empresa, UF e município; só agregados, base mínima, ligação rotulada e nenhuma ordenação por volume."""
    r = api.get("/api/v1/consumidor/resumo", headers=ALLOWED).json()
    assert r["natureza"] == "declarado_por_consumidores" and "não é prova de falha" in r["limites"] and r["minimos"] == {"base_para_media": 30, "reclamacoes_por_celula": 5}
    assert r["janela"]["meses"] == 3 and r["janela"]["meses_ausentes"] == [] and [x["mes"] for x in r["setor_por_mes"]] == ["2026-07", "2026-08", "2026-09"]
    c = r["casamento"]
    assert c["por_metodo"] == {"curada": 210, "sem_cnpj": 36, "automatico": 18} and c["pct_com_cnpj"] == 86.36 and c["automaticas_descartadas_por_uf"] == ["SEMASN2"] and c["tabela_curada"]["apelidos_consumidor_gov"] == 2
    assert r["cidades"]["pct_com_codigo_ibge"] == 100.0 and r["leitura"]["reclamacoes_telecom"] == 264       # o plano de saúde do CSV não entra
    m = api.get("/api/v1/consumidor/marcas", params={"limit": 100}, headers=ALLOWED).json()
    assert [x["marca"] for x in m["items"]] == sorted((x["marca"] for x in m["items"]), key=str.lower) and "sem ranking" in m["ordem"]      # ordem alfabética: o volume não ordena
    por = {x["marca"]: x for x in m["items"]}
    alfa = por["Alfa Fibra - Marca A"]
    assert (alfa["n"], alfa["avaliadas"], alfa["resolvidas"], alfa["indice_solucao"], alfa["casamento"], alfa["raizes"], alfa["cnpjs_matriz"]) == (165, 100, 50, 50.0, "curada", ["90000007"], ["90000007000104"])
    assert alfa["tempo_medio_dias"] is not None and alfa["nota_media"] is not None
    assert por["Beta Net"]["avaliadas"] == 26 and por["Beta Net"]["indice_solucao"] is None and por["Beta Net"]["nota_media"] is None      # menos de 30 avaliadas: sem índice nem nota, nulo e não zero
    assert por["SEMASN1"]["casamento"] == "automatico" and por["SEMASN2"]["raizes"] == [] and por["SEM DONO"]["casamento"] is None
    assert [x["marca"] for x in api.get("/api/v1/consumidor/marcas", params={"com_cnpj": "true", "limit": 100}, headers=ALLOWED).json()["items"]] == ["Alfa Fibra - Marca A", "Beta Net", "SEMASN1"]
    assert [x["marca"] for x in api.get("/api/v1/consumidor/marcas", params={"uf": "rs"}, headers=ALLOWED).json()["items"]] == ["Alfa Fibra - Marca A", "Beta Net", "SEM DONO"]      # só RS: a célula Alfa × RS (9) passa do mínimo de 5
    mu = api.get("/api/v1/consumidor/municipios/9900007", headers=ALLOWED).json()
    assert mu["nome"] == "Mbaracayú Novo" and mu["total"]["n"] == 141 and [i["marca"] for i in mu["itens"]] == ["Alfa Fibra - Marca A", "SEMASN2"]      # Beta Net tem 3 reclamações aqui: abaixo do mínimo de célula, não é listada
    assert all(i["n"] >= 5 for i in mu["itens"])
    assert api.get("/api/v1/consumidor/municipios/9900001", headers=ALLOWED).status_code == 404 and api.get("/api/v1/consumidor/municipios/9900001", params={"opcional": 1}, headers=ALLOWED).status_code == 204
    op = api.get("/api/v1/operadoras/90000007000104", params={"include": "consumidor"}, headers=ALLOWED).json()["consumidor"]
    assert op["raiz"] == "90000007" and [x["marca"] for x in op["marcas"]] == ["Alfa Fibra - Marca A"] and len(op["marcas"][0]["por_mes"]) == 3 and op["assuntos"] and op["grupos"]
    assert api.get("/api/v1/ufs/PR", params={"include": "consumidor"}, headers=ALLOWED).json()["consumidor"]["itens"][0]["marca"] == "Alfa Fibra - Marca A"
    assert api.get("/api/v1/municipios/9900007", params={"include": "consumidor"}, headers=ALLOWED).json()["consumidor"]["nome"] == "Mbaracayú Novo"
    colecao = api.post("/api/v1/query/consumidor_marca", json={"limit": 50}, headers=ALLOWED).json()
    assert colecao["total"] == 18 and {x["mes"] for x in colecao["items"]} == {"2026-07", "2026-08", "2026-09"}
    corpo = json.dumps([r, m, mu, op, colecao], ensure_ascii=False)
    assert not ({"sexo", "faixa_etaria", "Sexo", "Faixa Etária"} & _keys(mu)) and "entre 31 a 40" not in corpo and "Saúde Alfa" not in corpo           # nada de pessoa nem de outro segmento


def test_consumidor_marcas_lista_ampliada_exige_login_para_anonimo(api):
    """A lista de empresas é avançada (medida) e ampliar além da prévia exige login."""
    assert api.get("/api/v1/consumidor/marcas", params={"limit": 101}, headers=ANON).status_code in (401, 403)
    assert api.get("/api/v1/consumidor/marcas", params={"page": 2}, headers=ANON).status_code in (401, 403)


def test_instalacoes_lista_expandida_exige_login_para_anonimo(api):
    """A lista de instalações é avançada (medida) e ampliar além da prévia (limit > 100 ou page > 1) exige login."""
    assert api.get("/api/v1/facilities", params={"limit": 101}, headers=ANON).status_code in (401, 403)
    assert api.get("/api/v1/facilities", params={"page": 2}, headers=ANON).status_code in (401, 403)


def test_bloqueios_do_asn_veredito_da_sonda_licenca_minimo_e_sem_ranking(api):
    """OONI por ASN. Licença CC BY-NC-SA e aviso em toda resposta, célula abaixo do mínimo some, ASN estrangeiro fora, testes em lista (sem a chave `whatsapp`)."""
    q = api.post("/api/v1/query/bloqueios_asn", json={"limit": 50}, headers=ALLOWED).json()["items"]
    assert q and all(x["licenca"] == "CC BY-NC-SA 4.0" and x["veredito"] == "da sonda" and x["n"] >= 10 for x in q)
    assert {x["teste"] for x in q} == {"whatsapp", "tor", "webconnectivity"}
    assert len({x["asn"] for x in q}) == 1                                  # o segundo ASN tem 4 medições (abaixo do mínimo) e o estrangeiro não é do snapshot
    asn = q[0]["asn"]
    b = api.get(f"/api/v1/asns/{asn}/bloqueios", headers=ALLOWED).json()
    assert b["licenca"] == "CC BY-NC-SA 4.0" and "OONI" in b["fonte"]["atribuicao"] and "não é o veredito do backend" in b["aviso"] and b["limites"] and b["janela"]["inicio"]
    por = {t["teste"]: t for t in b["testes"]}
    assert por["whatsapp"]["n"] == 30 and por["whatsapp"]["anomalias"] == 6 and por["webconnectivity"]["amostra"] is True and por["tor"]["alvos_acessiveis_pct"]["obfs4"] == 23.81
    assert "whatsapp" not in b                                              # um teste como chave seria tomado por chave de contato pelo filtro de privacidade
    perfil = api.get(f"/api/v1/asns/{asn}", params={"include": "bloqueios"}, headers=ALLOWED).json()
    assert perfil["bloqueios"]["testes"] == b["testes"] and "bloqueios" not in api.get(f"/api/v1/asns/{asn}", headers=ALLOWED).json()
    assert api.get("/api/v1/asns/99999999/bloqueios", headers=ALLOWED).status_code == 404
    txt = str(b)
    assert not any(k in txt for k in ("report_id", "probe_ip", "127.0.0.1", "resolver"))


def test_empresas_cadastro_mercado_e_operadora(api):
    """Cadastro das empresas de telecom (Receita × SICI), sem contato nem endereço, com erros claros."""
    m = api.get("/api/v1/empresas/mercado", headers=ALLOWED)
    assert m.status_code == 200
    j = m.json()
    assert j["natureza"] == "fato_cadastral" and "não prova" in j["limites"] and j["entradas_por_ano"] and j["ativas_por_uf"]
    uf = next(iter(j["ativas_por_uf"]))
    ju = api.get("/api/v1/empresas/mercado", params={"uf": uf.lower()}, headers=ALLOWED).json()
    assert ju["uf"] == uf and ju["ativas"] == j["ativas_por_uf"][uf] and all(set(e) == {"ano", "total"} for e in ju["entradas_por_ano"])
    assert api.get("/api/v1/empresas/mercado", params={"uf": "XX"}, headers=ALLOWED).status_code == 404
    scms = api.get("/api/v1/scms", params={"limit": 1}, headers=ALLOWED).json()["items"]
    cnpj = scms[0]["cnpj"]
    r = api.get(f"/api/v1/empresas/operadoras/{cnpj}", headers=ALLOWED)
    assert r.status_code == 200
    d = r.json()
    assert d["raiz"] == cnpj[:8] and d["matriz"]["ibge"] == "3205309" and d["estabelecimentos"]["total"] >= 2 and d["presenca"]
    assert api.get(f"/api/v1/empresas/operadoras/{cnpj[:8]}", headers=ALLOWED).json()["raiz"] == d["raiz"]            # a raiz também serve
    formatado = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    assert api.get("/api/v1/empresas/operadoras/" + formatado.replace("/", "%2F"), headers=ALLOWED).status_code in (200, 404)
    assert api.get("/api/v1/empresas/operadoras/123", headers=ALLOWED).status_code == 400
    assert api.get("/api/v1/empresas/operadoras/00000000000000", headers=ALLOWED).status_code == 404
    assert not ({"email", "telefone", "logradouro", "cep", "bairro"} & _keys(d))                                         # sem contato nem endereço
    assert not ({"email", "telefone", "logradouro", "cep", "bairro"} & _keys(j))


def test_contratos_publicos_por_operadora_municipio_e_resumo(api):
    """Ausência não é zero (404 sem leitura, 200 lida sem resultado), licença não verificada declarada, sem pessoa física e sem ranking de fornecedor."""
    ctx = discover(api)
    j = api.get(f"/api/v1/contratos/operadoras/{ctx['cnpj_contratos']}", headers=ALLOWED).json()
    assert j["resultado"] == "com_resultado" and j["itens_cancelados"] == 1 and j["licenca"].startswith("dados abertos (Lei 12.527/2011") and "não é, por si" in j["aviso"] and j["cobertura"]["raizes_sem_leitura"] > 0
    assert api.get(f"/api/v1/contratos/operadoras/{ctx['cnpj_contratos'][:8]}", headers=ALLOWED).json()["raiz"] == j["raiz"]
    scms = api.get("/api/v1/scms", params={"limit": 100}, headers=ALLOWED).json()["items"]
    respostas = {x["cnpj"]: api.get(f"/api/v1/contratos/operadoras/{x['cnpj']}", headers=ALLOWED) for x in scms}
    assert {r.status_code for r in respostas.values()} == {200, 404}                                                     # lidas (com ou sem resultado) e ainda sem leitura
    vazia = next(r for r in respostas.values() if r.status_code == 200 and r.json()["resultado"] != "com_resultado").json()
    assert vazia["resultado"] == "sem_resultado_na_consulta" and vazia["itens"] == 0 and vazia["lida_em"]
    nao_lida = next(c for c, r in respostas.items() if r.status_code == 404)
    assert "ainda sem leitura" in respostas[nao_lida].json()["detail"] and api.get(f"/api/v1/contratos/operadoras/{nao_lida}", params={"opcional": 1}, headers=ALLOWED).status_code == 204
    assert api.get("/api/v1/contratos/operadoras/123", headers=ALLOWED).status_code == 400
    m = api.get("/api/v1/contratos/municipios/9900001", headers=ALLOWED).json()
    assert m["contratacoes"] == 2 and "órgão comprador" in m["criterio_municipio"] and m["fornecedores"][0]["itens"] == 2
    assert api.get("/api/v1/contratos/municipios/9900012", headers=ALLOWED).status_code == 404 and api.get("/api/v1/contratos/municipios/12", headers=ALLOWED).status_code == 400
    r = api.get("/api/v1/contratos/resumo", headers=ALLOWED).json()
    assert r["valor_homologado"] == 256277.25 and {x["esfera"] for x in r["por_esfera"]} == {"federal", "municipal", "nao_detalhada"}
    assert api.get("/api/v1/contratos/resumo", params={"uf": "sp"}, headers=ALLOWED).json()["uf"] == "SP" and api.get("/api/v1/contratos/resumo", params={"uf": "XX"}, headers=ALLOWED).status_code == 404
    assert not ({"cpf", "email", "telefone", "logradouro", "representante", "servidor"} & (_keys(j) | _keys(m)))
    assert "ranking" not in json.dumps(r).lower()


def test_comparacao_de_ixps_recusa_codigo_com_traversal(api):
    """Travessia de caminho (variante REST): `ixps=ext:<código>` com `..` ou `/` dá 400, não vaza a existência de arquivos nem 500."""
    for ruim in ("ext:../../../raw/x", "ixbr:../x", "ext:a/b", "ext:A", "ext:a.b"):
        r = api.get("/api/v1/ixp-compare/members", params={"ixps": f"ixbr:sp,{ruim}"}, headers=ALLOWED)
        assert r.status_code == 400, (ruim, r.status_code)


def test_comparacao_de_ixps_diz_quais_asns_tem_pagina(api, ctx):
    """O cadastro do IX.br traz ASNs sem documento no snapshot (privados, como o AS65000, ou sem registro no RIR); o link para
    `/asn/{asn}` dava 404. `has_detail` diz se a página existe."""
    r = api.get("/api/v1/ixp-compare/members", params={"ixps": ctx["codes"]}, headers=ALLOWED)
    assert r.status_code == 200
    ps = r.json()["participants"]
    assert ps and all(isinstance(p["has_detail"], bool) for p in ps)
    for p in ps[:5] + [p for p in ps if not p["has_detail"]][:5]:
        doc = api.get(f"/api/v1/asns/{p['asn']}", headers=ALLOWED)
        assert (doc.status_code == 200) == p["has_detail"], (p["asn"], doc.status_code)


def test_rotas_da_fase6_com_identificador_hostil_nao_dao_5xx(api):
    """Travessia de caminho nas rotas de grupo e de mudanças: `grupo_id` é chave de busca e `?ixp=` de `/changes` é filtro por igualdade; nenhum vira caminho."""
    for ruim in ("..%2f..%2fraw", "grp_..", "a\\b", "x" * 80):
        r = api.get(f"/api/v1/grupos/{ruim}", params={"include": "mercado,regulatorio,tecnico,relacoes"}, headers=ALLOWED)
        assert r.status_code in (404, 422), (ruim, r.status_code)
    for ruim in ("../../raw/x", "/etc/passwd", "a\\b"):
        r = api.get("/api/v1/changes", params={"ixp": ruim}, headers=ALLOWED)
        assert r.status_code < 500 and "@" not in r.text, (ruim, r.status_code)


def test_detalhe_de_snapshot_com_data_fora_do_formato_e_404(api):
    """A data vira nome de pasta; o fuzz (Starlette 1.10) achou um 500 com 300 bytes ("File name too long"). Fora de AAAA-MM-DD é 404."""
    for ruim in ("0" * 27 + "\u0080" * 60, "..", "2026-1-1", "x" * 300):
        r = api.get(f"/api/v1/snapshots/{ruim}", headers=ALLOWED)
        assert r.status_code == 404, (ruim[:20], r.status_code)


def test_geo_org_do_prefixo_so_tem_campos_permitidos(api, ctx):
    """`/prefixes/{prefix}` copiava o `geo_org` inteiro (telefone, logradouro, CEP, coordenadas)."""
    from api.privacidade import GEO_ORG_PUBLICO
    r = _call(api, "GET /api/v1/prefixes/{prefix}", ctx, ANON)
    assert r.status_code == 200, r.status_code
    g = r.json().get("geo_org")
    assert g, "o sintético deveria ter geo_org para o prefixo do contrato"
    assert set(g) <= GEO_ORG_PUBLICO, sorted(set(g) - GEO_ORG_PUBLICO)


def test_resposta_de_classe_login_nao_vai_para_cache_publico(api, pipeline):
    """lista expandida e histórico só chegam a quem tem login ou allowlist; com `public`/`immutable`
    o cache do nginx (chave sem identidade) os entregaria a anônimos se o gate falhasse aberto."""
    from tests.synth.world import T0, T1
    datas = api.get("/api/v1/snapshots", headers=ALLOWED).json()
    assert {T0, T1} <= {s["date"] if isinstance(s, dict) else s for s in (datas.get("snapshots") if isinstance(datas, dict) else datas)}
    for url, params in (("/api/v1/asns", {"limit": "1000"}), ("/api/v1/asns", {"page": "2"}), ("/api/v1/asns", {"limit": "1000", "date": T1})):
        r = api.get(url, params=params, headers=ALLOWED)
        assert r.status_code == 200, (url, params, r.status_code)
        assert r.headers.get("cache-control") == "private, no-store", (url, params, r.headers.get("cache-control"))
    r = api.get("/api/v1/asns", params={"limit": "50", "date": T1}, headers=ALLOWED)      # prévia de data publicada: continua imutável
    assert "immutable" in r.headers.get("cache-control", ""), r.headers.get("cache-control")


def test_query_larga_ou_corpo_grande_nao_chega_a_executar(api):
    """1.000 predicados davam 75 s de CPU; corpo acima de 64 KB nem é lido."""
    import time
    corpo = {"filter": {"or": [{"field": "name", "op": "contains", "value": f"x{i}"} for i in range(1000)]}}
    t = time.perf_counter()
    r = api.post("/api/v1/query/asns", json=corpo, headers=ALLOWED)
    assert r.status_code == 400 and "predicados" in r.text and time.perf_counter() - t < 2
    grande = {"filter": {"field": "name", "op": "contains", "value": "x" * 70_000}}
    assert api.post("/api/v1/query/asns", json=grande, headers=ALLOWED).status_code == 413


def test_s11_corpo_do_query_tem_a_previa_do_site_para_anonimo(api):
    """`limit`/`page` no corpo e o histórico escapavam do `classify` (que só vê a query string)."""
    for corpo in ({"limit": 1000}, {"page": 2}, {"limit": 100, "page": 3}):
        r = api.post("/api/v1/query/asns", json=corpo, headers=ANON)
        assert r.status_code == 401 and r.json()["login_required"] is True and r.headers["x-login-required"] == "true", (corpo, r.status_code)
    assert api.post("/api/v1/query/eventos", json={"limit": 10}, headers=ANON).status_code == 401
    r = api.post("/api/v1/query/asns", json={"limit": 10}, headers=ANON)                 # prévia: passa
    assert r.status_code == 200 and len(r.json()["items"]) <= 10
    assert api.post("/api/v1/query/asns", json={"limit": 1000, "page": 2}, headers=ALLOWED).status_code == 200    # allowlist: sem prévia


def test_brasil_indicadores_e_aberto_e_soma_o_apnic_dos_asns_br(api):
    """Agregados do país para a home (página de entrada, rota aberta)."""
    r = api.get("/api/v1/brasil/indicadores", headers=ANON)
    assert r.status_code == 200
    v = r.json()["ipv6"]
    store = api.app.state.store
    br = [a for a in store.asn_index(store.latest()) if a.get("is_br") and (a.get("apnic_users") or 0) > 0]
    assert v["usuarios"] == sum(a["apnic_users"] for a in br)
    assert v["usuarios_ipv6"] == sum(a.get("apnic_v6_users") or 0 for a in br)
    if v["usuarios"]:
        assert v["pct_usuarios_ipv6"] == round(100 * v["usuarios_ipv6"] / v["usuarios"], 1)
    assert "APNIC" in v["fonte"] and v["nota"]


def test_rota_medida_nao_fica_na_borda_exceto_mapas_e_agregados(api, ctx):
    """A borda (Cloudflare) não passa pelo gate: o que ela guarda vai para quem esgotou o orçamento. Rota `metered` sai com
    `Cloudflare-CDN-Cache-Control: no-store`, salvo as camadas de mapa e agregados da lista `_BORDA_PATTERNS`; rota aberta não leva o
    cabeçalho. Nenhuma resposta 200 carrega `X-Anon-Limit-Reached` (só o 403 do limite), para não ir parar em cache público."""
    d = ctx["date"]
    entidade = api.get(f"/api/v1/asns/{ctx['asn']}", params={"date": d})
    assert entidade.status_code == 200
    assert entidade.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert entidade.headers.get("cloudflare-cdn-cache-control") == "no-store"
    assert "x-anon-limit-reached" not in entidade.headers
    mapa = api.get("/api/v1/map/pix", params={"date": d})
    assert mapa.status_code == 200 and "cloudflare-cdn-cache-control" not in mapa.headers
    aberta = api.get("/api/v1/ixps", params={"date": d})
    assert aberta.status_code == 200 and "cloudflare-cdn-cache-control" not in aberta.headers
    from api.auth import access_policy as ap
    assert ap.cache_na_borda("/api/v1/bgp-stability/history") and ap.cache_na_borda("/ixps/sp/geo")
    assert not any(ap.cache_na_borda(p) for p in ("/api/v1/asns/1", "/api/v1/ixps/sp", "/api/v1/grupos/g", "/api/v1/query/asns"))


def test_consulta_por_get_e_a_mesma_do_post_e_cacheavel(api):
    """`GET /query/{coleção}?corpo=`: o mesmo motor e as mesmas regras do POST, mas cacheável (as perguntas da página inicial)."""
    data = api.get("/health").json()["latest_snapshot"]
    corpo = {"select": ["asn", "name"], "sort": [{"field": "asn", "dir": "asc"}], "limit": 3}
    p = api.post("/api/v1/query/asns", params={"date": data}, json=corpo, headers=ANON)
    g = api.get("/api/v1/query/asns", params={"date": data, "corpo": json.dumps(corpo)}, headers=ANON)
    assert p.status_code == g.status_code == 200 and p.json() == g.json()
    assert g.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert api.get("/api/v1/query/asns", params={"corpo": "{nao json"}, headers=ANON).status_code == 400
    assert api.get("/api/v1/query/asns", params={"corpo": "[1, 2]"}, headers=ANON).status_code == 400


def test_consulta_por_get_alem_da_previa_nao_depende_de_quem_pede(api):
    """Lista além da prévia por GET: 401 ao anônimo e `private, no-store` a quem tem acesso (o nginx guarda por URL)."""
    params = {"corpo": json.dumps({"select": ["asn"], "limit": 150})}
    negado = api.get("/api/v1/query/asns", params=params, headers=ANON)
    assert negado.status_code == 401 and negado.json().get("login_required") is True
    r = api.get("/api/v1/query/asns", params=params, headers=ALLOWED)
    assert r.status_code == 200 and r.headers["cache-control"] == "private, no-store"
