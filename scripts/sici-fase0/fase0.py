# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Validação exploratória do dado bruto do SICI (acessos de banda larga), anterior ao coletor: leitura do arquivo, totais por CNPJ e mês.

Variáveis: SICI_FASE0_DIR (diretório de trabalho: lê member2026.bin, grava e lê latest_by_cnpj.json e by_cnpj_month.json;
padrão: o diretório atual) e SICI_FASE0_SNAP (pasta summary/ de um normalizado, ex.: data/normalized/AAAA-MM-DD/summary).
"""
import struct, zlib, csv, io, json, gzip, re, collections, sys

import os
SCRATCH = os.environ.get("SICI_FASE0_DIR", ".")
SNAP = os.environ.get("SICI_FASE0_SNAP") or sys.exit("defina SICI_FASE0_SNAP (pasta summary/ de um normalizado)")

def member_stream(path):
    f = open(path, "rb")
    hdr = f.read(30)
    nl, el = struct.unpack("<HH", hdr[26:30])
    f.read(nl + el)
    d = zlib.decompressobj(-15)
    tail = b""
    while True:
        chunk = f.read(1 << 20)
        if not chunk:
            break
        data = tail + d.decompress(chunk)
        lines = data.split(b"\n")
        tail = lines.pop()
        for ln in lines:
            yield ln
    if tail:
        yield tail

# --- agregação -------------------------------------------------------------
rows = 0
mes_rows = collections.Counter()
by_cnpj_month = collections.defaultdict(int)          # (cnpj, mes) -> acessos
cnpj_meta = {}                                        # cnpj -> (empresa, grupo, porte)
latest = {}                                           # cnpj -> dict do último mês
vel_bad = 0; vel_zero = 0; vel_max = 0.0
ibge_bad = 0
mun_keys = set()
agg_keys_latest = set()
grupo_cnpjs = collections.defaultdict(set)
empresa_cnpjs = collections.defaultdict(set)
tipos_pessoa = collections.Counter(); produtos = collections.Counter()
tecs = collections.Counter(); meios = collections.Counter(); faixas = collections.Counter()
portes = collections.Counter()

it = member_stream(f"{SCRATCH}/member2026.bin")
header = next(it).decode("utf-8-sig").strip().split(";")
idx = {n: i for i, n in enumerate(header)}
I = lambda n: idx[n]
LATEST_MES = 7

for raw in it:
    try:
        line = raw.decode("utf-8")
    except UnicodeDecodeError:
        line = raw.decode("latin-1")
    line = line.rstrip("\r")
    if not line:
        continue
    r = line.split(";")
    if len(r) < len(header):
        continue
    rows += 1
    mes = int(r[I("Mês")])
    mes_rows[mes] += 1
    cnpj = re.sub(r"\D", "", r[I("CNPJ")])
    try:
        ac = int(r[I("Acessos")] or 0)
    except ValueError:
        ac = 0
    by_cnpj_month[(cnpj, mes)] += ac
    if cnpj not in cnpj_meta:
        cnpj_meta[cnpj] = (r[I("Empresa")], r[I("Grupo Econômico")], r[I("Porte da Prestadora")])
    grupo_cnpjs[r[I("Grupo Econômico")]].add(cnpj)
    empresa_cnpjs[r[I("Empresa")]].add(cnpj)

    try:
        vel = float(r[I("Velocidade")].replace(",", "."))
    except ValueError:
        vel = -1.0
    if vel < 0: vel_bad += 1
    elif vel == 0: vel_zero += 1
    else: vel_max = max(vel_max, vel)

    ibge = r[I("Código IBGE Município")].strip()
    if not ibge.isdigit() or len(ibge) != 7:
        ibge_bad += 1

    if mes == LATEST_MES:
        tp = r[I("Tipo de Pessoa")]
        tipos_pessoa[tp] += ac; produtos[r[I("Tipo de Produto")]] += ac
        tecs[r[I("Tecnologia")]] += ac; meios[r[I("Meio de Acesso")]] += ac
        faixas[r[I("Faixa de Velocidade")]] += ac; portes[r[I("Porte da Prestadora")]] += ac
        mun_keys.add((cnpj, ibge))
        agg_keys_latest.add((cnpj, ibge, tp, r[I("Meio de Acesso")]))
        d = latest.setdefault(cnpj, {"ac": 0, "pf": 0, "pj": 0, "cap": 0.0, "mun": set()})
        d["ac"] += ac
        if tp.startswith("Pessoa F"): d["pf"] += ac
        else: d["pj"] += ac
        if vel > 0: d["cap"] += vel * ac
        d["mun"].add(ibge)

print("=" * 72)
print("1) CARDINALIDADE")
print(f"  linhas totais no CSV 2026 ......... {rows:,}")
for m in sorted(mes_rows):
    print(f"    mês {m:02d} ........................ {mes_rows[m]:,} linhas")
print(f"  CNPJs distintos (ano) ............. {len(cnpj_meta):,}")
print(f"  CNPJs com acesso no mês {LATEST_MES:02d} ...... {len(latest):,}")
print(f"  chaves (cnpj,ibge) mês {LATEST_MES:02d} ....... {len(mun_keys):,}")
print(f"  chaves (cnpj,ibge,tp,meio) mês {LATEST_MES:02d}  {len(agg_keys_latest):,}   <- tamanho do agregado mensal")
tot_mes = sum(v for (c, m), v in by_cnpj_month.items() if m == LATEST_MES)
print(f"  acessos totais mês {LATEST_MES:02d} ........... {tot_mes:,}")

print("\n4) SANIDADE DA VELOCIDADE")
print(f"  não-numéricas ..................... {vel_bad:,}")
print(f"  zero .............................. {vel_zero:,}")
print(f"  máxima observada (Mbps) ........... {vel_max:,.0f}")

print("\n5) CÓDIGO IBGE")
print(f"  linhas com IBGE inválido .......... {ibge_bad:,} ({100*ibge_bad/rows:.3f}%)")

print("\n6) AGRUPADORES")
print(f"  Grupos Econômicos distintos ....... {len(grupo_cnpjs)}")
outros = len(grupo_cnpjs.get("OUTROS", ()))
print(f"  CNPJs em 'OUTROS' ................. {outros:,} de {len(cnpj_meta):,} ({100*outros/len(cnpj_meta):.1f}%)")
print(f"  Empresas (marcas) distintas ....... {len(empresa_cnpjs):,}")
amb = sum(1 for e, cs in empresa_cnpjs.items() if len(cs) > 1)
print(f"  marcas com >1 CNPJ (ambíguas) ..... {amb:,} ({100*amb/len(empresa_cnpjs):.2f}%)")
print("  grupos nomeados multi-CNPJ:")
for g, cs in sorted(grupo_cnpjs.items(), key=lambda kv: -len(kv[1]))[:10]:
    if g != "OUTROS":
        print(f"    {g:<28} {len(cs)} CNPJs")

print("\n7) DISTRIBUIÇÃO (mês %02d, por acessos)" % LATEST_MES)
for name, ctr in (("Tipo de Pessoa", tipos_pessoa), ("Tipo de Produto", produtos),
                  ("Porte", portes), ("Meio de Acesso", meios)):
    print(f"  {name}:")
    for k, v in ctr.most_common(6):
        print(f"    {k:<34} {v:>12,}  {100*v/tot_mes:5.2f}%")

json.dump({c: {"ac": d["ac"], "pf": d["pf"], "pj": d["pj"], "cap": d["cap"],
               "mun": len(d["mun"]), "meta": cnpj_meta[c]} for c, d in latest.items()},
          open(f"{SCRATCH}/latest_by_cnpj.json", "w"))
json.dump({f"{c}|{m}": v for (c, m), v in by_cnpj_month.items()},
          open(f"{SCRATCH}/by_cnpj_month.json", "w"))
print("\n(agregados salvos para a etapa de match)")
