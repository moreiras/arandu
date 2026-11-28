# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T5 — argumentos válidos para cada tool do MCP sobre o dataset sintético."""

# parâmetros obrigatórios (e os opcionais necessários) → valor, a partir de `ctx` (ver discover)
ARG_FROM_CTX = {
    "asn": lambda c: int(c["asn"]),
    "code": lambda c: c["code"],
    "prefix": lambda c: c["prefix"],
    "asns": lambda c: [int(x) for x in c["asns"].split(",")],
    "cnpj": lambda c: c["cnpj"],
    "ibge": lambda c: c["ibge"],
    "uf": lambda c: c["uf"],
    "slash8": lambda c: 198,
    "collection": lambda c: "asns",
    "place": lambda c: "Arandurápolis",
    "name": lambda c: "Arandu",
}

# tools cujo dado não existe no dataset sintético (a REST também responde 404 nele): o T5 espera "indisponível" e o comportamento real
# é coberto em tests/unit/test_mcp_bgp.py com um Store falso
SEM_DADOS_NO_SINTETICO = {"rota_analise", "rota_estabilidade"}

# parâmetros opcionais que a tool precisa para responder algo útil
EXTRA = {
    "geo_localizar": {"asn"},
    "operadora_acessos": {"cnpj"},
    "historico_acessos": {"cnpj"},
    "municipio_banda_larga": {"ibge"},
    "operadora_grupo": {"cnpj"},
    "rota_prefixo": {"prefix"},
}

def _ponto_sintetico(_ctx):
    from tests.synth.world import MUNICIPIOS
    return {"lat": MUNICIPIOS[0][3], "lon": MUNICIPIOS[0][4], "raio_km": 500}


OVERRIDE = {
    "historico_serie": lambda c: {"escopo": "uf:" + c["uf"]},
    "infra_proximos": _ponto_sintetico,
    "ixp_externo": lambda c: {"code": c["ext_code"]},
    "ixp_participantes": lambda c: {"code": c["code"], "visao": "peers", "afi": "v4"},
    "viz": lambda c: {"kind": "hilbert_v4"},
    "query": lambda c: {"collection": "asns", "limit": 3},
    "asn_politica": lambda c: {"asn": int(c["asn_politica"])},
    "ixp_communities": lambda c: {"community": c["community"]},
    "facility_detalhe": lambda c: {"id": int(c["fac_id"])},
    "ixp_portas": lambda c: {"code": c["ext_code"]},
    "ixp_area_influencia": lambda c: {"code": c["code"]},
    "asn_peering": lambda c: {"asn": int(c["asn"])},
    "asn_bloqueios": lambda c: {"asn": int(c["asn_bloqueios"])},
    "asn_radar": lambda c: {"asn": int(c["asn_radar"])},
    "asn_exposicao": lambda c: {"asn": int(c["asn_exposicao"])},
    "operadora_financiamento": lambda c: {"cnpj": c["cnpj_financiamento"]},
    "operadora_sancoes": lambda c: {"cnpj": c["cnpj_financiamento"]},
    "operadora_contratos": lambda c: {"cnpj": c["cnpj_contratos"]},
    "grupo_perfil": lambda c: {"grupo_id": c["grupo_id"], "blocos": ["mercado", "regulatorio", "tecnico", "relacoes"]},
}


def args_for(tool: str, schema: dict, ctx: dict) -> dict:
    if tool in OVERRIDE:
        return OVERRIDE[tool](ctx)
    wanted = set(schema.get("required", [])) | EXTRA.get(tool, set())
    return {k: ARG_FROM_CTX[k](ctx) for k in wanted}
