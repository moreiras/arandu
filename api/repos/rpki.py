# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""RPKI de `published/{data}/rpki/`: VRPs (ROAs) e objetos ASPA, indexados em memória por data.

Não herda `ArtifactRepo`: guarda só os índices (não o documento lido) e **não** cacheia a ausência do VRP, porque o coletor RPKI roda
depois do pipeline e o arquivo pode aparecer com a API no ar.
"""
from __future__ import annotations

import gzip
import json
from ipaddress import ip_network
from pathlib import Path
from typing import Callable, Optional


class RpkiRepo:
    def __init__(self, pub: Callable[[str], Path]):
        self._pub = pub
        self._vrp_cache: dict[str, Optional[dict]] = {}
        self._aspa_cache: dict[str, Optional[dict]] = {}

    @staticmethod
    def _read_json_gz(path: Path):
        if not path.exists():
            return None
        try:
            with gzip.open(path, "rt", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return None

    def vrps(self, date_str: str) -> Optional[dict]:
        """Load and index VRP list for the given snapshot date. Cached per date.

        Builds two lookup structures per AFI:
          - by_asn: {asn: [{prefix, maxLength, ta}, ...]}  (for roa_list queries)
          - by_prefix: {(prefixlen, net_int): [(asn, maxlen, ta), ...]}  (O(1) RPKI validation)
        """
        if date_str in self._vrp_cache:
            return self._vrp_cache[date_str]

        path = self._pub(date_str) / "rpki" / "vrp_list.json.gz"
        data = self._read_json_gz(path)
        if not data:
            # Don't cache absence — file may appear later (collector runs after pipeline)
            return None

        try:
            roas_raw = data if isinstance(data, list) else data.get("vrps") or data.get("roas") or []
            by_asn: dict[int, list[dict]] = {}
            # Hash map: (prefixlen, net_int) → [(asn, maxlen, ta)] — O(1) lookup per covering check
            v4_by_prefix: dict[tuple, list[tuple]] = {}
            v6_by_prefix: dict[tuple, list[tuple]] = {}

            for roa in roas_raw:
                asn_raw = roa.get("asn", 0)
                try:
                    asn = int(str(asn_raw).removeprefix("AS"))
                except (ValueError, AttributeError):
                    continue
                prefix = roa.get("prefix", "")
                max_len = int(roa.get("maxLength") or roa.get("max_length") or 0)
                ta = roa.get("ta", "")
                if not prefix:
                    continue
                try:
                    net = ip_network(prefix, strict=False)
                except ValueError:
                    continue

                entry = {"asn": asn, "prefix": prefix, "maxLength": max_len, "ta": ta}
                by_asn.setdefault(asn, []).append(entry)

                key = (net.prefixlen, int(net.network_address))
                if net.version == 4:
                    v4_by_prefix.setdefault(key, []).append((asn, max_len, ta))
                else:
                    v6_by_prefix.setdefault(key, []).append((asn, max_len, ta))

            result = {
                "by_asn": by_asn,
                "v4_by_prefix": v4_by_prefix,
                "v6_by_prefix": v6_by_prefix,
            }
            self._vrp_cache[date_str] = result
            return result
        except Exception:
            self._vrp_cache[date_str] = None
            return None

    def vrps_do_asn(self, date_str: str, asn: int) -> list[dict]:
        """Returns all ROAs authorizing this ASN. Each dict: {prefix, maxLength, ta}."""
        data = self.vrps(date_str)
        if data is None:
            return []
        return list(data["by_asn"].get(asn, []))

    @staticmethod
    def _cobrem(data: dict, net) -> list[tuple[int, int, int, str]]:
        """VRPs que cobrem `net` (de qualquer AS): [(tamanho do VRP, asn, maxLength, ta)], do menos ao mais específico."""
        p_int = int(net.network_address)
        bits = net.max_prefixlen
        by_prefix = data["v4_by_prefix"] if net.version == 4 else data["v6_by_prefix"]
        covering: list[tuple[int, int, int, str]] = []
        for vrp_len in range(0, net.prefixlen + 1):
            p_masked = 0 if vrp_len == 0 else (p_int >> (bits - vrp_len)) << (bits - vrp_len)
            for asn, max_len, ta in by_prefix.get((vrp_len, p_masked)) or ():
                covering.append((vrp_len, asn, max_len, ta))
        return covering

    def validar_prefixos(self, date_str: str, asn: int, prefixes: list[str]) -> dict[str, str]:
        """
        Validates each prefix against RPKI (RFC 6811).
        Returns {prefix: 'valid'|'invalid'|'not_found'}.

        Uses hash-map lookup O(prefix_len) per prefix instead of O(prefix_len × vrps_per_len).
        """
        data = self.vrps(date_str)
        if data is None:
            return {}
        result: dict[str, str] = {}
        for prefix_str in prefixes:
            try:
                net = ip_network(prefix_str, strict=False)
            except ValueError:
                continue
            covering = self._cobrem(data, net)
            if not covering:
                result[prefix_str] = "not_found"
            elif any(va == asn and net.prefixlen <= vm for _, va, vm, _ in covering):
                result[prefix_str] = "valid"
            else:
                result[prefix_str] = "invalid"
        return result

    def diagnosticar(self, date_str: str, prefix: str, asn: Optional[int]) -> Optional[dict]:
        """Validação de origem (RFC 6811) de UM par prefixo/AS, com os VRPs de qualquer AS que cobrem o prefixo e o motivo.

        `asn` None (prefixo sem anúncio observado) não valida nada: `estado` sai `nao_avaliado`, mas os VRPs que cobrem o prefixo
        são listados, com `autoriza_origem` nulo. Devolve None se o snapshot não tem VRPs."""
        data = self.vrps(date_str)
        if data is None:
            return None
        net = ip_network(prefix, strict=False)
        covering = self._cobrem(data, net)
        roas = [{"prefix": str(type(net)((int(net.network_address) >> (net.max_prefixlen - tam) << (net.max_prefixlen - tam), tam))),
                 "asn": va, "maxLength": vm, "ta": ta,
                 "autoriza_origem": None if asn is None else (va == asn and net.prefixlen <= vm)}
                for tam, va, vm, ta in covering]
        if asn is None:
            estado, motivo = "nao_avaliado", "sem_anuncio"
        elif not covering:
            estado, motivo = "not_found", "sem_roa"
        elif any(r["autoriza_origem"] for r in roas):
            estado, motivo = "valid", None
        elif any(r["asn"] == asn for r in roas):
            estado, motivo = "invalid", "maxlength_excedido"
        else:
            estado, motivo = "invalid", "origem_diferente"
        return {"estado": estado, "motivo": motivo, "asn": asn, "roas_que_cobrem": roas}

    def aspas(self, date_str: str) -> Optional[dict]:
        """Carrega e indexa a lista de objetos ASPA para o snapshot. Cacheado por data.

        Constrói dois índices:
          - by_customer: {customer_asn: [{providers, tal}, ...]}
          - by_provider: {provider_asn: [{customer, tal}, ...]}
        """
        if date_str in self._aspa_cache:
            return self._aspa_cache[date_str]

        path = self._pub(date_str) / "rpki" / "aspa_list.json.gz"
        data = self._read_json_gz(path)
        if not data:
            return None

        try:
            aspas_raw = data if isinstance(data, list) else []
            by_customer: dict[int, list[dict]] = {}
            by_provider: dict[int, list[dict]] = {}

            for aspa in aspas_raw:
                customer = aspa.get("customer")
                providers = aspa.get("providers") or []
                tal = aspa.get("tal", "")
                if not isinstance(customer, int):
                    continue
                by_customer.setdefault(customer, []).append(
                    {"providers": providers, "tal": tal}
                )
                for provider_asn in providers:
                    if isinstance(provider_asn, int):
                        by_provider.setdefault(provider_asn, []).append(
                            {"customer": customer, "tal": tal}
                        )

            result = {"by_customer": by_customer, "by_provider": by_provider}
            self._aspa_cache[date_str] = result
            return result
        except Exception:
            self._aspa_cache[date_str] = None
            return None

    def como_customer(self, date_str: str, asn: int) -> list[dict]:
        """Objetos ASPA publicados por este AS (como customer). Cada dict: {providers, tal}."""
        data = self.aspas(date_str)
        if data is None:
            return []
        return list(data["by_customer"].get(asn, []))

    def como_provider(self, date_str: str, asn: int) -> list[dict]:
        """Objetos ASPA de outros ASes que listam este AS como provider. Cada dict: {customer, tal}."""
        data = self.aspas(date_str)
        if data is None:
            return []
        return list(data["by_provider"].get(asn, []))
