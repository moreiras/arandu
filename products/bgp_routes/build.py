# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`bgp_ixp` — Parser BGP

Transforma saídas Telnet brutas em JSON normalizado:

    data/raw/{date}/{ixp}/bgp-{afi}-{ixp}-{date}.txt
        →
    data/normalized/{date}/{ixp}/routes-{afi}.json.gz
    data/normalized/{date}/{ixp}/origin-prefixes-{afi}.json.gz  ← {str(asn): [prefixo...]}
    data/normalized/{date}/{ixp}/prefix-set-{afi}.json.gz       ← [prefixo...]

Formatos de saída BGP observados nos LGs do IX.br (FRR/Quagga):

  IPv4 — rota de linha única:
    *> 1.0.0.0/24   200.192.108.14   10   0 16735 22548 i

  IPv6 — rota de duas linhas (nexthop + AS_PATH não cabem na mesma linha):
    *  2001:500:3::/48  2001:12f8:0:11::14
                                           0 16735 20144 i

  IPv6 — rota de três linhas (FRR mais recente):
    *  2001:500:3::/48
       2001:12f8:0:11::14
                         0 16735 20144 i

  "Continuation" — mesmo prefixo, caminho alternativo (segunda rota):
    *>                  200.192.108.14   10   0 52925 i

  FRR 8.x — prefixo RPKI antes dos status codes:
    V*>i1.0.0.0/24 ... (V=valid, N=not-found, I=invalid)

Relações inferidas do AS_PATH calculadas por compute_relationships():
    asn_direct: primeiro ASN do caminho (peer direto no IXP)
    asn_origin: último ASN do caminho (originador do prefixo)
    asn_relate: pares (asn_direct, asn_origin) — inferência, não fato contratual
    asn_stub:   asn_direct com exatamente 1 asn_origin distinto (AS folha)

Uso:
    python -m products.bgp_routes.build --date 2026-06-06
    python -m products.bgp_routes.build --date 2026-06-06 --ixp cas laj
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from core.ixp_peers import estatisticas_por_peer
from core.common import (
    raw_bgp_ixp,
    ler_texto_bruto,
    raw_existente,
    configure_logging,
    data_dir,
    load_ixps,
    normalized_path,
    now_iso,
    raw_path,
    today_str,
    write_json_gz,
)

# ---------------------------------------------------------------------------
# Expressões regulares para parsing de linhas BGP
# ---------------------------------------------------------------------------

# AS_PATH no fim de um trecho: um ou mais ASNs separados por espaço + código de origem.
# Aplicado DEPOIS de fatiar a linha a partir da coluna Path — exclui metric/locpref/weight.
_ASPATH_RE = re.compile(r'\b((?:\d+\s+)*\d+)\s+([ie?])\s*$')

# Prefixo IPv4 com comprimento: ex. 1.0.0.0/24
# (?<!\d) em vez de \b: no FRR 8.x o código RPKI "V*>i" precede diretamente o prefixo
# sem espaço (ex: "V*>i1.0.0.0/24"), e \b falha entre "i" (não-dígito) e "1" (dígito).
_V4_PREFIX_RE = re.compile(r'(?<!\d)(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2})\b')

# Prefixo IPv6 com comprimento: ex. 2001:500:3::/48
# (?<![0-9a-fA-F:]) pela mesma razão: evita capturar parte de um endereço maior.
_V6_PREFIX_RE = re.compile(
    r'(?<![0-9a-fA-F:])([0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{0,4}){1,7}/\d{1,3})\b'
)

# Flags de status BGP: *, >, espaço, s (suppressed), i (history)
_ROUTE_STATUS_RE = re.compile(r'^([*> si]{1,4})')

# FRR 8.x prefixa rotas com código de validação RPKI antes dos flags padrão.
# V = valid, N = not-found, I = invalid
_RPKI_ROUTE_RE = re.compile(r'^[VNI][* i]')

# Linha de cabeçalho de colunas: presente no início da tabela BGP.
# Exemplo: "   Network          Next Hop            Metric LocPrf Weight Path"
_COL_HEADER_RE = re.compile(r'\bNetwork\b.*\bPath\b')

# Prefixos de linhas que são metadados da sessão BGP (não rotas) e devem ser ignoradas.
_HEADER_STARTS = (
    "BGP table version",
    "Default local pref",
    "Status codes",
    "Nexthop codes",
    "Origin codes",
    "RPKI",
    "   Network",
    "Total number",
    "Displayed",
)


def _is_header_line(line: str) -> bool:
    """Retorna True se a linha é metadado/cabeçalho BGP (não uma entrada de rota).

    Reconhece três tipos de linhas não-rota:
    1. Linhas que começam com prefixos de metadados conhecidos (_HEADER_STARTS)
    2. Linha de cabeçalho de colunas ("Network ... Path")
    3. Linhas de continuação de descrição de status codes: muito indentadas,
       começam com letra (não dígito) — distinguíveis das continuações de AS_PATH
       que começam com dígito.
    """
    stripped = line.strip()
    if not stripped:
        return True
    for h in _HEADER_STARTS:
        if stripped.startswith(h) or line.startswith(h):
            return True
    if _COL_HEADER_RE.search(line):
        return True
    # Descrições de status codes: linha muito indentada (≥14 espaços) sem '*'
    if line.startswith("              ") and "*" not in line[:20]:
        after = line.lstrip()
        if after and not after[0].isdigit():
            return True
    return False


def _is_route_line(stripped: str) -> bool:
    """True se a linha (já lstripped) inicia uma entrada de rota BGP.

    Uma linha de rota começa com '*' (rota válida) ou com código RPKI V/N/I
    seguido de flag de status (formato FRR 8.x).
    """
    if not stripped:
        return False
    return stripped[0] == '*' or bool(_RPKI_ROUTE_RE.match(stripped))


def _extract_prefix(line: str) -> str | None:
    """Extrai prefixo IPv4 ou IPv6 com /len da linha. Retorna None se não encontrado."""
    m = _V4_PREFIX_RE.search(line)
    if m:
        return m.group(1)
    m = _V6_PREFIX_RE.search(line)
    if m:
        return m.group(1)
    return None


def _extract_aspath(line: str) -> tuple[list[int], str] | None:
    """Extrai AS_PATH e código de origem do fim da linha.

    Busca o padrão: um ou mais números separados por espaço + código de origem (i/e/?).
    O código de origem indica: i = IGP, e = EGP, ? = incomplete.

    Returns:
        (lista_de_asns, código_de_origem) ou None se não encontrado.
    """
    m = _ASPATH_RE.search(line)
    if not m:
        return None
    aspath = [int(x) for x in m.group(1).split()]
    return aspath, m.group(2)


def _extract_status(line: str) -> str:
    """Extrai flags de status BGP (*, >, i etc.) dos primeiros caracteres da linha."""
    m = _ROUTE_STATUS_RE.match(line)
    return m.group(1).strip() if m else ""


# ---------------------------------------------------------------------------
# Parser principal
# ---------------------------------------------------------------------------

def _path_slice(line: str, path_col: int | None) -> str:
    """Retorna o trecho da linha a partir da coluna Path, excluindo metric/locpref/weight.

    Quando path_col é conhecido (detectado do cabeçalho de colunas), fatia a linha
    a partir dessa posição — garante que os números de metric, locpref e weight
    que precedem o AS_PATH não sejam confundidos com ASNs.

    Recua até o início da palavra caso path_col caia no meio de um número
    (situação comum em linhas de continuação IPv6, onde o primeiro ASN pode
    começar alguns caracteres antes da coluna "Path" do cabeçalho).

    Sem path_col (não detectado), devolve a linha inteira como fallback.
    """
    if path_col is None or len(line) <= path_col:
        return line
    i = path_col
    while i > 0 and line[i - 1] not in (' ', '\t'):
        i -= 1
    return line[i:]


def parse_bgp_output(text: str) -> list[dict]:
    """Parseia saída completa de 'show ip bgp' ou 'show bgp ipv6 unicast'.

    Estratégia para extrair o AS_PATH sem incluir metric/locpref/weight:
      - Detecta o cabeçalho de colunas ("Network ... Path") e salva path_col
      - Fatia cada linha a partir de path_col antes de aplicar o regex de AS_PATH

    Máquina de estados para rotas multi-linha:
      - `pending`: guarda prefixo+status quando o AS_PATH não aparece na mesma linha
      - `current_prefix`: propaga o prefixo para linhas de continuation

    Returns:
        Lista de dicts com chaves: prefix, status, aspath (list[int]), origin, nexthop.
    """
    routes: list[dict] = []
    current_prefix: str | None = None
    pending: dict | None = None  # rota incompleta aguardando AS_PATH na próxima linha
    path_col: int | None = None  # índice da coluna "Path" no cabeçalho

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue

        # Detecta linha de cabeçalho de colunas para obter path_col
        if path_col is None and _COL_HEADER_RE.search(line):
            idx = line.rfind("Path")
            if idx >= 0:
                path_col = idx
            continue

        stripped = line.lstrip()

        # Prioridade 1: continuação de rota pendente (linha sem início de rota)
        if pending is not None and not _is_route_line(stripped):
            path_part = _path_slice(line, path_col)
            result = _extract_aspath(path_part)
            if result:
                aspath, origin = result
                routes.append({
                    "prefix":  pending["prefix"],
                    "status":  pending["status"],
                    "aspath":  aspath,
                    "origin":  origin,
                    "nexthop": "",
                })
                pending = None
            # else: linha de nexthop em formato IPv6 de 3 linhas — mantém pending
            continue

        # Prioridade 2: linhas de cabeçalho/metadado — descarta
        if _is_header_line(line):
            pending = None
            continue

        # Prioridade 3: deve ser linha de rota — descarta se não for
        if not _is_route_line(stripped):
            pending = None
            continue

        status = _extract_status(line)
        prefix = _extract_prefix(line)
        if prefix:
            current_prefix = prefix

        if current_prefix is None:
            continue

        # Tenta extrair AS_PATH apenas a partir da coluna Path
        path_part = _path_slice(line, path_col)
        result = _extract_aspath(path_part)

        if result:
            aspath, origin = result
            routes.append({
                "prefix":  current_prefix,
                "status":  status,
                "aspath":  aspath,
                "origin":  origin,
                "nexthop": "",
            })
            pending = None
        else:
            # AS_PATH não está nesta linha — rota multi-linha (IPv6 típico)
            pending = {"prefix": current_prefix, "status": status}

    return routes


# ---------------------------------------------------------------------------
# Cálculo de relações inferidas do AS_PATH
# ---------------------------------------------------------------------------

def compute_relationships(routes: list[dict]) -> dict:
    """Calcula relações inferidas do AS_PATH para o conjunto de rotas de uma fonte.

    Definições:
      asn_direct: ASNs que aparecem como PRIMEIRO elemento do AS_PATH — representam
                  o peer direto no IXP (quem anuncia diretamente ao Route Server).
      asn_origin: ASNs que aparecem como ÚLTIMO elemento do AS_PATH — representam
                  o AS que originou o prefixo (atribuição RIR).
      asn_relate: Conjunto de pares (asn_direct, asn_origin) observados — captura
                  quais origens chegam através de qual peer direto. Inferência do
                  AS_PATH observado, não relação contratual verificada.
      asn_stub:   asn_direct que tem exatamente 1 asn_origin distinto — indício de
                  AS folha (cliente único, sem downstream próprio visível no IXP).

    Returns:
        Dict com "asn_direct", "asn_origin", "asn_relate", "asn_stub" (todos sorted).
    """
    asn_direct: set[int] = set()
    asn_origin: set[int] = set()
    asn_relate: set[tuple[int, int]] = set()
    direct_to_origins: dict[int, set[int]] = {}

    for route in routes:
        aspath = route.get("aspath", [])
        if not aspath:
            continue

        first = aspath[0]
        last  = aspath[-1]

        asn_direct.add(first)
        asn_origin.add(last)
        asn_relate.add((first, last))

        if first not in direct_to_origins:
            direct_to_origins[first] = set()
        direct_to_origins[first].add(last)

    asn_stub = {asn for asn, origins in direct_to_origins.items() if len(origins) == 1}

    return {
        "asn_direct": sorted(asn_direct),
        "asn_origin": sorted(asn_origin),
        "asn_relate": sorted(asn_relate),
        "asn_stub":   sorted(asn_stub),
    }


# ---------------------------------------------------------------------------
# Processamento de um IXP/AFI
# ---------------------------------------------------------------------------

def _parse_afi(
    raw_file: Path,
    norm_file: Path,
    afi: str,
    label: str,
    log,
) -> dict:
    """Parseia um arquivo raw BGP (um AFI de uma fonte) e grava três arquivos normalizados.

    Arquivos gerados em norm_file.parent/:
      routes-{afi}.json.gz         — stats + relationships + lista completa de rotas
      origin-prefixes-{afi}.json.gz — {str(asn): [prefixo, ...]} índice compacto por ASN originador
      prefix-set-{afi}.json.gz      — lista ordenada de prefixos únicos
      peers-{afi}.json.gz           — estatísticas por peer direto (core/ixp_peers.py)

    Args:
        raw_file:  Caminho do arquivo bruto de entrada (.txt)
        norm_file: Caminho do arquivo de saída principal (routes-{afi}.json.gz)
        afi:       "v4" ou "v6"
        label:     Identificador da fonte (ex: "sp", "fulltable") — gravado no campo "source"
        log:       Logger estruturado

    Returns:
        {"status": "ok", "routes": int, "unique_prefixes": int, "path": str}
        {"status": "missing"} se o arquivo raw não existir
        {"status": "error", "error": str} em caso de exceção
    """
    if not raw_existente(raw_file).exists():
        return {"status": "missing"}

    try:
        text = ler_texto_bruto(raw_file, errors="replace")
        routes = parse_bgp_output(text)
        relationships = compute_relationships(routes)
        unique_prefixes = len({r["prefix"] for r in routes})

        normalized = {
            "source":        label,
            "afi":           afi,
            "snapshot_date": norm_file.parent.parent.name,
            "generated_at":  now_iso(),
            "source_file":   str(raw_file),
            "stats": {
                "total_routes":     len(routes),
                "unique_prefixes":  unique_prefixes,
                "asn_direct_count": len(relationships["asn_direct"]),
                "asn_origin_count": len(relationships["asn_origin"]),
                "asn_stub_count":   len(relationships["asn_stub"]),
            },
            "relationships": relationships,
            "routes":        routes,
        }

        norm_file.parent.mkdir(parents=True, exist_ok=True)
        write_json_gz(norm_file, normalized)

        # origin-prefixes: índice compacto {str(asn): [prefixo...]} — consumido por `metricas_ixp_asn`
        origin_idx: dict[str, list[str]] = {}
        for route in routes:
            if route["aspath"]:
                key = str(route["aspath"][-1])
                origin_idx.setdefault(key, []).append(route["prefix"])
        origin_idx = {k: sorted(set(v)) for k, v in origin_idx.items()}
        write_json_gz(norm_file.parent / f"origin-prefixes-{afi}.json.gz", origin_idx)

        # peers: estatísticas por peer direto, para a API não reler as rotas do PTT inteiro (1.4.2.1)
        write_json_gz(norm_file.parent / f"peers-{afi}.json.gz", estatisticas_por_peer(routes, afi))

        # prefix-set: conjunto de prefixos únicos para cálculo de cobertura nas métricas de IXP
        prefix_set = sorted({r["prefix"] for r in routes})
        write_json_gz(norm_file.parent / f"prefix-set-{afi}.json.gz", prefix_set)

        log.info(
            "parsed",
            source=label, afi=afi,
            routes=len(routes),
            prefixes=unique_prefixes,
        )
        return {
            "status":         "ok",
            "routes":         len(routes),
            "unique_prefixes": unique_prefixes,
            "path":           str(norm_file),
        }

    except Exception as exc:
        log.error("parse error", source=label, afi=afi, error=str(exc))
        return {"status": "error", "error": str(exc)}


def parse_ixp(ixp_code: str, date_str: str, base: Path, log) -> dict:
    """Parseia arquivos raw de um IXP (v4 e v6) e grava os arquivos normalizados.

    Args:
        ixp_code: Código do IXP (ex: "sp", "rj")
        date_str: Data do snapshot (YYYY-MM-DD)
        base:     Diretório raiz dos dados
        log:      Logger estruturado

    Returns:
        {"ixp": code, "v4": resultado_v4, "v6": resultado_v6}
        Nunca lança exceção — erros em um AFI não afetam o outro.
    """
    result = {"ixp": ixp_code, "v4": {}, "v6": {}}
    for afi in ("v4", "v6"):
        log.info("parsing", ixp=ixp_code, afi=afi)
        raw_file  = raw_bgp_ixp(raw_path(base, date_str, ixp_code), afi, ixp_code, date_str)
        norm_file = normalized_path(base, date_str, ixp_code) / f"routes-{afi}.json.gz"
        result[afi] = _parse_afi(raw_file, norm_file, afi, ixp_code, log)
    return result


# ---------------------------------------------------------------------------
# Execução de todos os IXPs
# ---------------------------------------------------------------------------

def run(
    date_str: str,
    base: Path,
    ixp_codes: list[str] | None = None,
    log=None,
) -> list[dict]:
    """Parseia todos os IXPs (ou subconjunto) sequencialmente.

    Args:
        date_str:  Data do snapshot (YYYY-MM-DD)
        base:      Diretório raiz dos dados
        ixp_codes: Lista de códigos; None = todos os 40 IXPs do IX.br
        log:       Logger estruturado

    Returns:
        Lista de resultados por IXP (ver parse_ixp).
        Falhas em IXPs individuais não interrompem os demais.
    """
    all_ixps = load_ixps()
    if ixp_codes:
        all_ixps = [ix for ix in all_ixps if ix["code"] in ixp_codes]

    results = []
    for ixp in all_ixps:
        result = parse_ixp(ixp["code"], date_str, base, log)
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada CLI do `bgp_ixp`."""
    parser = argparse.ArgumentParser(description="`bgp_ixp` — parser BGP das saídas dos LGs")
    parser.add_argument("--date", default=today_str(),
                        help="Data do snapshot (YYYY-MM-DD); padrão: hoje")
    parser.add_argument("--ixp", nargs="+", metavar="CODE",
                        help="Parseia apenas estes IXPs (ex: --ixp sp rj ce)")
    args = parser.parse_args(argv)

    log  = configure_logging()
    base = data_dir()

    resultados = run(date_str=args.date, base=base, ixp_codes=args.ixp, log=log)
    # nenhum PTT com bruto legível: o snapshot sairia com todos `missing` e a execução constaria como ok
    if resultados and not any(r[afi].get("status") == "ok" for r in resultados for afi in ("v4", "v6")):
        log.error("nenhum bruto de PTT foi processado", date=args.date, ixps=len(resultados))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
