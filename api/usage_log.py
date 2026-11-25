# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Log de uso da API e do MCP.

Objetivo: medir uso (rota/tool, status, bytes, duração, tipo de usuário) para guiar
otimização e, no futuro, cotas — **sem bloquear nada** e **sem dado pessoal em claro**.

Arquivo: `data/ops/usage/AAAA-MM-DD.jsonl` (UTC), uma linha JSON por chamada:
  {"ts","src","kind","route","method","status","bytes","ms","tier","client"}

Privacidade (descrita em /privacidade):
  - `client` = SHA-256(sal-do-dia + IP + User-Agent) truncado em 16 hex. O sal é
    aleatório, gerado por dia e apagado depois de 1 dia, então o identificador
    não liga a mesma pessoa em dias diferentes e não permite recuperar o IP;
  - nenhum IP, cookie, e-mail ou query string é gravado (a rota é o *template*, p. ex.
    `/api/v1/asns/{asn}`, e a querystring é descartada);
  - retenção: `USAGE_LOG_RETENTION_DAYS` (padrão 90) — arquivos mais velhos são apagados.

Desligar: `USAGE_LOG=off`. Falha ao gravar nunca afeta a resposta.
"""
from __future__ import annotations

import functools
import hashlib
import inspect
import json
import logging
import os
import re
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

_log = logging.getLogger("arandurape.usage")

# Rotas de infraestrutura que só gerariam ruído (heartbeat a cada ~45 s por aba).
SKIP_PATHS = ("/health", "/auth/heartbeat", "/api/v1/warmup", "/auth/gate", "/_gate")

# Chamadas internas da própria API (pré-aquecimento do cache) levam este cabeçalho e não entram no log.
INTERNAL_HEADER = "x-arandu-internal"

_NUMERIC_SEG = re.compile(r"^\d+$")
_DATE_SEG = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def enabled() -> bool:
    return os.environ.get("USAGE_LOG", "on").strip().lower() not in ("off", "0", "false", "no")


RETENCAO_PADRAO_DIAS = 90


def retention_days() -> int:
    try:
        return max(1, int(os.environ.get("USAGE_LOG_RETENTION_DAYS", str(RETENCAO_PADRAO_DIAS))))
    except ValueError:
        return RETENCAO_PADRAO_DIAS


def _template_from_scope(scope: dict, path: str) -> Optional[str]:
    """Template completo (com prefixo) a partir da rota casada e dos `path_params`.

    FastAPI >= 0.13x guarda a rota incluída SEM o prefixo do `include_router`
    (`route.path` = `/ixps`, não `/api/v1/ixps`); por isso o template é reconstruído
    do caminho real, trocando o valor de cada parâmetro pelo seu nome."""
    route = scope.get("route")
    if getattr(route, "path", None) is None:
        return None
    template = path
    params = scope.get("path_params") or {}
    # valores mais longos primeiro (conversores `:path` podem conter "/")
    for name, value in sorted(params.items(), key=lambda kv: -len(str(kv[1]))):
        needle = "/" + str(value)
        i = template.find(needle)
        if i >= 0 and str(value):
            template = template[: i + 1] + "{" + name + "}" + template[i + len(needle):]
    return template


def route_template(app, path: str, method: str = "GET") -> Optional[str]:
    """Template da rota (`/api/v1/asns/{asn}`) casando `path` com as rotas do app.

    Usado quando a resposta saiu de um middleware (byte-cache do latest) e o roteador não rodou,
    para que a mesma rota tenha SEMPRE o mesmo nome no log."""
    try:
        from starlette.routing import Match

        scope = {"type": "http", "path": path, "method": method.upper(), "root_path": ""}
        for r in getattr(getattr(app, "router", None), "routes", None) or []:
            # FastAPI recente agrupa as rotas incluídas em `_IncludedRouter`; as rotas efetivas
            # (com o prefixo aplicado) saem de `effective_route_contexts()`.
            flat = r.effective_route_contexts() if hasattr(r, "effective_route_contexts") else [r]
            for c in flat:
                match, child = c.matches(scope)
                if match == Match.FULL:
                    full = {**scope, **(child or {}), "route": c}
                    return _template_from_scope(full, path) or getattr(c, "path", None)
    except Exception:  # noqa: BLE001
        return None
    return None


def normalize_route(path: str) -> str:
    """Fallback quando o template da rota não está disponível: troca ids e datas."""
    parts = path.split("/")
    return "/".join(
        "{n}" if _NUMERIC_SEG.match(p) else "{date}" if _DATE_SEG.match(p) else p for p in parts
    )


class UsageLogger:
    def __init__(self, base_dir: Path):
        self.dir = Path(base_dir) / "ops" / "usage"
        self._lock = threading.Lock()
        self._salt_day: Optional[str] = None
        self._salt: bytes = b""
        self._cleaned_day: Optional[str] = None

    # ── sal rotativo ──────────────────────────────────────────────────────
    def _today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _salt_for(self, day: str) -> bytes:
        if self._salt_day == day and self._salt:
            return self._salt
        path = self.dir / f".salt-{day}"
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            try:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w") as f:
                    f.write(secrets.token_hex(32))
            except FileExistsError:
                pass
            salt = path.read_text().strip().encode()
        except OSError:
            salt = secrets.token_hex(32).encode()  # só em memória: ainda não liga dias
        self._salt_day, self._salt = day, salt
        self._cleanup(day)
        return salt

    def _cleanup(self, day: str) -> None:
        """Apaga sais antigos e arquivos além da retenção (uma vez por dia)."""
        if self._cleaned_day == day:
            return
        self._cleaned_day = day
        try:
            limit = datetime.now(timezone.utc) - timedelta(days=retention_days())
            for p in self.dir.iterdir():
                if p.name.startswith(".salt-"):
                    if p.name != f".salt-{day}":
                        p.unlink(missing_ok=True)
                elif p.suffix == ".jsonl":
                    try:
                        d = datetime.strptime(p.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    except ValueError:
                        continue
                    if d < limit:
                        p.unlink(missing_ok=True)
        except OSError:
            pass

    def client_hash(self, ip: str, user_agent: str = "") -> str:
        salt = self._salt_for(self._today())
        h = hashlib.sha256(salt + b"|" + ip.encode() + b"|" + user_agent.encode()).hexdigest()
        return h[:16]

    # ── gravação ──────────────────────────────────────────────────────────
    def write(self, record: dict) -> None:
        try:
            now = datetime.now(timezone.utc)
            record = {"ts": now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z", **record}
            line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            with self._lock:
                self.dir.mkdir(parents=True, exist_ok=True)
                with open(self.dir / f"{now:%Y-%m-%d}.jsonl", "a", encoding="utf-8") as f:
                    f.write(line + "\n")
        except Exception as exc:  # noqa: BLE001 — log de uso nunca derruba a resposta
            _log.debug("falha ao gravar log de uso: %s", exc)


# ── middleware ASGI (API e MCP) ────────────────────────────────────────────

class UsageLogMiddleware:
    """Middleware ASGI puro: mede status, bytes enviados e duração de cada requisição HTTP.

    Deve ser o MAIS EXTERNO, para registrar também respostas barradas pelo guard.
    O tipo de usuário vem de `scope["state"]["access_tier"]` (preenchido pelo guard).
    """

    _DIR_TTL = 30.0  # segundos entre resoluções de `data_dir()` (testes zeram)

    def __init__(self, app, data_dir, src: str = "api"):
        """`data_dir`: caminho ou função sem argumentos que o devolve (resolvido a cada uso)."""
        self.app = app
        self.src = src
        self._get_dir = data_dir if callable(data_dir) else (lambda: data_dir)
        self._logger: Optional[UsageLogger] = None
        self._resolved_at = 0.0

    @property
    def logger(self) -> UsageLogger:
        # `data_dir()` pode ler config/settings.yaml: resolve no máximo a cada 30 s.
        now = time.monotonic()
        if self._logger is None or now - self._resolved_at > self._DIR_TTL:
            base = Path(self._get_dir())
            self._resolved_at = now
            if self._logger is None or self._logger.dir != base / "ops" / "usage":
                self._logger = UsageLogger(base)
        return self._logger

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not enabled():
            return await self.app(scope, receive, send)
        path = scope.get("path", "")
        if path.startswith(SKIP_PATHS):
            return await self.app(scope, receive, send)
        if any(k.decode("latin-1").lower() == INTERNAL_HEADER for k, _ in scope.get("headers", [])):
            return await self.app(scope, receive, send)

        t0 = time.perf_counter()
        status = 0
        sent = 0

        async def send_wrapper(message):
            nonlocal status, sent
            if message["type"] == "http.response.start":
                status = message["status"]
            elif message["type"] == "http.response.body":
                sent += len(message.get("body") or b"")
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            try:
                route = (_template_from_scope(scope, path)
                         or route_template(scope.get("app"), path, scope.get("method", "GET"))
                         or normalize_route(path))
                headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
                client = scope.get("client")
                ip = _normalize_ip(headers.get("x-real-ip") or (client[0] if client else "?"))
                state: Any = scope.get("state") or {}
                tier = state.get("access_tier") if isinstance(state, dict) else getattr(state, "access_tier", None)
                self.logger.write({
                    "src": self.src,
                    "kind": "http",
                    "route": route,
                    "method": scope.get("method", ""),
                    "status": status,
                    "bytes": sent,
                    "ms": round((time.perf_counter() - t0) * 1000, 1),
                    "tier": tier,
                    "client": self.logger.client_hash(ip, headers.get("user-agent", "")),
                })
                conta_id = state.get("conta_id") if isinstance(state, dict) else getattr(state, "conta_id", None)
                if conta_id and self.src == "api":              # registro por conta: arquivo separado, ver api/uso_conta.py e /privacidade 2.3
                    from api import uso_conta
                    from api.auth import access_policy
                    origem = "site" if headers.get("sec-fetch-site") in ("same-origin", "same-site") else "api"
                    classe = access_policy.classify(scope.get("method", "GET"), path, {}, None).cls
                    uso_conta.registrar(Path(self._get_dir()), conta_id, origem, route, status, sent, (time.perf_counter() - t0) * 1000, classe)
            except Exception as exc:  # noqa: BLE001
                _log.debug("falha no log de uso: %s", exc)


def _normalize_ip(raw: str) -> str:
    from api.auth.deps import normalize_ip

    return normalize_ip(raw) or "?"


# ── instrumentação das tools do MCP ────────────────────────────────────────

def instrument_mcp_tools(mcp, data_dir) -> int:
    """Envolve cada tool registrada do FastMCP para registrar nome, duração e tamanho.

    Usa `mcp._tool_manager._tools` (API interna do FastMCP); o teste
    `test_instrument_mcp_tools` falha se a biblioteca mudar essa estrutura.
    Devolve o número de tools instrumentadas.
    """
    # `data_dir` pode ser caminho ou função sem argumentos (como no middleware).
    logger = UsageLogger(Path(data_dir() if callable(data_dir) else data_dir))
    tools = getattr(getattr(mcp, "_tool_manager", None), "_tools", None)
    if not isinstance(tools, dict):
        return 0
    count = 0
    for name, tool in tools.items():
        fn = getattr(tool, "fn", None)
        if fn is None or getattr(fn, "_usage_logged", False):
            continue

        def make(fn=fn, name=name):
            def record(t0: float, status: str, result: Any = None) -> None:
                if not enabled():
                    return
                size = None
                if status == "ok":
                    try:
                        size = len(result) if isinstance(result, str) else len(json.dumps(result, default=str))
                    except Exception:  # noqa: BLE001
                        size = None
                logger.write({
                    "src": "mcp", "kind": "tool", "route": f"tool:{name}", "method": "CALL",
                    "status": status, "bytes": size, "ms": round((time.perf_counter() - t0) * 1000, 1),
                    "tier": None, "client": None,
                })

            if inspect.iscoroutinefunction(fn):
                @functools.wraps(fn)
                async def wrapper(*a, **kw):
                    t0 = time.perf_counter()
                    try:
                        result = await fn(*a, **kw)
                    except Exception:
                        record(t0, "erro")
                        raise
                    record(t0, "ok", result)
                    return result
            else:
                @functools.wraps(fn)
                def wrapper(*a, **kw):
                    t0 = time.perf_counter()
                    try:
                        result = fn(*a, **kw)
                    except Exception:
                        record(t0, "erro")
                        raise
                    record(t0, "ok", result)
                    return result
            wrapper._usage_logged = True  # type: ignore[attr-defined]
            return wrapper

        tool.fn = make()
        count += 1
    return count
