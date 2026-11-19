# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Rankings e omissão de declaração do SICI.

  * `GET /ranking/operadoras` — operadoras por acessos declarados, parcela, variação ou declínio, no país ou numa UF.
  * `GET /ranking/municipios` — municípios por acessos, concentração (HHI) ou variação.
  * `GET /omissao-sici` — outorgas SCM sem acessos declarados no mês (com os usuários estimados pela APNIC) ou CNPJs que pararam de declarar.

Rankings de dado declarado ou medido, sem juízo (política editorial). Cada resposta traz o critério, o mês de referência da declaração
e a data do snapshot. A prévia (limit ≤ 100, página 1) é aberta na área avançada; ampliar exige login (api/auth/access_policy.py).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import sici_indicadores as s

router = APIRouter()


def _docs(request: Request, date: Optional[str], omissao: bool = False) -> tuple[dict, Optional[dict]]:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    ind = store.sici_indicadores(d)
    om = store.omissao_sici(d)
    if not ind or (omissao and not om):
        raise HTTPException(404, f"Indicadores do SICI não publicados no snapshot {d}.")
    return ind, om


def _ok(fn, *a):
    try:
        return fn(*a)
    except s.IndicadoresErro as e:
        raise HTTPException(e.status, e.mensagem)


@router.get(
    "/ranking/operadoras",
    summary="Ranking de operadoras por acessos declarados ao SICI (fixo)",
    description=f"""
Operadoras (CNPJ) ordenadas por um critério de dado **declarado**: `acessos`, `share` (parcela dos acessos declarados),
`var_aa_pct`/`var_aa_abs` (12 meses), `var_mm_pct` (mês) ou `declinio` (meses seguidos de queda). Com `uf`, só os acessos naquela UF
(a variação é da operadora no país e fica de fora). `asc=true` inverte. Mês de referência e snapshot em toda resposta.
Ordens aceitas: {', '.join(s.ORDENS_OPERADORA)}. HHI e parcelas são sobre acessos declarados, não sobre receita.
""",
)
def ranking_operadoras(
    request: Request, date: Optional[str] = Query(None), uf: Optional[str] = Query(None, description="Sigla da UF dos acessos."),
    ordem: str = Query("acessos"), asc: bool = Query(False),
    limit: int = Query(25, ge=1, le=500), page: int = Query(1, ge=1),
) -> dict:
    ind, _ = _docs(request, date)
    return _ok(s.ranking_operadoras, ind, uf, ordem, asc, limit, (page - 1) * limit)


@router.get(
    "/ranking/municipios",
    summary="Ranking de municípios por acessos, concentração ou variação (fixo)",
    description=f"Municípios por `acessos`, `hhi` (concentração sobre acessos declarados), `n_operadoras` ou `var_aa_pct`. Traz o líder, o maior ganho e a maior perda em 12 meses. Ordens: {', '.join(s.ORDENS_MUNICIPIO)}.",
)
def ranking_municipios(
    request: Request, date: Optional[str] = Query(None), uf: Optional[str] = Query(None),
    ordem: str = Query("acessos"), asc: bool = Query(False),
    limit: int = Query(25, ge=1, le=500), page: int = Query(1, ge=1),
) -> dict:
    ind, _ = _docs(request, date)
    return _ok(s.ranking_municipios, ind, uf, ordem, asc, limit, (page - 1) * limit)


@router.get(
    "/omissao-sici",
    summary="Outorgas SCM sem acessos declarados ao SICI no mês",
    description="""
`tipo=outorga_sem_declaracao` (padrão): CNPJs com outorga SCM sem acessos declarados no mês de referência, em ordem de usuários estimados (APNIC) dos
ASNs do CNPJ, com a `classe` (`com_usuarios_apnic`, `sem_usuarios`, `nao_comparavel` = CNPJ sem ASN) e `grupo_declara` (outro CNPJ do grupo
declarou). `tipo=parou_de_declarar`: CNPJs que declararam antes e estão há 6 meses ou mais sem declarar. É a descrição de um fato sobre a
declaração, sem causa nem intenção. Metodologia na página Rankings.
""",
)
def omissao_sici(
    request: Request, date: Optional[str] = Query(None), tipo: str = Query("outorga_sem_declaracao"),
    uf: Optional[str] = Query(None), classe: Optional[str] = Query(None), grupo_declara: Optional[bool] = Query(None),
    limit: int = Query(25, ge=1, le=500), page: int = Query(1, ge=1),
) -> dict:
    ind, om = _docs(request, date, omissao=True)
    return _ok(s.omissao, om, ind, tipo, uf, classe, grupo_declara, limit, (page - 1) * limit)


@router.get(
    "/mercado/grupos",
    summary="Concentração por grupo econômico: faixas, municípios que mudam de faixa e HHI por UF",
    description="""
Resumo do cruzamento de mercado: o HHI do mercado fixo por UF **por CNPJ e por grupo econômico** (CNPJs do mesmo grupo contam como um) e quantos municípios mudam de faixa
(competitivo, moderado, concentrado) ao juntar os CNPJs do grupo. O grupo é **inferido** do quadro societário em comum e o HHI é sobre acessos declarados, não receita. A lista por município e a
sobreposição de concorrentes vêm de `include=mercado_grupos` nos perfis de município, UF e operadora.
""",
)
def mercado_grupos(request: Request, date: Optional[str] = Query(None)) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.mercado_grupos(d)
    if not doc:
        raise HTTPException(404, f"Cruzamento de mercado não publicado no snapshot {d}.")
    from api.services.sici_indicadores import resumo_mercado_grupos
    return resumo_mercado_grupos(doc)


@router.get(
    "/mercado/maiores",
    summary="Maiores do mercado fixo: posição mês a mês das maiores operadoras e as maiores empresas ou grupos",
    description="""
Dois recortes do SICI fixo: a **posição por acessos declarados**, mês a mês, das `n` maiores operadoras de hoje (a posição é entre todos os CNPJs que declararam) e as maiores
empresas-ou-grupos por acessos (o grupo econômico é **inferido** do quadro societário). Fatos declarados à Anatel; não é receita nem qualidade.
""",
)
def mercado_maiores(request: Request, date: Optional[str] = Query(None), n: int = Query(8, ge=3, le=12), meses: int = Query(24, ge=6, le=60)) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    chave = (id(store), d, n, meses)
    pronto = _MAIORES.get(chave)
    if pronto is not None:
        return pronto
    dados = store._load_sici(d)
    if not dados:
        raise HTTPException(404, f"SICI não publicado no snapshot {d}.")
    from api.services.sici_indicadores import maiores
    pronto = {"snapshot_date": d, **maiores(dados, store.grupos_societarios_overview(d), n, meses)}
    _MAIORES[chave] = pronto
    return pronto


# ~0,5 s de CPU por chamada medidos no ambiente de teste (2026-11-15), segurando o GIL: com 8 clientes simultâneos a rota sozinha levava o p95 da API a 755 ms.
# O resultado só depende de (snapshot, n, meses); n e meses são limitados pela validação (≤ 10 × 55 combinações), ~5 KB cada.
from api.store import _SafeLRU  # noqa: E402

_MAIORES = _SafeLRU(maxsize=128)
