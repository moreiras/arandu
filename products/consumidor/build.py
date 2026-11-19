# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Reclamações no Consumidor.gov.br. Saídas em `published/{date}/consumidor/`.

  * `consumidor.json.gz` — por empresa (nome fantasia): série mensal e janela de 12 meses (finalizadas, respondidas, índice de solução, tempo médio de resposta e nota média), por UF,
    por assunto e por grupo de problema, mais o total do setor por mês e a cobertura da ligação empresa → CNPJ.
  * `consumidor_municipios/{UF}.json.gz` — o mesmo por município (casado ao código IBGE pelo nome) e empresa, na janela.

**Só agregados.** O arquivo de origem tem sexo e faixa etária de quem reclamou; aqui nada disso entra (ver `core/consumidor.py`). Uma média, índice ou nota só sai com base mínima
(`MIN_BASE`) e uma linha de município × empresa só sai com `MIN_CELULA` reclamações; a menor célula publicada nunca é de uma ou duas pessoas. A ligação empresa → CNPJ reusa a tabela curada
de `core/marcas.py` (com apelidos do Consumidor.gov.br). Sem ranking nem veredito: as listas saem em ordem alfabética.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from core import consumidor as cg
from core import marcas as m
from core.common import normalized_path, now_iso, published_path
from core.jsonio import carregar_json_gz, gravar_json_gz
from products.qualidade.build import MIN_CONCENTRACAO_UF, _matrizes, _outorgas, _ufs_por_raiz

JANELA_MESES = 12
MIN_BASE = 30           # abaixo disso a média, o índice e a nota oscilam demais para serem publicados
MIN_CELULA = 5          # linhas município × empresa com menos reclamações no ano não são publicadas (a soma do município as inclui)
LIMITES = (
    "Reclamações FINALIZADAS (a empresa respondeu ou o prazo acabou) de consumidores no Consumidor.gov.br, serviço público e gratuito da Senacon (Ministério da Justiça e Segurança Pública), só do segmento "
    "de operadoras de telecomunicações; não é o total de reclamações contra a empresa (as da Anatel e as dos Procons são outras bases) e só empresas que aderiram à plataforma aparecem. Reclamação não é "
    "prova de falha da empresa e o número depende do tamanho da base de clientes: não há taxa por cliente aqui. O índice de solução é resolvidas ÷ avaliadas pelo consumidor (quem não avaliou não entra); "
    "o tempo médio é em dias, só das respondidas; a nota é a média (1 a 5) das avaliações. Média, índice e nota só aparecem com pelo menos "
    f"{MIN_BASE} casos; linha de município × empresa só com pelo menos {MIN_CELULA} reclamações no ano. A cidade vem como nome digitado e é casada ao código IBGE por nome e UF (o que não casa fica fora dos "
    "municípios). A ligação empresa → CNPJ é curada (config/curada_marcas_operadoras.yaml) ou automática por nome fantasia único, nunca um palpite. Sem ranking."
)


def _meses_janela(meses: list[str]) -> list[str]:
    return sorted(meses)[-JANELA_MESES:]


def _soma(acc: list[int], c: dict) -> None:
    for i, k in enumerate(cg.CAMPOS_CELULA):
        acc[i] += c[k]


def metricas(v: list[int]) -> dict:
    """De `[n, respondidas, avaliadas, resolvidas, tempo_n, tempo_soma, nota_n, nota_soma]` para os indicadores, com a base mínima. Chaves nulas dizem "base insuficiente", não zero."""
    n, resp, aval, resolv, tn, ts, nn, ns = v
    return {"n": n, "respondidas": resp, "avaliadas": aval, "resolvidas": resolv,
            "pct_respondidas": round(100 * resp / n, 1) if n >= MIN_BASE else None,
            "indice_solucao": round(100 * resolv / aval, 1) if aval >= MIN_BASE else None,
            "tempo_medio_dias": round(ts / tn, 2) if tn >= MIN_BASE else None,
            "nota_media": round(ns / nn, 2) if nn >= MIN_BASE else None}


def _normalizar_cidade(s: str) -> str:
    return m.normalizar(s)


class ResolvedorMunicipios:
    """Casa o nome digitado da cidade ao código IBGE, por UF e nome normalizado (sem acento, caixa nem pontuação). Nome repetido na UF não casa. O arquivo traz `?` no lugar de letra acentuada em
    alguns nomes (`Ub?` por Ubá): nesses, o `?` vale uma letra e só se aceita se exatamente um município da UF servir."""

    def __init__(self, ibge: dict | None) -> None:
        self.exato: dict[tuple[str, str], str | None] = {}
        self.por_uf: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for cod, mun in ((ibge or {}).get("municipios") or {}).items():
            n = _normalizar_cidade(mun["nome"])
            k = (mun["uf"], n)
            self.exato[k] = None if k in self.exato else cod
            self.por_uf[mun["uf"]].append((n, cod))
        self.com_interrogacao = 0

    def resolver(self, uf: str, cidade: str) -> str | None:
        if "?" not in cidade:
            return self.exato.get((uf, _normalizar_cidade(cidade)))
        padrao = re.compile("".join("[A-Z0-9]" if ch == "?" else _normalizar_cidade(ch) for ch in cidade))
        achados = {cod for n, cod in self.por_uf.get(uf, []) if padrao.fullmatch(n)}
        if len(achados) == 1:
            self.com_interrogacao += 1
            return next(iter(achados))
        return None


def calcular(norm: dict, curada: dict, fantasia: dict, ufs_raiz: dict, matrizes: dict, ibge: dict | None) -> tuple[dict, dict]:
    """Devolve `(documento nacional, municípios por UF)` a partir do normalizado `consumidor_gov`."""
    calendario = sorted(norm["meses"])                      # todos os meses publicados, também os que não puderam ser lidos
    janela = _meses_janela(calendario)
    na_janela = set(janela)
    ausentes = [mes for mes in janela if "resumo" not in norm["meses"][mes]]
    meses_todos = [mes for mes in calendario if "resumo" in norm["meses"][mes]]
    por_mes: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0] * len(cg.CAMPOS_CELULA))     # (marca, mes)
    setor_mes: dict[str, list[int]] = defaultdict(lambda: [0] * len(cg.CAMPOS_CELULA))
    janela_marca: dict[str, list[int]] = defaultdict(lambda: [0] * len(cg.CAMPOS_CELULA))
    uf_marca: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0] * len(cg.CAMPOS_CELULA))
    mun_marca: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0] * len(cg.CAMPOS_CELULA))     # (ibge, marca)
    mun_total: dict[str, list[int]] = defaultdict(lambda: [0] * len(cg.CAMPOS_CELULA))
    sem_municipio = 0
    total_janela = 0
    resolvedor = ResolvedorMunicipios(ibge)
    nomes = {cod: mun for cod, mun in ((ibge or {}).get("municipios") or {}).items()}
    cidades_sem: dict[tuple[str, str], int] = defaultdict(int)
    for mes in meses_todos:
        for c in norm["meses"][mes]["cidades"]:
            _soma(por_mes[(c["marca"], mes)], c)
            _soma(setor_mes[mes], c)
            if mes not in na_janela:
                continue
            _soma(janela_marca[c["marca"]], c)
            _soma(uf_marca[(c["marca"], c["uf"])], c)
            total_janela += c["n"]
            cod = resolvedor.resolver(c["uf"], c["cidade"])
            if cod:
                _soma(mun_marca[(cod, c["marca"])], c)
                _soma(mun_total[cod], c)
            else:
                sem_municipio += c["n"]
                cidades_sem[(c["uf"], c["cidade"])] += c["n"]
    ass: dict[tuple[str, str], int] = defaultdict(int)
    grp: dict[tuple[str, str], int] = defaultdict(int)
    for mes in (x for x in janela if x not in ausentes):
        for a in norm["meses"][mes]["assuntos"]:
            ass[(a["marca"], a["assunto"])] += a["n"]
        for g in norm["meses"][mes]["grupos"]:
            grp[(g["marca"], g["grupo"])] += g["n"]
    marca_uf_n: dict[str, dict[str, int]] = defaultdict(dict)
    for (marca, uf), v in uf_marca.items():
        marca_uf_n[marca][uf] = v[0]
    descartadas: list[str] = []
    cache: dict[str, dict | None] = {}

    def casa(marca: str):
        if marca not in cache:
            c = m.casar_consumidor(marca, curada, fantasia)
            if c and c["metodo"] == "automatico":
                total = sum(marca_uf_n[marca].values())
                ufs = ufs_raiz.get(c["raizes"][0], set())
                dentro = sum(q for u, q in marca_uf_n[marca].items() if u in ufs)
                if not total or dentro / total < MIN_CONCENTRACAO_UF:
                    descartadas.append(marca)
                    c = None
            cache[marca] = c
        return cache[marca]

    marcas_doc = []
    cob = defaultdict(int)
    for marca in sorted({k[0] for k in por_mes}):
        c = casa(marca)
        serie = [{"mes": mes, **metricas(por_mes[(marca, mes)])} for mes in meses_todos if (marca, mes) in por_mes]
        jan = metricas(janela_marca[marca]) if marca in janela_marca else None
        marcas_doc.append({"marca": marca, "raizes": c["raizes"] if c else [], "cnpjs_matriz": [matrizes[r] for r in c["raizes"] if r in matrizes] if c else [], "casamento": c["metodo"] if c else None,
                           "base_casamento": c["base"] if c else None, "janela": jan, "por_mes": serie})
        if jan:
            cob["curada" if c and c["metodo"] == "curada" else "automatico" if c else "sem_cnpj"] += jan["n"]
    total_cob = sum(cob.values())
    uf_doc = [{"marca": marca, "uf": uf, **metricas(v)} for (marca, uf), v in sorted(uf_marca.items()) if v[0] >= MIN_CELULA]
    doc = {"municipios_uf": {cod: mun["uf"] for cod, mun in nomes.items()},
           "janela": {"de": janela[0], "ate": janela[-1], "meses": len(janela), "meses_com_dado": len(janela) - len(ausentes), "meses_ausentes": ausentes,
                      "aviso": f"sem dado em {', '.join(ausentes)}: o arquivo do mês não pôde ser lido; os totais da janela cobrem {len(janela) - len(ausentes)} de {len(janela)} meses" if ausentes else None},
           "meses_disponiveis": meses_todos,
           "setor_por_mes": [{"mes": mes, **metricas(setor_mes[mes])} for mes in meses_todos],
           "marcas": marcas_doc, "uf": uf_doc,
           "assuntos": [{"marca": k[0], "assunto": k[1], "n": v} for k, v in sorted(ass.items()) if v >= MIN_CELULA],
           "grupos": [{"marca": k[0], "grupo": k[1], "n": v} for k, v in sorted(grp.items()) if v >= MIN_CELULA],
           "casamento": {"reclamacoes_janela": total_cob, "por_metodo": dict(cob), "pct_com_cnpj": round(100 * (cob["curada"] + cob["automatico"]) / total_cob, 2) if total_cob else None,
                         "automaticas_descartadas_por_uf": sorted(descartadas), "marcas": len(marcas_doc), "marcas_com_cnpj": sum(1 for x in marcas_doc if x["raizes"]),
                         "tabela_curada": {"versao": curada["versao"], "curada_em": curada["curada_em"], "fonte": curada["fonte_da_curadoria"], "marcas": len(curada["marcas"]), "apelidos_consumidor_gov": len(curada.get("aliases_consumidor_gov") or {})}},
           "cidades": {"reclamacoes_janela": total_janela, "sem_codigo_ibge": sem_municipio, "casadas_com_interrogacao": resolvedor.com_interrogacao, "pct_com_codigo_ibge": round(100 * (total_janela - sem_municipio) / total_janela, 2) if total_janela else None,
                       "maiores_sem_codigo": [{"uf": k[0], "cidade": k[1], "n": v} for k, v in sorted(cidades_sem.items(), key=lambda t: (-t[1], t[0]))[:10]]},
           "leitura": norm["resumo"]}
    por_uf: dict[str, dict] = defaultdict(dict)
    por_mun: dict[str, list] = defaultdict(list)
    for (cod, marca), v in sorted(mun_marca.items()):
        if v[0] >= MIN_CELULA:
            c = casa(marca)
            por_mun[cod].append({"marca": marca, "raizes": c["raizes"] if c else [], **metricas(v)})
    for cod, tot in mun_total.items():
        mun = nomes[cod]
        itens = por_mun.get(cod, [])
        por_uf[mun["uf"]][cod] = {"nome": mun["nome"], "uf": mun["uf"], "populacao": mun.get("populacao_estimada") or mun.get("populacao"), "total": metricas(tot), "itens": itens}
    return doc, por_uf


def publicar_consumidor(base: Path, date_str: str, log) -> dict:
    norm_dir = normalized_path(base, date_str, "summary")
    norm = carregar_json_gz(norm_dir / "consumidor_gov.json.gz")
    if not norm:
        log.info("consumidor_gov ausente: consumidor não gerado")
        return {}
    outorgas = _outorgas(norm_dir)
    ibge = carregar_json_gz(norm_dir / "ibge_municipios.json.gz")
    doc, por_uf = calcular(norm, m.carregar_curada(), m.indice_fantasia(outorgas), _ufs_por_raiz(outorgas), _matrizes(outorgas), ibge)
    destino = published_path(base, date_str) / "consumidor"
    (destino / "consumidor_municipios").mkdir(parents=True, exist_ok=True)
    meta = {"snapshot_date": date_str, "generated_at": now_iso(), "fonte": norm["fonte"], "natureza": "declarado_por_consumidores", "url_fonte": norm["url"]}
    for uf, mun in por_uf.items():
        gravar_json_gz(destino / "consumidor_municipios" / f"{uf}.json.gz", {**meta, "uf": uf, "janela": doc["janela"], "municipios": mun})
    gravar_json_gz(destino / "consumidor.json.gz", {**meta, "limites": LIMITES, "minimos": {"base_para_media": MIN_BASE, "reclamacoes_por_celula": MIN_CELULA}, **doc})
    saida = {"marcas": doc["casamento"]["marcas"], "marcas_com_cnpj": doc["casamento"]["marcas_com_cnpj"], "pct_com_cnpj": doc["casamento"]["pct_com_cnpj"], "pct_com_codigo_ibge": doc["cidades"]["pct_com_codigo_ibge"],
             "municipios": sum(len(v) for v in por_uf.values())}
    log.info("consumidor written", **saida)
    return saida
