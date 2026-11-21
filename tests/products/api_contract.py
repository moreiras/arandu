# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — monta uma requisição válida para cada operação da API sobre o dataset sintético."""
import json
import re

from core.capacidades import carregar_todas
from tests.synth.world import T0, T1

ALLOWED = {"X-Real-IP": "203.0.113.129"}      # IP da allowlist: nunca vê login
ANON = {"X-Real-IP": "203.0.113.9"}         # visitante anônimo


def _primeiro_cnpj(client, cap) -> str:
    lista = next(o for o in cap.operacoes if o.tipo == "lista_outorgas")
    itens = client.get("/api/v1" + lista.caminho, params={"limit": 3}, headers=ALLOWED).json().get("items") or []
    return itens[0]["cnpj"] if itens else "00000000000191"


def discover(client) -> dict:
    """Identificadores reais do dataset (sem número fixo no teste): ASN, PTT, CNPJ, IBGE, grupo, prefixo."""
    h = ALLOWED
    ixps = client.get("/api/v1/ixps", headers=h).json()["ixps"]
    asns = client.get("/api/v1/asns", params={"limit": 100}, headers=h).json()["items"]
    br = [a for a in asns if a.get("is_br")]
    asn = (br or asns)[0]["asn"]
    doc = client.get(f"/api/v1/asns/{asn}", headers=h).json()
    scms = client.get("/api/v1/scms", params={"limit": 5}, headers=h).json()["items"]
    mun = client.get("/api/v1/acessos/municipios", headers=h).json().get("items") or []
    grupos = client.get("/api/v1/grupos", headers=h).json().get("grupos") or []
    ext = client.get("/api/v1/external-ixps", headers=h).json().get("ixps") or []
    mmun = client.get("/api/v1/acessos-movel/municipios", headers=h).json().get("items") or []
    prefixes = client.get("/api/v1/prefixes", params={"limit": 3}, headers=h).json().get("items") or []
    # entidades declaradas (serve/capabilities): o CNPJ de exemplo vem da própria rota de lista; só a ENTRADA nasce da declaração,
    # a saída esperada continua no golden revisado à mão (senão um erro da declaração mudaria rota e contrato juntos)
    declarados = {f"cnpj_{c.entidade}": _primeiro_cnpj(client, c) for c in carregar_todas()}
    rej = (client.get(f"/api/v1/ixps/{ixps[0]['code']}/rejeicoes", headers=h).json().get("rejeicoes") or {}).get("asns") or []      # um ASN com rejeição e política coletadas
    comm = (client.get("/api/v1/communities", params={"limit": 1}, headers=h).json().get("items") or [{}])[0].get("community", "65000:0:64510")
    fac = (client.get("/api/v1/facilities", params={"limit": 1}, headers=h).json().get("items") or [{}])[0].get("id", 9101)
    blq = (client.post("/api/v1/query/bloqueios_asn", json={"limit": 1}, headers=h).json().get("items") or [{}])[0].get("asn", asn)
    expo_asn = next((a["asn"] for a in br if client.get(f"/api/v1/asns/{a['asn']}/exposicao", headers=h).status_code == 200), asn)
    radar_asn = next((a["asn"] for a in br if client.get(f"/api/v1/asns/{a['asn']}/radar", headers=h).status_code == 200), asn)
    cnpj_fin = next((x["cnpj"] for x in scms if client.get(f"/api/v1/financiamento/operadoras/{x['cnpj']}", headers=h).status_code == 200), (scms[0]["cnpj"] if scms else "00000000000191"))
    cnpj_ctr = next((x["cnpj"] for x in scms if client.get(f"/api/v1/contratos/operadoras/{x['cnpj']}", headers=h).json().get("resultado") == "com_resultado"), (scms[0]["cnpj"] if scms else "00000000000191"))
    prefixo = (prefixes[0].get("prefix") if prefixes else (doc.get("global_prefixes_v4") or ["198.51.100.0/24"])[0])
    return {
        **declarados,
        "ip": prefixo.split("/")[0],
        "date": T1,
        "d0": T0,
        "code": ixps[0]["code"],
        "codes": ",".join("ixbr:" + i["code"] for i in ixps[:2]),
        "ext_code": next((str(ext[0][k]) for k in ("code", "ix_id", "id", "pdb_ix_id") if ext and k in ext[0]), "zx"),
        "ibge_movel": str((mmun[0].get("codigo_ibge") or mmun[0].get("ibge")) if mmun else "3550308"),
        "uf": str((mun[0].get("uf") if mun else None) or "SP"),
        "asn": str(asn),
        "asn_politica": str(rej[0]["asn"] if rej else asn),
        "fac_id": str(fac),
        "asn_bloqueios": str(blq),
        "asn_radar": str(radar_asn),
        "asn_exposicao": str(expo_asn),
        "cnpj_financiamento": cnpj_fin,
        "cnpj_contratos": cnpj_ctr,
        "community": comm,
        "asns": ",".join(str(a["asn"]) for a in (br or asns)[:3]),
        "cnpj": (scms[0]["cnpj"] if scms else "00000000000191"),
        "ibge": str((mun[0].get("codigo_ibge") or mun[0].get("ibge")) if mun else "3550308"),
        "grupo_id": str(grupos[0].get("grupo_id") if grupos else "g1"),
        "prefix": prefixo,
        "ibge_contratos": "9900001",        # município do órgão comprador dos contratos sintéticos
        "ibge_qualidade": "9900007",        # município do RQUAL e das reclamações sintéticas
    }


# nomes de parâmetro (de caminho) → chave de `discover`
# o mesmo nome de parâmetro muda de significado conforme a rota
PATH_OVERRIDE = {
    **{"/api/v1" + o.caminho: {"cnpj": f"cnpj_{c.entidade}"} for c in carregar_todas() for o in c.operacoes if o.tipo == "por_cnpj"},
    "/api/v1/external-ixps/{code}": {"code": "ext_code"},
    "/api/v1/acessos-movel/municipio/{ibge}": {"ibge": "ibge_movel"},
    "/api/v1/asns/{asn}/politica": {"asn": "asn_politica"},
    "/api/v1/asns/{asn}/bloqueios": {"asn": "asn_bloqueios"},
    "/api/v1/asns/{asn}/radar": {"asn": "asn_radar"},
    "/api/v1/asns/{asn}/exposicao": {"asn": "asn_exposicao"},
    "/api/v1/financiamento/operadoras/{cnpj}": {"cnpj": "cnpj_financiamento"},
    "/api/v1/contratos/operadoras/{cnpj}": {"cnpj": "cnpj_contratos"},
    "/api/v1/contratos/municipios/{ibge}": {"ibge": "ibge_contratos"},
    "/api/v1/qualidade/municipios/{ibge}": {"ibge": "ibge_qualidade"},
    "/api/v1/reclamacoes/municipios/{ibge}": {"ibge": "ibge_qualidade"},
    "/api/v1/consumidor/municipios/{ibge}": {"ibge": "ibge_qualidade"},
    "/api/v1/ixps/{code}/portas": {"code": "ext_code"},
}

PATH_PARAMS = {"fac_id": "fac_id", "code": "code", "asn": "asn", "n": "asn", "cnpj": "cnpj", "ibge": "ibge", "uf": "uf", "grupo_id": "grupo_id",
               "prefix": "prefix", "date": "date", "date_str": "date", "collection": None}

# consulta obrigatória por rota (os valores de `{x}` vêm de `discover`)
QUERY = {
    "/api/v1/territorio/mapa": {"indicador": "penetracao"},
    "/api/v1/qualidade/mapa": {"servico": "Banda Larga Fixa", "indicador": "IND4"},
    "/api/v1/busca": {"q": "Arandurápolis"},
    "/api/v1/snapshots/diff": {"a": "{d0}", "b": "{date}"},
    "/api/v1/ixps/{code}/hilbert/v4/detail": {"slash8": 200},
    "/api/v1/hilbert/v4/detail": {"slash8": 200},
    "/api/v1/ixp-compare/members": {"ixps": "{codes}"},
    "/api/v1/prefixes/lookup": {"ip": "{ip}"},
    "/api/v1/resolve/place": {"q": "Arandurápolis"},
    "/api/v1/resolve/operator": {"name": "Arandu"},
    "/api/v1/analytics/operators/reach": {"asns": "{asns}"},
    "/api/v1/analytics/ixps/{code}/nearby": {"radius_km": 500},
    "/api/v1/regiao": {"ibges": "{ibge}"},
    "/api/v1/qualidade/prestadoras": {"servico": "Banda Larga Fixa", "indicador": "IND4"},
    "/api/v1/qualidade/serie": {"servico": "Banda Larga Fixa", "indicador": "IND4"},
}
BODY = {
    "/api/v1/query/{collection}": ("asns", {"limit": 3}),
    "/api/v1/map/query": (None, {"filter": {"field": "is_br", "op": "eq", "value": True}}),
}


def request_for(path: str, method: str, ctx: dict):
    """(url, query, json) para a operação, ou levanta KeyError se faltar parâmetro."""
    url = path
    collection = None
    for name in re.findall(r"{([^}:]+)(?::[^}]*)?}", path):
        if name == "collection":
            collection = BODY[path][0]
            url = url.replace("{collection}", collection)
            continue
        key = PATH_OVERRIDE.get(path, {}).get(name) or PATH_PARAMS[name]
        url = re.sub(r"{" + name + r"(:[^}]*)?}", str(ctx[key]), url)
    query = {k: (v.format(**ctx) if isinstance(v, str) else v) for k, v in QUERY.get(path, {}).items()}
    body = BODY[path][1] if path in BODY else None
    if method.upper() == "GET" and path == "/api/v1/query/{collection}":      # o mesmo corpo, na URL
        query["corpo"] = json.dumps(body)
        body = None
    return url, query, body
