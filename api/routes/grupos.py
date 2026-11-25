# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoints de grupos societários — GET /grupos e GET /grupos/empresa/{cnpj}.

Serve o cruzamento de quadro societário (Receita Federal, sources.socios_grupos.enrich)
para a página "Grupos de Empresas" e para as seções "Empresas relacionadas"
das páginas de Operadora e ASN.
"""
from __future__ import annotations

import re
from typing import Optional

from collections import OrderedDict
from threading import Lock

from fastapi import APIRouter, HTTPException, Query, Request

from api.store import Store
from api.services import grupo_mercado as gm

router = APIRouter()

_CNPJ_RE = re.compile(r"\D")


def _clean_cnpj(raw: str) -> str:
    return _CNPJ_RE.sub("", raw or "")


@router.get(
    "/grupos",
    summary="Grupos societários (cruzamento de quadro societário via Receita Federal)",
    description="""
Uma linha por grupo societário (`grupo_id`, estável: `grp_` + o menor CNPJ básico do conjunto): `nome` do grupo com a regra que o escolheu
(`nome_regra`: marca curada, senão o CNPJ com mais acessos fixos declarados ao SICI), CNPJs membros, classificação
(`total` — toda relação interna é quadro idêntico/controle exclusivo;
`parcial` — toda relação é sócio em comum/controle não exclusivo; `misto` —
tem as duas; `individual` — empresa sem relação societária com nenhuma outra
da base, listada como "grupo de uma empresa só", `grupo_id` = `ind_{cnpj básico}`),
total de assinantes (acessos fixos declarados ao SICI/SCM — não
inclui móvel) e a distribuição municipal agregada desses acessos. Cada CNPJ
traz os ASNs registrados com o mesmo CNPJ (`asns`) e as flags de outorga Anatel.
O grupo traz `asns`: os do mesmo CNPJ de uma das empresas mais os de outro CNPJ
da mesma raiz de 8 dígitos (filial que não declara; vínculo `raiz`, inferido,
listados à parte em `asns_raiz`). `usuarios_apnic` soma cada ASN uma vez;
`visibilidade_bgp` = algum desses ASes origina ao menos um bloco IPv6/IPv4 na
tabela BGP global.

Alimenta a página "Grupos de Empresas" (scatter + mapa + tabela) num único
payload — evita round-trip por interação do usuário.
""",
)
def list_grupos(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    grupos = store.grupos_societarios_overview(date_str)
    individuais = sum(1 for g in grupos if g["classificacao"] == "individual")
    return {
        "snapshot_date": date_str,
        "total": len(grupos),
        "total_grupos": len(grupos) - individuais,
        "total_individuais": individuais,
        "grupos": grupos,
    }


_IDX: dict[str, dict] = {}


def _mercado(store: Store, date_str: str, g: dict) -> Optional[dict]:
    """Bloco de mercado do grupo; o índice (acessos mensais por unidade e posições) é calculado uma vez por snapshot."""
    dados = store._load_sici(date_str)
    if not dados:
        return None
    if date_str not in _IDX:
        if len(_IDX) >= 2:
            _IDX.pop(next(iter(_IDX)))
        _IDX[date_str] = gm.indice(dados, store.grupos_societarios_overview(date_str))
    return gm.mercado_do_grupo(g, _IDX[date_str], dados, store.mercado_grupos(date_str))


def _soma(valores) -> float:
    return sum(v for v in valores if isinstance(v, (int, float)))


@router.get(
    "/grupos/{grupo_id}",
    summary="Um grupo societário consolidado (composição, mercado, rede, crédito, sanções e contratos)",
    description="""
Página de grupo: composição (CNPJs com serviços e ASNs, classificação da correspondência), mercado consolidado (acessos fixos declarados ao SICI, usuários APNIC,
municípios), rede (ASNs) e as somas de crédito público (BNDES), sanções (CEIS/CNEP) e contratos públicos (PNCP) **das empresas do grupo**.

**Só estrutura entre empresas (PJ):** a resposta não traz sócio pessoa física, nome de sócio nem CPF. Cada soma vem com a contagem de empresas que têm o dado: ausência não é zero
(o crédito cobre só operações diretas do BNDES; as sanções, a data do arquivo da CGU; os contratos, o rodízio de leitura do PNCP). `grupo_id` é o de `GET /grupos`
(`ind_<cnpj básico>` para empresa individual). Só sócio com participação societária liga empresas (administrador, diretor e presidente sem participação não ligam).
Sociedade anônima (natureza 2046 e 2054 da Receita): o quadro traz diretoria e conselho, não acionistas, e não liga empresas; a resposta traz `grupo_inferivel: false`, `grupo_inferivel_rotulo` e `como_ler` no grupo individual da S.A. (`sociedades_anonimas` conta as S.A. do grupo). A ligação que vem do quadro de outra empresa em que a S.A. é sócia com participação continua.
Um `grupo_id` antigo (o id de snapshots anteriores era a raiz da union-find) devolve o grupo atual que contém aquele CNPJ básico, com `redirecionado_de` e o `grupo_id` estável.
""",
)
def get_grupo(
    grupo_id: str,
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
    include: Optional[str] = Query(None, description="Blocos extras, separados por vírgula: `mercado`, `regulatorio`, `tecnico`, `relacoes`."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    g = next((x for x in store.grupos_societarios_overview(date_str) if x["grupo_id"] == grupo_id), None)
    redirecionado_de = None
    if g is None:
        atual = store.grupo_equivalente(date_str, grupo_id)          # link antigo: o id era a raiz da union-find (GRUPO-E14)
        g = next((x for x in store.grupos_societarios_overview(date_str) if x["grupo_id"] == atual), None) if atual else None
        if g is None:
            raise HTTPException(404, f"Grupo '{grupo_id}' não encontrado no snapshot '{date_str}'")
        redirecionado_de, grupo_id = grupo_id, g["grupo_id"]

    raizes = sorted({c["cnpj"][:8] for c in g["cnpjs"]})
    fin_doc = store.financiamento_doc(date_str) or {}
    fin_ops = fin_doc.get("operadoras") or {}
    com_credito = [fin_ops[r]["financiamento"] for r in raizes if (fin_ops.get(r) or {}).get("financiamento")]
    com_sancao = [fin_ops[r]["sancoes"] for r in raizes if (fin_ops.get(r) or {}).get("sancoes")]
    con_doc = store.contratos_operadoras_doc(date_str) or {}
    con_ops = con_doc.get("operadoras") or {}
    lidas = [con_ops[r] for r in raizes if con_ops.get(r)]
    vinculados = store.asns_do_grupo(date_str, [c["cnpj"] for c in g["cnpjs"]])
    asns = [v["asn"] for v in sorted(vinculados, key=lambda v: v["asn"])]
    resposta = {
        "snapshot_date": date_str,
        "grupo_id": grupo_id,
        "redirecionado_de": redirecionado_de,
        "nome": g["nome"], "nome_regra": g["nome_regra"], "nome_regra_texto": g["nome_regra_texto"], "nome_base": g["nome_base"],
        "classificacao": g["classificacao"],
        "tamanho": g["tamanho"],
        **{k: g[k] for k in ("grupo_inferivel", "grupo_inferivel_motivo", "grupo_inferivel_rotulo", "como_ler", "sociedades_anonimas") if k in g},
        "assinantes": g["assinantes"],
        "usuarios_apnic": g["usuarios_apnic"],
        "visibilidade_bgp": g["visibilidade_bgp"],
        "cnpjs": g["cnpjs"],
        "asns": asns,
        "asns_vinculados": vinculados,
        "regra_vinculo": "ASNs do grupo: os registrados no Registro.br com o CNPJ de uma das empresas (`vinculo` = `cnpj`, fato) e os registrados em outro CNPJ da mesma raiz de 8 dígitos, como uma filial que não declara (`raiz`, inferido). Marca curada não liga ASN a grupo. Somas de usuários e visibilidade usam cada ASN uma vez.",
        "municipios": g["municipios"],
        "empresas": len(raizes),
        "credito_publico": {
            "empresas_com_registro": len(com_credito),
            "operacoes": int(_soma(c["operacoes_total"] for c in com_credito)),
            "contratado": _soma(c["contratado_total"] for c in com_credito),
            "desembolsado": _soma(c["desembolsado_total"] for c in com_credito),
            "natureza": "operações diretas e não automáticas do BNDES, em valores nominais da data da contratação; ausência não é prova de que nunca houve crédito",
        },
        "sancoes": {
            "empresas_com_registro": len(com_sancao),
            "vigentes": int(_soma(s.get("vigentes") and len(s["vigentes"]) for s in com_sancao)),
            "futuras": int(_soma(s.get("futuras") and len(s["futuras"]) for s in com_sancao)),
            "encerradas": int(_soma(s.get("encerradas") and len(s["encerradas"]) for s in com_sancao)),
            "natureza": "registro do órgão sancionador na data do arquivo da CGU (CEIS e CNEP); pode já ter sido suspenso ou anulado; não é julgamento",
        },
        "contratos": {
            "empresas_lidas": len(lidas),
            "empresas_com_resultado": sum(1 for c in lidas if c.get("resultado") == "com_resultado"),
            "itens": int(_soma(c.get("itens") for c in lidas)),
            "contratacoes": int(_soma(c.get("contratacoes") for c in lidas)),
            "valor_homologado": _soma(c.get("valor_homologado") for c in lidas),
            "natureza": "resultados de itens publicados no PNCP, não contratos assinados nem pagamentos; coleta em rodízio, só o CNPJ de matriz e só a Lei 14.133",
        },
        "limites": "Soma das empresas do grupo que têm o dado; as contagens `empresas_*` dizem quantas têm. A composição do grupo é inferida do quadro societário da Receita: cada ligação entre duas empresas é direta, e o grupo reúne as empresas ligadas em cadeia (duas podem estar no grupo sem ligação direta entre si); nomes de sócios não são públicos.",
    }
    extras = {x.strip() for x in (include or "").split(",") if x.strip()}
    if "regulatorio" in extras:
        from api.services.grupo_regulatorio import regulatorio_do_grupo
        resposta["regulatorio"] = regulatorio_do_grupo(g, store.multas_doc(date_str), store.rqual_doc(date_str), store.reclamacoes_doc(date_str), store.consumidor_doc(date_str))
    if "relacoes" in extras:
        from api.services.grupo_relacoes import relacoes_do_grupo
        resposta["relacoes"] = relacoes_do_grupo(g, store._load_socios_grupos(date_str), lambda c: store._display_name_for_cnpj(date_str, c) or c)
    if "tecnico" in extras:
        from api.routes.asns import documento_asn
        from api.services.grupo_tecnico import LIMITE_ASES, tecnico_do_grupo
        asns = sorted(set(resposta["asns"]))
        docs = {a: d for a in asns[:LIMITE_ASES * 3] if (d := documento_asn(store, date_str, a))}      # teto de leitura; o serviço mostra os LIMITE_ASES maiores
        resposta["tecnico"] = tecnico_do_grupo({**g, "asns": asns}, docs)
    if "mercado" in extras:
        resposta["mercado_fixo"] = _mercado(store, date_str, g)
    return resposta


#: linhas por município de um grupo, por (data, grupo): a lista pagina, filtra e reordena sobre a mesma montagem (a chave leva a data, como pede `api/memoria.py`)
_cache_onde_atua: "OrderedDict[tuple[str, str], list[dict]]" = OrderedDict()
_cache_onde_atua_lock = Lock()
_CACHE_ONDE_ATUA_MAX = 24


def _grupo_ou_404(store: Store, date_str: str, grupo_id: str) -> dict:
    gs = store.grupos_societarios_overview(date_str)
    g = next((x for x in gs if x["grupo_id"] == grupo_id), None)
    if g is None:
        atual = store.grupo_equivalente(date_str, grupo_id)
        g = next((x for x in gs if x["grupo_id"] == atual), None) if atual else None
    if g is None:
        raise HTTPException(404, f"Grupo '{grupo_id}' não encontrado no snapshot '{date_str}'")
    return g


@router.get(
    "/grupos/{grupo_id}/municipios",
    summary="Onde o grupo atua: municípios com parcela, declarantes e HHI local (PT-23)",
    description="""
Uma linha por município em que ao menos um CNPJ do grupo declarou acessos fixos ao SICI no `mes_referencia` (que não é a data do snapshot): `acessos` do conjunto,
`parcela` (acessos do conjunto ÷ acessos declarados por todas as empresas no município, em %), `declarantes` (empresas que declararam no município),
`hhi_grupo` (HHI local contando os CNPJs do mesmo grupo como um; **inferido** do quadro societário) e `hhi_cnpj` (HHI local por CNPJ, o declarado), com a faixa de cada um
(método do projeto; ver `limites`) e os `avisos` de recorte (`poucos_casos`; nada é suprimido). `resumo` conta os municípios do conjunto inteiro, não só os da página.

Filtros: `uf` e `q` (parte do nome do município). Ordem: `acessos` (padrão, decrescente), `parcela`, `hhi`, `nome`, `uf`; empate pelo código IBGE. Paginação por `page` e `limit`
(prévia de 100 linhas; além disso, login). Só estrutura entre empresas e municípios: nenhum sócio pessoa física. S.A. não tem grupo inferível (`grupo_inferivel: false`): o conjunto é o CNPJ.
""",
)
def grupo_municipios(
    grupo_id: str,
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
    uf: Optional[str] = Query(None, min_length=2, max_length=2, description="UF do município."),
    q: Optional[str] = Query(None, max_length=80, description="Parte do nome do município."),
    ordem: str = Query("acessos", description="Um de: acessos, parcela, hhi, nome, uf."),
    desc: bool = Query(True, description="Ordem decrescente (padrão); `false` para crescente."),
    limit: int = Query(25, ge=1, le=200),
    page: int = Query(1, ge=1),
) -> dict:
    from api.services import onde_atua as oa

    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    g = _grupo_ou_404(store, date_str, grupo_id)
    dados = store._load_sici(date_str)
    muns = store.sici_municipios(date_str)
    if not dados or not muns:
        raise HTTPException(404, f"O SICI não está publicado no snapshot '{date_str}'.")
    chave = (date_str, g["grupo_id"])
    with _cache_onde_atua_lock:
        linhas = _cache_onde_atua.get(chave)
        if linhas is not None:
            _cache_onde_atua.move_to_end(chave)
    if linhas is None:
        linhas = oa.linhas_do_grupo([x["cnpj"] for x in g["cnpjs"]], dados.get("cnpjs", {}), muns, store.mercado_grupos(date_str))
        with _cache_onde_atua_lock:
            _cache_onde_atua[chave] = linhas
            while len(_cache_onde_atua) > _CACHE_ONDE_ATUA_MAX:
                _cache_onde_atua.popitem(last=False)
    try:
        r = oa.pagina(linhas, uf, q, ordem, desc, limit, (page - 1) * limit)
    except oa.OndeAtuaErro as e:
        raise HTTPException(e.status, e.mensagem)
    return {
        "snapshot_date": date_str, "grupo_id": g["grupo_id"], "mes_referencia": (store.sici_meta(date_str) or {}).get("mes_referencia"),
        "tamanho": g["tamanho"], **{k: g[k] for k in ("grupo_inferivel", "grupo_inferivel_rotulo", "como_ler") if k in g},
        "natureza": "fato (acessos declarados ao SICI, banda larga fixa) com agrupamento inferido; o HHI por CNPJ é o declarado", "limites": oa.LIMITES,
        "resumo": oa.resumo_do_grupo(linhas),
        "filtros": {"uf": uf, "q": q}, "ordem": oa.ORDENS[ordem] + (" (decrescente)" if desc else " (crescente)"), "page": page, "limit": limit,
        **r,
    }


@router.get(
    "/grupos/empresa/{cnpj}",
    summary="Empresas relacionadas a um CNPJ via quadro societário",
    description="""
Para um CNPJ, lista as operadoras com relação societária DIRETA (nunca por
transitividade): `mesmo_grupo` (quadro de sócios idêntico ou controle
exclusivo) e `relacionadas_parcial` (sócio em comum, com a contagem, ou
controle não exclusivo). Listas vazias se o CNPJ não tiver nenhuma relação
detectada.
""",
)
def get_empresas_relacionadas(
    cnpj: str,
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    cnpj_clean = _clean_cnpj(cnpj)
    if len(cnpj_clean) != 14:
        raise HTTPException(400, "CNPJ inválido — informe 14 dígitos (com ou sem formatação).")

    result = store.empresas_relacionadas(date_str, cnpj_clean)
    return {"snapshot_date": date_str, **result}


@router.get(
    "/grupos/{grupo_id}/prefixos-geo",
    summary="Fallback geográfico de um grupo (blocos IPv6/IPv4 dos ASNs)",
    description="""
GeoJSON FeatureCollection com a distribuição geográfica dos blocos IPv6/IPv4
(tabela de roteamento global) de todos os ASNs das empresas do grupo,
agregados por cidade. Use como fallback no mapa **somente quando o grupo não
tiver município nenhum** em `GET /grupos` (ou seja, nenhuma empresa do grupo
declarou acessos ao SICI) — calculado sob demanda, não vem no payload de
`GET /grupos` porque geolocalizar prefixo por prefixo é caro.

Cada feature tem `properties.afi` ("v4"|"v6") e `block_count`.
""",
)
def grupo_prefixos_geo(
    grupo_id: str,
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    grupo_id = store.grupo_equivalente(date_str, grupo_id) or grupo_id
    geojson = store.grupo_prefixos_geo(date_str, grupo_id)
    if geojson is None:
        raise HTTPException(404, f"Grupo '{grupo_id}' não encontrado no snapshot '{date_str}'")

    return {**geojson, "snapshot_date": date_str, "grupo_id": grupo_id}
