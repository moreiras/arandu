# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Qualidade e reclamações da Anatel.

  * `GET /qualidade/resumo` — indicadores do RQUAL, prestadoras (com a ligação ao CNPJ) e limites.
  * `GET /qualidade/prestadoras?servico=&indicador=&uf=` — último valor de cada prestadora num indicador (alfabético, sem ranking).
  * `GET /qualidade/serie?servico=&indicador=&prestadora=&uf=` — série mensal nacional ou anual da UF.
  * `GET /qualidade/mapa?servico=&indicador=` — um indicador em todos os municípios medidos (média das prestadoras) e a faixa em relação às referências da Anatel, para o mapa.
  * `GET /qualidade/municipios/{ibge}` — último resultado de cada indicador no município, por prestadora.
  * `GET /reclamacoes/resumo`, `GET /reclamacoes/marcas`, `GET /reclamacoes/municipios/{ibge}` — reclamações agregadas, a ligação marca → CNPJ e a taxa por mil acessos.
  * `include=qualidade` e `include=reclamacoes` nos perfis de operadora, município e UF; coleções `qualidade_uf` e `reclamacoes_marca` do `/query`.

Fatos medidos ou declarados, com fonte e período; sem ranking nem veredito. Reclamações só agregadas.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import qualidade as q

router = APIRouter()


def _doc_de(request: Request, date: Optional[str], nome: str, rotulo: str) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = getattr(store, f"{nome}_doc")(d)
    if not doc:
        raise HTTPException(404, f"{rotulo} não publicado(s) no snapshot {d}.")
    return doc


def nomes_de(request: Request, date: Optional[str], cnpjs) -> dict[str, str]:
    """CNPJ → nome de exibição (mesma cadeia da página de operadora), para a tela mostrar a empresa e não a raiz do CNPJ; CNPJ sem nome conhecido fica de fora."""
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        return {}
    unicos = sorted({c for c in cnpjs if c})
    nomes = {c: store._display_name_for_cnpj(d, c) for c in unicos}
    return {c: n for c, n in nomes.items() if n and n != c}


def _municipio(request: Request, date: Optional[str], ibge: str, nome: str, rotulo: str) -> tuple[dict, dict, str]:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    cod = ibge.strip()
    nacional = getattr(store, f"{nome}_doc")(d)
    if not nacional:
        raise HTTPException(404, f"{rotulo} não publicado(s) no snapshot {d}.")
    uf = q.uf_do_municipio(nacional, cod)
    por_uf = getattr(store, f"{nome}_municipios_uf")(d, uf) if uf else None
    if not por_uf:
        raise HTTPException(404, f"Município {cod} sem {rotulo} no snapshot {d}.")
    return nacional, por_uf, cod


@router.get(
    "/qualidade/resumo",
    summary="Qualidade (RQUAL da Anatel): indicadores, prestadoras e limites",
    description="""
Indicadores de qualidade do RQUAL apurados pela Anatel por município, prestadora e serviço (banda larga fixa, telefonia fixa e móvel), desde 2022: a lista de indicadores com unidade e valores de
referência da própria Anatel, as prestadoras cobertas (**só as grandes**; a ausência de uma empresa não diz nada sobre ela) e a ligação prestadora → raiz do CNPJ (tabela curada). **Sem ranking nem veredito**; veja `limites`.
""",
)
def qualidade_resumo(request: Request, date: Optional[str] = Query(None)) -> dict:
    r = q.resumo(_doc_de(request, date, "rqual", "RQUAL"))
    return {**r, "nomes": nomes_de(request, date, (c for p in r.get("prestadoras", []) for c in p.get("cnpjs_matriz") or []))}


@router.get(
    "/qualidade/prestadoras",
    summary="Último valor de cada prestadora em um indicador do RQUAL",
    description="""
Para um `servico` (Banda Larga Fixa, Telefonia Fixa ou Telefonia Móvel) e um `indicador` (código do `/qualidade/resumo`, ex.: `IND4`): o último valor de cada prestadora, nacional (último mês: média
dos municípios medidos, média ponderada pelas medidas e mediana) ou, com `uf`, o último ano daquela UF. Ordem alfabética; **não há ordenação por melhor ou pior**.
""",
)
def qualidade_prestadoras(
    request: Request, servico: str = Query(..., description="Banda Larga Fixa, Telefonia Fixa ou Telefonia Móvel."), indicador: str = Query(..., description="Código do indicador, ex.: IND4."),
    uf: Optional[str] = Query(None, min_length=2, max_length=2), date: Optional[str] = Query(None),
) -> dict:
    try:
        return q.prestadoras(_doc_de(request, date, "rqual", "RQUAL"), servico, indicador, uf)
    except q.QualidadeErro as x:
        raise HTTPException(x.status, x.mensagem)


@router.get(
    "/qualidade/serie",
    summary="Série de um indicador do RQUAL: mensal nacional ou anual por UF",
    description="Série do `indicador` de um `servico`: mensal nacional por prestadora (municípios medidos, medidas, média, média ponderada e mediana) ou, com `uf`, anual daquela UF. `prestadora` restringe a uma.",
)
def qualidade_serie(
    request: Request, servico: str = Query(...), indicador: str = Query(...), prestadora: Optional[str] = Query(None, max_length=40), uf: Optional[str] = Query(None, min_length=2, max_length=2),
    date: Optional[str] = Query(None),
) -> dict:
    try:
        return q.serie(_doc_de(request, date, "rqual", "RQUAL"), servico, indicador, prestadora, uf)
    except q.QualidadeErro as x:
        raise HTTPException(x.status, x.mensagem)


@router.get(
    "/qualidade/municipios/{ibge}",
    summary="Qualidade no município: último resultado de cada indicador, por prestadora",
    description="""
Para cada prestadora e serviço medidos no município, o último resultado numérico de cada indicador (mês, resultado, número de medidas e de coletores, erro amostral, intervalo e a coluna "Estatística"
da fonte). Poucas medidas significam resultado incerto: veja o erro amostral e o intervalo. 404 se o município não tem RQUAL no snapshot.
""",
)
def qualidade_municipio(request: Request, ibge: str, date: Optional[str] = Query(None)) -> dict:
    nacional, por_uf, cod = _municipio(request, date, ibge, "rqual", "RQUAL")
    r = q.municipio(por_uf, cod, nacional)
    if r is None:
        raise HTTPException(404, f"Município {ibge} sem resultado do RQUAL.")
    return r


@router.get(
    "/reclamacoes/resumo",
    summary="Reclamações na Anatel: totais por ano e serviço, assuntos e cobertura da ligação marca → CNPJ",
    description="""
Reclamações de consumidores registradas na Anatel desde 2015 (arquivo legado até 2020 e `contexto` de 2020 em diante): totais por ano e serviço, por UF, os assuntos do último ano, a regra da taxa por
mil acessos e **quanto das reclamações está ligado a um CNPJ** (tabela curada do Arandurapé mais nome fantasia único). Só agregados: nenhum texto livre nem dado de quem reclamou. Sem ranking de empresas.
""",
)
def reclamacoes_resumo(request: Request, date: Optional[str] = Query(None)) -> dict:
    return q.reclamacoes_resumo(_doc_de(request, date, "reclamacoes", "Reclamações"))


@router.get(
    "/reclamacoes/marcas",
    summary="Reclamações por marca no ano, com a ligação ao CNPJ e a taxa por mil acessos",
    description="""
Uma linha por marca (nome que o consumidor escolheu) no `ano` (padrão: o último): reclamações por serviço, raízes de CNPJ ligadas (`casamento` = curada ou automatico; sem CNPJ aparece vazio) e as
taxas por mil acessos (SCM e SMP, janela de 12 meses ÷ acessos do SICI, só com volume suficiente; veja `motivo_sem_taxa`). `q` busca no nome. **Ordem alfabética: a ordenação por volume ou por taxa não é
oferecida sem metodologia aprovada**. "NÃO LOCALIZEI A MINHA EMPRESA" e "Outros" não identificam ninguém.
""",
)
def reclamacoes_marcas(
    request: Request, servico: Optional[str] = Query(None, description="SCM, SMP_Pós, SMP_Pré, STFC, SeAC ou Outros."), ano: Optional[int] = Query(None, ge=2015, le=2100), q_: Optional[str] = Query(None, alias="q", max_length=80),
    com_cnpj: Optional[bool] = Query(None, description="Só marcas com (true) ou sem (false) CNPJ ligado."), date: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=500), page: int = Query(1, ge=1),
) -> dict:
    try:
        r = q.marcas(_doc_de(request, date, "reclamacoes", "Reclamações"), servico, ano, q_, com_cnpj, limit, (page - 1) * limit)
        return {**r, "nomes": nomes_de(request, date, (c for m in r["items"] for c in m.get("cnpjs_matriz") or []))}
    except q.QualidadeErro as x:
        raise HTTPException(x.status, x.mensagem)


@router.get(
    "/reclamacoes/municipios/{ibge}",
    summary="Reclamações no município por ano, serviço e marca (últimos 3 anos)",
    description="Reclamações do município nos últimos 3 anos da fonte, por serviço e marca, e por 100 mil habitantes (população estimada do IBGE). Só agregados. 404 se não há reclamações no município.",
)
def reclamacoes_municipio(request: Request, ibge: str, date: Optional[str] = Query(None)) -> dict:
    nacional, por_uf, cod = _municipio(request, date, ibge, "reclamacoes", "Reclamações")
    r = q.reclamacoes_municipio(por_uf, cod, nacional)
    if r is None:
        raise HTTPException(404, f"Município {ibge} sem reclamações nos últimos anos da fonte.")
    return r


_MAPA_CACHE: dict = {}


@router.get(
    "/qualidade/mapa",
    summary="Um indicador do RQUAL em todos os municípios medidos, para o mapa",
    description="""
`{ibge: valor}` do último resultado do indicador, **média das prestadoras medidas no município** (ponderada pelas medidas quando todas as informam), com o número de prestadoras por município.
Quando o indicador tem as duas referências numéricas da Anatel, `faixas` diz se o valor está acima da superior, entre as duas ou abaixo da inferior. Não diz "melhor" nem "pior" (o sentido depende do
indicador), não nomeia empresa e só cobre os municípios medidos nas grandes prestadoras. Mesmos `limites` e datas das demais rotas de qualidade.
""",
)
def qualidade_mapa(request: Request, date: Optional[str] = Query(None), servico: str = Query(..., description="Banda Larga Fixa | Telefonia Fixa | Telefonia Móvel"), indicador: str = Query(..., description="Código do indicador (ver /qualidade/resumo).")) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.rqual_doc(d)
    if not doc:
        raise HTTPException(404, f"RQUAL não publicado no snapshot {d}.")
    chave = (d, servico, indicador)
    if chave not in _MAPA_CACHE:
        try:
            ufs = sorted(set(doc.get("municipios_uf", {}).values()))
            _MAPA_CACHE[chave] = q.mapa_municipios(doc, {u: store.rqual_municipios_uf(d, u) or {} for u in ufs}, servico, indicador)
        except q.QualidadeErro as e:
            raise HTTPException(e.status, e.mensagem)
        while len(_MAPA_CACHE) > 24:
            _MAPA_CACHE.pop(next(iter(_MAPA_CACHE)))
    return _MAPA_CACHE[chave]
