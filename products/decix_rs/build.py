# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""DE-CIX Rio de Janeiro e São Paulo vistos pelos route servers. Saída: `published/{date}/decix_rs/ixps.json.gz`.

Estende o `external-ixps` (que só tem os membros declarados no PeeringDB) com o que o Alice-LG do DE-CIX mostra, por PTT (`decix-sp`, `decix-rj`):
  * `asn_direct`: ASNs com sessão **up** em algum route server do PTT (peering multilateral). Não é o mesmo critério do IX.br (`ixps/{code}.json`, onde direto é o
    primeiro salto do AS_PATH nas rotas do PTT): aqui é sessão BGP com o route server, e o campo `criterio` diz isso. Quem peer só bilateralmente não aparece;
  * `asn_origin`: ASNs de origem (último do AS_PATH) das rotas lidas por vizinho em rodízio (nível 3). **É um piso**: a leitura é limitada por vizinho e por rodada, e
    a cobertura (`rotas.cobertura`, `rotas.parcial`) diz quantos vizinhos foram lidos por inteiro. Sem leitura não há ASN de origem (não é "zero");
  * `membros`: por ASN, o nome do LG, as sessões up e down por família e as rotas recebidas; o cruzamento com o PeeringDB (`peeringdb`: cadastrado sem sessão e sessão sem cadastro);
  * `comparacao_cidade`: o PTT do IX.br da mesma cidade, o DE-CIX e, em São Paulo, o Equinix cadastrado no PeeringDB: contagens, interseção dos ASNs diretos e os ASNs com
    sessão no DE-CIX que não são diretos no IX.br. Os critérios diferem (sessão no route server, primeiro salto, cadastro): a comparação é de conjuntos de ASNs, não de tráfego.

Fatos medidos no route server na data da coleta, sem veredito. Os nomes são rótulos públicos do LG (organização), nunca contatos.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.common import normalized_path, now_iso, published_path
from core.jsonio import carregar_json, carregar_json_gz, gravar_json_gz

# PTT do DE-CIX → cidade, PTT do IX.br da mesma cidade e PTTs externos do PeeringDB da cidade (além do próprio DE-CIX)
CIDADES: dict[str, dict] = {
    "decix-sp": {"cidade": "São Paulo", "nome": "DE-CIX São Paulo", "ixbr": "sp", "externos": ["equinix-sp"]},
    "decix-rj": {"cidade": "Rio de Janeiro", "nome": "DE-CIX Rio de Janeiro", "ixbr": "rj", "externos": []},
}
LIMITE_LISTA = 500          # ASNs listados em `no_decix_sem_ixbr` (a contagem é sempre completa)
CRITERIOS = {
    "asn_direct": "sessão BGP up em route server do DE-CIX (multilateral); não é o primeiro salto do AS_PATH que o IX.br usa",
    "asn_origin": "último ASN do AS_PATH das rotas lidas por vizinho em rodízio; piso (leitura parcial), não o conjunto",
}


def _conjunto(valores) -> set[int]:
    out = set()
    for v in valores or []:
        try:
            out.add(int(v["asn"] if isinstance(v, dict) else v))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def membros_do_rs(sessoes: list[dict]) -> dict[int, dict]:
    """Por ASN: nome do LG, sessões up/down por família e rotas recebidas pelo route server (somadas entre os route servers: a mesma rota conta uma vez por RS)."""
    por: dict[int, dict] = {}
    for s in sessoes:
        asn = s.get("asn")
        if asn is None:
            continue
        m = por.setdefault(int(asn), {"asn": int(asn), "nome": s.get("descricao") or "", "up": 0, "down": 0, "v4": {"up": 0, "down": 0}, "v6": {"up": 0, "down": 0},
                                      "recebidas": {"v4": 0, "v6": 0}})
        estado = "up" if s.get("estado") == "up" else "down"
        m[estado] += 1
        if s.get("afi") in ("v4", "v6"):
            m[s["afi"]][estado] += 1
        if estado == "up":
            m["recebidas"][s["afi"]] = max(m["recebidas"][s["afi"]], (s.get("rotas") or {}).get("recebidas") or 0)      # rs1 e rs2 recebem as mesmas rotas: vale o maior
    return por


def origens_do_ptt(rotas_doc: Optional[dict], code: str) -> tuple[dict[int, int], dict]:
    """({ASN de origem: rotas lidas}, resumo da leitura) dos vizinhos do PTT no documento de rotas."""
    origens: dict[int, int] = {}
    n = lidos = completos = herdados = 0
    total_rotas = lidas = 0
    for v in (rotas_doc or {}).get("vizinhos") or []:
        if v.get("ixp") != code:
            continue
        n += 1
        herdados += 1 if v.get("herdado") else 0
        completos += 1 if v.get("completo") else 0
        lidos += 1
        total_rotas += v.get("total") or 0
        lidas += v.get("lidas") or 0
        for a, c in (v.get("origens") or {}).items():
            origens[int(a)] = origens.get(int(a), 0) + int(c)
    return origens, {"vizinhos_lidos": lidos, "vizinhos_completos": completos, "herdados": herdados, "rotas_total_dos_lidos": total_rotas, "rotas_lidas": lidas}


def calcular(sess_doc: dict, rotas_doc: Optional[dict], br: set[int], ixbr: dict[str, dict], peeringdb: dict[str, dict[int, str]]) -> dict[str, dict]:
    """`ixbr`: {código do PTT: {"direct": {asn}, "br_origin": {asn}}}; `peeringdb`: {código externo: {asn: nome}} (inclui o próprio decix-* e o equinix-sp)."""
    sessoes_por: dict[str, list[dict]] = {}
    for s in sess_doc.get("sessoes") or []:
        sessoes_por.setdefault(s["ixp"], []).append(s)
    rs_por: dict[str, list[dict]] = {}
    for r in sess_doc.get("rs") or []:
        rs_por.setdefault(r["ixp"], []).append({k: r.get(k) for k in ("rs", "numero", "afi", "estado_rotas", "rotas_atualizadas_em", "vizinhos_em", "rotas_importadas", "rotas_filtradas", "consultado", "erro", "sessoes", "sessoes_up")})
    cob_ptt = ((rotas_doc or {}).get("cobertura_rodizio") or {}).get("por_ptt") or {}
    saida: dict[str, dict] = {}
    for code, cfg in CIDADES.items():
        if code not in rs_por:
            continue
        mem = membros_do_rs(sessoes_por.get(code, []))
        direct = {a for a, m in mem.items() if m["up"]}
        origens, leitura = origens_do_ptt(rotas_doc, code)
        cob = cob_ptt.get(code) or {}
        parcial = (not rotas_doc) or (not cob) or cob.get("sem_leitura", 0) > 0 or leitura["vizinhos_completos"] < leitura["vizinhos_lidos"] or not leitura["vizinhos_lidos"]
        pdb = peeringdb.get(code) or {}
        ix = ixbr.get(cfg["ixbr"])
        comp: dict = {"cidade": cfg["cidade"], "ixbr": None, "decix": {"ptt": code, "asn_direct": len(direct), "br_asn_direct": len(direct & br), "asn_origin_piso": len(origens)}, "externos": {}}
        if ix is not None:
            comp["ixbr"] = {"ptt": cfg["ixbr"], "asn_direct": len(ix["direct"]), "br_asn_origin": len(ix["br_origin"])}
            comp["interseccao_direct"] = {"ambos": len(direct & ix["direct"]), "so_decix": len(direct - ix["direct"]), "so_ixbr": len(ix["direct"] - direct),
                                          "pct_do_decix_no_ixbr": round(100 * len(direct & ix["direct"]) / len(direct), 1) if direct else None}
            comp["decix_br_origin_no_ixbr"] = {"decix": len(set(origens) & br), "ambos": len(set(origens) & br & ix["br_origin"]), "so_decix": len((set(origens) & br) - ix["br_origin"])}
            sem = sorted(direct - ix["direct"])
            comp["no_decix_sem_ixbr"] = {"total": len(sem), "asns": sem[:LIMITE_LISTA], "truncado": len(sem) > LIMITE_LISTA}
        for ext in cfg["externos"]:
            if ext in peeringdb:
                comp["externos"][ext] = {"membros_peeringdb": len(peeringdb[ext]), "ambos_decix_sessao": len(direct & set(peeringdb[ext])),
                                         **({"ambos_ixbr": len(set(peeringdb[ext]) & ix["direct"])} if ix is not None else {})}
        saida[code] = {
            "nome": cfg["nome"], "cidade": cfg["cidade"], "criterio": CRITERIOS, "rs": sorted(rs_por[code], key=lambda r: r["rs"]),
            "resumo": {"rs": len(rs_por[code]), "rs_consultados": sum(1 for r in rs_por[code] if r["consultado"]),
                       "sessoes": sum(m["up"] + m["down"] for m in mem.values()), "sessoes_up": sum(m["up"] for m in mem.values()), "sessoes_down": sum(m["down"] for m in mem.values()),
                       "membros": len(mem), "membros_up": len(direct), "asn_direct_count": len(direct), "br_asn_direct_count": len(direct & br),
                       "asn_origin_count": len(origens), "br_asn_origin_count": len(set(origens) & br)},
            "asn_direct": sorted(direct), "br_asns_direct": sorted(direct & br),
            "asn_origin": sorted(origens), "br_asns_origin": sorted(set(origens) & br),
            "rotas": {**leitura, "parcial": parcial, "cobertura": cob or None, "origens_por_asn_lidas": {str(a): origens[a] for a in sorted(origens)}},
            "membros": [mem[a] for a in sorted(mem)],
            "peeringdb": ({"cadastrados": len(pdb), "cadastrados_sem_sessao_up": sorted(set(pdb) - direct)[:LIMITE_LISTA], "sessao_up_sem_cadastro": sorted(direct - set(pdb))[:LIMITE_LISTA],
                           "cadastrados_sem_sessao_up_total": len(set(pdb) - direct), "sessao_up_sem_cadastro_total": len(direct - set(pdb))} if pdb else None),
            "comparacao_cidade": comp,
        }
    return saida


def _ixbr_publicado(base: Path, date_str: str, code: str) -> Optional[dict]:
    d = carregar_json(published_path(base, date_str, "ixps") / f"{code}.json")
    if not d:
        return None
    direct = _conjunto((d.get("v4") or {}).get("asn_direct")) | _conjunto((d.get("v6") or {}).get("asn_direct"))
    br_origin = _conjunto((d.get("v4") or {}).get("br_asns_origin")) | _conjunto((d.get("v6") or {}).get("br_asns_origin"))
    return {"direct": direct, "br_origin": br_origin}


def _membros_peeringdb(base: Path, date_str: str, code: str) -> Optional[dict[int, str]]:
    d = carregar_json(published_path(base, date_str, "external-ixps") / f"{code}.json")
    if not d:
        return None
    return {int(m["asn"]): m.get("name") or "" for m in d.get("members") or [] if m.get("asn") is not None}


def _br(base: Path, date_str: str) -> set[int]:
    out: set[int] = set()
    for e in carregar_json(published_path(base, date_str, "asns") / "index.json") or []:
        if e.get("is_br"):
            try:
                out.add(int(e["asn"]))
            except (KeyError, ValueError):
                pass
    return out


def publicar_decix_rs(base: Path, date_str: str, log) -> dict:
    resumo = normalized_path(base, date_str, "summary")
    sess = carregar_json_gz(resumo / "decix_rs_sessions.json.gz")
    if not sess or not sess.get("rs"):
        log.info("decix_rs_sessions.json.gz ausente ou sem route servers (bloqueio ou coleta falha): decix_rs não gerado")
        return {}
    rotas = carregar_json_gz(resumo / "decix_rs_rotas.json.gz")
    ixbr = {c["ixbr"]: x for c in CIDADES.values() if (x := _ixbr_publicado(base, date_str, c["ixbr"])) is not None}
    codigos = {c for code, cfg in CIDADES.items() for c in [code, *cfg["externos"]]}
    pdb = {c: m for c in sorted(codigos) if (m := _membros_peeringdb(base, date_str, c)) is not None}
    ixps = calcular(sess, rotas, _br(base, date_str), ixbr, pdb)
    destino = published_path(base, date_str) / "decix_rs"
    destino.mkdir(parents=True, exist_ok=True)
    cab = {"snapshot_date": date_str, "generated_at": now_iso(), "coletado_em": sess.get("generated_at"), "rotas_coletadas_em": (rotas or {}).get("generated_at"),
           "fonte": sess.get("fonte"), "versao_alice": sess.get("versao_alice"),
           "aviso": "Sessão BGP no route server e rotas lidas por vizinho em rodízio, medidas no Alice-LG do DE-CIX na data da coleta; não é tráfego nem relação comercial, e a origem é um piso.",
           "bloqueio": (rotas or {}).get("bloqueio") or sess.get("bloqueio")}
    gravar_json_gz(destino / "ixps.json.gz", {**cab, "ixps": ixps})
    log.info("decix_rs published", ixps=len(ixps))
    return {"ixps": len(ixps), "sessoes": sum(i["resumo"]["sessoes"] for i in ixps.values())}
