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
Uma linha por grupo societário (`grupo_id`): CNPJs membros, classificação
(`total` — toda relação interna é quadro idêntico/controle exclusivo;
`parcial` — toda relação é sócio em comum/controle não exclusivo; `misto` —
tem as duas; `individual` — empresa sem relação societária com nenhuma outra
da base, listada como "grupo de uma empresa só", `grupo_id` = `ind_{cnpj básico}`),
total de assinantes (acessos fixos declarados ao SICI/SCM — não
inclui móvel) e a distribuição municipal agregada desses acessos. Cada CNPJ
traz os ASNs associados (`asns`) e as flags de outorga Anatel.
`visibilidade_bgp` = algum AS de alguma empresa do grupo origina ao menos um
bloco IPv6/IPv4 na tabela BGP global.

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
(`ind_<cnpj básico>` para empresa individual).
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
    if g is None:
        raise HTTPException(404, f"Grupo '{grupo_id}' não encontrado no snapshot '{date_str}'")

    raizes = sorted({c["cnpj"][:8] for c in g["cnpjs"]})
    fin_doc = store.financiamento_doc(date_str) or {}
    fin_ops = fin_doc.get("operadoras") or {}
    com_credito = [fin_ops[r]["financiamento"] for r in raizes if (fin_ops.get(r) or {}).get("financiamento")]
    com_sancao = [fin_ops[r]["sancoes"] for r in raizes if (fin_ops.get(r) or {}).get("sancoes")]
    con_doc = store.contratos_operadoras_doc(date_str) or {}
    con_ops = con_doc.get("operadoras") or {}
    lidas = [con_ops[r] for r in raizes if con_ops.get(r)]
    asns = sorted({a for c in g["cnpjs"] for a in (c.get("asns") or [])})
    resposta = {
        "snapshot_date": date_str,
        "grupo_id": grupo_id,
        "classificacao": g["classificacao"],
        "tamanho": g["tamanho"],
        "assinantes": g["assinantes"],
        "usuarios_apnic": g["usuarios_apnic"],
        "visibilidade_bgp": g["visibilidade_bgp"],
        "cnpjs": g["cnpjs"],
        "asns": asns,
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
        "limites": "Soma das empresas do grupo que têm o dado; as contagens `empresas_*` dizem quantas têm. A composição do grupo é inferida do quadro societário da Receita (evidência direta, nunca transitiva) e não é pública em nomes de sócios.",
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

    geojson = store.grupo_prefixos_geo(date_str, grupo_id)
    if geojson is None:
        raise HTTPException(404, f"Grupo '{grupo_id}' não encontrado no snapshot '{date_str}'")

    return {**geojson, "snapshot_date": date_str, "grupo_id": grupo_id}
