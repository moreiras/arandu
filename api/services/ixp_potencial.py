# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Potencial dos PTTs: usuários estimados por IXP, vizinhança de ASes por raio e o índice de potencial.

Serviço sobre o `Store`: guarda os caches e a lógica deste assunto; o que lê de outros artefatos pede ao `Store` por
`__getattr__`, então o `Store` segue sendo a fachada e delega aqui os métodos públicos.
"""
from __future__ import annotations

import ipaddress
from api.geo import haversine_km
from typing import Optional

from api.store import IXP_POTENTIAL_PROXIMITY_KM, _collapsed_nets, _space_gap_units


class IxpPotencialService:
    def __init__(self, store):
        self._s = store
        self._ixp_est_users_agg_cache: dict[str, dict] = {}
        # Cache: "{date}/{code}" → estimativa de usuários finais BR visíveis (IPv4)
        self._ixp_est_users_cache: dict[str, dict] = {}
        # Cache: "{date}/{code}" → indicadores da seção "Potencial" do IXP
        self._ixp_potential_cache: dict[str, Optional[dict]] = {}

    def __getattr__(self, nome):
        if nome == "_s":
            raise AttributeError(nome)
        return getattr(self._s, nome)

    def ixp_nearby_breakdown(
        self, date_str: str, code: str, radius_km: float = 80.0, limit: int = 500
    ) -> dict:
        """ASes com prefixos geolocalizados a ≤ radius_km de algum PIX do PTT `code`.

        Para cada AS: classificação de presença no PTT (direct = membro do cadastro / origin / absent) e
        quantos dos seus prefixos próximos ainda NÃO estão anunciados no PTT.
        Generaliza a seção "Potencial" com raio parametrizável e quebra por AS.
        """
        from api.query import QueryError

        code = code.lower()
        pix = self._pix_points(date_str, code)
        if not pix:
            raise QueryError(f"PTT '{code}' sem PIX geolocalizado")

        # 1) prefixos próximos por AS (a partir da tabela geo de prefixos BR)
        nearby: dict[int, list[str]] = {}
        for row in self.query_table(date_str, "prefixes"):
            lat, lon = row.get("lat"), row.get("lon")
            asn = row.get("origin_asn")
            pfx = row.get("prefix")
            if lat is None or lon is None or asn is None or not pfx:
                continue
            if any(haversine_km(lat, lon, plat, plon) <= radius_km for plat, plon in pix):
                nearby.setdefault(int(asn), []).append(pfx)

        # 2) prefixos já anunciados no PTT, por AS (v6 ∪ v4)
        announced: dict[int, set] = {}
        for afi in ("v4", "v6"):
            for asn_str, pfxs in (self._load_origin_prefixes(date_str, code, afi) or {}).items():
                try:
                    announced.setdefault(int(asn_str), set()).update(pfxs or [])
                except (TypeError, ValueError):
                    continue

        pres = self.asn_ix_presence(date_str).get("asns", {})
        names = self.asn_map(date_str)

        items: list[dict] = []
        summary = {"direct": 0, "origin": 0, "absent": 0, "with_gap": 0}
        for asn, pfxs in nearby.items():
            p = pres.get(str(asn), {})
            if code in p.get("m", []):
                status = "direct"
            elif code in p.get("o", []):
                status = "origin"
            else:
                status = "absent"
            summary[status] += 1
            ann = announced.get(asn, set())
            gap = [x for x in pfxs if x not in ann]
            if gap:
                summary["with_gap"] += 1
            items.append({
                "asn": asn,
                "name": (names.get(asn) or {}).get("name"),
                "status": status,
                "nearby_prefixes": len(pfxs),
                "not_announced": len(gap),
                "not_announced_sample": sorted(gap)[:10],
            })

        items.sort(key=lambda x: (x["not_announced"], x["nearby_prefixes"]), reverse=True)
        return {
            "snapshot_date": date_str,
            "ixp": code,
            "radius_km": radius_km,
            "pix_points": len(pix),
            "summary": {**summary, "total_nearby_asns": len(nearby)},
            "asns": items[:limit],
        }

    def _ixp_user_contributions(self, date_str: str, code: str) -> dict[int, float]:
        """{asn BR originador: fração de espaço IPv4 visível no PTT}. Mesma matemática
        de ixp_estimated_users; usado para de-duplicar usuários em operator_reach."""
        origins = self._load_origin_prefixes(date_str, code, "v4")
        asn_lkp = self.asn_map(date_str)
        out: dict[int, float] = {}
        for asn_str, prefixes in (origins or {}).items():
            try:
                asn = int(asn_str)
            except (TypeError, ValueError):
                continue
            row = asn_lkp.get(asn)
            if row is None or not row.get("is_br"):
                continue
            users, space_v4 = row.get("apnic_users"), row.get("space_v4")
            if not users or not space_v4:
                continue
            nets = []
            for p in prefixes or []:
                try:
                    net = ipaddress.ip_network(p, strict=False)
                except ValueError:
                    continue
                if net.version == 4 and net.prefixlen <= 24:
                    nets.append(net)
            if not nets:
                continue
            visible_24 = sum(1 << (24 - n.prefixlen) for n in ipaddress.collapse_addresses(nets))
            out[asn] = min(visible_24 / space_v4, 1.0)
        return out

    def operator_reach(self, date_str: str, asns: list[int]) -> dict:
        """Alcance de usuários finais BR de um operador (conjunto de ASes) via os PTTs
        onde está presente.

        Para cada PTT onde algum dos `asns` participa (direto ou origem), considera os
        usuários BR visíveis (metodologia de estimated_users). O total de-duplicado
        toma, por AS-olho, a MAIOR fração entre os PTTs (um usuário alcançável por
        vários PTTs conta uma vez). Também reporta a soma simples por PTT.
        """
        op = {int(a) for a in asns}
        pres = self.asn_ix_presence(date_str).get("asns", {})
        ptts: set[str] = set()
        for a in op:
            p = pres.get(str(a), {})
            ptts.update(p.get("m", []))
            ptts.update(p.get("o", []))
        ptts = sorted(ptts)

        best: dict[int, float] = {}
        per_ptt: list[dict] = []
        for code in ptts:
            est = self.ixp_estimated_users(date_str, code).get("estimated_users", 0)
            per_ptt.append({"code": code, "estimated_users": est})
            for ey, frac in self._ixp_user_contributions(date_str, code).items():
                if frac > best.get(ey, 0.0):
                    best[ey] = frac

        asn_lkp = self.asn_map(date_str)
        reach = sum((asn_lkp.get(ey, {}).get("apnic_users") or 0) * frac
                    for ey, frac in best.items())
        return {
            "snapshot_date": date_str,
            "operator_asns": sorted(op),
            "ptt_count": len(ptts),
            "ptts": ptts,
            "reach_users_dedup": int(round(reach)),
            "reach_users_sum_per_ptt": sum(p["estimated_users"] for p in per_ptt),
            "eyeball_asns": len(best),
            "per_ptt": per_ptt,
            "method": ("usuários BR visíveis (apnic × fração de espaço IPv4 anunciado no "
                       "PTT); dedup = máx. fração por AS-olho entre os PTTs do operador"),
        }

    def ixp_estimated_users(self, date_str: str, code: str) -> dict:
        """Estimativa de usuários finais BR visíveis via o IXP (IPv4).

        Para cada AS BR que origina prefixos IPv4 no IXP:
            fração = espaço_v4_visível_no_IXP / espaço_v4_total_anunciado_do_AS
            usuários_visíveis = usuários_APNIC × min(fração, 1)
        Soma sobre os AS BR originadores. Espaços em /24-equivalentes; os prefixos
        visíveis são colapsados para não contar blocos aninhados em duplicidade.
        Cacheado por (date, code).
        """
        cache_key = f"{date_str}/{code}"
        if cache_key in self._ixp_est_users_cache:
            return self._ixp_est_users_cache[cache_key]

        origins = self._load_origin_prefixes(date_str, code, "v4")  # {asn_str: [prefixes]}
        asn_lkp = self.asn_map(date_str)

        total_users = 0.0
        contributing = 0
        for asn_str, prefixes in origins.items():
            try:
                asn = int(asn_str)
            except (TypeError, ValueError):
                continue
            row = asn_lkp.get(asn)
            if row is None or not row.get("is_br"):
                continue
            users = row.get("apnic_users")
            space_v4 = row.get("space_v4")  # /24-equiv do espaço global anunciado
            if not users or not space_v4:
                continue

            nets = []
            for p in prefixes or []:
                try:
                    net = ipaddress.ip_network(p, strict=False)
                except ValueError:
                    continue
                if net.version == 4 and net.prefixlen <= 24:
                    nets.append(net)
            if not nets:
                continue
            visible_24 = sum(
                1 << (24 - net.prefixlen)
                for net in ipaddress.collapse_addresses(nets)
            )

            frac = min(visible_24 / space_v4, 1.0)
            total_users += users * frac
            contributing += 1

        result = {
            "snapshot_date": date_str,
            "ixp": code,
            "afi": "v4",
            "estimated_users": int(round(total_users)),
            "contributing_asns": contributing,
        }
        self._ixp_est_users_cache[cache_key] = result
        return result

    def all_ixp_estimated_users(self, date_str: str) -> dict:
        """{code: estimated_users} para todos os IXes do índice. Reusa o cache por IXP."""
        out: dict[str, int] = {}
        for entry in self.ixp_index(date_str):
            code = entry.get("code")
            if code:
                out[code] = self.ixp_estimated_users(date_str, code)["estimated_users"]
        return {"snapshot_date": date_str, "afi": "v4", "ixps": out}

    def ixp_estimated_users_aggregate(self, date_str: str) -> dict:
        """Estimativa de usuários finais BR visíveis no IX.br como um todo (IPv4).

        Mesma metodologia de `ixp_estimated_users`, mas une os prefixos que cada AS
        origina em TODOS os IXPs do IX.br antes de calcular a fração — evita contar
        o mesmo espaço (e os mesmos usuários) uma vez por IXP em que o AS aparece.
        Cacheado por data.
        """
        if date_str in self._ixp_est_users_agg_cache:
            return self._ixp_est_users_agg_cache[date_str]

        prefixes_by_asn: dict[int, set] = {}
        for entry in self.ixp_index(date_str):
            code = entry.get("code")
            if not code:
                continue
            origins = self._load_origin_prefixes(date_str, code, "v4")
            for asn_str, prefixes in origins.items():
                try:
                    asn = int(asn_str)
                except (TypeError, ValueError):
                    continue
                prefixes_by_asn.setdefault(asn, set()).update(prefixes or [])

        asn_lkp = self.asn_map(date_str)
        total_users = 0.0
        contributing = 0
        for asn, prefixes in prefixes_by_asn.items():
            row = asn_lkp.get(asn)
            if row is None or not row.get("is_br"):
                continue
            users = row.get("apnic_users")
            space_v4 = row.get("space_v4")
            if not users or not space_v4:
                continue

            nets = []
            for p in prefixes:
                try:
                    net = ipaddress.ip_network(p, strict=False)
                except ValueError:
                    continue
                if net.version == 4 and net.prefixlen <= 24:
                    nets.append(net)
            if not nets:
                continue
            visible_24 = sum(
                1 << (24 - net.prefixlen)
                for net in ipaddress.collapse_addresses(nets)
            )

            frac = min(visible_24 / space_v4, 1.0)
            total_users += users * frac
            contributing += 1

        result = {
            "snapshot_date": date_str,
            "afi": "v4",
            "estimated_users": int(round(total_users)),
            "contributing_asns": contributing,
        }
        self._ixp_est_users_agg_cache[date_str] = result
        return result

    def _ixp_pix_points(self, date_str: str, code: str, ixp_doc: dict) -> list[tuple]:
        """Lista de (lat, lon) dos PIX (pontos de presença) de um IXP — de
        config/pix.yaml ou, na ausência, da mediana dos ASNs geolocalizados na
        mesma cidade (mesmo fallback usado no mapa do IXP)."""
        pix_cfg = self._load_pix_config()
        if code in pix_cfg:
            return [(p["lat"], p["lon"]) for p in pix_cfg[code]]
        uf = ixp_doc.get("uf") or ""
        name = ixp_doc.get("name") or ""
        if uf and name:
            coords = self._ixp_city_coords(date_str, uf, name)
            if coords:
                return [(coords["lat"], coords["lon"])]
        return []

    def ixp_potential(self, date_str: str, code: str) -> Optional[dict]:
        """Indicadores de potencial de crescimento de um PTT do IX.br (seção
        "Potencial" da página do IXP).

        - `nearby_asn_count`: ASes com sede ou prefixos anunciados a até
          `IXP_POTENTIAL_PROXIMITY_KM` de algum PIX do PTT que ainda não
          participam diretamente nem originam prefixos nele.
        - `v4_prefixes_24` / `v6_prefixes_48`: prefixos já anunciados neste
          PTT (route server) ∪ todos os prefixos geolocalizados num raio de
          `IXP_POTENTIAL_PROXIMITY_KM` km de algum PIX — colapsados e
          contados em equivalentes /24 ou /48.
        - `estimated_users_total`: para cada AS BR com prefixos na union v4,
          apnic_users × min(union_24_do_AS / space_v4_global, 1.0) — mesma
          metodologia de `ixp_estimated_users` mas sobre a union de prefixos.
        Cacheado por (date, code).
        """
        cache_key = f"{date_str}/{code}"
        if cache_key in self._ixp_potential_cache:
            return self._ixp_potential_cache[cache_key]

        ixp_doc = self.ixp_detail(date_str, code)
        if ixp_doc is None:
            return None

        pix_points = self._ixp_pix_points(date_str, code, ixp_doc)

        origins_v4 = self._load_origin_prefixes(date_str, code, "v4")
        origins_v6 = self._load_origin_prefixes(date_str, code, "v6")
        origin_set = {int(a) for a in origins_v4} | {int(a) for a in origins_v6}

        nearby: set = set()
        asn_v4_nearby: dict[int, set[str]] = {}
        asn_v6_nearby: dict[int, set[str]] = {}

        if pix_points:
            asns_geo = self.geo_map(date_str, "asns") or {}
            for f in asns_geo.get("features", []):
                props = f.get("properties") or {}
                asn = props.get("asn")
                coords = (f.get("geometry") or {}).get("coordinates")
                if asn is None or not coords:
                    continue
                lon, lat = coords[0], coords[1]
                if any(haversine_km(lat, lon, plat, plon) <= IXP_POTENTIAL_PROXIMITY_KM
                       for plat, plon in pix_points):
                    nearby.add(int(asn))

            prefixes_geo = self.geo_map(date_str, "prefixes") or {}
            for f in prefixes_geo.get("features", []):
                props = f.get("properties") or {}
                asn = props.get("origin_asn")
                coords = (f.get("geometry") or {}).get("coordinates")
                if asn is None or not coords:
                    continue
                lon, lat = coords[0], coords[1]
                if any(haversine_km(lat, lon, plat, plon) <= IXP_POTENTIAL_PROXIMITY_KM
                       for plat, plon in pix_points):
                    nearby.add(int(asn))
                    prefix = props.get("prefix")
                    if prefix:
                        version = props.get("ip_version")
                        if version == 4:
                            asn_v4_nearby.setdefault(int(asn), set()).add(prefix)
                        elif version == 6:
                            asn_v6_nearby.setdefault(int(asn), set()).add(prefix)

        nearby_absent = nearby - origin_set

        # Build per-AS union of origin prefixes at IXP + nearby geolocated prefixes
        asn_v4_union: dict[int, set[str]] = {}
        for asn_str, prefs in origins_v4.items():
            try:
                asn_int = int(asn_str)
            except (TypeError, ValueError):
                continue
            asn_v4_union[asn_int] = set(prefs or [])
        for asn_int, prefs in asn_v4_nearby.items():
            asn_v4_union.setdefault(asn_int, set()).update(prefs)

        # Space metrics: IXP prefix-set (all announced, incl. transit) ∪ nearby geolocated
        all_nearby_v4 = {p for prefs in asn_v4_nearby.values() for p in prefs}
        all_nearby_v6 = {p for prefs in asn_v6_nearby.values() for p in prefs}
        ixp_v4 = set(self._load_ixp_prefix_set(date_str, code, "v4"))
        ixp_v6 = set(self._load_ixp_prefix_set(date_str, code, "v6"))
        union_v4 = _collapsed_nets(list(ixp_v4 | all_nearby_v4), 4)
        union_v6 = _collapsed_nets(list(ixp_v6 | all_nearby_v6), 6)
        v4_units = _space_gap_units(union_v4, [], 24)
        v6_units = _space_gap_units(union_v6, [], 48)

        # Users metric: para cada AS BR com prefixos na union v4,
        # apnic_users × min(union_24_do_AS / space_v4_global, 1.0)
        asn_lkp = self.asn_map(date_str)
        users_total = 0.0
        for asn_int, prefs in asn_v4_union.items():
            row = asn_lkp.get(asn_int)
            if row is None or not row.get("is_br"):
                continue
            apnic_users = row.get("apnic_users")
            space_v4 = row.get("space_v4")  # /24-equiv do espaço global anunciado
            if not apnic_users or not space_v4:
                continue
            nets = []
            for p in prefs:
                try:
                    net = ipaddress.ip_network(p, strict=False)
                except ValueError:
                    continue
                if net.version == 4 and net.prefixlen <= 24:
                    nets.append(net)
            if not nets:
                continue
            union_24 = sum(
                1 << (24 - net.prefixlen)
                for net in ipaddress.collapse_addresses(nets)
            )
            frac = min(union_24 / space_v4, 1.0)
            users_total += apnic_users * frac

        result = {
            "snapshot_date": date_str,
            "ixp": code,
            "nearby_asn_count": len(nearby_absent),
            "v4_prefixes_24": int(round(v4_units)),
            "v6_prefixes_48": int(round(v6_units)),
            "estimated_users_total": int(round(users_total)),
        }
        self._ixp_potential_cache[cache_key] = result
        return result
