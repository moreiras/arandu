# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Documentos de nível de snapshot de `published/{data}/` lidos inteiros: resumo, manifesto, Hilbert, análise BGP,
estabilidade BGP, CDNs, índices de IXPs, ASNs e IXPs externos, e nomes de ASNs.

Cada acessor é uma leitura com cache por data e ausência = `None` (ou `[]`/`{}` onde o `Store` sempre devolveu isso). As consultas que
cruzam estes documentos com outros ficam nos serviços.
"""
from __future__ import annotations

from typing import Optional

from api.repos.base import ArtifactRepo
from core.chaves_registro import com_os_dois_nomes


class DocumentosRepo(ArtifactRepo):
    # resumo e manifesto saem com os nomes `m3_` e `registro_br_` das contagens do Registro.br (snapshot já publicado só tem o primeiro)
    def summary(self, date_str: str) -> Optional[dict]:
        return com_os_dois_nomes(self.ler(date_str, "summary.json"))

    def manifest(self, date_str: str) -> Optional[dict]:
        return com_os_dois_nomes(self.ler(date_str, "manifest.json"))

    def manifest_em_memoria(self, date_str: str) -> Optional[dict]:
        """O manifesto só se já está em cache (não lê o disco)."""
        return com_os_dois_nomes(self._cache.get((date_str, "manifest.json")))

    def hilbert_v4(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "hilbert_v4.json")

    def hilbert_v6(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "hilbert_v6.json")

    def routing_analysis(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "routing_analysis.json")

    def bgp_stability(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "bgp_stability.json")

    def bgp_stability_em_memoria(self, date_str: str) -> Optional[dict]:
        return self._cache.get((date_str, "bgp_stability.json"))

    def bgp_stability_datas_em_memoria(self) -> set[str]:
        return {d for d, a in self._cache if a == "bgp_stability.json"}

    def soltar_bgp_stability(self, date_str: str) -> None:
        self.invalidar(date_str, "bgp_stability.json")

    def bgp_stability_deep(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "bgp_stability_deep.json")

    def cdns(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "cdns.json")

    def external_ixp_index(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "external-ixps/index.json")

    def ixp_index(self, date_str: str) -> list[dict]:
        data = self.ler(date_str, "ixps/index.json")
        return data if isinstance(data, list) else []

    def asn_index(self, date_str: str) -> list[dict]:
        data = self.ler(date_str, "asns/index.json")
        return data if isinstance(data, list) else []

    def asn_names(self, date_str: str) -> dict[str, str]:
        data = self.ler(date_str, "asns/names.json")
        return data if isinstance(data, dict) else {}
