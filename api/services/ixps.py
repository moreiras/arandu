# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Por IXP: estatísticas por peer, assinantes e os mapas de Hilbert por PTT.

Serviço sobre o `Store`: guarda os caches e a lógica deste assunto; o que lê de outros artefatos pede ao `Store` por
`__getattr__`, então o `Store` segue sendo a fachada e delega aqui os métodos públicos.
"""
from __future__ import annotations

from ipaddress import ip_network
from typing import Optional

from api.store import _SafeLRU, _env_int, _v6_to_sparse


class IxpsService:
    def __init__(self, store):
        self._s = store
        # muitas páginas de ASN. LRU evita crescimento ilimitado (80 IXPs × 2 AFIs).
        self._ixp_peers_cache: _SafeLRU = _SafeLRU(maxsize=_env_int("STORE_IXP_PEERS_LRU", 24))

    def __getattr__(self, nome):
        if nome == "_s":
            raise AttributeError(nome)
        return getattr(self._s, nome)

    def ixp_peers_stats(self, date_str: str, code: str, afi: str) -> Optional[dict]:
        """Calcula estatísticas por peer direto a partir das rotas normalizadas.

        Memoizado por (date, code, afi): parsear o routes-{afi}.json.gz é caro e o
        mesmo IXP é consultado por muitas páginas de ASN.
        """
        key = f"{date_str}/{code}/{afi}"
        try:
            return self._ixp_peers_cache[key]
        except KeyError:
            pass

        # `bgp_ixp` grava `peers-{afi}.json.gz` ao lado das rotas (1.4.2.1): ler isto é milissegundos; reler as rotas do PTT
        # inteiro leva segundos por PTT e AFI. Snapshot sem o arquivo recalcula com a mesma função (core/ixp_peers.py).
        norm = self._norm_dir(date_str, code)
        pronto = self._read_json_gz(norm / f"peers-{afi}.json.gz")
        if isinstance(pronto, dict):
            self._ixp_peers_cache[key] = pronto
            return pronto
        data = self._read_json_gz(norm / f"routes-{afi}.json.gz")
        if not data:
            self._ixp_peers_cache[key] = None
            return None
        from core.ixp_peers import estatisticas_por_peer
        result = estatisticas_por_peer(data.get("routes", []), afi)
        self._ixp_peers_cache[key] = result
        return result

    def ixp_assinantes(self, date_str: str, code: str) -> Optional[dict]:
        """Empresa (CNPJ), outorgas, usuários APNIC e assinantes SICI (SCM) por
        peer direto de um IXP, mais a distribuição municipal agregada.

        - `assinantes_diretos` — acessos SICI (pf + pj) do CNPJ do próprio peer.
        - `assinantes_total` — acessos SICI dos CNPJs de todos os ASNs que aparecem
          nos AS-paths anunciados pelo peer no IXP (ele próprio e seus clientes),
          por AFI. Soma deduplicada por CNPJ: vários ASNs do mesmo CNPJ contam uma
          vez só (o SICI atribui o total integral a cada AS do CNPJ).

        No nível do IXP, `municipios_diretos` agrega os CNPJs dos peers diretos
        (v6 ∪ v4) e `municipios_totais` os de todos os ASNs vistos nas rotas.
        Memoizado por (date, code).
        """
        key = f"{date_str}/{code}/assinantes"
        try:
            return self._ixp_peers_cache[key]
        except KeyError:
            pass

        if self.ixp_detail(date_str, code) is None:
            return None

        # ASN → CNPJ: geo_orgs (todos os AS BR com CNPJ), completado pelo SICI
        asn_cnpj: dict[int, str] = {}
        for cnpj, asns in self.cnpj_asns_index(date_str).items():
            for a in asns:
                asn_cnpj[a] = cnpj
        sici = self._load_sici(date_str) or {}
        for a, cnpj in sici.get("asn_to_cnpj", {}).items():
            asn_cnpj.setdefault(int(a), cnpj)
        sici_cnpjs: dict = sici.get("cnpjs", {})

        def acessos(cnpjs: set[str]) -> int:
            return sum((sici_cnpjs.get(c) or {}).get("acessos", 0) for c in cnpjs)

        # Peer direto → ASNs presentes nos AS-paths que ele anuncia, por AFI
        cones: dict[str, dict[int, set[int]]] = {}
        for afi in ("v4", "v6"):
            data = self._read_json_gz(self._norm_dir(date_str, code) / f"routes-{afi}.json.gz") or {}
            cone: dict[int, set[int]] = {}
            for route in data.get("routes", []):
                aspath = route.get("aspath") or []
                if aspath:
                    cone.setdefault(aspath[0], set()).update(aspath)
            cones[afi] = cone

        asn_map = self.asn_map(date_str)
        all_peers = set(cones["v4"]) | set(cones["v6"])
        asns_out: dict[str, dict] = {}
        for asn in all_peers:
            cnpj = asn_cnpj.get(asn)
            asns_out[str(asn)] = {
                "cnpj": cnpj,
                "empresa": self._display_name_for_cnpj(date_str, cnpj) if cnpj else None,
                **(self.outorgas_flags_for_cnpj(date_str, cnpj) if cnpj else {
                    "has_scm": False, "has_smp": False, "has_stfc": False, "has_seac": False,
                }),
                "usuarios_apnic": (asn_map.get(asn) or {}).get("apnic_users"),
                "assinantes_diretos": acessos({cnpj}) if cnpj else 0,
            }

        peers_out: dict[str, dict[str, int]] = {}
        for afi, cone in cones.items():
            peers_out[afi] = {
                str(asn): acessos({asn_cnpj[a] for a in members if a in asn_cnpj})
                for asn, members in cone.items()
            }

        def municipios(cnpjs: set[str]) -> list[dict]:
            agg: dict[str, dict] = {}
            for c in cnpjs:
                for ibge, mun in ((sici_cnpjs.get(c) or {}).get("por_municipio") or {}).items():
                    e = agg.setdefault(ibge, {
                        "ibge": ibge, "nome": mun.get("nome", ""), "uf": mun.get("uf", ""),
                        "acessos": 0,
                    })
                    e["acessos"] += mun.get("acessos", 0)
            return sorted(agg.values(), key=lambda m: -m["acessos"])

        cnpjs_diretos = {asn_cnpj[a] for a in all_peers if a in asn_cnpj}
        cnpjs_totais = {
            asn_cnpj[a]
            for cone in cones.values() for members in cone.values() for a in members
            if a in asn_cnpj
        }
        result = {
            "mes_referencia": sici.get("mes_referencia", ""),
            "asns": asns_out,
            "peers": peers_out,
            "assinantes_diretos": acessos(cnpjs_diretos),
            "assinantes_total": acessos(cnpjs_totais),
            "municipios_diretos": municipios(cnpjs_diretos),
            "municipios_totais": municipios(cnpjs_totais),
        }
        self._ixp_peers_cache[key] = result
        return result

    def ixp_hilbert_v4(self, date_str: str, code: str, peer: Optional[int] = None) -> Optional[dict]:
        """Densidade Hilbert /16 para o IXP (total ou filtrado por peer direto)."""
        if peer is None:
            path = self._norm_dir(date_str, code) / "prefix-set-v4.json.gz"
            data = self._read_json_gz(path)
            if data is None:
                return None
            prefixes = data if isinstance(data, list) else []
            return {"all": self._prefixes_to_density16(prefixes)}

        path = self._norm_dir(date_str, code) / "routes-v4.json.gz"
        data = self._read_json_gz(path)
        if not data:
            return None

        own: set[str] = set()
        third: set[str] = set()
        for route in data.get("routes", []):
            aspath = route.get("aspath", [])
            if not aspath or aspath[0] != peer:
                continue
            pfx = route.get("prefix", "")
            if not pfx:
                continue
            if aspath[-1] == peer:
                own.add(pfx)
            else:
                third.add(pfx)

        return {
            "own": self._prefixes_to_density16(own),
            "third": self._prefixes_to_density16(third),
        }

    def ixp_hilbert_v4_detail(
        self, date_str: str, code: str, slash8: int, peer: Optional[int] = None
    ) -> Optional[dict]:
        """Blocos /24 presentes dentro de um /8 específico, para o zoom do Hilbert."""

        def extract_24s(prefixes) -> dict[str, list[int]]:
            result: dict[str, set[int]] = {}
            for prefix_str in prefixes:
                try:
                    net = ip_network(prefix_str, strict=False)
                    if net.version != 4:
                        continue
                    addr_int = int(net.network_address)
                    if (addr_int >> 24) & 0xFF != slash8:
                        continue
                    b = (addr_int >> 16) & 0xFF
                    c_start = (addr_int >> 8) & 0xFF
                    plen = net.prefixlen
                    if plen <= 16:
                        c_vals: set[int] = set(range(256))
                    elif plen <= 24:
                        c_vals = set(range(c_start, min(c_start + (1 << (24 - plen)), 256)))
                    else:
                        c_vals = {c_start}
                    key = str(b)
                    if key not in result:
                        result[key] = set()
                    result[key].update(c_vals)
                except ValueError:
                    pass
            return {k: sorted(v) for k, v in result.items()}

        if peer is None:
            path = self._norm_dir(date_str, code) / "prefix-set-v4.json.gz"
            data = self._read_json_gz(path)
            if data is None:
                return None
            prefixes = data if isinstance(data, list) else []
            return {"all": extract_24s(prefixes)}

        path = self._norm_dir(date_str, code) / "routes-v4.json.gz"
        data = self._read_json_gz(path)
        if not data:
            return None

        own: set[str] = set()
        third: set[str] = set()
        for route in data.get("routes", []):
            aspath = route.get("aspath", [])
            if not aspath or aspath[0] != peer:
                continue
            pfx = route.get("prefix", "")
            if not pfx:
                continue
            if aspath[-1] == peer:
                own.add(pfx)
            else:
                third.add(pfx)

        return {"own": extract_24s(own), "third": extract_24s(third)}

    def ixp_hilbert_v6(self, date_str: str, code: str, peer: Optional[int] = None) -> Optional[dict]:
        """Índices esparsos /32 IPv6 para o IXP (total ou filtrado por peer direto)."""
        if peer is None:
            path = self._norm_dir(date_str, code) / "prefix-set-v6.json.gz"
            data = self._read_json_gz(path)
            if data is None:
                return None
            prefixes = data if isinstance(data, list) else []
            return {"all": _v6_to_sparse(prefixes)}

        path = self._norm_dir(date_str, code) / "routes-v6.json.gz"
        data = self._read_json_gz(path)
        if not data:
            return None

        own: set[str] = set()
        third: set[str] = set()
        for route in data.get("routes", []):
            aspath = route.get("aspath", [])
            if not aspath or aspath[0] != peer:
                continue
            pfx = route.get("prefix", "")
            if not pfx:
                continue
            if aspath[-1] == peer:
                own.add(pfx)
            else:
                third.add(pfx)

        return {
            "own": _v6_to_sparse(own),
            "third": _v6_to_sparse(third),
        }
