# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Interconexão mensurável e alcance de CDN.

Só o que os dados públicos mostram: PTTs onde o AS origina prefixos sem ser par direto (e quem os carrega nos caminhos observados), sessões ausentes ou só de uma família de IP nos route servers
do IX.br, rotas rejeitadas e ações de communities declaradas. **Nunca** diz "o AS não troca tráfego com B": peering bilateral não é visível nesses dados. O alcance de CDN usa os membros
registrados nos PTTs onde a CDN tem presença e os usuários estimados pela APNIC; não mede tráfego.
"""
from __future__ import annotations

from collections import Counter
from typing import Optional

LIMITES_OPORTUNIDADES = ("Só o que os dados públicos mostram: originação vista no looking glass do IX.br, sessões dos route servers (Alice-LG) e rejeições e communities coletadas. "
                         "Peering bilateral (sessão direta entre dois ASes) não aparece nesses dados: nada aqui diz com quem o AS troca ou deixa de trocar tráfego, nem que uma sessão ausente seja um problema. "
                         "Cada item é um fato observado na data da coleta, não uma recomendação.")
LIMITES_ALCANCE = ("Fração dos usuários estimados pela APNIC (ASes do Brasil, por UF da sede do AS) em ASes membros de algum PTT do IX.br onde a CDN também é membro (lista de membros do IX.br). "
                   "Estimativa: usuários se repetem entre ASes da mesma operadora, membro registrado não quer dizer que o tráfego da CDN passe ali, e não mede tráfego nem qualidade.")


def _carregadores(paths: list, topo: int = 3) -> list[dict]:
    """Quem entrega o AS no PTT: o primeiro AS de cada caminho observado (o par direto do PTT), contado."""
    c = Counter(p[0] for p in paths if isinstance(p, list) and len(p) > 1)
    return [{"asn": a, "caminhos": n} for a, n in c.most_common(topo)]


def oportunidades(doc: dict, rs_asn: Optional[dict], rs_ixps: Optional[dict], pol_asn: Optional[dict], ixps: dict[str, dict], uf_as: Optional[str], km_por_ptt: Optional[dict[str, float]] = None) -> dict:
    """Fatos de interconexão de um AS, na ordem em que a pessoa vai querer ler. `ixps` = {código: {nome, uf}}."""
    origem = []
    for code, pres in (doc.get("ixp_presence") or {}).items():
        fams = [afi for afi in ("v4", "v6") if (pres.get(afi) or {}).get("origin") and not (pres.get(afi) or {}).get("direct")]
        if not fams:
            continue
        info = ixps.get(code, {})
        paths = (doc.get("ixp_paths") or {}).get(code) or []
        origem.append({"ixp": code, "nome": info.get("nome", code), "uf": info.get("uf"), "familias": fams, "mesma_uf": bool(uf_as and info.get("uf") == uf_as), "carregadores": _carregadores(paths),
                       "km_da_sede": (km_por_ptt or {}).get(code)})
    # proximidade: do PTT mais perto da sede do AS para o mais longe (linha reta do endereço da sede, não do usuário); sem coordenada, cai para a UF
    origem.sort(key=lambda x: (x["km_da_sede"] is None, x["km_da_sede"] if x["km_da_sede"] is not None else 0, not x["mesma_uf"], -len(x["familias"]), x["ixp"]))

    sessoes = []
    for code, e in ((rs_asn or {}).get("ixps") or {}).items():
        afis = {s["afi"] for s in e.get("lista", [])}
        rs_afis = {r["afi"] for r in ((rs_ixps or {}).get("ixps", {}).get(code, {}).get("rs") or [])}
        info = ixps.get(code, {})
        if e.get("cadastrado") and not e.get("sessoes"):
            sessoes.append({"ixp": code, "nome": info.get("nome", code), "situacao": "sem_sessao", "rotulo": "cadastrado sem sessão nos route servers (pode haver peering bilateral)"})
        else:
            for faltante in sorted(rs_afis - afis):
                if afis:
                    sessoes.append({"ixp": code, "nome": info.get("nome", code), "situacao": f"sem_{faltante}", "rotulo": f"sessão só em {'/'.join(sorted(a.upper() for a in afis))}; o PTT tem route server {faltante.upper()}"})

    rej = []
    for code, e in ((pol_asn or {}).get("ixps") or {}).items():
        info = ixps.get(code, {})
        r = e.get("rejeicoes") or {}
        pol = e.get("politica") or {}
        if not r.get("rotas") and not pol.get("acoes"):
            continue
        rej.append({"ixp": code, "nome": info.get("nome", code), "rotas_rejeitadas": r.get("rotas", 0),
                    "motivos": [{"rotulo": m.get("rotulo"), "codigo": m.get("codigo"), "rotas": m.get("rotas")} for m in (r.get("motivos") or [])[:3] if m.get("classe") == "rejeicao"],
                    "perfil": pol.get("perfil"), "perfil_inferido": pol.get("perfil_inferido"), "acoes": sorted((pol.get("acoes") or {}).keys())})
    rej.sort(key=lambda x: (-x["rotas_rejeitadas"], x["ixp"]))
    return {"asn": doc["asn"], "limites": LIMITES_OPORTUNIDADES, "uf_sede": uf_as, "usuarios_estimados": doc.get("apnic_users"),
            "carregadores_disponiveis": any((doc.get("ixp_paths") or {}).get(o["ixp"]) for o in origem),
            "origem_sem_direto": origem, "sessoes": sessoes, "rejeicoes": rej,
            "resumo": {"origem_sem_direto": len(origem), "sem_sessao": sum(1 for s in sessoes if s["situacao"] == "sem_sessao"), "sessao_parcial": sum(1 for s in sessoes if s["situacao"] != "sem_sessao"),
                       "ptts_com_rejeicao": sum(1 for r in rej if r["rotas_rejeitadas"])}}


def alcance_cdns(cdns: list[dict], membros: dict[int, list[str]], usuarios: dict[int, int], uf_de: dict[int, str]) -> dict:
    """Por CDN: usuários BR (por UF da sede do AS) em ASes membros de algum PTT do IX.br onde a CDN está. `membros` = {asn: [PTTs onde é membro]}."""
    total_uf: dict[str, int] = {}
    for a, u in usuarios.items():
        if uf_de.get(a):
            total_uf[uf_de[a]] = total_uf.get(uf_de[a], 0) + u
    total = sum(total_uf.values())
    out = []
    for c in cdns:
        ptts = set(c.get("ixbr") or [])
        if not ptts:
            continue
        alc_uf: dict[str, int] = {}
        for a, u in usuarios.items():
            uf = uf_de.get(a)
            if uf and ptts & set(membros.get(a, [])):
                alc_uf[uf] = alc_uf.get(uf, 0) + u
        alc = sum(alc_uf.values())
        out.append({"name": c["name"], "ptts": sorted(ptts), "usuarios_alcancados": alc, "pct": round(100 * alc / total, 1) if total else None,
                    "por_uf": {uf: {"usuarios": total_uf[uf], "alcancados": alc_uf.get(uf, 0), "pct": round(100 * alc_uf.get(uf, 0) / total_uf[uf], 1)} for uf in sorted(total_uf)}})
    out.sort(key=lambda x: (-(x["pct"] or 0), x["name"]))
    return {"limites": LIMITES_ALCANCE, "usuarios_br_com_uf": total, "cdns": out}
