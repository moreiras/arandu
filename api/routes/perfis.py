# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Perfis consolidados por entidade: uma chamada devolve o que a página da entidade
montaria com 4 a 6.

  * `GET /municipios/{ibge}`  — SICI fixo (com % de fibra) e móvel, centróide e PTTs mais próximos.
  * `GET /ufs` e `GET /ufs/{uf}` — resumo das 27 UFs (acessos, fibra, usuários, PTTs) e o perfil de uma UF.
  * `GET /operadoras/{cnpj}`  — outorgas e acessos dos 4 serviços (SCM, SMP, STFC, SeAC), ASNs, rede, grupo e
    `contacts_available` (só a contagem; contatos seguem em `/acessos/operadora/{cnpj}/contacts`, com login).

`?blocos=` omite seções pesadas e `?fields=` projeta campos do primeiro nível; as rotas antigas
(`/acessos/municipio/{ibge}` etc.) seguem como estão.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.routes.acessos import acessos_operadora
from api.routes.acessos_movel import acessos_movel_operadora
from api.routes.seac import get_seac
from api.routes.stfc import get_stfc
from api.store import Store

router = APIRouter()

_BLOCOS_MUNICIPIO = {"fixo", "movel", "ptts"}


def _lista(valor: Optional[str]) -> Optional[set[str]]:
    itens = {x.strip() for x in (valor or "").split(",") if x.strip()}
    return itens or None


def _blocos(valor: Optional[str], validos: set[str]) -> Optional[set[str]]:
    sel = _lista(valor)
    if sel is not None and not sel <= validos:
        raise HTTPException(400, f"blocos inválidos: {sorted(sel - validos)}; válidos: {sorted(validos)}")
    return sel


def _projetar(doc: dict, fields: Optional[str]) -> dict:
    sel = _lista(fields)
    if sel is None:
        return doc
    return {k: v for k, v in doc.items() if k in sel or k in ("snapshot_date", "ibge", "uf", "cnpj")}


@router.get(
    "/municipios/{ibge}",
    summary="Perfil do município (fixo, móvel, fibra e PTTs mais próximos)",
    description="""
Consolida em uma chamada o que a página do município usava de 4 rotas: banda larga fixa
(SICI, com `fibra_pct` quando o mês foi coletado com o meio de acesso), telefonia móvel,
centróide e os PTTs mais próximos em linha reta. Existe se houver fixo **ou** móvel.

`blocos` (fixo, movel, ptts) omite seções; `fields` projeta campos do primeiro nível.
""",
)
def municipio_perfil(
    request: Request,
    ibge: str,
    date: Optional[str] = Query(None),
    blocos: Optional[str] = Query(None, description="Seções a incluir, separadas por vírgula: fixo, movel, ptts."),
    fields: Optional[str] = Query(None, description="Campos do primeiro nível a manter, separados por vírgula."),
    include: Optional[str] = Query(None, description="Extras: `indicadores` = HHI, variações e ganho/perda em 12 meses; `territorio` = população, domicílios, penetração, mercado não visto e PTT mais próximo; `erbs` = estações do SMP licenciadas no município. `fust` = compromissos do FUST no município. `qualidade` = último resultado do RQUAL por prestadora e `reclamacoes` = reclamações na Anatel por ano, serviço e marca. `consumidor` = reclamações finalizadas no Consumidor.gov.br no município, por empresa, na janela de 12 meses. `serie_mercado` = série mensal (13 meses) de acessos, HHI e participação das 4 maiores operadoras. `mercado_grupos` = HHI por CNPJ e por grupo econômico (inferido) e a faixa de concentração; na operadora, as que mais aparecem nos mesmos municípios; na UF, o HHI por grupo e quantos municípios mudam de faixa. `rede_territorio` = IPv6 estimado, usuários atrás de ROV (UF) e dependência de trânsito, com suposição e cobertura."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    sel = _blocos(blocos, _BLOCOS_MUNICIPIO)
    extras = _blocos(include, {"indicadores", "territorio", "erbs", "fust", "qualidade", "reclamacoes", "consumidor", "serie_mercado", "mercado_grupos", "rede_territorio"})
    perfil = store.perfil_municipio(date_str, ibge.strip(), sel)
    if perfil is None:
        raise HTTPException(404, f"Município IBGE {ibge} sem acessos declarados.")
    if extras and "indicadores" in extras:
        from api.services.sici_indicadores import bloco_municipio
        perfil = {**perfil, "indicadores": bloco_municipio(store.sici_indicadores(date_str), ibge.strip())}
    if extras and "mercado_grupos" in extras:
        from api.services.sici_indicadores import bloco_mercado_municipio
        perfil = {**perfil, "mercado_grupos": bloco_mercado_municipio(store.mercado_grupos(date_str), ibge.strip())}
    if extras and "rede_territorio" in extras:
        from api.services.rede_territorio import bloco_municipio as rede_municipio
        perfil = {**perfil, "rede_territorio": rede_municipio(store.rede_territorio_doc(date_str), ibge.strip())}
    if extras and "serie_mercado" in extras:
        from api.services.sici_indicadores import bloco_serie_municipio
        perfil = {**perfil, "serie_mercado": bloco_serie_municipio(store.sici_serie_municipio(date_str), ibge.strip())}
    if extras and "territorio" in extras:
        from api.services.territorio import bloco_municipio as terr_municipio
        perfil = {**perfil, "territorio": terr_municipio(store.territorio_doc(date_str), store.territorio_linhas(date_str), ibge.strip())}
    if extras and "erbs" in extras:
        from api.services.erbs import bloco_municipio as erbs_municipio
        perfil = {**perfil, "erbs": erbs_municipio(store.erbs_doc(date_str), ibge.strip(), perfil.get("uf"))}
    if extras and "fust" in extras:
        from api.services.fust import bloco_municipio as fust_municipio
        perfil = {**perfil, "fust": fust_municipio(store.fust_doc(date_str), ibge.strip(), perfil.get("uf"))}
    if extras and ({"qualidade", "reclamacoes"} & extras):
        from api.services import qualidade as qual
        cod = ibge.strip()
        if "qualidade" in extras:
            rq = store.rqual_doc(date_str)
            uf_mun = qual.uf_do_municipio(rq, cod)
            perfil = {**perfil, "qualidade": qual.bloco_municipio(rq, store.rqual_municipios_uf(date_str, uf_mun) if uf_mun else None, cod)}
        if "reclamacoes" in extras:
            rc = store.reclamacoes_doc(date_str)
            uf_mun = qual.uf_do_municipio(rc, cod)
            perfil = {**perfil, "reclamacoes": qual.bloco_reclamacoes_municipio(rc, store.reclamacoes_municipios_uf(date_str, uf_mun) if uf_mun else None, cod)}
    if extras and "consumidor" in extras:
        from api.services import consumidor as cons
        cod = ibge.strip()
        cg = store.consumidor_doc(date_str)
        uf_mun = cons.uf_do_municipio(cg, cod)
        perfil = {**perfil, "consumidor": cons.bloco_municipio(cg, store.consumidor_municipios_uf(date_str, uf_mun) if uf_mun else None, cod)}
    return _projetar(perfil, fields)


_BLOCOS_OPERADORA = {"scm", "smp", "stfc", "seac"}
_INCLUDES_PERFIL = {"historico", "historico_completo", "indicadores", "territorio", "cetic", "erbs", "fust", "multas", "prontidao", "qualidade", "reclamacoes", "consumidor", "transito", "radar", "exposicao", "mercado_grupos", "rede_territorio"}
_ENVELOPE = ("snapshot_date", "cnpj")


def _sub(handler) -> Optional[dict]:
    """Roda a rota antiga do serviço e devolve o corpo sem o envelope repetido; None se o CNPJ não existe nele.

    Reusar o handler (e não reescrever a consulta) garante que o perfil tenha os mesmos números das rotas que ele
    consolida."""
    try:
        doc = handler()
    except HTTPException as e:
        if e.status_code == 404:
            return None
        raise
    return {k: v for k, v in doc.items() if k not in _ENVELOPE}


@router.get(
    "/operadoras/{cnpj}",
    summary="Perfil da operadora por CNPJ (SCM, SMP, STFC, SeAC, ASNs e rede)",
    description="""
Consolida em uma chamada o que a página da operadora montava com 4 rotas: `scm` (outorgas SCM, SICI fixo, ASNs,
grupo), `smp` (móvel), `stfc` e `seac`, cada um **nulo** quando o CNPJ não tem aquele serviço. A `rede` (agregação
de rede dos ASNs) vem uma vez só, no topo. Existe se **qualquer** serviço existir. Contatos não vêm aqui:
`contacts_available` só conta, e os valores ficam na rota `/contacts`, com login.

`blocos` (scm, smp, stfc, seac) omite serviços; `fields` projeta campos do primeiro nível.
""",
)
def operadora_perfil(
    request: Request,
    cnpj: str,
    date: Optional[str] = Query(None),
    blocos: Optional[str] = Query(None, description="Serviços a incluir, separados por vírgula: scm, smp, stfc, seac."),
    fields: Optional[str] = Query(None, description="Campos do primeiro nível a manter, separados por vírgula."),
    include: Optional[str] = Query(None, description="Extras: `historico` = série e eventos dos 2 snapshots atuais; `historico_completo` = a série inteira (exige login); `indicadores` = share, HHI, variações e declaração ao SICI; `territorio` = população, domicílios, penetração e mercado não visto; `erbs` = estações do SMP licenciadas da operadora. `multas` = multas constituídas da Anatel contra a empresa (raiz do CNPJ), por serviço. `qualidade` = RQUAL das prestadoras ligadas ao CNPJ e `reclamacoes` = reclamações das marcas ligadas ao CNPJ, com a ligação rotulada. `consumidor` = reclamações finalizadas das empresas do Consumidor.gov.br ligadas ao CNPJ, com série mensal e assuntos."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    extras = _blocos(include, _INCLUDES_PERFIL)
    try:
        perfil = montar_perfil_operadora(store, cnpj, date_str, _blocos(blocos, _BLOCOS_OPERADORA))
    except HTTPException as e:
        # CNPJ sem ASN, outorga nem SICI, mas com multa constituída: perfil mínimo só com as multas, para a página não dizer que não há informação.
        if e.status_code != 404 or not (extras and "multas" in extras):
            raise
        from api.services.regulatorio import bloco_operadora as multas_operadora
        digitos = "".join(c for c in cnpj if c.isdigit())
        multas = multas_operadora(store.multas_doc(date_str), digitos)
        if not multas:
            raise
        return _projetar({"snapshot_date": date_str, "cnpj": digitos, "multas": multas}, fields)
    from api.routes.historico import bloco_historico, pede_historico
    if (completo := pede_historico(extras)) is not None:
        perfil["historico"] = bloco_historico(request, "operadora", perfil["cnpj"], completo)
    if extras and "mercado_grupos" in extras:
        from api.services.sici_indicadores import bloco_sobreposicao_operadora
        perfil["mercado_grupos"] = bloco_sobreposicao_operadora(store.mercado_grupos(date_str), perfil["cnpj"])
    if extras and "indicadores" in extras:
        from api.services.sici_indicadores import bloco_operadora
        perfil["indicadores"] = bloco_operadora(store.sici_indicadores(date_str), store.sem_declaracao_sici(date_str), perfil["cnpj"])
    if extras and "erbs" in extras:
        from api.services.erbs import bloco_operadora as erbs_operadora
        perfil["erbs"] = erbs_operadora(store.erbs_doc(date_str), perfil["cnpj"])
    if extras and "multas" in extras:
        from api.services.regulatorio import bloco_operadora as multas_operadora
        perfil["multas"] = multas_operadora(store.multas_doc(date_str), perfil["cnpj"])
    if extras and "prontidao" in extras:
        from api.services.prontidao import bloco_operadora as prontidao_operadora
        perfil["prontidao"] = prontidao_operadora(store.prontidao_doc(date_str), perfil["cnpj"])
    if extras and "qualidade" in extras:
        from api.services.qualidade import bloco_operadora as qualidade_operadora
        perfil["qualidade"] = qualidade_operadora(store.rqual_doc(date_str), perfil["cnpj"])
    if extras and "reclamacoes" in extras:
        from api.services.qualidade import bloco_reclamacoes_operadora
        perfil["reclamacoes"] = bloco_reclamacoes_operadora(store.reclamacoes_doc(date_str), perfil["cnpj"])
    if extras and "consumidor" in extras:
        from api.services.consumidor import bloco_operadora as consumidor_operadora
        perfil["consumidor"] = consumidor_operadora(store.consumidor_doc(date_str), perfil["cnpj"])
    return _projetar(perfil, fields)


def montar_perfil_operadora(store: Store, cnpj: str, date_str: str, sel: Optional[set[str]] = None) -> dict:
    """Perfil da operadora (usado pela rota e pela tool `get_operator` do MCP). Levanta `HTTPException` 400/404.

    Reusa os handlers das rotas por serviço por meio de um `request` mínimo que só carrega a `store`."""
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(store=store)))
    quer = lambda b: sel is None or b in sel  # noqa: E731
    out: dict = {"snapshot_date": date_str}
    achou = False
    rede = None
    chamadas = (
        ("scm", lambda: acessos_operadora(request, cnpj, date_str)),
        ("smp", lambda: acessos_movel_operadora(request, cnpj, date_str)),
        ("stfc", lambda: get_stfc(cnpj, request, date_str)),
        ("seac", lambda: get_seac(cnpj, request, date_str)),
    )
    for chave, handler in chamadas:
        if not quer(chave):
            continue
        doc = _sub(handler)
        if doc is not None and "rede" in doc:
            rede = rede or doc["rede"]
            doc = {k: v for k, v in doc.items() if k != "rede"}
        out[chave] = doc
        achou = achou or doc is not None
    if not achou:
        raise HTTPException(404, "Não há informação para este CNPJ.")
    out["cnpj"] = "".join(c for c in cnpj if c.isdigit())
    if rede is not None:
        out["rede"] = rede
    return out


UFS = frozenset(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)
_BLOCOS_UF = {"ptts", "municipios", "operadoras"}


@router.get(
    "/ufs",
    summary="Resumo das 27 UFs (acessos, fibra, usuários estimados e PTTs)",
    description="""
Uma linha por UF com os números que a página `/estados` mostra: `ptts` (PTTs do IX.br na UF no snapshot, com ou sem coleta: a mesma
lista usada na distância) e `ptts_com_coleta`, municípios e acessos fixos declarados ao SICI (`null` quando o snapshot não tem o SICI;
ausência, não zero), `fibra_pct` (meio de acesso "Fibra"), ASNs BR e **usuários estimados** (soma APNIC dos ASNs
da UF, pela geolocalização da organização — estimativa, não censo), municípios a mais de 100 km de um PTT e, quando há o produto de território,
`domicilios` (projetados, IBGE) e `penetracao` (acessos fixos ÷ domicílios; é razão, não percentual, e pode passar de 1 porque um domicílio tem vários acessos).
""",
)
def ufs_resumo(request: Request, date: Optional[str] = Query(None)) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    meta = store.sici_meta(date_str) or {}
    itens = store.resumo_ufs(date_str)
    return {"snapshot_date": date_str, "mes_referencia": meta.get("mes_referencia"), "total": len(itens), "items": itens}


@router.get(
    "/ufs/{uf}",
    summary="Perfil da UF (totais, PTTs, municípios com distância ao PTT, operadoras e ASNs)",
    description="""
Consolida em uma chamada o que a página da UF montava com 5: `totais` (acessos, `fibra_pct`, ASNs, usuários estimados,
municípios sem PTT a 100 km), `ixps` (PTTs da UF), `municipios` (com a distância em linha reta ao PTT mais próximo,
calculada no servidor) e `operadoras` sediadas (as 10 maiores e o total).

`blocos` (ptts, municipios, operadoras) omite seções; `fields` projeta campos do primeiro nível.
""",
)
def uf_perfil(
    request: Request,
    uf: str,
    date: Optional[str] = Query(None),
    blocos: Optional[str] = Query(None, description="Seções a incluir, separadas por vírgula: ptts, municipios, operadoras."),
    fields: Optional[str] = Query(None, description="Campos do primeiro nível a manter, separados por vírgula."),
    include: Optional[str] = Query(None, description="Extras: `historico` = série e eventos dos 2 snapshots atuais; `historico_completo` = a série inteira (exige login); `indicadores` = share, HHI, variações e declaração ao SICI; `territorio` = população, domicílios, penetração e mercado não visto; `cetic` = estimativas da TIC Domicílios para a UF, do Arandurapé, com erro-padrão, e `demanda_oferta` = banda larga fixa declarada pelas famílias × acessos do SICI; `erbs` = estações do SMP licenciadas. `fust` = compromissos do FUST na UF. `qualidade` = RQUAL por prestadora (último ano) e `reclamacoes` = reclamações por ano e serviço na UF. `consumidor` = empresas com reclamações finalizadas na UF no Consumidor.gov.br. `transito` = concentração dos provedores de trânsito inferidos dos ASNs com sede na UF. `radar` = agregado derivado do Cloudflare Radar (IPv6, tráfego e BGP) dos ASNs da UF. `exposicao` = agregado derivado de serviços expostos observados pelo Shodan nos ASNs da UF lidos."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    sigla = uf.strip().upper()
    if sigla not in UFS:
        raise HTTPException(404, f"UF '{uf}' desconhecida.")
    extras = _blocos(include, _INCLUDES_PERFIL)
    perfil = store.perfil_uf(date_str, sigla, _blocos(blocos, _BLOCOS_UF))
    from api.routes.historico import bloco_historico, pede_historico
    if (completo := pede_historico(extras)) is not None:
        perfil = {**perfil, "historico": bloco_historico(request, "uf", sigla, completo)}
    if extras and "rede_territorio" in extras:
        from api.services.rede_territorio import bloco_uf as rede_uf
        perfil = {**perfil, "rede_territorio": rede_uf(store.rede_territorio_doc(date_str), sigla)}
    if extras and "mercado_grupos" in extras:
        from api.services.sici_indicadores import bloco_mercado_uf
        perfil = {**perfil, "mercado_grupos": bloco_mercado_uf(store.mercado_grupos(date_str), sigla)}
    if extras and "indicadores" in extras:
        from api.services.sici_indicadores import bloco_uf
        perfil = {**perfil, "indicadores": bloco_uf(store.sici_indicadores(date_str), store.sem_declaracao_sici(date_str), sigla)}
    if extras and "territorio" in extras:
        from api.services.territorio import bloco_uf as terr_uf
        perfil = {**perfil, "territorio": terr_uf(store.territorio_doc(date_str), sigla)}
    if extras and "cetic" in extras:
        from api.services.cetic import bloco_uf as cetic_uf
        from api.services.demanda_oferta import bloco_uf as do_uf
        perfil = {**perfil, "cetic": cetic_uf(store.cetic_uf_doc(date_str), sigla), "demanda_oferta": do_uf(store.demanda_oferta_doc(date_str), sigla)}
    if extras and "erbs" in extras:
        from api.services.erbs import bloco_uf as erbs_uf
        perfil = {**perfil, "erbs": erbs_uf(store.erbs_doc(date_str), sigla)}
    if extras and "fust" in extras:
        from api.services.fust import bloco_uf as fust_uf
        perfil = {**perfil, "fust": fust_uf(store.fust_doc(date_str), sigla)}
    if extras and "prontidao" in extras:
        from api.services.prontidao import bloco_uf as prontidao_uf
        perfil = {**perfil, "prontidao": prontidao_uf(store.prontidao_doc(date_str), sigla)}
    if extras and "qualidade" in extras:
        from api.services.qualidade import bloco_uf as qualidade_uf
        perfil = {**perfil, "qualidade": qualidade_uf(store.rqual_doc(date_str), sigla)}
    if extras and "reclamacoes" in extras:
        from api.services.qualidade import bloco_reclamacoes_uf
        perfil = {**perfil, "reclamacoes": bloco_reclamacoes_uf(store.reclamacoes_doc(date_str), sigla)}
    if extras and "transito" in extras:
        from api.services.transito import bloco_uf as transito_uf
        perfil = {**perfil, "transito": transito_uf(store.transito_ufs_doc(date_str), sigla)}
    if extras and "radar" in extras:
        from api.services.radar import bloco_uf as radar_uf
        perfil = {**perfil, "radar": radar_uf(store.radar_doc(date_str), sigla)}
    if extras and "exposicao" in extras:
        from api.services.exposicao import bloco_uf as exposicao_uf
        perfil = {**perfil, "exposicao": exposicao_uf(store.exposicao_doc(date_str), sigla)}
    if extras and "consumidor" in extras:
        from api.services.consumidor import bloco_uf as consumidor_uf
        perfil = {**perfil, "consumidor": consumidor_uf(store.consumidor_doc(date_str), sigla)}
    return _projetar(perfil, fields)
