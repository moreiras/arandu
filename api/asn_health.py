# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
**Referência:** as regras vivem em `products/alerts/` (uma por arquivo, versionadas). Esta função é só a referência do teste de
paridade (`tests/products/test_t2_alertas_paridade.py`); nada a chama em produção.

Pontos de atenção (health checks) por ASN.

Cruza as fontes já integradas — Registro.br/RIR, full table global, RPKI,
PeeringDB, membros do IX.br e geolocalização — para apontar práticas
possivelmente mal feitas ou divergências entre fontes. Computado em tempo de
request a partir do documento do AS (já enriquecido com RPKI e ixp_member_codes)
e de índices auxiliares lidos da Store.

Cada alerta: {id, category, severity, title, detail, refs}
  severity ∈ {"critico", "aviso", "info"}
  category ∈ {"roteamento", "rpki", "v4v6", "presenca", "geo"}
"""

from __future__ import annotations

import ipaddress
from bisect import bisect_left
from typing import Optional

from core.alerta_ptt_proximo import deve_avaliar as _ptt_deve_avaliar, detalhe as _ptt_detalhe
from core.geo import haversine_km

# Raio (km) para considerar um AS "próximo" de um PTT onde não participa.
GEO_PROXIMITY_KM = 80.0
# maxLength - prefixlen a partir do qual um ROA é considerado folgado demais.
ROA_MAXLENGTH_SLACK = 8
# Razão global/RIR (e mínimo absoluto) para sinalizar desagregação excessiva.
DEAGG_RATIO = 4
DEAGG_MIN = 8

_SEVERITY_RANK = {"critico": 0, "aviso": 1, "info": 2}


def _net(prefix: str) -> Optional[ipaddress._BaseNetwork]:
    try:
        return ipaddress.ip_network(prefix, strict=False)
    except (ValueError, TypeError):
        return None


def _nets(prefixes) -> list:
    out = []
    for p in prefixes or []:
        n = _net(p)
        if n is not None:
            out.append(n)
    return out


def _reachable(p_net, starts_sorted: list, origin_map: dict) -> bool:
    """Um bloco alocado é alcançável se um agregado que o cobre, o próprio bloco,
    ou qualquer rota mais-específica dentro dele (de qualquer origem) aparece na
    full table."""
    # Agregado menos-específico que cobre o bloco
    minlen = 8 if p_net.version == 4 else 12
    n = p_net
    while n.prefixlen > minlen:
        n = n.supernet()
        if str(n) in origin_map:
            return True
    # Qualquer rota cujo início caia dentro do bloco (exato ou mais-específico)
    lo = int(p_net.network_address)
    hi = int(p_net.broadcast_address)
    i = bisect_left(starts_sorted, lo)
    return i < len(starts_sorted) and starts_sorted[i] <= hi


def compute_asn_alerts(store, date_str: str, asn: int, doc: dict) -> list[dict]:
    """Retorna a lista de pontos de atenção para o AS. Nunca levanta exceção
    fatal: cada checagem é isolada para não derrubar a página."""
    alerts: list[dict] = []

    def add(id, category, severity, title, detail, refs=None):
        alerts.append({
            "id": id,
            "category": category,
            "severity": severity,
            "title": title,
            "detail": detail,
            "refs": refs or {},
        })

    rir_v4 = doc.get("rir_prefixes_v4") or []
    rir_v6 = doc.get("rir_prefixes_v6") or []
    glob_v4 = doc.get("global_prefixes_v4") or []
    glob_v6 = doc.get("global_prefixes_v6") or []
    has_alloc = bool(rir_v4 or rir_v6)
    has_alloc_or_global = has_alloc or bool(glob_v4 or glob_v6)

    # ----- roteamento: sem IPv6 -------------------------------------------
    try:
        if (rir_v4 or glob_v4) and not (rir_v6 or glob_v6):
            add("sem_ipv6", "roteamento", "aviso",
                "Sem IPv6",
                "O AS tem presença em IPv4 mas nenhum prefixo IPv6 alocado nem "
                "anunciado. IPv6 é requisito de boas práticas para novas redes.")
    except Exception:
        pass

    # ----- roteamento: alcançabilidade global e anúncio por outro AS ------
    try:
        unreachable: list[str] = []
        by_other: list[dict] = []
        for afi, rir in (("v4", rir_v4), ("v6", rir_v6)):
            if not rir:
                continue
            origin_map = store.origin_by_prefix(date_str, afi)
            starts = store.announced_starts(date_str, afi)
            for p in rir:
                pn = _net(p)
                if pn is None:
                    continue
                if not _reachable(pn, starts, origin_map):
                    unreachable.append(p)
                origin = origin_map.get(p)
                if origin is not None and origin != asn:
                    by_other.append({"prefix": p, "origin_asn": origin})
        if unreachable:
            add("prefixo_inalcancavel", "roteamento", "aviso",
                "Bloco alocado não anunciado",
                f"{len(unreachable)} bloco(s) atribuído(s) pelo Registro.br não têm "
                "nenhuma rota (nem agregado que os cubra, nem mais-específico) na "
                "tabela de roteamento global — espaço alocado mas não anunciado.",
                {"prefixes": unreachable[:30]})
        if by_other:
            add("anuncio_por_outro_as", "roteamento", "aviso",
                "Bloco anunciado por outro AS",
                f"{len(by_other)} prefixo(s) deste AS são originados na full table "
                "por um ASN diferente. Pode ser anúncio gerenciado por terceiro — "
                "vale confirmar se é intencional.",
                {"items": by_other[:30]})
    except Exception:
        pass

    # ----- roteamento: desagregação excessiva -----------------------------
    try:
        for afi, rir, gcount in (
            ("IPv4", rir_v4, doc.get("global_prefixes_v4_count") or 0),
            ("IPv6", rir_v6, doc.get("global_prefixes_v6_count") or 0),
        ):
            base = len(rir)
            if gcount >= DEAGG_MIN and base > 0 and gcount >= DEAGG_RATIO * base:
                add(f"desagregacao_{afi.lower()}", "roteamento", "info",
                    f"Desagregação {afi} elevada",
                    f"{gcount} prefixos {afi} anunciados para {base} bloco(s) "
                    "alocado(s). Anunciar mais-específicos desnecessários infla a "
                    "tabela global; avalie agregar.",
                    {"global_count": gcount, "rir_count": base})
    except Exception:
        pass

    # ----- roteamento: prefixo anunciado fora da alocação RIR -------------
    try:
        outside: list[str] = []
        for afi, rir, glob in (("v4", rir_v4, glob_v4), ("v6", rir_v6, glob_v6)):
            if not rir:
                continue
            rir_nets = _nets(rir)
            for p in glob:
                gn = _net(p)
                if gn is None:
                    continue
                if not any(gn.version == r.version and (gn.subnet_of(r) or gn == r) for r in rir_nets):
                    outside.append(p)
        if outside:
            add("prefixo_fora_alocacao", "roteamento", "info",
                "Prefixo anunciado fora da alocação",
                f"{len(outside)} prefixo(s) anunciado(s) não estão contidos em "
                "nenhum bloco atribuído a este AS no Registro.br — pode ser espaço "
                "sub-alocado por um provedor ou de terceiro.",
                {"prefixes": outside[:30]})
    except Exception:
        pass

    # ----- rpki ------------------------------------------------------------
    try:
        roa_list = doc.get("roa_list")
        rpki_validation = doc.get("rpki_validation") or {}
        # sem_rpki só faz sentido quando a validação RPKI foi avaliada (roa_list
        # presente, mesmo que vazio) e o AS tem alocação própria.
        if roa_list is not None and has_alloc and len(roa_list) == 0:
            add("sem_rpki", "rpki", "aviso",
                "Sem RPKI (ROA)",
                "O AS possui blocos alocados mas nenhum ROA publicado. Sem RPKI, "
                "os prefixos ficam sujeitos a sequestro de rota sem proteção de "
                "origem.")

        if roa_list:
            # anúncios próprios marcados como inválidos pelo RPKI
            invalid = [p for p, st in rpki_validation.items() if st == "invalid"]
            if invalid:
                add("rpki_invalido", "rpki", "critico",
                    "Anúncio RPKI inválido",
                    f"{len(invalid)} prefixo(s) anunciado(s) estão como RPKI "
                    "inválidos (origem/maxLength não batem com os ROAs) e podem ser "
                    "descartados por redes que validam.",
                    {"prefixes": invalid[:30]})

            # cobertura parcial: alocações RIR sem nenhum ROA cobrindo
            roa_nets = []
            for r in roa_list:
                rn = _net(r.get("prefix", ""))
                if rn is not None:
                    roa_nets.append((rn, r.get("maxLength")))
            uncovered: list[str] = []
            for p in (rir_v4 + rir_v6):
                pn = _net(p)
                if pn is None:
                    continue
                covered = any(
                    pn.version == rn.version and (pn.subnet_of(rn) or pn == rn)
                    for rn, _ in roa_nets
                )
                if not covered:
                    uncovered.append(p)
            if uncovered and len(uncovered) < len(rir_v4 + rir_v6):
                add("rpki_cobertura_parcial", "rpki", "aviso",
                    "Cobertura RPKI parcial",
                    f"{len(uncovered)} bloco(s) alocado(s) não têm ROA cobrindo — "
                    "parte do espaço fica sem proteção de origem.",
                    {"prefixes": uncovered[:30]})

            # maxLength folgado demais
            loose = []
            for rn, maxlen in roa_nets:
                if isinstance(maxlen, int) and maxlen - rn.prefixlen >= ROA_MAXLENGTH_SLACK:
                    loose.append({"prefix": str(rn), "maxLength": maxlen})
            if loose:
                add("roa_maxlength_folgado", "rpki", "info",
                    "ROA com maxLength folgado",
                    f"{len(loose)} ROA(s) com maxLength muito acima do tamanho do "
                    "prefixo. Isso autoriza mais-específicos não anunciados e amplia "
                    "a superfície para sequestro por mais-específico.",
                    {"items": loose[:30]})
    except Exception:
        pass

    # ----- aspa ------------------------------------------------------------
    try:
        aspa_providers = doc.get("aspa_providers")
        # sem_aspa só faz sentido quando o AS tem ROAs mas não tem ASPA publicado.
        # ASPA é novo e a adoção é baixa, portanto é info, não aviso.
        if roa_list and aspa_providers is None:
            add("sem_aspa", "rpki", "aviso",
                "Sem ASPA",
                "O AS possui ROAs no RPKI mas não publicou nenhum objeto ASPA "
                "(Autonomous System Provider Authorization). O ASPA declara os "
                "upstreams autorizados e permite validação de AS_PATH — sua "
                "ausência não expõe o AS a risco imediato, mas a publicação é "
                "recomendada à medida que a adoção cresce.")
    except Exception:
        pass

    # ----- v6/v4: políticas divergentes -----------------------------------
    try:
        presence = doc.get("ixp_presence") or {}
        v4_only, v6_only = [], []
        for code, pres in presence.items():
            d4 = bool((pres.get("v4") or {}).get("direct"))
            d6 = bool((pres.get("v6") or {}).get("direct"))
            if d4 and not d6:
                v4_only.append(code)
            elif d6 and not d4:
                v6_only.append(code)
        # Só sinaliza quando o AS é capaz de IPv6 (tem v6) mas faz peering
        # assimétrico entre as famílias num número relevante de IXPs.
        has_v6 = bool(rir_v6 or glob_v6)
        if has_v6 and (v4_only or v6_only):
            parts = []
            if v4_only:
                parts.append(f"{len(v4_only)} IXP(s) com peering só IPv4")
            if v6_only:
                parts.append(f"{len(v6_only)} IXP(s) com peering só IPv6")
            add("politica_v4v6_divergente", "v4v6", "info",
                "Políticas IPv6 e IPv4 divergentes",
                "Peering assimétrico entre as famílias: " + "; ".join(parts) +
                ". Tendo IPv6, o ideal é fazer peering nas duas famílias nos mesmos IXPs.",
                {"v4_only": sorted(v4_only), "v6_only": sorted(v6_only)})
    except Exception:
        pass

    # ----- presença: PeeringDB / IRR / membro sem peering / single-homed --
    try:
        member_codes = set(doc.get("ixp_member_codes") or [])
        pdb = doc.get("pdb") or {}
        pdb_registered = bool(doc.get("pdb_registered"))

        if member_codes and not pdb_registered:
            add("sem_peeringdb", "presenca", "aviso",
                "Sem cadastro no PeeringDB",
                "O AS é membro de PTT(s) do IX.br mas não tem registro no "
                "PeeringDB, o que dificulta o estabelecimento de peering.")

        if pdb_registered and not pdb.get("irr_as_set"):
            add("sem_irr_as_set", "presenca", "info",
                "Sem AS-SET no IRR",
                "O cadastro no PeeringDB não informa um as-set no IRR. Sem objeto "
                "IRR, peers e provedores não conseguem montar filtros de prefixo "
                "automaticamente.")

        presence = doc.get("ixp_presence") or {}
        not_peering = []
        for code in member_codes:
            pres = presence.get(code) or {}
            d4 = bool((pres.get("v4") or {}).get("direct"))
            d6 = bool((pres.get("v6") or {}).get("direct"))
            if not d4 and not d6:
                not_peering.append(code)
        if not_peering:
            add("membro_sem_peering", "presenca", "aviso",
                "Membro de PTT sem peering observado",
                f"{len(not_peering)} PTT(s) onde o AS é membro registrado mas não "
                "aparece fazendo peering no route server — possível "
                "subaproveitamento ou má configuração.",
                {"ixps": sorted(not_peering)})

        su4 = doc.get("single_upstream_v4")
        su6 = doc.get("single_upstream_v6")
        if su4 is not None or su6 is not None:
            add("single_homed", "presenca", "aviso",
                "Conectividade single-homed",
                "O AS aparenta depender de um único upstream "
                + ("(IPv4)" if su4 is not None and su6 is None else
                   "(IPv6)" if su6 is not None and su4 is None else "(IPv6 e IPv4)")
                + " na tabela global — risco de resiliência.",
                {"upstream_v4": su4, "upstream_v6": su6})

        # declarado no PDB muito abaixo do observado → max-prefix arriscado
        for afi, declared_key, gcount in (
            ("IPv4", "info_prefixes4", doc.get("global_prefixes_v4_count") or 0),
            ("IPv6", "info_prefixes6", doc.get("global_prefixes_v6_count") or 0),
        ):
            declared = pdb.get(declared_key)
            if isinstance(declared, int) and declared > 0 and gcount > 2 * declared:
                add(f"pdb_prefixos_divergente_{afi.lower()}", "presenca", "info",
                    f"Prefixos {afi} declarados no PeeringDB abaixo do real",
                    f"PeeringDB declara {declared} prefixos {afi}, mas {gcount} são "
                    "observados na full table. Peers que usam esse número como "
                    "max-prefix podem derrubar a sessão.",
                    {"declared": declared, "observed": gcount})
    except Exception:
        pass

    # ----- geo: PTT próximo sem participação ------------------------------
    try:
        coords = store.asn_coords(date_str, asn) if _ptt_deve_avaliar(store, date_str, asn, doc) else None
        if coords:
            lat, lon = coords
            member_codes = set(doc.get("ixp_member_codes") or [])
            member_codes |= set((doc.get("ixp_presence") or {}).keys())
            pix_cfg = store._load_pix_config()
            ixp_names = {row.get("code"): row.get("name") for row in store.ixp_index(date_str)}
            near = []
            for code, points in pix_cfg.items():
                if code in member_codes:
                    continue
                dmin = min(haversine_km(lat, lon, pt["lat"], pt["lon"]) for pt in points)
                if dmin <= GEO_PROXIMITY_KM:
                    near.append({"code": code, "name": ixp_names.get(code, code),
                                 "dist_km": round(dmin, 1)})
            near.sort(key=lambda x: x["dist_km"])
            if near:
                add("ptt_proximo_sem_participar", "geo", "aviso",
                    "PTT próximo sem participação",
                    _ptt_detalhe(near, int(GEO_PROXIMITY_KM)),
                    {"ixps": near[:10]})
    except Exception:
        pass

    # ----- BGP: routing_analysis (agregação, filtráveis, prepend, loop de AS) ----------
    try:
        ra = store.routing_analysis(date_str)
        if ra:
            # Potencial de agregação > 90% (INFO)
            for row in (ra.get("aggregation_by_asn") or []):
                if row.get("asn") != asn:
                    continue
                pct = row.get("savings_path_pct", 0)
                if pct > 90:
                    afi = row.get("afi", "")
                    add(f"agregacao_elevada_{afi}", "roteamento", "info",
                        f"Potencial de agregação {afi.upper()} > 90%",
                        f"Análise de agregação indica que {pct}% dos prefixos "
                        f"{afi.upper()} poderiam ser eliminados agrupando blocos "
                        "contíguos (RFC 4632). Anunciar mais-específicos desnecessários "
                        "infla a tabela global.",
                        {"current": row.get("current"),
                         "aggregated": row.get("by_origin"),
                         "savings_pct": pct})

            # Prefixos potencialmente filtráveis exceto /32 (v4) e /64 (v6) (AVISO)
            too_spec = ra.get("too_specific") or {}
            filterable: list[str] = []
            for r in (too_spec.get("v4") or []):
                if r.get("origin_as") != asn:
                    continue
                n = _net(r.get("prefix", ""))
                if n and n.prefixlen != 32:
                    filterable.append(r["prefix"])
            for r in (too_spec.get("v6") or []):
                if r.get("origin_as") != asn:
                    continue
                n = _net(r.get("prefix", ""))
                if n and n.prefixlen != 64:
                    filterable.append(r["prefix"])
            if filterable:
                add("prefixos_filtraveis", "roteamento", "aviso",
                    "Prefixos potencialmente filtráveis",
                    f"{len(filterable)} prefixo(s) excedem os limites convencionais "
                    "(IPv6 >/48, IPv4 >/24) e podem ser descartados por operadores "
                    "de backbone. Se há um agregado menos específico cobrindo o espaço, "
                    "o tráfego seria absorvido por ele; do contrário, o descarte "
                    "causaria blackhole.",
                    {"prefixes": filterable[:30]})

            # Repetições médias de prepend > 2x e Loop de AS (requerem Fase 2 AS_PATH)
            as_path = ra.get("as_path_stats") or {}
            if as_path:
                # Prepend excessivo (AVISO)
                for row in (as_path.get("top_prependers") or []):
                    if row.get("asn") != asn:
                        continue
                    avg_excess = row.get("avg_excess", 0)
                    if avg_excess > 2:
                        afi = row.get("afi", "")
                        add(f"prepend_excessivo_{afi}", "roteamento", "aviso",
                            f"Prepend excessivo no AS_PATH ({afi.upper()})",
                            f"A média de repetições de prepend em {afi.upper()} é "
                            f"{avg_excess:.1f}x nas rotas deste AS. Prepend excessivo "
                            "pode causar seleção de caminho subótima por peers e "
                            "provedores; o valor recomendado é ≤ 2.",
                            {"afi": afi,
                             "avg_excess": avg_excess,
                             "routes_with_prepend": row.get("routes_with_prepend")})

                # Loop de AS (AVISO)
                loop_prefixes = [
                    r["prefix"]
                    for r in (as_path.get("hygiene_issues") or [])
                    if r.get("origin_as") == asn and r.get("issue") == "as_loop"
                ]
                if loop_prefixes:
                    add("as_loop_detectado", "roteamento", "aviso",
                        "Loop de AS detectado",
                        f"{len(loop_prefixes)} prefixo(s) têm AS_PATH com loop "
                        "(mesmo ASN aparece mais de uma vez de forma não-consecutiva "
                        "no caminho). Pode indicar má configuração de rota ou "
                        "manipulação incorreta de AS_PATH.",
                        {"prefixes": loop_prefixes[:30]})
    except Exception:
        pass

    alerts.sort(key=lambda a: (_SEVERITY_RANK.get(a["severity"], 9), a["category"]))
    return alerts
