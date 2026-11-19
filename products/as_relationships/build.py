# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Produto `as_relationships`: relações entre ASNs inferidas (ARC v1), com probabilidade, nível e evidência.

Entradas (normalized/{date}/…, com recuo para a data anterior mais recente quando a do dia não tem o arquivo):
  {ptt}/routes-{afi}.json.gz               rampa dos route servers do IX.br
  summary/aspaths-{afi}/{coletor}.tsv.gz   caminhos únicos com VP dos coletores (opcional)
  summary/caida_asrel.json.gz              prior e régua (opcional)
  summary/registro_br.json.gz              ASNs brasileiros (filtro dos elos) e CNPJ (irmãos)
  published/{date}/rpki/aspa_list.json.gz  objetos ASPA
  summary/caida_as2org.json.gz            organização por ASN (irmãos) — opcional
  published/{date}/rs_policy/*.json.gz     perfil de política e restrições declaradas no IX.br — opcional
Saída: published/{date}/as_relationships.json.gz — um registro por elo {a, b, tipo, p, nivel, afi, evid, n_vps, n_ptt, visto_em}.
`tipo` = p2c (a é provedor de b) | p2p | s2s | complexa | sem_classificacao. Só elos com ao menos um ASN brasileiro.
ARC v2: refino probabilístico (refino.py), irmãos/ciclos/complexa (restricoes.py) e histerese (estabilidade.py)."""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Iterator, Optional

from core import compose
from core.common import (configure_logging, data_dir, normalized_path, now_iso, published_path, read_json_gz, today_str,
                         write_json_gz)
from products.as_relationships import arc, estabilidade, irr_relacao, refino, restricoes
from products.as_relationships.config import carregar
from sources.fulltable_routeviews import caminhos as cm

AFIS = ("v4", "v6")


def _datas_ate(base: Path, date_str: str) -> list[str]:
    raiz = base / "normalized"
    ds = sorted((d.name for d in raiz.iterdir() if d.is_dir() and len(d.name) == 10 and d.name <= date_str), reverse=True) if raiz.exists() else []
    return ds or [date_str]


def _achar(base: Path, date_str: str, *partes: str) -> Optional[Path]:
    """Arquivo de normalized/{data}/… da data pedida ou da mais recente anterior que o tenha."""
    for d in _datas_ate(base, date_str):
        p = normalized_path(base, d, *partes)
        if p.exists():
            return p
    return None


def _ptts_com_rotas(base: Path, date_str: str, afi: str) -> list[tuple[str, Path]]:
    """(ptt, arquivo de rotas) da data mais recente (≤ date_str) que tenha rotas de route server."""
    for d in _datas_ate(base, date_str):
        raiz = base / "normalized" / d
        achados = [(p.name, p / f"routes-{afi}.json.gz") for p in sorted(raiz.iterdir()) if p.is_dir() and (p / f"routes-{afi}.json.gz").exists()]
        if achados:
            return achados
    return []


def _rs(base: Path, date_str: str, afi: str) -> Iterator[tuple[list[int], str]]:
    for ptt, arq in _ptts_com_rotas(base, date_str, afi):
        for r in (read_json_gz(arq) or {}).get("routes", []):
            if r.get("aspath"):
                yield r["aspath"], ptt


MAX_IDADE_COLETORES_DIAS = 10        # a coleta dos RIBs é semanal; além disto os caminhos são velhos demais para valer


def _dir_colecao(base: Path, date_str: str, afi: str) -> tuple[Optional[Path], Optional[str]]:
    """Diretório `aspaths-{afi}` da data ou, nos dias em que a coleta dos coletores não rodou (cadência semanal), o da mais recente
    anterior (até MAX_IDADE_COLETORES_DIAS). Devolve (diretório, data de onde veio)."""
    import datetime as dt

    limite = dt.date.fromisoformat(date_str) - dt.timedelta(days=MAX_IDADE_COLETORES_DIAS)
    for d in _datas_ate(base, date_str):
        if dt.date.fromisoformat(d) < limite:
            break
        pasta = normalized_path(base, d, "summary") / f"aspaths-{afi}"
        if pasta.is_dir() and any(pasta.glob("*.tsv.gz")):
            return pasta, d
    return None, None


def _colecao(base: Path, date_str: str, afi: str):
    pasta, de = _dir_colecao(base, date_str, afi)
    if pasta is None:
        return None, [], None
    arqs = sorted(pasta.glob("*.tsv.gz"))

    def abrir():
        for a in arqs:
            for c in cm.ler(a):
                yield c.asns, c.n_vps, c.vp0

    return abrir, [a.name.removesuffix(".tsv.gz") for a in arqs], de


def _estrato(v) -> dict:
    """`estrato` e `p_calibrada` da linha, lidos da evidência da família de maior nível; ausentes se o elo não é p2c."""
    e = (v.evid or {}).get("estrato")
    return {"estrato": e["classe"], "p_calibrada": e.get("p_calibrada")} if e else {}


def _juntar(por_afi: dict[str, list]) -> list[dict]:
    """Une os vereditos de v4 e v6: mesma relação → uma linha com os dois AFIs; relação diferente → duas linhas marcadas."""
    ordem = {"declarado": 4, "confirmado": 3, "provavel": 2, "possivel": 1, "sem_classificacao": 0}
    por_elo: dict[tuple[int, int], dict[str, object]] = {}
    for afi, vs in por_afi.items():
        for v in vs:
            por_elo.setdefault((min(v.a, v.b), max(v.a, v.b)), {})[afi] = v
    linhas = []
    for (x, y), d in sorted(por_elo.items()):
        com = {afi: v for afi, v in d.items() if v.tipo != "sem_classificacao"}
        if not com:                                                      # nenhuma família classificou: uma linha só
            v = next(iter(d.values()))
            linhas.append({"a": v.a, "b": v.b, "tipo": v.tipo, "p": v.p, "nivel": v.nivel, "afi": sorted(d), "evid": v.evid,
                           "n_vps": v.n_vps, "n_ptt": v.n_ptt})
            continue
        vs = list(com.items())
        assinatura = {(v.tipo, v.a, v.b) for _, v in vs}
        if len(assinatura) == 1:                                         # as famílias concordam: a evidência de uma corrobora a outra
            v0 = max((v for _, v in vs), key=lambda v: (ordem[v.nivel], v.p))
            evid = {afi: v.evid for afi, v in vs} if len(vs) > 1 else v0.evid
            linhas.append({"a": v0.a, "b": v0.b, "tipo": v0.tipo, "p": v0.p, "nivel": v0.nivel, "afi": sorted(com), "evid": evid,
                           "n_vps": max(v.n_vps for _, v in vs), "n_ptt": max(v.n_ptt for _, v in vs), **_estrato(v0)})
        else:
            for afi, v in vs:
                linhas.append({"a": v.a, "b": v.b, "tipo": v.tipo, "p": v.p, "nivel": v.nivel, "afi": [afi], "evid": v.evid,
                               "n_vps": v.n_vps, "n_ptt": v.n_ptt, "afi_divergente": True, **_estrato(v)})
    return linhas


def _organizacoes(base: Path, date_str: str) -> dict[int, str]:
    """{asn: org_id} da organização do CAIDA (`as2org`); vazio se a fonte não foi coletada."""
    p = _achar(base, date_str, "summary", "caida_as2org.json.gz")
    doc = read_json_gz(p) if p else None
    return {int(a): str(o["org_id"]) for a, o in ((doc or {}).get("asns") or {}).items() if o.get("org_id")}


PERFIL = {"aberto": "A", "seletivo": "S", "restritivo": "R"}


def _politica(base: Path, date_str: str) -> tuple[dict[int, str], dict[tuple[int, int], str]]:
    """(perfil por ASN, restrição declarada por par) do `rs_policy` do snapshot; cobertura pequena (PTTs e rodízio da coleta)."""
    perfil: dict[int, str] = {}
    restr: dict[tuple[int, int], str] = {}
    pa = published_path(base, date_str, "rs_policy", "asns.json.gz")
    if pa.exists():
        ordem = "ASR"
        for asn, v in (read_json_gz(pa) or {}).get("asns", {}).items():
            ps = [PERFIL[x["politica"]["perfil"]] for x in (v.get("ixps") or {}).values() if (x.get("politica") or {}).get("perfil") in PERFIL]
            if ps:
                perfil[int(asn)] = max(ps, key=ordem.index)
    pg = published_path(base, date_str, "rs_policy", "grafo.json.gz")
    if pg.exists():
        for a in (read_json_gz(pg) or {}).get("arestas", []):
            restr[(int(a["de"]), int(a["para"]))] = "nao" if a["tipo"] == "nao_exporta_para" else "so"
    return perfil, restr


def _anterior(base: Path, date_str: str) -> Optional[dict]:
    pasta = base / "published"
    if not pasta.exists():
        return None
    ds = sorted((d.name for d in pasta.iterdir() if d.is_dir() and d.name < date_str and (d / "as_relationships.json.gz").exists()), reverse=True)
    return read_json_gz(pasta / ds[0] / "as_relationships.json.gz") if ds else None


def run(date_str: str, base: Path, log, cfg=None) -> bool:
    cfg = cfg or carregar()
    reg = read_json_gz(normalized_path(base, date_str, "summary") / "registro_br.json.gz") if (normalized_path(base, date_str, "summary") / "registro_br.json.gz").exists() else None
    if not reg:
        log.error("registro_br.json.gz não encontrado — abortando")
        return False
    br = {int(a["asn"]) for a in reg.get("asns", [])}
    cnpj_raiz = {int(a["asn"]): str(a["cnpj"])[:8] for a in reg.get("asns", []) if a.get("cnpj") and len(str(a["cnpj"])) >= 8}
    organizacao = _organizacoes(base, date_str)
    irmaos = restricoes.grupos_de_irmaos(cnpj_raiz, organizacao)                      # {asn: representante}, só grupos com 2+ ASNs
    grupos = {a: (f"g{irmaos[a]}" if a in irmaos else c) for a, c in cnpj_raiz.items()} | {a: f"g{r}" for a, r in irmaos.items()}
    v2 = cfg.versao >= 2 and cfg.refino.ativo
    perfil, restr = _politica(base, date_str) if v2 else ({}, {})
    irr_doc = irr_relacao.com_politicas(base) if v2 and cfg.refino.irr else None                     # `lg_ixbr`: só quando a chave `refino.irr` está ligada
    irr_rel = irr_relacao.relacoes(irr_doc["politicas"]) if irr_doc else None
    aspa_path = published_path(base, date_str, "rpki", "aspa_list.json.gz")
    aspa = read_json_gz(aspa_path) if aspa_path.exists() else []
    caida_path = _achar(base, date_str, "summary", "caida_asrel.json.gz")
    caida_doc = read_json_gz(caida_path) if caida_path else None
    caida = (caida_doc["p2c"], caida_doc["p2p"]) if caida_doc else None
    so_br = lambda a, b: a in br or b in br                                   # noqa: E731

    por_afi: dict[str, list] = {}
    diag: dict[str, dict] = {}
    coletores: dict[str, list[str]] = {}
    coletores_de: dict[str, Optional[str]] = {}
    for afi in AFIS:
        abrir, nomes, de = _colecao(base, date_str, afi)
        coletores[afi] = nomes
        coletores_de[afi] = de
        log.info("inferring relationships", afi=afi, coletores=len(nomes), aspa=len(aspa), caida=bool(caida))
        ctx: dict = {}
        vs, d = arc.inferir(_rs(base, date_str, afi), abrir, aspa, caida, grupos, cfg, so_elos=so_br, contexto=ctx if v2 else None)
        if v2:
            vs, d2 = refino.refinar(vs, ctx, cfg, afi, perfil, restr, log=log, irr=irr_rel)
            d["refino"] = {k: v for k, v in d2.items() if k in ("iteracoes", "treino", "elos", "temperatura", "abstencoes", "rebaixados_por_estrato")}
            del ctx, d2
        por_afi[afi], diag[afi] = vs, d
        log.info("relationships inferred", afi=afi, **{k: v for k, v in d.items() if k not in ("clique", "elos")}, elos=len(vs))
    linhas = _juntar(por_afi)
    for l in linhas:
        l["visto_em"] = date_str
    v2_doc: dict = {}
    if v2:
        n_irm = restricoes.aplicar_irmaos(linhas, cnpj_raiz, organizacao)
        n_ciclos = restricoes.quebrar_ciclos(linhas, irmaos)
        linhas, n_complexas = restricoes.unir_complexas(linhas, cfg)
        ger = estabilidade.geracao({"coletores_coletados_em": coletores_de}, date_str)
        linhas, mudancas, est = estabilidade.aplicar(linhas, _anterior(base, date_str), date_str, ger, cfg.refino.persistencia)
        ece = dict(cfg.refino.ece)
        v2_doc = {
            "refino": {afi: diag[afi].get("refino", {}) for afi in AFIS},
            "restricoes": {"irmaos": n_irm, "ciclos_rompidos": n_ciclos, "complexas": n_complexas,
                           "organizacoes_com_irmaos": len({r for r in irmaos.values()}), "asns_com_organizacao": len(organizacao)},
            "calibracao": {afi: {"temperatura": refino.temperatura_da_afi(cfg, afi), "ece": ece.get(afi), "p_calibrada": ece.get(afi) is not None and ece[afi] <= cfg.refino.ece_max,
                                 "medido_em": cfg.refino.calibrado_em or None} for afi in AFIS},
            "estabilidade": {**est, "geracao": ger, "persistencia": cfg.refino.persistencia},
            "mudancas": mudancas,
            "politica_rs": {"asns_com_perfil": len(perfil), "restricoes_declaradas": len(restr)},
            **({"irr": {"data": irr_doc["snapshot_date"], "pares_na_referencia": len(irr_rel)}} if irr_doc else {}),       # só com a chave ligada: o formato publicado não muda desligada
            "estratos": {"ativo": cfg.refino.estratos.ativo, "rebaixar": list(cfg.refino.estratos.rebaixar), "medido_em": cfg.refino.estratos.medido_em,
                         "p_calibrada": {f"{e}/{a}": x for e, a, x in cfg.refino.estratos.p_calibrada},
                         "rebaixados": {afi: diag[afi].get("refino", {}).get("rebaixados_por_estrato", {}) for afi in AFIS},
                         "elos_por_estrato": dict(sorted(Counter(l["estrato"] for l in linhas if l.get("estrato")).items()))},
        }
    resumo = Counter(f"{l['tipo']}/{l['nivel']}" for l in linhas)
    doc = {
        "snapshot_date": date_str, "generated_at": now_iso(), "algoritmo": f"ARC v{cfg.versao}",
        "entradas": {"route_servers": True, "coletores": coletores, "coletores_coletados_em": coletores_de, "aspa_objetos": len(aspa),
                     "caida_as_of": (caida_doc or {}).get("as_of"), "elos_so_com_asn_brasileiro": True},
        "clique": {afi: diag[afi].get("clique", []) for afi in AFIS},
        "diagnostico": {afi: {k: v for k, v in diag[afi].items() if k not in ("clique", "refino")} for afi in AFIS},
        "resumo": dict(sorted(resumo.items())),
        **v2_doc,
        "relacoes": linhas,
    }
    if compose.fluxo_novo(base, date_str):                               # fragmento `relacoes` do documento de ASN
        from products.as_relationships.por_asn import por_asn

        nomes_arq = _achar(base, date_str, "summary", "asn_names.json.gz")
        nomes = {int(k): v for k, v in (read_json_gz(nomes_arq) if nomes_arq else {}).items()}
        docs = por_asn(linhas, cfg, {afi: bool(coletores[afi]) for afi in AFIS}, nomes,
                       {afi: (v2_doc.get("calibracao", {}).get(afi) or {}).get("p_calibrada", False) for afi in AFIS})
        with compose.gravar_fragmento(base, date_str, "relacoes") as w:
            for asn in sorted(docs):
                w.escrever(asn, {"relacoes": docs[asn]})
        log.info("relacoes fragment written", asns=len(docs))
    destino = published_path(base, date_str, "as_relationships.json.gz")
    write_json_gz(destino, doc)
    log.info("as_relationships written", elos=len(linhas), bytes=destino.stat().st_size)
    return True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Relações entre ASNs (ARC v1)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true")
    a = p.parse_args(argv)
    log = configure_logging()
    base = data_dir()
    if not a.force and published_path(base, a.date, "as_relationships.json.gz").exists():
        log.info("already exists, skipping", date=a.date)
        return 0
    return 0 if run(a.date, base, log) else 1


if __name__ == "__main__":
    sys.exit(main())
