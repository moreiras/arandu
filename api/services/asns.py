# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Consultas por ASN: caminhos, peers em IXPs, nomes, estabilidade BGP resumida, coordenadas, origem por prefixo e inícios anunciados.

Serviço sobre o `Store`: guarda os caches e a lógica deste assunto; o que lê de outros artefatos pede ao `Store` por
`__getattr__`, então o `Store` segue sendo a fachada e delega aqui os métodos públicos.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from ipaddress import ip_network
from typing import Optional


class AsnsService:
    def __init__(self, store):
        self._s = store
        # Cache: "{date}/{afi}" → lista ordenada de endereços-início anunciados (int)
        self._announced_starts_cache: dict[str, list[int]] = {}
        self._bgp_por_asn: dict[str, dict[int, dict]] = {}
        # Lazy mmdb reader — None until first geo request; False if unavailable
        self._bgp_resumo: dict[str, list[dict]] = {}
        # Cache: date_str → {asn: (lat, lon)} de geo_orgs.json.gz
        self._geo_orgs_coords: dict[str, dict[int, tuple]] = {}
        # Cache: "{date}/{afi}" → {prefixo: asn_origem} (índice reverso da full table)
        self._origin_by_prefix_cache: dict[str, dict[str, int]] = {}

    def __getattr__(self, nome):
        if nome == "_s":
            raise AttributeError(nome)
        return getattr(self._s, nome)

    def asn_paths(self, date_str: str, asn: int) -> Optional[dict]:
        """Cadeias AS_PATH por IXP onde o AS aparece como originador (não direto).

        Inclui metadados dos ASes intermediários (`path_node_meta`). Retorna None se
        o AS não existe no snapshot; `ixp_paths` é `{}` quando não há caminhos.
        """
        doc = self.asn_detail(date_str, asn)
        if doc is None:
            return None

        origin_ixp_count = sum(
            1 for presence in doc.get("ixp_presence", {}).values()
            if (presence.get("v4", {}).get("origin") or presence.get("v6", {}).get("origin"))
            and not (presence.get("v4", {}).get("direct") or presence.get("v6", {}).get("direct"))
        )
        precomputed_paths = doc.get("ixp_paths")

        ixp_paths: dict = {}
        path_node_meta: dict = {}

        if precomputed_paths or origin_ixp_count <= 40:
            try:
                if precomputed_paths:
                    ixp_paths = precomputed_paths
                else:
                    origin_tasks: list[tuple[str, str]] = []
                    for code, presence in doc.get("ixp_presence", {}).items():
                        v4 = presence.get("v4", {})
                        v6 = presence.get("v6", {})
                        if v4.get("direct") or v6.get("direct"):
                            continue
                        for afi in ("v4", "v6"):
                            if presence.get(afi, {}).get("origin"):
                                origin_tasks.append((code, afi))

                    path_index: dict[tuple[str, str], dict] = {}
                    with ThreadPoolExecutor(max_workers=min(len(origin_tasks), 8)) as pool:
                        fut_map = {
                            pool.submit(self.ixp_origin_paths, date_str, code, afi): (code, afi)
                            for code, afi in origin_tasks
                        }
                        for fut in as_completed(fut_map):
                            key = fut_map[fut]
                            try:
                                path_index[key] = fut.result()
                            except Exception:
                                path_index[key] = {}

                    for code, presence in doc.get("ixp_presence", {}).items():
                        v4 = presence.get("v4", {})
                        v6 = presence.get("v6", {})
                        if v4.get("direct") or v6.get("direct"):
                            continue
                        if not (v4.get("origin") or v6.get("origin")):
                            continue
                        seen_paths: set[tuple] = set()
                        all_paths: list[list[int]] = []
                        for afi in ("v4", "v6"):
                            if not presence.get(afi, {}).get("origin"):
                                continue
                            idx = path_index.get((code, afi), {})
                            for path_tuple, _count in idx.get(asn, []):
                                if path_tuple not in seen_paths:
                                    seen_paths.add(path_tuple)
                                    all_paths.append(list(path_tuple))
                        if all_paths:
                            ixp_paths[code] = all_paths

                if ixp_paths:
                    try:
                        path_asns: dict[int, set[str]] = {}
                        for code, paths in ixp_paths.items():
                            for path in paths:
                                for path_asn in path:
                                    path_asns.setdefault(path_asn, set()).add(code)

                        FEW = 10
                        for path_asn, relevant_codes in path_asns.items():
                            asn_doc = self.asn_detail(date_str, path_asn)
                            if asn_doc is None:
                                continue
                            rir_v4 = asn_doc.get("rir_prefixes_v4", [])
                            rir_v6 = asn_doc.get("rir_prefixes_v6", [])
                            rir_sp4 = self._space24(set(rir_v4))
                            rir_sp6 = self._space48(set(rir_v6))
                            ixp_pres = asn_doc.get("ixp_presence", {})
                            ixp_stats: dict[str, dict] = {}
                            for code in relevant_codes:
                                pres = ixp_pres.get(code, {})
                                v4p = pres.get("v4", {}).get("prefixes", [])
                                v6p = pres.get("v6", {}).get("prefixes", [])
                                sp4 = self._space24(set(v4p))
                                sp6 = self._space48(set(v6p))
                                ixp_stats[code] = {
                                    "v4_count": len(v4p),
                                    "v4_space_24": sp4,
                                    "v4_pct": round(sp4 / rir_sp4 * 100, 1) if rir_sp4 else None,
                                    "v4_prefixes": v4p if len(v4p) <= FEW else None,
                                    "v6_count": len(v6p),
                                    "v6_space_48": sp6,
                                    "v6_pct": round(sp6 / rir_sp6 * 100, 1) if rir_sp6 else None,
                                    "v6_prefixes": v6p if len(v6p) <= FEW else None,
                                }
                            global_v4 = set(asn_doc.get("global_prefixes_v4") or [])
                            global_v6 = set(asn_doc.get("global_prefixes_v6") or [])
                            path_node_meta[str(path_asn)] = {
                                "name": asn_doc.get("name", ""),
                                "is_br": asn_doc.get("is_br", False),
                                "ixp_stats": ixp_stats,
                                "space_v4": self._space24(global_v4),
                                "space_v6": self._space48(global_v6),
                            }
                    except Exception:
                        pass
            except Exception:
                pass

        return {
            "snapshot_date": date_str,
            "asn": asn,
            "ixp_paths": ixp_paths,
            "path_node_meta": path_node_meta,
        }

    def asn_ixp_peers(self, date_str: str, asn: int) -> Optional[dict]:
        """Estatísticas de peering deste AS em cada IXP onde faz peering direto (v6/v4).

        Extrai apenas a linha deste AS de cada IXP direto. Retorna None se o AS não
        existe no snapshot; `peers` é `{}` se não houver peering direto.
        """
        doc = self.asn_detail(date_str, asn)
        if doc is None:
            return None

        direct_codes = [
            code for code, pres in doc.get("ixp_presence", {}).items()
            if pres.get("v4", {}).get("direct") or pres.get("v6", {}).get("direct")
        ]

        peers: dict[str, dict] = {}
        if direct_codes:
            asn_key = str(asn)
            tasks = [(code, afi) for code in direct_codes for afi in ("v4", "v6")]
            with ThreadPoolExecutor(max_workers=min(len(tasks), 8)) as pool:
                fut_map = {
                    pool.submit(self.ixp_peers_stats, date_str, code, afi): (code, afi)
                    for code, afi in tasks
                }
                for fut in as_completed(fut_map):
                    code, afi = fut_map[fut]
                    try:
                        stats = fut.result()
                    except Exception:
                        continue
                    row = (stats or {}).get(asn_key)
                    if row is not None:
                        peers.setdefault(code, {})[afi] = row

        return {"snapshot_date": date_str, "asn": asn, "peers": peers}

    def asn_names(self, date_str: str) -> dict[str, str]:
        """Dicionário {str(asn): name} para todos os ASNs com nome. Cacheado por data."""
        return self._docs.asn_names(date_str)

    def nomes_asns(self, date_str: str, asns: Optional[list[int]] = None, br_only: bool = False, detalhe: bool = False) -> dict:
        """Nomes de ASNs: todos, só os pedidos (`asns`) ou só os BR (`br_only`). Com `detalhe`, cada valor vira
        `{name, uf}` (UF da organização pela geo; `null` fora do Brasil ou sem geo). Passo 1.4.2."""
        nomes = self.asn_names(date_str)
        if asns is not None:
            chaves = [str(a) for a in asns if str(a) in nomes]
        elif br_only:
            br = {str(r["asn"]) for r in self.asn_index(date_str) if r.get("is_br")}
            chaves = [k for k in nomes if k in br]
        else:
            chaves = list(nomes)
        if not detalhe:
            return {k: nomes[k] for k in chaves}
        geo = self._load_geo_orgs(date_str) or {}
        return {k: {"name": nomes[k], "uf": (geo.get(int(k)) or {}).get("uf") or None} for k in chaves}

    def bgp_stability_resumo(self, date_str: str) -> Optional[list[dict]]:
        """Uma linha por AS com `epppd` (eventos/prefixo/dia, total, v6 e v4), a partir de `bgp_stability.json`. Cacheado (4 datas)."""
        cache = self._bgp_resumo
        if date_str not in cache:
            data = self.bgp_stability(date_str)
            if data is None:
                return None
            itens = []
            for a in data.get("as_stability", []):
                p = a.get("period") or {}
                itens.append({"asn": a.get("asn"), "epppd": p.get("events_per_prefix_per_day"),
                              "epppd_v4": p.get("events_per_prefix_per_day_v4"), "epppd_v6": p.get("events_per_prefix_per_day_v6")})
            if len(cache) >= 4:
                cache.pop(next(iter(cache)))
            cache[date_str] = itens
        return cache[date_str]

    def bgp_stability_por_asn(self, date_str: str) -> dict[int, dict]:
        """{asn: {epppd, epppd_v4, epppd_v6}}; vazio se o snapshot não tem a análise."""
        mapas = self._bgp_por_asn
        if date_str not in mapas:
            itens = self.bgp_stability_resumo(date_str) or []
            if len(mapas) >= 4:
                mapas.pop(next(iter(mapas)))
            mapas[date_str] = {i["asn"]: {k: v for k, v in i.items() if k != "asn"} for i in itens}
        return mapas[date_str]

    def asn_coords(self, date_str: str, asn: int) -> Optional[tuple]:
        """Coordenada (lat, lon) do AS via CNPJ geolocalizado em geo_orgs.json.gz. Cacheado."""
        cache = self._geo_orgs_coords.get(date_str)
        if cache is None:
            path = self.base / "normalized" / date_str / "summary" / "geo_orgs.json.gz"
            data = self._read_json_gz(path) or {}
            orgs = data.get("orgs", {}) if isinstance(data, dict) else {}
            cache = {}
            for key, org in orgs.items():
                lat = org.get("lat")
                lon = org.get("lon")
                if lat is None or lon is None:
                    continue
                try:
                    cache[int(key)] = (float(lat), float(lon))
                except (TypeError, ValueError):
                    pass
            self._geo_orgs_coords[date_str] = cache
        return cache.get(asn)

    def origin_by_prefix(self, date_str: str, afi: str) -> dict[str, int]:
        """Índice reverso {prefixo: asn_origem} da full table (origin-prefixes-{afi}). Cacheado."""
        key = f"{date_str}/{afi}"
        cache = self._origin_by_prefix_cache.get(key)
        if cache is None:
            path = self.base / "normalized" / date_str / "summary" / f"origin-prefixes-{afi}.json.gz"
            data = self._read_json_gz(path) or {}
            cache = {}
            if isinstance(data, dict):
                for asn_str, prefixes in data.items():
                    try:
                        a = int(asn_str)
                    except (TypeError, ValueError):
                        continue
                    for p in prefixes or []:
                        cache[p] = a
            self._origin_by_prefix_cache[key] = cache
        return cache

    def announced_starts(self, date_str: str, afi: str) -> list[int]:
        """Lista ordenada dos endereços-início (int) de todos os prefixos anunciados
        na full table, para busca binária de 'existe rota dentro deste bloco'. Cacheado."""
        key = f"{date_str}/{afi}"
        cache = self._announced_starts_cache.get(key)
        if cache is None:
            starts: list[int] = []
            for p in self.origin_by_prefix(date_str, afi).keys():
                try:
                    starts.append(int(ip_network(p, strict=False).network_address))
                except ValueError:
                    pass
            starts.sort()
            self._announced_starts_cache[key] = starts
            cache = starts
        return cache

    # Mapas e geolocalização: ver api/services/mapas.py
