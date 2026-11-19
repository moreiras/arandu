# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Configuração do módulo de autenticação.

Carrega secrets JWT/OAuth de variáveis de ambiente. `allowed_ips` também vem
de variável de ambiente (`ALLOWED_IPS`), para não exigir commit a cada ajuste de faixa de IP.
"""
from __future__ import annotations

import ipaddress
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fastapi import Request

_log = logging.getLogger("arandurape.auth")


@dataclass
class AuthConfig:
    jwt_secret: str
    google_client_id: str
    google_client_secret: str
    linkedin_client_id: str
    linkedin_client_secret: str
    peeringdb_client_id: str
    peeringdb_client_secret: str
    app_base_url: str          # URL pública do site, ex: https://exemplo.example
    allowed_ips: list[str]     # CIDRs ou IPs individuais sem necessidade de login
    data_dir: Path


_config: Optional[AuthConfig] = None


def _load_allowed_ips() -> list[str]:
    """Lê ALLOWED_IPS do .env — lista de IPs/CIDRs separados por vírgula.

    Falha alto e cedo (no boot) se a variável não estiver definida, em vez de
    assumir uma allowlist vazia silenciosamente (o que passaria a exigir login
    de todo mundo, inclusive de quem hoje navega sem login por estar em uma
    faixa isenta).
    """
    if "ALLOWED_IPS" not in os.environ:
        raise RuntimeError(
            "ALLOWED_IPS não definida. Configure no .env uma lista de IPs/CIDRs "
            "separados por vírgula (ex.: ALLOWED_IPS=127.0.0.1,10.0.0.0/8) antes "
            "de subir a API — mesmo que vazia (ALLOWED_IPS=), para deixar explícito."
        )
    raw = os.environ["ALLOWED_IPS"]
    entries = [entry.strip() for entry in raw.split(",") if entry.strip()]
    valid: list[str] = []
    for entry in entries:
        try:
            ipaddress.ip_network(entry, strict=False)
        except ValueError:
            _log.error("ALLOWED_IPS: entrada inválida ignorada: %r", entry)
            continue
        valid.append(entry)
        if entry.endswith("/0") or entry.startswith("0.0.0.0") or entry in ("::/0",):
            _log.warning("ALLOWED_IPS contém %r: a exigência de login fica desligada", entry)
    return valid


def init_auth_config(data_path: Path) -> AuthConfig:
    global _config
    _config = AuthConfig(
        jwt_secret=os.environ["JWT_SECRET"],
        google_client_id=os.environ["GOOGLE_CLIENT_ID"],
        google_client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        linkedin_client_id=os.environ.get("LINKEDIN_CLIENT_ID", ""),
        linkedin_client_secret=os.environ.get("LINKEDIN_CLIENT_SECRET", ""),
        peeringdb_client_id=os.environ.get("PEERINGDB_CLIENT_ID", ""),
        peeringdb_client_secret=os.environ.get("PEERINGDB_CLIENT_SECRET", ""),
        app_base_url=os.environ.get("APP_BASE_URL", "http://localhost:5173").rstrip("/"),
        allowed_ips=_load_allowed_ips(),
        data_dir=data_path,
    )
    return _config


def get_auth_config(request: Request) -> AuthConfig:
    return request.app.state.auth_config
