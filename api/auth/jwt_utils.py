# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Utilitários JWT — geração e validação de tokens de autenticação.

Emite tokens HS256 com sub (e-mail), exp e jti (UUID para revogação futura).
Valida assinatura, expiração e formato sem consultar banco de dados.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt


_ALGORITHM = "HS256"
_TTL_DAYS = 30  # 30 dias — razoável para usuário que acessa regularmente


def create_token(email: str, name: str, provider: str, secret: str, conta_id: Optional[str] = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "name": name,
        "provider": provider,
        **({"cid": conta_id} if conta_id else {}),
        "iat": now,
        "exp": now + timedelta(days=_TTL_DAYS),
    }
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def verify_token(token: str, secret: str) -> Optional[dict]:
    try:
        return jwt.decode(token, secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
