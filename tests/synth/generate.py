# SPDX-License-Identifier: AGPL-3.0-or-later
"""Gerador determinístico do dataset sintético "Arandurápolis".

    python -m tests.synth.generate --seed 1 --out tests/data/arandurapolis

Escreve, para cada instante (T0, T1), a mesma árvore que o pipeline produz:
  raw/{data}/{ptt}/bgp-{afi}-{ptt}-{data}.txt     — saída do LG (FRR) que o parser `bgp_ixp` lê
  raw/{data}/{ptt}/ixbr_members.json
  normalized/{data}/summary/*.json.gz              — fontes já normalizadas (coletores/enriquecedores)
  published/{data}/rpki/{vrp,aspa}_list.json.gz    — RPKI (publicado pelo coletor)
O repositório guarda o GERADOR e o `expected/`, não os dados.
"""
from __future__ import annotations

import argparse
import gzip
import ipaddress
import json
import shutil
from pathlib import Path

from tests.synth import consumidor, contratos, exposicao, financiamento, infra, market, qualidade, radar, receita
from tests.synth.world import MUNICIPIOS, PTTS, T0, T1, World, build_world

HEADER = "   Network          Next Hop            Metric LocPrf Weight Path"
PATH_COL = HEADER.rfind("Path")
BANNER = """==============================================
=            IX.br Arandurápolis (FICTÍCIO)  =
=            Looking Glass Server            =
=   All connections and keystrokes logged    =
==============================================
lg.{code}.ix.br> terminal length 0
lg.{code}.ix.br> {cmd}
BGP table version is 1, local router ID is 192.0.2.1, vrf id 0
Default local pref 100, local AS 64496
Status codes:  s suppressed, d damped, h history, * valid, > best, = multipath,
               i internal, r RIB-failure, S Stale, R Removed
Nexthop codes: @NNN nexthop's vrf id, < announce-nh-self
Origin codes:  i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

"""


def write_gz(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _nh(i: int) -> str:
    return f"192.0.2.{10 + i % 200}"


def lg_text(code: str, afi: str, routes: list[tuple[str, list[int]]]) -> str:
    cmd = "show ip bgp" if afi == "v4" else "show bgp ipv6 unicast"
    out = [BANNER.format(code=code, cmd=cmd).rstrip("\n"), HEADER]
    n = 0
    for prefix, path in routes:
        if (":" in prefix) != (afi == "v6"):
            continue
        n += 1
        asp = " ".join(str(a) for a in path)
        if afi == "v4":
            left = f"*> {prefix}".ljust(21) + _nh(n)
            out.append(left.ljust(PATH_COL - 2) + f"0 {asp} i")
        else:
            out.append(f"*> {prefix}".ljust(21) + f"fe80::{n:x}")
            out.append(" " * (PATH_COL - 2) + f"0 {asp} i")
    out += ["", f"Displayed {n} routes and {n} total paths", f"lg.{code}.ix.br> "]
    return "\n".join(out) + "\n"


def _aspaths(world: World, summary: Path) -> None:
    """`summary/aspaths-{afi}/rvT.tsv.gz`: caminhos que um coletor veria. Clique = 3 ASNs externos (pares entre si); cada trânsito é
    cliente de um deles; os acessos, clientes do seu trânsito; 2 VPs externos, clientes do clique. Um caminho com laço (poisoning)."""
    from sources.fulltable_routeviews.caminhos import AgregadorCaminhos

    foreign = sorted(a.asn for a in world.ases.values() if a.role == "foreign")
    clique, vps = foreign[10:13], foreign[13:15]
    transits = sorted(a.asn for a in world.ases.values() if a.role == "transit")
    topo = {t: clique[i % 3] for i, t in enumerate(transits)}
    for afi in ("v4", "v6"):
        ag = AgregadorCaminhos()
        ag.definir_peers(vps)
        for i, vp in enumerate(vps):
            cv = clique[i % 3]
            for acc, t in sorted(world.transit_of.items()):
                if (":" in "".join(world.ases[acc].v6[:1] or world.ases[acc].v4[:1])) != (afi == "v6"):
                    continue
                ct = topo[t]
                ag.adicionar([vp, cv] + ([ct] if ct != cv else []) + [t, acc], i)
            ag.adicionar([vp, cv, topo[transits[0]], cv, world.transit_of and sorted(world.transit_of)[0]], i)     # poisoning: laço
        ag.escrever(summary / f"aspaths-{afi}" / "rvT.tsv.gz", "rvT")


def _origens_multiplas(world: World, summary: Path) -> None:
    """`summary/origins-multi-{afi}.json.gz` de dois coletores (rvT, rvU). Cenário 1 (198.18.0.0/24: 64496 nos dois, 64497 só no
    rvU, MOAS brasileiro entre coletores); um prefixo estrangeiro com duas origens (entra só na contagem global); no v6, o prefixo
    de 64496 visto com origem estrangeira no rvU (MOAS brasileiro, um coletor por origem)."""
    foreign = sorted((a for a in world.ases.values() if a.role == "foreign"), key=lambda a: a.asn)
    fv4 = next(a for a in foreign if a.v4)
    fv6 = next(a for a in foreign if a.v6 and a.asn != fv4.asn)
    br_v6 = world.ases[64496].v6[0]
    docs = {
        "v4": {"198.18.0.0/24": {"64496": ["rvT", "rvU"], "64497": ["rvU"]},
               fv4.v4[0]: {str(fv4.asn): ["rvT", "rvU"], str(fv6.asn): ["rvU"]}},
        "v6": {br_v6: {"64496": ["rvT"], str(fv6.asn): ["rvU"]}},
    }
    for afi, prefixos in docs.items():
        write_gz(summary / f"origins-multi-{afi}.json.gz", {
            "afi": afi, "snapshot_date": world.instant, "generated_at": f"{world.instant}T03:00:00+00:00", "coletores": ["rvT", "rvU"],
            "definicao": "Prefixos com duas ou mais origens (sintético).", "prefixos": dict(sorted(prefixos.items()))})


def generate_instant(world: World, out: Path) -> None:
    d = world.instant
    raw = out / "raw" / d
    summary = out / "normalized" / d / "summary"
    ases = world.ases

    # ── raw por PTT ──
    for code, _, _ in PTTS:
        for afi in ("v4", "v6"):
            if afi in world.failed.get(code, []):
                continue                                              # coleta falhou: arquivo não existe
            p = raw / code / f"bgp-{afi}-{code}-{d}.txt"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(lg_text(code, afi, world.routes[code]), encoding="utf-8")
        mem = world.members[code]
        (raw / code / "ixbr_members.json").write_text(json.dumps({
            "ixp": code, "fetched_at": f"{d}T01:00:00+00:00", "members_count": len(mem),
            "members": [{"asn": a, "name": ases[a].name} for a in sorted(mem)]}, ensure_ascii=False), encoding="utf-8")

    # ── Registro.br (`registro_br`) e LACNIC (`lacnic_delegated`) ──
    br = [a for a in ases.values() if a.is_br]
    write_gz(summary / "registro_br.json.gz", {
        "snapshot_date": d, "total_asns": len(br),
        "asns": [{"asn": a.asn, "name": a.name, "cnpj": a.cnpj, "prefixes_v4": sorted(a.v4 + a.v4_idle),
                  "prefixes_v6": sorted(a.v6)} for a in sorted(br, key=lambda x: x.asn)]})
    write_gz(summary / "lacnic_delegated.json.gz", {"snapshot_date": d, "br_asns": sorted(a.asn for a in br),
                                                    "total_br_asns": len(br)})
    write_gz(summary / "asn_names.json.gz", {str(a.asn): f"{a.name}, {a.cc}" for a in ases.values()})

    # `rdap` (rdap) e geolocalização de ASNs internacionais (PeeringDB)
    write_gz(summary / "orgs.json.gz", {"snapshot_date": d, "total": len(br), "with_cnpj": len(br),
                                         "orgs": {str(a.asn): {"name": a.name, "cnpj": a.cnpj} for a in br}})
    fo = [a for a in ases.values() if a.role == "foreign"]
    write_gz(summary / "geo_intl_asns.json.gz", {"snapshot_date": d, "total": len(fo), "geolocated": len(fo), "asns": {
        str(a.asn): {"name": a.name, "city": "Nova Exemplo", "country": a.cc, "lat": 40.0, "lon": -74.0,
                     "geo_source": "peeringdb", "geo_confidence": "org_coords"} for a in fo}})

    # ── tabela global (RouteViews): índice de origens, conjunto de prefixos, grafo de adjacência ──
    for afi in ("v4", "v6"):
        by_origin: dict[str, list[str]] = {}
        for p, o in world.full_table.items():
            if (":" in p) == (afi == "v6"):
                by_origin.setdefault(str(o), []).append(p)
        write_gz(summary / f"origin-prefixes-{afi}.json.gz", {k: sorted(v) for k, v in sorted(by_origin.items(), key=lambda kv: int(kv[0]))})
        write_gz(summary / f"prefix-set-{afi}.json.gz", sorted(p for p in world.full_table if (":" in p) == (afi == "v6")))
        up: dict[int, set] = {}
        dn: dict[int, set] = {}
        for code in world.routes:
            for p, path in world.routes[code]:
                if (":" in p) != (afi == "v6"):
                    continue
                for i in range(len(path) - 1):
                    up.setdefault(path[i + 1], set()).add(path[i])
                    dn.setdefault(path[i], set()).add(path[i + 1])
        for acc, tr in world.transit_of.items():
            up.setdefault(acc, set()).add(tr)
            dn.setdefault(tr, set()).add(acc)
        write_gz(summary / f"aspath-adj-{afi}.json.gz", {str(a): {"up": sorted(up.get(a, ())), "down": sorted(dn.get(a, ()))}
                                                         for a in sorted(set(up) | set(dn))})

    # ── caminhos dos coletores com VP: clique de 3 ASNs externos, 2 VPs, trânsitos abaixo do clique ──
    _aspaths(world, summary)

    # ── origens múltiplas por coletor (MOAS, `origins-multi-{afi}`): 2 coletores fictícios ──
    _origens_multiplas(world, summary)

    # ── APNIC, PeeringDB, geolocalização ──
    write_gz(summary / "apnic_pop.json.gz", {"date": d, "window_days": 60, "asns": {
        str(a.asn): {"users": a.users, "users_pct_cc": round(a.users / 2e6 * 100, 4), "v6_users": a.v6_users,
                     "v6_pct_as": round(a.v6_users / a.users * 100, 2) if a.users else 0.0}
        for a in br if a.users}})
    pdb_registered = {str(a.asn): {"asn": a.asn, "name": a.name, "info_type": "NSP" if a.role == "transit" else "Cable/DSL/ISP",
                                   "policy_general": "Open"} for a in br if a.asn % 2 == 0}
    write_gz(summary / "peeringdb_networks.json.gz", {"snapshot_date": d, "total_br_asns": len(br),
                                                      "pdb_registered": len(pdb_registered), "networks": pdb_registered})
    ext = infra.peeringdb_external(world)
    write_gz(summary / "peeringdb_ixps.json.gz", {"snapshot_date": d, "external_ixps": ext["external_ixps"], "ixbr_ixps": {
        c: {"pdb_ix_id": 9000 + i, "member_count": len(world.members[c]), "asns": sorted(world.members[c])}
        for i, (c, _, _) in enumerate(PTTS)}, "per_asn": ext["per_asn"]})
    write_gz(summary / "peeringdb_fac.json.gz", infra.peeringdb_fac(world, [int(a) for a in pdb_registered], d))
    write_gz(summary / "peeringdb_contacts.json.gz", {"snapshot_date": d, "total_asns_queried": len(pdb_registered),
        "asns_with_contacts": len(pdb_registered), "contacts": {a: [{"name": f"Contato {a}", "email": f"noc{a}@peeringdb.example.org",
                                                                      "role": "NOC", "phone": "+55 11 90000-0000", "visible": "Public"}]
                                                              + ([{"name": f"Restrito {a}", "email": f"restrito{a}@peeringdb.example.org",
                                                                   "role": "Policy", "visible": "Users"}] if i == 0 else [])
                                                              for i, a in enumerate(pdb_registered)}})
    # RDAP de contatos: normalized/, nunca em published/. Sintético: e-mails em rdap.example.org; o primeiro ASN só tem tentativa incompleta
    rdap_asns = sorted(pdb_registered, key=int)[:6]
    write_gz(summary / "rdap_contatos.json.gz", {"snapshot_date": d, "dado_de_contato": True,
        "cobertura": {"asns_no_universo": len(br), "com_leitura_valida": len(rdap_asns) - 1, "completos": len(rdap_asns) - 1, "parcial_confirmado": 0,
                      "nao_encontrado": 0, "so_incompletos": 1, "leitura_mais_antiga": d, "leitura_mais_recente": d},
        "contatos": {a: ({"em": None, "tentou_em": d, "status": "incompleto", "contatos": [], "incompletas": 0} if i == 0 else
                         {"em": d, "tentou_em": d, "status": "completo", "incompletas": 0, "contatos": [
                             {"papel": "administrative", "email": f"adm{a}@rdap.example.org", "handle": f"ADM{a}"},
                             {"papel": "abuse", "email": f"abuse{a}@rdap.example.org", "handle": f"ABU{a}"}]}) for i, a in enumerate(rdap_asns)}})
    mun = {m[0]: m for m in MUNICIPIOS}
    orgs = {}
    for a in br:
        m = mun[a.municipio_ibge]
        orgs[str(a.asn)] = {"name": a.name, "cnpj": a.cnpj, "lat": m[3], "lon": m[4], "city": m[1], "uf": m[2],
                            "municipio": m[1], "geo_confidence": "city_centroid", "geo_source": "nominatim"}
    write_gz(summary / "geo_orgs.json.gz", {"snapshot_date": d, "total": len(br), "geolocated": len(orgs), "cached": 0,
                                            "unknown": 0, "orgs": orgs})
    geo_prefixes = {}
    for a in br:
        m = mun[a.municipio_ibge]
        for p in a.v4 + a.v4_idle + a.v6:
            geo_prefixes[p] = {"lat": m[3], "lon": m[4], "city": m[1], "country": "BR", "uf": m[2],
                               "geo_confidence": "city_centroid", "geo_source": "geolite2-2026-09"}
    write_gz(summary / "geo_prefixes.json.gz", {"snapshot_date": d, "mmdb_month": "2026-09", "geo_source": "geolite2-2026-09",
                                                "total": len(geo_prefixes), "geolocated": len(geo_prefixes), "unknown": 0,
                                                "prefixes": geo_prefixes})

    # ── mercado: outorgas (brutas e geocodificadas), SICI fixo/móvel e quadro societário ──
    outs = market.outorgas(world)
    for svc, recs in outs.items():
        by = {}
        for r in recs:
            by.setdefault(r["cnpj"], []).append(r)
        write_gz(summary / f"anatel_{svc}.json.gz", {"snapshot_date": d, "total": len(recs), "unique_cnpjs": len(by),
                                                       f"{svc}s": recs, "by_cnpj": by})
        geo = market.with_geo(recs)
        gby = {}
        for r in geo:
            gby.setdefault(r["cnpj"], []).append(r)
        write_gz(summary / f"anatel_{svc}_geo.json.gz", {"snapshot_date": d, "total": len(geo), "geolocated": len(geo),
                                                           "cached": 0, "unknown": 0, "unique_cnpjs": len(gby),
                                                           f"{svc}s": geo, "by_cnpj": gby})
    sici_doc = market.sici(world)
    write_gz(summary / "sici_acessos.json.gz", sici_doc)
    # cache mensal do SICI (coletor anatel_sici): um arquivo por mês, compartilhado entre os instantes; o instante T1 lê o mês de T0 como "anterior"
    write_gz(out / "normalized" / "sici_cache" / "months" / f"{sici_doc['mes_referencia']}.json.gz", {"mes": sici_doc["mes_referencia"], "cnpjs": sici_doc["cnpjs"]})
    write_gz(summary / "sici_movel_acessos.json.gz", market.sici_movel(world))
    for nome, doc in zip(("apnic_irov", "apnic_dnssec", "caida_asrank", "bogons"), market.seguranca(world)):
        write_gz(summary / f"{nome}.json.gz", doc)
    as2org_doc, abusech_doc = market.as2org_abusech(world)
    write_gz(summary / "caida_as2org.json.gz", as2org_doc)
    write_gz(summary / "abusech.json.gz", abusech_doc)
    write_gz(summary / "ooni_bloqueios.json.gz", market.ooni_bloqueios(world))
    sp_doc, irr_doc = market.spoofer_irr(world, d)
    write_gz(summary / "caida_spoofer.json.gz", sp_doc)
    write_gz(summary / "irr_route_objects.json.gz", irr_doc)
    write_gz(summary / "manrs_participantes.json.gz", market.manrs(world, d))
    rs_doc, rs_comm = market.route_servers(world)
    write_gz(summary / "rs_sessions.json.gz", rs_doc)
    write_gz(summary / "ixbr_communities.json.gz", rs_comm)
    rs_f, rs_c = market.rs_rotas(world, rs_doc)
    write_gz(summary / "rs_filtered.json.gz", rs_f)
    write_gz(summary / "rs_communities.json.gz", rs_c)
    for nome, doc in market.cetic(d).items():
        write_gz(summary / f"{nome}.json.gz", doc)
    write_gz(summary / "anatel_erbs.json.gz", market.erbs(world, d))
    write_gz(summary / "anatel_fust.json.gz", market.fust(world, d))
    write_gz(summary / "anatel_multas.json.gz", market.multas(world, d))
    write_gz(summary / "anatel_rqual.json.gz", qualidade.rqual(world, d))
    write_gz(summary / "anatel_reclamacoes.json.gz", qualidade.reclamacoes(world, d))
    write_gz(summary / "consumidor_gov.json.gz", consumidor.consumidor_gov(world, d))
    write_gz(summary / "receita_cnpj.json.gz", receita.receita_cnpj(world, d))
    write_gz(summary / "cloudflare_radar.json.gz", radar.cloudflare_radar(world, d))
    write_gz(summary / "shodan_exposicao.json.gz", exposicao.shodan_exposicao(world, d))
    write_gz(summary / "bndes_operacoes.json.gz", financiamento.bndes(world, d))
    write_gz(summary / "cgu_ceis_cnep.json.gz", financiamento.cgu(world, d))
    write_gz(summary / "siasg_contratos.json.gz", contratos.siasg_contratos(world, d))
    write_gz(summary / "anatel_pdff.json.gz", market.pdff(world, d))
    write_gz(summary / "anatel_satelites.json.gz", market.satelites(world, d))
    ipv4_doc, ipv4_estado, ipv4_ev = market.ipv4(world, d)
    write_gz(summary / "ipv4_listas.json.gz", ipv4_doc)
    write_gz(out / "ipv4" / "delegated_estado.json.gz", ipv4_estado)
    for mes, evs in ipv4_ev.items():
        (out / "ipv4" / "eventos").mkdir(parents=True, exist_ok=True)
        (out / "ipv4" / "eventos" / f"{mes}.jsonl.gz").write_bytes(gzip.compress("\n".join(json.dumps(e) for e in evs).encode(), mtime=0))
    muns, taxas = market.ibge(world)
    write_gz(summary / "ibge_municipios.json.gz", {"snapshot_date": d, "generated_at": "2026-01-01T00:00:00+00:00", "fonte": "sintético", "censo_ano": "2022", "estimativa_ano": "2026",
                                                   "total": len(muns), "municipios": muns})
    write_gz(summary / "ibge_taxa_internet.json.gz", {"snapshot_date": d, "generated_at": "2026-01-01T00:00:00+00:00", "fonte": "sintético", "pnad_ano": "2025",
                                                      "brasil": None, "ufs": taxas})
    write_gz(summary / "receita_socios.json.gz", market.receita_socios(world))

    # ── infraestrutura física e prefixos globais geolocalizados ──
    for name, doc in (("itu_transmission", infra.itu()), ("aneel_transmission", infra.aneel()), ("ibge_rodovias", infra.rodovias()),
                      ("telegeography_cables", infra.cables())):
        write_gz(summary / f"{name}.json.gz", {**doc, "snapshot_date": d})
    write_gz(summary / "geo_global_prefixes.json.gz", infra.global_prefixes(world))

    # ── RPKI publicado ──
    write_gz(out / "published" / d / "rpki" / "vrp_list.json.gz", world.rpki)
    write_gz(out / "published" / d / "rpki" / "aspa_list.json.gz", world.aspa)


def generate(out: Path, seed: int = 1, instants=(T0, T1), extra_asns: int = 0) -> dict:
    out = Path(out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    worlds = {}
    for t in instants:
        w = build_world(t, seed, extra_asns)
        generate_instant(w, out)
        worlds[t] = w
    return {"seed": seed, "instants": list(instants), "ases": len(worlds[instants[0]].ases),
            "ptts": [p[0] for p in PTTS]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    print(json.dumps(generate(Path(a.out), a.seed)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
