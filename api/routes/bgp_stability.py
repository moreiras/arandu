# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoints de estabilidade BGP — GET /bgp/stability e GET /bgp/stability/{asn}/deep.

Serve os dados de análise de updates BGP dos 7 dias anteriores ao snapshot:
distribuição de eventos por AS, série horária global, e diagnóstico aprofundado
dos ASes mais ruidosos.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()

# Resumos já calculados por snapshot (o documento completo tem ~40 MB).


@router.get(
    "/bgp-stability",
    summary="Análise de estabilidade de updates BGP — ASes BR ruidosos",
    description="""
Retorna análise de estabilidade de anúncios BGP para os ASes brasileiros nos
últimos 7 dias anteriores ao snapshot.

Identifica ASes ruidosos (muitos updates por prefixo por dia) e classifica o
padrão de ruído: flapper crônico, explosão pontual, oscilador de atributos ou
injeção de mais-específicos.

Inclui:
- `distribution.v4` e `distribution.v6`: histograma de eventos/prefixo/dia de todos os ASes BR
- `as_stability[]`: lista ordenada por `events_per_prefix_per_day` (descendente), com
  métricas por período (7 dias) e por dia, e os prefixos mais instáveis de cada AS.
""",
    tags=["bgp-stability"],
)
def get_bgp_stability(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    from api.store import Store
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    data = store.bgp_stability(date_str)
    if data is None:
        raise HTTPException(
            404,
            "bgp_stability não disponível para este snapshot. "
            "Execute: python -m sources.bgp_updates_routeviews.collect --date "
            + date_str
            + " && python -m products.bgp_stability.build --date "
            + date_str,
        )
    return data


@router.get(
    "/bgp-stability/summary",
    summary="Resumo leve da estabilidade BGP por AS (eventos/prefixo/dia)",
    description="""
Versão enxuta de `/bgp-stability`: só `events_per_prefix_per_day` (total, v6 e v4) por
AS, o suficiente para a coluna de estabilidade da lista de ASes. O documento completo
tem ~40 MB; este tem algumas centenas de KB e é calculado uma vez por snapshot.
""",
    tags=["bgp-stability"],
)
def get_bgp_stability_summary(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    from api.store import Store
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    items = store.bgp_stability_resumo(date_str)
    if items is None:
        raise HTTPException(404, "bgp_stability não disponível para este snapshot.")
    return {"snapshot_date": date_str, "items": items}


@router.get(
    "/bgp-stability/overview",
    summary="Visão geral da estabilidade BGP: o que a página /bgp mostra, sem o documento inteiro",
    description="""
Período, `distribution`, `epppd_stats`, `hourly_global`, a contagem de ASes por categoria de ruído (`categorias`) e por severidade
(`severidades`, `medio_ou_maior`) e os 10 ASes mais ruidosos em `as_stability` (por `rank`, **sem** `hourly` nem `top_prefixes`).
`ordens[coluna][asc|desc]` dá os 10 primeiros ASNs da lista de severidade média ou maior ordenada por `rank`, `epppd`, `epppd_v6`,
`epppd_v4` ou `flap` (prefixos com flap), e `as_stability_ordens` traz os que não estão em `as_stability`, no mesmo formato.
Algumas dezenas de KB em vez dos ~46 MB de `/bgp-stability`, que continua existindo para a lista completa.
""",
    tags=["bgp-stability"],
)
def get_bgp_stability_overview(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    from api.store import Store
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    out = store.bgp_stability_visao_geral(date_str)
    if out is None:
        raise HTTPException(404, "bgp_stability não disponível para este snapshot.")
    return out


@router.get(
    "/bgp-stability/asn/{asn}",
    summary="Estabilidade BGP de um AS: snapshot ativo, diagnóstico e séries horárias das últimas semanas",
    description="""
O que a página de um AS usa da estabilidade BGP, sem baixar o documento inteiro (~46 MB) nem o histórico de **todos** os
ASes (~27 MB): `stability` (o AS no snapshot ativo; `null` se não está na análise), `epppd_stats` e `timestamps` da semana,
`diagnosis` (diagnóstico aprofundado, se houver) e `weeks` (séries horárias `ann`/`wd`/`attr_upd` do AS nas últimas
`weeks` semanas, da mais antiga à mais recente; semanas sem série do AS são omitidas). 404 se o snapshot não tem a análise.
""",
    tags=["bgp-stability"],
)
def get_bgp_stability_asn(
    request: Request,
    asn: int,
    date: Optional[str] = Query(None, description="Data do snapshot mais recente (YYYY-MM-DD)."),
    weeks: int = Query(6, ge=1, le=12, description="Número de semanas de série horária."),
) -> dict:
    from api.store import Store
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    out = store.bgp_stability_asn(date_str, asn, weeks)
    if out is None:
        raise HTTPException(404, "bgp_stability não disponível para este snapshot.")
    return out


@router.get(
    "/bgp-stability/history",
    summary="Histórico de estabilidade BGP — últimas N semanas",
    description="""
Retorna os dados de `bgp-stability` para os últimos `weeks` snapshots disponíveis
até (e incluindo) a data informada, em ordem cronológica crescente.

Cada snapshot cobre uma janela de 7 dias, então isso permite montar séries
horárias contínuas de várias semanas. Snapshots ausentes (sem bgp_stability.json
publicado) são simplesmente omitidos da resposta.
""",
    tags=["bgp-stability"],
)
def get_bgp_stability_history(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot mais recente (YYYY-MM-DD)."),
    weeks: int = Query(6, ge=1, le=12, description="Número de snapshots semanais a incluir."),
    resumo: bool = Query(False, description="1.4.2.4: cada semana vem só com `data.hourly_global` (o gráfico de atividade global), sem os ASes: alguns KB em vez de ~13 MB."),
) -> dict:
    from api.store import Store
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    if resumo:
        return {"weeks": store.bgp_stability_historico_resumo(date_str, weeks)}
    return {"weeks": store.bgp_stability_history(date_str, weeks)}
