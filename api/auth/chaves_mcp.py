# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Chave de MCP: `<esquema>_mcp_<id>_<segredo>` (esquema de `SITE_MCP_ESQUEMA`), 256 bits, guardada só como HMAC-SHA-256 com pepper do ambiente.

O `id` (8 caracteres) não é secreto: acha a linha sem varrer a tabela e aparece no perfil. O hash e o pepper existem só na API; o MCP pergunta à API
(`/internal/mcp-chave/verificar`). A chave nunca é registrada, nem o hash. Uma chave ativa por conta; gerar outra revoga a anterior na mesma transação.
Desligada por padrão (`MCP_KEY_ATIVA=1` e `MCP_KEY_PEPPER` com 32+ caracteres ligam).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from core.site import FORMATO_CHAVE_MCP, prefixo_chave_mcp

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chaves (
    id TEXT PRIMARY KEY,
    conta_id TEXT NOT NULL,
    hash TEXT,
    criada_em TEXT NOT NULL,
    ultimo_uso_dia TEXT,
    rotulo TEXT,
    revogada_em TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_chave_ativa ON chaves(conta_id) WHERE revogada_em IS NULL;
"""


def ativa() -> bool:
    return os.environ.get("MCP_KEY_ATIVA", "0").strip().lower() in ("1", "true", "sim") and len(os.environ.get("MCP_KEY_PEPPER", "")) >= 32


def _pepper() -> bytes:
    p = os.environ.get("MCP_KEY_PEPPER", "")
    if len(p) < 32:
        raise RuntimeError("MCP_KEY_PEPPER ausente ou curto (mínimo 32 caracteres): a chave de MCP fica desligada.")
    return p.encode()


def _hash(segredo: str) -> str:
    return hmac.new(_pepper(), segredo.encode(), hashlib.sha256).hexdigest()


@contextmanager
def _db(data_path: Path) -> Iterator[sqlite3.Connection]:
    d = Path(data_path) / "auth"
    d.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(d / "chaves_mcp.db", timeout=10, isolation_level=None)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.executescript(_SCHEMA)
        yield con
    finally:
        con.close()


def _b32(n: int) -> str:
    return base64.b32encode(secrets.token_bytes(n)).decode().rstrip("=")


def _dia() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def gerar(data_path: Path, conta_id: str, rotulo: Optional[str] = None) -> tuple[str, dict]:
    """Cria a chave da conta e revoga a anterior (mesma transação). A chave completa só existe no valor devolvido."""
    _pepper()
    rotulo = (rotulo or "").strip()[:40] or None
    segredo = _b32(32)
    with _db(data_path) as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            agora = datetime.now(timezone.utc).isoformat()
            con.execute("UPDATE chaves SET revogada_em=?, hash=NULL WHERE conta_id=? AND revogada_em IS NULL", (agora, conta_id))
            while True:
                kid = _b32(5)[:8]
                if con.execute("SELECT 1 FROM chaves WHERE id=?", (kid,)).fetchone() is None:
                    break
            con.execute("INSERT INTO chaves (id, conta_id, hash, criada_em, rotulo) VALUES (?,?,?,?,?)", (kid, conta_id, _hash(segredo), agora, rotulo))
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
    return f"{prefixo_chave_mcp()}{kid}_{segredo}", {"id": kid, "criada_em": agora, "rotulo": rotulo}


def verificar(data_path: Path, chave: str) -> Optional[str]:
    """`conta_id` se a chave é válida e ativa; `None` caso contrário. Tempo constante: sempre calcula o HMAC e compara com `compare_digest`."""
    m = FORMATO_CHAVE_MCP.fullmatch(chave or "")
    kid, segredo = (m.group(2), m.group(3)) if m else ("", "")
    calculado = _hash(segredo or "x")
    with _db(data_path) as con:
        r = con.execute("SELECT * FROM chaves WHERE id=?", (kid,)).fetchone() if kid and segredo else None
        guardado = (r["hash"] if r and r["revogada_em"] is None and r["hash"] else "0" * 64)
        if not hmac.compare_digest(calculado, guardado) or r is None or r["revogada_em"] is not None:
            return None
        if r["ultimo_uso_dia"] != _dia():                       # no máximo uma escrita por chave por dia
            con.execute("UPDATE chaves SET ultimo_uso_dia=? WHERE id=?", (_dia(), kid))
        return r["conta_id"]


def da_conta(data_path: Path, conta_id: str) -> Optional[dict]:
    """Metadados da chave ativa (sem hash, sem segredo)."""
    with _db(data_path) as con:
        r = con.execute("SELECT id, criada_em, ultimo_uso_dia, rotulo FROM chaves WHERE conta_id=? AND revogada_em IS NULL", (conta_id,)).fetchone()
        return dict(r) if r else None


def revogar(data_path: Path, conta_id: str) -> bool:
    """Revoga a chave ativa e apaga o hash (fica só o `id` e as datas)."""
    with _db(data_path) as con:
        n = con.execute("UPDATE chaves SET revogada_em=?, hash=NULL WHERE conta_id=? AND revogada_em IS NULL", (datetime.now(timezone.utc).isoformat(), conta_id)).rowcount
        return n > 0


def apagar_da_conta(data_path: Path, conta_id: str) -> None:
    with _db(data_path) as con:
        con.execute("DELETE FROM chaves WHERE conta_id=?", (conta_id,))
