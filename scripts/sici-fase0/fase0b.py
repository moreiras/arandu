# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cruza o resultado de fase0.py com as organizações geolocalizadas e as outorgas SCM.

Variáveis: SICI_FASE0_DIR (diretório de trabalho: lê member2026.bin, grava e lê latest_by_cnpj.json e by_cnpj_month.json;
padrão: o diretório atual) e SICI_FASE0_SNAP (pasta summary/ de um normalizado, ex.: data/normalized/AAAA-MM-DD/summary).
"""
import json, gzip, re, collections, sys
import os
SCRATCH = os.environ.get("SICI_FASE0_DIR", ".")
SNAP = os.environ.get("SICI_FASE0_SNAP") or sys.exit("defina SICI_FASE0_SNAP (pasta summary/ de um normalizado)")
latest = json.load(open(os.path.join(SCRATCH, "latest_by_cnpj.json")))
tot_ac = sum(d["ac"] for d in latest.values())

geo = json.load(gzip.open(f"{SNAP}/geo_orgs.json.gz", "rt", encoding="utf-8"))
cnpj_to_asns = collections.defaultdict(list)
for asn_str, org in geo.get("orgs", {}).items():
    c = re.sub(r"\D", "", org.get("cnpj") or "")
    if len(c) == 14:
        cnpj_to_asns[c].append(int(asn_str))
root_to_asns = collections.defaultdict(set)
for c, a in cnpj_to_asns.items():
    root_to_asns[c[:8]].update(a)

scm = json.load(gzip.open(f"{SNAP}/anatel_scm.json.gz", "rt", encoding="utf-8"))
scm_cnpjs = set(scm["by_cnpj"])
scm_roots = {c[:8] for c in scm_cnpjs}

def rate(pred):
    n = sum(1 for c in latest if pred(c))
    a = sum(d["ac"] for c, d in latest.items() if pred(c))
    return n, 100*n/len(latest), a, 100*a/tot_ac

print("="*74)
print(f"2) MATCH DE CNPJ  (universo: {len(latest):,} CNPJs com acesso, {tot_ac:,} acessos)")
print(f"{'':38} {'CNPJs':>8} {'%':>6} {'acessos':>14} {'%':>7}")
for label, pred in [
    ("SICI ∩ outorga SCM (CNPJ-14)", lambda c: c in scm_cnpjs),
    ("SICI ∩ outorga SCM (raiz-8)",  lambda c: c[:8] in scm_roots),
    ("SICI ∩ ASN via geo_orgs (CNPJ-14)", lambda c: c in cnpj_to_asns),
    ("SICI ∩ ASN via geo_orgs (raiz-8)",  lambda c: c[:8] in root_to_asns),
    ("SICI ∩ ASN (14 ou raiz)",      lambda c: c in cnpj_to_asns or c[:8] in root_to_asns),
    ("sem outorga e sem ASN",        lambda c: c not in scm_cnpjs and c[:8] not in scm_roots and c[:8] not in root_to_asns),
]:
    n, pn, a, pa = rate(pred)
    print(f"  {label:<36} {n:>8,} {pn:5.1f}% {a:>14,} {pa:6.1f}%")

print("\n  ganho da raiz-8 sobre CNPJ-14 (ASN):")
only_root = [c for c in latest if c not in cnpj_to_asns and c[:8] in root_to_asns]
print(f"    +{len(only_root):,} CNPJs, +{sum(latest[c]['ac'] for c in only_root):,} acessos")

print("\n3) MULTIPLICIDADE CNPJ ↔ ASN (entre os que casam)")
multi = {c: cnpj_to_asns[c] for c in latest if len(cnpj_to_asns.get(c, [])) > 1}
print(f"  CNPJs com >1 ASN .................. {len(multi):,}")
print(f"    acessos envolvidos ............. {sum(latest[c]['ac'] for c in multi):,} "
      f"({100*sum(latest[c]['ac'] for c in multi)/tot_ac:.1f}% do total)")
asn_cnpjs = collections.defaultdict(set)
for c in latest:
    for a in cnpj_to_asns.get(c, []):
        asn_cnpjs[a].add(c)
multi_asn = {a: cs for a, cs in asn_cnpjs.items() if len(cs) > 1}
print(f"  ASNs com >1 CNPJ do SICI ......... {len(multi_asn):,}")
print(f"  ASNs BR com dados SICI ........... {len(asn_cnpjs):,}")

print("\n4b) OUTLIERS DE VELOCIDADE (capacidade média por acesso, mês 07)")
susp = sorted(((d["cap"]/d["ac"], c, d) for c, d in latest.items() if d["ac"] > 0),
              key=lambda t: -t[0])[:8]
for v, c, d in susp:
    print(f"    {c}  {d['meta'][0][:28]:<28} {d['ac']:>8,} acessos  média {v:>18,.0f} Mbps")
med = sorted(d["cap"]/d["ac"] for d in latest.values() if d["ac"] > 0)
print(f"    mediana da capacidade média/acesso: {med[len(med)//2]:,.0f} Mbps")

print("\n8) MUNICÍPIOS")
print(f"  média de municípios por CNPJ ..... {sum(d['mun'] for d in latest.values())/len(latest):.1f}")
big = sorted(latest.items(), key=lambda kv: -kv[1]["mun"])[:5]
for c, d in big:
    print(f"    {d['meta'][0][:30]:<30} {d['mun']:>5} municípios  {d['ac']:>12,} acessos")
