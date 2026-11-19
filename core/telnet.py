# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Cliente Telnet/BGP assíncrono — usado por `lg_ixbr` (lg_ixbr).

Arquitetura:
  - Conexão TCP pura via asyncio (sem o módulo telnetlib, deprecated no Python 3.11)
  - Protocolo IAC (RFC 854) tratado inline: todas as opções são recusadas (DONT/WONT)
  - Suporte a três variantes de firmware: FRR >= 7, FRR older, Quagga
  - Detecção ativa de fim de tabela: encerra assim que o roteador imprime
    "Displayed N routes..." ou "Total number of prefixes" — sem depender só de timeout

Estratégia de encerramento (o que ocorrer primeiro):
  1. Marcador de fim de tabela detectado no buffer acumulado
  2. idle_timeout de inatividade (nenhum novo dado recebido)
  3. total_timeout absoluto esgotado
"""

from __future__ import annotations

import asyncio

# ---------------------------------------------------------------------------
# Comandos BGP por AFI — em ordem de preferência (fallback de firmware)
# ---------------------------------------------------------------------------

AFI_COMMANDS: dict[str, list[str]] = {
    "v4": ["show ip bgp"],
    "v6": [
        "show bgp ipv6 unicast",  # FRR >= 7
        "show ipv6 bgp",          # Quagga / FRR older
        "show bgp ipv6",          # variante de alguns firmwares
    ],
}

# Enviado ao roteador antes do comando BGP para desabilitar paginação.
INIT_CMDS = ["terminal length 0"]

# ---------------------------------------------------------------------------
# Constantes do protocolo Telnet/IAC (RFC 854)
# ---------------------------------------------------------------------------

_IAC  = 255  # Interpret As Command — prefixo de todas as sequências de controle
_WILL = 251  # Oferta de ativação de opção pelo servidor
_WONT = 252  # Recusa de ativação de opção pelo servidor
_DO   = 253  # Pedido para o cliente ativar uma opção
_DONT = 254  # Pedido para o cliente desativar uma opção
_SB   = 250  # Início de sub-negociação
_SE   = 240  # Fim de sub-negociação


def _process_iac(buf: bytes) -> tuple[bytes, bytes, bytes]:
    """Processa sequências IAC em buf e separa dados de texto dos comandos Telnet.

    Estratégia de negociação: recusa tudo (DONT para WILL, WONT para DO).
    Suficiente para os LGs do IX.br; nenhuma opção Telnet é necessária.

    Retorna:
        clean:      bytes de texto limpo (sem IAC)
        responses:  bytes de resposta a enviar ao servidor (recusas de opções)
        remainder:  bytes não processados (sequência IAC incompleta no fim do buf)
    """
    clean = bytearray()
    responses = bytearray()
    i = 0

    while i < len(buf):
        b = buf[i]
        if b != _IAC:
            clean.append(b)
            i += 1
            continue

        if i + 1 >= len(buf):
            # Sequência IAC truncada — devolve para o próximo chunk
            return bytes(clean), bytes(responses), buf[i:]

        cmd = buf[i + 1]

        if cmd == _IAC:
            # IAC IAC = byte literal 255
            clean.append(_IAC)
            i += 2
        elif cmd in (_WILL, _WONT, _DO, _DONT):
            if i + 2 >= len(buf):
                return bytes(clean), bytes(responses), buf[i:]
            opt = buf[i + 2]
            if cmd == _WILL:
                responses.extend([_IAC, _DONT, opt])
            elif cmd == _DO:
                responses.extend([_IAC, _WONT, opt])
            # WONT e DONT não exigem resposta
            i += 3
        elif cmd == _SB:
            # Sub-negociação: descarta tudo até IAC SE
            j = i + 2
            while j < len(buf) - 1:
                if buf[j] == _IAC and buf[j + 1] == _SE:
                    i = j + 2
                    break
                j += 1
            else:
                return bytes(clean), bytes(responses), buf[i:]
        else:
            # Comando IAC de dois bytes desconhecido — ignora
            i += 2

    return bytes(clean), bytes(responses), b""


# Marcadores que FRR/Quagga imprime ao final da tabela BGP.
# Detectar qualquer um deles permite encerrar sem aguardar idle_timeout.
_BGP_END_MARKERS = (
    b"Displayed ",               # "Displayed 49272 routes and 49272 total paths"
    b"Total number of prefixes", # variantes mais antigas do FRR/Quagga
    b"No BGP prefixes displayed",  # tabela vazia: o FRR não imprime cabeçalho nem "Displayed"
)


def _bgp_table_ended(buf: bytes) -> bool:
    """Retorna True se o buffer contém o marcador de fim de tabela BGP."""
    for marker in _BGP_END_MARKERS:
        if marker in buf:
            return True
    return False


async def telnet_collect(
    host: str,
    port: int,
    commands: list[str],
    connect_timeout: float,
    idle_timeout: float,
    total_timeout: float,
) -> str:
    """Abre sessão TCP/Telnet, envia comandos e coleta a tabela BGP completa.

    Args:
        host:            Endereço do LG (ex: "sp.ix.br")
        port:            Porta Telnet (geralmente 23)
        commands:        Lista de comandos a enviar em sequência (ex: ["terminal length 0", "show ip bgp"])
        connect_timeout: Timeout da conexão TCP inicial (segundos)
        idle_timeout:    Timeout de inatividade — encerra se não receber dados por este período
        total_timeout:   Timeout absoluto — encerra independente do estado de coleta

    Returns:
        Texto completo recebido do roteador, decodificado como UTF-8 (erros ignorados).

    Raises:
        asyncio.TimeoutError: se connect_timeout for ultrapassado
        ConnectionRefusedError: se a porta Telnet recusar conexão
        OSError: outros erros de rede
    """
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(host, port, happy_eyeballs_delay=0.25),
        timeout=connect_timeout,
    )

    collected = bytearray()
    buf = bytearray()

    try:
        async with asyncio.timeout(total_timeout):
            # Lê banner inicial (prompt de login, negociação IAC)
            try:
                initial = await asyncio.wait_for(reader.read(4096), timeout=5.0)
            except asyncio.TimeoutError:
                initial = b""

            if initial:
                clean, responses, remainder = _process_iac(initial)
                collected.extend(clean)
                buf.extend(remainder)
                if responses:
                    writer.write(responses)

            # Envia todos os comandos de uma vez
            for cmd in commands:
                writer.write((cmd + "\r\n").encode("ascii", errors="replace"))
            await writer.drain()

            while True:
                if buf:
                    clean, responses, remainder = _process_iac(bytes(buf))
                    collected.extend(clean)
                    buf = bytearray(remainder)
                    if responses:
                        writer.write(responses)
                        await writer.drain()

                if _bgp_table_ended(collected):
                    break  # encerramento ativo: roteador sinalizou fim da tabela

                try:
                    chunk = await asyncio.wait_for(
                        reader.read(65536), timeout=idle_timeout
                    )
                except asyncio.TimeoutError:
                    break  # fallback: silêncio prolongado = tabela provavelmente completa

                if not chunk:
                    break  # conexão fechada pelo servidor

                buf.extend(chunk)

    finally:
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=2.0)
        except Exception:
            pass

    return collected.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Validação de resposta BGP
# ---------------------------------------------------------------------------

# Presença de qualquer um destes strings indica resposta BGP válida
_BGP_VALID_MARKERS = ("BGP table version", "Network          Next Hop", "No BGP prefixes displayed")

# Resposta válida de uma tabela sem rotas (ex.: IX recém-implantado, route servers sem membros anunciando).
# O FRR responde só esta linha, sem cabeçalho; é coleta correta, não falha.
BGP_EMPTY_MARKER = "No BGP prefixes displayed"

# Presença de qualquer um destes strings indica comando inválido para o firmware
_BGP_ERROR_MARKERS = (
    "% Unknown command",
    "% Invalid input",
    "% Incomplete command",
    "% Command incomplete",
    "% No match",
)


def _is_valid_bgp_response(text: str) -> bool:
    """Retorna True se text contém cabeçalho BGP válido e nenhuma mensagem de erro."""
    for err in _BGP_ERROR_MARKERS:
        if err in text:
            return False
    for marker in _BGP_VALID_MARKERS:
        if marker in text:
            return True
    return False


# ---------------------------------------------------------------------------
# Ponto de entrada público: coleta de um AFI com fallback de comandos
# ---------------------------------------------------------------------------

async def collect_afi(
    host: str,
    port: int,
    afi: str,
    connect_timeout: float,
    idle_timeout: float,
    total_timeout: float,
) -> dict:
    """Tenta cada comando do AFI em ordem e retorna o primeiro com resposta válida.

    A ordem dos comandos em AFI_COMMANDS implementa o fallback de firmware:
    tenta FRR >= 7 primeiro, depois Quagga e variantes mais antigas.

    Args:
        host, port:      Endereço do LG
        afi:             "v4" ou "v6"
        connect_timeout: Timeout da conexão TCP
        idle_timeout:    Timeout de inatividade por leitura
        total_timeout:   Timeout absoluto da sessão

    Returns:
        Em sucesso:  {"status": "ok",    "command": str, "text": str}
        Em falha:    {"status": "error", "command": str, "error": str}
    """
    last_error = ""
    for cmd in AFI_COMMANDS[afi]:
        try:
            text = await telnet_collect(
                host, port,
                INIT_CMDS + [cmd],
                connect_timeout, idle_timeout, total_timeout,
            )
            if _is_valid_bgp_response(text):
                return {"status": "ok", "command": cmd, "text": text}
            last_error = f"no BGP header in response to '{cmd}'"
        except asyncio.TimeoutError:
            last_error = f"timeout on '{cmd}'"
        except ConnectionRefusedError:
            return {"status": "error", "command": cmd, "error": "connection refused"}
        except OSError as exc:
            last_error = f"OS error on '{cmd}': {exc}"

    return {"status": "error", "command": "", "error": last_error}
