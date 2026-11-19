# SPDX-License-Identifier: AGPL-3.0-or-later
"""Servidor Telnet falso de Looking Glass (FRR do IX.br) para testes T1.

Reproduz: banner, negociação IAC, `terminal length 0`, `show ip bgp`, `show bgp ipv6 unicast`
(e as variantes antigas), erro `% Unknown command` de firmware antigo, silêncio (timeout) e
tabela sem o marcador final (encerra por inatividade).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

IAC, DO, WONT, DONT, WILL = 255, 253, 252, 254, 251


@dataclass
class LGBehavior:
    v4_text: str = ""
    v6_text: str = ""
    v6_commands: tuple[str, ...] = ("show bgp ipv6 unicast", "show ipv6 bgp", "show bgp ipv6")   # comandos aceitos
    negotiate: bool = True
    silent: bool = False            # aceita a conexão e não responde (testa timeout)
    no_end_marker: bool = False     # não imprime "Displayed N routes" (testa idle timeout)
    received: list[str] = field(default_factory=list)
    iac_replies: list[bytes] = field(default_factory=list)


class FakeLG:
    def __init__(self, behavior: LGBehavior):
        self.b = behavior
        self.server: asyncio.AbstractServer | None = None
        self.port = 0

    async def __aenter__(self) -> "FakeLG":
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]
        return self

    async def __aexit__(self, *exc) -> None:
        self.server.close()
        await self.server.wait_closed()

    def _body(self, text: str) -> str:
        if self.b.no_end_marker:
            return "\n".join(l for l in text.splitlines() if not l.startswith("Displayed")) + "\n"
        return text

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            if self.b.silent:
                while await reader.read(1024):     # aceita e não responde; sai quando o cliente fecha
                    pass
                return
            banner = b"==============\r\n= IX.br Looking Glass =\r\n==============\r\n"
            if self.b.negotiate:
                banner = bytes([IAC, DO, 24, IAC, WILL, 1]) + banner       # DO TERMINAL-TYPE, WILL ECHO
            writer.write(banner + b"lg.fake.ix.br> ")
            await writer.drain()
            buf = b""
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    return
                # separa respostas IAC (começam por 255) do texto
                while IAC in chunk:
                    i = chunk.index(IAC)
                    self.b.iac_replies.append(chunk[i:i + 3])
                    chunk = chunk[:i] + chunk[i + 3:]
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    cmd = line.decode("ascii", "ignore").strip()
                    if not cmd:
                        continue
                    self.b.received.append(cmd)
                    out = self._answer(cmd)
                    writer.write(f"{cmd}\r\n".encode() + out.replace("\n", "\r\n").encode("utf-8") + b"lg.fake.ix.br> ")
                    await writer.drain()
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        finally:
            writer.close()

    def _answer(self, cmd: str) -> str:
        if cmd == "terminal length 0":
            return ""
        if cmd == "show ip bgp":
            return self._body(self.b.v4_text)
        if cmd in self.b.v6_commands:
            return self._body(self.b.v6_text)
        return "% Unknown command: " + cmd + "\n"
