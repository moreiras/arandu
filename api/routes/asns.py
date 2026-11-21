# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoints de ASNs — GET /asns e GET /asns/{asn}.

Serve a lista paginada de ASNs brasileiros (do índice compacto) e o documento
completo de um ASN individual com enriquecimento sob demanda (RPKI, ASPA, alertas,
relações de AS_PATH, membros de IX.br).
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from api.respostas import JSONResponse

from api.auth.deps import require_user
from api.ratelimit import limiter, LIMIT_CONTACTS, LIMIT_HEAVY
from api import contatos_cota
from api.schemas import PaginatedASNsResponse, ASNDocumentResponse
from api.store import Store

router = APIRouter()

_log = logging.getLogger("arandurape")

# Campos de contato das outorgas SCM removidos do documento público (info de
# outorga permanece; valores de contato só via /asns/{asn}/contacts).
_SCM_CONTACT_FIELDS = ("telefone", "email")


def _consolidate_contacts(scm_data: list[dict], pdb_contacts: list[dict], geo_org: dict, rdap_contacts: Optional[list[dict]] = None) -> list[dict]:
    """Lista consolidada de contatos (PeeringDB + RDAP do Registro.br + Receita + Anatel) com origem e função.

    Servida APENAS pelo endpoint protegido por login — nunca no documento público.
    """
    contacts: list[dict] = []
    seen: set = set()

    def add(source: str, role: str, name, email, phone) -> None:
        email = (email or "").strip() or None
        phone = (phone or "").strip() or None
        if not email and not phone:
            return
        key = (source, email, phone)
        if key in seen:
            return
        seen.add(key)
        contacts.append({"source": source, "role": role,
                         "name": (name or "").strip() or None,
                         "email": email, "phone": phone})

    for c in pdb_contacts:
        add("PeeringDB", (c.get("role") or "").strip(), c.get("name"), c.get("email"), c.get("phone"))
    for c in rdap_contacts or []:                      # só papel e e-mail; sem nome nem telefone
        add("RDAP (Registro.br)", {"administrative": "administrativo", "abuse": "abuso"}.get(c.get("papel"), c.get("papel") or ""), None, c.get("email"), None)
    add("Receita (CNPJ)", "cadastral", geo_org.get("razao_social"), geo_org.get("email"), geo_org.get("phone"))
    for rec in scm_data:
        add("Anatel (SCM)", "outorga", rec.get("razao_social"), rec.get("email"), rec.get("telefone"))
    return contacts


def _contacts_available(scm_data: list[dict], pdb_contacts: list[dict], geo_org: dict, rdap_contacts: Optional[list[dict]] = None) -> dict:
    """Contagens (sem valores) para o front decidir mostrar o botão 'revelar'. `rdap` só aparece quando informado (rota de ASN)."""
    pdb = sum(1 for c in pdb_contacts if (c.get("email") or c.get("phone")))
    anatel = sum(1 for r in scm_data if (r.get("email") or r.get("telefone")))
    receita = bool((geo_org.get("email") or "").strip() or (geo_org.get("phone") or "").strip())
    out = {"peeringdb": pdb, "anatel": anatel, "receita": receita, "total": pdb + anatel + (1 if receita else 0)}
    if rdap_contacts is not None:
        rdap = sum(1 for c in rdap_contacts if c.get("email"))
        out["rdap"] = rdap
        out["total"] += rdap
    return out

_SORT_FIELDS = {
    "asn", "name", "cnpj",
    "apnic_users", "apnic_v6_users", "pct_v6",
    "ixps_direct_count", "ixps_origin_v4_count", "ixps_origin_v6_count",
    "has_rpki", "has_aspa", "pdb_registered", "has_scm", "has_smp", "has_stfc",
    "has_seac", "external_ixps_count",
}


_SORT_BGP = {"epppd", "epppd_v4", "epppd_v6"}
_INCLUDES = {"bgp_stability", "paths", "prontidao"}
_INCLUDES_UM = {"bloqueios", "paths", "ixp_peers", "estabilidade", "historico", "seguranca", "prontidao", "route_servers", "politica_rs", "organizacao", "abuso", "facilities", "peering", "transito", "referencias", "radar", "exposicao"}      # GET /asns/{asn}?include=: o perfil consolidado da página do ASN
_LOTE_MAX = 100
_NOMES_LOTE_MAX = 500


def _lista(valor: Optional[str]) -> Optional[set[str]]:
    itens = {x.strip() for x in (valor or "").split(",") if x.strip()}
    return itens or None


def _como_resposta(doc: dict) -> dict:
    """O documento como `GET /asns/{asn}` o serve: passa pelo `ASNDocumentResponse` (que descarta campos internos como `geo_org`)."""
    return ASNDocumentResponse.model_validate(doc).model_dump(mode="json")


def _projetar_item(doc: dict, sel: set[str]) -> dict:
    return {k: v for k, v in doc.items() if k in sel or k == "asn"}


def _lote(store: Store, date_str: str, asns: str, fields: Optional[str], extras: set[str]):
    """`GET /asns?asns=…`: documentos completos de vários ASNs numa chamada (até 100), com projeção opcional."""
    try:
        numeros = list(dict.fromkeys(int(x) for x in asns.split(",") if x.strip()))
    except ValueError:
        raise HTTPException(400, "asns deve ser uma lista de números separados por vírgula")
    if not numeros:
        raise HTTPException(400, "asns vazio")
    if len(numeros) > _LOTE_MAX:
        raise HTTPException(400, f"No máximo {_LOTE_MAX} ASNs por chamada.")
    sel = _lista(fields)
    est = store.bgp_stability_por_asn(date_str) if "bgp_stability" in extras else {}
    itens, faltam = [], []
    for n in numeros:
        doc = documento_asn(store, date_str, n)
        if doc is None:
            faltam.append(n)
            continue
        doc = _como_resposta(doc)
        if sel:
            doc = _projetar_item(doc, sel)
        if "bgp_stability" in extras:
            doc = {**doc, **est.get(n, {"epppd": None, "epppd_v4": None, "epppd_v6": None})}
        if "paths" in extras:
            doc = {**doc, "paths": store.asn_paths(date_str, n) or {}}
        itens.append(doc)
    return {"snapshot_date": date_str, "total": len(itens), "items": itens, "not_found": faltam}


@router.get(
    "/asns",
    response_model=PaginatedASNsResponse,
    summary="Listar ASNs (paginado)",
    description="""
Retorna a lista paginada de ASNs com campos compactos. Suporta filtros e busca textual.

**Campos de contagem de prefixos:**
- `rir_prefixes_v4_count` — prefixos **atribuídos** pelo RIR/Registro.br
- `global_prefixes_v4_count` — prefixos observados na tabela de roteamento **global**

**Exemplos de uso:**
- Listar apenas ASNs brasileiros: `?br_only=true`
- Buscar por nome: `?q=rede+nacional`
- Buscar por número: `?q=1916`
- ASNs BR com IPv6: `?br_only=true&ipv6_only=true`
- Paginar: `?page=2&limit=50`
""",
)
def list_asns(
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
        examples=["2026-06-06"],
    ),
    page: int = Query(1, ge=1, description="Número da página (começa em 1)"),
    limit: int = Query(100, ge=1, le=1000, description="Itens por página (máx 1000)"),
    br_only: bool = Query(False, description="Retornar apenas ASNs com registro no Registro.br"),
    ipv6_only: bool = Query(False, description="Retornar apenas ASNs com prefixos IPv6 observados"),
    q: Optional[str] = Query(
        None,
        description="Busca por nome (substring, case-insensitive) ou número exato do AS",
        examples=["1916"],
    ),
    sort_by: Optional[str] = Query(None, description=f"Campo para ordenação. Valores: {', '.join(sorted(_SORT_FIELDS | _SORT_BGP))}"),
    sort_desc: bool = Query(False, description="True para ordem decrescente"),
    asns: Optional[str] = Query(None, description="Lote: ASNs separados por vírgula (até 100). Devolve o **documento completo** de cada um em `items` (os que não existem vão em `not_found`); ignora filtros, ordem e paginação."),
    fields: Optional[str] = Query(None, description="Projeção: campos do primeiro nível a manter em cada item, separados por vírgula (`asn` sempre fica)."),
    include: Optional[str] = Query(None, description="Extras, separados por vírgula: `bgp_stability` (epppd, epppd_v4, epppd_v6 em cada item) e, no lote, `paths` (o corpo de `/asns/{asn}/paths` em `paths`); `prontidao` (`prontidao_indice` e `prontidao_classe` em cada item e `sort_by=prontidao_indice`), ignorado enquanto a lista nominal de prontidão não for liberada (`PRONTIDAO_LISTA_NOMINAL`)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    extras = _lista(include)
    if extras and not extras <= _INCLUDES:
        raise HTTPException(400, f"include inválido: {sorted(extras - _INCLUDES)}; válidos: {sorted(_INCLUDES)}")
    if asns is not None:
        return JSONResponse(_lote(store, date_str, asns, fields, extras or set()))

    index = store.asn_index(date_str)
    scm_asns = store.scm_asn_set(date_str)
    smp_asns = store.smp_asn_set(date_str)
    stfc_asns = store.stfc_asn_set(date_str)
    seac_asns = store.seac_asn_set(date_str)
    geo = store._load_geo_orgs(date_str) or {}

    def _cnpj_of(a: dict) -> str:
        return (geo.get(a.get("asn")) or {}).get("cnpj") or ""

    from api.services import prontidao as _pr
    pront = _pr.indice_por_asn(store.prontidao_doc(date_str)) if (extras and "prontidao" in extras and _pr.lista_nominal_habilitada()) else {}
    if br_only:
        index = [a for a in index if a.get("is_br")]
    if ipv6_only:
        index = [a for a in index if a.get("has_ipv6")]
    if q:
        q_lower = q.lower()
        index = [
            a for a in index
            if q_lower in str(a.get("asn", "")) or q_lower in a.get("name", "").lower()
        ]

    est = store.bgp_stability_por_asn(date_str) if (extras and "bgp_stability" in extras) or sort_by in _SORT_BGP else {}
    if pront and sort_by == "prontidao_indice":
        def _kp(a):
            v = (pront.get(a.get("asn")) or {}).get("prontidao_indice")
            return (1, 0) if v is None else (0, -v if sort_desc else v)
        index = sorted(index, key=_kp)
    elif sort_by and sort_by in _SORT_BGP:
        # None sempre por último, nos dois sentidos
        def _k(a, _c=sort_by):
            v = (est.get(a.get("asn")) or {}).get(_c)
            return (1, 0) if v is None else (0, -v if sort_desc else v)
        index = sorted(index, key=_k)
    elif sort_by and sort_by in _SORT_FIELDS:
        if sort_by == "name":
            index = sorted(index, key=lambda a: (a.get("name") or "").lower(), reverse=sort_desc)
        elif sort_by == "cnpj":
            index = sorted(index, key=_cnpj_of, reverse=sort_desc)
        elif sort_by in ("has_scm", "has_smp", "has_stfc", "has_seac"):
            outorga_set = {"has_scm": scm_asns, "has_smp": smp_asns,
                           "has_stfc": stfc_asns, "has_seac": seac_asns}[sort_by]
            def outorga_key(a, _set=outorga_set):
                v = 1 if a.get("asn") in _set else 0
                return (0, -v if sort_desc else v)
            index = sorted(index, key=outorga_key)
        else:
            def sort_key(a):
                v = a.get(sort_by)
                if v is None:
                    return (1, 0)  # None always last
                if isinstance(v, bool):
                    v = 1 if v else 0
                return (0, -v if sort_desc else v)
            index = sorted(index, key=sort_key)

    total = len(index)
    start = (page - 1) * limit
    # Enriquece a página com has_scm e cnpj (cópia — não muta o índice cacheado).
    items = [
        {**a,
         "has_scm": a.get("asn") in scm_asns,
         "has_smp": a.get("asn") in smp_asns,
         "has_stfc": a.get("asn") in stfc_asns,
         "has_seac": a.get("asn") in seac_asns,
         "cnpj": (geo.get(a.get("asn")) or {}).get("cnpj"),
         "uf": (geo.get(a.get("asn")) or {}).get("uf") or None,
         **(est.get(a.get("asn"), {"epppd": None, "epppd_v4": None, "epppd_v6": None}) if extras and "bgp_stability" in extras else {}),
         **({"prontidao_indice": None, "prontidao_classe": None, **pront.get(a.get("asn"), {})} if pront else {})}
        for a in index[start : start + limit]
    ]
    sel = _lista(fields)
    if sel:
        items = [_projetar_item(i, sel) for i in items]

    corpo = {
        "snapshot_date": date_str,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 0,
        "items": items,
    }
    # `fields` tira campos que o modelo exige: a projeção sai sem a validação do response_model
    return JSONResponse(corpo) if sel else corpo


@router.get(
    "/asns/names",
    summary="Índice de nomes de ASNs",
    description="""
Retorna dicionário `{str(asn): nome}` para todos os ASNs do snapshot que possuem nome.

Fontes de dados (prioridade decrescente):
1. **Registro.br** — autoritativo para ASNs BR
2. **PeeringDB** — redes registradas globalmente
3. **Potaroo/autnums.txt** — compilado por Geoff Huston a partir dos cinco RIRs (~100k ASNs)

Destinado ao frontend para lookup de nomes sem chamadas individuais por ASN.
Resultado cacheado por snapshot — use `staleTime: Infinity` no cliente.
""",
)
def asn_names(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
    asns: Optional[str] = Query(None, description="Lote: só os nomes destes ASNs, separados por vírgula (até 500). Ausentes simplesmente não aparecem."),
    br_only: bool = Query(False, description="Só os ASNs BR (Registro.br): ~10x menos bytes que o dicionário inteiro."),
    detalhe: bool = Query(False, description="Cada valor vira `{name, uf}` em vez de só o nome (UF da organização; nula fora do Brasil)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    lote = None
    if asns is not None:
        try:
            lote = list(dict.fromkeys(int(x) for x in asns.split(",") if x.strip()))
        except ValueError:
            raise HTTPException(400, "asns deve ser uma lista de números separados por vírgula")
        if len(lote) > _NOMES_LOTE_MAX:
            raise HTTPException(400, f"No máximo {_NOMES_LOTE_MAX} ASNs por chamada.")
    return {"snapshot_date": date_str, "names": store.nomes_asns(date_str, lote, br_only, detalhe)}


@router.get(
    "/asns/ix-presence",
    summary="Índice reverso de participação de ASNs em IXes do IX.br",
    description="""
Retorna, para cada ASN, em quais IXes do IX.br ele participa.

```
{ "snapshot_date": "...", "asns": { "<asn>": { "m": ["sp","rj"], "o": ["sp"] } } }
```

- `m` — IXes onde o AS é **membro** do IX.br (lista oficial de participantes)
- `o` — IXes onde o AS **origina prefixos BR** (visto no Looking Glass)

Índice compacto destinado ao Localizador para montar tags de participação sem
chamadas individuais por AS. Cacheado por snapshot — use `staleTime: Infinity`.
""",
)
def asn_ix_presence(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return store.asn_ix_presence(date_str)


@router.get(
    "/asns/by-organization",
    summary="Organizações com vários ASNs (mesmo CNPJ)",
    description="""
Agrupa os ASNs brasileiros pelo CNPJ da organização (Registro.br) e retorna as
organizações com **mais de um ASN**, ordenadas pelo número de ASNs (e usuários APNIC
como desempate). Para cada uma inclui os ASNs com nome, usuários estimados,
blocos IPv6/IPv4 (full table), RPKI/ASPA e participação em IXes.

É uma única pessoa jurídica com vários ASNs (separação de serviços, regiões,
incorporações etc.), **não** um grupo econômico: grupos de empresas ligadas por
sócios ou controle estão em `GET /grupos`. A lista sai em `groups` (nome mantido
por compatibilidade). Substitui `GET /asns/economic-groups`, que segue como alias.
""",
)
def asns_por_organizacao(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
    limit: int = Query(30, ge=1, le=200, description="Número de organizações a retornar."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    rows = store.query_table(date_str, "asns")
    groups: dict[str, list[dict]] = {}
    for r in rows:
        cnpj = re.sub(r"\D", "", r.get("cnpj") or "")
        if len(cnpj) != 14:
            continue
        groups.setdefault(cnpj, []).append(r)

    def _asn_detail(r: dict) -> dict:
        return {
            "asn": r.get("asn"),
            "name": r.get("name") or "",
            "apnic_users": r.get("apnic_users"),
            "apnic_v6_users": r.get("apnic_v6_users"),
            "pct_v6": r.get("pct_v6"),
            "global_prefixes_v4_count": r.get("global_prefixes_v4_count") or 0,
            "global_prefixes_v6_count": r.get("global_prefixes_v6_count") or 0,
            "rir_prefixes_v4_count": r.get("rir_prefixes_v4_count") or 0,
            "rir_prefixes_v6_count": r.get("rir_prefixes_v6_count") or 0,
            "has_rpki": r.get("has_rpki"),
            "has_aspa": r.get("has_aspa"),
            "ixps_direct_count": r.get("ixps_direct_count") or 0,
        }

    items = []
    for cnpj, members in groups.items():
        if len(members) < 2:
            continue
        members.sort(key=lambda r: -(r.get("apnic_users") or 0))
        items.append({
            "cnpj": cnpj,
            "razao_social": next((m.get("razao_social") for m in members if m.get("razao_social")), ""),
            "nome_fantasia": next((m.get("nome_fantasia") for m in members if m.get("nome_fantasia")), ""),
            "uf": next((m.get("uf") for m in members if m.get("uf")), ""),
            "asn_count": len(members),
            "total_apnic_users": sum(m.get("apnic_users") or 0 for m in members),
            "total_v4_blocks": sum(m.get("rir_prefixes_v4_count") or 0 for m in members),
            "total_v6_blocks": sum(m.get("rir_prefixes_v6_count") or 0 for m in members),
            "asns": [_asn_detail(m) for m in members],
        })

    items.sort(key=lambda g: (-g["asn_count"], -g["total_apnic_users"]))

    return {"snapshot_date": date_str, "total": len(items), "groups": items[:limit]}


@router.get(
    "/asns/economic-groups",
    summary="Alias de /asns/by-organization",
    description="Nome antigo de `GET /asns/by-organization` (mesma resposta): os itens são organizações com vários ASNs, não grupos econômicos.",
)
def economic_groups(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
    limit: int = Query(30, ge=1, le=200, description="Número de organizações a retornar."),
) -> dict:
    return asns_por_organizacao(request, date, limit)


def documento_asn(store: Store, date_str: str, asn: int) -> Optional[dict]:
    """Documento completo e enriquecido de um ASN (a resposta de `GET /asns/{asn}`), ou None. Usado também pelo lote."""
    # Documento já enriquecido (ixp_member_codes, path_node_meta, RPKI e alerts).
    # Quando o snapshot foi pré-enriquecido no publish, isto é apenas leitura + serve;
    # caso contrário, a augmentação roda uma vez por processo (memoizada na Store).
    doc = store.asn_full(date_str, asn)
    if doc is None:
        return None

    # Enriquece com dados SCM e contatos PeeringDB (não cacheados no doc de ASN para manter
    # os arquivos publicados imutáveis; calculados on-the-fly com custo mínimo de índice).
    cnpj = doc.get("cnpj") or ""
    import re as _re
    cnpj_digits = _re.sub(r"\D", "", cnpj)

    scm_data = store.scm_for_asn(date_str, asn)
    smp_data = store.smp_for_asn(date_str, asn)
    stfc_data = store.stfc_for_asn(date_str, asn)
    seac_data = store.seac_for_asn(date_str, asn)
    pdb_contacts = store.peeringdb_contacts_for_asn(date_str, asn)
    geo_org = (store._load_geo_orgs(date_str) or {}).get(asn) or {}

    # `geo_prefixes_v4/v6` guardam a posição de cada prefixo (lat/lon/cidade): ficam no publicado, mas não saem.
    doc = {k: v for k, v in doc.items() if k not in ("geo_prefixes_v4", "geo_prefixes_v6")}
    # Documento público: dados de outorga SEM contatos (telefone/email só via
    # /asns/{asn}/contacts, protegido por login).
    if scm_data:
        doc["scm"] = [{k: v for k, v in r.items() if k not in _SCM_CONTACT_FIELDS} for r in scm_data]
    if smp_data:
        doc["smp"] = [{k: v for k, v in r.items() if k not in _SCM_CONTACT_FIELDS} for r in smp_data]
    if stfc_data:
        doc["stfc"] = [{k: v for k, v in r.items() if k not in _SCM_CONTACT_FIELDS} for r in stfc_data]
    if seac_data:
        doc["seac"] = [{k: v for k, v in r.items() if k not in _SCM_CONTACT_FIELDS} for r in seac_data]

    # Possui outorga SCM/SMP/STFC/SeAC? (CNPJ cruza com Anatel)
    doc["has_scm"] = bool(scm_data)
    doc["has_smp"] = bool(smp_data)
    doc["has_stfc"] = bool(stfc_data)
    doc["has_seac"] = bool(seac_data)

    # Outros ASNs do mesmo CNPJ (grupo econômico), com nome para link.
    same: list[dict] = []
    if len(cnpj_digits) == 14:
        names = store.asn_names(date_str)
        for other in store.cnpj_asns_index(date_str).get(cnpj_digits, []):
            if other != asn:
                same.append({"asn": other, "name": names.get(str(other)) or ""})
    doc["same_cnpj_asns"] = same

    # Nomes alternativos (com origem), deduplicados contra o nome do AS.
    alt: list[dict] = []
    seen_names = {(doc.get("name") or "").strip().lower()}

    def _add_name(n: Optional[str], source: str) -> None:
        n = (n or "").strip()
        if n and n.lower() not in seen_names and n != "N/I":
            alt.append({"name": n, "source": source})
            seen_names.add(n.lower())

    _add_name(geo_org.get("razao_social"), "Receita (CNPJ)")
    _add_name(geo_org.get("nome_fantasia"), "nome fantasia (CNPJ)")
    for rec in scm_data:
        _add_name(rec.get("razao_social"), "Anatel (SCM)")
        _add_name(rec.get("nome_fantasia"), "Anatel (SCM, fantasia)")
    doc["alt_names"] = alt

    # Apenas contagens — sem valores. Os contatos vão em /asns/{asn}/contacts.
    doc["contacts_available"] = _contacts_available(scm_data, pdb_contacts, geo_org, store.rdap_contatos_for_asn(date_str, asn)["contatos"])

    return doc


@router.get(
    "/asns/{asn}",
    response_model=ASNDocumentResponse,
    summary="Documento completo de um ASN",
    description="""
Retorna o documento completo de um AS com todas as informações disponíveis.

**Prefixos — três fontes distintas:**
- `rir_prefixes_v4/v6` — atribuídos pelo **RIR/Registro.br** (fonte autoritativa de alocação)
- `global_prefixes_v4/v6` — observados na **full table global** (tabela de roteamento BGP)
- `ixp_presence[código].v4.prefixes` — observados em cada **IXP específico**

**Presença em IXPs (`ixp_presence`):**
Dicionário com código do IXP como chave. Para cada IXP:
- `direct` — True se o AS faz peering direto (aparece no primeiro hop do AS_PATH)
- `origin` — True se prefixos do AS são visíveis (pode ser via upstream)
- `prefixes` — lista dos prefixos deste AS observados neste IXP

**Relações de peering (`upstreams` / `downstreams`):**
Inferidas do AS_PATH observado nos Looking Glasses coletados.
Não representam acordos comerciais verificados — são observações de roteamento.

**Exemplos de ASNs BR interessantes:**
- `1916` — RNP (Rede Nacional de Ensino e Pesquisa)
- `18881` — Global Village Telecom
- `28573` — Claro Brasil
- `7738` — Telemar
""",
)
def get_asn(
    asn: int,
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
        examples=["2026-06-06"],
    ),
    fields: Optional[str] = Query(None, description="Projeção: campos do primeiro nível a manter, separados por vírgula (`asn` sempre fica)."),
    include: Optional[str] = Query(None, description="Perfil consolidado: blocos extras, separados por vírgula — `referencias` (posição por usuários estimados e medianas dos ASes BR), `paths` (o corpo de `/asns/{asn}/paths`), `ixp_peers` (as linhas deste AS nos PTTs diretos, o `peers` de `/asns/{asn}/ixp-peers`) `estabilidade` (o corpo de `/bgp-stability/asn/{asn}`, 6 semanas) `historico` (série e eventos recentes do AS; o anônimo vê só as datas atuais), `seguranca` (ROV, DNSSEC, AS Rank e bogons) e `route_servers` (as sessões do AS nos route servers do IX.br) e `politica_rs` (rejeições e política por communities nos route servers, o corpo de `/asns/{asn}/politica`). `organizacao` (organização do CAIDA/AS Rank por ASN, o corpo de `/asns/{asn}/organizacao`) e `abuso` (contagem agregada do Feodo Tracker, o corpo de `/asns/{asn}/abuso`), `facilities` (instalações do Brasil do PeeringDB onde o AS declara estar, `/asns/{asn}/facilities`) e `peering` (atributos de peering autodeclarados no PeeringDB e portas nos PTTs externos, `/asns/{asn}/peering`). Cada um vem como chave de mesmo nome; sem `include` a resposta é a de sempre."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    extras = _lista(include) or set()
    if extras - _INCLUDES_UM:
        raise HTTPException(400, f"include inválido: {sorted(extras - _INCLUDES_UM)}; válidos: {sorted(_INCLUDES_UM)}")
    doc = documento_asn(store, date_str, asn)
    if doc is None:
        raise HTTPException(404, f"ASN {asn} não encontrado no snapshot '{date_str}'")
    sel = _lista(fields)
    if not sel and not extras:
        return doc
    out = _projetar_item(_como_resposta(doc), sel) if sel else dict(_como_resposta(doc))
    if "paths" in extras:
        out["paths"] = store.asn_paths(date_str, asn) or {}
    if "ixp_peers" in extras:
        out["ixp_peers"] = (store.asn_ixp_peers(date_str, asn) or {}).get("peers", {})
    if "estabilidade" in extras:
        out["estabilidade"] = store.bgp_stability_asn(date_str, asn, 6)
    if "historico" in extras:
        from api.routes.historico import bloco_historico
        out["historico"] = bloco_historico(request, "asn", str(asn))
    if "seguranca" in extras:
        from api.services.seguranca import bloco_asn
        out["seguranca"] = bloco_asn(store.seguranca_doc(date_str), asn)
    if "prontidao" in extras:
        from api.services.prontidao import bloco_asn as _pr_asn
        out["prontidao"] = _pr_asn(store.prontidao_doc(date_str), asn)
    if "route_servers" in extras:
        from api.services.route_servers import bloco_asn as _rs_asn
        out["route_servers"] = _rs_asn(store.route_servers_asns_doc(date_str), asn)
    if "politica_rs" in extras:
        from api.services.rs_policy import bloco_asn as _pol_asn
        out["politica_rs"] = _pol_asn(store.rs_policy_asns_doc(date_str), asn)
    if "bloqueios" in extras:
        from api.services.bloqueios import bloco_asn as _blq
        out["bloqueios"] = _blq(store.bloqueios_doc(date_str), asn)
    if "radar" in extras:
        from api.services.radar import bloco_asn as _radar
        out["radar"] = _radar(store.radar_doc(date_str), asn)
    if "exposicao" in extras:
        from api.services.exposicao import bloco_asn as _expo
        out["exposicao"] = _expo(store.exposicao_doc(date_str), asn)
    if "organizacao" in extras:
        from api.services.as2org import bloco_organizacao as _org
        out["organizacao"] = _org(store.as2org_doc(date_str), asn)
    if "abuso" in extras:
        from api.services.as2org import bloco_abuso as _ab
        out["abuso"] = _ab(store.abuso_doc(date_str), asn)
    if "referencias" in extras:
        from api.services.referencias_asn import bloco_referencias as _ref
        out["referencias"] = _ref(store, date_str, asn)
    if "transito" in extras:
        from api.services.transito import bloco_asn as _tr
        out["transito"] = _tr(store.transito_asns_doc(date_str), asn)
    if "facilities" in extras:
        from api.services.instalacoes import bloco_asn as _fac
        out["facilities"] = _fac(store.instalacoes_doc(date_str), store.vinculos_instalacoes_doc(date_str), asn)
    if "peering" in extras:
        from api.services.instalacoes import bloco_peering as _peer
        out["peering"] = _peer(store.atributos_rede_doc(date_str), store.portas_externas_doc(date_str), store.vinculos_instalacoes_doc(date_str), asn)
    return JSONResponse(out)


@router.get(
    "/asns/{asn}/contacts",
    summary="Contatos de um AS (protegido por login)",
    description="""
Retorna os contatos consolidados de um AS (PeeringDB POC, Receita/CNPJ, Anatel/SCM)
com origem e função. **Requer autenticação** (cookie de login ou IP na allowlist) e é
limitado por taxa. Os contatos NUNCA são servidos em lote — apenas por AS aqui.
""",
)
@limiter.limit(LIMIT_CONTACTS)
def get_asn_contacts(
    asn: int,
    request: Request,
    user: dict = Depends(require_user),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    # Cota de contatos: conta obrigatória, custo 1 por ASN, tetos por conta, rede e global.
    restante = contatos_cota.exigir(request, user, 1)

    scm_data = store.scm_for_asn(date_str, asn)
    pdb_contacts = store.peeringdb_contacts_for_asn(date_str, asn)
    geo_org = (store._load_geo_orgs(date_str) or {}).get(asn) or {}
    rdap = store.rdap_contatos_for_asn(date_str, asn)
    contacts = _consolidate_contacts(scm_data, pdb_contacts, geo_org, rdap["contatos"])

    # Auditoria: quem acessou contatos de qual AS (gancho p/ detecção de enumeração). Conta, nunca e-mail nem IP.
    _log.info("contact_access asn=%s conta=%s count=%d", asn, (user.get("conta_id") or user.get("provider")), len(contacts))

    return {"snapshot_date": date_str, "asn": asn, "total": len(contacts), "contacts": contacts, "rdap": {k: rdap[k] for k in ("leitura_em", "tentou_em", "status", "cobertura")},
            "cota": {"restante_hoje": restante}}


@router.get(
    "/asns/{asn}/paths",
    summary="AS_PATH chains de IXPs para um ASN (origin-only)",
    description="""
Retorna os caminhos AS_PATH observados em cada IXP onde este AS aparece como originador
(mas não como membro direto). Inclui metadados dos ASes intermediários (`path_node_meta`).

Endpoint separado do documento principal para permitir carregamento progressivo:
o documento base (`/asns/{asn}`) retorna imediatamente; este endpoint pode levar
mais tempo para ASes com muitos IXPs origin-only sem caminhos pré-computados.

Sempre retorna HTTP 200. Se não houver caminhos, `ixp_paths` é `{}`.
""",
)
@limiter.limit(LIMIT_HEAVY)
def get_asn_paths(
    asn: int,
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    result = store.asn_paths(date_str, asn)
    if result is None:
        raise HTTPException(404, f"ASN {asn} não encontrado no snapshot '{date_str}'")
    return result


@router.get(
    "/asns/{asn}/interconexao",
    summary="Interconexão mensurável do AS: originação sem sessão direta, sessões nos route servers e rejeições",
    description="""
O que os dados públicos mostram sobre a interconexão do AS: os PTTs do IX.br onde ele origina prefixos **sem ser par direto** (com quem entrega os caminhos observados), os PTTs onde o
cadastro e as sessões do route server não batem (sem sessão, ou só IPv6/IPv4), e as rotas rejeitadas e as ações de communities declaradas. **Nunca** diz com quem o AS troca tráfego: peering
bilateral não é visível nesses dados. Cada item é um fato na data da coleta, não uma recomendação.
""",
)
def asn_interconexao(asn: int, request: Request, date: Optional[str] = Query(None)) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.asn_detail(date_str, asn)
    if doc is None:
        raise HTTPException(404, f"AS{asn} não encontrado no snapshot {date_str}")
    from api.services.interconexao import oportunidades
    ixps = {e["code"]: {"nome": e.get("name"), "uf": e.get("uf")} for e in store.ixp_index(date_str) if e.get("code")}
    rs = (store.route_servers_asns_doc(date_str) or {}).get("asns", {}).get(str(asn))
    pol = (store.rs_policy_asns_doc(date_str) or {}).get("asns", {}).get(str(asn))
    geo = doc.get("geo_org") or {}
    uf = geo.get("uf")
    # distância em linha reta da sede do AS a cada PTT (um PTT com vários locais vale pelo mais próximo)
    km = {p["codigo"]: p["km"] for p in store.ptts_proximos(date_str, geo["lon"], geo["lat"], n=1000)} if geo.get("lat") is not None and geo.get("lon") is not None else None
    return {"snapshot_date": date_str, **oportunidades(doc, rs, store.route_servers_ixps_doc(date_str), pol, ixps, uf, km)}


@router.get(
    "/asns/{asn}/ixp-peers",
    summary="Estatísticas de peering deste AS em cada IXP direto (batch)",
    description="""
Retorna, em uma única chamada, as estatísticas de peering deste AS em **cada IXP onde
ele faz peering direto**, para v6 e v4.

Evita o fan-out do frontend, que faria uma requisição por IXP × AFI
(`/ixps/{code}/peers`) só para extrair a linha deste AS — baixando a lista inteira de
peers de cada IXP. Aqui o servidor extrai apenas a linha relevante.

Formato: `peers[code] = {v4?: stats, v6?: stats}` (mesma estrutura de `IXPPeerStats`).
Sempre HTTP 200; `peers` é `{}` se o AS não tiver peering direto.
""",
)
def get_asn_ixp_peers(
    asn: int,
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    result = store.asn_ixp_peers(date_str, asn)
    if result is None:
        raise HTTPException(404, f"ASN {asn} não encontrado no snapshot '{date_str}'")
    return result


@router.get(
    "/asns/{asn}/acessos",
    summary="Acessos de banda larga declarados à Anatel (SICI) por este AS",
    description="""
Base de assinantes declarada ao SICI pelo CNPJ que detém o ASN, no mês de referência
mais recente: total, B2C (Pessoa Física) × B2B (Pessoa Jurídica), capacidade contratada,
municípios atendidos, mix de tecnologia, série histórica mensal e a comparação com os
usuários estimados pelo APNIC.

**Atenção ao campo `acessos_compartilhados`**: quando o CNPJ tem mais de um ASN, o total
declarado é atribuído integralmente a cada um deles — somar ASes do mesmo CNPJ conta o
mesmo assinante mais de uma vez. Agregue por CNPJ.

Cite sempre as duas datas: a do snapshot e o `mes_referencia` da declaração.
""",
)
def get_asn_acessos(
    asn: int,
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    meta = store.sici_meta(date_str)
    if not meta:
        raise HTTPException(404, "Dados de acessos (SICI) não disponíveis neste snapshot.")

    agg = store.sici_for_asn(date_str, asn)
    if not agg:
        raise HTTPException(
            404, f"AS{asn} não tem CNPJ com acessos declarados em {meta['mes_referencia']}.")

    cnpj = store.sici_cnpj_for_asn(date_str, asn)
    return {
        "snapshot_date": date_str,
        "mes_referencia": meta["mes_referencia"],
        "asn": asn,
        "cnpj": cnpj,
        **{k: v for k, v in agg.items() if k != "por_municipio"},
        "serie": store.sici_serie(date_str, cnpj) if cnpj else [],
        "divergencia_apnic_anatel": store.sici_divergencia(date_str, asn),
    }


@router.get(
    "/asns/{asn}/acessos/municipios",
    summary="Distribuição municipal dos acessos deste AS",
    description="Uma linha por município atendido pelo CNPJ do AS, com acessos, "
                "split PF/PJ, capacidade contratada e share do operador no município. "
                "Alimenta o mapa de distribuição da página do AS.",
)
def get_asn_acessos_municipios(
    asn: int,
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
    limit: int = Query(6000, ge=1, le=6000),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    meta = store.sici_meta(date_str)
    if not meta:
        raise HTTPException(404, "Dados de acessos (SICI) não disponíveis neste snapshot.")
    agg = store.sici_for_asn(date_str, asn)
    if not agg:
        raise HTTPException(404, f"AS{asn} sem acessos declarados.")

    cnpj = store.sici_cnpj_for_asn(date_str, asn)
    items = []
    for ibge, mun in agg.get("por_municipio", {}).items():
        total_mun = store.sici_municipio(date_str, ibge) or {}
        denom = total_mun.get("acessos") or 0
        items.append({
            "ibge": ibge,
            "nome": mun.get("nome", ""),
            "uf": mun.get("uf", ""),
            "acessos": mun.get("acessos", 0),
            "pf": mun.get("pf", 0),
            "pj": mun.get("pj", 0),
            "capacidade_mbps": mun.get("capacidade_mbps", 0.0),
            "municipio_acessos": denom,
            "share": round(100 * mun.get("acessos", 0) / denom, 2) if denom else None,
            "municipio_operadores": total_mun.get("operadores_count", 0),
        })
    items.sort(key=lambda m: -m["acessos"])
    return {
        "snapshot_date": date_str,
        "mes_referencia": meta["mes_referencia"],
        "asn": asn, "cnpj": cnpj,
        "total": len(items),
        "acessos_compartilhados": agg.get("acessos_compartilhados", False),
        "items": items[:limit],
    }
