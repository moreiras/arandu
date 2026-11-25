# SPDX-License-Identifier: AGPL-3.0-or-later
"""Política de acesso (api/auth/access_policy.py)."""
import json
import re
from pathlib import Path

import pytest

from api.auth.access_policy import LOGIN, METERED, OPEN, PREVIEW_LIMIT, classify

RECENT = ["2026-10-04", "2026-09-27"]


def c(path, q=None, method="GET", recent=RECENT):
    return classify(method, path, q or {}, recent).cls


@pytest.mark.parametrize("path", [
    "/api/v1/brasil/snapshots", "/api/v1/brasil/snapshots/2026-10-04", "/api/v1/brasil/destaques", "/api/v1/cdns/presence", "/api/v1/prontidao/resumo",
    "/api/v1/rpki/summary", "/api/v1/ixps", "/api/v1/ixps/estimated-users",
    "/api/v1/hilbert/v4", "/api/v1/hilbert/v6", "/api/v1/hilbert/v4/detail",
    "/api/v1/ixps/sp/hilbert/v4/detail", "/api/v1/scms/stats", "/api/v1/map/scms",
    "/api/v1/grupos", "/api/v1/grupos/123/prefixos-geo", "/api/v1/bgp-stability/summary",
    "/api/v1/acessos/municipios", "/api/v1/acessos/municipio/3550308",
    "/api/v1/map/asns-overview", "/api/v1/external-ixps", "/api/v1/asns/ix-presence",
])
def test_entrada_aberta(path):
    assert c(path, {"date": "2026-10-04"}) == OPEN


@pytest.mark.parametrize("path", [
    "/api/v1/map/asns", "/api/v1/map/prefixes", "/api/v1/map/pix", "/api/v1/ixps/sp",
    "/api/v1/ixps/sp/members", "/api/v1/ixps/sp/peers", "/api/v1/asns/3356",
    "/api/v1/asns/3356/paths", "/api/v1/prefixes/200.160.0.0/20",
    "/api/v1/ixp-compare/members", "/api/v1/bgp-stability-deep",
    "/api/v1/bgp-stability",
    "/api/v1/resolve/place", "/api/v1/analytics/ixps/sp/nearby", "/api/v1/scms/12345678000190",
])
def test_avancada_medida(path):
    assert c(path, {"date": "2026-10-04"}) == METERED


def test_post_de_consulta_e_medido():
    assert c("/api/v1/map/query", method="POST") == METERED
    assert c("/api/v1/query/asns", method="POST") == METERED


def test_get_de_consulta_classifica_pelo_corpo():
    """`GET /query/{coleção}?corpo=` vai para o cache do nginx e da API (chave = URL): o que o corpo pede além da prévia é `login`
    para a URL inteira, senão a resposta completa de quem tem login seria entregue a anônimos."""
    def c(corpo, colecao="operadoras", date=None):
        q = {"corpo": json.dumps(corpo)} | ({"date": date} if date else {})
        return classify("GET", f"/api/v1/query/{colecao}", q, ["2026-11-08", "2026-11-15"]).cls
    assert c({"select": ["empresa"], "limit": 5}) == METERED
    assert c({"limit": PREVIEW_LIMIT}) == METERED
    assert c({"limit": PREVIEW_LIMIT + 1}) == LOGIN
    assert c({"page": 2}) == LOGIN and c({"offset": 10}) == LOGIN
    assert c({"limit": True}) == METERED                                       # booleano não é número
    assert c({"limit": 1, "de": "2026-11-15"}, "eventos") == METERED            # histórico a partir de um snapshot atual
    assert c({"limit": 1}, "eventos") == LOGIN                                   # sem início: a série inteira
    assert c({"limit": 1}, "eventos", "2026-11-15") == LOGIN                     # EXP-E4: `date` não restringe as linhas, então não conta como início
    assert c({"limit": 1}, "series_asn", "2026-11-15") == LOGIN
    assert c({"limit": 1, "de": "2026-10-01"}, "eventos", "2026-11-15") == LOGIN
    assert classify("GET", "/api/v1/query/operadoras", {"corpo": "não é json"}, None).cls == METERED   # a rota responde 400
    assert c({"limit": 5}, date="2026-10-04") == LOGIN                          # snapshot antigo, como nas outras rotas


@pytest.mark.parametrize("path", [
    "/api/v1/asns/3356/contacts", "/api/v1/acessos/operadora/123/contacts",
    "/api/v1/acessos-movel/operadora/123/contacts",
])
def test_contatos_exigem_login(path):
    assert c(path) == LOGIN


@pytest.mark.parametrize("path", ["/api/v1/asns/3356", "/api/v1/ixps/sp", "/api/v1/operadoras/02558157000162", "/api/v1/ufs/SP"])
def test_serie_historica_inteira_no_perfil_exige_login(path):
    assert c(path, {"include": "paths, historico_completo", "date": RECENT[0]}) == LOGIN
    assert c(path, {"include": "paths,historico", "date": RECENT[0]}) != LOGIN


@pytest.mark.parametrize("path", ["/api/v1/asns", "/api/v1/scms", "/api/v1/smps", "/api/v1/stfcs", "/api/v1/seacs"])
def test_listas_primeira_pagina_aberta_e_alem_exige_login(path):
    assert c(path, {"date": "2026-10-04"}) == OPEN
    assert c(path, {"date": "2026-10-04", "page": "1", "limit": str(PREVIEW_LIMIT)}) == OPEN
    assert c(path, {"page": "2"}) == LOGIN
    assert c(path, {"limit": str(PREVIEW_LIMIT + 1)}) == LOGIN
    assert c(path, {"limit": "1000"}) == LOGIN


def test_tabela_de_participantes_do_ptt_previa_medida_e_ampliar_exige_login():
    path = "/api/v1/ixps/sp/participantes"
    assert c(path, {"date": RECENT[0]}) == METERED
    assert c(path, {"limit": str(PREVIEW_LIMIT)}) == METERED
    assert c(path, {"page": "2"}) == LOGIN
    assert c(path, {"limit": str(PREVIEW_LIMIT + 1)}) == LOGIN


@pytest.mark.parametrize("path", ["/api/v1/asns", "/api/v1/scms", "/api/v1/acessos/divergencias"])
@pytest.mark.parametrize("campo,valor", [("limit", "1000.0"), ("limit", "1e3"), ("limit", " 1000"), ("limit", "-1"), ("limit", ""),
                                         ("page", "2.0"), ("page", "+2"), ("page", "0x2")])
def test_limit_e_page_fora_do_formato_inteiro_exigem_login(path, campo, valor):
    """`limit=1000.0` era lido como o padrão (prévia aberta) e o FastAPI entregava 1000 linhas."""
    assert c(path, {campo: valor}) == LOGIN


def test_divergencias_previa_medida_e_ampliar_exige_login():
    for path in ("/api/v1/acessos/divergencias", "/api/v1/acessos/divergencias/scm"):
        assert c(path, {"limit": "20"}) == METERED
        assert c(path, {"limit": "1000"}) == LOGIN


def test_lote_de_asns_e_medido_mas_a_lista_comum_continua_aberta():
    """`/asns?asns=` devolve documentos completos (avançados em /asns/{asn}); não pode ser a brecha da prévia aberta."""
    assert c("/api/v1/asns", {"asns": "1916,28573"}) == METERED
    assert c("/api/v1/asns", {"br_only": "true", "limit": "100", "include": "bgp_stability"}) == OPEN


@pytest.mark.parametrize("novo,antigo", [
    ("/api/v1/acessos/stats", "/api/v1/acessos-movel/stats"),
    ("/api/v1/acessos/operadoras", "/api/v1/acessos-movel/operadoras"),
    ("/api/v1/acessos/operadora/12345678000190", "/api/v1/acessos-movel/operadora/12345678000190"),
    ("/api/v1/acessos/operadora/12345678000190/contacts", "/api/v1/acessos-movel/operadora/12345678000190/contacts"),
    ("/api/v1/acessos/municipios", "/api/v1/acessos-movel/municipios"),
    ("/api/v1/acessos/municipio/3550308", "/api/v1/acessos-movel/municipio/3550308"),
])
def test_acessos_com_servico_movel_tem_a_classe_do_alias_movel(novo, antigo):
    """A aba SMP de /operadoras (página de entrada) chama o contrato novo; ele não pode ficar mais restrito que o antigo."""
    assert c(novo, {"servico": "movel"}) == c(antigo)
    assert c(novo) == c(novo, {"servico": "fixa"})


def test_busca_de_autocomplete_aberta():
    assert c("/api/v1/asns", {"q": "claro", "limit": "8", "date": "2026-10-04"}) == OPEN


def test_historico_exige_login_mas_os_dois_ultimos_nao():
    assert c("/api/v1/ixps", {"date": "2026-10-04"}) == OPEN
    assert c("/api/v1/ixps", {"date": "2026-09-27"}) == OPEN
    assert c("/api/v1/ixps", {"date": "2026-08-01"}) == LOGIN
    assert c("/api/v1/map/asns", {"date": "2026-08-01"}) == LOGIN
    assert c("/api/v1/brasil/snapshots/2026-10-04") == OPEN
    assert c("/api/v1/brasil/snapshots/2026-08-01") == LOGIN
    assert c("/api/v1/snapshots/2026-10-04") == LOGIN            # D9: o resumo pela rota antiga é `login` mesmo para a data atual
    assert c("/api/v1/snapshots/2026-08-01") == LOGIN


def test_series_e_eventos_do_historico_so_nos_dois_snapshots_atuais(
):
    for rota in ("/api/v1/history/asns/28571", "/api/v1/history/ixps/sp", "/api/v1/history/operadoras/1", "/api/v1/history/uf/SP", "/api/v1/changes"):
        assert c(rota) == LOGIN, rota                                           # sem `from`: série inteira
        assert c(rota, {"from": "2026-08-01"}) == LOGIN, rota                    # começa antes dos atuais
        assert c(rota, {"from": "2026-09-27"}) == METERED, rota                  # começa num snapshot atual: avançada, medida
        assert c(rota, {"from": "2026-10-04"}) == METERED, rota
        assert c(rota, recent=None) == METERED, rota                             # sem lista de datas, conservador
    # o resumo das mudanças (contagens da janela atual, sem linhas) é entrada; fora da janela, a série inteira, `login`
    assert c("/api/v1/changes/summary") == LOGIN and c("/api/v1/changes/summary", {"from": "2026-08-01"}) == LOGIN
    assert c("/api/v1/changes/summary", {"from": "2026-09-27"}) == OPEN and c("/api/v1/changes/summary", {"from": "2026-10-04"}) == OPEN
    assert c("/api/v1/changes/summary", recent=None) == METERED
    assert c("/api/v1/snapshots/diff", {"a": "2026-09-27", "b": "2026-10-04"}) == METERED
    assert c("/api/v1/snapshots/diff", {"a": "2026-08-01", "b": "2026-10-04"}) == LOGIN
    assert c("/api/v1/snapshots/diff") == LOGIN
    assert c("/api/v1/cdns/mudancas", {"a": "2026-09-27", "b": "2026-10-04"}) == METERED
    assert c("/api/v1/cdns/mudancas", {"a": "2026-08-01", "b": "2026-10-04"}) == LOGIN
    assert c("/api/v1/cdns/mudancas") == LOGIN


def test_historico_nao_se_aplica_sem_lista_de_datas():
    assert c("/api/v1/ixps", {"date": "2020-01-01"}, recent=None) == OPEN


def test_lista_de_snapshots_nunca_e_historico():
    assert c("/api/v1/brasil/snapshots", {"date": "2020-01-01"}) == OPEN


def test_rota_desconhecida_e_medida_nunca_aberta():
    assert c("/api/v1/algo-novo") == METERED


def test_fora_da_api_e_aberta():
    assert c("/health") == OPEN
    assert c("/") == OPEN


def test_toda_rota_do_openapi_tem_classe_explicita(app_client):
    """Rota nova em /api/v1 precisa ser decidida: aberta, paginada ou login — ou
    declarada aqui como medida de propósito (lista abaixo)."""
    from api.auth import access_policy as ap

    _, app, _ = app_client
    rotas = sorted({
        r.path for r in app.routes
        if hasattr(r, "methods") and r.path.startswith("/api/v1/") and "GET" in r.methods
    }) 
    rotas = [p for p in rotas if p not in ("/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json")]
    declaradas_medidas = set(json.loads((Path(__file__).parent / "access_metered_routes.json").read_text()))
    sem_decisao = []
    for p in rotas:
        rel = p[len("/api/v1"):]
        explicita = (
            any(rx.match(rel) for rx in ap._OPEN)
            or any(rx.match(rel) for rx in ap._PAGED)
            or any(rx.match(rel) for rx in ap._PAGED_METERED)
            or any(rx.match(rel) for rx in ap._LOGIN)
        )
        if not explicita and p not in declaradas_medidas:
            sem_decisao.append(p)
    assert not sem_decisao, f"Rotas sem classe explícita (adicione a access_policy ou a tests/access_metered_routes.json): {sem_decisao}"


def test_paginas_de_entrada_usam_so_endpoints_abertos():
    """Golden das chamadas de API das páginas de entrada (gerado do frontend)."""
    entry = json.loads((Path(__file__).parent / "access_entry_calls.json").read_text())
    ruins = []
    for page, urls in entry["paginas"].items():
        for u in urls:
            if not u.startswith("/api/v1/"):
                continue
            path = u.replace("${date}", RECENT[0])
            path = re.sub(r"\$\{[^}]+\}", "X", path)
            path, _, qs = path.partition("?")            # a entrada pode trazer parâmetros que mudam a classe (ex.: ?servico=movel)
            query = {"date": RECENT[0], **dict(kv.split("=", 1) for kv in qs.split("&") if "=" in kv)}
            if classify("GET", path, query, RECENT).cls != OPEN:
                ruins.append((page, u))
    assert not ruins, f"Página de entrada chama endpoint não aberto: {ruins}"


def test_chamadas_degradaveis_das_paginas_de_entrada_sao_medidas():
    """Mapas/popups opcionais de páginas abertas: bloqueiam só o bloco, com aviso na página."""
    entry = json.loads((Path(__file__).parent / "access_entry_calls.json").read_text())
    for page, urls in entry["degradaveis"].items():
        for u in urls:
            path = re.sub(r"\$\{[^}]+\}", "X", u)
            assert classify("GET", path, {"date": RECENT[0]}, RECENT).cls == METERED, (page, u)


# ── PT-12 / D9 ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", ["/api/v1/snapshots", "/api/v1/snapshots/2026-10-04", "/api/v1/snapshots/2026-08-01"])
def test_snapshots_da_api_sao_login_e_a_entrada_usa_brasil_snapshots(path):
    """TRANSV-E19: `/snapshots` era `open` na API e `login` no SPA. Agora a lista inteira e o resumo de qualquer data exigem login; a entrada usa
    `/brasil/snapshots`, aberta, que só lista as datas atuais."""
    assert c(path) == LOGIN
    assert c(path, recent=None) == LOGIN


def test_brasil_snapshots_lista_aberta_e_data_antiga_exige_login():
    assert c("/api/v1/brasil/snapshots") == OPEN
    assert c("/api/v1/brasil/snapshots/" + RECENT[0]) == OPEN and c("/api/v1/brasil/snapshots/" + RECENT[1]) == OPEN
    assert c("/api/v1/brasil/snapshots/2026-08-01") == LOGIN
    assert c("/api/v1/brasil/snapshots/2026-08-01", recent=None) == OPEN        # sem lista de datas a regra de histórico não se aplica


def test_snapshots_diff_segue_a_regra_de_historico_e_nao_a_de_snapshots_login():
    assert c("/api/v1/snapshots/diff", {"a": RECENT[1], "b": RECENT[0]}) == METERED


@pytest.mark.parametrize("path", ["/api/v1/external-ixps/decix-rj", "/api/v1/external-ixps/amsix"])
def test_ptt_externo_e_medido_e_a_lista_continua_aberta(path):
    """PT-12b (revisão da D9, 2026-11-25): o detalhe do PTT externo não exige login; é `metered`, como antes do PT-12."""
    assert c(path, {"date": RECENT[0]}) == METERED
    assert c("/api/v1/external-ixps", {"date": RECENT[0]}) == OPEN


def test_comparador_com_ptt_externo_segue_a_classe_do_ptt_externo():
    assert c("/api/v1/ixp-compare/members", {"ixps": "ixbr:sp,ext:decix-rj"}) == METERED
    assert c("/api/v1/ixp-compare/members", {"ixps": "ext:amsix, ext:decix-rj"}) == METERED
    assert c("/api/v1/ixp-compare/members", {"ixps": "ixbr:sp,ixbr:rj"}) == METERED


@pytest.mark.parametrize("path", ["/api/v1/cdns/presence", "/api/v1/prontidao/resumo", "/api/v1/rpki/summary", "/api/v1/brasil/destaques"])
def test_rotas_de_entrada_do_panorama_e_da_home_sao_abertas(path):
    """TRANSV-E20: abrir a Home, o panorama e /snapshots consumia orçamento `metered`."""
    assert c(path, {"date": RECENT[0]}) == OPEN


def test_query_generico_segue_medido_e_nao_virou_entrada():
    assert c("/api/v1/query/operadoras", {"corpo": json.dumps({"limit": 1})}) == METERED
    assert c("/api/v1/acessos/divergencias", {"limit": "1"}) == METERED


def test_eventos_sem_de_nao_alcancam_o_historico_para_anonimo():
    """EXP-E4: o portão aceitava `date` como início, mas o motor ignorava e devolvia todas as datas. Só `de` vale, e o motor o aplica."""
    def q(corpo, colecao="eventos", date=RECENT[0]):
        return classify("GET", f"/api/v1/query/{colecao}", {"corpo": json.dumps(corpo), "date": date}, RECENT).cls
    for colecao in ("eventos", "series_asn"):
        assert q({"limit": 5}, colecao) == LOGIN
        assert q({"limit": 5, "de": "2026-01-01"}, colecao) == LOGIN
        assert q({"limit": 5, "de": RECENT[1]}, colecao) == METERED
        assert q({"limit": 5, "de": RECENT[0]}, colecao) == METERED


def test_datas_atuais_sao_as_mesmas_da_rota_e_da_regra():
    from api.auth import access_policy as ap
    assert ap.N_DATAS_ATUAIS == 2


def test_municipios_do_grupo_previa_medida_e_ampliar_exige_login():
    path = "/api/v1/grupos/grp_09132659/municipios"
    assert c(path, {"date": RECENT[0]}) == METERED
    assert c(path, {"limit": str(PREVIEW_LIMIT)}) == METERED
    assert c(path, {"page": "2"}) == LOGIN
    assert c(path, {"limit": str(PREVIEW_LIMIT + 1)}) == LOGIN
