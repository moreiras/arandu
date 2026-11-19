# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoints de snapshots — GET /snapshots e GET /snapshots/{date}.

Lista os snapshots disponíveis e retorna os metadados (summary.json e
manifest.json) de um snapshot específico.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from api.schemas import SnapshotListResponse, SnapshotDetailResponse
from api.store import Store

router = APIRouter()


@router.get(
    "/snapshots",
    response_model=SnapshotListResponse,
    summary="Listar snapshots disponíveis",
    description="""
Retorna todas as datas de snapshot disponíveis, em ordem cronológica.

Cada snapshot corresponde a uma rodada completa do pipeline de coleta e análise.
Use a data retornada em `latest` como valor padrão para os demais endpoints
quando não quiser especificar `?date=`.
""",
)
def list_snapshots(request: Request) -> dict:
    store: Store = request.app.state.store
    dates = store.list_snapshots()
    return {
        "count": len(dates),
        "latest": dates[-1] if dates else None,
        "snapshots": dates,
    }


# Detalhe enriquecido por snapshot (imutável) — ver get_snapshot.
_DETAIL_CACHE: dict[str, dict] = {}


@router.get(
    "/snapshots/{date_str}",
    response_model=SnapshotDetailResponse,
    summary="Detalhes de um snapshot",
    description="""
Retorna o `summary` e o `manifest` de um snapshot específico.

**summary** — estatísticas globais: total de ASNs BR, cobertura IPv6, prefixos `registro_br`, etc.

**manifest** — metadados do pipeline: versão, IXPs coletados/falhos, checksums SHA-256
de todos os artefatos publicados.
""",
)
def get_snapshot(date_str: str, request: Request) -> dict:
    store: Store = request.app.state.store
    # A data vira nome de pasta: fora de AAAA-MM-DD é 404 sem tocar o disco (o fuzz achou um 500 com 300 bytes: "File name too long").
    if not Store._DATE_RE.fullmatch(date_str):
        raise HTTPException(404, f"Snapshot '{date_str[:40]}' não encontrado")
    # O snapshot é imutável: o resumo enriquecido (várias passagens sobre o índice de
    # ASNs e das operadoras) é calculado uma vez por data. Refazer a cada
    # chamada custaria ~0,6 s de CPU com o GIL preso, atrasando as demais rotas da API).
    cached = _DETAIL_CACHE.get(date_str)
    if cached is not None:
        return cached
    from api import snapshot_detail

    # Preferido: o detalhe calculado pelo pipeline (alguns KiB). Sem ele (snapshots anteriores), recalcula.
    detail = snapshot_detail.read_sidecar(store.base, date_str)
    if detail is None:
        detail = snapshot_detail.compute_detail(store, date_str)
    else:
        detail.pop("versao", None)
    if detail is None:
        raise HTTPException(404, f"Snapshot '{date_str}' não encontrado")
    if len(_DETAIL_CACHE) >= 8:
        _DETAIL_CACHE.pop(next(iter(_DETAIL_CACHE)))
    _DETAIL_CACHE[date_str] = detail
    return detail
