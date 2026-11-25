# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Penetração de banda larga fixa e mercado não visto.

  * `GET /territorio/resumo` — agregados do país (ou de uma UF) por distância ao PTT, para a síntese de `/municipios`.
  * `GET /territorio/ranking` — municípios por penetração, mercado não visto, população, domicílios, acessos ou distância ao PTT mais próximo;
    `sem_ptt_proximo=true` lista as cidades a mais de 100 km de um PTT.

Penetração = acessos fixos declarados (SICI) ÷ domicílios do Censo 2022 projetados pelo crescimento de domicílios da UF (PNAD). O mercado não visto é uma ESTIMATIVA (inclui quem usa só o celular); toda resposta traz as
fórmulas e as limitações. Rankings de dado declarado ou medido, sem juízo (política editorial). A prévia (limit ≤ 100, página 1) é aberta na área avançada.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import territorio as t

router = APIRouter()


@router.get(
    "/territorio/ranking",
    summary="Municípios por penetração, mercado não visto ou distância ao PTT",
    description=f"""
Municípios ordenados por `campo` ({', '.join(t.CAMPOS)}). `uf` restringe; `sem_ptt_proximo=true` mantém só os a mais de 100 km de um PTT (linha reta do
centróide); `min_domicilios` evita o ruído de municípios muito pequenos. Cada linha traz população, domicílios, acessos, penetração, o não visto estimado e o PTT mais próximo (`ptt_proximo`, `ptt_proximo_nome`) com o PIX, o local de interconexão, mais próximo (`pix_proximo`).
O `nao_visto` é max(0, domicílios projetados × taxa de internet da UF − acessos de pessoa física): estimativa que inclui quem usa só o celular (PNAD). Fórmulas e limites vêm na resposta.
""",
)
def territorio_ranking(
    request: Request, date: Optional[str] = Query(None), campo: str = Query("penetracao"), uf: Optional[str] = Query(None),
    asc: bool = Query(False), sem_ptt_proximo: Optional[bool] = Query(None), min_domicilios: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=500), page: int = Query(1, ge=1),
) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.territorio_doc(d)
    if not doc:
        raise HTTPException(404, f"Penetração não publicada no snapshot {d}.")
    try:
        return t.ranking(doc, store.territorio_linhas(d), campo, uf, asc, sem_ptt_proximo, min_domicilios, limit, (page - 1) * limit)
    except t.TerritorioErro as e:
        raise HTTPException(e.status, e.mensagem)


@router.get(
    "/territorio/resumo",
    summary="Agregados por distância ao PTT mais próximo, para o país ou uma UF",
    description="""
Para o país (ou `uf`): quantos municípios, habitantes estimados, domicílios projetados e acessos fixos declarados ficam a mais de 100 km em linha reta de um PTT do IX.br e quantos ficam
até 100 km, com a razão de acessos por domicílio projetado de cada grupo e as contagens de municípios com penetração calculada, abaixo do porte mínimo e com mais acessos que domicílios.
É comparação de médias entre grupos, sem causa: renda, urbanização e densidade explicam parte da diferença. A distância é do centróide, não o trajeto de fibra. Mesmas datas e limites das
demais rotas de território.
""",
)
def territorio_resumo(request: Request, date: Optional[str] = Query(None), uf: Optional[str] = Query(None)) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.territorio_doc(d)
    if not doc:
        raise HTTPException(404, f"Território não publicado no snapshot {d}.")
    try:
        return t.resumo(doc, store.territorio_linhas(d), uf)
    except t.TerritorioErro as e:
        raise HTTPException(e.status, e.mensagem)


@router.get(
    "/territorio/mapa",
    summary="Um indicador normalizado de todos os municípios, para o mapa coroplético",
    description=f"""
`{{ibge: valor}}` de todos os municípios para um indicador **normalizado** (`indicador`: {', '.join(t.INDICADORES)}), com `rotulo`, `normalizacao` (a fórmula, por domicílio, por mil habitantes
ou distância) e as mesmas `formulas`, `limites` e datas das demais rotas de território. Município sem dado fica de fora (nunca zero). O desenho usa a malha municipal do IBGE (Fonte: IBGE).
""",
)
def territorio_mapa(request: Request, date: Optional[str] = Query(None), indicador: str = Query("penetracao")) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.territorio_doc(d)
    if not doc:
        raise HTTPException(404, f"Território não publicado no snapshot {d}.")
    try:
        from api.services import rede_territorio as rt
        if indicador in rt.INDICADORES:
            rede = store.rede_territorio_doc(d)
            if not rede:
                raise HTTPException(404, f"Rede no território não publicada no snapshot {d}.")
            return rt.mapa(rede, indicador)
        if indicador in t.EXTERNOS:
            fust = store.fust_doc(d)
            if not fust:
                raise HTTPException(404, f"FUST não publicado no snapshot {d}.")
            return t.mapa_fust(doc, fust)
        return t.mapa(doc, store.territorio_linhas(d), indicador)
    except t.TerritorioErro as e:
        raise HTTPException(e.status, e.mensagem)


@router.get(
    "/territorio/municipio/{ibge}/semelhantes",
    summary="Municípios do mesmo porte, com a posição do município entre eles",
    description="""
Municípios com domicílios projetados entre metade e o dobro dos do município (regra simples e declarada em `criterio`, não um modelo), os mais próximos em tamanho primeiro, com acessos, penetração,
fibra e distância ao PTT. `posicao` diz onde o município está entre os de mesmo porte em penetração e em fibra (1 = maior valor, sem juízo de bom ou ruim). Mesmas datas e limites das demais rotas de território.
""",
)
def territorio_semelhantes(ibge: str, request: Request, date: Optional[str] = Query(None), limit: int = Query(8, ge=1, le=12)) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.territorio_doc(d)
    if not doc:
        raise HTTPException(404, f"Território não publicado no snapshot {d}.")
    try:
        return t.semelhantes(doc, store.territorio_linhas(d), ibge, limit)
    except t.TerritorioErro as e:
        raise HTTPException(e.status, e.mensagem)


@router.get(
    "/territorio/rede",
    summary="IPv6 estimado, usuários atrás de ROV e dependência de trânsito, por UF e país",
    description="""
Resumo da rede no território: por UF e no país, os acessos em IPv6 **estimados** (acessos do SICI × adoção de IPv6 do AS, APNIC), os usuários estimados atrás de ASNs que validam ROV (APNIC IRoV × usuários)
e a parcela dos acessos cujas operadoras têm um único provedor de trânsito **inferido**. Toda linha traz a `cobertura` (parcela que entrou na estimativa) e a resposta traz `limites` e a suposição
(a adoção do AS vale igual em todos os municípios da operadora). Os valores por município vêm de `include=rede_territorio` no perfil do município e de `/territorio/mapa`.
""",
)
def territorio_rede(request: Request, date: Optional[str] = Query(None)) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.rede_territorio_doc(d)
    if not doc:
        raise HTTPException(404, f"Rede no território não publicada no snapshot {d}.")
    from api.services.rede_territorio import resumo
    return resumo(doc)


@router.get(
    "/territorio/infra-proximos",
    summary="Infraestrutura física e instalações do PeeringDB num raio em torno de um ponto",
    description="""
Para o ponto `lat`/`lon`: quantas feições das camadas leves do mapa passam a até `raio_km` (cabos submarinos, pontos de aterrissagem, enlaces terrestres da UIT e linhas de transmissão
de energia) e as `limit` mais próximas de cada uma, com a distância em km, a fonte e, nos enlaces, a contagem por `status` (por exemplo operacional ou planejado). Traz também as instalações
cadastradas no PeeringDB a até `raio_instalacoes_km`. Distância em linha reta até a geometria, com projeção local; as geometrias são aproximadas, não informam capacidade disponível nem
quem opera, e a instalação é cadastro autodeclarado. Proximidade de uma linha de energia ou de um cabo não indica que as redes locais a usam. Sem GeoJSON; rodovias ficam de fora (arquivo grande).
Mesma regra do `infra_proximos` do MCP.
""",
)
def territorio_infra_proximos(
    request: Request, lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180), date: Optional[str] = Query(None),
    raio_km: float = Query(50.0, ge=1, le=500), raio_instalacoes_km: float = Query(150.0, ge=1, le=500), limit: int = Query(3, ge=1, le=10),
) -> dict:
    from api.services import infra

    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    r = infra.resumo_infra(store, d, lat, lon, raio_km, list(infra.PADRAO), limit)
    for nome, item in r["camadas"].items():
        item["fonte"] = infra.FONTES[nome]
    instalacoes = infra.instalacoes_proximas(store.query_table(d, "facilities"), lat, lon, raio_instalacoes_km, limit)
    return {"snapshot_date": d, "ponto": {"lat": lat, "lon": lon}, "raio_km": raio_km, **r,
            "instalacoes": {**instalacoes, "fonte": "PeeringDB (cadastro autodeclarado)"}}
