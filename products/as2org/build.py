# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Organização por ASN e abuso agregado. Saídas: `published/{date}/as2org/asns.json.gz` e `abuso_agregado/asns.json.gz`.

  * `as2org`: organização de cada ASN do Brasil (CAIDA, via AS Rank), os outros ASNs do Brasil da mesma organização ("irmãos") e a cobertura em relação aos ASNs do Brasil
    do snapshot. A organização é do CAIDA (inferida do WHOIS), não declaração da rede: pode juntar filiais sob uma "Parent" e não é o grupo societário (esse vem da Receita, em `grupos`).
  * `abuso_agregado`: contagens por ASN de servidores C2 de botnets do Feodo Tracker (abuse.ch, CC0). Só ASNs do Brasil com pelo menos um C2 entram em `asns`; o resto é "nenhum
    registrado", que NÃO é "limpo": a lista do Feodo cobre poucas famílias de botnet e hoje está quase vazia. O URLhaus não é coletado (exige cadastro). Sem lista de IPs.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Optional

from core.common import normalized_path, now_iso, published_path
from core.jsonio import carregar_json_gz, gravar_json_gz
from products.seguranca.build import _docs_br

LIMITES_AS2ORG = ("A organização é a do CAIDA AS Rank (derivada do WHOIS pelo as2org do CAIDA): pode agrupar filiais sob uma 'Parent' e o nome é o do registro, não o nome fantasia. "
                  "Irmãos são só os ASNs do Brasil com a mesma organização; a organização pode ter ASNs em outros países (`membros_total`). Não é grupo societário (veja `grupos`), e ASN "
                  "ausente do AS Rank (não visto na tabela de rotas) fica sem organização aqui.")
LIMITES_ABUSO = ("Contagem de servidores de comando e controle de botnets listados pelo Feodo Tracker (abuse.ch, CC0) que estão em prefixos do ASN na data da coleta. 'Nenhum registrado' não "
                 "quer dizer rede limpa: a lista cobre poucas famílias (Dridex, Emotet, TrickBot, QakBot, BazarLoader) e o próprio abuse.ch a declara quase vazia em 2026. O ASN que hospeda um C2 "
                 "não é o dono do servidor. URLhaus não coletado (exige cadastro). Sem IPs.")


def calcular_as2org(orgs: dict[str, dict], br: set[int]) -> tuple[dict, dict]:
    """(asns, cobertura): organização e irmãos (ASNs do Brasil com o mesmo `org_id`) dos ASNs do Brasil que o CAIDA conhece."""
    por_org: dict[str, list[int]] = defaultdict(list)
    for a, o in orgs.items():
        por_org[o["org_id"]].append(int(a))
    asns = {}
    for a in sorted(int(x) for x in orgs):
        o = orgs[str(a)]
        irmaos = sorted(x for x in por_org[o["org_id"]] if x != a)
        asns[str(a)] = {"org_id": o["org_id"], "org_nome": o.get("org_nome"), "org_pais": o.get("org_pais"), "membros_total": o.get("membros_total"),
                        **({"irmaos_br": irmaos} if irmaos else {})}
    com = sum(1 for a in br if str(a) in asns)
    cobertura = {"asns_br": len(br), "com_organizacao": com, "pct": round(100 * com / len(br), 1) if br else None, "sem_organizacao": len(br) - com,
                 "asns_no_caida_fora_do_snapshot": sum(1 for a in asns if int(a) not in br),
                 "organizacoes": len(por_org), "organizacoes_com_irmaos": sum(1 for v in por_org.values() if len(v) > 1)}
    return asns, cobertura


def calcular_abuso(doc: Optional[dict], br: set[int]) -> dict:
    """Contagens do Feodo para os ASNs do Brasil; `fora_do_brasil` só conta, sem listar."""
    feodo = (doc or {}).get("feodo") or {}
    asns = {a: {"feodo_c2": v["c2_total"], "feodo_c2_online": v["c2_online"], "feodo_malware": v.get("malware") or {}}
            for a, v in (feodo.get("asns") or {}).items() if int(a) in br}
    return {"asns": asns, "feodo_total_mundo": feodo.get("total"), "feodo_online_mundo": feodo.get("online"),
            "feodo_asns_br": len(asns), "feodo_c2_br": sum(v["feodo_c2"] for v in asns.values())}


def publicar_as2org(base: Path, date_str: str, log) -> dict:
    doc = carregar_json_gz(normalized_path(base, date_str, "summary") / "caida_as2org.json.gz")
    if not doc:
        log.info("caida_as2org.json.gz ausente: as2org não gerado")
        return {}
    br = set(_docs_br(base, date_str))
    asns, cobertura = calcular_as2org(doc["asns"], br)
    destino = published_path(base, date_str) / "as2org"
    destino.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "asns.json.gz", {
        "snapshot_date": date_str, "generated_at": now_iso(), "coletado_em": doc.get("fetched_at"),
        "fonte": {"nome": "CAIDA AS Rank (organização por ASN)", "url": doc.get("fonte"), "citacao": doc.get("citacao")},
        "limites": LIMITES_AS2ORG, "cobertura": cobertura, "asns": asns})
    log.info("as2org published", asns=len(asns), pct=cobertura["pct"])
    return {"asns": len(asns), "cobertura_pct": cobertura["pct"]}


def publicar_abuso_agregado(base: Path, date_str: str, log) -> dict:
    doc = carregar_json_gz(normalized_path(base, date_str, "summary") / "abusech.json.gz")
    if not doc:
        log.info("abusech.json.gz ausente: abuso_agregado não gerado")
        return {}
    r = calcular_abuso(doc, set(_docs_br(base, date_str)))
    destino = published_path(base, date_str) / "abuso_agregado"
    destino.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "asns.json.gz", {
        "snapshot_date": date_str, "generated_at": now_iso(), "coletado_em": doc.get("fetched_at"),
        "fonte": {"nome": "Feodo Tracker (abuse.ch)", "url": doc.get("fonte"), "licenca": doc.get("licenca")}, "urlhaus": doc.get("urlhaus"), "limites": LIMITES_ABUSO, **r})
    log.info("abuso_agregado published", asns_br=r["feodo_asns_br"], c2_br=r["feodo_c2_br"])
    return {"asns_br": r["feodo_asns_br"], "c2_br": r["feodo_c2_br"]}
