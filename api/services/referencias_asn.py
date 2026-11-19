# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Referências de comparação do AS: onde ele fica entre os ASes brasileiros do snapshot (`include=referencias` do perfil).

Só estatística do próprio índice de ASNs (sem dado de pessoa): posição por usuários estimados (APNIC) e medianas de IPv6, prefixos IPv4 e PTTs
diretos entre os ASes BR. Cacheado por snapshot (os arquivos publicados são imutáveis). A mediana é do universo declarado em `universo`."""
from __future__ import annotations

from statistics import median
from typing import Any, Optional

_CACHE: dict[tuple[int, str], dict[str, Any]] = {}
UNIVERSO = "ASes brasileiros com registro no Registro.br"


def _universo(store: Any, date_str: str) -> dict[str, Any]:
    chave = (id(store), date_str)
    if chave not in _CACHE:
        while len(_CACHE) >= 2:
            _CACHE.pop(next(iter(_CACHE)))
        br = [a for a in store.asn_index(date_str) if a.get("is_br")]
        com_usuarios = sorted((a for a in br if (a.get("apnic_users") or 0) > 0), key=lambda a: -(a["apnic_users"]))
        _CACHE[chave] = {
            "total": len(br),
            "posicao": {a["asn"]: i + 1 for i, a in enumerate(com_usuarios)},
            "pct_v6": median([a["pct_v6"] for a in br if a.get("pct_v6") is not None] or [0]) if br else None,
            "prefixos_v4": median([a.get("global_prefixes_v4_count") or 0 for a in br]) if br else None,
            "ixps": median([a.get("ixps_direct_count") or 0 for a in br]) if br else None,
        }
    return _CACHE[chave]


def bloco_referencias(store: Any, date_str: str, asn: int) -> Optional[dict[str, Any]]:
    """Referências do AS, ou None se o snapshot não tem o índice."""
    u = _universo(store, date_str)
    if not u["total"]:
        return None
    return {
        "universo": UNIVERSO,
        "total": u["total"],
        "usuarios_posicao": u["posicao"].get(asn),
        "usuarios_com_dado": len(u["posicao"]),
        "pct_v6_mediana": u["pct_v6"],
        "prefixos_v4_mediana": u["prefixos_v4"],
        "ixps_diretos_mediana": u["ixps"],
    }
