# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Route servers do IX.br (níveis 0 e 1). Saídas: `published/{date}/route_servers/ixps.json.gz` e `asns.json.gz`.

Cruza as sessões BGP vistas no Alice-LG (`ixbr_alice`) com o cadastro de membros do IX.br (`ixbr_members`):
  * por PTT: route servers (estado), sessões, membros cadastrados com e sem sessão, sessões sem cadastro e quantos membros estão com todas as sessões
    down há `DIAS_DOWN` dias ou mais;
  * o `state` READY/BUSY/ERROR do `/status` do Alice é o do cache de **rotas** e não diz nada sobre as sessões (medido: o SP rs1 v4 aparece BUSY/ERROR nas rotas e
    tem sessões com minutos de uptime, como na tela do lg.ix.br). O frescor das sessões é o `cache_status.cached_at` da resposta do `neighbors`: sessão cujo cache de
    vizinhos tem mais de `IDADE_MAX_VIZINHOS_H` horas, não traz esse dado ou não foi consultada vem marcada `rs_incerto`, e o membro nunca conta como down por causa dela;
  * por ASN: as sessões em cada PTT (route server, família, estado, há quantos dias, último erro, rotas e uso do limite de importação).

Fatos medidos no route server naquele instante, com a data da coleta: "cadastrado sem sessão" não diz que o membro não troca tráfego (pode ser
bilateral) e "sessão down" não diz de quem é a causa. Sem veredito (política editorial). Mudança de estado entre semanas fica para o histórico.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.common import load_ixps, normalized_path, now_iso, published_path, raw_path
from core.jsonio import carregar_json_gz, gravar_json_gz

DIAS_DOWN = 7                 # sessão down há pelo menos isso entra em "membro down há N dias"
IDADE_MAX_VIZINHOS_H = 24     # idade máxima do cache de vizinhos do Alice (cached_at) para as sessões valerem como estado atual
USO_LIMITE = 0.8              # rotas recebidas / limite de importação a partir do qual a sessão está "perto do limite"


def dias_desde(state_changed: Optional[str], referencia: str) -> Optional[int]:
    """Dias inteiros entre a última mudança de estado do route server ("AAAA-MM-DD HH:MM:SS") e o instante da coleta (ISO)."""
    if not state_changed:
        return None
    try:
        t = datetime.fromisoformat(state_changed.replace("Z", ""))
        ref = datetime.fromisoformat(referencia.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None
    return max(0, (ref - t).days)


def uso_limite(s: dict) -> Optional[float]:
    lim = s.get("import_limit")
    rec = (s.get("rotas") or {}).get("recebidas")
    if not lim or rec is None:
        return None
    return round(rec / lim, 3)


def vizinhos_incertos(rs_doc: dict) -> set[str]:
    """Route servers cujas sessões não valem como estado atual: consulta que falhou, `cached_at` ausente ou mais velho que `IDADE_MAX_VIZINHOS_H` na coleta."""
    ref = rs_doc.get("generated_at") or now_iso()
    out = set()
    for r in rs_doc.get("rs") or []:
        idade = None
        if r.get("consultado") and r.get("vizinhos_em"):
            try:
                idade = (datetime.fromisoformat(ref.replace("Z", "+00:00")) - datetime.fromisoformat(r["vizinhos_em"].replace("Z", "+00:00"))).total_seconds() / 3600
            except ValueError:
                idade = None
        if idade is None or idade > IDADE_MAX_VIZINHOS_H:
            out.add(r["rs"])
    return out


def sessao_compacta(s: dict, referencia: str, incerto: bool = False) -> dict:
    d = {"rs": s["rs"], "afi": s["afi"], "ip": s["neighbor_ip"], "estado": s["estado"], "dias": dias_desde(s.get("state_changed"), referencia),
         "recebidas": (s.get("rotas") or {}).get("recebidas"), "aceitas": (s.get("rotas") or {}).get("aceitas"),
         "filtradas": (s.get("rotas") or {}).get("filtradas"), "limite": s.get("import_limit"), "uso_limite": uso_limite(s)}
    if s.get("last_error"):
        d["erro"] = s["last_error"]
    if incerto:
        d["rs_incerto"] = True          # cache de vizinhos do route server sem frescor confirmado (ver `vizinhos_incertos`)
    return d


def resumo_membro(sessoes: list[dict]) -> dict:
    up = [s for s in sessoes if s["estado"] == "up"]
    down = [s for s in sessoes if s["estado"] != "up"]
    certas = [s for s in down if not s.get("rs_incerto")]          # só as de route server com vizinhos atuais contam para tempo de queda e ranking
    dias_down = [s["dias"] for s in certas if s["dias"] is not None]
    usos = [s["uso_limite"] for s in up if s["uso_limite"] is not None]
    r = {"sessoes": len(sessoes), "up": len(up), "down": len(down), "down_certo": len(certas)}
    if dias_down:
        r["max_dias_down"] = max(dias_down)
    if usos:
        r["max_uso_limite"] = max(usos)
    r["todas_down"] = bool(sessoes) and not up
    incertas = sum(1 for s in sessoes if s.get("rs_incerto"))
    if incertas:
        r["rs_incerto"] = incertas
    r["membro_down"] = bool(sessoes) and not up and bool(dias_down) and min(dias_down) >= DIAS_DOWN and not incertas
    r["perto_do_limite"] = bool(usos) and max(usos) >= USO_LIMITE
    return r


def calcular(rs_doc: dict, cadastro: dict[str, dict[int, str]], ixps_conhecidos: dict[str, str]) -> tuple[dict, dict]:
    """`cadastro`: {ixp: {asn: nome}}; `ixps_conhecidos`: {código: nome} do config (route servers de PTT fora dele, como os antigos, não entram).
    Devolve ({ixp: bloco do PTT}, {asn: bloco do ASN})."""
    ref = rs_doc.get("generated_at") or now_iso()
    por_ixp_sessoes: dict[str, dict[int, list[dict]]] = {}
    nao_pronto = vizinhos_incertos(rs_doc)
    for s in rs_doc.get("sessoes") or []:
        if s["ixp"] in ixps_conhecidos and s.get("asn") is not None:
            por_ixp_sessoes.setdefault(s["ixp"], {}).setdefault(s["asn"], []).append(sessao_compacta(s, ref, s["rs"] in nao_pronto))
    rs_por_ixp: dict[str, list[dict]] = {}
    for r in rs_doc.get("rs") or []:
        if r["ixp"] in ixps_conhecidos:
            rs_por_ixp.setdefault(r["ixp"], []).append({"vizinhos_incerto": r["rs"] in nao_pronto, **{k: r.get(k) for k in ("rs", "numero", "afi", "estado_rotas", "rotas_atualizadas_em", "vizinhos_em", "rotas_importadas", "consultado", "erro", "sessoes", "sessoes_up")}})
    ixps: dict[str, dict] = {}
    asns: dict[str, dict] = {}
    for code in sorted(set(rs_por_ixp) | set(cadastro)):
        if code not in ixps_conhecidos:
            continue
        cad = cadastro.get(code) or {}
        sess = por_ixp_sessoes.get(code) or {}
        consultado = [r for r in rs_por_ixp.get(code, []) if r["consultado"]]
        medido = bool(consultado)            # sem nenhum RS consultado não se afirma "sem sessão" de ninguém
        membros = []
        for asn in sorted(set(cad) | set(sess)):
            lista = sorted(sess.get(asn, []), key=lambda x: (x["rs"], x["ip"]))
            r = resumo_membro(lista)
            m = {"asn": asn, "nome": cad.get(asn), "cadastrado": asn in cad, **r}
            if medido and asn in cad and not lista:
                m["cadastrado_sem_sessao"] = True
            membros.append(m)
            if lista:
                asns.setdefault(str(asn), {"ixps": {}})["ixps"][code] = {"cadastrado": asn in cad, **r, "lista": lista}
        com = [m for m in membros if m["sessoes"]]
        ixps[code] = {
            "nome": ixps_conhecidos[code], "rs": rs_por_ixp.get(code, []),
            "resumo": {"rs": len(rs_por_ixp.get(code, [])), "rs_consultados": len(consultado),
                       "rs_rotas_prontas": sum(1 for r in rs_por_ixp.get(code, []) if r["estado_rotas"] == "READY"),
                       "rs_vizinhos_atuais": sum(1 for r in rs_por_ixp.get(code, []) if r["rs"] not in nao_pronto),
                       "cadastrados": len(cad), "cadastrados_com_sessao": sum(1 for m in com if m["cadastrado"]),
                       "cadastrados_sem_sessao": sum(1 for m in membros if m.get("cadastrado_sem_sessao")),
                       "sessao_sem_cadastro": sum(1 for m in com if not m["cadastrado"]),
                       "sessoes": sum(m["sessoes"] for m in com), "sessoes_up": sum(m["up"] for m in com), "sessoes_down": sum(m["down"] for m in com),
                       "membros_down": sum(1 for m in com if m["membro_down"]), "membros_com_rs_incerto": sum(1 for m in com if m.get("rs_incerto")), "membros_perto_do_limite": sum(1 for m in com if m["perto_do_limite"])},
            "membros": membros}
    for a, d in asns.items():
        ls = list(d["ixps"].values())
        d["total"] = {"ixps": len(ls), "sessoes": sum(x["sessoes"] for x in ls), "up": sum(x["up"] for x in ls), "down": sum(x["down"] for x in ls),
                      "ixps_down": sum(1 for x in ls if x["membro_down"]), "ixps_perto_do_limite": sum(1 for x in ls if x["perto_do_limite"])}
    return ixps, dict(sorted(asns.items(), key=lambda kv: int(kv[0])))


def _cadastro(base: Path, date_str: str, codigos: list[str]) -> dict[str, dict[int, str]]:
    out: dict[str, dict[int, str]] = {}
    for code in codigos:
        p = raw_path(base, date_str, code) / "ixbr_members.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        out[code] = {int(m["asn"]): m.get("name") or "" for m in d.get("members") or [] if m.get("asn") is not None}
    return out


def publicar_route_servers(base: Path, date_str: str, log, ixps_cfg: Optional[list[dict]] = None) -> dict:
    rs_doc = carregar_json_gz(normalized_path(base, date_str, "summary") / "rs_sessions.json.gz")
    if not rs_doc:
        log.info("rs_sessions.json.gz ausente: route_servers não gerado")
        return {}
    cfg = ixps_cfg if ixps_cfg is not None else load_ixps()
    conhecidos = {i["code"]: i.get("name") or i["code"] for i in cfg}
    ixps, asns = calcular(rs_doc, _cadastro(base, date_str, sorted(conhecidos)), conhecidos)
    destino = published_path(base, date_str) / "route_servers"
    destino.mkdir(parents=True, exist_ok=True)
    cab = {"snapshot_date": date_str, "generated_at": now_iso(), "coletado_em": rs_doc.get("generated_at"), "fonte": rs_doc.get("fonte"),
           "versao_alice": rs_doc.get("versao_alice"), "dias_down": DIAS_DOWN, "uso_limite": USO_LIMITE, "idade_max_vizinhos_h": IDADE_MAX_VIZINHOS_H}
    gravar_json_gz(destino / "ixps.json.gz", {**cab, "ixps": ixps})
    gravar_json_gz(destino / "asns.json.gz", {**cab, "asns": asns})
    log.info("route_servers published", ixps=len(ixps), asns=len(asns))
    return {"ixps": len(ixps), "asns": len(asns), "sessoes": sum(i["resumo"]["sessoes"] for i in ixps.values())}
