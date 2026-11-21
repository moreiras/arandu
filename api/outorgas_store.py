# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Leitura das outorgas da Anatel publicadas: uma implementação para SCM, SMP, STFC e SeAC.

Antes o `Store` tinha quatro cópias de ~85 linhas (`scm_*`, `smp_*`, `stfc_*`, `seac_*`: lógica idêntica, só mudava o arquivo
e o nome da lista). `OutorgasPublicadas` guarda o cache de um serviço; `instalar()` devolve ao `Store` os mesmos métodos públicos
de sempre (`scm_index`, `smp_for_cnpj`, `stfc_asn_set`, `seac_geo_map`…), então rotas, MCP e testes não mudam.
"""
from __future__ import annotations

import gzip
import json
import logging
from pathlib import Path
from typing import Callable, Optional

from api.repos.base import ArtifactRepo
from core.outorgas import SERVICOS as _REGISTRO

_log = logging.getLogger("arandurape")

# Campos de contato das outorgas — NUNCA servidos em lote, apenas por AS (endpoint protegido).
CONTACT_FIELDS = ("telefone", "email")

# sigla → (nome da lista no JSON publicado, arquivo do mapa em maps/): vem do registro único (core/outorgas.py)
SERVICOS: dict[str, tuple[str, str]] = {sigla: (s.chave, s.mapa) for sigla, s in _REGISTRO.items()}


def strip_contacts(rec: dict) -> dict:
    """Cópia de um registro sem os campos de contato (não muta o cache)."""
    return {k: v for k, v in rec.items() if k not in CONTACT_FIELDS}


class OutorgasPublicadas(ArtifactRepo):
    """`OutorgaRepo`: outorgas de um serviço lidas de `published/{data}/<sigla>.json.gz` e `maps/<sigla>s.geojson`, com cache por data
    (a leitura e a invalidação vêm do `ArtifactRepo`)."""

    def __init__(self, pub: Callable[[str], Path], sigla: str):
        super().__init__(pub)
        self.sigla = sigla
        self.chave, self.mapa = _REGISTRO[sigla].chave, _REGISTRO[sigla].mapa
        self._asn_set: dict[str, frozenset[int]] = {}
        self._geo: dict[str, Optional[dict]] = {}

    def load(self, date_str: str) -> Optional[dict]:
        """Carrega <sigla>.json.gz do snapshot. None se não disponível."""
        return self.ler(date_str, f"{self.sigla}.json.gz")

    def index(self, date_str: str) -> list[dict]:
        """Todas as outorgas do snapshot, SEM contatos. [] se indisponível.

        Caminho de consumo em lote (REST, MCP list/query). Contatos (telefone/email) só são servidos por AS via `for_asn`.
        """
        data = self.load(date_str)
        return [strip_contacts(r) for r in data.get(self.chave, [])] if data else []

    def for_cnpj(self, date_str: str, cnpj: str) -> list[dict]:
        """Outorgas de um CNPJ (14 dígitos), SEM contatos."""
        data = self.load(date_str)
        if not data:
            return []
        return [strip_contacts(r) for r in data.get("by_cnpj", {}).get(cnpj, [])]

    def for_cnpj_with_contacts(self, date_str: str, cnpj: str) -> list[dict]:
        """Outorgas de um CNPJ, COM telefone/email. Só para o endpoint protegido de contatos — nunca em rota pública."""
        data = self.load(date_str)
        if not data:
            return []
        return list(data.get("by_cnpj", {}).get(cnpj, []))

    def for_asn(self, date_str: str, asn: int) -> list[dict]:
        """Outorgas associadas a um ASN via cruzamento de CNPJ (`cnpj_to_asns` do snapshot).

        **Mantém os campos de contato** (telefone/email): único caminho per-AS, usado apenas pelo endpoint protegido de contatos.
        """
        data = self.load(date_str)
        if not data:
            return []
        by_cnpj = data.get("by_cnpj", {})
        results: list[dict] = []
        for cnpj, asns in data.get("cnpj_to_asns", {}).items():
            if asn in asns:
                results.extend(by_cnpj.get(cnpj, []))
        return results

    def asn_set(self, date_str: str) -> frozenset[int]:
        """ASNs cujo CNPJ possui ao menos uma outorga do serviço. Cacheado.

        ``cnpj_to_asns`` vem de geo_orgs (TODOS os AS BR com CNPJ): restringe-se aos CNPJs com outorga (``by_cnpj``).
        """
        key = f"{date_str}/{self.sigla}_asn_set"
        cached = self._asn_set.get(key)
        if cached is not None:
            return cached
        data = self.load(date_str)
        asns: set[int] = set()
        if data:
            licensed = data.get("by_cnpj", {})
            for cnpj, asn_list in data.get("cnpj_to_asns", {}).items():
                if cnpj in licensed:
                    asns.update(asn_list)
        result = frozenset(asns)
        self._asn_set[key] = result
        return result

    def geo_map(self, date_str: str) -> Optional[dict]:
        """Carrega (e cacheia) maps/<sigla>s.geojson. None se não disponível."""
        key = f"{date_str}/{self.sigla}_geo"
        if key not in self._geo:
            path = self._pub(date_str) / "maps" / self.mapa
            if not path.exists():
                self._geo[key] = None
            else:
                try:
                    self._geo[key] = json.loads(path.read_bytes())
                except Exception:
                    _log.warning("failed to load %s for %s", self.mapa, date_str)
                    self._geo[key] = None
        return self._geo[key]


_METODOS = ("index", "for_cnpj", "for_cnpj_with_contacts", "for_asn", "asn_set", "geo_map")
_PRIVADOS = {"_load_{sigla}": "load"}      # o resto do Store lê os dados completos por aqui


def instalar(cls) -> None:
    """Dá à classe `cls` (o `Store`) os métodos públicos `<sigla>_<método>` que delegam ao `OutorgasPublicadas` do serviço.

    A classe precisa ter `self._outorgas: dict[str, OutorgasPublicadas]` (ver `criar_todas`)."""
    for sigla in SERVICOS:
        for nome in _METODOS:
            def metodo(self, *args, _s=sigla, _n=nome):
                return getattr(self._outorgas[_s], _n)(*args)

            metodo.__name__ = metodo.__qualname__ = f"{sigla}_{nome}"
            metodo.__doc__ = getattr(OutorgasPublicadas, nome).__doc__
            setattr(cls, f"{sigla}_{nome}", metodo)
        for modelo, nome in _PRIVADOS.items():
            def privado(self, *args, _s=sigla, _n=nome):
                return getattr(self._outorgas[_s], _n)(*args)

            privado.__name__ = privado.__qualname__ = modelo.format(sigla=sigla)
            privado.__doc__ = getattr(OutorgasPublicadas, nome).__doc__
            setattr(cls, modelo.format(sigla=sigla), privado)


def criar_todas(pub: Callable[[str], Path]) -> dict[str, OutorgasPublicadas]:
    return {sigla: OutorgasPublicadas(pub, sigla) for sigla in SERVICOS}
