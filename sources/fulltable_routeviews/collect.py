# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`fulltable_routeviews` — Coleta da tabela BGP global via RouteViews (MRT dumps)

Baixa dumps RIB no formato MRT TABLE_DUMP_V2 (RFC 6396) de múltiplos coletores
RouteViews e grava os arquivos normalizados prontos para uso pelo `metricas_ixp_asn`:

    normalized/{date}/summary/routes-{afi}.json.gz          — stats (sem lista de rotas)
    normalized/{date}/summary/origin-prefixes-{afi}.json.gz — {str(asn): [prefixos]}
    normalized/{date}/summary/prefix-set-{afi}.json.gz      — [prefixo, ...]
    normalized/{date}/summary/aspath-adj-{afi}.json.gz      — {str(asn): {up: [...], down: [...]}}
    normalized/{date}/summary/origins-multi-{afi}.json.gz   — prefixos com 2+ origens: {prefixo: {str(asn): [coletores]}}
    normalized/{date}/summary/fulltable_manifest.json       — resultado e fontes usadas

`origin-prefixes-{afi}` guarda uma origem por prefixo (a do primeiro coletor que o viu); `origins-multi-{afi}` guarda todas as
origens observadas, por coletor, só dos prefixos com mais de uma (MOAS), para não carregar a tabela inteira duas vezes.

Não gera arquivos raw — os dumps MRT são processados em memória e descartados.

Skip inteligente:
    Verifica fulltable_manifest.json (não prefix-set-*.json.gz) para decidir
    se já foi executado.
    Use --force para re-executar mesmo com manifesto existente.

Uso:
    python -m sources.fulltable_routeviews.collect
    python -m sources.fulltable_routeviews.collect --date 2026-06-07
    python -m sources.fulltable_routeviews.collect --afi v4
    python -m sources.fulltable_routeviews.collect --force
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import shutil
import sys
import tempfile
import time
import urllib.request
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

try:
    import mrtparse
except ImportError:
    print("ERROR: mrtparse não instalado. Execute: pip install mrtparse==2.2.0",
          file=sys.stderr)
    sys.exit(1)

from sources.fulltable_routeviews.caminhos import AgregadorCaminhos
from core.common import (
    configure_logging,
    data_dir,
    normalized_path,
    now_iso,
    read_json_gz,
    today_str,
    write_json_gz,
    ignorar_sigpipe,
)
from core.site import USER_AGENT

# O mrtparse zera o tratamento de SIGPIPE ao ser importado (ver ignorar_sigpipe)
ignorar_sigpipe()

# ---------------------------------------------------------------------------
# Coletores por AFI — RouteViews (rv) e RIPE RIS (ris)
# ---------------------------------------------------------------------------
# Ordem determina prioridade no merge: prefixos do primeiro coletor prevalecem
# quando o mesmo prefixo aparece em múltiplos coletores.

_RV_BASE  = "http://archive.routeviews.org"
_RIS_BASE = "https://data.ris.ripe.net"

# Subdiretório do arquivo RouteViews para cada coletor (vazio = raiz).
_RV_PATHS: dict[str, str] = {
    "route-views2":          "",
    "route-views3":          "route-views3",
    "route-views6":          "route-views6",
    "route-views.linx":      "route-views.linx",
    "route-views.sg":        "route-views.sg",
    # o diretório no arquivo é o próprio nome do coletor ("napafrica" dá 404; RIBs até 12h do dia, 117 MB)
    "route-views.napafrica": "route-views.napafrica",
}

# (nome, tipo)  tipo = "rv" | "ris"
#: grava os caminhos únicos com VP por coletor; `ARANDU_CAMINHOS_VP=0` desliga
CAMINHOS_VP = os.environ.get("ARANDU_CAMINHOS_VP", "1") != "0"

COLLECTORS: dict[str, list[tuple[str, str]]] = {
    "v4": [
        ("route-views2",          "rv"),
        ("route-views3",          "rv"),
        ("route-views.linx",      "rv"),
        ("route-views.sg",        "rv"),
        ("route-views.napafrica", "rv"),
        ("rrc12",                 "ris"),
        ("rrc23",                 "ris"),
        ("rrc24",                 "ris"),
    ],
    "v6": [
        ("route-views6",          "rv"),
        ("route-views.linx",      "rv"),
        ("route-views.sg",        "rv"),
        ("route-views.napafrica", "rv"),
        ("rrc12",                 "ris"),
        ("rrc23",                 "ris"),
        ("rrc24",                 "ris"),
    ],
}

# ---------------------------------------------------------------------------
# Constantes MRT/BGP (mrtparse 2.x)
# RFC 6396 §4.3 — TABLE_DUMP_V2
# ---------------------------------------------------------------------------

_TABLE_DUMP_V2       = 13  # MRT type TABLE_DUMP_V2
_PEER_INDEX_TABLE    = 1   # subtype PEER_INDEX_TABLE: índice → (ASN, IP) do ponto de observação
_RIB_IPV4            = 2   # subtype RIB_IPV4_UNICAST
_RIB_IPV6            = 4   # subtype RIB_IPV6_UNICAST
_BGP_AS_PATH         = 2   # BGP path attribute type AS_PATH
_BGP_COMMUNITY       = 8   # RFC 1997
_BGP_LARGE_COMMUNITY = 32  # RFC 8092


def _first_key(d: dict):
    """Retorna a primeira chave de um dict {int: str} gerado pelo mrtparse.

    O mrtparse 2.x representa constantes como {valor_int: "nome_string"}.
    Para verificar tipo/subtipo, precisamos apenas do valor inteiro (primeira chave).
    """
    return next(iter(d), None)


# ---------------------------------------------------------------------------
# Descoberta do dump MRT mais recente — RouteViews
# ---------------------------------------------------------------------------

def _rv_base_url(name: str) -> str:
    subdir = _RV_PATHS[name]
    return f"{_RV_BASE}/{subdir}/bgpdata" if subdir else f"{_RV_BASE}/bgpdata"


def _list_ribs_rv(name: str, base: str, year_month: str, log) -> list[str]:
    """Lista arquivos rib.YYYYMMDD.HHMM.bz2 no diretório RIBS/ de um coletor RouteViews."""
    url = f"{base}/{year_month}/RIBS/"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode("utf-8", errors="replace")
        names = sorted(set(re.findall(r"rib\.\d{8}\.\d{4}\.bz2", html)))
        log.debug("listed ribs", collector=name, year_month=year_month, count=len(names))
        return names
    except Exception as exc:
        log.warning("failed listing ribs", collector=name, url=url, error=str(exc))
        return []


def _find_rib_url_rv(name: str, target: datetime.date, log) -> Optional[str]:
    """Retorna a URL do dump RIB RouteViews mais recente com data ≤ target.

    Pesquisa o mês atual e o mês anterior para cobrir o caso em que o pipeline
    roda no início do mês e o dump mais recente está no mês anterior.
    """
    base       = _rv_base_url(name)
    target_str = target.strftime("%Y%m%d")
    for month_back in range(2):
        year  = target.year
        month = target.month - month_back
        if month <= 0:
            month += 12
            year  -= 1
        ym = f"{year:04d}.{month:02d}"

        ribs = _list_ribs_rv(name, base, ym, log)
        # r[4:12] = YYYYMMDD; comparação lexicográfica é correta para datas ISO
        valid = [r for r in ribs if r[4:12] <= target_str]
        if valid:
            fname = valid[-1]
            url   = f"{base}/{ym}/RIBS/{fname}"
            log.info("found rib dump", collector=name, url=url, target=str(target))
            return url

    log.warning("no rib dump found", collector=name, target=str(target))
    return None


# ---------------------------------------------------------------------------
# Descoberta do dump MRT mais recente — RIPE RIS
# ---------------------------------------------------------------------------

def _list_bviews_ris(name: str, year_month: str, log) -> list[str]:
    """Lista arquivos bview.YYYYMMDD.HHMM.gz no diretório de um coletor RIPE RIS."""
    url = f"{_RIS_BASE}/{name}/{year_month}/"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode("utf-8", errors="replace")
        names = sorted(set(re.findall(r"bview\.\d{8}\.\d{4}\.gz", html)))
        log.debug("listed bviews", collector=name, year_month=year_month, count=len(names))
        return names
    except Exception as exc:
        log.warning("failed listing bviews", collector=name, url=url, error=str(exc))
        return []


def _find_rib_url_ris(name: str, target: datetime.date, log) -> Optional[str]:
    """Retorna a URL do bview RIPE RIS mais recente com data ≤ target."""
    target_str = target.strftime("%Y%m%d")
    for month_back in range(2):
        year  = target.year
        month = target.month - month_back
        if month <= 0:
            month += 12
            year  -= 1
        ym = f"{year:04d}.{month:02d}"

        bviews = _list_bviews_ris(name, ym, log)
        # bview.YYYYMMDD.HHMM.gz → posições 6:14 = YYYYMMDD
        valid = [b for b in bviews if b[6:14] <= target_str]
        if valid:
            fname = valid[-1]
            url   = f"{_RIS_BASE}/{name}/{ym}/{fname}"
            log.info("found bview", collector=name, url=url, target=str(target))
            return url

    log.warning("no bview found", collector=name, target=str(target))
    return None


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def _download(url: str, dest: Path, log) -> bool:
    """Baixa url para dest em chunks de 1 MiB. Retorna True em sucesso."""
    fname = url.rsplit("/", 1)[-1]
    log.info("download start", file=fname, url=url)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=600) as resp:
            total      = int(resp.headers.get("Content-Length", 0) or 0)
            total_mb   = round(total / 1e6, 1) if total else "?"
            done       = 0
            chunk      = 1 << 20   # 1 MiB
            t_start    = time.monotonic()
            t_last_log = t_start
            bytes_at_last_log = 0
            with dest.open("wb") as f:
                while True:
                    buf = resp.read(chunk)
                    if not buf:
                        break
                    f.write(buf)
                    done += len(buf)
                    # Log a cada 10 s para não spam em conexões rápidas
                    now = time.monotonic()
                    if now - t_last_log >= 10:
                        interval     = now - t_last_log
                        speed_mbps   = (done - bytes_at_last_log) / 1e6 / interval
                        pct          = f"{done / total * 100:.0f}%" if total else "?"
                        log.info(
                            "download progress",
                            file=fname,
                            downloaded_mb=round(done / 1e6, 1),
                            total_mb=total_mb,
                            pct=pct,
                            speed_mbps=round(speed_mbps, 2),
                        )
                        t_last_log        = now
                        bytes_at_last_log = done
        elapsed    = time.monotonic() - t_start
        speed_mbps = done / 1e6 / elapsed if elapsed > 0 else 0
        log.info(
            "download complete",
            file=fname,
            mb=round(done / 1e6, 1),
            elapsed_s=round(elapsed, 1),
            speed_mbps=round(speed_mbps, 2),
        )
        return True
    except Exception as exc:
        log.error("download failed", file=fname, url=url, error=str(exc))
        return False


# ---------------------------------------------------------------------------
# Parsing MRT
# ---------------------------------------------------------------------------

def _extract_aspath(path_attributes: list) -> Optional[list[int]]:
    """Extrai a lista de ASNs do atributo AS_PATH nos atributos BGP de um rib_entry.

    AS_SEQ e AS_SET são tratados de forma idêntica (flatten) — para métricas de
    cobertura, apenas o ASN origem (último) e o ASN direto (primeiro) importam.
    """
    for attr in path_attributes:
        if _first_key(attr.get("type", {})) == _BGP_AS_PATH:
            asns: list[int] = []
            for seg in attr.get("value", []):
                for asn in seg.get("value", []):
                    asns.append(int(asn))
            return asns
    return None


def _extract_communities(path_attributes: list) -> tuple[list[str], list[str]]:
    """Extrai standard communities (tipo 8) e large communities (tipo 32) dos atributos BGP."""
    communities:       list[str] = []
    large_communities: list[str] = []
    for attr in path_attributes:
        t = _first_key(attr.get("type", {}))
        if t == _BGP_COMMUNITY:
            v = attr.get("value", [])
            if isinstance(v, list):
                communities.extend(str(x) for x in v)
        elif t == _BGP_LARGE_COMMUNITY:
            v = attr.get("value", [])
            if isinstance(v, list):
                large_communities.extend(str(x) for x in v)
    return communities, large_communities


def _asn_do_peer(entrada: dict) -> int:
    try:
        return int(entrada.get("peer_as", -1))
    except (TypeError, ValueError):
        return -1


def _parse_mrt(
    path: Path,
    afi: str,
    log,
    br_asns: set[int] | None = None,
    caminhos=None,
    origens: dict | None = None,
) -> tuple[list[dict], dict[str, dict]]:
    """Parseia um dump MRT TABLE_DUMP_V2 e extrai rotas e grafo de adjacências.

    Para cada prefixo no dump:
      - A rota "best path" (primeiro rib_entry com AS_PATH válido) vai para `routes`
      - Todos os rib_entries alimentam o grafo de adjacências `adj_graph`

    O grafo de adjacências registra, para cada ASN, seus vizinhos imediatos em
    qualquer AS_PATH observado. Prepends (ASN repetido) são ignorados.

    Quando `br_asns` é fornecido, rotas com origin_as ∈ br_asns também capturam
    communities e large_communities no dict da rota (campos opcionais).

    Args:
        path:    Caminho do arquivo .bz2 MRT
        afi:     "v4" ou "v6"
        log:     Logger estruturado
        br_asns: Conjunto de ASNs BR para extração de communities (opcional)
        caminhos: `AgregadorCaminhos` opcional: recebe cada caminho único com o VP que o viu
        origens: dict opcional preenchido com {prefixo: set(origens)} dos prefixos que, neste dump, têm mais de uma origem
                 (último AS do AS_PATH) entre os pontos de observação; os de origem única não entram (estão em `routes`)

    Returns:
        routes:    Lista de dicts {"prefix", "status", "aspath", "origin", "nexthop"}
                   Rotas BR incluem opcionalmente "communities" e "large_communities".
        adj_graph: Dict {str(asn): {"up": [asns_à_esquerda], "down": [asns_à_direita]}}
    """
    target_sub = _RIB_IPV4 if afi == "v4" else _RIB_IPV6
    seen:   set[str]   = set()
    routes: list[dict] = []

    # up_of[B] = conjunto de ASNs imediatamente à esquerda de B em qualquer path observado
    # dn_of[A] = conjunto de ASNs imediatamente à direita de A em qualquer path observado
    up_of: dict[int, set[int]] = defaultdict(set)
    dn_of: dict[int, set[int]] = defaultdict(set)

    total_entries = 0
    t_start = time.monotonic()

    try:
        for m in mrtparse.Reader(str(path)):
            if m.err:
                continue
            d = m.data
            if _first_key(d.get("type", {})) != _TABLE_DUMP_V2:
                continue
            sub = _first_key(d.get("subtype", {}))
            if sub == _PEER_INDEX_TABLE:
                if caminhos is not None:
                    caminhos.definir_peers([_asn_do_peer(e) for e in d.get("peer_entries", [])])
                continue
            if sub != target_sub:
                continue

            pl = d.get("length", 0)
            if pl == 0:
                continue  # rota default /0 — não representativa do espaço roteado
            prefix = f"{d['prefix']}/{pl}"

            got_route = prefix in seen
            # MOAS: a primeira origem vista e, só se aparecer outra, o conjunto (evita um set por prefixo)
            orig1: Optional[int] = None
            outras: Optional[set[int]] = None
            for rib in d.get("rib_entries", []):
                path_attrs = rib.get("path_attributes", [])
                asp = _extract_aspath(path_attrs)
                if asp is None:
                    continue
                if origens is not None and asp:
                    if orig1 is None:
                        orig1 = asp[-1]
                    elif asp[-1] != orig1:
                        if outras is None:
                            outras = set()
                        outras.add(asp[-1])

                # Primeiro rib_entry com AS_PATH válido = "best path" para este prefixo
                if not got_route:
                    seen.add(prefix)
                    route: dict = {
                        "prefix":  prefix,
                        "status":  ">",
                        "aspath":  asp,
                        "origin":  "i",
                        "nexthop": "",
                    }
                    # Captura communities apenas para rotas com origin_as BR
                    if br_asns and asp and asp[-1] in br_asns:
                        comms, large = _extract_communities(path_attrs)
                        if comms:
                            route["communities"] = comms
                        if large:
                            route["large_communities"] = large
                    routes.append(route)
                    got_route = True

                # Todos os rib_entries alimentam o grafo (ignora prepend)
                prev = -1
                comp = [] if caminhos is not None else None
                for asn in asp:
                    if asn == prev:
                        continue  # prepend: mesmo AS repetido consecutivamente
                    if prev >= 0:
                        up_of[asn].add(prev)
                        dn_of[prev].add(asn)
                    prev = asn
                    if comp is not None:
                        comp.append(asn)
                if comp:
                    caminhos.adicionar(comp, rib.get("peer_index", -1))

            if outras:
                origens.setdefault(prefix, set()).update(outras, (orig1,))

            total_entries += 1
            if total_entries % 200_000 == 0:
                elapsed  = time.monotonic() - t_start
                rate     = int(total_entries / elapsed) if elapsed > 0 else 0
                log.info(
                    "parse progress",
                    afi=afi,
                    entries=total_entries,
                    prefixes=len(routes),
                    entries_per_sec=rate,
                )

    except EOFError:
        log.warning("mrt truncated, stopped early", afi=afi, prefixes=len(routes))

    elapsed = time.monotonic() - t_start
    all_asns = set(up_of.keys()) | set(dn_of.keys())
    adj_graph: dict[str, dict] = {
        str(asn): {
            "up":   sorted(up_of.get(asn, set())),
            "down": sorted(dn_of.get(asn, set())),
        }
        for asn in all_asns
    }

    log.info(
        "parse done",
        afi=afi,
        entries=total_entries,
        prefixes=len(routes),
        adj_asns=len(adj_graph),
        elapsed_s=round(elapsed, 1),
    )
    return routes, adj_graph


# ---------------------------------------------------------------------------
# Escrita dos normalizados
# ---------------------------------------------------------------------------

def _load_br_asns(base: Path, date_str: str, log) -> set[int]:
    """Carrega conjunto de ASNs BR do Registro.br.

    Tenta snapshot atual primeiro, depois o mais recente anterior.
    Retorna set vazio se nenhum encontrado (br-routes não será gravado).
    """
    candidates = [
        normalized_path(base, date_str, "summary") / "registro_br.json.gz",
    ]
    norm_root = base / "normalized"
    if norm_root.exists():
        for d in sorted(norm_root.iterdir(), reverse=True):
            if d.name != date_str and d.is_dir():
                candidates.append(d / "summary" / "registro_br.json.gz")
                break

    for path in candidates:
        if path.exists():
            try:
                data = read_json_gz(path)
                asns = {a["asn"] for a in data.get("asns", [])}
                log.info("loaded br_asns", source=str(path), count=len(asns))
                return asns
            except Exception as exc:
                log.warning("failed loading registro_br", path=str(path), error=str(exc))
    log.warning("br_asns not available — br-routes will not be written")
    return set()


def _write_normalized(
    routes:    list[dict],
    adj_graph: dict[str, dict],
    afi:       str,
    date_str:  str,
    sources:   list[str],
    base:      Path,
    log,
    br_asns:   set[int] | None = None,
) -> None:
    """Grava os arquivos normalizados em normalized/{date}/summary/.

    Arquivos gerados:
      routes-{afi}.json.gz          — estatísticas gerais (sem a lista de rotas)
      origin-prefixes-{afi}.json.gz — {str(asn): [prefixo, ...]} — usado por `metricas_ixp_asn`
      prefix-set-{afi}.json.gz      — lista ordenada de todos os prefixos únicos
      aspath-adj-{afi}.json.gz      — grafo de adjacências {str(asn): {up, down}}
      br-routes-{afi}.json.gz       — rotas BR com AS_PATH e communities (se br_asns)

    Args:
        sources:  Lista de identificadores das fontes usadas na agregação
        br_asns:  Conjunto de ASNs BR para filtrar br-routes (opcional)
    """
    asn_direct: set[int] = set()
    asn_origin: set[int] = set()
    origin_idx: dict[str, list[str]] = defaultdict(list)
    prefix_set: list[str] = []

    for r in routes:
        prefix_set.append(r["prefix"])
        asp = r["aspath"]
        if asp:
            asn_direct.add(asp[0])
            asn_origin.add(asp[-1])
            origin_idx[str(asp[-1])].append(r["prefix"])

    origin_idx_sorted = {k: sorted(set(v)) for k, v in origin_idx.items()}
    prefix_set_sorted = sorted(prefix_set)

    norm_dir = normalized_path(base, date_str, "summary")
    norm_dir.mkdir(parents=True, exist_ok=True)

    write_json_gz(norm_dir / f"routes-{afi}.json.gz", {
        "source": "routeviews",
        "afi":    afi,
        "snapshot_date": date_str,
        "generated_at":  now_iso(),
        "sources": sources,
        "stats": {
            "total_routes":     len(routes),
            "unique_prefixes":  len(prefix_set),
            "asn_direct_count": len(asn_direct),
            "asn_origin_count": len(asn_origin),
            "asn_stub_count":   0,  # não calculado para a full table
        },
    })

    write_json_gz(norm_dir / f"origin-prefixes-{afi}.json.gz", origin_idx_sorted)
    write_json_gz(norm_dir / f"prefix-set-{afi}.json.gz",      prefix_set_sorted)
    write_json_gz(norm_dir / f"aspath-adj-{afi}.json.gz",      adj_graph)

    log.info("normalized written", afi=afi,
             prefixes=len(prefix_set), origins=len(asn_origin),
             sources=len(sources), adj_asns=len(adj_graph))

    # --- br-routes: rotas com origin_as ∈ BR, com AS_PATH e communities ---
    if br_asns:
        br_routes = []
        for r in routes:
            asp = r.get("aspath", [])
            if asp and asp[-1] in br_asns:
                entry: dict = {"p": r["prefix"], "a": asp}
                comms = r.get("communities", [])
                large = r.get("large_communities", [])
                if comms:
                    entry["c"] = comms
                if large:
                    entry["lc"] = large
                br_routes.append(entry)
        if br_routes:
            write_json_gz(norm_dir / f"br-routes-{afi}.json.gz", br_routes)
            log.info("br-routes written", afi=afi, count=len(br_routes))


# ---------------------------------------------------------------------------
# Execução principal
# ---------------------------------------------------------------------------

def _merge_into(
    seen:      dict[str, dict],
    merged_up: dict[str, set],
    merged_dn: dict[str, set],
    routes:    list[dict],
    adj:       dict[str, dict],
) -> None:
    """Funde routes e adj no estado acumulado, descartando duplicatas.

    Operação in-place: modifica seen/merged_up/merged_dn.
    Após retornar, routes e adj podem ser descartados pelo chamador,
    liberando memória antes do próximo coletor.
    """
    for r in routes:
        if r["prefix"] not in seen:
            seen[r["prefix"]] = r
    for asn_str, nb in adj.items():
        merged_up[asn_str].update(nb.get("up", []))
        merged_dn[asn_str].update(nb.get("down", []))


class OrigensPorColetor:
    """Origens observadas por prefixo e por coletor, para achar os prefixos com mais de uma (MOAS).

    `_merge_into` guarda a rota do primeiro coletor que viu o prefixo, e com ela uma origem só. Aqui cada coletor entra com a origem
    da sua rota e, quando no próprio dump o prefixo já tem várias (`_parse_mrt(origens=...)`), com todas. Enquanto um prefixo tem
    uma origem só, ela fica num int (origem << 16 | máscara dos coletores que a viram), sem dict nem set por prefixo: a tabela
    inteira passa por aqui e quase todo prefixo tem origem única. Divergiu, o prefixo passa para `multiplas` ({origem: máscara}).
    """

    _BITS = 16

    def __init__(self, coletores: list[str]):
        if len(coletores) > self._BITS:
            raise ValueError(f"no máximo {self._BITS} coletores por família")
        self.coletores = list(coletores)
        self._bit = {n: 1 << i for i, n in enumerate(self.coletores)}
        self._unica: dict[str, int] = {}
        self.multiplas: dict[str, dict[int, int]] = {}

    def fundir(self, coletor: str, routes: list[dict], origens_coletor: dict) -> None:
        """Junta as origens de um coletor: `routes` (uma rota por prefixo) e `origens_coletor` ({prefixo: origens}, só os múltiplos)."""
        bit = self._bit[coletor]
        mask = (1 << self._BITS) - 1
        for r in routes:
            p = r["prefix"]
            varias = origens_coletor.get(p)
            if varias is None:
                asp = r.get("aspath")
                if not asp:
                    continue
                o = asp[-1]
                m = self.multiplas.get(p)
                if m is not None:
                    m[o] = m.get(o, 0) | bit
                    continue
                u = self._unica.get(p)
                if u is None:
                    self._unica[p] = (o << self._BITS) | bit
                elif u >> self._BITS == o:
                    self._unica[p] = u | bit
                else:
                    del self._unica[p]
                    self.multiplas[p] = {u >> self._BITS: u & mask, o: bit}
                continue
            m = self.multiplas.get(p)
            if m is None:
                m = {}
                u = self._unica.pop(p, None)
                if u is not None:
                    m[u >> self._BITS] = u & mask
                self.multiplas[p] = m
            for o in varias:
                o = int(o)
                m[o] = m.get(o, 0) | bit

    def documento(self) -> dict[str, dict[str, list[str]]]:
        """{prefixo: {str(origem): [coletores]}}, só prefixos com 2+ origens, em ordem estável."""
        def nomes(m: int) -> list[str]:
            return [n for n in self.coletores if m & self._bit[n]]
        return {p: {str(o): nomes(m) for o, m in sorted(self.multiplas[p].items())} for p in sorted(self.multiplas)}


def _gravar_origens_multiplas(norm_dir: Path, afi: str, date_str: str, coletores: list[str], estado: OrigensPorColetor) -> int:
    """`origins-multi-{afi}.json.gz` (escrita atômica). A presença do arquivo diz que a coleta guardou todas as origens: sem prefixo
    nenhum, é "nenhum MOAS observado entre estes coletores", diferente de não ter medido."""
    prefixos = estado.documento()
    destino = norm_dir / f"origins-multi-{afi}.json.gz"
    tmp = destino.with_name(destino.name + ".tmp")
    write_json_gz(tmp, {
        "afi": afi,
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "coletores": coletores,
        "definicao": "Prefixos com duas ou mais origens (último AS do AS_PATH) entre todas as rotas dos coletores; para cada origem, "
                     "os coletores em que algum ponto de observação a viu.",
        "prefixos": prefixos,
    })
    tmp.replace(destino)
    return len(prefixos)


def run(
    date_str: str,
    base: Path,
    afis: list[str],
    force: bool,
    log,
) -> dict:
    """Executa a coleta RouteViews + RIPE RIS para as AFIs especificadas.

    Fluxo por AFI:
      1. Verifica se fulltable_manifest.json já existe (skip se não --force)
      2. Fase A — checkpoints: coletores já processados são fundidos imediatamente
      3. Fase B — URL discovery: resolve URLs dos coletores restantes (sequencial)
      4. Fase C/D — pipeline: todos os downloads rodam em paralelo; à medida que
         cada arquivo fica disponível (as_completed), é parseado e fundido
         sequencialmente pelo processo principal, depois descartado do disco
      5. Escreve arquivos normalizados a partir do estado acumulado e `origins-multi-{afi}` (MOAS por coletor)
      6. Apaga checkpoints e grava fulltable_manifest.json

    Pico de memória: estado_merged + 1 coletor em processamento + `OrigensPorColetor` (um int por prefixo da família e
    um dict por prefixo com mais de uma origem).
    Pico de disco:   todos os dumps ainda não parseados simultaneamente (~800 MB v4).

    Args:
        date_str: Data do snapshot (YYYY-MM-DD)
        base:     Diretório raiz dos dados
        afis:     Lista de AFIs a processar (ex: ["v4", "v6"])
        force:    Re-executa mesmo se manifesto/checkpoints existirem
        log:      Logger estruturado

    Returns:
        Dict {afi: {"status": "ok"|"error"|"skipped", ...}} + "date"
    """
    target  = datetime.date.fromisoformat(date_str)
    result: dict = {"date": date_str}
    br_asns = _load_br_asns(base, date_str, log)

    for afi in afis:
        norm_dir = normalized_path(base, date_str, "summary")
        manifest = norm_dir / "fulltable_manifest.json"

        # v4 e v6 são independentes: o manifesto guarda uma entrada por família, e só uma família concluída é pulada
        # (senão o v4 pronto se perderia quando o v6 falha). Família concluída antes de existir `origins-multi` é refeita.
        if (not force and _manifesto_lido(manifest).get(afi, {}).get("status") == "ok"
                and (norm_dir / f"origins-multi-{afi}.json.gz").exists()):
            log.info("already exists, skipping", afi=afi, date=date_str)
            result[afi] = {"status": "skipped"}
            continue

        ckpt_dir = norm_dir / f"_ckpt_{afi}"
        if force:
            shutil.rmtree(ckpt_dir, ignore_errors=True)
            shutil.rmtree(norm_dir / f"aspaths-{afi}", ignore_errors=True)
        ckpt_dir.mkdir(parents=True, exist_ok=True)

        seen:      dict[str, dict]  = {}
        merged_up: dict[str, set]   = defaultdict(set)
        merged_dn: dict[str, set]   = defaultdict(set)
        sources_used: list[str]     = []
        coletores_ok: list[str]     = []
        origens = OrigensPorColetor([n for n, _ in COLLECTORS[afi]])
        n_ok = 0

        n_collectors = len(COLLECTORS[afi])

        with tempfile.TemporaryDirectory(prefix="arandurape_rib_") as tmpdir:
            tmp = Path(tmpdir)

            # ------------------------------------------------------------------
            # Fase A — checkpoints: coletores já processados não precisam baixar
            # ------------------------------------------------------------------
            to_download: list[tuple[str, str, str, object]] = []  # (col_name, col_kind, url, clog)

            for idx, (col_name, col_kind) in enumerate(COLLECTORS[afi], 1):
                clog = log.bind(collector=col_name, kind=col_kind,
                                step=f"{idx}/{n_collectors}")
                ckpt_routes_f = ckpt_dir / f"{col_name}.routes.json.gz"
                ckpt_adj_f    = ckpt_dir / f"{col_name}.adj.json.gz"
                ckpt_src_f    = ckpt_dir / f"{col_name}.src.txt"
                ckpt_orig_f   = ckpt_dir / f"{col_name}.origens.json.gz"

                # sem o arquivo de origens (checkpoint de antes dele) o coletor é baixado de novo: faltariam os MOAS do dump
                if ckpt_routes_f.exists() and ckpt_adj_f.exists() and ckpt_orig_f.exists():
                    try:
                        compact = read_json_gz(ckpt_routes_f)
                        routes  = []
                        for r in compact:
                            rec: dict = {"prefix": r["p"], "aspath": r["a"],
                                         "status": ">", "origin": "i", "nexthop": ""}
                            if r.get("c"):
                                rec["communities"] = r["c"]
                            if r.get("lc"):
                                rec["large_communities"] = r["lc"]
                            routes.append(rec)
                        adj = read_json_gz(ckpt_adj_f)
                        src = ckpt_src_f.read_text(encoding="utf-8").strip() \
                              if ckpt_src_f.exists() else col_name
                        origens_col = read_json_gz(ckpt_orig_f)
                        origens.fundir(col_name, routes, origens_col)
                        _merge_into(seen, merged_up, merged_dn, routes, adj)
                        del routes, adj, compact, origens_col
                        sources_used.append(src)
                        coletores_ok.append(col_name)
                        n_ok += 1
                        clog.info("collector resumed from checkpoint",
                                  afi=afi, seen_prefixes=len(seen))
                        continue
                    except Exception as exc:
                        clog.warning("checkpoint corrupt, will re-download",
                                     afi=afi, error=str(exc))

                # ------------------------------------------------------------------
                # Fase B — URL discovery (sequencial, apenas HTTP de listagem)
                # ------------------------------------------------------------------
                if col_kind == "rv":
                    url = _find_rib_url_rv(col_name, target, clog)
                else:
                    url = _find_rib_url_ris(col_name, target, clog)

                if not url:
                    clog.warning("collector skipped — no dump found", afi=afi)
                    continue

                to_download.append((col_name, col_kind, url, clog))

            # ------------------------------------------------------------------
            # Fases C + D — downloads paralelos → parse pipeline (as_completed)
            # ------------------------------------------------------------------
            if to_download:
                def _fetch(col_name: str, url: str, clog) -> tuple[str, str, Path, bool]:
                    ext  = ".gz" if url.endswith(".gz") else ".bz2"
                    dest = tmp / f"rib_{afi}_{col_name}{ext}"
                    ok   = _download(url, dest, clog)
                    return col_name, url, dest, ok

                clog_map = {cn: clog for cn, _, _, clog in to_download}

                with ThreadPoolExecutor(max_workers=len(to_download)) as pool:
                    futs = {
                        pool.submit(_fetch, cn, url, clog): cn
                        for cn, _, url, clog in to_download
                    }

                    for fut in as_completed(futs):
                        col_name, url, dest, ok = fut.result()
                        clog = clog_map[col_name]

                        if not ok:
                            clog.warning("collector skipped — download failed", afi=afi)
                            continue

                        t_col = time.monotonic()
                        agreg = AgregadorCaminhos() if CAMINHOS_VP else None
                        origens_col: dict = {}
                        routes, adj = _parse_mrt(dest, afi, clog, br_asns=br_asns or None, caminhos=agreg, origens=origens_col)
                        try:
                            dest.unlink()
                        except OSError:
                            pass

                        if not routes:
                            clog.warning("collector yielded no routes", afi=afi)
                            continue

                        ckpt_routes_f = ckpt_dir / f"{col_name}.routes.json.gz"
                        ckpt_adj_f    = ckpt_dir / f"{col_name}.adj.json.gz"
                        ckpt_src_f    = ckpt_dir / f"{col_name}.src.txt"
                        ckpt_orig_f   = ckpt_dir / f"{col_name}.origens.json.gz"
                        try:
                            compact = []
                            for r in routes:
                                entry: dict = {"p": r["prefix"], "a": r["aspath"]}
                                if r.get("communities"):
                                    entry["c"] = r["communities"]
                                if r.get("large_communities"):
                                    entry["lc"] = r["large_communities"]
                                compact.append(entry)
                            write_json_gz(ckpt_routes_f, compact)
                            write_json_gz(ckpt_adj_f,    adj)
                            ckpt_src_f.write_text(url, encoding="utf-8")
                            # por último: é a presença dele que valida o checkpoint na retomada
                            write_json_gz(ckpt_orig_f, {p: sorted(o) for p, o in origens_col.items()})
                            del compact
                            clog.info("checkpoint saved", afi=afi)
                        except Exception as exc:
                            clog.warning("checkpoint write failed (non-fatal)",
                                         afi=afi, error=str(exc))

                        if agreg is not None:
                            try:
                                n = agreg.escrever(norm_dir / f"aspaths-{afi}" / f"{col_name}.tsv.gz", col_name)
                                clog.info("aspaths written", afi=afi, unique_paths=n)
                            except Exception as exc:                                    # opcional: a coleta segue sem eles
                                clog.warning("aspaths write failed (non-fatal)", afi=afi, error=str(exc))
                            del agreg

                        origens.fundir(col_name, routes, origens_col)
                        _merge_into(seen, merged_up, merged_dn, routes, adj)
                        del routes, adj, origens_col

                        sources_used.append(url)
                        coletores_ok.append(col_name)
                        n_ok += 1
                        clog.info(
                            "collector done",
                            afi=afi,
                            seen_prefixes=len(seen),
                            elapsed_s=round(time.monotonic() - t_col, 1),
                        )

        if n_ok == 0:
            log.error("all collectors failed", afi=afi)
            result[afi] = {"status": "error", "error": "all collectors failed"}
            continue

        # Constrói estruturas finais a partir do estado acumulado
        all_asns = set(merged_up.keys()) | set(merged_dn.keys())
        merged_adj: dict[str, dict] = {
            asn_str: {
                "up":   sorted(merged_up.get(asn_str, set())),
                "down": sorted(merged_dn.get(asn_str, set())),
            }
            for asn_str in all_asns
        }
        merged = list(seen.values())

        log.info("merge complete", afi=afi,
                 prefixes=len(merged), collectors=n_ok,
                 adj_asns=len(merged_adj))

        _write_normalized(merged, merged_adj, afi, date_str, sources_used, base, log,
                         br_asns=br_asns or None)
        n_multi = _gravar_origens_multiplas(norm_dir, afi, date_str, sorted(coletores_ok, key=origens.coletores.index), origens)
        log.info("origins-multi written", afi=afi, prefixes=n_multi, collectors=n_ok)
        del origens
        result[afi] = {
            "status":          "ok",
            "sources":         sources_used,
            "unique_prefixes": len(merged),
            "origens_multiplas": n_multi,
        }

        # Remove checkpoints ao concluir o AFI com sucesso
        shutil.rmtree(ckpt_dir, ignore_errors=True)
        log.info("checkpoints removed", afi=afi)

        # Manifesto gravado a cada família concluída (sua entrada "ok" é o skip-check da família)
        _gravar_manifesto(manifest, date_str, afi, result[afi])

    return result


def _manifesto_lido(manifest: Path) -> dict:
    try:
        return json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _gravar_manifesto(manifest: Path, date_str: str, afi: str, entrada: dict) -> None:
    """Atualiza só a entrada da família `afi`, preservando a outra (escrita atômica)."""
    atual = _manifesto_lido(manifest)
    atual.update({"date": date_str, afi: entrada, "generated_at": now_iso()})
    manifest.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(atual, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(manifest)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="`fulltable_routeviews` — coleta full table BGP via RouteViews (MRT)"
    )
    p.add_argument("--date",  default=today_str(),
                   help="data do snapshot (YYYY-MM-DD, padrão: hoje)")
    p.add_argument("--afi",   choices=["v4", "v6", "both"], default="both",
                   help="família de endereços a coletar (padrão: both)")
    p.add_argument("--force", action="store_true",
                   help="reprocessa mesmo se os arquivos normalizados já existirem")
    args = p.parse_args(argv)

    log  = configure_logging()
    base = data_dir()
    afis = ["v4", "v6"] if args.afi == "both" else [args.afi]

    log.info("starting routeviews collection",
             date=args.date, afis=afis, force=args.force)
    result = run(date_str=args.date, base=base, afis=afis, force=args.force, log=log)

    ok = all(
        v.get("status") in ("ok", "skipped")
        for v in result.values()
        if isinstance(v, dict)
    )
    log.info("done", result=result)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
