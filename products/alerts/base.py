# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Contrato das regras de alerta.

Cada regra é um arquivo em `products/alerts/regras/` com `REGRA` (identidade e versão) e `avaliar(ctx)`, que devolve a lista de achados
(`achado(...)`); o registro monta o alerta final `{id, category, severity, title, detail, refs}` — as chaves, e a ordem, são as de
sempre (API, MCP e frontend leem esse formato).

`versao` sobe quando a regra muda de SEMÂNTICA (limiar, fonte, texto que muda o sentido): séries de alertas só são comparáveis entre
snapshots de mesma versão da regra. `ctx.store` é o acesso aos índices do snapshot (a `Store` da API, por duck typing: esta camada não
importa `api`).
"""
from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

SEVERIDADES = ("critico", "aviso", "info")
CATEGORIAS = ("roteamento", "rpki", "v4v6", "presenca", "geo")


@dataclass(frozen=True)
class Regra:
    id: str                                  # família da regra (arquivo); o alerta pode ter id derivado (ex.: desagregacao_ipv4)
    categoria: str
    severidade: str
    versao: int
    descricao: str
    avaliar: Optional[Callable[["Contexto"], list[dict]]] = None


@dataclass
class Contexto:
    """O que uma regra enxerga: o documento do ASN (já com RPKI e `ixp_member_codes`) e o acesso ao snapshot."""
    store: Any
    date_str: str
    asn: int
    doc: dict
    memo: dict = field(default_factory=dict)             # cálculos compartilhados entre regras (evita refazer)

    @property
    def rir_v4(self) -> list:
        return self.doc.get("rir_prefixes_v4") or []

    @property
    def rir_v6(self) -> list:
        return self.doc.get("rir_prefixes_v6") or []

    @property
    def glob_v4(self) -> list:
        return self.doc.get("global_prefixes_v4") or []

    @property
    def glob_v6(self) -> list:
        return self.doc.get("global_prefixes_v6") or []

    @property
    def has_alloc(self) -> bool:
        return bool(self.rir_v4 or self.rir_v6)


def achado(titulo: str, detalhe: str, refs: Optional[dict] = None, id: Optional[str] = None) -> dict:
    """Um achado da regra; `id` só quando difere do id da regra (famílias por AFI)."""
    return {"id": id, "title": titulo, "detail": detalhe, "refs": refs or {}}


def net(prefix: str) -> Optional[ipaddress._BaseNetwork]:
    try:
        return ipaddress.ip_network(prefix, strict=False)
    except (ValueError, TypeError):
        return None


def nets(prefixes) -> list:
    out = []
    for p in prefixes or []:
        n = net(p)
        if n is not None:
            out.append(n)
    return out
