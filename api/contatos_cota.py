# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cota de consultas de contato.

Meta: montar a lista de contatos de todos os ASNs a partir do site tem de ser bem mais difícil do que consultar as fontes (RDAP do Registro.br,
PeeringDB) diretamente. Com uma conta, a base inteira levaria meses; com muitas contas, o teto global a espalha por semanas, e o alerta e a
suspensão automática dão tempo de reagir.

- **Custo por resultado:** cada ASN revelado custa 1; a rota por operadora custa o número de ASNs do CNPJ (mínimo 1).
- **Janelas corridas** (10 min, 1 h, 24 h, 30 dias) por conta, por rede de origem (IPv4 inteiro, IPv6 pelo /64, em HMAC com o segredo do JWT:
  nunca o IP) e global (24 h, todas as contas). Conta com menos de `CONTATOS_CONTA_NOVA_DIAS` dias tem teto diário menor.
- **Persistente** (`data/auth/contatos_uso.db`), para reiniciar a API não renovar a cota. Guarda só instante, `conta_id`, hash da rede e custo;
  linhas com mais de 31 dias são apagadas.
- **Suspensão automática:** a conta que bate no teto diário em `CONTATOS_SUSPENDER_APOS` dias diferentes dentro de 7 perde o acesso a
  contatos (só a contatos) até o mantenedor liberar: `python -m api.contatos_cota --liberar CONTA_ID`. Exceção por conta, concedida pelo
  mantenedor: `--conceder CONTA_ID FATOR` (multiplica os tetos da conta). Eventos `contatos_*` no log para o alerta.

Cada teto vem de uma variável de ambiente (0 desliga aquele teto); os padrões estão em `PADROES`.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import math
import os
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

import structlog

_log = structlog.get_logger("arandurape.contatos_cota")

DIA = 86400
PADROES = {
    "CONTATOS_CONTA_RAJADA": 10,      # por 10 min
    "CONTATOS_CONTA_HORA": 20,
    "CONTATOS_CONTA_DIA": 40,
    "CONTATOS_CONTA_30D": 300,
    "CONTATOS_CONTA_NOVA_DIA": 10,
    "CONTATOS_CONTA_NOVA_DIAS": 7,
    "CONTATOS_REDE_RAJADA": 20,       # por 10 min, somando as contas da mesma rede
    "CONTATOS_REDE_HORA": 40,
    "CONTATOS_REDE_DIA": 80,
    "CONTATOS_GLOBAL_DIA": 800,
    "CONTATOS_GLOBAL_ALERTA": 400,
    "CONTATOS_SUSPENDER_APOS": 3,
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS eventos (ts REAL NOT NULL, conta TEXT, rede TEXT NOT NULL, custo INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS ev_conta ON eventos (conta, ts);
CREATE INDEX IF NOT EXISTS ev_rede ON eventos (rede, ts);
CREATE INDEX IF NOT EXISTS ev_ts ON eventos (ts);
CREATE TABLE IF NOT EXISTS teto (conta TEXT NOT NULL, dia TEXT NOT NULL, PRIMARY KEY (conta, dia));
CREATE TABLE IF NOT EXISTS suspensao (conta TEXT PRIMARY KEY, desde TEXT NOT NULL, motivo TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS excecao (conta TEXT PRIMARY KEY, fator REAL NOT NULL, desde TEXT NOT NULL);
"""


def _v(nome: str) -> int:
    try:
        return max(0, int(os.environ.get(nome, PADROES[nome])))
    except ValueError:
        return PADROES[nome]


def tetos_da_conta() -> dict:
    """Os tetos de contatos de uma conta, em vigor (variável de ambiente ou `PADROES`), para `GET /api/v1/limites`. Só o que a conta vê: o teto
    global, o da rede e o limiar de suspensão ficam fora (publicá-los ensinaria a esgotar a cota dos demais)."""
    return {"por_10_minutos": _v("CONTATOS_CONTA_RAJADA"), "por_hora": _v("CONTATOS_CONTA_HORA"), "por_dia": _v("CONTATOS_CONTA_DIA"),
            "por_30_dias": _v("CONTATOS_CONTA_30D"), "por_dia_conta_nova": _v("CONTATOS_CONTA_NOVA_DIA"),
            "dias_de_conta_nova": _v("CONTATOS_CONTA_NOVA_DIAS")}


@dataclass(frozen=True)
class Resultado:
    ok: bool
    motivo: str = ""
    espera_s: int = 0
    restante_dia: Optional[int] = None


@contextmanager
def _db(data_path: Path) -> Iterator[sqlite3.Connection]:
    d = Path(data_path) / "auth"
    d.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(d / "contatos_uso.db", timeout=10, isolation_level=None)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.executescript(_SCHEMA)
        yield con
    finally:
        con.close()


def hash_rede(rede: str, segredo: str) -> str:
    return hmac.new((segredo or "").encode(), f"contatos|{rede}".encode(), hashlib.sha256).hexdigest()[:24]


def _soma(con, coluna: Optional[str], valor: Optional[str], desde: float) -> tuple[int, Optional[float]]:
    if coluna is None:
        r = con.execute("SELECT COALESCE(SUM(custo),0), MIN(ts) FROM eventos WHERE ts > ?", (desde,)).fetchone()
    else:
        r = con.execute(f"SELECT COALESCE(SUM(custo),0), MIN(ts) FROM eventos WHERE {coluna} = ? AND ts > ?", (valor, desde)).fetchone()
    return int(r[0]), r[1]


def _hoje() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def consumir(data_path: Path, conta_id: Optional[str], rede_hash: str, custo: int, criada_em: Optional[str] = None,
             agora: Optional[float] = None) -> Resultado:
    """Debita `custo` se couber em todos os tetos; senão não debita nada e diz qual teto e quanto esperar."""
    agora = time.time() if agora is None else agora
    custo = max(1, int(custo))
    with _db(data_path) as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            if conta_id and con.execute("SELECT 1 FROM suspensao WHERE conta = ?", (conta_id,)).fetchone():
                con.execute("ROLLBACK")
                return Resultado(False, "suspensao", 0)
            fator = 1.0
            if conta_id:
                r = con.execute("SELECT fator FROM excecao WHERE conta = ?", (conta_id,)).fetchone()
                fator = float(r[0]) if r else 1.0
            nova = False
            if conta_id and criada_em:
                try:
                    nova = (agora - datetime.fromisoformat(criada_em).timestamp()) < _v("CONTATOS_CONTA_NOVA_DIAS") * DIA
                except ValueError:
                    nova = False
            dia_conta = _v("CONTATOS_CONTA_NOVA_DIA") if nova else _v("CONTATOS_CONTA_DIA")
            tetos: list[tuple[str, Optional[str], Optional[str], int, int]] = [("global", None, None, DIA, _v("CONTATOS_GLOBAL_DIA"))]
            if conta_id:
                tetos += [("conta_rajada", "conta", conta_id, 600, int(_v("CONTATOS_CONTA_RAJADA") * fator)),
                          ("conta_hora", "conta", conta_id, 3600, int(_v("CONTATOS_CONTA_HORA") * fator)),
                          ("conta_dia", "conta", conta_id, DIA, int(dia_conta * fator)),
                          ("conta_30d", "conta", conta_id, 30 * DIA, int(_v("CONTATOS_CONTA_30D") * fator))]
            tetos += [("rede_rajada", "rede", rede_hash, 600, _v("CONTATOS_REDE_RAJADA")),
                      ("rede_hora", "rede", rede_hash, 3600, _v("CONTATOS_REDE_HORA")),
                      ("rede_dia", "rede", rede_hash, DIA, _v("CONTATOS_REDE_DIA"))]
            restante_dia = None
            for nome, coluna, valor, janela, teto in tetos:
                if teto <= 0:
                    continue
                usado, mais_antigo = _soma(con, coluna, valor, agora - janela)
                if nome == "conta_dia":
                    restante_dia = max(0, teto - usado - custo)
                if usado + custo > teto:
                    espera = max(1, math.ceil((mais_antigo or agora) + janela - agora))
                    if nome == "conta_dia":
                        _registrar_teto(con, conta_id)
                    con.execute("COMMIT")
                    _log.warning("contatos_teto", teto=nome, limite=teto, usado=usado, custo=custo, conta=conta_id)
                    return Resultado(False, nome, espera, restante_dia=0 if nome == "conta_dia" else restante_dia)
            antes_global, _ = _soma(con, None, None, agora - DIA)
            con.execute("INSERT INTO eventos (ts, conta, rede, custo) VALUES (?,?,?,?)", (agora, conta_id, rede_hash, custo))
            alerta = _v("CONTATOS_GLOBAL_ALERTA")
            if alerta and antes_global < alerta <= antes_global + custo:
                _log.warning("contatos_global_alerta", usado_24h=antes_global + custo, alerta=alerta, teto=_v("CONTATOS_GLOBAL_DIA"))
            if int(agora) % 50 == 0:
                con.execute("DELETE FROM eventos WHERE ts < ?", (agora - 31 * DIA,))
            con.execute("COMMIT")
            return Resultado(True, restante_dia=restante_dia)
        except Exception:
            con.execute("ROLLBACK")
            raise


def _registrar_teto(con, conta_id: str) -> None:
    con.execute("INSERT OR IGNORE INTO teto (conta, dia) VALUES (?, ?)", (conta_id, _hoje()))
    apos = _v("CONTATOS_SUSPENDER_APOS")
    if not apos:
        return
    desde = datetime.fromtimestamp(time.time() - 7 * DIA, timezone.utc).strftime("%Y-%m-%d")
    n = con.execute("SELECT COUNT(*) FROM teto WHERE conta = ? AND dia >= ?", (conta_id, desde)).fetchone()[0]
    if n >= apos and not con.execute("SELECT 1 FROM suspensao WHERE conta = ?", (conta_id,)).fetchone():
        con.execute("INSERT INTO suspensao (conta, desde, motivo) VALUES (?,?,?)", (conta_id, _hoje(), f"teto diário em {n} dias de 7"))
        _log.warning("contatos_suspensao", conta=conta_id, dias_no_teto=n)


def contatos_pela_allowlist() -> bool:
    """`CONTATOS_ALLOWLIST=1` deixa o IP da allowlist ver contatos sem conta (padrão: não; contato exige conta)."""
    return os.environ.get("CONTATOS_ALLOWLIST", "0").strip().lower() in ("1", "true", "sim")


def exigir(request, user: dict, custo: int) -> Optional[int]:
    """Aplica a cota de uma revelação de contatos para `user` (dependência `require_user`). Levanta 401 se o acesso é só pela allowlist e
    `CONTATOS_ALLOWLIST` está desligado, 429 acima do teto (com `Retry-After`). Devolve quantas consultas da conta ainda cabem hoje."""
    from fastapi import HTTPException

    from api.auth.config import get_auth_config
    from api.auth.deps import client_ip

    cfg = get_auth_config(request)
    conta_id = user.get("conta_id")
    if not conta_id and not contatos_pela_allowlist():
        raise HTTPException(401, detail="Os contatos exigem login com uma conta.")
    return exigir_da_conta(cfg, conta_id, client_ip(request), custo)


def exigir_da_conta(cfg, conta_id: Optional[str], ip: str, custo: int) -> Optional[int]:
    """O mesmo `exigir` com a conta e o IP já resolvidos: a rota interna do MCP (`/internal/contatos`) cobra aqui, no mesmo registro e com
    os mesmos tetos do site, e a cota é uma só para a conta nos dois caminhos. Levanta 429 acima do teto."""
    from fastapi import HTTPException

    from api.auth import contas
    from api.limites import rede_do_ip

    criada_em = None
    if conta_id:
        c = contas.por_id(cfg.data_dir, conta_id)
        criada_em = c.criada_em if c else None
    r = consumir(cfg.data_dir, conta_id, hash_rede(rede_do_ip(ip), cfg.jwt_secret), custo, criada_em)
    if not r.ok:
        raise HTTPException(429, detail=mensagem(r), headers={"Retry-After": str(max(1, r.espera_s)), "Cache-Control": "private, no-store"})
    return r.restante_dia


def mensagem(r: Resultado) -> str:
    if r.motivo == "suspensao":
        return ("O acesso a contatos desta conta está suspenso por excesso de consultas. Escreva para o contato do projeto (página Sobre) "
                "se precisar dele.")
    if r.motivo == "global":
        return f"O limite de consultas de contato do serviço foi atingido. Tente novamente em {_humano(r.espera_s)}."
    quem = "sua conta" if r.motivo.startswith("conta") else "sua rede"
    return f"Você atingiu o limite de consultas de contato para {quem}. Tente novamente em {_humano(r.espera_s)}."


def _humano(s: int) -> str:
    if s < 120:
        return f"{s} s"
    if s < 7200:
        return f"{math.ceil(s / 60)} min"
    return f"{math.ceil(s / 3600)} h"


def main(argv: Optional[list[str]] = None) -> int:
    from core.common import data_dir
    p = argparse.ArgumentParser(description="Cota de contatos: estado, liberar conta suspensa, conceder exceção.")
    p.add_argument("--estado", action="store_true", help="uso nas últimas 24 h, contas suspensas e exceções")
    p.add_argument("--liberar", metavar="CONTA_ID", help="tira a suspensão de contatos da conta")
    p.add_argument("--conceder", nargs=2, metavar=("CONTA_ID", "FATOR"), help="multiplica os tetos da conta (1 remove a exceção)")
    a = p.parse_args(argv)
    base = data_dir()
    with _db(base) as con:
        if a.liberar:
            con.execute("DELETE FROM suspensao WHERE conta = ?", (a.liberar,))
            con.execute("DELETE FROM teto WHERE conta = ?", (a.liberar,))
            print(f"suspensão retirada: {a.liberar}")
        if a.conceder:
            conta, fator = a.conceder[0], float(a.conceder[1])
            if fator == 1:
                con.execute("DELETE FROM excecao WHERE conta = ?", (conta,))
            else:
                con.execute("INSERT OR REPLACE INTO excecao (conta, fator, desde) VALUES (?,?,?)", (conta, fator, _hoje()))
            print(f"exceção: {conta} × {fator}")
        if a.estado or not (a.liberar or a.conceder):
            usado, _ = _soma(con, None, None, time.time() - DIA)
            print(f"consultas nas últimas 24 h: {usado} de {_v('CONTATOS_GLOBAL_DIA')}")
            for conta, desde, motivo in con.execute("SELECT conta, desde, motivo FROM suspensao ORDER BY desde"):
                print(f"suspensa: {conta} desde {desde} ({motivo})")
            for conta, fator, desde in con.execute("SELECT conta, fator, desde FROM excecao ORDER BY desde"):
                print(f"exceção: {conta} × {fator} desde {desde}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
