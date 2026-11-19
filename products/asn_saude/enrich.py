# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Enriquecimento do documento de ASN (augmentação cara do GET /asns/{asn}).

Centraliza a lógica da rota: completa metadados de
relações (`path_node_meta`), valida RPKI (`roa_list` + `rpki_validation`),
adiciona objetos ASPA (`aspa_providers` + `aspa_customers`),
adiciona membros de IX.br (`ixp_member_codes`) e os pontos de atenção (`alerts`).

Usado em dois lugares:
- em tempo de request, via `Store.asn_full` (com memoização) — fallback para
  snapshots cujos arquivos ainda não foram pré-enriquecidos;
- no publish (`snapshot_builder.build_asn_health_for_asns`), gravando o resultado
  dentro de cada `asns/{asn}.json` para que a API só leia e sirva.

`enrich_asn_document` é idempotente: se o doc já tem `alerts`, retorna como está.
"""
from __future__ import annotations

_RELATION_FIELDS = (
    "upstreams_v4", "upstreams_v6", "upstreams_global_v4", "upstreams_global_v6",
    "downstreams_v4", "downstreams_v6", "downstreams_global_v4", "downstreams_global_v6",
)


def enrich_asn_document(store, date_str: str, asn: int, doc: dict) -> dict:
    """Retorna uma cópia de `doc` com a augmentação cara aplicada.

    Não levanta exceção: cada etapa é isolada para nunca derrubar a página.
    `store` é uma instância de `api.store.Store` apontando para o snapshot.
    """
    # Já enriquecido (ex.: pré-computado no publish) — nada a fazer.
    if "alerts" in doc:
        return doc

    doc = dict(doc)

    member_codes = store.asn_member_ixps(date_str, asn)
    if member_codes:
        doc["ixp_member_codes"] = sorted(member_codes)

    # Garante que todos os ASes de upstreams/downstreams têm entrada em path_node_meta.
    # Usa o asn_map (índice já em memória) para evitar N leituras de disco individuais.
    try:
        relation_asns: set[int] = set()
        for field in _RELATION_FIELDS:
            for a in doc.get(field, []):
                if a != asn:
                    relation_asns.add(a)
        existing_meta: dict = dict(doc.get("path_node_meta") or {})
        missing = [a for a in relation_asns if str(a) not in existing_meta]
        if missing:
            asn_map = store.asn_map(date_str)
            for rel_asn in missing:
                row = asn_map.get(rel_asn)
                if row is not None:
                    existing_meta[str(rel_asn)] = {
                        "name": row.get("name", ""),
                        "is_br": row.get("is_br", False),
                        "space_v4": row.get("space_v4", 0),
                        "space_v6": row.get("space_v6", 0),
                    }
            doc["path_node_meta"] = existing_meta
    except Exception:
        pass

    # RPKI: valida qualquer prefixo originado pelo AS (RIR e/ou tabela global/IXPs).
    # Cap em 1000 prefixos para limitar custo em ASNs com full table muito grande
    # (ex.: Cloudflare com 5k+ prefixos globais) sem deixar de validar nada.
    try:
        roa_list = store.rpki_vrps_for_asn(date_str, asn)
        if roa_list is not None:
            rir_prefixes = (
                list(doc.get("rir_prefixes_v4", []))
                + list(doc.get("rir_prefixes_v6", []))
            )
            global_prefixes = (
                list(doc.get("global_prefixes_v4", []))
                + list(doc.get("global_prefixes_v6", []))
            )
            # União sem duplicatas, prefixos RIR primeiro
            all_prefixes = list(dict.fromkeys(rir_prefixes + global_prefixes))
            if all_prefixes:
                rpki_validation = store.rpki_validate_prefixes(date_str, asn, all_prefixes[:1000])
                if roa_list or rpki_validation:
                    doc["roa_list"] = sorted(roa_list, key=lambda r: r["prefix"])
                    doc["rpki_validation"] = rpki_validation
    except Exception:
        pass

    # ASPA: objetos publicados por este AS (como customer) e objetos de terceiros
    # que listam este AS como provider.
    try:
        aspa_providers = store.aspa_as_customer(date_str, asn)
        aspa_customers = store.aspa_as_provider(date_str, asn)
        if aspa_providers:
            doc["aspa_providers"] = sorted(aspa_providers, key=lambda a: a.get("tal", ""))
        if aspa_customers:
            doc["aspa_customers"] = sorted(aspa_customers, key=lambda a: a.get("customer", 0))
    except Exception:
        pass

    # Pontos de atenção: cruza RIR, full table, RPKI, PeeringDB, IX.br e geo.
    try:
        from products.alerts.registro import calcular_alertas
        doc["alerts"] = calcular_alertas(store, date_str, asn, doc)
    except Exception:
        pass

    return doc
