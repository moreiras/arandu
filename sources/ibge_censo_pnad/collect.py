# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""IBGE: população, domicílios e uso de internet, pela API SIDRA.

  * Censo 2022, tabela 4714: população residente e área por município;
  * Censo 2022, tabela 4712: domicílios particulares permanentes OCUPADOS e moradores por município;
  * PNAD Contínua anual, tabela 7307: domicílios por UF segundo "havia utilização de internet no domicílio" (inclui quem usa só o móvel,
    não é banda larga fixa), com o coeficiente de variação da amostra, e o total de domicílios por UF em todos os anos (base da projeção);
  * Estimativas de População, tabela 6579: população residente estimada por município (1º de julho do ano mais recente, em geral o corrente),
    calculada a partir do Censo 2022.

Raw:         data/raw/{date}/summary/ibge-sidra-{tabela}-{ano}.json.gz (resposta da SIDRA, sem alteração)
Normalizado: data/normalized/{date}/summary/ibge_municipios.json.gz     {censo_ano, estimativa_ano, municipios: {ibge: {nome, uf, populacao, populacao_estimada, area_km2, domicilios, moradores}}}
             data/normalized/{date}/summary/ibge_taxa_internet.json.gz  {pnad_ano, brasil, ufs: {UF: {domicilios_mil, com_internet_mil, taxa, cv_domicilios_pct, domicilios_mil_por_ano}}}

Uso:
    python -m sources.ibge_censo_pnad.collect --date 2026-10-31 [--force]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import httpx

from core.common import configure_logging, data_dir, gravar_texto_gz, normalized_path, now_iso, raw_path, today_str, write_json_gz
from core.site import USER_AGENT

BASE = "https://apisidra.ibge.gov.br/values"
HEADERS = {"User-Agent": USER_AGENT}
ESPERA_S = 1.0                                       # entre chamadas (a SIDRA não publica limite; poucas chamadas por execução)
MINIMO_MUNICIPIOS = 5500                             # o Censo 2022 tem 5.570: bem menos que isso é resposta truncada
SEM_VALOR = {"", "-", "..", "...", "X"}              # códigos de ausência/sigilo da SIDRA

# Código IBGE da UF (2 primeiros dígitos do município e `n3` da SIDRA) → sigla
UF_POR_CODIGO = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}

# (tabela, caminho SIDRA). `p/last 1`: o ano mais recente da tabela.
CONSULTAS = {
    "4714": "/t/4714/n6/all/v/93,6318/p/last%201",
    "4712": "/t/4712/n6/all/v/381,382/p/last%201",
    "7307": "/t/7307/n3/all/v/162,5123/p/last%201/c1/6795/c688/all",
    "7307-serie": "/t/7307/n3/all/v/162/p/all/c1/6795/c688/33298",
    "6579": "/t/6579/n6/all/v/9324/p/last%201",
}
V_POP, V_AREA, V_DOM, V_MORADORES = "93", "6318", "381", "382"
V_PNAD_DOM, V_PNAD_CV = "162", "5123"
V_POP_ESTIMADA = "9324"
C_TOTAL, C_COM_INTERNET = "33298", "48534"


def numero(v: str) -> float | None:
    if v is None or v.strip() in SEM_VALOR:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def linhas(resposta: list[dict]) -> list[dict]:
    """A SIDRA devolve o cabeçalho como primeiro elemento."""
    return resposta[1:] if resposta and "NC" in resposta[0] and resposta[0].get("V") == "Valor" else resposta


def _nome(d1n: str) -> str:
    """"Alta Floresta D'Oeste - RO" (Censo) ou "São Paulo (SP)" (estimativas) → só o nome."""
    return re.sub(r"( - [A-Z]{2}| \([A-Z]{2}\))$", "", d1n)


def normalizar_municipios(r4714: list[dict], r4712: list[dict], r6579: list[dict] | None = None) -> tuple[dict, str, str]:
    """({ibge: {...}}, ano do Censo, ano da estimativa). Município sem valor numérico numa variável fica sem esse campo (nunca zero inventado).
    Município criado depois do Censo aparece só com a população estimada."""
    muns: dict[str, dict] = {}
    ano = estimativa_ano = ""
    for x in linhas(r4714) + linhas(r4712) + linhas(r6579 or []):
        ibge = x["D1C"]
        if len(ibge) != 7 or ibge[:2] not in UF_POR_CODIGO:
            continue
        m = muns.setdefault(ibge, {"nome": _nome(x["D1N"]), "uf": UF_POR_CODIGO[ibge[:2]]})
        v = numero(x["V"])
        if x["D2C"] == V_POP_ESTIMADA:
            estimativa_ano = x["D3C"]
            if v is not None:
                m["populacao_estimada"] = int(v)
            continue
        ano = x["D3C"]
        if v is None:
            continue
        campo = {V_POP: "populacao", V_AREA: "area_km2", V_DOM: "domicilios", V_MORADORES: "moradores"}.get(x["D2C"])
        if campo:
            m[campo] = round(v, 3) if campo == "area_km2" else int(v)
    return dict(sorted(muns.items())), ano, estimativa_ano


def normalizar_serie_domicilios(r_serie: list[dict]) -> dict[str, dict[str, float]]:
    """{UF: {ano: domicílios (mil)}} da PNAD, todos os anos da tabela (a projeção usa a razão entre o ano atual e o do Censo)."""
    out: dict[str, dict[str, float]] = {}
    for x in linhas(r_serie):
        uf = UF_POR_CODIGO.get(x["D1C"])
        v = numero(x["V"])
        if uf and v is not None:
            out.setdefault(uf, {})[x["D3C"]] = v
    return out


def normalizar_taxa_internet(r7307: list[dict]) -> tuple[dict, str]:
    """({'Brasil'?, UF: {...}}, ano). `taxa` = domicílios em que havia utilização de internet ÷ total (PNAD, amostra por UF)."""
    por: dict[str, dict] = {}
    ano = ""
    for x in linhas(r7307):
        codigo = x["D1C"]
        chave = "BR" if codigo == "1" else UF_POR_CODIGO.get(codigo)
        if chave is None:
            continue
        ano = x["D3C"]
        e = por.setdefault(chave, {})
        v = numero(x["V"])
        if x["D2C"] == V_PNAD_CV and x.get("D5C", C_TOTAL) == C_TOTAL:
            e["cv_domicilios_pct"] = v
        elif x["D2C"] == V_PNAD_DOM:
            cat = x.get("D5C") or x.get("D4C")
            if cat == C_TOTAL:
                e["domicilios_mil"] = v
            elif cat == C_COM_INTERNET:
                e["com_internet_mil"] = v
    for e in por.values():
        if e.get("domicilios_mil") and e.get("com_internet_mil") is not None:
            e["taxa"] = round(e["com_internet_mil"] / e["domicilios_mil"], 4)
    return por, ano


def _soma_brasil(ufs: dict[str, dict]) -> dict:
    """Total do país somando as UFs (a consulta é por UF); o coeficiente de variação do país não se deduz das UFs e fica de fora."""
    dom = sum(e["domicilios_mil"] for e in ufs.values())
    com = sum(e["com_internet_mil"] for e in ufs.values())
    return {"domicilios_mil": dom, "com_internet_mil": com, "taxa": round(com / dom, 4)}


def baixar(client: httpx.Client, caminho: str, tentativas: int = 3) -> list[dict]:
    for t in range(1, tentativas + 1):
        try:
            r = client.get(BASE + caminho)
            r.raise_for_status()
            dados = r.json()
            if not isinstance(dados, list) or len(dados) < 2:
                raise ValueError("resposta da SIDRA vazia")
            return dados
        except (httpx.HTTPError, ValueError):
            if t == tentativas:
                raise
            time.sleep(ESPERA_S * 5 * t)
    raise AssertionError("inalcançável")


def run(date_str: str, base: Path, log, espera_s: float = ESPERA_S) -> dict:
    respostas: dict[str, list[dict]] = {}
    with httpx.Client(timeout=120, follow_redirects=True, headers=HEADERS) as client:
        for tabela, caminho in CONSULTAS.items():
            respostas[tabela] = baixar(client, caminho)
            time.sleep(espera_s)
    muns, censo_ano, estimativa_ano = normalizar_municipios(respostas["4714"], respostas["4712"], respostas["6579"])
    if len(muns) < MINIMO_MUNICIPIOS:
        raise RuntimeError(f"ibge_censo_pnad: só {len(muns)} municípios (esperado ≥ {MINIMO_MUNICIPIOS}); resposta truncada?")
    taxas, pnad_ano = normalizar_taxa_internet(respostas["7307"])
    serie = normalizar_serie_domicilios(respostas["7307-serie"])
    ufs = {k: {**v, "domicilios_mil_por_ano": serie.get(k, {})} for k, v in taxas.items() if k != "BR"}
    if len(ufs) != 27 or not all("taxa" in v for v in ufs.values()):
        raise RuntimeError(f"ibge_censo_pnad: PNAD sem as 27 UFs com taxa ({len(ufs)} UFs)")
    raw_dir = raw_path(base, date_str, "summary")
    raw_dir.mkdir(parents=True, exist_ok=True)
    for tabela, r in respostas.items():
        ano = "serie" if tabela.endswith("-serie") else linhas(r)[0]["D3C"]
        gravar_texto_gz(raw_dir / f"ibge-sidra-{tabela.replace('-serie', '')}-{ano}.json.gz", json.dumps(r, ensure_ascii=False))
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    gerado = now_iso()
    write_json_gz(destino / "ibge_municipios.json.gz", {
        "snapshot_date": date_str, "generated_at": gerado, "fonte": "IBGE, Censo Demográfico 2022 (SIDRA 4714 e 4712) e Estimativas de População (SIDRA 6579)", "censo_ano": censo_ano,
        "estimativa_ano": estimativa_ano,
        "total": len(muns), "municipios": muns})
    write_json_gz(destino / "ibge_taxa_internet.json.gz", {
        "snapshot_date": date_str, "generated_at": gerado, "fonte": "IBGE, PNAD Contínua anual (SIDRA 7307)", "pnad_ano": pnad_ano,
        "brasil": taxas.get("BR") or _soma_brasil(ufs), "ufs": dict(sorted(ufs.items()))})
    log.info("ibge_censo_pnad written", municipios=len(muns), censo_ano=censo_ano, pnad_ano=pnad_ano)
    return {"municipios": len(muns), "censo_ano": censo_ano, "estimativa_ano": estimativa_ano, "pnad_ano": pnad_ano}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="IBGE: população, domicílios e uso de internet (SIDRA)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre refeita")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        run(a.date, data_dir(), log)
    except Exception:
        log.exception("falha na coleta de ibge_censo_pnad")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
