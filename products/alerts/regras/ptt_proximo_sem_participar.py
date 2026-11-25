# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""AS com a sede a menos de 80 km de um PTT do IX.br onde não consta como participante. Versão 2 (ASN-E6): só AS com prefixo na tabela global e CNPJ não baixado;
texto só com o fato, sem recomendação de negócio (`core.alerta_ptt_proximo`)."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado
from core.alerta_ptt_proximo import deve_avaliar, detalhe
from core.geo import haversine_km
from products.alerts.auxiliar import GEO_PROXIMITY_KM

REGRA = Regra(id="ptt_proximo_sem_participar", categoria="geo", severidade="aviso", versao=2,
              descricao="PTT do IX.br a <= 80 km da sede sem participação do AS (só AS com prefixo na tabela global e CNPJ não baixado)")


def avaliar(ctx: Contexto) -> list[dict]:
    if not deve_avaliar(ctx.store, ctx.date_str, ctx.asn, ctx.doc):
        return []
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
        detalhe(near, int(GEO_PROXIMITY_KM)),
        {"ixps": near[:10]})]
