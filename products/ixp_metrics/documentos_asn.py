# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Documento de cada ASN (base do compose)."""
from __future__ import annotations

import json
from ipaddress import ip_network
from pathlib import Path
from core import compose
from core.common import now_iso, published_path

from products.ixp_metrics.entradas import _load_apnic_pop, _load_geo_orgs, _load_geo_prefixes, _load_peeringdb_ixps, _load_peeringdb_networks


def gerar_documentos_asn(
    date_str: str,
    base: Path,
    asn_index: dict[int, dict],
    nicbr_map: dict[int, dict],
    log,
    lacnic_br_asns: set[int] | None = None,
    bulk_names: dict[int, str] | None = None,
) -> dict:
    """Gera published/{date}/asns/{asn}.json para cada ASN BR e cada ASN visto nos IXPs.

    Universo de ASNs: lacnic_br_asns ∪ asn_index.keys()
    Isso inclui ASNs não-BR que aparecem nos IXPs (para que o frontend possa exibir
    informações de qualquer ASN visto nos dados, não apenas os brasileiros).

    Hierarquia de nomes: Registro.br → PeeringDB → `asn_names` (RIPE NCC bulk)

    Campos de conectividade:
      upstreams/downstreams         — ASNs adjacentes nos AS_PATHs dos IXPs (v4+v6 unidos)
      upstreams_v4 / downstreams_v4 — idem separado por AFI
      upstreams_global_v4 / _v6     — adjacências do grafo RouteViews (visão global)
      is_multihomed_v4 / _v6        — True se mais de um upstream global distinto
      single_upstream_v4 / _v6      — o único upstream global (se exatamente um)

    Args:
        date_str:       Data do snapshot (YYYY-MM-DD)
        base:           Diretório raiz dos dados
        asn_index:      Resultado de _build_asn_index
        nicbr_map:      {asn: {"name", "cnpj", "prefixes_v4", "prefixes_v6"}} (`registro_br`)
        log:            Logger estruturado
        lacnic_br_asns: Set de ASNs BR (`lacnic_delegated`); se None, usa nicbr_map.keys()
        bulk_names:     {asn_int: nome} do `asn_names` (RIPE NCC); None = omite fallback de nome

    Returns:
        {"ok": int, "errors": int}
    """
    # is_br: usa LACNIC delegated se disponível, fallback para nicbr_map keys
    br_asns_set = lacnic_br_asns if lacnic_br_asns else set(nicbr_map.keys())
    _bulk = bulk_names or {}
    # Universo de ASNs: BR (delegated ou `registro_br`) ∪ presentes em algum IXP
    all_asns = br_asns_set | set(asn_index.keys())

    # Geolocalização — carrega se disponível (opcional; não bloqueia se ausente)
    geo_orgs = _load_geo_orgs(base, date_str)
    if geo_orgs:
        log.info("geo_orgs loaded", asns=len(geo_orgs))
    geo_prefixes = _load_geo_prefixes(base, date_str)
    if geo_prefixes:
        log.info("geo_prefixes loaded", prefixes=len(geo_prefixes))

    # PeeringDB — carrega se disponível (opcional; não bloqueia se ausente)
    pdb_ixps_data = _load_peeringdb_ixps(base, date_str)
    pdb_per_asn   = pdb_ixps_data.get("per_asn", {})      # str(asn) → {external, ixbr}
    pdb_nets_data = _load_peeringdb_networks(base, date_str)
    pdb_networks  = pdb_nets_data.get("networks", {})      # str(asn) → metadata
    if pdb_per_asn:
        log.info("peeringdb_ixps loaded", asns_with_pdb=len(pdb_per_asn))
    if pdb_networks:
        log.info("peeringdb_networks loaded", registered=len(pdb_networks))

    # APNIC Labs — estimativas de população (`apnic_pop`; opcional)
    apnic_pop = _load_apnic_pop(base, date_str)
    if apnic_pop:
        log.info("apnic_pop loaded", asns=len(apnic_pop))

    pub_dir = published_path(base, date_str, "asns")
    pub_dir.mkdir(parents=True, exist_ok=True)

    ok = errors = 0
    generated_at = now_iso()

    fragmento = None
    if compose.ativo():
        _frag_ctx = compose.gravar_fragmento(base, date_str, "base")
        fragmento = _frag_ctx.__enter__()

    for asn in sorted(all_asns):
        try:
            entry = asn_index.get(asn, {})
            br_info = nicbr_map.get(asn, {})

            prefixes_ft_v4 = entry.get("prefixes_ft", {}).get("v4", [])
            prefixes_ft_v6 = entry.get("prefixes_ft", {}).get("v6", [])

            # Prefixos declarados no `registro_br` (fonte de verdade para ASNs BR)
            rir_v4 = br_info.get("prefixes_v4", [])
            rir_v6 = br_info.get("prefixes_v6", [])

            # IXP presence
            ixps_direct = sorted(entry.get("ixps_direct", set()))
            ixps_origin = sorted(entry.get("ixps_origin", set()))
            all_ixps_for_asn = sorted(set(ixps_direct) | set(ixps_origin))

            ixp_presence: dict[str, dict] = {}
            for ixp_code in all_ixps_for_asn:
                ixp_presence[ixp_code] = {}
                ixp_pfx = entry.get("prefixes_ixp", {}).get(ixp_code, {})
                for afi in ("v4", "v6"):
                    ixp_presence[ixp_code][afi] = {
                        "direct": ixp_code in entry.get("ixps_direct", set()),
                        "origin": ixp_code in entry.get("ixps_origin", set()),
                        "prefixes": ixp_pfx.get(afi, []),
                    }

            has_ipv6 = bool(prefixes_ft_v6) or bool(rir_v6) or any(
                ixp_presence[c]["v6"]["prefixes"]
                for c in ixp_presence
            )

            # Relações por AFI — IXPs
            ups_v4 = sorted(entry.get("upstreams_v4", set()))
            ups_v6 = sorted(entry.get("upstreams_v6", set()))
            dns_v4 = sorted(entry.get("downstreams_v4", set()))
            dns_v6 = sorted(entry.get("downstreams_v6", set()))

            # Relações por AFI — RouteViews (visão global)
            ups_global_v4 = sorted(entry.get("upstreams_global_v4", set()))
            ups_global_v6 = sorted(entry.get("upstreams_global_v6", set()))
            dns_global_v4 = sorted(entry.get("downstreams_global_v4", set()))
            dns_global_v6 = sorted(entry.get("downstreams_global_v6", set()))

            # Multi-homing: mais de um upstream distinto na visão global
            is_multihomed_v4 = len(ups_global_v4) > 1
            is_multihomed_v6 = len(ups_global_v6) > 1

            # Single-upstream: exatamente um upstream global (dependência exclusiva)
            single_upstream_v4 = ups_global_v4[0] if len(ups_global_v4) == 1 else None
            single_upstream_v6 = ups_global_v6[0] if len(ups_global_v6) == 1 else None

            # PeeringDB — presença em IXPs externos
            pdb_entry    = pdb_per_asn.get(str(asn), {})
            ext_ixps     = pdb_entry.get("external", [])
            pdb_net      = pdb_networks.get(str(asn))
            pdb_registered = pdb_net is not None

            # APNIC Labs — estimativas de usuários
            apnic = apnic_pop.get(asn)
            apnic_users      = apnic.get("users")      if apnic else None
            apnic_users_pct  = apnic.get("users_pct_cc") if apnic else None
            apnic_v6_users   = apnic.get("v6_users")   if apnic else None
            apnic_v6_pct_as  = apnic.get("v6_pct_as")  if apnic else None

            # Razão usuários / espaço IPv4 anunciado na full table (proxy de CGNAT).
            # Usa os prefixos efetivamente anunciados (prefixes_ft_v4 = global_prefixes_v4),
            # não os alocados pelo RIR — captura o espaço real em uso pelo AS.
            announced_ipv4_addresses: int | None = None
            users_per_ip: float | None = None
            if prefixes_ft_v4:
                try:
                    announced_ipv4_addresses = sum(
                        2 ** (32 - ip_network(p, strict=False).prefixlen)
                        for p in prefixes_ft_v4
                    )
                    if announced_ipv4_addresses and apnic_users:
                        users_per_ip = round(apnic_users / announced_ipv4_addresses, 2)
                except Exception:
                    pass

            # Razão usuários IPv6 / espaço IPv6 anunciado (em /48 equivalentes).
            announced_ipv6_48s: int | None = None
            users_per_v6_48: float | None = None
            if prefixes_ft_v6:
                try:
                    announced_ipv6_48s = sum(
                        2 ** max(0, 48 - ip_network(p, strict=False).prefixlen)
                        for p in prefixes_ft_v6
                    )
                    if announced_ipv6_48s and apnic_v6_users:
                        users_per_v6_48 = round(apnic_v6_users / announced_ipv6_48s, 2)
                except Exception:
                    pass

            doc = {
                "asn": asn,
                "snapshot_date": date_str,
                "generated_at": generated_at,
                "is_br": asn in br_asns_set,
                # Prioridade: Registro.br > PeeringDB > bulk (Potaroo/autnums.txt)
                "name": (
                    br_info.get("name")
                    or (pdb_net.get("name") if pdb_net else "")
                    or _bulk.get(asn, "")
                ),
                "cnpj": br_info.get("cnpj", ""),
                # Prefixos atribuídos pelo RIR/Registro.br (fonte autoritativa de alocação)
                "rir_prefixes_v4": rir_v4,
                "rir_prefixes_v6": rir_v6,
                "rir_prefixes_v4_count": len(rir_v4),
                "rir_prefixes_v6_count": len(rir_v6),
                # Prefixos observados na tabela de roteamento global
                "global_prefixes_v4": prefixes_ft_v4,
                "global_prefixes_v6": prefixes_ft_v6,
                "global_prefixes_v4_count": len(prefixes_ft_v4),
                "global_prefixes_v6_count": len(prefixes_ft_v6),
                "has_ipv6": has_ipv6,
                # Presença nos IXPs do IX.br
                "ixps_direct": ixps_direct,
                "ixps_origin": ixps_origin,
                "ixp_presence": ixp_presence,
                # Relações inferidas dos IXPs — separadas por AFI
                "upstreams_v4": ups_v4,
                "upstreams_v6": ups_v6,
                "downstreams_v4": dns_v4,
                "downstreams_v6": dns_v6,
                # União v4+v6 dos IXPs — mantida para compatibilidade com clientes existentes
                "upstreams": sorted(set(ups_v4) | set(ups_v6)),
                "downstreams": sorted(set(dns_v4) | set(dns_v6)),
                # Relações inferidas do RouteViews (visão global, todos os vantage points)
                "upstreams_global_v4": ups_global_v4,
                "upstreams_global_v6": ups_global_v6,
                "downstreams_global_v4": dns_global_v4,
                "downstreams_global_v6": dns_global_v6,
                # Características de conectividade derivadas do grafo global
                "is_multihomed_v4": is_multihomed_v4,
                "is_multihomed_v6": is_multihomed_v6,
                "single_upstream_v4": single_upstream_v4,
                "single_upstream_v6": single_upstream_v6,
                # PeeringDB
                "pdb_registered": pdb_registered,
                "external_ixps": ext_ixps,
                "pdb": pdb_net,
                # Geolocalização da organização (`cnpj_geo`; None se não disponível)
                "geo_org": geo_orgs.get(str(asn)) if geo_orgs else None,
                # Geolocalização por prefixo (`prefix_geo` — só prefixos com correspondência exata em `registro_br`)
                "geo_prefixes_v4": (
                    {p: geo_prefixes[p] for p in prefixes_ft_v4 if p in geo_prefixes}
                    if geo_prefixes else {}
                ),
                "geo_prefixes_v6": (
                    {p: geo_prefixes[p] for p in prefixes_ft_v6 if p in geo_prefixes}
                    if geo_prefixes else {}
                ),
                # APNIC Labs — estimativas de usuários (janela de 60 dias)
                "apnic_users": apnic_users,
                "apnic_users_pct_cc": apnic_users_pct,
                "apnic_v6_users": apnic_v6_users,
                "apnic_v6_pct_as": apnic_v6_pct_as,
                # Derivado: usuários por endereço IPv4 anunciado (proxy de intensidade CGNAT)
                "announced_ipv4_addresses": announced_ipv4_addresses,
                "users_per_ip": users_per_ip,
                # Derivado: usuários IPv6 por /48 anunciado
                "announced_ipv6_48s": announced_ipv6_48s,
                "users_per_v6_48": users_per_v6_48,
            }

            if fragmento is not None:
                fragmento.escrever(asn, doc)          # ARANDU_COMPOSE=on: o `compose` grava o documento final
            else:
                out_file = pub_dir / f"{asn}.json"
                out_file.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            ok += 1
        except Exception as exc:
            log.error("p3 error", asn=asn, error=str(exc))
            errors += 1

    if fragmento is not None:
        _frag_ctx.__exit__(None, None, None)
    log.info("p3 done", total=ok + errors, ok=ok, errors=errors)
    return {"ok": ok, "errors": errors}
