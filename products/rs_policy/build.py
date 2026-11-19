# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Rejeições, communities e política de roteamento nos route servers do IX.br. Saídas em `published/{date}/rs_policy/`:

  ixps.json.gz         por PTT: rejeições (motivos, ASNs que mais têm rota rejeitada) e política (perfis, ações usadas, blackhole), com a cobertura da coleta
  asns.json.gz         por ASN e PTT: rejeições por motivo (com amostra de prefixos) e política (perfil inferido, ações, RPKI das rotas recebidas) + evidência para a prontidão
  communities.json.gz  por community: classe, rótulo, e em cada PTT quantos ASNs a usam, em quantas rotas e quem mais usa (explorador de communities)
  grafo.json.gz        relações declaradas por communities: "não exporto para AS" e "exporto somente para AS" (ASN × ASN × PTT)
  linhas.json.gz       uma linha por (PTT, ASN, community) e por (PTT, ASN, motivo) para o `/query` (coleções `rs_communities` e `rs_filtradas`); a classe `informativa` fica de fora das linhas

Tudo parte do que o próprio route server mostra (Alice-LG, `ixbr_alice_rotas`): o dado é a **declaração** do membro por communities e a **decisão** do route server
sobre as rotas dele, não tráfego nem relação comercial. O perfil (aberto, seletivo, restritivo) é **inferido** por heurística documentada abaixo e sempre rotulado
como tal. Só entra quem foi coletado: ASN sem coleta de nível 3 não tem perfil (não é "aberto"), e a cobertura vai em todo bloco. Contagens de communities são
exatas sobre todas as rotas do vizinho; as amostras de prefixos (no máximo `AMOSTRA_PREFIXOS` por ASN e motivo) são amostras.

Heurística do perfil (por ASN e PTT, sobre as rotas recebidas; precisa de pelo menos `MIN_ROTAS_PERFIL` rotas):
  restritivo  alguma community de "exportar somente para" em pelo menos 50% das rotas, ou "não exportar para" 50 ASNs distintos ou mais em pelo menos 50% das rotas;
  seletivo    alguma community de ação (não exportar para, somente para, por RIR, por PTT, por RTT ou perda) em pelo menos 10% das rotas;
  aberto      as demais (nenhuma ação, ou ação em menos de 10% das rotas).
A fração é a maior contagem entre as communities da classe ÷ rotas recebidas: um limite inferior da fração de rotas afetadas (as ações podem recair em rotas diferentes).
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Optional

from core.common import load_ixps, normalized_path, now_iso, published_path
from core.ixbr_communities import ACOES, Dicionario
from core.jsonio import carregar_json_gz, gravar_json_gz

AMOSTRA_PREFIXOS = 5          # prefixos de amostra por ASN × PTT × motivo
MIN_ROTAS_PERFIL = 10
FRACAO_SELETIVO = 0.10
FRACAO_RESTRITIVO = 0.50
ALVOS_RESTRITIVO = 50
TOP_ALVOS = 25                # alvos listados por classe de ação e ASN
TOP_ASNS_COMMUNITY = 10       # quem mais usa uma community, por PTT
TOP_ASNS_PTT = 25
BOGON = ("26162:190:1", "26162:190:2")
CHAVES_EVIDENCIA = {"rpki_invalido": ("26162:300:0",), "registro_invalido": ("26162:100:0",), "rirs_invalido": ("26162:400:0",), "comprimento_invalido": ("26162:190:0",), "bogon": BOGON,
                    "nunca_via_rs": ("26162:190:4",), "transito_livre": ("26162:190:3",), "prefixos_do_ixbr": ("26162:190:5",)}


def _por_asn(vizinhos: list[dict]) -> dict[tuple[str, int], list[dict]]:
    out: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for v in vizinhos:
        out[(v["ixp"], v["asn"])].append(v)
    return out


def _min_max(vs: list[dict]) -> tuple[Optional[str], Optional[str]]:
    datas = [str(v.get("coletado_em") or "")[:10] for v in vs if v.get("coletado_em")]
    return (min(datas), max(datas)) if datas else (None, None)


def rejeicoes_do_asn(vs: list[dict], dic: Dicionario) -> dict:
    """Bloco `rejeicoes` de um ASN em um PTT, somando as sessões consultadas (IPv4 e IPv6)."""
    total = sum(v.get("total") or 0 for v in vs)
    motivos: dict[str, dict] = {}
    amostras: dict[str, list[dict]] = defaultdict(list)
    for v in vs:
        for c, n in (v.get("motivos") or {}).items():
            m = motivos.setdefault(c, {"codigo": c, **{k: x for k, x in dic.classificar(c).items() if k in ("rotulo", "classe")}, "rotas": 0})
            m["rotas"] += n
        for a in v.get("amostra") or []:
            for c in (a.get("m") or ["sem_motivo"]):
                if len(amostras[c]) < AMOSTRA_PREFIXOS and a.get("p") not in {x["p"] for x in amostras[c]}:
                    amostras[c].append({"p": a.get("p"), "o": a.get("o")})
    lista = sorted(motivos.values(), key=lambda m: (-m["rotas"], m["codigo"]))
    for m in lista:
        m["amostra"] = amostras.get(m["codigo"], [])
    com_motivo = sum(m["rotas"] for m in lista)
    de, ate = _min_max(vs)
    r = {"rotas": total, "sessoes": len(vs), "afis": sorted({v["afi"] for v in vs}), "motivos": lista, "sem_motivo": max(0, total - com_motivo),
         "coletado_de": de, "coletado_ate": ate, "contagem": "exata" if all(v.get("contagem") == "exata" for v in vs) else "amostra"}
    if amostras.get("sem_motivo"):
        r["amostra_sem_motivo"] = amostras["sem_motivo"]
    if any(v.get("herdado") for v in vs):
        r["herdado"] = True
    return r


def evidencia_prontidao(rejeicoes_por_ptt: list[dict]) -> dict:
    """Rotas rejeitadas pelo route server por tipo, somadas nos PTTs coletados: evidência *do route server* (não é o veredito sobre o ASN)."""
    ev = {k: 0 for k in CHAVES_EVIDENCIA}
    ev["rotas_rejeitadas"] = 0
    for r in rejeicoes_por_ptt:
        ev["rotas_rejeitadas"] += r["rotas"]
        for m in r["motivos"]:
            for k, cs in CHAVES_EVIDENCIA.items():
                if m["codigo"] in cs:
                    ev[k] += m["rotas"]
    ev["ptts"] = len(rejeicoes_por_ptt)
    return ev


def politica_do_asn(vs: list[dict], dic: Dicionario) -> dict:
    """Bloco `politica` de um ASN em um PTT, das rotas recebidas coletadas (nível 3)."""
    total = sum(v.get("total") or 0 for v in vs)
    soma: dict[str, int] = defaultdict(int)
    for v in vs:
        for c, n in (v.get("comunidades") or {}).items():
            soma[c] += n
    grupos: dict[tuple[str, object], dict] = {}
    bh = 0
    rpki: dict[str, int] = defaultdict(int)
    for c, n in soma.items():
        k = dic.classificar(c)
        if k["classe"] in ACOES:
            g = grupos.setdefault((k["classe"], k.get("alvo")), {"alvo": k.get("alvo"), "rotulo": k["rotulo"], "rotas": 0, "formas": set()})
            g["rotas"] = max(g["rotas"], n)         # a mesma intenção vem em mais de uma forma (padrão, estendida, grande): vale a maior contagem, não a soma
            g["formas"].add(k["forma"])
        elif k["classe"] == "blackhole":
            bh = max(bh, n)
        elif k["classe"] == "rpki":
            rpki[k["estado_rpki"]] += n
    acoes: dict[str, dict] = {}
    for (classe, _), g in grupos.items():
        a = acoes.setdefault(classe, {"alvos": [], "alvos_total": 0, "rotas_max": 0})
        a["alvos"].append({"alvo": g["alvo"], "rotulo": g["rotulo"], "rotas": g["rotas"], "fracao": round(g["rotas"] / total, 3) if total else None,
                           "forma": "dicionario" if "dicionario" in g["formas"] else "equivalente_padrao"})
        a["alvos_total"] += 1
        a["rotas_max"] = max(a["rotas_max"], g["rotas"])
    for a in acoes.values():
        a["alvos"].sort(key=lambda x: (-x["rotas"], x["alvo"] if x["alvo"] is not None else -1))
        a["alvos"] = a["alvos"][:TOP_ALVOS]
        a["fracao_max"] = round(a["rotas_max"] / total, 3) if total else None
    perfil, criterio = (None, "dicionário de communities do snapshot ausente: nada foi decodificado") if dic.vazio else classificar_perfil(total, acoes)
    de, ate = _min_max(vs)
    r = {"rotas": total, "sessoes": len(vs), "afis": sorted({v["afi"] for v in vs}), "perfil": perfil, "perfil_criterio": criterio, "perfil_inferido": True, "acoes": dict(sorted(acoes.items())),
         "blackhole_rotas": bh, "rpki": {k: rpki.get(k, 0) for k in ("valid", "unknown", "not_checked", "invalid")}, "communities_distintas": len(soma),
         "coletado_de": de, "coletado_ate": ate, "contagem": "exata" if all(v.get("contagem") == "exata" for v in vs) else "amostra"}
    if any(v.get("herdado") for v in vs):
        r["herdado"] = True
    return r


def classificar_perfil(total: int, acoes: dict[str, dict]) -> tuple[Optional[str], str]:
    if total < MIN_ROTAS_PERFIL:
        return None, f"menos de {MIN_ROTAS_PERFIL} rotas recebidas coletadas ({total})"
    so = max((acoes.get(c, {}).get("fracao_max") or 0) for c in ("exportar_somente_para", "exportar_somente_rir"))
    ne = acoes.get("nao_exportar_para", {})
    if so >= FRACAO_RESTRITIVO:
        return "restritivo", f"'exportar somente para' em {so:.0%} das rotas (limite {FRACAO_RESTRITIVO:.0%})"
    if ne.get("alvos_total", 0) >= ALVOS_RESTRITIVO and (ne.get("fracao_max") or 0) >= FRACAO_RESTRITIVO:
        return "restritivo", f"'não exportar para' {ne['alvos_total']} ASNs distintos (limite {ALVOS_RESTRITIVO}), em até {ne['fracao_max']:.0%} das rotas"
    top = max(((c, a.get("fracao_max") or 0) for c, a in acoes.items()), key=lambda x: x[1], default=(None, 0))
    if top[1] >= FRACAO_SELETIVO:
        return "seletivo", f"ação '{top[0]}' em {top[1]:.0%} das rotas (limite {FRACAO_SELETIVO:.0%})"
    return "aberto", ("nenhuma community de ação de exportação nas rotas" if top[0] is None else f"maior ação ('{top[0]}') em {top[1]:.0%} das rotas, abaixo de {FRACAO_SELETIVO:.0%}")


def calcular(f_doc: Optional[dict], c_doc: Optional[dict], comm_doc: Optional[dict], rs_doc: Optional[dict], ixps_conhecidos: dict[str, str]) -> dict[str, dict]:
    """Devolve {ixps, asns, communities, grafo, linhas} (cada um já no formato publicado)."""
    dic = Dicionario(comm_doc)
    nomes: dict[int, str] = {}
    for s in (rs_doc or {}).get("sessoes") or []:
        if s.get("asn") is not None and s.get("descricao") and s["asn"] not in nomes:
            nomes[s["asn"]] = s["descricao"]
    viz_f = [v for v in (f_doc or {}).get("vizinhos") or [] if v["ixp"] in ixps_conhecidos]
    viz_c = [v for v in (c_doc or {}).get("vizinhos") or [] if v["ixp"] in ixps_conhecidos]
    rej = {k: rejeicoes_do_asn(vs, dic) for k, vs in _por_asn(viz_f).items()}
    pol = {k: politica_do_asn(vs, dic) for k, vs in _por_asn(viz_c).items()}

    asns: dict[str, dict] = {}
    for (ixp, asn), r in rej.items():
        asns.setdefault(str(asn), {"ixps": {}})["ixps"].setdefault(ixp, {})["rejeicoes"] = r
    for (ixp, asn), p in pol.items():
        asns.setdefault(str(asn), {"ixps": {}})["ixps"].setdefault(ixp, {})["politica"] = p
    for a, d in asns.items():
        if int(a) in nomes:
            d["nome"] = nomes[int(a)]
        rs = [x["rejeicoes"] for x in d["ixps"].values() if "rejeicoes" in x]
        if rs:
            d["evidencia_rs"] = evidencia_prontidao(rs)
    asns = dict(sorted(asns.items(), key=lambda kv: int(kv[0])))

    # communities: uma entrada por community, com o uso por PTT
    soma_por: dict[tuple[str, str, int], int] = defaultdict(int)
    for v in viz_c:
        for c, n in (v.get("comunidades") or {}).items():
            soma_por[(c, v["ixp"], v["asn"])] += n
    por_comm: dict[str, dict] = {}
    for (c, ixp, asn), n in soma_por.items():
        e = por_comm.get(c)
        if e is None:
            e = por_comm[c] = {**{k: x for k, x in dic.classificar(c).items() if k != "community"}, "community": c, "ixps": {}}
        u = e["ixps"].setdefault(ixp, {"asns": 0, "rotas": 0, "top": []})
        u["asns"] += 1
        u["rotas"] += n
        u["top"].append({"asn": asn, "rotas": n, **({"nome": nomes[asn]} if asn in nomes else {})})
    comunidades = []
    for c, e in por_comm.items():
        for u in e["ixps"].values():
            u["top"].sort(key=lambda x: (-x["rotas"], x["asn"]))
            u["top"] = u["top"][:TOP_ASNS_COMMUNITY]
        e["asns_total"] = sum(u["asns"] for u in e["ixps"].values())
        e["rotas_total"] = sum(u["rotas"] for u in e["ixps"].values())
        comunidades.append(e)
    comunidades.sort(key=lambda e: (-e["asns_total"], -e["rotas_total"], e["community"]))

    # grafo declarado
    arestas = []
    totais = {(v["ixp"], v["asn"]): 0 for v in viz_c}
    for v in viz_c:
        totais[(v["ixp"], v["asn"])] += v.get("total") or 0
    # as arestas usam a lista completa de alvos (não o top-N guardado no bloco do ASN)
    for (ixp, asn), vs in _por_asn(viz_c).items():
        soma: dict[str, int] = defaultdict(int)
        for v in vs:
            for c, n in (v.get("comunidades") or {}).items():
                soma[c] += n
        alvo_n: dict[tuple[str, int], int] = {}
        for c, n in soma.items():
            k = dic.classificar(c)
            if k["classe"] in ("nao_exportar_para", "exportar_somente_para") and k.get("alvo") is not None:
                chave = (k["classe"], k["alvo"])
                alvo_n[chave] = max(alvo_n.get(chave, 0), n)
        tot = totais[(ixp, asn)]
        for (classe, alvo), n in alvo_n.items():
            arestas.append({"ixp": ixp, "de": asn, "para": alvo, "tipo": "nao_exporta_para" if classe == "nao_exportar_para" else "exporta_somente_para", "rotas": n, "total_rotas": tot,
                            "fracao": round(n / tot, 3) if tot else None})
    arestas.sort(key=lambda a: (a["ixp"], a["de"], a["tipo"], a["para"]))

    # PTTs
    ixps: dict[str, dict] = {}
    cob_f = (f_doc or {}).get("cobertura") or {}
    cob_c = (c_doc or {}).get("cobertura") or {}
    for code in sorted(set(k[0] for k in rej) | set(k[0] for k in pol) | set(cob_f) | set(cob_c)):
        if code not in ixps_conhecidos:
            continue
        rs_ = {asn: r for (i, asn), r in rej.items() if i == code}
        ps_ = {asn: p for (i, asn), p in pol.items() if i == code}
        motivos: dict[str, dict] = {}
        for asn, r in rs_.items():
            for m in r["motivos"]:
                x = motivos.setdefault(m["codigo"], {"codigo": m["codigo"], "rotulo": m["rotulo"], "classe": m["classe"], "rotas": 0, "asns": 0})
                x["rotas"] += m["rotas"]
                x["asns"] += 1
        total_rej = sum(r["rotas"] for r in rs_.values())
        soma_motivos = sum(x["rotas"] for x in motivos.values())          # uma rota pode ter mais de um motivo: a soma pode passar do total
        com_motivo = total_rej - sum(r["sem_motivo"] for r in rs_.values())
        lista = [{"asn": asn, **({"nome": nomes[asn]} if asn in nomes else {}), "rotas": r["rotas"], "motivos": {m["codigo"]: m["rotas"] for m in r["motivos"]}} for asn, r in rs_.items()]
        lista.sort(key=lambda x: (-x["rotas"], x["asn"]))
        perfis: dict[str, int] = defaultdict(int)
        acoes_ptt: dict[str, dict] = {}
        for p in ps_.values():
            perfis[p["perfil"] or "indeterminado"] += 1
            for classe, a in p["acoes"].items():
                x = acoes_ptt.setdefault(classe, {"asns": 0})
                x["asns"] += 1
        ixps[code] = {
            "nome": ixps_conhecidos[code],
            "rejeicoes": {"cobertura": cob_f.get(code) or {"elegiveis": 0, "coletados": 0, "herdados": 0}, "asns_com_rejeicao": len(rs_), "rotas_rejeitadas": total_rej,
                          "rotas_com_motivo_decodificado": com_motivo, "soma_dos_motivos": soma_motivos, "por_motivo": sorted(motivos.values(), key=lambda m: (-m["rotas"], m["codigo"])),
                          "asns": lista} if code in cob_f or rs_ else None,
            "politica": {"cobertura": cob_c.get(code) or {"elegiveis": 0, "coletados": 0, "herdados": 0}, "asns_com_dado": len(ps_), "perfis": dict(sorted(perfis.items())),
                         "acoes": dict(sorted(acoes_ptt.items())),
                         "blackhole": {"asns": sum(1 for p in ps_.values() if p["blackhole_rotas"]), "rotas": sum(p["blackhole_rotas"] for p in ps_.values())},
                         "rpki": {k: sum(p["rpki"][k] for p in ps_.values()) for k in ("valid", "unknown", "not_checked", "invalid")}} if code in cob_c or ps_ else None,
        }

    # linhas para o /query
    linhas_c = []
    for (c, ixp, asn), n in sorted(soma_por.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0])):
        k = dic.classificar(c)
        if k["classe"] == "informativa":              # origem, validação e RTT do próprio IX.br: milhares de linhas sem política; ficam no explorador, não no /query
            continue
        tot = totais.get((ixp, asn)) or 0
        linhas_c.append({"ixp": ixp, "asn": asn, "nome": nomes.get(asn), "community": c, "classe": k["classe"], "rotulo": k["rotulo"], "forma": k["forma"], "alvo_asn": k.get("alvo") if k["classe"] in ("nao_exportar_para", "exportar_somente_para") else None,
                         "rotas": n, "rotas_do_asn": tot, "fracao": round(n / tot, 3) if tot else None})
    linhas_f = []
    for (ixp, asn), r in sorted(rej.items()):
        for m in r["motivos"]:
            linhas_f.append({"ixp": ixp, "asn": asn, "nome": nomes.get(asn), "motivo": m["codigo"], "rotulo": m["rotulo"], "classe": m["classe"], "rotas": m["rotas"], "rotas_rejeitadas_do_asn": r["rotas"],
                             "prefixos_amostra": [x["p"] for x in m["amostra"]]})
    return {"ixps": ixps, "asns": asns, "communities": comunidades, "grafo": arestas, "linhas": {"rs_communities": linhas_c, "rs_filtradas": linhas_f}}


def publicar_rs_policy(base: Path, date_str: str, log, ixps_cfg: Optional[list[dict]] = None) -> dict:
    resumo = normalized_path(base, date_str, "summary")
    f_doc = carregar_json_gz(resumo / "rs_filtered.json.gz")
    c_doc = carregar_json_gz(resumo / "rs_communities.json.gz")
    if not f_doc and not c_doc:
        log.info("rs_filtered e rs_communities ausentes: rs_policy não gerado")
        return {}
    cfg = ixps_cfg if ixps_cfg is not None else load_ixps()
    conhecidos = {i["code"]: i.get("name") or i["code"] for i in cfg}
    out = calcular(f_doc, c_doc, carregar_json_gz(resumo / "ixbr_communities.json.gz"), carregar_json_gz(resumo / "rs_sessions.json.gz"), conhecidos)
    destino = published_path(base, date_str) / "rs_policy"
    destino.mkdir(parents=True, exist_ok=True)
    cab = {"snapshot_date": date_str, "generated_at": now_iso(), "fonte": (f_doc or c_doc or {}).get("fonte"), "versao_alice": (f_doc or c_doc or {}).get("versao_alice"),
           "coletado_nivel2": (f_doc or {}).get("generated_at"), "coletado_nivel3": (c_doc or {}).get("generated_at"),
           "requisicoes_nivel2": (f_doc or {}).get("requisicoes_da_rodada"), "requisicoes_nivel3": (c_doc or {}).get("requisicoes_da_rodada"),
           "rs_pulados": sorted({x["rs"] for d in (f_doc, c_doc) for x in (d or {}).get("rs_pulados") or []}),
           "parametros": {"amostra_prefixos": AMOSTRA_PREFIXOS, "min_rotas_perfil": MIN_ROTAS_PERFIL, "fracao_seletivo": FRACAO_SELETIVO, "fracao_restritivo": FRACAO_RESTRITIVO,
                          "alvos_restritivo": ALVOS_RESTRITIVO}}
    gravar_json_gz(destino / "ixps.json.gz", {**cab, "ixps": out["ixps"]})
    gravar_json_gz(destino / "asns.json.gz", {**cab, "asns": out["asns"]})
    gravar_json_gz(destino / "communities.json.gz", {**cab, "total": len(out["communities"]), "communities": out["communities"]})
    gravar_json_gz(destino / "grafo.json.gz", {**cab, "total": len(out["grafo"]), "arestas": out["grafo"]})
    gravar_json_gz(destino / "linhas.json.gz", {**cab, **out["linhas"]})
    log.info("rs_policy published", ixps=len(out["ixps"]), asns=len(out["asns"]), communities=len(out["communities"]), arestas=len(out["grafo"]))
    return {"ixps": len(out["ixps"]), "asns": len(out["asns"]), "communities": len(out["communities"]), "arestas": len(out["grafo"])}
