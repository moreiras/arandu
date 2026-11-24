# SPDX-License-Identifier: AGPL-3.0-or-later
"""Camada geográfica/infraestrutura do dataset sintético: fundo (ITU, cabos, linhas, rodovias), IXP externo, prefixos globais."""
from __future__ import annotations

from tests.synth.world import MUNICIPIOS, PTTS, World

MUN = {m[1]: m for m in MUNICIPIOS}
EXTERNAL_IXP = {"code": "zx", "name": "IX Externo Fictício", "city": "Cidade Exemplo", "country": "UY", "pdb_ix_id": 99001}


def itu() -> dict:
    a, b, c = MUN["Arandurápolis"], MUN["Tupãnópolis"], MUN["Guaraniópolis"]
    feats = [
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[a[4], a[3]], [b[4], b[3]]]},
         "properties": {"type_inf": "Fibre Operational", "status": "Operational"}},
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[a[4], a[3]], [c[4], c[3]]]},
         "properties": {"type_inf": "Fibre Planned", "status": "Planned"}},
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[b[4], b[3]], [-43.0, -22.0]]},
         "properties": {"type_inf": "Microwave Operational", "status": "Operational"}},
    ]
    return {"snapshot_date": "", "source": "sintético", "total": 3,
            "status_counts": {"Operational": 2, "Planned": 1}, "features": feats}


def cables() -> dict:
    return {"snapshot_date": "", "source": "sintético", "cables": [
        {"id": "cabo-exemplo-1", "name": "Cabo Exemplo Atlântico", "color": "#336699",
         "geometry": {"type": "MultiLineString", "coordinates": [[[-46.4, -24.0], [-30.0, -20.0], [-10.0, 10.0]]]},
         "length": "6,000 km", "owners": "Consórcio Fictício", "suppliers": "Fornecedor Fictício", "rfs_year": 2024,
         "is_planned": False, "url": "", "landing_countries": ["Brazil", "Portugal"]}],
        "landing_points": [{"id": "ponto-exemplo-1", "name": "Praia Exemplo, Brazil", "is_tbd": False,
                            "geometry": {"type": "Point", "coordinates": [-46.4, -24.0]}}]}


def aneel() -> dict:
    a, d = MUN["Arandurápolis"], MUN["Itapuãzinho"]
    feats = [{"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[a[4], a[3]], [d[4], d[3]]]},
              "properties": {"name": "Linha LT 230 kV ARANDURA / ITAPUA C 1 SP", "subestacao_origem": "ARANDURA",
                             "subestacao_destino": "ITAPUA", "uf": "SP", "tensao_kv": 230.0, "extensao_km": 85.2}}]
    return {"snapshot_date": "", "source": "sintético", "total": 1, "features": feats}


def rodovias() -> dict:
    a, d = MUN["Arandurápolis"], MUN["Itapuãzinho"]
    props = {"tipo_via": "Rodovia", "jurisdicao": "Federal", "administracao": "Federal", "concessionaria": None,
             "revestimento": "Pavimentado", "operacional": "Sim", "situacao": "Construída", "trafego": "Permanente",
             "sigla": "BR-999", "codigo_trecho": "999BSP0010", "nr_pistas": 2, "nr_faixas": 4, "limite_velocidade_kmh": 100,
             "pavimentada": True}
    return {"snapshot_date": "", "source": "sintético", "total": 1, "features": [
        {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[a[4], a[3]], [d[4], d[3]]]}, "properties": props}]}


def peeringdb_external(world: World) -> dict:
    br = [a for a in world.ases.values() if a.is_br and a.role == "access"][:3]
    fo = [a for a in world.ases.values() if a.role == "foreign"][:2]
    members = [{"asn": a.asn, "name": a.name, "speed": 10000} for a in br + fo]
    members.append({"asn": br[0].asn, "name": br[0].name, "speed": 100000})          # segunda porta da mesma rede (IXE-E1: conta rede, não porta)
    per_asn = {str(m["asn"]): {"external": [EXTERNAL_IXP["code"]], "ixbr": [c for c, _, _ in PTTS if m["asn"] in world.members[c]]}
               for m in members}
    return {"external_ixps": {EXTERNAL_IXP["code"]: {**{k: EXTERNAL_IXP[k] for k in ("name", "city", "country", "pdb_ix_id")},
                                                    "member_count": len(members), "members": members}},
            "per_asn": per_asn}


def global_prefixes(world: World) -> dict:
    mun = {m[0]: m for m in MUNICIPIOS}
    prefixes = {}
    for code in world.routes:
        for p, path in world.routes[code]:
            e = prefixes.setdefault(p, {"ixps_seen": set(), "origin_asn": path[-1], "ip_version": 6 if ":" in p else 4})
            e["ixps_seen"].add(code)
    out = {}
    for p, e in prefixes.items():
        a = world.ases[e["origin_asn"]]
        if a.is_br:
            m = mun[a.municipio_ibge]
            geo = {"lat": m[3], "lon": m[4], "city": m[1], "country": "BR", "uf": m[2], "geo_confidence": "city_centroid"}
        else:
            geo = {"lat": 40.0, "lon": -74.0, "city": "Nova Exemplo", "country": a.cc, "uf": "", "geo_confidence": "city_centroid"}
        out[p] = {"ixps_seen": sorted(e["ixps_seen"]), "origin_asn": e["origin_asn"], "ip_version": e["ip_version"],
                  "geo_source": "geolite2-2026-09", **geo}
    return {"snapshot_date": world.instant, "mmdb_month": "2026-09", "geo_source": "geolite2-2026-09",
            "total": len(out), "geolocated": len(out), "unknown": 0, "prefixes": out}


def peeringdb_fac(world: World, registrados: list[int], d: str) -> dict:
    """PeeringDB `fac`/`netfac`/`ixfac`/`carrier`/`campus`/`net` sintéticos, já no formato normalizado do coletor (sem nenhum contato).
    Três instalações no Brasil (recente, parada e antiga pelas datas), uma no Uruguai que abriga o PTT externo fictício, dois carriers, um campus e os atributos das redes registradas."""
    a, b, c = MUN["Arandurápolis"], MUN["Tupãnópolis"], MUN["Guaraniópolis"]
    facilities = {
        "9101": {"id": 9101, "nome": "Datacenter Exemplo SP-1", "org_id": 7001, "org_nome": "Operadora Fictícia S.A.", "campus_id": 7, "site": "https://dc1.example.org", "propriedade": "Owner",
                 "redes_declaradas": 6, "ixps_declarados": 2, "carriers_declarados": 2, "criado": "2012-03-01T00:00:00Z", "atualizado": "2026-08-20T12:00:00Z",
                 "cidade": a[1], "uf": a[2], "pais": "BR", "lat": a[3], "lon": a[4]},
        "9102": {"id": 9102, "nome": "Colo Exemplo RJ", "org_id": 7002, "org_nome": "Colo Fictícia Ltda", "redes_declaradas": 2, "ixps_declarados": 1, "carriers_declarados": 1,
                 "criado": "2015-05-05T00:00:00Z", "atualizado": "2024-03-10T00:00:00Z", "cidade": b[1], "uf": b[2], "pais": "BR", "lat": b[3], "lon": b[4]},
        "9103": {"id": 9103, "nome": "Sala Cofre Exemplo PR", "org_id": 7003, "org_nome": "Sala Fictícia ME", "redes_declaradas": 0, "ixps_declarados": 1, "carriers_declarados": 0,
                 "criado": "2016-01-01T00:00:00Z", "atualizado": "2019-02-01T00:00:00Z", "cidade": c[1], "uf": c[2], "pais": "BR", "lat": c[3], "lon": c[4]},
        "9201": {"id": 9201, "nome": "Datacenter Fictício Montevidéu", "org_id": 7004, "org_nome": "Hosting Fictício SA", "criado": "2014-01-01T00:00:00Z", "atualizado": "2026-01-01T00:00:00Z",
                 "cidade": "Cidade Exemplo", "pais": "UY", "lat": -34.9, "lon": -56.2},
    }
    nets = sorted(registrados)
    vinc = [[9101, asn, "2020-01-0%dT00:00:00Z" % (1 + i % 9), "2026-06-0%dT00:00:00Z" % (1 + i % 9)] for i, asn in enumerate(nets[:6])]
    vinc += [[9102, asn, "2018-01-01T00:00:00Z", "2024-03-10T00:00:00Z"] for asn in nets[:2]]
    ixfac = [[9101, 9000], [9101, 9001], [9102, 9000], [9103, 9999], [9201, EXTERNAL_IXP["pdb_ix_id"]]]
    return {"snapshot_date": d, "fetched_at": f"{d}T12:00:00+00:00", "fonte": "https://www.peeringdb.com/api", "citacao": "sintético", "requisicoes": 1,
            "escopo": "sintético", "facilities": facilities, "netfac": sorted(vinc), "ixfac": sorted(ixfac), "ixps": {"9999": {"id": 9999, "nome": "PTT Fictício Sem Cadastro", "cidade": c[1], "pais": "BR"}},
            "carriers": {"501": {"id": 501, "nome": "Carrier Exemplo", "org_nome": "Carrier Fictícia S.A.", "site": "https://carrier.example.org", "instalacoes_declaradas": 2, "criado": "2020-01-01T00:00:00Z",
                                 "atualizado": "2025-01-01T00:00:00Z"},
                         "502": {"id": 502, "nome": "Backbone Exemplo", "criado": "2021-01-01T00:00:00Z", "atualizado": "2022-01-01T00:00:00Z"}},
            "carrierfac": [[501, 9101], [501, 9102], [502, 9101]],
            "campus": {"7": {"id": 7, "nome": "Campus Exemplo SP", "org_nome": "Operadora Fictícia S.A.", "cidade": a[1], "uf": a[2], "pais": "BR", "criado": "2023-01-01T00:00:00Z", "atualizado": "2025-06-01T00:00:00Z"}},
            "redes": {str(asn): {"escopo": "Regional" if i % 2 else "Global", "ipv6": i % 3 != 0, "multicast": False, "unicast": True, "nunca_via_route_server": False,
                                 **({"looking_glass": f"https://lg.example.org/as{asn}"} if i % 2 == 0 else {}), **({"route_server": f"telnet://rs.example.org/as{asn}"} if i % 4 == 0 else {}),
                                 "criado": "2019-01-01T00:00:00Z", "atualizado": "2026-05-01T00:00:00Z", "portas_atualizadas": "2025-01-01T00:00:00Z", "instalacoes_atualizadas": "2026-06-01T00:00:00Z",
                                 "ixps_declarados": 1, "instalacoes_declaradas": 1} for i, asn in enumerate(nets)}}
