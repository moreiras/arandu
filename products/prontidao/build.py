# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Prontidão em segurança de roteamento por ASN. Saída: `published/{date}/prontidao/asns.json.gz`.

Quatro pilares (filtragem, anti-spoofing, coordenação e validação global), cada um com componentes de 0 a 100, pesos em `regras.yaml` (versionado) e uma classe (`pronto`, `em_progresso`, `atrasado` ou
`sem_dados`). Componente ou pilar sem dado sai da conta e o índice diz quais pilares entraram: o anti-spoofing, por exemplo, só existe para os ASNs com testes do Spoofer. O índice é um conjunto de **medições e
fatos de terceiros** com fonte e data; não é veredito sobre a empresa nem usa o nome de nenhuma iniciativa. Agregados por UF, porte (usuários estimados do APNIC) e operadora ponderam pelos usuários estimados do APNIC.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Optional

import yaml

from core import compose
from core.common import configure_logging, data_dir, normalized_path, now_iso, published_path, today_str
from core.jsonio import carregar_json_gz, gravar_json_gz
from core.prontidao_agregado import CLASSES, COMPONENTES, agregar, medicoes  # noqa: F401  (reexportados: usados por MANRS e testes)
from products.seguranca.build import faixa_porte

REGRAS_PATH = Path(__file__).with_name("regras.yaml")
LIMITES = (
    "Índice de prontidão: soma ponderada de medições e fatos de terceiros (APNIC, CAIDA, RPKI, IRR, PeeringDB), cada um com fonte e data. Não é veredito sobre a empresa. ROV e DNSSEC são amostragens do APNIC; o Spoofer "
    "é voluntário e cobre pouco mais de 2% dos ASNs brasileiros; objeto IRR documenta política e pode ter sido criado por terceiro; ASPA é adoção inicial e só conta a favor. ASN sem dados suficientes fica `sem_dados`. "
    "Mudar os pesos muda o índice: a versão das regras acompanha o arquivo."
)


def carregar_regras(path: Path = REGRAS_PATH) -> dict:
    texto = path.read_text(encoding="utf-8")
    r = yaml.safe_load(texto)
    r["hash"] = hashlib.sha256(texto.encode()).hexdigest()[:12]
    return r


def _pct(parte: int, total: int) -> Optional[float]:
    return round(100 * parte / total, 1) if total else None


def componentes(asn: int, doc: dict, seg: dict, spoofer: dict, irr: dict, aspas: set[int], regras: dict) -> dict[str, dict[str, Optional[dict]]]:
    """Valores (0 a 100) e detalhe de cada componente, por pilar; `None` = sem dado. Funções puras sobre os dados do ASN."""
    prefixos = set(doc.get("prefixos") or [])
    val = doc.get("rpki_validation") or {}
    s = seg.get(str(asn)) or {}
    out: dict[str, dict[str, Optional[dict]]] = {p: {} for p in regras["pilares"]}
    rov = s.get("rov")
    min_rov = regras["minimos"]["amostras_rov"]
    out["filtragem"]["rov"] = {"valor": rov["validates_pct"], "detalhe": {"amostras": rov["amostras"]}} if rov and rov.get("amostras", 0) >= min_rov and rov.get("validates_pct") is not None else None
    n_bogon = s.get("n_prefixos_bogon", 0)
    out["filtragem"]["sem_bogon"] = ({"valor": 0.0 if n_bogon or s.get("asn_reservado") else 100.0, "detalhe": {"prefixos_em_bogon": n_bogon, "asn_reservado": s.get("asn_reservado")}}
                                     if prefixos or s.get("asn_reservado") else None)
    sp = spoofer.get(str(asn))
    out["anti_spoofing"]["spoofer"] = ({"valor": sp["pct_bloqueado"], "detalhe": {"conclusivas": sp["conclusivas"], "sessoes": sp["sessoes"], "ultima_sessao": sp["ultima_sessao"]}}
                                       if sp and sp.get("suficiente") and sp.get("pct_bloqueado") is not None else None)
    registrado = bool(doc.get("pdb_registered"))
    out["coordenacao"]["peeringdb"] = {"valor": 100.0 if registrado else 0.0, "detalhe": None}
    out["coordenacao"]["irr_aut_num"] = {"valor": 100.0 if asn in irr["aut_num"] else 0.0, "detalhe": {"irr": sorted(n for n, l in irr["aut_num_por_irr"].items() if asn in l)}}
    as_set = ((doc.get("pdb") or {}).get("irr_as_set") or "").strip()
    out["coordenacao"]["irr_as_set"] = {"valor": 100.0 if as_set else 0.0, "detalhe": {"as_set": as_set or None}} if registrado else None
    validos = sum(1 for p in prefixos if val.get(p) == "valid")
    avaliados = sum(1 for p in prefixos if p in val)
    out["validacao_global"]["roa"] = {"valor": _pct(validos, avaliados), "detalhe": {"prefixos": avaliados, "validos": validos, "invalidos": sum(1 for p in prefixos if val.get(p) == "invalid")}} if avaliados else None
    cobertos = irr["rotas"].get(asn, set()) & prefixos
    out["validacao_global"]["irr"] = {"valor": _pct(len(cobertos), len(prefixos)), "detalhe": {"prefixos": len(prefixos), "com_objeto": len(cobertos)}} if prefixos else None
    out["validacao_global"]["aspa"] = {"valor": 100.0, "detalhe": None} if asn in aspas else None
    return out


def pontuar(comps: dict[str, dict[str, Optional[dict]]], regras: dict) -> dict:
    """Pilares com dado, índice (0 a 100, uma casa) e classe. Pesos de componentes e de pilares se renormalizam pelo que existe."""
    pilares: dict[str, dict] = {}
    for p, cfg in regras["pilares"].items():
        itens = {c: v for c, v in comps[p].items() if v is not None and v.get("valor") is not None}
        if not itens or any(c not in itens for c in cfg.get("requer", [])):
            continue
        peso_c = sum(cfg["componentes"][c]["peso"] for c in itens)
        score = sum(v["valor"] * cfg["componentes"][c]["peso"] for c, v in itens.items()) / peso_c
        pilares[p] = {"score": round(score, 1), "peso": cfg["peso"], "componentes": {c: {**v, "peso": cfg["componentes"][c]["peso"]} for c, v in itens.items()}}
    sem_dado = [p for p in regras["pilares"] if p not in pilares]
    if len(pilares) < regras["minimos"]["pilares"]:
        return {"total": None, "classe": "sem_dados", "pilares": pilares, "pilares_sem_dado": sem_dado}
    peso_p = sum(v["peso"] for v in pilares.values())
    total = round(sum(v["score"] * v["peso"] for v in pilares.values()) / peso_p, 1)
    cl = regras["classes"]
    classe = "pronto" if total >= cl["pronto"] else "em_progresso" if total >= cl["em_progresso"] else "atrasado"
    return {"total": total, "classe": classe, "pilares": pilares, "pilares_sem_dado": sem_dado}


def calcular(docs: dict[int, dict], seg: dict, spoofer: dict, irr_doc: Optional[dict], aspas: set[int], regras: dict, acessos_por_cnpj: Optional[dict] = None) -> dict:
    """`docs`: {asn: {uf, cnpj, prefixos, rpki_validation, pdb_registered, pdb, usuarios}} dos ASNs do Brasil."""
    irr = {"rotas": defaultdict(set), "aut_num": set(), "aut_num_por_irr": {}}
    for nome, rotas in ((irr_doc or {}).get("rotas") or {}).items():
        for a, ps in rotas.items():
            irr["rotas"][int(a)] |= set(ps)
    for nome, lista in ((irr_doc or {}).get("aut_num") or {}).items():
        irr["aut_num"] |= set(lista)
        irr["aut_num_por_irr"][nome] = set(lista)
    asns: dict[str, dict] = {}
    for a, d in sorted(docs.items()):
        r = pontuar(componentes(a, d, seg, spoofer, irr, aspas, regras), regras)
        s = seg.get(str(a)) or {}
        asns[str(a)] = {**r, "uf": d.get("uf"), "cnpj": d.get("cnpj"), "faixa_porte": faixa_porte(d.get("usuarios")), "faixa_acessos_sici": s.get("faixa_acessos_sici"), "usuarios": d.get("usuarios") or 0}
    uf = {a: d["uf"] for a, d in asns.items() if d["uf"]}
    porte = {a: d["faixa_porte"] for a, d in asns.items() if d["faixa_porte"]}
    op = {a: d["cnpj"][:8] for a, d in asns.items() if d["cnpj"]}
    return {"asns": asns, "brasil": agregar(asns, {a: "BR" for a in asns}).get("BR", {}), "por_uf": agregar(asns, uf), "por_faixa_porte": agregar(asns, porte), "por_operadora": agregar(asns, op)}


def _doc_resumido(d: dict) -> dict:
    return {"uf": ((d.get("geo_org") or {}).get("uf") or None), "cnpj": d.get("cnpj") or None, "prefixos": sorted(set((d.get("global_prefixes_v4") or []) + (d.get("global_prefixes_v6") or []))),
            "rpki_validation": d.get("rpki_validation") or {}, "pdb_registered": bool(d.get("pdb_registered")), "pdb": {"irr_as_set": (d.get("pdb") or {}).get("irr_as_set")} if d.get("pdb") else None,
            "usuarios": int(d.get("apnic_users") or 0)}


def _docs_br(base: Path, date_str: str) -> dict[int, dict]:
    """ASNs do Brasil com os campos do índice. No fluxo de fragmentos o documento final só existe depois do compose, então lê `base` + `saude` (rpki_validation); no antigo lê os documentos publicados."""
    if compose.ativo() and compose.fluxo_novo(base, date_str):
        return {asn: _doc_resumido(d) for asn, d in compose.iterar_documentos(base, date_str, ("base", "saude")) if d.get("is_br")}
    pub = published_path(base, date_str)
    idx = json.loads((pub / "asns" / "index.json").read_text(encoding="utf-8")) if (pub / "asns" / "index.json").exists() else []
    out: dict[int, dict] = {}
    for e in idx:
        p = pub / "asns" / f"{e['asn']}.json"
        if e.get("is_br") and p.exists():
            out[e["asn"]] = _doc_resumido(json.loads(p.read_text(encoding="utf-8")))
    return out


def _aspas(pub: Path) -> set[int]:
    doc = carregar_json_gz(pub / "rpki" / "aspa_list.json.gz") or {}
    itens = doc if isinstance(doc, list) else (doc.get("aspas") or doc.get("items") or doc.get("aspa") or [])
    return {int(x.get("customer_asid") or x.get("customer") or x.get("asn")) for x in itens if isinstance(x, dict) and (x.get("customer_asid") or x.get("customer") or x.get("asn"))}


def publicar_prontidao(base: Path, date_str: str, log) -> dict:
    pub = published_path(base, date_str)
    norm = normalized_path(base, date_str, "summary")
    seg = carregar_json_gz(pub / "seguranca" / "asns.json.gz") or {}
    spoofer = carregar_json_gz(norm / "caida_spoofer.json.gz") or {}
    irr = carregar_json_gz(norm / "irr_route_objects.json.gz")
    if not seg.get("asns"):
        log.info("seguranca/asns.json.gz ausente: prontidao não gerada")
        return {}
    docs = _docs_br(base, date_str)
    if not docs:
        log.info("documentos de ASN ausentes: prontidao não gerada")
        return {}
    regras = carregar_regras()
    r = calcular(docs, seg["asns"], spoofer.get("asns") or {}, irr, _aspas(pub), regras)
    destino = pub / "prontidao"
    destino.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "asns.json.gz", {
        "snapshot_date": date_str, "generated_at": now_iso(), "natureza": "indice_composto", "limites": LIMITES,
        "regras": {"versao": regras["versao"], "hash": regras["hash"], "pilares": {p: {"nome": c["nome"], "peso": c["peso"], "descricao": c["descricao"],
                                                                                         "requer": c.get("requer", []), "componentes": c["componentes"]} for p, c in regras["pilares"].items()},
                   "minimos": regras["minimos"], "classes": regras["classes"]},
        "fontes": {"spoofer": {"fonte": "CAIDA Spoofer", "citacao": spoofer.get("citacao"), "janela": (spoofer.get("resumo") or {}).get("janela")},
                   "irr": {"fonte": "TC IRR e RADB", "citacao": (irr or {}).get("citacao"), "serial": {n: f.get("serial") for n, f in ((irr or {}).get("fontes") or {}).items()}},
                   "seguranca": {"fonte": "produto seguranca_asn (APNIC iROV, bogons)", "snapshot": seg.get("snapshot_date")}},
        **r})
    c = r["brasil"]
    log.info("prontidao written", asns=len(r["asns"]), classes=c.get("classes"))
    return {"asns": len(r["asns"]), "com_indice": c.get("asns_com_indice"), "classes": c.get("classes")}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Prontidão em segurança de roteamento por ASN")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; o índice é sempre recalculado")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        publicar_prontidao(data_dir(), a.date, log)
    except Exception:
        log.exception("falha no cálculo da prontidão")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
