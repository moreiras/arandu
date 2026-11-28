# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Área de influência observada dos PTTs do IX.br: `GET /ixps/area-influencia` (país, por município) e `GET /ixps/{code}/area-influencia`.

Lê só `territorio/area_influencia_ptt.json.gz`; snapshot sem o arquivo devolve 404 (204 com `?opcional=1`), nunca calcula na hora.
Registrado antes do roteador de `/ixps`: `/ixps/area-influencia` não pode cair em `/ixps/{code}`."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import area_influencia as ai

router = APIRouter()

_DESCRICAO_COMUM = """
**Inferência, não cobertura de rede.** Os acessos de banda larga fixa declarados ao SICI por município e operadora (CNPJ) são atribuídos ao PTT mais próximo entre os que a operadora enxerga na visão
(`diretos`: ASN com sessão própria no PTT e prefixo próprio visto nele; `todos`: ASN com prefixo próprio visto no PTT, com sessão ou levado por outro participante). A distância é em linha reta do centroide do município
ao PIX mais próximo do PTT. Por PTT há ainda duas visões de **alcance** (`alcance_diretos`, `alcance_todos`), sem disputa entre PTTs: todo município onde as operadoras do PTT declaram acessos entra no alcance dele,
mesmo que exista PTT mais próximo, e um município pode estar no alcance de vários PTTs. Não há exclusão de operadoras, e o produto não traz nome de operadora, só contagens. O mês do SICI difere da data do snapshot. Faixas: 1 até o P50, 2 acima do P50 até o P80, 3 acima do P80.
"""


def _doc(request: Request, date: Optional[str]) -> tuple[str, dict]:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.area_influencia_doc(d)
    if not doc:
        raise HTTPException(404, f"Área de influência dos PTTs não publicada no snapshot {d}.")
    return d, doc


@router.get(
    "/ixps/area-influencia",
    summary="Área de influência observada dos PTTs, por município (país)",
    description="""
Para cada município, o PTT principal (o que recebe mais acessos do município), a faixa do município nesse PTT, os acessos atribuídos a ele e no município e o número de PTTs que recebem acessos do município,
na visão pedida (`visao`: `diretos` ou `todos`, padrão `todos`). Traz também o resumo de cada PTT na visão (P50, P80 e P90 da distância ponderada por acessos, mediana por operadora, faixas) e os PTTs com PIX
posicionado por aproximação. Os `municipios` são listas na ordem de `campos_municipio`. Cacheada por snapshot.
""" + _DESCRICAO_COMUM,
)
def area_influencia_nacional(request: Request, visao: Literal["diretos", "todos"] = Query("todos", description="`diretos` ou `todos`."), date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD).")) -> dict:
    _, doc = _doc(request, date)
    return ai.nacional(doc, visao)


@router.get(
    "/ixps/{code}/area-influencia",
    summary="Área de influência observada de um PTT",
    description="""
Para o PTT, nas quatro visões (`diretos`, `todos`, `alcance_diretos`, `alcance_todos`; ou só na pedida em `visao`): operadoras (CNPJs), municípios e acessos atribuídos; P50, P80 e P90 da distância em km (peso por acessos); a mediana por operadora (cada operadora conta 1,
outra população que o P50); municípios e acessos por faixa; e, por município, os acessos atribuídos e a faixa. `pix` diz quantos PIX têm coordenada, quantos foram posicionados no centroide do município do
endereço ou da sede, e os pontos usados no cálculo. Visão sem nenhuma operadora atribuída ao PTT vem `null`. Cacheada por snapshot.
""" + _DESCRICAO_COMUM,
)
def area_influencia_ptt(code: str, request: Request, visao: Optional[Literal["diretos", "todos", "alcance_diretos", "alcance_todos"]] = Query(None, description="`diretos`, `todos`, `alcance_diretos` ou `alcance_todos`; sem o parâmetro vêm as quatro."),
                        date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD).")) -> dict:
    d, doc = _doc(request, date)
    r = ai.por_ptt(doc, code, visao)
    if r is None:
        raise HTTPException(404, f"PTT '{code}' sem área de influência no snapshot '{d}'")
    return r
