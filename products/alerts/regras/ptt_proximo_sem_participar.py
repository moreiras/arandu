# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""AS a menos de 80 km de um PTT do IX.br onde não participa."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado
from core.geo import haversine_km
from products.alerts.auxiliar import GEO_PROXIMITY_KM

REGRA = Regra(id="ptt_proximo_sem_participar", categoria="geo", severidade="aviso", versao=1,
              descricao="PTT do IX.br a <= 80 km sem participação do AS")


def avaliar(ctx: Contexto) -> list[dict]:
    coords = ctx.store.asn_coords(ctx.date_str, ctx.asn)
    if not coords:
        return []
    lat, lon = coords
    member_codes = set(ctx.doc.get("ixp_member_codes") or [])
    member_codes |= set((ctx.doc.get("ixp_presence") or {}).keys())
    pix_cfg = ctx.store._load_pix_config()
    ixp_names = {row.get("code"): row.get("name") for row in ctx.store.ixp_index(ctx.date_str)}
    near = []
    for code, points in pix_cfg.items():
        if code in member_codes:
            continue
        dmin = min(haversine_km(lat, lon, pt["lat"], pt["lon"]) for pt in points)
        if dmin <= GEO_PROXIMITY_KM:
            near.append({"code": code, "name": ixp_names.get(code, code), "dist_km": round(dmin, 1)})
    near.sort(key=lambda x: x["dist_km"])
    if not near:
        return []
    return [achado(
        "PTT próximo sem participação",
        f"O AS está a menos de {int(GEO_PROXIMITY_KM)} km de "
        f"{len(near)} PTT(s) do IX.br onde não participa. Participar "
        "pode reduzir custo de trânsito e latência.",
        {"ixps": near[:10]})]
