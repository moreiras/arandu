# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Contas: cadastro com `conta_id` estável, sessão revogável e exclusão com prazo.

SQLite em `{data}/auth/contas.db`, escrito só pela API. É aditivo: `storage.upsert_user` continua gravando o `emails.csv` até a integração.
A exclusão NUNCA é imediata: o pedido desativa a conta na hora (sem login, chave revogada) e o apagamento
acontece `PRAZO_EXCLUSAO_DIAS` depois, para quem abusa não poder criar a conta, abusar e excluir sem deixar registro.
"""
from __future__ import annotations

import math
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, Optional

PRAZO_EXCLUSAO_DIAS = 30

_SCHEMA = """
CREATE TABLE IF NOT EXISTS contas (
    conta_id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    nome TEXT,
    provedor TEXT,
    criada_em TEXT NOT NULL,
    ultimo_acesso TEXT NOT NULL,
    sessao_valida_desde TEXT,
    exclusao_solicitada_em TEXT
);
"""


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _iso(d: datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")


@contextmanager
def _db(data_path: Path) -> Iterator[sqlite3.Connection]:
    d = Path(data_path) / "auth"
    d.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(d / "contas.db", timeout=10, isolation_level=None)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.executescript(_SCHEMA)
        yield con
    finally:
        con.close()


@dataclass(frozen=True)
class Conta:
    conta_id: str
    email: str
    nome: Optional[str]
    provedor: Optional[str]
    criada_em: str
    ultimo_acesso: str
    sessao_valida_desde: Optional[str]
    exclusao_solicitada_em: Optional[str]

    @property
    def desativada(self) -> bool:
        return self.exclusao_solicitada_em is not None

    def exclusao_efetiva_em(self) -> Optional[str]:
        if not self.exclusao_solicitada_em:
            return None
        return _iso(datetime.fromisoformat(self.exclusao_solicitada_em) + timedelta(days=PRAZO_EXCLUSAO_DIAS))[:10]


def _conta(r: Optional[sqlite3.Row]) -> Optional[Conta]:
    return Conta(**{k: r[k] for k in r.keys()}) if r else None


def por_id(data_path: Path, conta_id: str) -> Optional[Conta]:
    with _db(data_path) as con:
        return _conta(con.execute("SELECT * FROM contas WHERE conta_id=?", (conta_id,)).fetchone())


def normalizar_email(email: str) -> str:
    """Forma canônica do e-mail para identificar a conta: sem espaços nas pontas e em minúsculas."""
    return (email or "").strip().lower()


def por_email(data_path: Path, email: str) -> Optional[Conta]:
    with _db(data_path) as con:
        return _conta(con.execute("SELECT * FROM contas WHERE lower(email)=lower(?)", (email,)).fetchone())


def registrar_login(data_path: Path, email: str, nome: str, provedor: str) -> Optional[Conta]:
    """Cria a conta no primeiro login ou atualiza o último acesso. Devolve `None` se a conta está com exclusão pendente (login recusado)."""
    # o e-mail é comparado sem distinção de maiúsculas (`Fulano@x` e `fulano@x` eram duas contas);
    # conta nova grava em minúsculas, e as antigas gravadas com maiúsculas continuam sendo achadas.
    email = normalizar_email(email)
    agora = _iso(_agora())
    with _db(data_path) as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            r = con.execute("SELECT * FROM contas WHERE lower(email)=?", (email,)).fetchone()
            if r is None:
                con.execute("INSERT INTO contas (conta_id, email, nome, provedor, criada_em, ultimo_acesso) VALUES (?,?,?,?,?,?)", (str(uuid.uuid4()), email, nome, provedor, agora, agora))
            elif r["exclusao_solicitada_em"] is None:
                con.execute("UPDATE contas SET nome=?, ultimo_acesso=? WHERE conta_id=?", (nome, agora, r["conta_id"]))
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        c = _conta(con.execute("SELECT * FROM contas WHERE lower(email)=?", (email,)).fetchone())
    return None if c is None or c.desativada else c


def sessao_valida(c: Optional[Conta], emitida_em: Optional[int]) -> bool:
    """A sessão (JWT) vale se a conta existe, não está desativada e o token não é anterior a "sair de todos os dispositivos"."""
    if c is None or c.desativada:
        return False
    if c.sessao_valida_desde and emitida_em is not None:
        # arredonda para cima: o `iat` do JWT é em segundos inteiros e um token emitido no mesmo segundo do pedido não pode sobreviver a ele
        return emitida_em >= math.ceil(datetime.fromisoformat(c.sessao_valida_desde).timestamp())
    return True


def sair_de_todos(data_path: Path, conta_id: str) -> None:
    with _db(data_path) as con:
        con.execute("UPDATE contas SET sessao_valida_desde=? WHERE conta_id=?", (_iso(_agora()), conta_id))


def solicitar_exclusao(data_path: Path, conta_id: str) -> Optional[Conta]:
    """Desativa a conta agora; o apagamento vem `PRAZO_EXCLUSAO_DIAS` depois. Pedido repetido não reinicia o prazo."""
    with _db(data_path) as con:
        con.execute("UPDATE contas SET exclusao_solicitada_em=COALESCE(exclusao_solicitada_em, ?) WHERE conta_id=?", (_iso(_agora()), conta_id))
        return _conta(con.execute("SELECT * FROM contas WHERE conta_id=?", (conta_id,)).fetchone())


def cancelar_exclusao(data_path: Path, conta_id: str) -> None:
    """Só pelos mantenedores (pedido do titular por e-mail, dentro do prazo): reativa a conta. A chave revogada não volta."""
    with _db(data_path) as con:
        con.execute("UPDATE contas SET exclusao_solicitada_em=NULL WHERE conta_id=?", (conta_id,))


def vencidas(data_path: Path, agora: Optional[datetime] = None) -> list[Conta]:
    limite = _iso((agora or _agora()) - timedelta(days=PRAZO_EXCLUSAO_DIAS))
    with _db(data_path) as con:
        return [c for r in con.execute("SELECT * FROM contas WHERE exclusao_solicitada_em IS NOT NULL AND exclusao_solicitada_em <= ?", (limite,)) if (c := _conta(r))]


def apagar(data_path: Path, conta_id: str) -> None:
    with _db(data_path) as con:
        con.execute("DELETE FROM contas WHERE conta_id=?", (conta_id,))
