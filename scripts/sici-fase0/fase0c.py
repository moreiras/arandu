# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cruza o resultado de fase0.py com as organizações geolocalizadas e os usuários estimados da APNIC.

Variáveis: SICI_FASE0_DIR (diretório de trabalho: lê member2026.bin, grava e lê latest_by_cnpj.json e by_cnpj_month.json;
padrão: o diretório atual) e SICI_FASE0_SNAP (pasta summary/ de um normalizado, ex.: data/normalized/AAAA-MM-DD/summary).
"""
import json, gzip, re, collections, statistics, sys
import os
SCRATCH = os.environ.get("SICI_FASE0_DIR", ".")
SNAP = os.environ.get("SICI_FASE0_SNAP") or sys.exit("defina SICI_FASE0_SNAP (pasta summary/ de um normalizado)")
latest=json.load(open(os.path.join(SCRATCH, "latest_by_cnpj.json")))
geo=json.load(gzip.open(f"{SNAP}/geo_orgs.json.gz","rt",encoding="utf-8"))
ap=json.load(gzip.open(f"{SNAP}/apnic_pop.json.gz","rt",encoding="utf-8"))
print("apnic keys:", list(ap)[:5])
pop = ap.get("asns") or ap.get("data") or ap
sample=list(pop.items())[:2]; print("amostra apnic:", sample)
asn_cnpj={}
for a,org in geo.get("orgs",{}).items():
    c=re.sub(r"\D","",org.get("cnpj") or "")
    if len(c)==14: asn_cnpj[int(a)]=c
rows=[]
for a,c in asn_cnpj.items():
    d=latest.get(c)
    if not d or d["ac"]<100: continue
    e=pop.get(str(a)) or pop.get(a)
    if not e: continue
    u=e.get("users") if isinstance(e,dict) else e
    if not u or u<100: continue
    rows.append((u/d["ac"],a,u,d["ac"],d["meta"][0]))
rows.sort()
print(f"\nASNs comparáveis (>=100 acessos e >=100 usuários APNIC): {len(rows)}")
r=[x[0] for x in rows]
print(f"  razão usuários_APNIC/acessos_SICI — mediana {statistics.median(r):.2f}  "
      f"p10 {r[len(r)//10]:.2f}  p90 {r[9*len(r)//10]:.2f}")
print("\n  APNIC MUITO BAIXO (bottom 6):")
for ra,a,u,ac,nm in rows[:6]: print(f"    AS{a:<7} {nm[:26]:<26} apnic {u:>9,}  sici {ac:>9,}  razão {ra:6.2f}")
print("  APNIC MUITO ALTO (top 6):")
for ra,a,u,ac,nm in rows[-6:]: print(f"    AS{a:<7} {nm[:26]:<26} apnic {u:>9,}  sici {ac:>9,}  razão {ra:6.2f}")
