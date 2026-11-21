# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`ArtifactRepo`: leitura de um artefato de `published/{data}/` com cache por data.

Regras comuns de leitura, num lugar só:
  * **ausência = `None`**: arquivo inexistente ou ilegível devolve `None` (com aviso no log se ilegível) e o `None` fica em cache;
  * **invalidação**: `invalidar(data)` esquece a data, para o pipeline publicar um artefato num snapshot já servido sem reiniciar a API;
  * leitura `.json.gz` ou `.json` pela extensão;
  * `validar`: gancho de teste — recebe o documento lido e levanta se não bate com o esquema declarado no catálogo.
"""
from __future__ import annotations

import gzip
import json
import logging
from pathlib import Path
from typing import Any, Callable, Optional

from core import layout

_log = logging.getLogger("arandurape")


class ArtifactRepo:
    """Base dos repositórios: `ler(data, arquivo)` com cache. Subclasses expõem as consultas do seu artefato."""

    def __init__(self, pub: Callable[[str], Path], validar: Optional[Callable[[str, Any], None]] = None):
        self._pub = pub
        self._cache: dict[tuple[str, str], Optional[Any]] = {}
        self._validar = validar

    def ler(self, date_str: str, arquivo: str) -> Optional[Any]:
        """Conteúdo de `published/{data}/{arquivo}` ou `None` (ausente ou ilegível). Cacheado, inclusive o `None`."""
        chave = (date_str, arquivo)
        if chave not in self._cache:
            dados = self._ler_do_disco(date_str, arquivo)
            # o `None` só fica guardado se a data existe (artefato ausente num snapshot real);
            # para data inventada (formato válido, sem snapshot) cada pedido viraria uma entrada eterna.
            if dados is None and not (Path(self._pub(date_str)) / "manifest.json").exists():
                return None
            self._cache[chave] = dados
        return self._cache[chave]

    def _ler_do_disco(self, date_str: str, arquivo: str) -> Optional[Any]:
        pub = self._pub(date_str)
        path = layout.caminho(pub, arquivo)                          # os dois formatos do snapshot (core/layout.py)
        dados = None if path is not None else layout.ler_bytes(pub, arquivo)     # só o que está no ZIP vem em bytes
        if path is None and dados is None:
            return None
        try:
            if path is not None and arquivo.endswith(".gz"):
                with gzip.open(path, "rt", encoding="utf-8") as f:       # em fluxo: não segura o documento descomprimido duas vezes
                    doc = json.load(f)
            elif path is not None:
                doc = json.loads(path.read_text(encoding="utf-8"))
            else:
                doc = json.loads(gzip.decompress(dados) if arquivo.endswith(".gz") else dados)
        except Exception:
            _log.warning("failed to load %s for %s", arquivo, date_str)
            return None
        if self._validar is not None:
            self._validar(arquivo, doc)
        return doc

    def invalidar(self, date_str: str, arquivo: Optional[str] = None) -> None:
        """Esquece a data (ou só um arquivo dela): a próxima leitura vai ao disco, inclusive se antes era `None`."""
        for chave in [k for k in self._cache if k[0] == date_str and (arquivo is None or k[1] == arquivo)]:
            del self._cache[chave]
