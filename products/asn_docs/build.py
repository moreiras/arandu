# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Documentos de ASN: índice (`asns/index.json`), nomes (`asns/names.json`) e caminhos de IXP.
Leem o fragmento `base` do compose ou, em snapshots antigos, os documentos publicados."""
from __future__ import annotations

import gzip
import ipaddress
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from core import compose
from core import intermediarios
from core.common import published_path
from core.jsonio import carregar_json, carregar_json_gz

_load_json = carregar_json            # nomes históricos do snapshot_builder
_load_json_gz = carregar_json_gz


def publicar_asn_index(
    base: Path, date_str: str, log
) -> tuple[list[dict], set[str], set[str], set[str], set[str]]:
    """
    Gera asns/index.json lendo cada asns/{asn}.json em streaming.
    Retorna (index, global_br_prefixes_v4, ixp_all_prefixes_v4,
             ixp_all_v6_prefixes, global_br_prefixes_v6) para os mapas Hilbert.
    """
    pub_dir = published_path(base, date_str, "asns")
    novo = compose.fluxo_novo(base, date_str)      # ARANDU_COMPOSE=on: lê o fragmento `base`; os documentos ainda não existem
    if not novo and not pub_dir.exists():
        log.warning("asns dir missing", path=str(pub_dir))
        return [], set(), set(), set(), set()

    # Build set of ASNs that have at least one RPKI ROA
    rpki_vrps = carregar_json_gz(published_path(base, date_str, "rpki") / "vrp_list.json.gz") or []
    rpki_asns: set[int] = {int(r["asn"]) for r in rpki_vrps if "asn" in r}

    # Build set of ASNs that have published at least one ASPA object (as customer)
    aspa_list = carregar_json_gz(published_path(base, date_str, "rpki") / "aspa_list.json.gz") or []
    aspa_asns: set[int] = {int(a["customer"]) for a in aspa_list if "customer" in a}

    if novo:
        documentos = compose.iterar_documentos(base, date_str, ("base",))
        total = None                                # não relê o fragmento só para contar
    else:
        paths = sorted(
            (p for p in pub_dir.glob("*.json") if p.stem.isdigit()),
            key=lambda p: int(p.stem),
        )
        total = len(paths)
        documentos = ((int(p.stem), carregar_json(p)) for p in paths)
    log.info("indexing asns", total=total)
    index = []
    global_br_prefixes: set[str] = set()
    ixp_all_prefixes: set[str] = set()
    ixp_all_v6_prefixes: set[str] = set()
    global_br_v6_prefixes: set[str] = set()

    for i, (_asn, doc) in enumerate(documentos, 1):
        if i % 10000 == 0:
            log.info("asn index progress", done=i, total=total)
        if doc is None:
            continue
        ixp_presence = doc.get("ixp_presence", {})
        ixps_origin_v4 = sum(1 for p in ixp_presence.values() if p.get("v4", {}).get("origin", False))
        ixps_origin_v6 = sum(1 for p in ixp_presence.values() if p.get("v6", {}).get("origin", False))
        gv4 = doc.get("global_prefixes_v4") or []
        gv6 = doc.get("global_prefixes_v6") or []
        space_v4 = 0
        for p in gv4:
            try:
                net = ipaddress.ip_network(p, strict=False)
                if net.version == 4 and net.prefixlen <= 24:
                    space_v4 += 1 << (24 - net.prefixlen)
            except ValueError:
                pass
        space_v6 = 0
        for p in gv6:
            try:
                net = ipaddress.ip_network(p, strict=False)
                if net.version == 6 and net.prefixlen <= 48:
                    space_v6 += 1 << (48 - net.prefixlen)
            except ValueError:
                pass
        index.append({
            "asn": doc["asn"],
            "name": doc.get("name", ""),
            "is_br": doc.get("is_br", False),
            "has_ipv6": doc.get("has_ipv6", False),
            "rir_prefixes_v4_count": doc.get("rir_prefixes_v4_count", 0),
            "rir_prefixes_v6_count": doc.get("rir_prefixes_v6_count", 0),
            "global_prefixes_v4_count": doc.get("global_prefixes_v4_count", 0),
            "global_prefixes_v6_count": doc.get("global_prefixes_v6_count", 0),
            "space_v4": space_v4,
            "space_v6": space_v6,
            "ixps_direct_count": len(doc.get("ixps_direct", [])),
            "ixps_origin_count": len(doc.get("ixps_origin", [])),
            "ixps_origin_v4_count": ixps_origin_v4,
            "ixps_origin_v6_count": ixps_origin_v6,
            "apnic_users": doc.get("apnic_users"),
            "apnic_v6_users": doc.get("apnic_v6_users"),
            "pct_v6": (
                min(round(doc["apnic_v6_users"] / doc["apnic_users"] * 100, 2), 100.0)
                if doc.get("apnic_users") and doc.get("apnic_v6_users") is not None
                else None
            ),
            "has_rpki": doc["asn"] in rpki_asns,
            "has_aspa": doc["asn"] in aspa_asns,
            "external_ixps_count": len(doc.get("external_ixps") or []),
            "pdb_registered": doc.get("pdb_registered"),
        })
        # Collect prefixes for Hilbert density maps and IXP aggregate
        if doc.get("is_br"):
            global_br_prefixes.update(doc.get("global_prefixes_v4", []))
            global_br_v6_prefixes.update(doc.get("global_prefixes_v6", []))
        for ixp_pres in ixp_presence.values():
            v4 = ixp_pres.get("v4", {})
            ixp_all_prefixes.update(v4.get("prefixes", []))
            v6 = ixp_pres.get("v6", {})
            ixp_all_v6_prefixes.update(v6.get("prefixes", []))

    return index, global_br_prefixes, ixp_all_prefixes, ixp_all_v6_prefixes, global_br_v6_prefixes


def publicar_asn_names(base: Path, date_str: str, log) -> int:
    """
    Gera asns/names.json: dicionário {str(asn): name} para todos os ASNs do snapshot.
    Usado pelo endpoint GET /api/v1/asns/names para lookup global de nomes no frontend.
    """
    pub_dir = published_path(base, date_str, "asns")
    novo = compose.fluxo_novo(base, date_str)
    if not novo and not pub_dir.exists():
        log.warning("asns dir missing, skipping names build")
        return 0
    pub_dir.mkdir(parents=True, exist_ok=True)

    if novo:
        documentos = compose.iterar_documentos(base, date_str, ("base",))
    else:
        documentos = ((int(p.stem), carregar_json(p))
                      for p in sorted(pub_dir.glob("*.json"), key=lambda p: int(p.stem) if p.stem.isdigit() else -1)
                      if p.stem.isdigit())

    names: dict[str, str] = {}
    for _asn, doc in documentos:
        if doc is None:
            continue
        name = doc.get("name", "")
        if name:
            names[str(doc["asn"])] = name

    out = pub_dir / "names.json"
    out.write_text(json.dumps(names, ensure_ascii=False), encoding="utf-8")
    log.info("asn names written", path=str(out), count=len(names))
    return len(names)


# ---------------------------------------------------------------------------
# Pré-computação de ixp_paths por ASN
# ---------------------------------------------------------------------------

def _parse_route_file(path: Path) -> dict[int, dict[tuple, int]]:
    """
    Lê routes-{afi}.json.gz e retorna {origin_asn: {intermediaries_tuple: count}}.
    intermediaries_tuple = ASes entre o AS de origem e o peer direto no IXP,
    em ordem de origem → IXP (o mesmo formato de ixp_origin_paths no store).
    """
    index: dict[int, dict[tuple, int]] = {}
    if not path.exists():
        return index
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return index
    for route in data.get("routes", []):
        aspath = route.get("aspath", [])
        if not aspath:
            continue
        deduped: list[int] = []
        for a in aspath:
            if not deduped or deduped[-1] != a:
                deduped.append(a)
        if not deduped:
            continue
        origin = deduped[-1]
        intermediaries = tuple(reversed(deduped[:-1]))
        if intermediaries:
            inner = index.setdefault(origin, {})
            inner[intermediaries] = inner.get(intermediaries, 0) + 1
    return index


def publicar_ixp_paths(base: Path, date_str: str, log) -> int:
    """
    Pré-computa ixp_paths para todos os ASNs e escreve de volta nos arquivos JSON.

    Estratégia:
    1. Lê todos routes-{afi}.json.gz de todos os IXPs em paralelo.
    2. Constrói índice reverso: origin_asn → {(code, afi): sorted_paths}.
    3. Para cada ASN com ≤ 40 IXPs origin-only, adiciona ixp_paths ao JSON.

    Retorna número de arquivos ASN enriquecidos.
    """
    norm_dir = base / "normalized" / date_str
    if not norm_dir.exists():
        log.warning("normalized dir missing, skipping ixp_paths build")
        return 0

    # Descobrir todos os (code, afi) com arquivo de rotas disponível
    tasks: list[tuple[str, str, Path]] = []
    for ixp_dir in sorted(norm_dir.iterdir()):
        if not ixp_dir.is_dir():
            continue
        for afi in ("v4", "v6"):
            p = ixp_dir / f"routes-{afi}.json.gz"
            if p.exists():
                tasks.append((ixp_dir.name, afi, p))

    if not tasks:
        log.warning("no route files found for ixp_paths build")
        return 0

    log.info("building ixp_paths index", ixp_afi_files=len(tasks))

    # Lê todos em paralelo: cada tarefa retorna (code, afi, {origin: {path: count}})
    import os
    workers = min(len(tasks), os.cpu_count() or 4)
    raw_indexes: list[tuple[str, str, dict]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        fut_map = {
            pool.submit(_parse_route_file, path): (code, afi)
            for code, afi, path in tasks
        }
        for fut in as_completed(fut_map):
            code, afi = fut_map[fut]
            try:
                idx = fut.result()
                raw_indexes.append((code, afi, idx))
                log.debug("route file parsed", code=code, afi=afi, origins=len(idx))
            except Exception as exc:
                log.warning("route file parse failed", code=code, afi=afi, error=str(exc))

    # Constrói índice reverso: origin_asn → {code → {afi → [(path_tuple, count), ...]}}
    by_asn: dict[int, dict[str, dict[str, list[tuple]]]] = {}
    for code, afi, idx in raw_indexes:
        for origin_asn, paths_dict in idx.items():
            entry = by_asn.setdefault(origin_asn, {})
            afi_paths = entry.setdefault(code, {})
            sorted_paths = sorted(paths_dict.items(), key=lambda kv: -kv[1])
            afi_paths[afi] = [list(pt) for pt, _cnt in sorted_paths]

    log.info("reverse index built", asns_with_paths=len(by_asn))

    # Enriquece os arquivos ASN
    pub_dir = published_path(base, date_str, "asns")
    enriched = 0
    fragmento = None
    if compose.fluxo_novo(base, date_str):    # ARANDU_COMPOSE=on: grava o pedaço `ixp_paths`; o compose monta o documento
        _frag_ctx = compose.gravar_fragmento(base, date_str, "ixp_paths")
        fragmento = _frag_ctx.__enter__()
    def _candidatos():
        if fragmento is not None:
            # lê o fragmento `base` (os documentos publicados só existem depois do compose final)
            for a, d in compose.iterar_documentos(base, date_str, ("base",)):
                if a in by_asn:
                    yield a, by_asn[a], None, d
            return
        for a, cm in by_asn.items():
            p = pub_dir / f"{a}.json"
            if not p.exists():
                continue
            try:
                d = json.loads(p.read_bytes())
            except Exception:
                continue
            yield a, cm, p, d

    for asn, code_map, path, doc in _candidatos():
        ixp_presence = doc.get("ixp_presence", {})

        # Conta IXPs origin-only para aplicar o mesmo cap do handler da API
        origin_only_count = sum(
            1 for code, pres in ixp_presence.items()
            if (pres.get("v4", {}).get("origin") or pres.get("v6", {}).get("origin"))
            and not (pres.get("v4", {}).get("direct") or pres.get("v6", {}).get("direct"))
        )
        if origin_only_count > 40:
            continue

        ixp_paths: dict[str, list[list[int]]] = {}
        for code, afi_map in code_map.items():
            pres = ixp_presence.get(code, {})
            if pres.get("v4", {}).get("direct") or pres.get("v6", {}).get("direct"):
                continue  # pular IXPs diretos

            seen: set[tuple] = set()
            merged: list[list[int]] = []
            for afi in ("v4", "v6"):
                for path_list in afi_map.get(afi, []):
                    pt = tuple(path_list)
                    if pt not in seen:
                        seen.add(pt)
                        merged.append(path_list)
            if merged:
                ixp_paths[code] = merged

        if not ixp_paths:
            continue

        if fragmento is not None:
            fragmento.escrever(asn, {"ixp_paths": ixp_paths})
        else:
            doc["ixp_paths"] = ixp_paths
            path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        enriched += 1

    if fragmento is not None:
        _frag_ctx.__exit__(None, None, None)

    log.info("ixp_paths enrichment done", enriched=enriched)
    return enriched


def executar_indice(base: Path, date_str: str, log) -> dict:
    """Produto `asn_docs`, parte 1: `asns/index.json` (e, em `build/`, os conjuntos de prefixos que o Hilbert e o resumo usam)."""
    asn_index, g4, i4, i6, g6 = publicar_asn_index(base, date_str, log)
    destino = published_path(base, date_str, "asns") / "index.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(asn_index, ensure_ascii=False), encoding="utf-8")
    intermediarios.gravar_conjuntos(base, date_str, g4, g6, i4, i6)
    log.info("asn index written", asns=len(asn_index), global_br_prefixes=len(g4), global_br_v6_prefixes=len(g6),
             ixp_v4_prefixes=len(i4), ixp_v6_prefixes=len(i6))
    return {"asns_indexed": len(asn_index)}


def executar_nomes(base: Path, date_str: str, log) -> dict:
    """Produto `asn_docs`, parte 2: `asns/names.json`."""
    return {"asn_names": publicar_asn_names(base, date_str, log)}


def executar_ixp_paths(base: Path, date_str: str, log) -> dict:
    """Produto `asn_docs`, parte 3: caminhos de IXP por ASN (fragmento `ixp_paths`)."""
    return {"ixp_paths_enriched": publicar_ixp_paths(base, date_str, log)}
