# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Mercado de IPv4 publicado: `ipv4/{transferencias,mercado,recuperacao,blocos_br}.json.gz` e os eventos do `delegated` em `data/ipv4/eventos/` (derivado, só leitura)."""
from __future__ import annotations

import gzip
import ipaddress
import json
from pathlib import Path
from typing import Callable, Optional

from api.repos.base import ArtifactRepo


class Ipv4Repo(ArtifactRepo):
    def __init__(self, pub: Callable[[str], Path], base: Path):
        super().__init__(pub)
        self._eventos_dir = Path(base) / "ipv4" / "eventos"
        self._eventos: Optional[list[dict]] = None
        self._mtime: Optional[float] = None

    def transferencias_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "ipv4/transferencias.json.gz")

    def mercado_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "ipv4/mercado.json.gz")

    def recuperacao_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "ipv4/recuperacao.json.gz")

    def blocos_br_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "ipv4/blocos_br.json.gz")

    def espaco_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "ipv4/ips_sem_uso.json.gz")

    def uso_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "ipv4/uso_por_terceiros.json.gz")

    def subasig_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "ipv4/subasignacoes.json.gz")

    def eventos_br(self) -> list[dict]:
        """Eventos do `delegated` que envolvem o Brasil (país de um dos lados), do mais recente ao mais antigo, com o intervalo de endereços já em inteiros (`_i0`, `_i1`)."""
        arqs = sorted(self._eventos_dir.glob("*.jsonl.gz")) if self._eventos_dir.exists() else []
        m = max((a.stat().st_mtime for a in arqs), default=0.0)
        if self._eventos is None or m != self._mtime:
            out = []
            for a in arqs:
                for ln in gzip.decompress(a.read_bytes()).decode().splitlines():
                    if not ln:
                        continue
                    e = json.loads(ln)
                    if (e.get("de") or {}).get("cc") == "BR" or (e.get("para") or {}).get("cc") == "BR":
                        i0 = int(ipaddress.IPv4Address(e["inicio"]))
                        e["_i0"], e["_i1"] = i0, i0 + e["quantidade"] - 1
                        out.append(e)
            out.sort(key=lambda e: (e["data"], e["id"]), reverse=True)
            self._eventos, self._mtime = out, m
        return self._eventos
