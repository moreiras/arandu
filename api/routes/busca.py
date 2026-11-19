# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`GET /busca` — busca universal. A lógica e a privacidade do índice estão em `api/busca.py`."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api import busca
from api.store import Store

router = APIRouter()


@router.get(
    "/busca",
    summary="Busca universal: AS, operadora, grupo, município, UF, PTT, CDN, datacenter, prefixo e página",
    description="""
Procura uma consulta em todos os tipos de entidade do snapshot e devolve os acertos **agrupados por tipo**, cada um com título, detalhe e o
caminho (`url`) da página no site. Ignora acento e caixa.

Reconhecimento pela forma (aparece em `reconhecido`; o grupo vai para o topo):
- `64496` ou `AS64496` → o AS;
- `192.0.2.0/24`, `2001:db8::/32` ou um IP → a página do prefixo;
- CNPJ completo, com ou sem máscara → a operadora; 8 dígitos → as operadoras da raiz;
- 7 dígitos → município pelo código IBGE; sigla de 2 letras (`SP`) → UF.

O índice só tem dado de pessoa jurídica e de recursos de rede: sem contatos, e-mails, telefones nem pessoas físicas.
""",
)
def buscar(
    request: Request,
    q: str = Query(..., min_length=1, max_length=busca.TAMANHO_MAX_CONSULTA, description="Consulta: nome, número, CNPJ, prefixo, sigla…", examples=["vivo"]),
    limite: int = Query(busca.LIMITE_PADRAO, ge=1, le=busca.LIMITE_MAX, description="Máximo de itens por tipo"),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    out = busca.indice(store, date_str).buscar(q, limite)
    out["snapshot_date"] = date_str
    return out
