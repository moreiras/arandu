# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Leitura preguiçosa de um snapshot para o gerador de eventos: linhas do histórico, documentos de ASN,
conjuntos de outorgas e estado da coleta. Só lê (`published/` é imutável)."""
from __future__ import annotations

import gzip
import json
from functools import cached_property
from pathlib import Path
from typing import Optional

from core import layout
from core.common import published_path, read_json_gz

SERVICOS = ("scm", "smp", "stfc", "seac")


class Snap:
    def __init__(self, base: Path, date: str):
        self.base = base
        self.date = date
        self.pub = published_path(base, date)

    @cached_property
    def manifesto(self) -> dict:
        p = self.pub / "manifest.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    @property
    def rules_version(self) -> Optional[str]:
        return self.manifesto.get("rules_version")

    @property
    def parcial(self) -> bool:
        """Coleta incompleta: o que sumiu pode ser falha de coleta, então nada negativo se conclui deste snapshot."""
        m = self.manifesto
        return m.get("coleta") == "parcial" or m.get("coleta_ok") is False

    @cached_property
    def linhas(self) -> dict[int, dict]:
        """{asn: linha} do histórico deste snapshot (weekly/{date}/asn.jsonl.gz)."""
        p = self.base / "history" / "weekly" / self.date / "asn.jsonl.gz"
        if not p.exists():
            return {}
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return {ln["asn"]: ln for ln in (json.loads(x) for x in f if x.strip())}

    @cached_property
    def ptts_ok(self) -> set[str]:
        """PTTs coletados por inteiro (status ok) neste snapshot."""
        p = self.base / "history" / "weekly" / self.date / "ixp.jsonl.gz"
        if not p.exists():
            return set()
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return {ln["ixp"] for ln in (json.loads(x) for x in f if x.strip()) if ln.get("status") == "ok"}

    def doc(self, asn: int) -> Optional[dict]:
        """Documento publicado do ASN, nos dois formatos do snapshot (`asns/` ou, depois da compactação, `asns.zip`)."""
        b = layout.ler_bytes(self.pub, f"asns/{asn}.json")
        return json.loads(b) if b is not None else None

    @cached_property
    def outorgas(self) -> dict[str, set[str]]:
        """{serviço: CNPJs com outorga} (scm, smp, stfc, seac); serviço sem arquivo fica ausente."""
        out: dict[str, set[str]] = {}
        for sv in SERVICOS:
            p = self.pub / f"{sv}.json.gz"
            if p.exists():
                d = read_json_gz(p)
                out[sv] = set(d.get("by_cnpj") or {}) or {x["cnpj"] for x in d.get(f"{sv}s") or [] if x.get("cnpj")}
        return out

    def detentores(self, prefixos: set[str]) -> dict[str, set[int]]:
        """{prefixo: ASNs que o originam} para os prefixos pedidos; varre os documentos com prefixos (sem custo se `prefixos` é vazio)."""
        achados: dict[str, set[int]] = {p: set() for p in prefixos}
        if not prefixos:
            return achados
        for asn, ln in self.linhas.items():
            if not (ln.get("p4") or ln.get("p6")):
                continue
            d = self.doc(asn)
            if not d:
                continue
            for p in set(d.get("global_prefixes_v4") or []) | set(d.get("global_prefixes_v6") or []):
                if p in achados:
                    achados[p].add(asn)
        return achados
