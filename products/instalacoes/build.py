# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Instalações do PeeringDB. Saídas em `published/{date}/instalacoes/`:

  * `instalacoes.json.gz`: instalações (datacenters, pontos de interconexão) do Brasil e as dos PTTs externos cadastrados, com PTTs, carriers, campus e o indicador
    de "cadastro vivo ou abandonado";
  * `vinculos.json.gz`: redes por instalação e instalações por ASN (`netfac`);
  * `atributos_rede.json.gz`: atributos de peering das redes do Brasil no PeeringDB (escopo, IPv6, multicast, looking glass, route server) e a mesma leitura de cadastro;
  * `portas_externas.json.gz`: portas (velocidade declarada) nos PTTs externos, por PTT e por ASN do Brasil;
  * `portas_ixbr.json.gz`: portas declaradas no PeeringDB pelos participantes de cada PTT do IX.br, por ASN.

Tudo é cadastro **autodeclarado** de organizações no PeeringDB. O indicador de cadastro é INFERÊNCIA a partir de datas de atualização: mede a manutenção do registro, não a
operação da instalação nem da empresa (sem veredito). Nenhum contato entra aqui (o coletor já os descarta). Sem ranking.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core.common import load_peeringdb_ixps_config, normalized_path, now_iso, published_path
from core.jsonio import carregar_json, carregar_json_gz, gravar_json_gz

# Limiares do indicador de cadastro (dias desde a última atualização de qualquer registro da instalação ou da rede no PeeringDB).
LIMITE_RECENTE_DIAS = 365
LIMITE_PARADO_DIAS = 1095
ROTULOS_CADASTRO = {"recente": "atualizado nos últimos 12 meses", "parado": "sem atualização há 1 a 3 anos", "antigo": "sem atualização há mais de 3 anos"}

LIMITES = ("Cadastro autodeclarado por organizações no PeeringDB, sem verificação independente: instalação ou vínculo (rede, PTT, carrier) pode faltar, sobrar ou estar desatualizado. "
           "Contagens `*_declaradas` são as que o próprio cadastro informa; `n_redes` conta os vínculos que o Arandurapé coletou (só instalações do Brasil). Instalações de outros países "
           "estão aqui só porque abrigam PTTs externos cadastrados no Arandurapé. O indicador `cadastro` é inferência a partir das datas de atualização do registro e mede a manutenção do "
           "cadastro, não a operação da instalação nem da empresa. Contatos do PeeringDB não são coletados.")
LIMITES_PORTAS = ("Velocidade de porta declarada no PeeringDB (netixlan) dos PTTs externos cadastrados; um membro pode ter várias portas. A soma das velocidades é capacidade contratada "
                  "declarada, não tráfego nem utilização. Só PTTs externos: o PeeringDB não é a fonte das portas do IX.br neste passo. Cadastro autodeclarado.")
LIMITES_PORTAS_IXBR = ("Velocidade de porta declarada pelo próprio participante no PeeringDB (netixlan) para o PTT do IX.br; pode estar desatualizada ou faltar (0 = não informada). "
                      "Não é a porta contratada no IX.br nem tráfego. Um participante pode ter várias portas. Cadastro autodeclarado.")
LIMITES_ATRIBUTOS = ("Atributos autodeclarados pela rede no PeeringDB; podem estar desatualizados. URL de looking glass e de route server é a informada pela rede, sem verificação de que "
                     "responde. Só redes do Brasil que têm registro no PeeringDB.")


def _dt(v: Optional[str]) -> Optional[date]:
    if not v:
        return None
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def classe_cadastro(datas: list[Optional[str]], hoje: date) -> Optional[dict]:
    """Leitura de 'cadastro vivo ou abandonado' pela data mais recente entre `datas` (ISO); None se nenhuma data existe. Inferido."""
    ds = [d for d in (_dt(x) for x in datas) if d]
    if not ds:
        return None
    ultima = max(ds)
    dias = max((hoje - ultima).days, 0)
    classe = "recente" if dias <= LIMITE_RECENTE_DIAS else "parado" if dias <= LIMITE_PARADO_DIAS else "antigo"
    return {"ultima_atualizacao": ultima.isoformat(), "dias": dias, "classe": classe, "rotulo": ROTULOS_CADASTRO[classe], "inferido": True}


def _ptts(ixps_doc: dict, cfg: dict, ixps_pdb: dict) -> dict[int, dict]:
    """{pdb_ix_id: {code, nome, tipo}} dos PTTs que o Arandurapé conhece, do `peeringdb_ixps` do próprio snapshot (a config completa o nome); os demais PTTs do PeeringDB entram só com o nome do cadastro."""
    nome_cfg = {i["code"]: i.get("name") for i in cfg["ixbr"] + cfg["external"]}
    out: dict[int, dict] = {}
    for code, x in (ixps_doc.get("ixbr_ixps") or {}).items():
        if x.get("pdb_ix_id"):
            out[int(x["pdb_ix_id"])] = {"code": code, "nome": nome_cfg.get(code), "tipo": "ixbr"}
    for code, x in (ixps_doc.get("external_ixps") or {}).items():
        if x.get("pdb_ix_id"):
            out[int(x["pdb_ix_id"])] = {"code": code, "nome": x.get("name") or nome_cfg.get(code), "tipo": "externo"}
    for k, v in ixps_pdb.items():
        out.setdefault(int(k), {"code": None, "nome": v.get("nome"), "tipo": "outro"})
    return out


def calcular_instalacoes(doc: dict, ptts: dict[int, dict], hoje: date, nomes: dict[str, dict]) -> tuple[dict, dict]:
    """(instalacoes, vinculos): o documento de `instalacoes.json.gz` (sem cabeçalho) e o de `vinculos.json.gz`."""
    facs = doc["facilities"]
    por_inst: dict[str, list] = defaultdict(list)
    por_asn: dict[str, list] = defaultdict(list)
    for fid, asn, criado, atualizado in doc["netfac"]:
        por_inst[str(fid)].append([asn, criado, atualizado])
        por_asn[str(asn)].append([fid, criado, atualizado])
    ixps_de: dict[str, list] = defaultdict(list)
    for fid, ix in doc["ixfac"]:
        p = ptts.get(ix, {"code": None, "nome": None, "tipo": "outro"})
        ixps_de[str(fid)].append({"ix_id": ix, **{k: v for k, v in p.items() if v is not None}})
    carriers_de: dict[str, list] = defaultdict(list)
    for cid, fid in doc["carrierfac"]:
        carriers_de[str(fid)].append(cid)
    saida = {}
    for fid, f in facs.items():
        no_brasil = f.get("pais") == "BR"
        vinc = por_inst.get(fid, [])
        d = {**f, "escopo": "brasil" if no_brasil else "ptt_externo",
             "ixps": sorted(ixps_de.get(fid, []), key=lambda x: (x.get("code") or "~", x["ix_id"])), "carriers": sorted(carriers_de.get(fid, []))}
        if no_brasil:
            d["n_redes"] = len(vinc)
            d["n_redes_br"] = sum(1 for a, *_ in vinc if nomes.get(str(a), {}).get("is_br"))
        cad = classe_cadastro([f.get("atualizado"), *(v[2] for v in vinc)], hoje)
        if cad:
            ult_v = max((v[2] for v in vinc if v[2]), default=None)
            d["cadastro"] = {**cad, "registro_atualizado": (f.get("atualizado") or "")[:10] or None, "vinculo_atualizado": (ult_v or "")[:10] or None}
        saida[fid] = d
    vinculos = {"por_instalacao": {k: sorted(v) for k, v in por_inst.items()},
                "por_asn": {k: sorted(v) for k, v in sorted(por_asn.items(), key=lambda kv: int(kv[0]))},
                "redes": {str(a): nomes[str(a)] for a in sorted({int(x[0]) for v in por_inst.values() for x in v}) if str(a) in nomes}}
    return saida, vinculos


def calcular_cobertura(instalacoes: dict, vinculos: dict, ptts: dict[int, dict], doc: dict, n_asns_br: int, br_pdb: set[int]) -> dict:
    br = [f for f in instalacoes.values() if f["escopo"] == "brasil"]
    com_ix = {ix for _, ix in doc["ixfac"]}
    ixbr = [i for i, p in ptts.items() if p["tipo"] == "ixbr"]
    ext = [i for i, p in ptts.items() if p["tipo"] == "externo"]
    asns_com_fac = {int(a) for a in vinculos["por_asn"]}
    classes = defaultdict(int)
    for f in br:
        classes[(f.get("cadastro") or {}).get("classe", "sem_data")] += 1
    return {
        "instalacoes_br": len(br), "instalacoes_ptt_externo": len(instalacoes) - len(br),
        "com_coordenadas": sum(1 for f in br if f.get("lat") is not None and f.get("lon") is not None),
        "com_ptt": sum(1 for f in br if f["ixps"]), "com_carrier": sum(1 for f in br if f["carriers"]), "em_campus": sum(1 for f in br if f.get("campus_id")),
        "ptts_ixbr": len(ixbr), "ptts_ixbr_com_instalacao": sum(1 for i in ixbr if i in com_ix),
        "ptts_ixbr_sem_instalacao": sorted(ptts[i]["code"] for i in ixbr if i not in com_ix),
        "ptts_externos": len(ext), "ptts_externos_com_instalacao": sum(1 for i in ext if i in com_ix),
        "asns_br": n_asns_br, "asns_br_no_peeringdb": len(br_pdb), "asns_br_com_instalacao": len(asns_com_fac & br_pdb) if br_pdb else None,
        "asns_com_instalacao_total": len(asns_com_fac),
        "cadastro_br": dict(classes), "carriers": len(doc["carriers"]), "campus": len(doc["campus"]),
    }


def calcular_atributos(doc: dict, hoje: date, br_pdb: set[int]) -> dict:
    asns = {}
    for a, r in doc["redes"].items():
        d = dict(r)
        cad = classe_cadastro([r.get("atualizado"), r.get("portas_atualizadas"), r.get("instalacoes_atualizadas")], hoje)
        if cad:
            d["cadastro"] = cad
        asns[a] = d
    return asns


def calcular_portas(doc_ixps: dict, br_pdb_asns: set[int]) -> dict:
    """Portas por PTT externo (distribuição por velocidade) e por ASN do Brasil. `members` do peeringdb_ixps é uma linha por porta (netixlan)."""
    ixps, por_asn = {}, defaultdict(dict)
    for code, x in sorted((doc_ixps.get("external_ixps") or {}).items()):
        vel = [m["speed"] for m in x.get("members", []) if m.get("speed")]
        hist: dict[str, int] = defaultdict(int)
        for v in vel:
            hist[str(v)] += 1
        ixps[code] = {"nome": x.get("name"), "cidade": x.get("city"), "pais": x.get("country"), "pdb_ix_id": x.get("pdb_ix_id"),
                      "portas": len(x.get("members", [])), "portas_com_velocidade": len(vel), "membros": len({m["asn"] for m in x.get("members", [])}),
                      "capacidade_mbps": sum(vel), "mediana_mbps": int(statistics.median(vel)) if vel else None, "maior_mbps": max(vel) if vel else None,
                      "por_velocidade": dict(sorted(hist.items(), key=lambda kv: int(kv[0])))}
        for m in x.get("members", []):
            if m.get("speed") and int(m["asn"]) in br_pdb_asns:
                por_asn[str(m["asn"])].setdefault(code, []).append(m["speed"])
    return {"ixps": ixps, "por_asn": {k: {c: sorted(v) for c, v in d.items()} for k, d in sorted(por_asn.items(), key=lambda kv: int(kv[0]))}}


def calcular_portas_ixbr(doc_ixps: dict) -> dict:
    """Portas declaradas no PeeringDB por PTT do IX.br e ASN: {code: {asn: [Mbps, ...]}}. Vazio quando o
    normalizado é anterior ao campo `portas` (só tinha a lista de ASNs)."""
    out: dict[str, dict[str, list[int]]] = {}
    for code, x in sorted((doc_ixps.get("ixbr_ixps") or {}).items()):
        if "portas" not in x:
            continue
        por: dict[str, list[int]] = defaultdict(list)
        for asn, vel in x["portas"]:
            por[str(asn)].append(int(vel or 0))
        out[code] = {a: sorted(v, reverse=True) for a, v in sorted(por.items(), key=lambda kv: int(kv[0]))}
    return out


def publicar_instalacoes(base: Path, date_str: str, log) -> dict:
    doc = carregar_json_gz(normalized_path(base, date_str, "summary") / "peeringdb_fac.json.gz")
    if not doc:
        log.info("peeringdb_fac.json.gz ausente: instalacoes não gerado")
        return {}
    hoje = _dt(doc.get("fetched_at")) or date.fromisoformat(date_str)           # a idade do cadastro conta até o dia da coleta (o PeeringDB só dá o estado de agora)
    ixps_doc = carregar_json_gz(normalized_path(base, date_str, "summary") / "peeringdb_ixps.json.gz") or {}
    ptts = _ptts(ixps_doc, load_peeringdb_ixps_config(), doc.get("ixps") or {})
    idx = carregar_json(published_path(base, date_str) / "asns" / "index.json", []) or []
    nomes = {str(e["asn"]): {"nome": e.get("name"), "is_br": bool(e.get("is_br"))} for e in idx}
    br_pdb = {int(a) for a in doc["redes"] if nomes.get(a, {}).get("is_br")} if nomes else {int(a) for a in doc["redes"]}
    n_br = sum(1 for e in idx if e.get("is_br"))
    instalacoes, vinculos = calcular_instalacoes(doc, ptts, hoje, nomes)
    cobertura = calcular_cobertura(instalacoes, vinculos, ptts, doc, n_br, br_pdb)
    fonte = {"nome": "PeeringDB", "url": "https://www.peeringdb.com", "citacao": doc.get("citacao"), "aup": "https://www.peeringdb.com/aup"}
    cab = {"snapshot_date": date_str, "generated_at": now_iso(), "coletado_em": doc.get("fetched_at"), "fonte": fonte}
    destino = published_path(base, date_str) / "instalacoes"
    destino.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "instalacoes.json.gz", {**cab, "limites": LIMITES, "cobertura": cobertura, "instalacoes": instalacoes, "carriers": doc["carriers"], "campus": doc["campus"],
                                                    "limiares_cadastro_dias": {"recente": LIMITE_RECENTE_DIAS, "parado": LIMITE_PARADO_DIAS}})
    gravar_json_gz(destino / "vinculos.json.gz", {**cab, "limites": LIMITES, **vinculos})
    gravar_json_gz(destino / "atributos_rede.json.gz", {**cab, "limites": LIMITES_ATRIBUTOS, "asns": calcular_atributos(doc, hoje, br_pdb)})
    portas = calcular_portas(ixps_doc, br_pdb or {int(a) for a in doc["redes"]})
    gravar_json_gz(destino / "portas_externas.json.gz", {**cab, "fonte": {**fonte, "nome": "PeeringDB (netixlan)", "coletado_em": ixps_doc.get("generated_at")}, "limites": LIMITES_PORTAS, **portas})
    portas_ixbr = calcular_portas_ixbr(ixps_doc)
    if portas_ixbr:
        gravar_json_gz(destino / "portas_ixbr.json.gz", {**cab, "fonte": {**fonte, "nome": "PeeringDB (netixlan)", "coletado_em": ixps_doc.get("generated_at")},
                                                        "limites": LIMITES_PORTAS_IXBR, "ptts": portas_ixbr})
    log.info("instalacoes published", instalacoes=len(instalacoes), asns_com_instalacao=cobertura["asns_com_instalacao_total"], ptts_ixbr_pct=cobertura["ptts_ixbr_com_instalacao"])
    return {"instalacoes": len(instalacoes), "instalacoes_br": cobertura["instalacoes_br"], "asns_com_instalacao": cobertura["asns_com_instalacao_total"]}
