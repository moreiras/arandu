# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Bloqueios e interferência medidos pelo OONI, por ASN. Saída: `published/{date}/bloqueios/asns.json.gz`.

Os testes vão em LISTA (`teste` como campo, não como chave): a chave `whatsapp` seria tomada por chave de contato pelo filtro de privacidade da API.

Soma, na janela do normalizado `ooni_bloqueios`, as medições por ASN × teste e publica só a célula com pelo menos `MIN_MEDICOES` medições (k-anonimato simples: ASN com poucas sondas poderia
expor um voluntário). O veredito é o da própria sonda (não é o do backend do OONI nem prova de censura) e o `webconnectivity` é AMOSTRA de horas. Os dados são do OONI, CC BY-NC-SA 4.0: licença e atribuição
vão no arquivo, e o derivado é rotulado com a mesma licença. Sem ranking de ASN, sem site, sem medição individual.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from core import ooni
from core.common import normalized_path, now_iso, published_path
from core.jsonio import carregar_json_gz, gravar_json_gz
from products.seguranca.build import _docs_br

LIMITES = ("Sondas são de voluntários: viés de quem instala o aplicativo e de onde mora, poucas por ASN e concentradas em redes grandes; sem sonda no ASN, nada se sabe (ausência de dado não é 'sem bloqueio'). "
           "Célula com menos de 10 medições na janela não é publicada. O veredito é da sonda, não do backend do OONI, e não distingue bloqueio de falha do serviço, filtro do cliente ou VPN. "
           "O `webconnectivity` é uma amostra de horas de cada dia e a sonda não dá veredito de bloqueio para https (a taxa é um piso). Cobertura por ASN, não por município. Não é prova de censura.")


def _pct(a: int, n: int) -> Optional[float]:
    return round(100 * a / n, 2) if n else None


def calcular(doc: dict, br: set[int], minimo: int = ooni.MIN_MEDICOES) -> dict:
    """Agrega a janela do normalizado e aplica o mínimo por célula; só ASNs do Brasil do snapshot entram em `asns`."""
    dias = doc.get("dias") or {}
    por_teste: dict[str, dict[str, list[dict]]] = {}
    for d in sorted(dias):
        for t, por_asn in (dias[d].get("testes") or {}).items():
            for asn, cel in por_asn.items():
                por_teste.setdefault(t, {}).setdefault(asn, []).append(cel)
        for asn, cel in (dias[d].get("web") or {}).items():
            por_teste.setdefault(ooni.TESTE_WEB, {}).setdefault(asn, []).append(cel)
    asns: dict[str, dict] = {}
    resumo: list[dict] = []
    for t in (*ooni.TESTES_LEVES, ooni.TESTE_WEB):
        celulas = por_teste.get(t, {})
        pub = baixo = fora = medicoes = 0
        for asn, lista in celulas.items():
            c = ooni.somar(lista)
            medicoes += c["n"]
            if c["n"] < minimo:
                baixo += 1
                continue
            if int(asn) not in br:
                fora += 1
                continue
            pub += 1
            sai = {"teste": t, "rotulo": ooni.ROTULOS[t], "n": c["n"], "anomalias": c["anom"], "pct_anomalia": _pct(c["anom"], c["n"])}
            if c.get("partes"):
                sai["partes"] = c["partes"]
            if c.get("alvos"):
                sai["alvos_acessiveis_pct"] = {k: _pct(ok, tot) for k, (tot, ok) in c["alvos"].items() if tot}
            if t == ooni.TESTE_WEB:
                sai["amostra"] = True
                sai["sem_veredito"] = c.get("sem_veredito", 0)
                sai["inacessivel"] = c.get("inacessivel", 0)
            asns.setdefault(asn, {"testes": []})["testes"].append(sai)
        resumo.append({"teste": t, "rotulo": ooni.ROTULOS[t], "criterio": ooni.CRITERIOS[t], "medicoes": medicoes, "asns_publicados": pub, "asns_abaixo_do_minimo": baixo, "asns_fora_do_snapshot": fora})
    amostras = [v["web_amostra"] for v in dias.values() if v.get("web_amostra")]
    web = {"horas_utc": doc.get("horas_amostra_web"), "dias_com_amostra": len(amostras), "dias_com_amostra_completa": sum(1 for a in amostras if a.get("completa")),
           "arquivos": sum(a["arquivos"] for a in amostras), "bytes_lidos": sum(a["bytes"] for a in amostras)}
    ordenados = sorted(dias)
    return {"janela": {"inicio": ordenados[0] if ordenados else None, "fim": ordenados[-1] if ordenados else None, "dias_com_dado": len(ordenados), "dias_da_janela": doc.get("janela_dias")},
            "minimo_medicoes": minimo, "testes": resumo, "web_amostra": web, "asns": dict(sorted(asns.items(), key=lambda kv: int(kv[0])))}


def publicar_bloqueios(base: Path, date_str: str, log) -> dict:
    doc = carregar_json_gz(normalized_path(base, date_str, "summary") / "ooni_bloqueios.json.gz")
    if not doc:
        log.info("ooni_bloqueios.json.gz ausente: bloqueios não gerado")
        return {}
    r = calcular(doc, set(_docs_br(base, date_str)))
    destino = published_path(base, date_str) / "bloqueios"
    destino.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "asns.json.gz", {
        "snapshot_date": date_str, "generated_at": now_iso(), "coletado_em": doc.get("fetched_at"),
        "fonte": {"nome": "OONI (Open Observatory of Network Interference), dados abertos", "url": "https://ooni.org/data/", "bucket": doc.get("fonte"),
                  "licenca": doc.get("licenca") or ooni.LICENCA, "licenca_url": doc.get("licenca_url") or ooni.LICENCA_URL, "atribuicao": doc.get("atribuicao") or ooni.ATRIBUICAO},
        "licenca": doc.get("licenca") or ooni.LICENCA, "aviso": ooni.AVISO, "limites": LIMITES, **r})
    log.info("bloqueios published", asns=len(r["asns"]), dias=r["janela"]["dias_com_dado"])
    return {"asns": len(r["asns"]), "dias": r["janela"]["dias_com_dado"]}
