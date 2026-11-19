# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Pré-compressão brotli-11 das camadas estáticas endereçadas por conteúdo.

`/api/v1/map/<camada>?v=<hash>` é imutável: a URL identifica os bytes. Comprimir em nível 11 ganha −20% a −28% sobre o gzip-9 da API
(medido no ambiente de teste), mas leva 8–16 s por resposta — viável só **uma vez por URL**, fora do pedido. Por isso:

  * cliente que aceita `br` e já existe `data/cache/br11/<sha256(caminho|v)>.br`: a API serve o arquivo (sem rodar a rota, sem CPU);
  * ainda não existe: a resposta sai como hoje (o nginx a comprime em nível 6), marcada `X-Accel-Expires: 0` para o proxy_cache do nginx
    não guardar por 7 dias a versão menos compacta, e a compressão roda em segundo plano, uma só vez por URL;
  * sem a biblioteca `brotli`, o middleware não faz nada.

É ASGI puro e fica **dentro** do GZip (o primeiro `add_middleware`), para enxergar o corpo ainda sem gzip. O arquivo é só cache: pode ser
apagado a qualquer momento (volta a ser gerado no próximo pedido).
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional, Union
from urllib.parse import parse_qs

try:
    import brotli
except ImportError:  # pragma: no cover - a imagem instala; o resto roda sem
    brotli = None

_log = logging.getLogger("arandurape")

_V = re.compile(r"^[0-9a-f]{16}$")
_ACEITA_BR = re.compile(r"(^|[ ,])br([ ,;]|$)", re.I)
_MAX_CORPO = 256 * 1024 * 1024        # a camada de rodovias tem ~135 MB sem compressão; o nível 11 leva alguns minutos, uma vez
IMUTAVEL = b"public, max-age=31536000, immutable"
_MAX_PENDENTES = 4                    # compressões na fila ao mesmo tempo (cada uma segura o corpo da camada em memória)
# Versão da chave do arquivo: muda quando a regra de quem entra no cache muda, e os arquivos de outra versão deixam de ser lidos (arquivo
# gravado sob outra regra pode não ter passado pela validação do hash). São só cache e podem ser apagados.
_VERSAO_CHAVE = "2"


class PreBrotliMiddleware:
    def __init__(self, app, data_dir: Union[Path, Callable[[], Path]], executor: Optional[ThreadPoolExecutor] = None, nivel: int = 11,
                 max_corpo: int = _MAX_CORPO, caminhos: Optional[frozenset] = None, max_pendentes: int = _MAX_PENDENTES):
        """`caminhos`: as rotas das camadas estáticas (`_CAMADAS_ESTATICAS` de `api/routes/map.py`); `None` aceita qualquer `/api/v1/map/`
        (só para testes). Em qualquer caso a resposta só vira arquivo se a rota validou o `v` (`request.state.cache_imutavel`)."""
        self.app = app
        self._caminhos = frozenset(caminhos) if caminhos is not None else None
        self._max_pendentes = max_pendentes
        self._data_dir = data_dir
        self._executor = executor or ThreadPoolExecutor(max_workers=1, thread_name_prefix="prebrotli")
        self._nivel = nivel
        self._max_corpo = max_corpo
        self._em_andamento: set[str] = set()

    def _pasta(self) -> Path:
        base = self._data_dir() if callable(self._data_dir) else self._data_dir
        return Path(base) / "cache" / "br11"

    def _arquivo(self, caminho: str, v: str) -> Path:
        return self._pasta() / (hashlib.sha256(f"{_VERSAO_CHAVE}|{caminho}|{v}".encode()).hexdigest() + ".br")

    def _candidato(self, scope) -> Optional[tuple[str, str]]:
        """(caminho, v) se o pedido é uma camada estática por hash, com `v` como ÚNICO parâmetro, de um cliente que aceita brotli; senão None.

        a chave ignorava os outros parâmetros, e `?v=<hash>&sigla=<nada>` gravava (e servia a todos,
        imutável por 1 ano) uma resposta vazia; qualquer rota de `/map/` com `v` aleatório enchia o disco e a fila."""
        if scope["type"] != "http" or scope["method"] != "GET" or not scope["path"].startswith("/api/v1/map/"):
            return None
        if self._caminhos is not None and scope["path"] not in self._caminhos:
            return None
        cab = {k.lower(): val for k, val in scope["headers"]}
        if not _ACEITA_BR.search(cab.get(b"accept-encoding", b"").decode("latin-1")):
            return None
        qs = parse_qs(scope.get("query_string", b"").decode("latin-1"), keep_blank_values=True)
        if list(qs) != ["v"] or len(qs["v"]) != 1:
            return None
        v = qs["v"][0]
        return (scope["path"], v) if _V.match(v) else None

    async def __call__(self, scope, receive, send):
        alvo = self._candidato(scope) if brotli is not None else None
        if alvo is None:
            return await self.app(scope, receive, send)
        arquivo = self._arquivo(*alvo)
        try:
            dados = arquivo.read_bytes()
        except OSError:
            dados = None
        if dados is not None:
            # a rota não roda: marca o estado para o middleware de cabeçalhos tratar como camada imutável (Cache-Control de 1 ano)
            scope.setdefault("state", {})["cache_imutavel"] = True
            await send({"type": "http.response.start", "status": 200, "headers": [
                (b"content-type", b"application/json"), (b"content-encoding", b"br"), (b"vary", b"Accept-Encoding"),
                (b"cache-control", IMUTAVEL), (b"content-length", str(len(dados)).encode()),
            ]})
            return await send({"type": "http.response.body", "body": dados})

        partes: list[bytes] = []
        estado = {"ok": False, "tamanho": 0}

        async def captura(msg):
            if msg["type"] == "http.response.start":
                # só guarda o que a rota reconheceu como a versão de uma camada (o `v` existe): `v` inventado dá 404 ou não marca
                validado = bool((scope.get("state") or {}).get("cache_imutavel"))
                estado["ok"] = validado and msg["status"] == 200 and not any(k.lower() == b"content-encoding" for k, _ in msg["headers"])
                if estado["ok"]:
                    msg = {**msg, "headers": [*msg["headers"], (b"x-accel-expires", b"0")]}
            elif msg["type"] == "http.response.body" and estado["ok"]:
                estado["tamanho"] += len(msg.get("body", b""))
                if estado["tamanho"] > self._max_corpo:
                    if estado["ok"]:
                        _log.info("camada grande demais para pré-comprimir (> %d bytes): %s", self._max_corpo, arquivo.name)
                    estado["ok"] = False
                    partes.clear()
                else:
                    partes.append(msg.get("body", b""))
                    if not msg.get("more_body"):
                        corpo = b"".join(partes)
                        partes.clear()                       # não segura duas cópias da camada enquanto o nível 11 roda
                        self._agendar(arquivo, corpo)
            await send(msg)

        await self.app(scope, receive, captura)

    def _agendar(self, arquivo: Path, corpo: bytes) -> None:
        chave = str(arquivo)
        if chave in self._em_andamento or arquivo.exists():
            return
        if len(self._em_andamento) >= self._max_pendentes:
            _log.info("fila de pré-compressão cheia (%d): %s fica para o próximo pedido", self._max_pendentes, arquivo.name)
            return
        self._em_andamento.add(chave)
        self._executor.submit(self._comprimir, arquivo, corpo)

    def _comprimir(self, arquivo: Path, corpo: bytes) -> None:
        try:
            arquivo.parent.mkdir(parents=True, exist_ok=True)
            tmp = arquivo.with_suffix(f".tmp{os.getpid()}")
            tmp.write_bytes(brotli.compress(corpo, quality=self._nivel, mode=brotli.MODE_TEXT))
            os.replace(tmp, arquivo)                           # escrita atômica
            _log.info("brotli-%d pronto: %s (%d -> %d bytes)", self._nivel, arquivo.name, len(corpo), arquivo.stat().st_size)
        except Exception as exc:                               # nunca derruba o pedido; o arquivo é só cache
            _log.warning("pré-compressão brotli falhou (%s): %s", arquivo.name, exc)
        finally:
            self._em_andamento.discard(str(arquivo))
