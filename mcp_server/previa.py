# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Prévia do MCP sem chave, equivalente à do site sem login.

No site, quem não tem login vê listas até `PREVIEW_LIMIT` itens, só a primeira página, só os dois snapshots mais recentes e o histórico só a
partir deles (`api/auth/access_policy.py`). O MCP sem chave servia tudo. Aqui cada tool é envolvida e, para o cliente anônimo:

  * `limit` pedido acima da prévia, `page` > 1, `offset` > 0 ou `date` fora dos dois snapshots recentes → erro que diz como ter a chave;
  * `limit` padrão da tool acima da prévia → reduzido à prévia (o cliente não pediu mais);
  * histórico (`historico_serie`, `historico_mudancas`, `historico_acessos` e a coleção `eventos`/`series_asn` do `query`) só com `de`/`date`
    a partir do snapshot recente mais antigo.

Quem chega com chave válida (o `ChaveMiddleware` marca `access_tier=user` no escopo) ou de IP na allowlist (`ALLOWED_IPS`, como no site) não
tem restrição. Sem pedido HTTP (stdio local, testes que chamam a tool direto) também não: não há cliente remoto a limitar.
"""
from __future__ import annotations

import functools
import inspect
import os
from typing import Callable, Optional, Sequence


from api.auth.previa import COLECOES_HISTORICO, COMO_TER_CHAVE, HISTORICO, PreviaExcedida, conferir  # noqa: F401  (reexporta)


def _allowlist() -> list[str]:
    return [e.strip() for e in os.environ.get("ALLOWED_IPS", "").split(",") if e.strip()]


def nivel(mcp) -> str:
    """'local' (sem pedido HTTP), 'user' (chave válida), 'allowed' (IP na allowlist) ou 'anon'."""
    try:
        req = mcp.get_context().request_context.request
    except (ValueError, LookupError, AttributeError):
        return "local"
    if req is None:
        return "local"
    estado = (getattr(req, "scope", None) or {}).get("state") or {}
    if estado.get("access_tier") == "user":
        return "user"
    lista = _allowlist()
    if lista:
        from api.auth.deps import ip_in_allowlist
        ip = (req.headers.get("x-real-ip") or (req.client.host if req.client else "")).split(",")[0].strip()
        if ip and ip_in_allowlist(ip, lista):
            return "allowed"
    return "anon"


def aplicar(mcp, datas_recentes: Callable[[], Sequence[str]]) -> int:
    """Envolve todas as tools registradas (inclusive os aliases ocultos). Devolve quantas."""
    tools = getattr(getattr(mcp, "_tool_manager", None), "_tools", None)
    if not isinstance(tools, dict):
        return 0
    n = 0
    for nome, tool in tools.items():
        fn = getattr(tool, "fn", None)
        if fn is None or getattr(fn, "_previa", False):
            continue
        sig = inspect.signature(fn)

        # Tudo o que a envolvente usa entra como argumento padrão: uma closure sobre variável do laço veria a ÚLTIMA tool
        # (tools passariam sem prévia ou receberiam parâmetros de outra tool).
        def preparar(a: tuple, kw: dict, nome=nome, sig=sig) -> tuple[tuple, dict]:
            if nivel(mcp) != "anon":
                return a, kw
            try:
                b = sig.bind_partial(*a, **kw)
            except TypeError:
                return a, kw                                  # a validação da própria tool responde
            recebidos = dict(b.arguments)
            # O FastMCP passa todos os campos, inclusive os que ficaram no padrão: "explícito" é o que difere do padrão da tool.
            explicitos = {k for k, v in recebidos.items() if k in sig.parameters and v != sig.parameters[k].default}
            b.apply_defaults()
            novos = conferir(nome, {**b.arguments, "__explicitos__": explicitos}, list(datas_recentes() or []))
            saida = {k: novos.get(k, v) for k, v in recebidos.items()}
            if "limit" in novos and "limit" not in recebidos and novos["limit"] != b.arguments.get("limit"):
                saida["limit"] = novos["limit"]               # padrão da tool acima da prévia, reduzido
            return (), saida

        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def envoltorio(*a, __fn=fn, __preparar=preparar, **kw):
                a, kw = __preparar(a, kw)
                return await __fn(*a, **kw)
        else:
            @functools.wraps(fn)
            def envoltorio(*a, __fn=fn, __preparar=preparar, **kw):
                a, kw = __preparar(a, kw)
                return __fn(*a, **kw)
        envoltorio._previa = True                             # type: ignore[attr-defined]
        for attr in ("_usage_logged",):
            if getattr(fn, attr, False):
                setattr(envoltorio, attr, True)
        tool.fn = envoltorio
        n += 1
    return n

