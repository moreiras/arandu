# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Rede no território: três estimativas que juntam o SICI (onde estão os acessos) com o que se sabe da rede dos ASNs.

Entradas em `published/{date}/`: `sici_municipios.json.gz` (acessos por município e CNPJ, com os ASNs de cada CNPJ), `asns/index.json` (usuários APNIC e % de IPv6 por ASN),
`seguranca/asns.json.gz` (ROV medido pela APNIC e UF por ASN) e `territorio/regiao.json.gz` (provedores de trânsito inferidos por ASN).
Saída: `territorio/rede_territorio.json.gz`.

Tudo é ESTIMATIVA ou INFERÊNCIA, com a suposição à vista:
  * **IPv6 por município**: acessos da operadora no município × a adoção de IPv6 dos ASNs dela (APNIC, ponderada pelos usuários estimados). Suposição declarada:
    a adoção do AS vale igual em todos os municípios em que a operadora atua. Operadora sem ASN ou sem medida de IPv6 não entra, e a `cobertura` diz que parcela dos acessos entrou.
  * **Usuários atrás de ROV**: usuários estimados de cada ASN × a fração dos testes da APNIC em que o ASN valida ROV, somados por UF (a da sede do ASN). Só ASNs com amostras
    suficientes e com usuários estimados entram; `cobertura` é a parcela dos usuários do ASN com medida.
  * **Dependência de trânsito**: operadoras cujos ASNs têm um único provedor de trânsito inferido (nível provável ou superior), por acessos; e o provedor do qual mais acessos dependem.
    Operadora sem relação inferida fica de fora (desconhecido não é "um só provedor").

Uso:
    python -m products.rede_territorio.build --date 2026-11-03
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

from core.common import configure_logging, data_dir, now_iso, published_path, today_str
from core.jsonio import carregar_json_gz, gravar_json_gz

NIVEIS_FIRMES = (0, 1)      # na `regiao` o nível do provedor é numérico: 0 confirmado, 1 provável, 2 possível (2 não entra)
MIN_AMOSTRAS_ROV = 100
LIMITES = ("Estimativas e inferências, não medidas por município. IPv6: supõe que a adoção do AS (APNIC) vale igual em todos os municípios da operadora e usa os usuários estimados como peso; "
           "a `cobertura` é a parcela dos acessos que entrou. ROV: fração dos testes da APNIC em que o AS valida ROV, vezes os usuários estimados, somada por UF da sede do AS; não é a UF dos usuários. "
           "Trânsito: provedor inferido pelas rotas observadas (ARC), nível provável ou superior; um provedor só pode ser falta de observação e não diz nada de contrato. Operadora sem ASN ou sem relação inferida fica de fora.")


def _soma(partes: dict[str, float], chave: str, v: float) -> None:
    partes[chave] = partes.get(chave, 0) + v


def adocao_v6(asns_idx: dict[int, dict], asns: list[int]) -> Optional[float]:
    """% de IPv6 da operadora: média das % de IPv6 dos ASNs, ponderada pelos usuários estimados (média simples se nenhum tem usuários). `None` se nenhum tem medida."""
    com = [(a, asns_idx[a]) for a in asns if asns_idx.get(a) and asns_idx[a].get("pct_v6") is not None]
    if not com:
        return None
    pesos = [(x.get("apnic_users") or 0) for _, x in com]
    if sum(pesos) > 0:
        return sum(x["pct_v6"] * p for (_, x), p in zip(com, pesos)) / sum(pesos)
    return sum(x["pct_v6"] for _, x in com) / len(com)


def calcular_ipv6(municipios: dict[str, dict], asns_idx: dict[int, dict]) -> dict:
    por_mun: dict[str, dict] = {}
    por_uf: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for ibge, m in municipios.items():
        tot = com = v6 = 0
        for o in m.get("operadores", []):
            a = o.get("acessos") or 0
            tot += a
            p = adocao_v6(asns_idx, o.get("asns") or [])
            if p is not None:
                com += a
                v6 += a * p / 100
        if not tot:
            continue
        por_mun[ibge] = {"uf": m.get("uf", ""), "acessos": tot, "acessos_com_estimativa": com, "v6_estimado": round(v6), "pct_v6": round(100 * v6 / com, 1) if com else None, "cobertura": round(100 * com / tot, 1)}
        u = por_uf[m.get("uf", "")]
        u["acessos"] += tot; u["com"] += com; u["v6"] += v6
    ufs = {uf: {"acessos": round(u["acessos"]), "v6_estimado": round(u["v6"]), "pct_v6": round(100 * u["v6"] / u["com"], 1) if u["com"] else None, "cobertura": round(100 * u["com"] / u["acessos"], 1)} for uf, u in sorted(por_uf.items())}
    t = sum(u["acessos"] for u in por_uf.values()); c = sum(u["com"] for u in por_uf.values()); v = sum(u["v6"] for u in por_uf.values())
    return {"municipios": por_mun, "ufs": ufs, "brasil": {"acessos": round(t), "v6_estimado": round(v), "pct_v6": round(100 * v / c, 1) if c else None, "cobertura": round(100 * c / t, 1) if t else None}}


def calcular_rov(asns_idx: dict[int, dict], seguranca: dict[str, dict]) -> dict:
    """Usuários estimados atrás de ASNs que validam ROV, por UF da sede do ASN e no país."""
    por_uf: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for a_str, s in seguranca.items():
        a = int(a_str)
        x = asns_idx.get(a) or {}
        if not x.get("is_br") or not x.get("apnic_users"):
            continue
        uf = s.get("uf") or "?"
        u = por_uf[uf]
        u["usuarios"] += x["apnic_users"]
        rov = s.get("rov") or {}
        if rov.get("validates_pct") is not None and (rov.get("amostras") or 0) >= MIN_AMOSTRAS_ROV:
            u["com_medida"] += x["apnic_users"]
            u["atras_rov"] += x["apnic_users"] * rov["validates_pct"] / 100
    def linha(u):
        return {"usuarios": round(u["usuarios"]), "usuarios_com_medida": round(u["com_medida"]), "usuarios_atras_rov": round(u["atras_rov"]),
                "pct_atras_rov": round(100 * u["atras_rov"] / u["com_medida"], 1) if u["com_medida"] else None, "cobertura": round(100 * u["com_medida"] / u["usuarios"], 1) if u["usuarios"] else None}
    ufs = {uf: linha(u) for uf, u in sorted(por_uf.items()) if uf != "?"}
    br = defaultdict(float)
    for u in por_uf.values():
        for k, v in u.items():
            br[k] += v
    return {"ufs": ufs, "brasil": linha(br), "parametros": {"min_amostras": MIN_AMOSTRAS_ROV}}


def calcular_transito(municipios: dict[str, dict], provedores: dict[int, set[int]], nomes: dict[int, str]) -> dict:
    """Por município e UF: parcela dos acessos (das operadoras com relação inferida) com um único provedor de trânsito, e o provedor do qual mais acessos dependem."""
    def da_operadora(asns: list[int]) -> Optional[set[int]]:
        com = [provedores[a] for a in asns if provedores.get(a)]
        return set().union(*com) if com else None

    por_mun: dict[str, dict] = {}
    uf_acc: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    uf_prov: dict[str, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for ibge, m in municipios.items():
        tot = com = unico = 0
        dep: dict[int, float] = defaultdict(float)
        for o in m.get("operadores", []):
            a = o.get("acessos") or 0
            tot += a
            prov = da_operadora(o.get("asns") or [])
            if prov is None:
                continue
            com += a
            if len(prov) == 1:
                unico += a
            for p in prov:
                dep[p] += a
        if not tot:
            continue
        top = max(dep, key=lambda p: (dep[p], -p)) if dep else None
        por_mun[ibge] = {"uf": m.get("uf", ""), "acessos": tot, "acessos_com_relacao": com, "acessos_provedor_unico": unico,
                         "pct_provedor_unico": round(100 * unico / com, 1) if com else None, "cobertura": round(100 * com / tot, 1),
                         "provedor_principal": ({"asn": top, "nome": nomes.get(top, ""), "pct_dos_acessos": round(100 * dep[top] / com, 1)} if top is not None else None)}
        u = uf_acc[m.get("uf", "")]
        u["acessos"] += tot; u["com"] += com; u["unico"] += unico
        for p, v in dep.items():
            uf_prov[m.get("uf", "")][p] += v
    ufs = {}
    for uf, u in sorted(uf_acc.items()):
        dep = uf_prov[uf]
        top = max(dep, key=lambda p: (dep[p], -p)) if dep else None
        ufs[uf] = {"acessos": round(u["acessos"]), "acessos_com_relacao": round(u["com"]), "pct_provedor_unico": round(100 * u["unico"] / u["com"], 1) if u["com"] else None,
                   "cobertura": round(100 * u["com"] / u["acessos"], 1) if u["acessos"] else None,
                   "provedor_principal": ({"asn": top, "nome": nomes.get(top, ""), "pct_dos_acessos": round(100 * dep[top] / u["com"], 1)} if top is not None and u["com"] else None)}
    return {"municipios": por_mun, "ufs": ufs}


def _provedores_firmes(regiao: dict) -> tuple[dict[int, set[int]], dict[int, str]]:
    prov: dict[int, set[int]] = {}
    nomes: dict[int, str] = {}
    for a_str, t in (regiao.get("asns") or {}).items():
        firmes = {p[0] for p in t.get("p", []) if len(p) > 2 and p[2] in NIVEIS_FIRMES}
        if firmes:
            prov[int(a_str)] = firmes
        nomes[int(a_str)] = t.get("n", "")
    return prov, nomes


def publicar_rede_territorio(base: Path, date_str: str, log) -> dict:
    import json
    pub = published_path(base, date_str)
    sici = (carregar_json_gz(pub / "sici_municipios.json.gz") or {}).get("municipios")
    idx_p = pub / "asns" / "index.json"
    if not sici or not idx_p.exists():
        log.info("sici_municipios ou índice de ASNs ausentes: rede_territorio não gerada")
        return {}
    asns_idx = {a["asn"]: a for a in json.loads(idx_p.read_text(encoding="utf-8"))}
    seg = (carregar_json_gz(pub / "seguranca" / "asns.json.gz") or {}).get("asns") or {}
    regiao = carregar_json_gz(pub / "territorio" / "regiao.json.gz") or {}
    prov, nomes = _provedores_firmes(regiao)
    out = {"snapshot_date": date_str, "generated_at": now_iso(), "natureza": "estimado", "limites": LIMITES,
           "fontes": {"sici": (carregar_json_gz(pub / "sici_municipios.json.gz") or {}).get("mes_referencia"), "apnic": "APNIC Labs (usuários e IPv6 por ASN, IRoV)", "relacoes": "ARC (relações inferidas)"},
           "ipv6": calcular_ipv6(sici, asns_idx), "rov": calcular_rov(asns_idx, seg), "transito": calcular_transito(sici, prov, nomes)}
    destino = pub / "territorio"
    destino.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "rede_territorio.json.gz", out)
    log.info("rede_territorio written", municipios=len(out["ipv6"]["municipios"]), ufs_rov=len(out["rov"]["ufs"]))
    return {"municipios": len(out["ipv6"]["municipios"]), "ufs_rov": len(out["rov"]["ufs"]), "transito": len(out["transito"]["municipios"])}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="IPv6 por município, usuários atrás de ROV e dependência de trânsito")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; o produto é sempre recalculado")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        publicar_rede_territorio(data_dir(), a.date, log)
    except Exception:
        log.exception("falha no cálculo da rede no território")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
