# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Produtos regulatórios. Saídas em `published/{date}/regulatorio/`.

  * `fust.json.gz` — compromissos do FUST por município, UF, programa e edital.
  * `multas.json.gz` — multas constituídas da Anatel por empresa (SCM, SMP, STFC e SeAC; só pessoa jurídica) e por ano.
  * `faixas.json.gz` — quadro de atribuição e destinação de faixas (PDFF) com as faixas de interesse para a Internet.
  * `satelites.json.gz` — direitos de exploração de satélite, constelações NGEO e satélites em operação comercial.

O FUST do arquivo da Anatel não identifica a empresa executora: aqui não há operadora. A situação (Atendido, A vencer, Em apuração) é a que a Anatel registra; "Em apuração" não é
inadimplência. Valor é o investimento total previsto no compromisso, não o desembolsado.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from core.common import normalized_path, now_iso, published_path
from core.fust import STATUS
from core.pdff import REFERENCIAS
from core.satelites import sem_copias, sistemas_ngeo
from core.jsonio import carregar_json_gz, gravar_json_gz

LIMITES_FUST = (
    "Compromissos de aplicação do FUST registrados pela Anatel (programa, edital, prazo e situação). Não identifica a empresa executora, então não há ligação com operadoras. "
    "'Em apuração' é a situação registrada pela Anatel, não inadimplência. O valor é o investimento total previsto no compromisso, não o desembolsado. "
    "Um compromisso é uma escola, unidade de saúde, favela, localidade ou município a atender."
)
_CHAVE_STATUS = {"Atendido": "atendidos", "A vencer": "a_vencer", "Em apuração": "em_apuracao"}


def _codigo(programa: str) -> str:
    return programa.split(" - ", 1)[0].strip() or programa


def _agrega(itens: list[dict]) -> dict:
    s = Counter(i["status"] for i in itens)
    return {"compromissos": len(itens), **{_CHAVE_STATUS[k]: s.get(k, 0) for k in STATUS}, "investimento": round(sum(i["investimento"] or 0 for i in itens), 2)}


def calcular_fust(compromissos: list[dict], ibge_muns: dict[str, dict]) -> dict:
    por_mun: dict[str, list[dict]] = defaultdict(list)
    sem_municipio = 0
    for c in compromissos:
        if c.get("ibge") in ibge_muns:
            por_mun[c["ibge"]].append(c)
        else:
            sem_municipio += 1
    municipios = {}
    for ibge, itens in sorted(por_mun.items()):
        m = ibge_muns[ibge]
        pop = m.get("populacao_estimada") or m.get("populacao")
        municipios[ibge] = {"nome": m.get("nome"), "uf": m["uf"], **_agrega(itens), "programas": dict(Counter(_codigo(i["programa"]) for i in itens).most_common()),
                            "tipos": dict(Counter(i["tipo"] for i in itens).most_common()), **({"por_10mil_hab": round(len(itens) * 10000 / pop, 2)} if pop else {})}
    ufs = {}
    for uf in sorted({m["uf"] for m in ibge_muns.values()}):
        itens = [c for i, lst in por_mun.items() if ibge_muns[i]["uf"] == uf for c in lst]
        muns_uf = [i for i, m in ibge_muns.items() if m["uf"] == uf]
        ufs[uf] = {**_agrega(itens), "municipios": len(muns_uf), "municipios_com_compromisso": sum(1 for i in muns_uf if i in por_mun),
                   "programas": dict(Counter(_codigo(i["programa"]) for i in itens).most_common())}
    dentro = [c for lst in por_mun.values() for c in lst]
    nomes: dict[str, str] = {}
    for c in compromissos:
        nomes.setdefault(_codigo(c["programa"]), c["programa"].split(" - ", 1)[-1].strip())
    programas = [{"codigo": k, "nome": nomes[k], **_agrega([c for c in dentro if _codigo(c["programa"]) == k]),
                  "municipios": len({c["ibge"] for c in dentro if _codigo(c["programa"]) == k})} for k in sorted(nomes)]
    editais = [{"origem": o, **_agrega([c for c in dentro if c["origem"] == o]), "municipios": len({c["ibge"] for c in dentro if c["origem"] == o})}
               for o, _ in Counter(c["origem"] for c in dentro).most_common()]
    brasil = {**_agrega(dentro), "municipios": len(ibge_muns), "municipios_com_compromisso": len(por_mun), "programas": len(programas), "editais": len(editais)}
    casamento = {"compromissos": len(compromissos), "com_municipio_no_ibge": len(dentro), "sem_municipio_no_ibge": sem_municipio,
                 "base_2010": sum(1 for c in dentro if c["base_ibge"] == "IBGE_2010"), "base_2022": sum(1 for c in dentro if c["base_ibge"] == "IBGE_2022"),
                 "sem_investimento": sum(1 for c in compromissos if c["investimento"] is None)}
    return {"brasil": brasil, "ufs": ufs, "programas": programas, "editais": editais, "municipios": municipios, "casamento": casamento}


LIMITES_MULTAS = (
    "Multas constituídas pela Anatel contra pessoas jurídicas prestadoras de SCM, SMP, STFC e SeAC (agregadas por raiz do CNPJ, matriz e filiais). Multa constituída não é condenação definitiva: pode estar "
    "quitada, parcelada, suspensa judicialmente ou em recurso (a situação é a do arquivo). Pessoa física, radiodifusão, serviços privados e multas sem serviço (a quem não tem outorga) ficam de fora. "
    "O saldo devedor é o valor atualizado informado pela Anatel; o ano é o da aplicação da sanção."
)
LIMITES_FAIXAS = (
    "Quadro de atribuição e destinação de faixas da Anatel (PDFF): para que serviços cada faixa pode ser usada no Brasil. É norma, não licença: não diz quem explora a faixa, nem se está em uso. "
    "Os nomes das faixas de interesse (700 MHz, 3,5 GHz, Wi-Fi 6 GHz...) são referência do Arandurapé, não nomes oficiais."
)
LIMITES_SATELITES = (
    "Direitos de exploração de satélite no Brasil, constelações de órbita não geoestacionária (NGEO) e satélites em operação comercial, segundo a Anatel. Muitas operadoras são estrangeiras, sem CNPJ "
    "brasileiro nos direitos, e não se ligam aos grupos do SICI. Direito concedido não é capacidade em uso nem assinantes."
)


def _soma(es: list[dict]) -> dict:
    sit: Counter = Counter()
    for e in es:
        sit.update(e["situacoes"])
    return {"empresas": len(es), "multas": sum(e["multas"] for e in es), "original": round(sum(e["original"] for e in es), 2), "pago": round(sum(e["pago"] for e in es), 2),
            "saldo": round(sum(e["saldo"] for e in es), 2), "situacoes": dict(sit)}


def calcular_multas(empresas: list[dict]) -> dict:
    ordenadas = sorted(empresas, key=lambda e: (-e["saldo"], -e["multas"], e["raiz"], e["grupo"]))
    linhas = [{**e, "cnpj_matriz": next((c for c in e["cnpjs"] if c[8:12] == "0001"), None)} for e in ordenadas]
    grupos = sorted({e["grupo"] for e in empresas})
    por_ano: dict[str, dict] = {}
    for e in empresas:
        for ano, n in e["anos"].items():
            por_ano.setdefault(ano, {g: 0 for g in grupos})[e["grupo"]] += n
    return {"brasil": _soma(empresas), "por_grupo": {g: _soma([e for e in empresas if e["grupo"] == g]) for g in grupos},
            "por_ano": [{"ano": int(a), **v, "total": sum(v.values())} for a, v in sorted(por_ano.items())], "empresas": linhas}


def calcular_faixas(faixas: list[dict]) -> dict:
    refs = []
    for nome, ini, fim in REFERENCIAS:
        dentro = [f for f in faixas if f["fim_mhz"] > ini and f["ini_mhz"] < fim]
        servicos: dict[str, str] = {}
        for f in dentro:
            for d in f["destinacao"]:
                if d["carater"] == "Primário" or d["servico"] not in servicos:
                    servicos[d["servico"]] = d["carater"]
        refs.append({"nome": nome, "ini_mhz": ini, "fim_mhz": fim, "faixas": len(dentro), "destinacao": [{"servico": k, "carater": v} for k, v in sorted(servicos.items(), key=lambda kv: (kv[1] != "Primário", kv[0]))]})
    return {"referencias": refs, "faixas": faixas, "resumo": {"faixas": len(faixas), "com_destinacao": sum(1 for f in faixas if f["destinacao"]),
                                                                "com_atribuicao": sum(1 for f in faixas if f["atribuicao"]), "de_interesse": len(refs)}}


def calcular_satelites(tabelas: dict, data: str) -> dict:
    d = tabelas["direitos"]
    tabelas = {**tabelas, "ngeo": sem_copias(tabelas["ngeo"])}          # normalizado antigo ainda traz as cópias exatas da origem
    vencidos = [x for x in d if x["validade"] and x["validade"] < data]
    resumo = {"direitos": len(d), "operadoras": len({x["operadora"] for x in d}), "satelites": len({x["satelite"] for x in d}), "por_tipo": dict(Counter(x["tipo"] for x in d)),
              "por_status": dict(Counter(x["status"] for x in d)), "vencidos_na_data": len(vencidos), "ngeo": len(tabelas["ngeo"]), "operando": len(tabelas["operando"]),
              "ngeo_por_orbita": dict(Counter(x["orbita"] for x in tabelas["ngeo"]))}
    # `ngeo` é registro (um por sistema e ano de agenda); `ngeo_sistemas`, um por sistema (REGULATORIO-E1)
    sistemas = sistemas_ngeo(tabelas["ngeo"])
    resumo["ngeo_sistemas"] = len(sistemas)
    return {"resumo": resumo, "direitos": d, "ngeo": tabelas["ngeo"], "ngeo_sistemas": sistemas, "operando": tabelas["operando"]}


def publicar_regulatorio(base: Path, date_str: str, log) -> dict:
    norm = normalized_path(base, date_str, "summary")
    pub = published_path(base, date_str)
    ibge = carregar_json_gz(norm / "ibge_municipios.json.gz")
    saida: dict = {}
    destino = pub / "regulatorio"
    fust = carregar_json_gz(norm / "anatel_fust.json.gz")
    if fust and ibge:
        r = calcular_fust(fust["compromissos"], ibge["municipios"])
        destino.mkdir(parents=True, exist_ok=True)
        gravar_json_gz(destino / "fust.json.gz", {
            "snapshot_date": date_str, "generated_at": now_iso(), "fonte": "Anatel, dados abertos (FUST) e IBGE", "data_arquivo": fust.get("data_arquivo"),
            "natureza": "cadastro_regulatorio", "limites": LIMITES_FUST, **r})
        log.info("regulatorio/fust written", compromissos=r["brasil"]["compromissos"], municipios=r["brasil"]["municipios_com_compromisso"])
        saida["fust"] = {"compromissos": r["brasil"]["compromissos"], "municipios": r["brasil"]["municipios_com_compromisso"], "sem_municipio": r["casamento"]["sem_municipio_no_ibge"]}
    else:
        log.info("FUST ou IBGE ausentes: regulatorio/fust não gerado")
    meta = lambda doc: {"snapshot_date": date_str, "generated_at": now_iso(), "data_arquivo": doc.get("data_arquivo")}      # noqa: E731
    mu = carregar_json_gz(norm / "anatel_multas.json.gz")
    if mu:
        r = calcular_multas(mu["empresas"])
        destino.mkdir(parents=True, exist_ok=True)
        gravar_json_gz(destino / "multas.json.gz", {**meta(mu), "fonte": "Anatel, dados abertos (multas constituídas)", "natureza": "cadastro_regulatorio", "limites": LIMITES_MULTAS,
                                                    "leitura": mu["resumo"], **r})
        saida["multas"] = {"empresas": r["brasil"]["empresas"], "multas": r["brasil"]["multas"], "saldo": r["brasil"]["saldo"]}
        log.info("regulatorio/multas written", **saida["multas"])
    pd = carregar_json_gz(norm / "anatel_pdff.json.gz")
    if pd:
        r = calcular_faixas(pd["faixas"])
        destino.mkdir(parents=True, exist_ok=True)
        gravar_json_gz(destino / "faixas.json.gz", {**meta(pd), "fonte": "Anatel, dados abertos (PDFF)", "natureza": "norma", "limites": LIMITES_FAIXAS, **r})
        saida["faixas"] = r["resumo"]
        log.info("regulatorio/faixas written", **r["resumo"])
    st = carregar_json_gz(norm / "anatel_satelites.json.gz")
    if st:
        r = calcular_satelites(st, date_str)
        destino.mkdir(parents=True, exist_ok=True)
        gravar_json_gz(destino / "satelites.json.gz", {**meta(st), "fonte": "Anatel, dados abertos (satélites)", "natureza": "cadastro_regulatorio", "limites": LIMITES_SATELITES, **r})
        saida["satelites"] = r["resumo"]
        log.info("regulatorio/satelites written", direitos=r["resumo"]["direitos"])
    return saida
