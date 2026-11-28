# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Estado de sessão anônima (navegação sem login, com limite de tempo ativo).

Armazenado em SQLite (WAL) sob `{data_dir}/auth/anon_sessions.db` — mesmo
diretório usado por `storage.py` para o CSV de usuários e os logs de acesso,
mas com garantias transacionais nativas (BEGIN IMMEDIATE), evitando o tipo de
condição de corrida já observada em `storage._rotate_old_logs()`.

Identidade resolvida por cookie (prioridade), fingerprint forte e fingerprint
estável (fallbacks, nesta ordem), com TTL de 24h por padrão — é essa expiração do
registro que reinicia a contagem, não uma lógica de aplicação separada.

Além do orçamento individual há um teto por rede: a soma do tempo ativo de todas as
sessões da mesma rede no dia (`rede_hash`), por padrão `REDE_MULTIPLICADOR_PADRAO` vezes o
orçamento individual. Ele fecha o contorno de quem abre uma janela privada que muda cookie
e fingerprint forte.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import os
import secrets
import sqlite3
import threading
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

COOKIE_NAME = "anon_sid"
FINGERPRINT_HEADER = "X-Device-Fingerprint"
FINGERPRINT_ESTAVEL_HEADER = "X-Device-Fingerprint-Estavel"

_DB_FILENAME = "anon_sessions.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS anon_sessions (
    session_id TEXT PRIMARY KEY,
    fingerprint_hash TEXT,
    active_seconds INTEGER NOT NULL DEFAULT 0,
    last_heartbeat_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    ipua_hash TEXT,
    fingerprint_estavel_hash TEXT,
    rede_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_anon_sessions_fingerprint
    ON anon_sessions(fingerprint_hash);
"""

# Colunas acrescentadas depois da criação da tabela: `ipua_hash` (cliente sem cookie nem fingerprint, identificado por hash(IP + User-Agent)),
# `fingerprint_estavel_hash` (fingerprint sem os sinais que o modo privado altera) e `rede_hash` (HMAC da rede e do dia, nunca o IP).
_COLUNAS_NOVAS = (
    ("ipua_hash", "TEXT"),
    ("fingerprint_estavel_hash", "TEXT"),
    ("rede_hash", "TEXT"),
)
_INDICES = (
    "CREATE INDEX IF NOT EXISTS idx_anon_sessions_ipua ON anon_sessions(ipua_hash)",
    "CREATE INDEX IF NOT EXISTS idx_anon_sessions_fp_estavel ON anon_sessions(fingerprint_estavel_hash)",
    "CREATE INDEX IF NOT EXISTS idx_anon_sessions_rede ON anon_sessions(rede_hash)",
)

# Limpeza de sessões expiradas: no máximo 1x a cada 10 min por processo.
_PURGE_INTERVAL_SECONDS = 600.0
_last_purge = 0.0

AREA_METERED = "metered"
AREA_HEADER = "X-Arandu-Area"


@dataclass
class AnonSessionConfig:
    limit_minutes: int
    heartbeat_interval_seconds: int
    heartbeat_ceiling_multiplier: int
    ttl_hours: int
    inactivity_timeout_seconds: int
    # Custo (s) debitado por requisição medida de clientes SEM sessão válida (scripts/curl, cookie inventado), na conta do IP (IPv6 pelo /64).
    # com 3 s e o orçamento padrão (600 s), 200 pedidos medidos por IP a cada 24 h. Navegador atrás de
    # CGNAT tem cookie de sessão próprio e não entra nesta conta. 0 = desligado.
    api_client_cost_seconds: int = 3
    # Teto do tempo ativo somado de todas as sessões da mesma rede no dia, em múltiplos de `limit_seconds`. 0 = desligado.
    rede_multiplier: int = 3

    @property
    def limit_seconds(self) -> int:
        return self.limit_minutes * 60

    @property
    def rede_limit_seconds(self) -> int:
        """Teto da rede em segundos; 0 = sem teto por rede."""
        return max(0, self.rede_multiplier) * self.limit_seconds


TTL_PADRAO_HORAS = 24
REDE_MULTIPLICADOR_PADRAO = 3


def load_anon_config() -> AnonSessionConfig:
    return AnonSessionConfig(
        limit_minutes=int(os.environ.get("ANON_SESSION_LIMIT_MINUTES", "10")),
        heartbeat_interval_seconds=int(os.environ.get("ANON_HEARTBEAT_INTERVAL_SECONDS", "15")),
        heartbeat_ceiling_multiplier=int(os.environ.get("ANON_HEARTBEAT_CEILING_MULTIPLIER", "3")),
        ttl_hours=int(os.environ.get("ANON_SESSION_TTL_HOURS", str(TTL_PADRAO_HORAS))),
        inactivity_timeout_seconds=int(os.environ.get("ANON_INACTIVITY_TIMEOUT_SECONDS", "45")),
        api_client_cost_seconds=int(os.environ.get("ANON_API_CLIENT_COST_SECONDS", "3")),
        rede_multiplier=int(os.environ.get("ANON_REDE_LIMIT_MULTIPLIER", str(REDE_MULTIPLICADOR_PADRAO))),
    )


def hash_fingerprint(raw: str, rede: Optional[str] = None) -> str:
    """Fingerprint de dispositivo restrito à rede do cliente (`rede` = `hash_rede`).

    O fingerprint (frontend/src/auth/fingerprint.ts: user-agent, idioma, fuso, tela, núcleos, canvas, WebGL) identifica o modelo de
    aparelho e navegador, não a pessoa: sem a rede, todos os aparelhos iguais do país dividiriam uma sessão anônima, e quem chegasse pela
    primeira vez herdaria o orçamento já gasto por outra pessoa (IP nunca visto, bloqueado na 1ª carga).
    Com a rede, apagar o cookie e voltar na mesma rede continua sem renovar o orçamento, e aparelhos iguais em redes diferentes não se
    misturam."""
    base = f"{rede}|{raw}" if rede else raw
    return hashlib.sha256(base.encode("utf-8", errors="ignore")).hexdigest()


def hash_fingerprint_estavel(raw: str, rede: Optional[str] = None) -> str:
    """Fingerprint estável (frontend/src/auth/fingerprint.ts: família do navegador, idioma, fuso, tela e núcleos), sem canvas, WebGL nem
    versão do user-agent, que o modo privado do Safari e do Firefox altera. Mesmo escopo de rede e dia de `hash_fingerprint`; o prefixo
    separa os dois espaços de hash."""
    return hash_fingerprint(f"estavel|{raw}", rede)


def rede_do_ip(ip: str) -> str:
    """IPv4 inteiro; IPv6 pelo /64 (o prefixo do assinante: trocar o sufixo não vira outro cliente)."""
    try:
        end = ipaddress.ip_address((ip or "").strip())
    except ValueError:
        return ip or "?"
    return str(ipaddress.ip_network(f"{end}/64", strict=False)) if end.version == 6 else str(end)


def hash_rede(ip: str, segredo: str) -> str:
    """Identidade de quem não tem sessão válida: a rede do IP (`rede_do_ip`), em HMAC com o segredo do JWT e a data do dia (um hash
    de IP+UA sem sal se reverte por força bruta). O mesmo valor na API e no gate (processos diferentes, mesmo segredo)."""
    dia = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return hmac.new((segredo or "").encode(), f"{dia}|{rede_do_ip(ip)}".encode(), hashlib.sha256).hexdigest()


# sessões novas por rede e por hora. Um prédio atrás de CGNAT não chega a isto; um script que joga fora o cookie a cada pedido, sim.
MAX_SESSOES_NOVAS_POR_HORA = 50
_criacoes: dict[str, deque] = {}
_criacoes_lock = threading.Lock()


def _pode_criar_sessao(rede: Optional[str]) -> bool:
    if not rede:
        return True
    agora = time.monotonic()
    with _criacoes_lock:
        fila = _criacoes.setdefault(rede, deque())
        while fila and fila[0] < agora - 3600:
            fila.popleft()
        if len(fila) >= MAX_SESSOES_NOVAS_POR_HORA:
            return False
        fila.append(agora)
        if len(_criacoes) > 100_000:                      # memória limitada: esquece as redes sem criação recente
            for k in [k for k, f in _criacoes.items() if not f or f[-1] < agora - 3600]:
                del _criacoes[k]
        return True


def hash_ipua(ip: str, user_agent: Optional[str]) -> str:
    """Identidade de último recurso (cliente sem cookie nem fingerprint)."""
    return hashlib.sha256(f"{ip}|{user_agent or ''}".encode("utf-8", errors="ignore")).hexdigest()


def _db_path(data_dir: Path) -> Path:
    d = data_dir / "auth"
    d.mkdir(parents=True, exist_ok=True)
    return d / _DB_FILENAME


_initialized: set[str] = set()


@contextmanager
def _connect(data_dir: Path):
    path = _db_path(data_dir)
    conn = sqlite3.connect(path, timeout=5, isolation_level=None)
    if str(path) not in _initialized:
        # Esquema/migração/WAL 1x por processo (o gate roda a cada requisição de API).
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_SCHEMA)
        existentes = {r[1] for r in conn.execute("PRAGMA table_info(anon_sessions)")}
        for coluna, tipo in _COLUNAS_NOVAS:
            if coluna not in existentes:
                try:
                    conn.execute(f"ALTER TABLE anon_sessions ADD COLUMN {coluna} {tipo}")
                except sqlite3.OperationalError:
                    pass  # outro processo (API e gate abrem o banco juntos) acrescentou antes
        for stmt in _INDICES:
            conn.execute(stmt)
        _initialized.add(str(path))
    _maybe_purge(conn)
    try:
        yield conn
    finally:
        conn.close()


def _maybe_purge(conn: sqlite3.Connection) -> None:
    """Apaga sessões com TTL vencido (a tabela não cresce sem limite)."""
    global _last_purge
    import time

    now = time.monotonic()
    # `_last_purge <= 0` = "nunca limpou": `time.monotonic()` parte de um ponto arbitrário (em geral o boot),
    # então logo depois de ligar a máquina `now - 0.0` seria < intervalo e a primeira limpeza ficaria adiada.
    if _last_purge > 0.0 and now - _last_purge < _PURGE_INTERVAL_SECONDS:
        return
    _last_purge = now
    try:
        conn.execute(
            "DELETE FROM anon_sessions WHERE expires_at < ?",
            (datetime.now(timezone.utc).isoformat(),),
        )
    except sqlite3.OperationalError:
        pass


def _new_session_id() -> str:
    return secrets.token_urlsafe(32)


@dataclass
class Resolucao:
    session_id: str
    active_seconds: int
    limit_reached: bool          # orçamento individual esgotado OU rede acima do teto
    needs_cookie: bool
    bloqueio_rede: bool = False  # o bloqueio vem do teto da rede (o individual pode não ter acabado)


def _total_rede(conn: sqlite3.Connection, rede: Optional[str]) -> int:
    """Tempo ativo somado das sessões da rede no dia (`rede_hash` já traz o dia). Só linhas com `rede_hash`: o custo por chamada de
    script (`charge_client`) tem teto próprio e não entra, para um script não gastar o teto de quem navega."""
    if not rede:
        return 0
    return conn.execute("SELECT COALESCE(SUM(active_seconds), 0) FROM anon_sessions WHERE rede_hash = ?", (rede,)).fetchone()[0]


def rede_acima_do_teto(conn: sqlite3.Connection, cfg: AnonSessionConfig, rede: Optional[str]) -> bool:
    teto = cfg.rede_limit_seconds
    return bool(teto and rede and _total_rede(conn, rede) >= teto)


_SELECT_SESSAO = "SELECT session_id, active_seconds, last_heartbeat_at, expires_at FROM anon_sessions WHERE "


def resolver_sessao(
    data_dir: Path,
    cfg: AnonSessionConfig,
    cookie_session_id: Optional[str],
    fingerprint_hash: Optional[str],
    area: str = AREA_METERED,
    rede: Optional[str] = None,
    fingerprint_estavel_hash: Optional[str] = None,
) -> Resolucao:
    """Resolve a sessão anônima (cookie > fingerprint forte > fingerprint estável > nova) e registra um heartbeat.

    O delta somado a `active_seconds` é `agora - last_heartbeat_at`, limitado a um
    teto de `heartbeat_interval_seconds * heartbeat_ceiling_multiplier` — evita que
    uma aba suspensa que atrase um heartbeat infle o contador, e como o cálculo é
    por diferença de timestamp (não incremento fixo), múltiplas abas do mesmo
    usuário não contam tempo em dobro.

    Só soma tempo quando `area == "metered"` (o heartbeat informa a área da página
    em uso). Em páginas de entrada (`open`) o relógio do orçamento não anda, mas
    `last_heartbeat_at` é atualizado — ao voltar a uma página avançada o primeiro
    delta não infla o contador.

    Achada pelo estável (janela privada: cookie e fingerprint forte novos), a sessão passa a gravar o forte novo, para os próximos pedidos
    acharem-na pelo forte, e o cookie é reemitido com o id dela (sem sessão nova). Os fingerprints são sempre buscados dentro da rede e do dia
    (o hash os traz).

    Com `rede`, vale também o teto da rede (`AnonSessionConfig.rede_limit_seconds`): somado o tempo de todas as sessões dela, acima do teto
    `limit_reached` fica True mesmo com o orçamento individual sobrando, e uma rede acima do teto não cria sessão nova.
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    ttl = timedelta(hours=cfg.ttl_hours)
    ceiling = timedelta(seconds=cfg.heartbeat_interval_seconds * cfg.heartbeat_ceiling_multiplier)

    with _connect(data_dir) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = None
            if cookie_session_id:
                row = conn.execute(_SELECT_SESSAO + "session_id = ?", (cookie_session_id,)).fetchone()
                if row and row[3] < now_iso:
                    row = None  # TTL expirado — trata como inexistente

            needs_cookie = row is None
            achada_pelo_estavel = False
            for coluna, valor in (("fingerprint_hash", fingerprint_hash), ("fingerprint_estavel_hash", fingerprint_estavel_hash)):
                if row is not None or not valor:
                    continue
                row = conn.execute(
                    _SELECT_SESSAO + f"{coluna} = ? ORDER BY last_heartbeat_at DESC LIMIT 1", (valor,),
                ).fetchone()
                if row and row[3] < now_iso:
                    row = None
                achada_pelo_estavel = row is not None and coluna == "fingerprint_estavel_hash"

            if row is None:
                if rede_acima_do_teto(conn, cfg, rede):       # rede no teto: nova sessão não adianta nada
                    conn.execute("ROLLBACK")
                    return Resolucao("", cfg.limit_seconds, True, False, True)
                if not _pode_criar_sessao(rede):              # rede criando sessões demais (script trocando de cookie)
                    conn.execute("ROLLBACK")
                    return Resolucao("", cfg.limit_seconds, True, False)
                session_id = _new_session_id()
                expires_at = (now + ttl).isoformat()
                conn.execute(
                    "INSERT INTO anon_sessions "
                    "(session_id, fingerprint_hash, active_seconds, last_heartbeat_at, created_at, expires_at, "
                    "fingerprint_estavel_hash, rede_hash) VALUES (?, ?, 0, ?, ?, ?, ?, ?)",
                    (session_id, fingerprint_hash, now_iso, now_iso, expires_at, fingerprint_estavel_hash, rede),
                )
                conn.execute("COMMIT")
                return Resolucao(session_id, 0, False, True)

            session_id, active_seconds, last_heartbeat_at, _expires_at = row
            last_dt = datetime.fromisoformat(last_heartbeat_at)
            delta = now - last_dt
            if delta > ceiling:
                delta = ceiling
            if area == AREA_METERED and delta.total_seconds() > 0:
                # para no limite: depois dele cada /auth/me seguia somando tempo de quem só vê o painel de login
                active_seconds = min(active_seconds + int(delta.total_seconds()), max(active_seconds, cfg.limit_seconds))
            expires_at = (now + ttl).isoformat()
            conn.execute(
                "UPDATE anon_sessions SET active_seconds = ?, last_heartbeat_at = ?, expires_at = ?, "
                "fingerprint_hash = CASE WHEN ? = 1 THEN COALESCE(?, fingerprint_hash) ELSE COALESCE(fingerprint_hash, ?) END, "
                "fingerprint_estavel_hash = COALESCE(fingerprint_estavel_hash, ?), rede_hash = COALESCE(rede_hash, ?) "
                "WHERE session_id = ?",
                (active_seconds, now_iso, expires_at, int(achada_pelo_estavel), fingerprint_hash, fingerprint_hash,
                 fingerprint_estavel_hash, rede, session_id),
            )
            individual = active_seconds >= cfg.limit_seconds
            bloqueio_rede = (not individual) and rede_acima_do_teto(conn, cfg, rede)
            conn.execute("COMMIT")
            return Resolucao(session_id, active_seconds, individual or bloqueio_rede, needs_cookie, bloqueio_rede)
        except Exception:
            conn.execute("ROLLBACK")
            raise


def resolve_and_touch(
    data_dir: Path,
    cfg: AnonSessionConfig,
    cookie_session_id: Optional[str],
    fingerprint_hash: Optional[str],
    area: str = AREA_METERED,
    rede: Optional[str] = None,
    fingerprint_estavel_hash: Optional[str] = None,
) -> tuple[str, int, bool, bool]:
    """`resolver_sessao` no formato antigo: (session_id, active_seconds, limit_reached, cookie_precisa_ser_emitido)."""
    r = resolver_sessao(data_dir, cfg, cookie_session_id, fingerprint_hash, area, rede, fingerprint_estavel_hash)
    return r.session_id, r.active_seconds, r.limit_reached, r.needs_cookie


def peek_limit_reached(data_dir: Path, cfg: AnonSessionConfig, cookie_session_id: Optional[str]) -> bool:
    """Leitura somente-consulta (sem heartbeat), usada pelo guard de requisições comuns."""
    if not cookie_session_id:
        return False
    now_iso = datetime.now(timezone.utc).isoformat()
    with _connect(data_dir) as conn:
        row = conn.execute(
            "SELECT active_seconds, expires_at FROM anon_sessions WHERE session_id = ?",
            (cookie_session_id,),
        ).fetchone()
    if not row:
        return False
    active_seconds, expires_at = row
    if expires_at < now_iso:
        return False
    return active_seconds >= cfg.limit_seconds


@dataclass
class PeekResult:
    found: bool
    active_seconds: int
    limit_reached: bool      # individual esgotado OU rede acima do teto (a mesma regra de `resolver_sessao`)
    identity: str  # cookie | fingerprint | fingerprint_estavel | ipua | none
    bloqueio_rede: bool = False


def peek_state(
    data_dir: Path,
    cfg: AnonSessionConfig,
    cookie_session_id: Optional[str],
    fingerprint_hash: Optional[str] = None,
    ipua_hash: Optional[str] = None,
    fingerprint_estavel_hash: Optional[str] = None,
    rede: Optional[str] = None,
) -> PeekResult:
    """Estado da sessão anônima sem heartbeat: cookie > fingerprint forte > fingerprint estável > hash(IP+UA), mais o teto da rede."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with _connect(data_dir) as conn:
        attempts = []
        if cookie_session_id:
            attempts.append(("cookie", "session_id", cookie_session_id))
        if fingerprint_hash:
            attempts.append(("fingerprint", "fingerprint_hash", fingerprint_hash))
        if fingerprint_estavel_hash:
            attempts.append(("fingerprint_estavel", "fingerprint_estavel_hash", fingerprint_estavel_hash))
        if ipua_hash:
            attempts.append(("ipua", "ipua_hash", ipua_hash))
        achado = None
        for kind, column, value in attempts:
            row = conn.execute(
                f"SELECT active_seconds, expires_at FROM anon_sessions WHERE {column} = ? "
                "ORDER BY last_heartbeat_at DESC LIMIT 1",
                (value,),
            ).fetchone()
            if row and row[1] >= now_iso:
                achado = (kind, row[0])
                break
        individual = achado is not None and achado[1] >= cfg.limit_seconds
        bloqueio_rede = (not individual) and rede_acima_do_teto(conn, cfg, rede)
    if achado is None:
        return PeekResult(False, 0, bloqueio_rede, "none", bloqueio_rede)
    return PeekResult(True, achado[1], individual or bloqueio_rede, achado[0], bloqueio_rede)


def charge_client(
    data_dir: Path, cfg: AnonSessionConfig, ipua_hash: str, cost_seconds: int
) -> bool:
    """Debita `cost_seconds` de um cliente sem cookie/fingerprint (identificado por
    hash(IP+UA)). Devolve True se o limite foi atingido. Cria a linha se preciso."""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    expires = (now + timedelta(hours=cfg.ttl_hours)).isoformat()
    session_id = "ipua:" + ipua_hash[:32]
    with _connect(data_dir) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                "SELECT active_seconds, expires_at FROM anon_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None or row[1] < now_iso:
                conn.execute(
                    "INSERT OR REPLACE INTO anon_sessions "
                    "(session_id, fingerprint_hash, active_seconds, last_heartbeat_at, "
                    "created_at, expires_at, ipua_hash) VALUES (?, NULL, ?, ?, ?, ?, ?)",
                    (session_id, cost_seconds, now_iso, now_iso, expires, ipua_hash),
                )
                total = cost_seconds
            else:
                total = row[0] + cost_seconds
                conn.execute(
                    "UPDATE anon_sessions SET active_seconds = ?, last_heartbeat_at = ? "
                    "WHERE session_id = ?",
                    (total, now_iso, session_id),
                )
            conn.execute("COMMIT")
            return total >= cfg.limit_seconds
        except Exception:
            conn.execute("ROLLBACK")
            raise
