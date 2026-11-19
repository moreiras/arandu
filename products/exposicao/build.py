# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Exposição de serviços por ASN e por UF. Saída: `published/{date}/exposicao/asns.json.gz`.

Só CONTAGENS que o Shodan observou (nunca lista de IPs nem host individual), com a data da leitura de cada ASN (rodízio). Por ASN: serviços observados (banners, não IPs únicos),
as portas mais vistas, os serviços em portas de risco por classe (acesso remoto, gestão de roteador/CPE, banco de dados, compartilhamento) e, SE o plano da conta tiver a faceta, as CVEs mais
vistas; sem a faceta o campo diz "não disponível no plano". Por UF, só agregado **derivado** dos ASNs (o Shodan não tem recorte pelo cadastro do projeto), com a cobertura declarada. Sem ranking
de ASN. Ausência de leitura não é zero; zero serviço observado é "o Shodan não viu serviço", não "não tem serviço". Atribuição ao Shodan no arquivo.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from core import shodan
from core.common import normalized_path, now_iso, published_path
from core.jsonio import carregar_json_gz, gravar_json_gz
from products.seguranca.build import _docs_br

TOP_PORTAS_PUBLICADAS = 10

AVISO = ("Contagem de serviços observados pelo Shodan na data da leitura de cada ASN; NÃO é prova de vulnerabilidade, nem inventário da rede, nem estado atual. "
         "Serviço observado é um banner, não um IP único: um host com duas portas conta duas vezes. Uma porta de risco aberta (Telnet, RDP, gestão de roteador, banco de dados) indica exposição à Internet; "
         "não diz se há falha nem se o acesso é possível. ASN sem leitura ainda não foi consultado (isso não quer dizer zero), e zero serviço observado quer dizer que o Shodan não viu serviço.")
LIMITES = ("Rodízio: cada ASN tem a sua data de leitura. O Shodan cobre só o que varreu, com atraso e viés (portas padrão, IPs que respondem). A classe de risco por porta é definição do projeto (`classes`), "
           "não do Shodan; SNMP e outras portas UDP vêm do que o Shodan indexou. CVEs: só se o plano da conta tem a faceta (`plano.facetas.vuln`); o Shodan as infere pelo banner (versão), o que não prova a falha. "
           "UF é agregado derivado do cadastro dos ASNs (ASN multi-UF conta na UF do cadastro), sem CVEs. Sem ranking de ASN.")


def _classes_declaradas() -> dict:
    return {c: {"rotulo": shodan.ROTULO_CLASSE[c], "portas": [{"porta": p, "servico": n} for p, n in sorted(d.items())]} for c, d in shodan.CLASSES_DE_RISCO.items()}


def _bloco_asn(leitura: dict, plano_vuln: str) -> dict:
    total = int(leitura.get("total") or 0)
    saida: dict = {"lido_em": leitura["em"], "servicos_observados": total}
    if total <= 0:
        saida["sem_servico_observado"] = True
        return saida
    saida["portas_mais_vistas"] = [{"porta": p, "n": n} for p, n in (leitura.get("portas") or [])[:TOP_PORTAS_PUBLICADAS]]
    classes: dict[str, dict] = {}
    for porta_s, n in (leitura.get("risco") or {}).items():
        classe, nome = shodan.PORTAS_DE_RISCO[int(porta_s)]
        c = classes.setdefault(classe, {"total": 0, "servicos": []})
        c["total"] += n
        c["servicos"].append({"porta": int(porta_s), "servico": nome, "n": n})
    for c in classes.values():
        c["servicos"].sort(key=lambda s: (-s["n"], s["porta"]))
    risco_total = int(leitura.get("risco_total") or 0)
    saida["risco"] = {"servicos_de_risco": risco_total, "pct_dos_servicos_observados": round(100 * risco_total / total, 2), "classes": dict(sorted(classes.items()))}
    if leitura.get("vulns") is not None:
        saida["vulnerabilidades"] = {"disponivel": True, "cves_mais_vistas": [{"cve": c, "n": n} for c, n in leitura["vulns"]]}
    elif plano_vuln == "indisponivel":
        saida["vulnerabilidades"] = {"disponivel": False, "nota": "não disponível no plano da conta do Shodan"}
    return saida


def calcular(doc: dict, docs_br: dict[int, dict]) -> dict:
    br = set(docs_br)
    plano = (doc.get("plano") or {}).get("facetas") or {}
    plano_vuln = plano.get("vuln") or "nao_testada"
    lidos = {int(k): v for k, v in (doc.get("asns") or {}).items() if int(k) in br}
    asns = {str(a): _bloco_asn(v, plano_vuln) for a, v in sorted(lidos.items())}
    datas = sorted(v["em"] for v in lidos.values() if v.get("em"))
    cobertura = {"asns_do_brasil_no_snapshot": len(br), "asns_com_leitura": len(lidos), "asns_com_servicos_observados": sum(1 for v in lidos.values() if v.get("total")),
                 "leitura_mais_antiga": datas[0] if datas else None, "leitura_mais_recente": datas[-1] if datas else None}
    return {"cobertura": cobertura, "plano": {"facetas": {"port": plano.get("port", "ok"), "vuln": plano_vuln}}, "classes": _classes_declaradas(), "asns": asns, "por_uf": _por_uf(lidos, docs_br)}


def _por_uf(lidos: dict[int, dict], docs_br: dict[int, dict]) -> dict:
    """Agregado DERIVADO por UF: soma das contagens dos ASNs com leitura, com a cobertura (quantos ASNs do cadastro da UF já foram lidos)."""
    ufs: dict[str, dict] = {}
    for a, d in docs_br.items():
        uf = d.get("uf")
        if not uf:
            continue
        u = ufs.setdefault(uf, {"asns_do_cadastro": 0, "asns_com_leitura": 0, "asns_com_servicos_observados": 0, "servicos_observados": 0, "servicos_de_risco": 0,
                                "classes": {c: 0 for c in shodan.CLASSES_DE_RISCO}, "portas": {}, "derivado": True})
        u["asns_do_cadastro"] += 1
        v = lidos.get(a)
        if not v:
            continue
        u["asns_com_leitura"] += 1
        if v.get("total"):
            u["asns_com_servicos_observados"] += 1
            u["servicos_observados"] += int(v["total"])
            u["servicos_de_risco"] += int(v.get("risco_total") or 0)
            for porta_s, n in (v.get("risco") or {}).items():
                classe, nome = shodan.PORTAS_DE_RISCO[int(porta_s)]
                u["classes"][classe] += n
                u["portas"][nome] = u["portas"].get(nome, 0) + n
    out = {}
    for uf in sorted(ufs):
        u = ufs[uf]
        u["pct_de_servicos_de_risco"] = round(100 * u["servicos_de_risco"] / u["servicos_observados"], 2) if u["servicos_observados"] else None
        u["servicos_de_risco_por_servico"] = dict(sorted(u.pop("portas").items(), key=lambda kv: (-kv[1], kv[0])))
        out[uf] = u
    return out


def publicar_exposicao(base: Path, date_str: str, log) -> dict:
    doc = carregar_json_gz(normalized_path(base, date_str, "summary") / "shodan_exposicao.json.gz")
    if not doc:
        log.info("shodan_exposicao.json.gz ausente: exposição não gerada")
        return {}
    r = calcular(doc, _docs_br(base, date_str))
    destino = published_path(base, date_str) / "exposicao"
    destino.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "asns.json.gz", {
        "snapshot_date": date_str, "generated_at": now_iso(), "coletado_em": doc.get("fetched_at"),
        "fonte": {"nome": "Shodan", "url": "https://www.shodan.io", "api": doc.get("fonte"), "licenca": doc.get("licenca") or shodan.LICENCA, "atribuicao": doc.get("atribuicao") or shodan.ATRIBUICAO},
        "licenca": doc.get("licenca") or shodan.LICENCA, "aviso": AVISO, "limites": LIMITES, **r})
    log.info("exposicao published", asns=len(r["asns"]), ufs=len(r["por_uf"]))
    return {"asns": len(r["asns"]), "ufs": len(r["por_uf"])}
