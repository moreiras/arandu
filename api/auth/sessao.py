# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Sessão do usuário com conta: valida o JWT contra o cadastro de contas (conta ativa, "sair de todos os dispositivos").

Consulta o `contas.db` com cache de 5 s por conta, para o guard (que roda em toda requisição) não abrir o SQLite a cada vez.
JWT sem `cid` é resolvido pelo e-mail: a conta é criada no primeiro uso.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from api.auth import contas
from api.auth.jwt_utils import verify_token

_TTL_S = 5.0
_cache: dict[str, tuple[float, Optional[contas.Conta]]] = {}


def limpar_cache() -> None:
    _cache.clear()


def _conta(data_path: Path, chave: str, busca) -> Optional[contas.Conta]:
    agora = time.monotonic()
    hit = _cache.get(chave)
    if hit and agora - hit[0] < _TTL_S:
        return hit[1]
    c = busca()
    if len(_cache) > 5000:
        _cache.clear()
    _cache[chave] = (agora, c)
    return c


def usuario_do_cookie(token: Optional[str], secret: str, data_path: Path) -> Optional[dict]:
    """`{email, name, provider, conta_id}` se o JWT é válido e a conta está ativa; senão `None`."""
    if not token:
        return None
    payload = verify_token(token, secret)
    if not payload:
        return None
    cid = payload.get("cid")
    if cid:
        c = _conta(data_path, "id:" + cid, lambda: contas.por_id(data_path, cid))
    else:                                                   # sessão sem `cid`
        email = payload["sub"]
        c = _conta(data_path, "em:" + email, lambda: contas.por_email(data_path, email) or contas.registrar_login(data_path, email, payload.get("name") or email, payload.get("provider") or "?"))
    if not contas.sessao_valida(c, payload.get("iat")):
        return None
    return {"email": payload["sub"], "name": payload.get("name"), "provider": payload.get("provider"), "conta_id": c.conta_id}
