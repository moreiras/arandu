# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Mapas de Hilbert (densidade /16 e detalhe /24), leitura dos JSONs normalizados e origem/membros por IXP.

Serviço sobre o `Store`: guarda os caches e a lógica deste assunto; o que lê de outros artefatos pede ao `Store` por
`__getattr__`, então o `Store` segue sendo a fachada e delega aqui os métodos públicos.
"""
from __future__ import annotations

import gzip
import json
from ipaddress import ip_network
from pathlib import Path
from typing import Optional

from core import layout
from core.common import codigo_valido
from core.cpf import mascarar_cpf_em


class HilbertService:
    def __init__(self, store):
        self._s = store
        # Cache: date_str → {asn: [ixp_code, ...]} from raw ixbr_members.json
        self._member_index: dict[str, dict[int, list[str]]] = {}

    def __getattr__(self, nome):
        if nome == "_s":
            raise AttributeError(nome)
        return getattr(self._s, nome)

    def hilbert_v4(self, date_str: str) -> Optional[dict]:
        """Mapas de densidade /16 para o mapa de Hilbert IPv4."""
        return self._docs.hilbert_v4(date_str)

    def hilbert_v6(self, date_str: str) -> Optional[dict]:
        """Índices esparsos de /32 por bloco RIR para o mapa de Hilbert IPv6."""
        return self._docs.hilbert_v6(date_str)

    def hilbert_v4_detail(self, date_str: str, slash8: int, layer: str) -> Optional[dict]:
        """Blocos /24 dentro de um /8 para zoom do dashboard (dados globais)."""

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

        norm = self.base / "normalized" / date_str / "summary"

        if layer == "global_all":
            data = self._read_json_gz(norm / "prefix-set-v4.json.gz")
            if data is None:
                return None
            return extract_24s(data if isinstance(data, list) else [])

        if layer == "global_br":
            data = self._read_json_gz(norm / "origin-prefixes-v4.json.gz")
            if data is None:
                return None
            prefixes = [p for ps in (data if isinstance(data, dict) else {}).values() for p in ps]
            return extract_24s(prefixes)

        if layer in ("rir_br", "rir_br_visible"):
            reg = self._read_json_gz(norm / "registro_br.json.gz")
            if reg is None:
                return None
            rir_prefixes = [
                p
                for asn in (reg.get("asns", []) if isinstance(reg, dict) else [])
                for p in asn.get("prefixes_v4", [])
            ]
            if layer == "rir_br":
                return extract_24s(rir_prefixes)
            global_data = self._read_json_gz(norm / "prefix-set-v4.json.gz")
            if global_data is None:
                return extract_24s(rir_prefixes)
            global_24s = extract_24s(global_data if isinstance(global_data, list) else [])
            rir_24s = extract_24s(rir_prefixes)
            result: dict[str, list[int]] = {}
            for b, cs in rir_24s.items():
                g_set = set(global_24s.get(b, []))
                visible = [c for c in cs if c in g_set]
                if visible:
                    result[b] = visible
            return result

        if layer == "ixp_all":
            seen: set[str] = set()
            all_prefixes: list[str] = []
            norm_date = self.base / "normalized" / date_str
            if norm_date.exists():
                for ixp_dir in norm_date.iterdir():
                    if not ixp_dir.is_dir() or ixp_dir.name == "summary":
                        continue
                    pf = ixp_dir / "prefix-set-v4.json.gz"
                    if pf.exists():
                        data = self._read_json_gz(pf)
                        if isinstance(data, list):
                            for p in data:
                                if p not in seen:
                                    seen.add(p)
                                    all_prefixes.append(p)
            return extract_24s(all_prefixes)

        return None

    # -------------------------------------------------------------------------
    # IXP: dados por peer (on-demand, lê arquivos normalizados)
    # -------------------------------------------------------------------------

    def _read_json_gz(self, path: Path) -> Optional[dict | list]:
        try:
            existe = path.exists()
        except OSError:                                # código de IXP vindo da URL com componente > 255 bytes (ENAMETOOLONG): não existe → 404, não 500
            return None
        if existe:                                     # em fluxo: não segura o documento descomprimido duas vezes
            try:
                with gzip.open(path, "rt", encoding="utf-8") as f:
                    return mascarar_cpf_em(json.load(f))           # nomes de titulares (EI/MEI) com CPF
            except Exception:
                return None
        dados = layout.ler_bytes_de_caminho(path)      # snapshot compactado (layout 2): o membro vem do ZIP
        if dados is None:
            return None
        try:
            return json.loads(gzip.decompress(dados))
        except Exception:
            return None

    @staticmethod
    def _space24(prefixes: set) -> int:
        total = 0
        for p in prefixes:
            try:
                net = ip_network(p, strict=False)
                if net.version == 4 and net.prefixlen <= 24:
                    total += 1 << (24 - net.prefixlen)
            except ValueError:
                pass
        return total

    @staticmethod
    def _space48(prefixes: set) -> int:
        total = 0
        for p in prefixes:
            try:
                net = ip_network(p, strict=False)
                if net.version == 6 and net.prefixlen <= 48:
                    total += 1 << (48 - net.prefixlen)
            except ValueError:
                pass
        return total

    @staticmethod
    def _prefixes_to_density16(prefixes) -> list[int]:
        """Converte lista de prefixos IPv4 em array de densidade /16 (65536 inteiros)."""
        density = [0] * 65536
        for p in prefixes:
            try:
                net = ip_network(p, strict=False)
                if net.version != 4:
                    continue
                addr_int = int(net.network_address)
                a = (addr_int >> 24) & 0xFF
                b = (addr_int >> 16) & 0xFF
                plen = net.prefixlen
                if plen <= 16:
                    num16 = 1 << (16 - plen)
                    base = a * 256 + b
                    for i in range(num16):
                        idx = base + i
                        if 0 <= idx < 65536:
                            density[idx] = min(256, density[idx] + 256)
                elif plen <= 24:
                    idx = a * 256 + b
                    if 0 <= idx < 65536:
                        density[idx] = min(256, density[idx] + (1 << (24 - plen)))
            except ValueError:
                pass
        return density

    def _norm_dir(self, date_str: str, code: str) -> Path:
        if not codigo_valido(code):                                  # o código vira nome de pasta
            return self.base / "normalized" / "_codigo_invalido"      # caminho que não existe
        return self.base / "normalized" / date_str / code

    def ixp_origin_paths(self, date_str: str, code: str, afi: str) -> dict[int, list[tuple]]:
        """
        Returns {origin_asn: [(path_tuple, count), ...]} sorted by count descending.
        path_tuple = intermediary ASNs between origin and IXP, in origin→IXP order.
        Cached per (date, code, afi).
        """
        key = f"{date_str}/{code}/{afi}"
        try:
            return self._origin_paths[key]
        except KeyError:
            pass

        path = self._norm_dir(date_str, code) / f"routes-{afi}.json.gz"
        data = self._read_json_gz(path)
        index: dict[int, dict[tuple, int]] = {}

        if data:
            for route in data.get("routes", []):
                aspath = route.get("aspath", [])
                if not aspath:
                    continue
                # Deduplicate consecutive prepends
                deduped: list[int] = []
                for a in aspath:
                    if not deduped or deduped[-1] != a:
                        deduped.append(a)
                if not deduped:
                    continue
                origin = deduped[-1]
                # Path from origin outward to IXP direct peer (origin excluded)
                intermediaries = tuple(reversed(deduped[:-1]))
                if intermediaries:
                    index.setdefault(origin, {})
                    index[origin][intermediaries] = index[origin].get(intermediaries, 0) + 1

        result: dict[int, list[tuple]] = {
            asn: sorted(paths.items(), key=lambda kv: -kv[1])
            for asn, paths in index.items()
        }
        self._origin_paths[key] = result
        return result

    def asn_member_ixps(self, date_str: str, asn: int) -> list[str]:
        """IXP codes where this ASN is a registered IX.br member. Cached per date."""
        if date_str not in self._member_index:
            index: dict[int, list[str]] = {}
            raw_date = self.base / "raw" / date_str
            if raw_date.exists():
                for ixp_dir in raw_date.iterdir():
                    if not ixp_dir.is_dir():
                        continue
                    members_file = ixp_dir / "ixbr_members.json"
                    if not members_file.exists():
                        continue
                    try:
                        data = json.loads(members_file.read_bytes())
                        code = ixp_dir.name
                        for m in data.get("members", []):
                            member_asn = m.get("asn")
                            if member_asn:
                                index.setdefault(member_asn, []).append(code)
                    except Exception:
                        pass
            self._member_index[date_str] = index
        return self._member_index[date_str].get(asn, [])
