# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Técnico do grupo econômico: os ASes do grupo, IPv6, validação RPKI, trânsito e presença nos PTTs.

Soma o que é aditivo (prefixos originados, usuários estimados) e une o que é conjunto (PTTs, provedores). Usuários da APNIC se repetem entre ASes da mesma
operadora quando há prefixos anunciados por mais de um AS: é estimativa, e o bloco diz isso. A validação RPKI é a do looking glass (válido, inválido, sem ROA).
Para grupo com muitos ASes só os `LIMITE_ASES` maiores por usuários entram no detalhe, e o número omitido é informado.
"""
from __future__ import annotations

from collections import Counter

LIMITE_ASES = 40


def tecnico_do_grupo(g: dict, docs: dict[int, dict]) -> dict:
    asns = sorted(set(g.get("asns") or []))
    presentes = {a: docs[a] for a in asns if a in docs}
    ordem = sorted(presentes, key=lambda a: (-(presentes[a].get("apnic_users") or 0), a))
    usados = ordem[:LIMITE_ASES]
    linhas, rpki, ptts, provedores = [], Counter(), {}, Counter()
    v4 = v6 = usuarios = usuarios_v6 = 0
    multihomed = 0
    for a in usados:
        d = presentes[a]
        c = Counter((v.get("status") if isinstance(v, dict) else v) for v in (d.get("rpki_validation") or {}).values())
        rpki.update(c)
        n4, n6 = d.get("global_prefixes_v4_count") or 0, d.get("global_prefixes_v6_count") or 0
        v4 += n4
        v6 += n6
        usuarios += d.get("apnic_users") or 0
        usuarios_v6 += d.get("apnic_v6_users") or 0
        multihomed += 1 if (d.get("is_multihomed_v4") or d.get("is_multihomed_v6")) else 0
        for p in d.get("ixps_direct") or []:
            ptts.setdefault(p, []).append(a)
        for u in {(u if isinstance(u, int) else u.get("asn")) for u in (d.get("upstreams_global_v4") or []) + (d.get("upstreams_global_v6") or [])}:
            provedores[u] += 1                                               # um AS do grupo conta uma vez por provedor, em v6 e v4
        validados = sum(c.values())
        linhas.append({"asn": a, "nome": d.get("name"), "usuarios": d.get("apnic_users"), "pct_v6": d.get("apnic_v6_pct_as"), "prefixos_v4": n4, "prefixos_v6": n6, "tem_ipv6": bool(d.get("has_ipv6")),
                       "roa_valido_pct": round(100 * c.get("valid", 0) / validados, 1) if validados else None, "ptts_diretos": len(d.get("ixps_direct") or [])})
    validados = sum(rpki.values())
    return {
        "grupo_id": g["grupo_id"], "asns_total": len(asns), "asns_com_dado": len(presentes), "asns_detalhados": len(usados), "asns_omitidos": max(0, len(presentes) - len(usados)),
        "visibilidade_bgp": bool(v4 or v6),
        "prefixos": {"v4": v4, "v6": v6},
        "ipv6": {"asns_com_ipv6": sum(1 for r in linhas if r["tem_ipv6"]), "usuarios": usuarios, "usuarios_v6": usuarios_v6, "pct_v6": round(100 * usuarios_v6 / usuarios, 1) if usuarios else None},
        "rpki": {"validados": validados, "valido": rpki.get("valid", 0), "invalido": sum(v for k, v in rpki.items() if k and k.startswith("invalid")), "sem_roa": rpki.get("not_found", 0),
                 "valido_pct": round(100 * rpki.get("valid", 0) / validados, 1) if validados else None},
        "transito": {"asns_multihomed": multihomed, "provedores": [{"asn": a, "asns_do_grupo": n} for a, n in sorted(provedores.items(), key=lambda kv: (-kv[1], kv[0])) if a][:10]},
        "ptts": [{"ixp": p, "asns": sorted(a)} for p, a in sorted(ptts.items())],
        "por_asn": sorted(linhas, key=lambda r: r["asn"]),
        "natureza": "fato observado (BGP, RPKI, looking glass do IX.br) e estimativa (usuários APNIC), somados por agrupamento inferido",
        "limites": "O grupo é inferido do quadro societário. Prefixos e validação RPKI são o que o looking glass viu na data da coleta; usuários APNIC são estimativa e podem se repetir entre ASes da mesma "
                   "operadora; presença em PTT é sessão direta observada, não tráfego. Ordem alfabética ou por número de AS: sem ranking de desempenho.",
    }
