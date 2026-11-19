#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Recorta as amostras reais mínimas de `tests/fixtures/raw/<fonte>/`.

Requer os dados locais (`data/raw/<data>/…`, `data/normalized/<data>/…`), que NÃO estão no
repositório; foi executado uma vez e o resultado está versionado. Mantido só para que o
recorte seja reproduzível/auditável (cada fonte tem um README dizendo o que foi cortado).

Uso: python3 tests/fixtures/cut_fixtures.py [--date 2026-09-20] [grupo ...]
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tests" / "fixtures" / "raw"
DATE = "2026-09-20"


def raw(*p):
    return ROOT / "data" / "raw" / DATE / Path(*p)


def norm(*p):
    return ROOT / "data" / "normalized" / DATE / Path(*p)


def w(src: str, name: str, content: str | bytes) -> None:
    d = OUT / src
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    print(f"  {p.relative_to(ROOT)} ({p.stat().st_size} B)")


def readme(src: str, text: str) -> None:
    w(src, "README.md", text.strip() + "\n")


# ── grupo A: texto/HTTP simples ────────────────────────────────────────────

def group_a() -> None:
    # Registro.br nicbr-asn-blk: linhas reais; listas longas de prefixos truncadas em 6.
    keep = {174, 1251, 2635, 2914, 28573}
    lines = []
    for ln in raw("summary", f"nicbr-asn-blk-{DATE}.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"AS(\d+)\|", ln)
        if m and int(m.group(1)) in keep:
            parts = ln.split("|")
            lines.append("|".join(parts[:3] + parts[3:9]))
    w("registro_br", "nicbr-asn-blk.sample.txt", "\n".join(lines) + "\n")
    readme("registro_br", f"""
# registro_br — nicbr-asn-blk-latest.txt
Origem: https://ftp.registro.br/pub/numeracao/origin/nicbr-asn-blk-latest.txt, coletado em {DATE}.
Recorte: 5 linhas reais (AS174, AS1251, AS2635, AS2914, AS28573), com no máximo 6 prefixos por ASN.
Formato: `AS{{n}}|Nome|CNPJ|prefixo|prefixo…` (dados cadastrais públicos de operadoras).
""")

    # LACNIC delegated-extended: cabeçalho + resumo + amostra de linhas reais.
    out, br_asn, br_v4, other_asn = [], 0, 0, 0
    for ln in raw("summary", f"delegated-lacnic-extended-{DATE}.txt").read_text().splitlines():
        p = ln.split("|")
        if ln.startswith("2.3|") or (len(p) > 5 and p[5] == "summary"):
            out.append(ln)
        elif len(p) > 6 and p[2] == "asn" and p[1] == "BR" and br_asn < 5:
            out.append(ln); br_asn += 1
        elif len(p) > 6 and p[2] == "asn" and p[1] != "BR" and other_asn < 3:
            out.append(ln); other_asn += 1
        elif len(p) > 6 and p[2] == "ipv4" and p[1] == "BR" and br_v4 < 3:
            out.append(ln); br_v4 += 1
        elif len(p) > 6 and p[2] == "ipv4" and len([x for x in out if "ipv4|" in x and "|BR|" not in x]) < 3 and p[1] != "BR":
            out.append(ln)
    w("lacnic_delegated", "delegated-lacnic-extended.sample.txt", "\n".join(out) + "\n")
    readme("lacnic_delegated", f"""
# lacnic_delegated — delegated-lacnic-extended-latest
Origem: https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-extended-latest, coletado em {DATE}.
Recorte: cabeçalho de versão, 3 linhas de resumo, 5 ASNs do BR, 3 ASNs de outros países e
alguns blocos IPv4 (BR e não BR). Formato: `rir|cc|tipo|início|valor|data|status|id`.
""")

    # RIPE asn.txt: derivado do normalizado (o bruto não é guardado): "{asn} {nome}, {CC}".
    names = json.load(gzip.open(norm("summary", "asn_names.json.gz"), "rt"))
    pick = [k for k in ("1", "174", "1251", "2914", "4230", "7018", "13335", "15169", "26599", "28573", "262589", "64496") if k in names]
    w("asn_names", "asn.sample.txt", "\n".join(f"{k} {names[k]}" for k in pick) + "\n")
    readme("asn_names", f"""
# asn_names — https://ftp.ripe.net/ripe/asnames/asn.txt
Origem: arquivo compilado do RIPE NCC. O bruto não é retido pelo pipeline; esta amostra foi
reconstruída a partir de `normalized/{DATE}/summary/asn_names.json.gz` (mesmos nomes reais) no
formato original `{{asn}} {{nome}}, {{CC}}`. 12 ASNs (globais e brasileiros).
""")

    # APNIC v6pop: HTML real — cabeçalho + 6 linhas + rodapé.
    html = raw(f"apnic_v6pop-{DATE}.html").read_text(encoding="utf-8", errors="replace").splitlines()
    head_end = next(i for i, l in enumerate(html) if l.strip().startswith("['Rank'"))
    rows = [l for l in html[head_end + 1:] if l.strip().startswith("[") and "AS" in l][:6]
    tail_start = next(i for i, l in enumerate(html) if "]);" in l and i > head_end)
    sample = html[: head_end + 1] + rows + html[tail_start:]
    w("apnic_pop", "v6pop.sample.html", "\n".join(sample) + "\n")
    readme("apnic_pop", f"""
# apnic_pop — https://stats.labs.apnic.net/v6pop?c=BR&w=60
Origem: página HTML do APNIC Labs, coletada em {DATE}. Recorte: cabeçalho da página, linha de
colunas, as 6 primeiras linhas da tabela `arrayToDataTable([...])` e o rodapé.
""")

    # IX.br dashboard generate_json: derivado do raw guardado (asn/name).
    mem = json.load(open(raw("sp", "ixbr_members.json")))["members"][:6]
    payload = {"member_list": [{"asnum": m["asn"], "name": m["name"] or f"AS{m['asn']}"} for m in mem]}
    w("ixbr_api", "generate_json.sample.json", json.dumps(payload, ensure_ascii=False, indent=1))
    readme("ixbr_api", f"""
# ixbr_api — https://dashboard.ix.br/generate_json?ixp=sp
Origem: lista de membros do PTT SP, coletada em {DATE}. O bruto original não é retido (o
pipeline grava o resultado já reduzido a `asn`/`name`); esta amostra recria o envelope
`member_list[].asnum/name` lido pelo coletor com 6 ASNs reais.
""")

    # PeeringDB: net (real), netixlan (recriado a partir do raw), poc (real, anonimizado).
    nets = json.load(open(raw("summary", f"peeringdb-networks-{DATE}.json")))
    sel = [n for n in nets if n["asn"] in (1251, 28573, 262589, 53181, 4230)][:5] or nets[:5]
    w("peeringdb", "net.sample.json", json.dumps({"data": sel, "meta": {}}, ensure_ascii=False, indent=1))
    ixps = json.load(open(raw("summary", f"peeringdb-ixps-{DATE}.json")))
    ext = next(iter(ixps["external"].values()))["members"][:5]
    netixlan = [{"id": 1000 + i, "ix_id": 4642, "name": m["name"], "ixlan_id": 4642, "asn": m["asn"],
                 "speed": m["speed"], "is_rs_peer": True, "operational": True, "status": "ok"} for i, m in enumerate(ext)]
    w("peeringdb", "netixlan.sample.json", json.dumps({"data": netixlan, "meta": {}}, indent=1))
    pocs = json.load(open(raw("summary", f"peeringdb-contacts-{DATE}.json")))
    ids = {n["id"] for n in sel}
    chosen = [p for p in pocs if p["net_id"] in ids][:5]
    anon = []
    for i, p in enumerate(chosen):
        anon.append({**p, "name": f"Contato Ficticio {i + 1}", "phone": f"+5511900000{i:03d}",
                     "email": f"contato{i + 1}@example.org", "url": ""})
    w("peeringdb", "poc.sample.json", json.dumps({"data": anon, "meta": {}}, ensure_ascii=False, indent=1))
    readme("peeringdb", f"""
# peeringdb — /api/net, /api/netixlan, /api/poc
- `net.sample.json`: 5 registros reais de `/api/net` (coletados em {DATE}), envelope `{{"data": [...]}}`.
- `netixlan.sample.json`: 5 membros de um IXP externo; recriado a partir do raw guardado
  (asn/nome/velocidade) com os demais campos do esquema da API.
- `poc.sample.json`: 5 registros de `/api/poc` da amostra de `net`, **anonimizados**: nome,
  telefone e e-mail substituídos por valores fictícios (`@example.org`); `net_id`, `role` e
  `visible` originais. Nenhum dado pessoal real.
""")

    # RPKI Routinator /json: reconstruído a partir do publicado.
    pub = ROOT / "data" / "published" / DATE / "rpki"
    vrps = json.load(gzip.open(pub / "vrp_list.json.gz", "rt"))
    br = [v for v in vrps if v["asn"] in (28573, 262589, 53181)][:6] + vrps[:2]
    aspas = json.load(gzip.open(pub / "aspa_list.json.gz", "rt")) if (pub / "aspa_list.json.gz").exists() else []
    payload = {
        "roas": [{"asn": f"AS{v['asn']}", "prefix": v["prefix"], "maxLength": v["maxLength"], "ta": v["ta"]} for v in br],
        "aspas": [{"customer": f"AS{a['customer']}", "providers": [f"AS{p}" for p in a["providers"]], "tal": a.get("tal", "")} for a in aspas[:3]],
    }
    w("rpki", "routinator-json.sample.json", json.dumps(payload, indent=1))
    readme("rpki", f"""
# rpki — Routinator `GET /json`
A saída do Routinator (`routinator vrps -f json`, mesmo formato do `GET /json`) é sobrescrita a cada execução e não é guardada; esta amostra foi reconstruída
no formato do endpoint a partir de `published/{DATE}/rpki/{{vrp,aspa}}_list.json.gz` (8 VRPs e até 3 ASPAs reais).
""")


# ── grupo B: Anatel (outorgas e SICI) ──────────────────────────────────────

def group_b() -> None:
    import csv

    src = raw("summary", f"anatel-scm-{DATE}.csv")  # os 4 CSVs de outorgas são o mesmo arquivo
    with open(src, encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f, delimiter=";")
        header = next(r)
        i_svc = header.index("Código e Nome do Serviço da Notificação")
        i_id = header.index("Tipo de Identificação")
        i_mail = header.index("Endereço Eletrônico")
        i_tel = header.index("Telefone Principal")
        i_nome = header.index("Nome Entidade Prestadora de Serviço")
        i_fan = header.index("Nome Fantasia")
        want = {"045 - Serviço de Comunicação Multimídia": 3, "047 - Serviço de Comunicação Multimídia - Est. Terrena": 1,
                "010 - SERVIÇO MOVEL PESSOAL": 2, "110 - Serviço Móvel Pessoal por Satélite": 1,
                "171 - SERVICO TELEFONICO FIXO COMUTADO": 2, "175 - STFC/RADIOTELEFONICO - ESTACOES TERRESTRES": 1,
                "750 - Serviço de Acesso Condicionado": 2, "302 - Radioamador": 1}
        got: dict[str, int] = {}
        cpf_rows = 0
        out = []
        for row in r:
            svc = row[i_svc]
            if row[i_id] == "CPF":
                if cpf_rows < 1 and svc.startswith("302"):
                    cpf_rows += 1
                    row = list(row)
                    row[1] = "12345678909"          # CPF fictício
                    row[i_nome] = "Pessoa Fisica Ficticia"
                    row[i_fan] = "N/I"
                    row[i_mail] = "pessoa@example.org"
                    row[i_tel] = "N/I"
                    out.append(row)
                continue
            if svc in want and got.get(svc, 0) < want[svc] and row[i_id] == "CNPJ":
                got[svc] = got.get(svc, 0) + 1
                row = list(row)
                row[i_mail] = "contato@example.org"      # e-mail/telefone cadastrais mascarados
                row[i_tel] = "N/I"
                out.append(row)
            if len(got) == len(want) and all(got[k] >= v for k, v in want.items()) and cpf_rows:
                break
    buf = io.StringIO()
    wr = csv.writer(buf, delimiter=";", lineterminator="\n")
    wr.writerow(header)
    wr.writerows(out)
    w("anatel_outorgas", "prestadoras_servicos_telecomunicacoes.sample.csv", ("\ufeff" + buf.getvalue()).encode("utf-8"))
    readme("anatel_outorgas", f"""
# anatel_outorgas — prestadoras_servicos_telecomunicacoes.zip (SCM, SMP, STFC, SeAC)
Origem: dados abertos da Anatel (https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/),
coletado em {DATE}. Os quatro coletores (SCM, SMP, STFC, SeAC) leem o MESMO CSV e filtram por serviço.
Recorte: {len(out)} linhas reais de 8 serviços (045 e 047 SCM; 010 e 110 SMP; 171 e 175 STFC; 750 SeAC; 302 de controle),
mais 1 linha de pessoa física **fictícia**. E-mail e telefone cadastrais substituídos por valores
genéricos (`contato@example.org`, `N/I`). Os testes empacotam o CSV em um ZIP, como a fonte entrega.
""")

    # contratos de rede virtual (MVNO): derivado do normalizado de SMP (raw não retido).
    smp = json.load(gzip.open(norm("summary", "anatel_smp.json.gz"), "rt"))["smps"]
    seen: set[str] = set()
    cred = []
    for r_ in smp:
        if (r_.get("rede_virtual") or {}).get("papel") == "credenciada" and r_["cnpj"] not in seen:
            seen.add(r_["cnpj"])
            cred.append(r_)
    cred = cred[:3]
    lines = ["CREDENCIADA;CREDENCIADA_CNPJ;PRESTADORA_ORIGEM;PRESTADORA_ORIGEM_CNPJ;VIGENCIA_DATA_FIM"]
    for rv in cred:
        o = rv["rede_virtual"]
        lines.append(f"{rv['razao_social']};{rv['cnpj']};{o['prestadora_origem_nome']};{o['prestadora_origem_cnpj']};VIGENTE")
    if cred:
        lines.append(f"{cred[0]['razao_social']} ENCERRADA;11111111000111;{cred[0]['rede_virtual']['prestadora_origem_nome']};{cred[0]['rede_virtual']['prestadora_origem_cnpj']};31/12/2020")
    w("anatel_outorgas", "contratos_mvno.sample.csv", ("\ufeff" + "\n".join(lines) + "\n").encode("utf-8"))


def group_c() -> None:
    """SICI fixo e móvel: CSVs reconstruídos linha a linha a partir do cache agregado real."""
    cache = ROOT / "data" / "normalized"

    def month(kind: str, mes: str) -> dict:
        return json.load(gzip.open(cache / kind / "months" / f"{mes}.json.gz", "rt"))

    # ── banda larga fixa ──
    cols = ["Ano", "Mês", "Grupo Econômico", "Empresa", "CNPJ", "Porte da Prestadora", "UF", "Município",
            "Código IBGE Município", "Faixa de Velocidade", "Velocidade", "Tecnologia", "Meio de Acesso",
            "Tipo de Pessoa", "Tipo de Produto", "Acessos"]
    jul = month("sici_cache", "2026-07")
    pick = [k for _, k in sorted((v["acessos"], k) for k, v in jul["cnpjs"].items()
                                 if 0 < len(v["por_municipio"]) <= 2 and v["acessos"] > 200)[:3]]
    rows = [cols]
    for mes in ("2026-06", "2026-07"):
        m = month("sici_cache", mes)["cnpjs"]
        for cnpj in pick:
            a = m.get(cnpj)
            if not a:
                continue
            ano, mm = mes.split("-")
            faixa = next(iter(a["por_faixa"]), "N/I")
            for ibge, mun in a["por_municipio"].items():
                for tipo, n in (("Pessoa Física", mun["pf"]), ("Pessoa Jurídica", mun["pj"])):
                    if n:
                        rows.append([ano, str(int(mm)), a["grupo"], a["empresa"], cnpj, a["porte"], mun["uf"], mun["nome"],
                                     ibge, faixa, str(a["velocidade_media_mbps"]).replace(".", ","),
                                     a["tecnologia_predominante"], a["meio_predominante"], tipo, "INTERNET", str(n)])
    c0 = pick[0]
    a0 = jul["cnpjs"][c0]
    mun0 = next(iter(a0["por_municipio"].items()))
    rows.append(["2026", "7", a0["grupo"], a0["empresa"], c0, a0["porte"], mun0[1]["uf"], mun0[1]["nome"], mun0[0],
                 "> 34Mbps", "1000", "FTTH", "Fibra", "Pessoa Jurídica", "LINHA_DEDICADA", "5"])      # produto fora de INTERNET
    rows.append(["2026", "7", "OUTROS", "Empresa Sem CNPJ", "123", "Pequeno Porte", "SP", "X", "3550308", "x", "1", "x", "x", "Pessoa Física", "INTERNET", "9"])  # CNPJ inválido
    rows.append(["2026", "7", a0["grupo"], a0["empresa"], c0, a0["porte"], mun0[1]["uf"], mun0[1]["nome"], mun0[0], "x", "1", "x", "x", "Pessoa Física", "INTERNET", "0"])  # acessos = 0
    csv_text = "\ufeff" + "\n".join(";".join(r) for r in rows) + "\n"
    w("anatel_sici", "Acessos_Banda_Larga_Fixa_2026.sample.csv", csv_text.encode("utf-8"))
    tot = ["Ano;Mês;Acessos"]
    for mes in ("2026-05", "2026-06", "2026-07"):
        ano, mm = mes.split("-")
        tot.append(f"{ano};{int(mm)};{month('sici_cache', mes)['total_acessos']}")
    w("anatel_sici", "Acessos_Banda_Larga_Fixa_Total.sample.csv", ("\n".join(tot) + "\n").encode())
    readme("anatel_sici", f"""
# anatel_sici — acessos_banda_larga_fixa.zip (SICI)
Origem: https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/acessos_banda_larga_fixa.zip
(~1 GB). O bruto não é retido (o coletor lê por HTTP Range e só guarda agregados). Estas amostras foram
**reconstruídas** linha a linha a partir do cache agregado real (`normalized/sici_cache/months`, {DATE}):
3 provedores pequenos (1–2 municípios), meses 2026-06 e 2026-07, com o cabeçalho do CSV anual
(`Ano;Mês;Grupo Econômico;Empresa;CNPJ;…;Acessos`) e 3 linhas de controle (produto LINHA_DEDICADA,
CNPJ inválido, acessos = 0). `Total.sample.csv` é o membro sentinela `Ano;Mês;Acessos`.
Os testes empacotam os CSVs em um ZIP e o servem com suporte a `Range`, como a Anatel faz.
""")

    # ── telefonia móvel ──
    mcols = ["Ano", "Mês", "Grupo Econômico", "Empresa", "CNPJ", "Porte da Prestadora", "UF", "Município",
             "Código IBGE Município", "Código Nacional", "Modalidade de Cobrança", "Tecnologia Geração",
             "Tipo de Pessoa", "Tipo de Produto", "Acessos"]
    mjul = month("sici_movel_cache", "2026-07")
    mpick = [k for _, k in sorted((v["acessos"], k) for k, v in mjul["cnpjs"].items()
                                  if 0 < len(v["por_municipio"]) <= 2 and v["acessos"] > 200)[:2]]
    mrows = [mcols]
    for mes in ("2026-06", "2026-07"):
        m = month("sici_movel_cache", mes)["cnpjs"]
        for cnpj in mpick:
            a = m.get(cnpj)
            if not a:
                continue
            ano, mm = mes.split("-")
            for ibge, mun in a["por_municipio"].items():
                mod = next(iter(a["por_modalidade"]), "Pré-pago")
                ger = next(iter(a["por_geracao"]), "4G")
                for tipo, n in (("Pessoa Física", mun["pf"]), ("Pessoa Jurídica", mun["pj"])):
                    if n:
                        mrows.append([ano, str(int(mm)), a["grupo"], a["empresa"], cnpj, a["porte"], mun["uf"], mun["nome"],
                                      ibge, "11", mod, ger, tipo, "VOZ+DADOS", str(n)])
            if a["acessos_m2m"]:
                mrows.append([ano, str(int(mm)), a["grupo"], a["empresa"], cnpj, a["porte"], a["uf"], "São Paulo", "3550308",
                              "11", "Pós-pago", "4G", "Pessoa Jurídica", "M2M", str(a["acessos_m2m"])])
    mrows.append(["2026", "7", "OUTROS", "Infra Ficticia", "11111111000191", "Pequeno Porte", "SP", "São Paulo", "3550308",
                  "11", "Pós-pago", "4G", "Pessoa Jurídica", "PONTO_DE_SERVICO", "7"])
    mcsv = "\ufeff" + "\n".join(";".join(r) for r in mrows) + "\n"
    w("anatel_sici_movel", "Acessos_Telefonia_Movel_2026_2S.sample.csv", mcsv.encode("utf-8"))
    mtot = ["Ano;Mês;Acessos"]
    for mes in ("2026-05", "2026-06", "2026-07"):
        ano, mm = mes.split("-")
        mtot.append(f"{ano};{int(mm)};{month('sici_movel_cache', mes)['total_acessos']}")
    w("anatel_sici_movel", "Acessos_Telefonia_Movel_Total.sample.csv", ("\n".join(mtot) + "\n").encode())
    readme("anatel_sici_movel", f"""
# anatel_sici_movel — acessos_telefonia_movel.zip (SICI móvel)
Origem: https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/acessos_telefonia_movel.zip (~3 GB).
Mesma situação do SICI fixo: amostra **reconstruída** a partir do cache agregado real (`sici_movel_cache`,
{DATE}) com o cabeçalho do membro semestral `Acessos_Telefonia_Movel_2026_2S.csv`; 2 prestadoras pequenas,
produtos VOZ+DADOS, M2M e PONTO_DE_SERVICO (estes dois não entram no total).
""")


def group_d() -> None:
    """Camadas de infraestrutura: ITU, TeleGeography, ANEEL SIGEL e IBGE BC250 (reconstruídas)."""
    import struct

    N = ROOT / "data" / "normalized" / DATE / "summary"

    def load(name: str) -> dict:
        return json.load(gzip.open(N / f"{name}.json.gz", "rt"))

    def trunc(coords, n=5):
        return coords[:n]

    # ── ITU: WFS GetFeature (GeoJSON) ──
    itu = load("itu_transmission")["features"]
    feats = []
    for i, f in enumerate(itu[:4]):
        g = f["geometry"]
        feats.append({"type": "Feature", "id": f"trx_geocatalogue.{i}", "geometry": {"type": "LineString", "coordinates": trunc(g["coordinates"])},
                      "properties": {"uid": 1000 + i, "type_inf": f["properties"]["type_inf"], "status": f["properties"]["status"]}})
    feats.append({"type": "Feature", "id": "trx_geocatalogue.99", "geometry": {"type": "Point", "coordinates": [-47.9, -15.8]},
                  "properties": {"uid": 1099, "type_inf": "Node", "status": "Operational"}})
    w("itu", "wfs-getfeature.sample.json", json.dumps({"type": "FeatureCollection", "features": feats, "totalFeatures": len(feats),
                                                        "numberMatched": len(feats), "numberReturned": len(feats)}, indent=1))
    readme("itu", f"""
# itu — WFS `itu-geocatalogue:trx_geocatalogue` (GeoJSON)
Origem: https://bbmaps.itu.int/geoserver/itu-geocatalogue/wfs. O bruto não é retido; amostra reconstruída
no envelope do WFS (`numberMatched`, `features[]`) a partir de 4 enlaces reais de
`normalized/{DATE}/summary/itu_transmission.json.gz` (geometrias truncadas em 5 vértices) + 1 feição
`Point` (que o coletor deve ignorar).
""")

    # ── TeleGeography ──
    tg = load("telegeography_cables")
    br = [c for c in tg["cables"] if "Brazil" in c["landing_countries"]][:2]
    other = next(c for c in tg["cables"] if "Brazil" not in c["landing_countries"] and c["geometry"])
    cabos = br + [other]
    cable_geo = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"id": c["id"], "name": c["name"], "color": c["color"]},
         "geometry": {"type": c["geometry"]["type"], "coordinates": (c["geometry"]["coordinates"][:1] if c["geometry"]["type"] == "MultiLineString" else c["geometry"]["coordinates"][:4])}}
        for c in cabos]}
    for f in cable_geo["features"]:
        if f["geometry"]["type"] == "MultiLineString":
            f["geometry"]["coordinates"] = [f["geometry"]["coordinates"][0][:4]]
    w("telegeography", "cable-geo.sample.json", json.dumps(cable_geo, ensure_ascii=False, indent=1))
    lp = tg["landing_points"][:3]
    w("telegeography", "landing-point-geo.sample.json", json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"id": p["id"], "name": p["name"], "is_tbd": p["is_tbd"]}, "geometry": p["geometry"]} for p in lp]},
        ensure_ascii=False, indent=1))
    detalhes = {c["id"]: {"id": c["id"], "name": c["name"], "length": c["length"], "owners": c["owners"], "suppliers": c["suppliers"],
                          "rfs_year": c["rfs_year"], "is_planned": c["is_planned"], "url": c["url"],
                          "landing_points": [{"country": x} for x in c["landing_countries"]]} for c in cabos[:2]}
    w("telegeography", "cable-details.sample.json", json.dumps(detalhes, ensure_ascii=False, indent=1))
    readme("telegeography", f"""
# telegeography — Submarine Cable Map API v3 (CC BY-SA 4.0)
Origem: https://www.submarinecablemap.com/api/v3 (`cable/cable-geo.json`, `landing-point/landing-point-geo.json`,
`cable/{{id}}.json`). Amostra reconstruída a partir de `normalized/{DATE}/summary/telegeography_cables.json.gz`:
3 cabos (2 com pouso no Brasil) com geometria truncada, 3 pontos de aterrissagem e os detalhes dos 2 primeiros
cabos (o terceiro NÃO tem detalhe, para exercitar o tratamento de erro 404 no coletor).
""")

    # ── ANEEL SIGEL (Esri JSON) ──
    an = load("aneel_transmission")["features"]
    rows = []
    for f in an[:3]:
        pr = f["properties"]
        coords = f["geometry"]["coordinates"] if f["geometry"]["type"] == "LineString" else f["geometry"]["coordinates"][0]
        unit = [list(c) for c in coords[:4]]
        popup = (f"<b>Tensão: </b>{str(pr['tensao_kv']).replace('.', ',')} kV<br><b>Extensão: </b>"
                 f"{str(pr['extensao_km']).replace('.', ',')} km<br>")
        rows.append({"attributes": {"OBJECTID": len(rows) + 1, "Name": pr["name"], "PopupInfo": popup}, "geometry": {"paths": [unit * 3]}})   # vértices em ciclo ×3
    rows.append({"attributes": {"OBJECTID": 4, "Name": "Linha LT  34P5 kV  SE A / SE B  C P1  PI/CE", "PopupInfo": "<b>Tensão: </b>34,5 kV<br><b>Extensão: </b>1.234,5 km<br>"},
                 "geometry": {"paths": [[[-42.1, -5.1], [-42.2, -5.2], [-42.3, -5.1]]]}})
    rows.append({"attributes": {"OBJECTID": 5, "Name": "Linha sem geometria", "PopupInfo": ""}, "geometry": {}})
    w("aneel_sigel", "query-page.sample.json", json.dumps({"features": rows}, ensure_ascii=False, indent=1))
    readme("aneel_sigel", f"""
# aneel_sigel — SIGEL/ANEEL MapServer PORTAL/Transmissão, camada 1 (`f=json`, Esri JSON)
Origem: https://sigel.aneel.gov.br/arcgis/rest/services/PORTAL/Transmiss%C3%A3o/MapServer/1/query.
Amostra reconstruída de 3 linhas reais de `normalized/{DATE}/summary/aneel_transmission.json.gz`, com `PopupInfo`
no formato HTML da fonte e os vértices REPETIDOS EM CICLO (×3), que é o defeito documentado da fonte. Mais
2 feições de controle: nome com "34P5 kV"/"C P1"/"PI/CE" e uma sem geometria.
""")

    # ── IBGE BC250: shapefile binário mínimo (3 trechos reais) ──
    ib = load("ibge_rodovias")["features"]
    pick = [f for f in ib if f["geometry"]["type"] == "LineString" and f["properties"].get("sigla")][:2] + ib[:1]
    fields = [("tipovia", 30), ("jurisdicao", 30), ("administra", 30), ("concession", 30), ("revestimen", 40), ("operaciona", 10),
              ("situacaofi", 20), ("trafego", 20), ("sigla", 10), ("codtrechor", 20), ("nrpistas", 4), ("nrfaixas", 4), ("limitevelo", 6)]
    keymap = {"tipovia": "tipo_via", "jurisdicao": "jurisdicao", "administra": "administracao", "concession": "concessionaria",
              "revestimen": "revestimento", "operaciona": "operacional", "situacaofi": "situacao", "trafego": "trafego",
              "sigla": "sigla", "codtrechor": "codigo_trecho", "nrpistas": "nr_pistas", "nrfaixas": "nr_faixas", "limitevelo": "limite_velocidade_kmh"}
    rec_len = 1 + sum(n for _, n in fields)
    hdr_len = 32 + 32 * len(fields) + 1
    dbf = bytearray(struct.pack("<BBBBIHH", 3, 126, 9, 20, len(pick), hdr_len, rec_len) + b"\x00" * 20)
    for name, ln in fields:
        dbf += name.encode().ljust(11, b"\x00") + b"C" + b"\x00" * 4 + bytes([ln, 0]) + b"\x00" * 14
    dbf += b"\x0d"
    for f in pick:
        dbf += b" "
        for name, ln in fields:
            v = f["properties"].get(keymap[name])
            dbf += ("" if v is None else str(v)).encode("utf-8")[:ln].ljust(ln, b" ")
    dbf += b"\x1a"
    body = b""
    shx = b""
    off = 50
    for i, f in enumerate(pick, 1):
        pts = f["geometry"]["coordinates"]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        content = struct.pack("<i4d2i", 3, min(xs), min(ys), max(xs), max(ys), 1, len(pts)) + struct.pack("<i", 0)
        content += b"".join(struct.pack("<2d", x, y) for x, y in pts)
        words = len(content) // 2
        body += struct.pack(">2i", i, words) + content
        shx += struct.pack(">2i", off, words)
        off += 4 + words
    allx = [p[0] for f in pick for p in f["geometry"]["coordinates"]]
    ally = [p[1] for f in pick for p in f["geometry"]["coordinates"]]

    def header(total_words):
        return struct.pack(">7i", 9994, 0, 0, 0, 0, 0, total_words) + struct.pack("<2i4d4d", 1000, 3, min(allx), min(ally), max(allx), max(ally), 0, 0, 0, 0)

    shp = header((100 + len(body)) // 2) + body
    shx_file = header((100 + len(shx)) // 2) + shx
    w("ibge_bc250", "rod_trecho_rodoviario_l.dbf", bytes(dbf))
    w("ibge_bc250", "rod_trecho_rodoviario_l.shp", shp)
    w("ibge_bc250", "rod_trecho_rodoviario_l.shx", shx_file)
    readme("ibge_bc250", f"""
# ibge_bc250 — BC250 `rod_trecho_rodoviario_l` (shapefile)
Origem: https://geoftp.ibge.gov.br/…/bc_250_shapefiles_2026_03_03.zip (761 MB; o coletor lê 3 membros por HTTP Range).
Os 3 arquivos (.shp/.shx/.dbf) são um shapefile **binário válido** gerado por `cut_fixtures.py` com 3 trechos reais
de `normalized/{DATE}/summary/ibge_rodovias.json.gz` (PolyLine, campos dBASE de 10 caracteres como o IBGE).
Os testes os empacotam em um ZIP servido com suporte a `Range`.
""")


def group_e() -> None:
    """BGP/MRT/telnet: updates reais do RouteViews, RIB TABLE_DUMP_V2 sintético e saída de LG real."""
    import bz2
    import struct

    # ── LG IX.br (Telnet): banner + cabeçalho + 12 linhas + rodapé, v4 e v6 reais ──
    for afi in ("v4", "v6"):
        txt = raw("sp", f"bgp-{afi}-sp-{DATE}.txt").read_text(encoding="utf-8", errors="replace").splitlines()
        end = next(i for i, l in enumerate(txt) if l.startswith("Displayed"))
        hdr = next(i for i, l in enumerate(txt) if "Network" in l and "Next Hop" in l)
        body = txt[hdr + 1: hdr + 1 + (24 if afi == "v6" else 12)]
        out = txt[: hdr + 1] + body + [""] + txt[end:end + 2]
        w("lg_ixbr", f"bgp-{afi}.sample.txt", "\n".join(out) + "\n")
    readme("lg_ixbr", f"""
# lg_ixbr — saída Telnet do Looking Glass do IX.br (FRR)
Origem: `lg.sp.ix.br`, comandos `show ip bgp` e `show bgp ipv6 unicast`, coletado em {DATE}. Recorte: banner e
cabeçalho reais, 12 (v4) / 24 (v6) linhas de rota e o rodapé `Displayed N routes…`. O IPv6 usa o formato de
2 linhas (prefixo/nexthop + caminho). O `Displayed` original reflete a tabela completa, não o recorte.
""")

    # ── MRT updates (BGP4MP_ET), bz2: 60 registros reais com origem em ASN brasileiro ──
    import mrtparse

    br = {a["asn"] for a in json.load(gzip.open(norm("summary", "registro_br.json.gz"), "rt"))["asns"]}
    rawmrt = bz2.decompress((raw("route-views.saopaulo") / "updates.20260913.0000.bz2").read_bytes())
    pos, kept = 0, []
    while pos + 12 <= len(rawmrt) and len(kept) < 60:
        ln = struct.unpack(">I", rawmrt[pos + 8: pos + 12])[0]
        rec = rawmrt[pos: pos + 12 + ln]
        pos += 12 + ln
        try:
            d = next(iter(mrtparse.Reader(io.BytesIO(rec)))).data
            asp = None
            for a in d.get("bgp_message", {}).get("path_attributes", []):
                if next(iter(a.get("type", {}))) == 2:
                    asp = [int(x) for sg in a["value"] for x in sg["value"]]
            if asp and asp[-1] in br:
                kept.append(rec)
        except Exception:
            continue
    w("bgp_updates", "updates.20260913.0000.sample.bz2", bz2.compress(b"".join(kept)))
    readme("bgp_updates", f"""
# bgp_updates — RouteViews route-views.saopaulo, arquivos `updates.AAAAMMDD.HHMM.bz2` (MRT BGP4MP_ET)
Origem: http://archive.routeviews.org/route-views.saopaulo/bgpdata/2026.09/UPDATES/ . Recorte: {len(kept)} registros
reais de `updates.20260913.0000.bz2` (de ~223) cujo AS de origem é brasileiro, recomprimidos em bz2.
""")

    # ── RIB TABLE_DUMP_V2 sintético (o RIB real tem >1 GB e não é retido) ──
    def mrt(subtype: int, payload: bytes, ts: int = 1789000000) -> bytes:
        return struct.pack(">IHHI", ts, 13, subtype, len(payload)) + payload

    def attr(flags: int, typ: int, val: bytes) -> bytes:
        return struct.pack(">BBB", flags, typ, len(val)) + val

    def attrs(path: list[int], comms: list[tuple[int, int]] | None = None, nexthop: bytes | None = None) -> bytes:
        a = attr(0x40, 1, b"\x00") + attr(0x40, 2, struct.pack(">BB", 2, len(path)) + b"".join(struct.pack(">I", x) for x in path))
        if nexthop:
            a += attr(0x40, 3, nexthop)
        if comms:
            a += attr(0xC0, 8, b"".join(struct.pack(">HH", x, y) for x, y in comms))
        return a

    def rib(subtype: int, seq: int, prefix: str, entries: list[bytes]) -> bytes:
        import ipaddress
        net = ipaddress.ip_network(prefix)
        nbytes = (net.prefixlen + 7) // 8
        body = struct.pack(">IB", seq, net.prefixlen) + net.network_address.packed[:nbytes] + struct.pack(">H", len(entries))
        for peer, a in entries:
            body += struct.pack(">HIH", peer, 1789000000, len(a)) + a
        return mrt(subtype, body)

    peers = struct.pack(">4sH", bytes([10, 0, 0, 1]), 3) + b"rv2" + struct.pack(">H", 2)
    for i, asn in enumerate((64496, 64497)):
        peers += struct.pack(">B4s4sI", 2, bytes([10, 0, 0, 10 + i]), bytes([192, 0, 2, 10 + i]), asn)
    pit = mrt(1, peers)
    v4 = pit + b"".join([
        rib(2, 0, "0.0.0.0/0", [(0, attrs([64496, 64500]))]),
        rib(2, 1, "198.51.100.0/24", [(0, attrs([64496, 64510], [(64510, 100)])), (1, attrs([64497, 64496, 64510]))]),
        rib(2, 2, "203.0.113.0/24", [(1, attrs([64497, 64511, 64511, 64511], [(64511, 200), (65535, 666)]))]),
        rib(2, 3, "192.0.2.0/25", [(0, attrs([64496, 64520]))]),
        rib(2, 4, "10.0.0.0/8", [(0, attrs([64496, 64530, 64540]))]),
    ])
    v6 = pit + b"".join([
        rib(4, 0, "2001:db8::/32", [(0, attrs([64496, 64510]))]),
        rib(4, 1, "2001:db8:1::/48", [(1, attrs([64497, 64511]))]),
    ])
    w("fulltable", "rib-v4.sample.mrt.bz2", bz2.compress(v4))
    w("fulltable", "rib-v6.sample.mrt.bz2", bz2.compress(v6))
    readme("fulltable", """
# fulltable — RouteViews/RIS RIB (MRT TABLE_DUMP_V2) — SINTÉTICO
Os dumps reais (`rib.AAAAMMDD.HHMM.bz2`, > 1 GB) não são retidos. Estas amostras são MRT TABLE_DUMP_V2 binários
válidos gerados por `cut_fixtures.py` (PEER_INDEX_TABLE + RIB_IPV4/IPV6_UNICAST) com prefixos de documentação
(RFC 5737/3849) e ASNs reservados (64496–64540): rota default (ignorada), prefixo com 2 caminhos, prepend, communities
padrão e um /8. É exatamente o formato que o `mrtparse` lê da fonte real.
""")


def group_f() -> None:
    """DB-IP City Lite: mmdb SINTÉTICO no formato da base (estado só pelo nome, cidade só em inglês, bairro como cidade)."""
    from mmdb_writer import MMDBWriter      # pip install mmdb-writer netaddr (só para gerar a amostra)
    from netaddr import IPSet

    wr = MMDBWriter(ip_version=6, database_type="DBIP-City-Lite", languages=["en"],
                    description={"en": "fixture sintetico do Arandurape"}, ipv4_compatible=True)

    def rec(city, estado, lat, lon):
        r = {"country": {"iso_code": "BR", "names": {"en": "Brazil"}},
             "location": {"latitude": lat, "longitude": lon},
             "subdivisions": [{"names": {"en": estado}}]}
        if city:
            r["city"] = {"names": {"en": city}}
        return r

    wr.insert_network(IPSet(["200.160.0.0/20"]), rec("Pinheiros", "São Paulo", -23.5611, -46.6876))    # bairro → município
    wr.insert_network(IPSet(["200.192.0.0/18"]), rec("Rio de Janeiro", "Rio de Janeiro", -22.91, -43.17))
    wr.insert_network(IPSet(["177.129.168.0/22"]), rec("", "Rio de Janeiro", -22.9, -43.2))             # sem cidade
    wr.insert_network(IPSet(["201.6.0.0/16"]), {"country": {"iso_code": "BR"}, "location": {}})       # sem coordenadas
    wr.insert_network(IPSet(["2804:8f8::/32"]), rec("Curitiba", "Paraná", -25.43, -49.27))
    wr.insert_network(IPSet(["8.8.8.0/24"]), {"country": {"iso_code": "US", "names": {"en": "United States"}},
                                              "city": {"names": {"en": "Mountain View"}},
                                              "location": {"latitude": 37.39, "longitude": -122.08},
                                              "subdivisions": [{"names": {"en": "California"}}]})
    d = OUT / "dbip"
    d.mkdir(parents=True, exist_ok=True)
    wr.to_db_file(str(d / "dbip-city-lite-2026-09.sample.mmdb"))
    print("  tests/fixtures/raw/dbip/dbip-city-lite-2026-09.sample.mmdb")
    readme("dbip", """
# dbip — DB-IP City Lite (mmdb) — SINTÉTICO
O banco real (~120 MB, CC BY 4.0, https://db-ip.com/db/download/ip-to-city-lite) é baixado sem chave. Esta amostra é um
**MMDB binário válido gerado por `cut_fixtures.py`** (biblioteca `mmdb-writer`) com o esquema do DB-IP: estado só pelo nome
(`subdivisions[].names.en`, sem `iso_code`), cidade só em inglês, bairro no lugar da cidade e coordenadas públicas de centros de
cidades; não contém registros do DB-IP. Redes: 200.160.0.0/20 (Pinheiros, São Paulo), 200.192.0.0/18 (Rio), 177.129.168.0/22
(sem cidade), 201.6.0.0/16 (sem coordenadas), 2804:8f8::/32 (Curitiba), 8.8.8.0/24 (EUA).
""")


def group_g() -> None:
    """Respostas de API usadas pelos enriquecedores: BrasilAPI (real), Nominatim e PeeringDB org (esquema)."""
    g = load_gz(norm("summary", "geo_orgs.json.gz"))["orgs"]
    keys = ("cnpj", "razao_social", "nome_fantasia", "logradouro", "descricao_tipo_de_logradouro", "numero", "complemento",
            "bairro", "municipio", "uf", "cep", "codigo_municipio", "codigo_municipio_ibge", "identificador_matriz_filial",
            "descricao_identificador_matriz_filial", "cnae_fiscal", "cnae_fiscal_descricao", "cnaes_secundarios",
            "situacao_cadastral", "descricao_situacao_cadastral", "motivo_situacao_cadastral",
            "descricao_motivo_situacao_cadastral", "natureza_juridica", "codigo_natureza_juridica", "porte",
            "codigo_porte", "data_inicio_atividade")
    out: dict = {}
    for o in g.values():
        if o.get("cnpj") and o.get("lat") is not None and o.get("logradouro") and o.get("geo_confidence") == "exact_address" and len(out) < 2:
            d = {k: o.get(k) for k in keys}
            d.update(cep=o.get("cep") or "", email="contato@example.org", ddd_telefone_1="1100000000", ddd_telefone_2="")
            out[o["cnpj"]] = d
    w("brasilapi", "cnpj.sample.json", json.dumps(out, ensure_ascii=False, indent=1))
    nom = [{"place_id": 123456, "licence": "Data © OpenStreetMap contributors, ODbL 1.0. http://osm.org/copyright",
            "osm_type": "way", "osm_id": 987654, "lat": "-23.5614", "lon": "-46.6558", "category": "building", "type": "yes",
            "place_rank": 30, "importance": 0.00000999, "addresstype": "building", "name": "",
            "display_name": "Avenida Paulista, Bela Vista, São Paulo, Brasil",
            "boundingbox": ["-23.5615", "-23.5613", "-46.6559", "-46.6557"]}]
    w("nominatim", "search.sample.json", json.dumps(nom, ensure_ascii=False, indent=1))
    orgs = {"data": [
        {"id": 9001, "name": "Org Exemplo Frankfurt", "city": "Frankfurt", "country": "DE", "latitude": 50.11, "longitude": 8.68, "status": "ok"},
        {"id": 9002, "name": "Org Exemplo Sem Coordenadas", "city": "Buenos Aires", "country": "AR", "latitude": None, "longitude": None, "status": "ok"},
        {"id": 9003, "name": "Org Exemplo Sem Cidade", "city": "", "country": "US", "latitude": None, "longitude": None, "status": "ok"}], "meta": {}}
    w("peeringdb", "org.sample.json", json.dumps(orgs, ensure_ascii=False, indent=1))


def load_gz(path: Path):
    return json.load(gzip.open(path, "rt", encoding="utf-8"))


GROUPS = {"a": group_a, "b": group_b, "c": group_c, "d": group_d, "e": group_e, "f": group_f, "g": group_g}


def main() -> None:
    global DATE
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=DATE)
    ap.add_argument("groups", nargs="*", default=list(GROUPS))
    a = ap.parse_args()
    DATE = a.date
    for g in a.groups:
        print(f"[grupo {g}]")
        GROUPS[g]()


if __name__ == "__main__":
    main()
