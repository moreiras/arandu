# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tools de histórico do MCP: a evolução no tempo e o que mudou entre snapshots, sobre `data/history/`.

Duas tools cobrem o histórico (o número de tools visíveis tem teto no T5): `historico_serie` (ASN, PTT, operadora, UF e Brasil, com `metrica` para a
tendência) e `historico_mudancas` (eventos, resumo e diferença entre duas datas). Mesmo serviço da API REST (`api/services/historico.py`)."""
from __future__ import annotations

from typing import Optional

from api.repos.historico import HistoricoRepo
from api.services import historico as h
from mcp_server.contexto import _store, mcp

_repo: Optional[HistoricoRepo] = None


def _historico() -> HistoricoRepo:
    global _repo
    if _repo is None:
        _repo = HistoricoRepo(_store.base)
    return _repo


def _chama(fn, *a, **kw):
    try:
        return fn(_historico(), *a, **kw)
    except h.HistoricoErro as e:
        # nomes dos parâmetros da REST (`from`, `to`, `a`, `b`) trocados pelos do MCP: "a deve ser…" era incompreensível
        msg = e.mensagem
        for rest, mcp_nome in (("`from`", "`de`"), ("`to`", "`ate`"), ("`a`", "`comparar`"), ("`b`", "`ate`")):
            msg = msg.replace(rest, mcp_nome)
        raise ValueError(msg) from None


@mcp.tool()
def historico_serie(
    escopo: str,
    metrica: Optional[str] = None,
    metrics: Optional[str] = None,
    de: Optional[str] = None,
    ate: Optional[str] = None,
) -> dict:
    """Série histórica de uma entidade: uma linha por snapshot com histórico. Cite as datas dos pontos e quantos snapshots existem.

    `escopo`: `asn:28571`, `ixp:sp`, `operadora:<cnpj de 14 dígitos>`, `uf:SP` ou `brasil` (soma das UFs; UF = sede da organização, não a dos
    usuários). Sem `metrica`, devolve as linhas inteiras (`metrics` escolhe colunas de ASN: users, prefixes_v4, ixps, roa, rpki, alertas…).
    Com `metrica` (ex.: `users`, `p4`, `n_roa`, `n_asns`), devolve só esse valor por data e a variação do primeiro ao último ponto (tendência).
    Usuários são estimativas da APNIC; nas séries de operadora e UF, `users_ma4` é a média dos últimos 28 dias. Coluna ausente = sem dado
    naquele snapshot (ex.: provedores antes do bloco de relações), nunca zero. O histórico começou a ser guardado em 2026-10 e pode ter poucos pontos.

    Args:
        escopo: asn:N | ixp:código | operadora:cnpj | uf:XX | brasil.
        metrica: uma coluna para a tendência (opcional).
        metrics: colunas ou apelidos de ASN, separados por vírgula (só com asn:N e sem `metrica`).
        de: data inicial (AAAA-MM-DD).
        ate: data final (AAAA-MM-DD).
    """
    if metrica:
        return _chama(h.tendencia, escopo, metrica, de, ate)
    tipo, _, chave = escopo.partition(":")
    if tipo == "asn" and chave.isdigit():
        return _chama(h.serie_asn, int(chave), metrics, de, ate)
    if tipo == "ixp" and chave:
        return _chama(h.serie_ixp, chave, de, ate)
    if tipo == "operadora" and chave:
        return _chama(h.serie_operadora, chave, de, ate)
    if tipo == "uf" and chave:
        return _chama(h.serie_uf, chave, de, ate)
    if escopo == "brasil":
        raise ValueError("escopo 'brasil' exige `metrica` (ex.: users, p4, n_asns)")
    raise ValueError("escopo deve ser asn:N, ixp:código, operadora:cnpj, uf:XX ou brasil")


@mcp.tool()
def historico_mudancas(
    de: Optional[str] = None,
    ate: Optional[str] = None,
    tipo: Optional[str] = None,
    uf: Optional[str] = None,
    asn: Optional[int] = None,
    estado: str = "confirmado",
    limit: int = 50,
    resumo: bool = False,
    comparar: Optional[str] = None,
) -> dict:
    """O que mudou entre snapshots: eventos observados (ASN novo ou sumido, entrada ou saída de PTT, mudança de origem de prefixo, ROA/ASPA, RPKI
    inválido, outorga nova ou baixa, alerta novo ou resolvido). Cada evento é uma **diferença observada**, sem causa nem intenção: não afirme
    culpa nem motivo. `estado`: `confirmado` (padrão; o novo estado persistiu pela janela), `pendente`, `revertido` ou `todos`.

    Eventos de provedor (`provedor_novo`, `provedor_perdido`) vêm de uma inferência (ARC v1), saem com `natureza: "inferido"` e variam entre
    snapshots: diga "provável" e prefira não citá-los como fato. `resumo=True` devolve só as contagens por tipo e estado. `comparar=AAAA-MM-DD`
    devolve a variação agregada (Brasil) entre essa data e `ate` (padrão: o snapshot com histórico mais recente), com o resumo dos eventos entre elas.

    Args:
        de: data inicial (AAAA-MM-DD).
        ate: data final (AAAA-MM-DD).
        tipo: tipos separados por vírgula (ex.: asn_novo,mudanca_origem,ixp_entrada).
        uf: sigla da UF (eventos de ASN).
        asn: só eventos deste ASN.
        estado: confirmado | pendente | revertido | todos.
        limit: máximo de eventos (padrão 50, até 500).
        resumo: só as contagens.
        comparar: data para comparar com `ate`.
    """
    if comparar:
        repo = _historico()
        final = ate or (repo.datas() or [None])[-1]
        if final is None:
            raise ValueError("Ainda não há snapshot com histórico.")
        return _chama(h.diferenca, comparar, final)
    if resumo:
        return _chama(h.mudancas_resumo, de, ate)
    return _chama(h.mudancas, de, ate, tipo, uf, asn, estado, max(1, min(limit, 500)), 0)
