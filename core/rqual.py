# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Indicadores de qualidade da Anatel (RQUAL), a partir de `Tabela_CSV_Indicadores_RQUAL.csv`.

O CSV tem ~18 milhões de linhas (município × prestadora × serviço × indicador × mês, desde 2022) e é lido **em fluxo**, uma linha por vez. O que sai é agregado, sem ordenar nem julgar ninguém:

  * `nacional`: por serviço × prestadora × indicador × mês, municípios medidos, medidas, média simples, média ponderada pelo número de medidas e mediana dos municípios;
  * `uf`: o mesmo por UF e ano (médias, sem mediana);
  * `municipios`: o último resultado numérico de cada município × serviço × prestadora × indicador, com medidas, coletores, erro amostral e intervalo.

Resultado não numérico (`NA`, `NO`, `NI`) é contado, não somado: o arquivo não documenta o significado dos códigos. O RQUAL só cobre as grandes prestadoras de cada serviço (13 na banda larga fixa, 7 na telefonia fixa e 4 na móvel
no arquivo de 2026-11); a ausência de uma empresa aqui não diz nada sobre a qualidade dela.
"""
from __future__ import annotations

import csv
import io
from array import array
from collections import Counter, defaultdict
from typing import IO

COLUNAS = ("Ano", "Mês", "Serviço", "Indicador", "Descrição", "Tipo", "Grupo", "Código IBGE", "Município", "UF", "Prestadora", "Resultado", "Unidade de Medida", "Número de Coletores",
           "Número de Medidas", "Erro Amostral", "Estatística", "Limite Inferior", "Limite Superior", "Valor de Referência Superior", "Valor de Referência Inferior")
SERVICOS = ("Banda Larga Fixa", "Telefonia Fixa", "Telefonia Móvel")


def numero(v: str) -> float | None:
    """`94,0199` → 94.0199; `NA`/`NO`/`NI`/vazio → None."""
    v = (v or "").strip()
    if not v or not (v[0].isdigit() or v[0] in "-+"):
        return None
    try:
        return float(v.replace(",", "."))
    except ValueError:
        return None


def _inteiro(v: str) -> int | None:
    n = numero(v)
    return int(n) if n is not None else None


def _mediana(a: array) -> float:
    s = sorted(a)
    m = len(s) // 2
    return float(s[m]) if len(s) % 2 else (s[m - 1] + s[m]) / 2


class _Estat:
    """Acumulador de um grupo: contagem, soma simples e soma ponderada pelo número de medidas."""
    __slots__ = ("n", "soma", "medidas", "peso", "soma_pond", "municipios", "valores")

    def __init__(self, guardar: bool):
        self.n = self.soma = self.medidas = self.peso = self.soma_pond = 0
        self.municipios: set[str] = set()
        self.valores = array("f") if guardar else None

    def add(self, v: float, medidas: int | None, ibge: str) -> None:
        self.n += 1
        self.soma += v
        self.municipios.add(ibge)
        if self.valores is not None:
            self.valores.append(v)
        if medidas:
            self.medidas += medidas
            self.peso += medidas
            self.soma_pond += v * medidas

    def saida(self) -> dict:
        d = {"municipios": len(self.municipios), "resultados": self.n, "medidas": self.medidas or None, "media": round(self.soma / self.n, 4),
             "media_ponderada": round(self.soma_pond / self.peso, 4) if self.peso else None}
        if self.valores is not None:
            d["mediana"] = round(_mediana(self.valores), 4)
        return d


def consolidar(csv_bytes: IO[bytes]) -> dict:
    """Lê o CSV em fluxo e devolve o documento normalizado. Falha alto se faltar coluna (leiaute mudou)."""
    leitor = csv.reader(io.TextIOWrapper(csv_bytes, encoding="utf-8-sig", newline=""), delimiter=";")
    cab = next(leitor)
    faltam = [c for c in COLUNAS if c not in cab]
    if faltam:
        raise RuntimeError(f"anatel_rqual: colunas ausentes {faltam}; o leiaute mudou")
    ix = {c: cab.index(c) for c in COLUNAS}
    i_ano, i_mes, i_serv, i_cod, i_desc, i_tipo, i_grupo = (ix[c] for c in ("Ano", "Mês", "Serviço", "Indicador", "Descrição", "Tipo", "Grupo"))
    i_ibge, i_mun, i_uf, i_prest, i_res, i_un = (ix[c] for c in ("Código IBGE", "Município", "UF", "Prestadora", "Resultado", "Unidade de Medida"))
    i_col, i_med, i_err, i_est, i_li, i_ls, i_rs, i_ri = (ix[c] for c in ("Número de Coletores", "Número de Medidas", "Erro Amostral", "Estatística", "Limite Inferior", "Limite Superior",
                                                                         "Valor de Referência Superior", "Valor de Referência Inferior"))
    nacional: dict[tuple, _Estat] = {}
    uf: dict[tuple, _Estat] = {}
    ultimo: dict[tuple, tuple] = {}
    indicadores: dict[tuple, dict] = {}
    refs: dict[tuple, Counter] = defaultdict(Counter)
    prest_mun: dict[tuple, set] = defaultdict(set)
    sem_valor: Counter = Counter()
    municipios: dict[str, tuple] = {}
    linhas = numericas = 0
    mes_min = mes_max = None
    for r in leitor:
        if len(r) < len(cab):
            continue
        linhas += 1
        serv, cod, prest, ibge = r[i_serv], r[i_cod], r[i_prest], r[i_ibge]
        ano, mes = int(r[i_ano]), int(r[i_mes])
        am = ano * 100 + mes
        mes_min = am if mes_min is None or am < mes_min else mes_min
        mes_max = am if mes_max is None or am > mes_max else mes_max
        chave_ind = (serv, cod)
        if chave_ind not in indicadores:
            indicadores[chave_ind] = {"servico": serv, "codigo": cod, "descricao": r[i_desc], "tipo": r[i_tipo], "grupo": r[i_grupo], "unidade": r[i_un]}
        refs[chave_ind][(r[i_rs], r[i_ri])] += 1
        prest_mun[(serv, prest)].add(ibge)
        municipios.setdefault(ibge, (r[i_mun], r[i_uf]))
        v = numero(r[i_res])
        if v is None:
            sem_valor[(r[i_res] or "").strip() or "(vazio)"] += 1
            continue
        numericas += 1
        medidas = _inteiro(r[i_med])
        k = (serv, prest, cod, am)
        e = nacional.get(k)
        if e is None:
            e = nacional[k] = _Estat(True)
        e.add(v, medidas, ibge)
        ku = (r[i_uf], serv, prest, cod, ano)
        e = uf.get(ku)
        if e is None:
            e = uf[ku] = _Estat(False)
        e.add(v, medidas, ibge)
        km = (ibge, serv, prest, cod)
        atual = ultimo.get(km)
        if atual is None or am > atual[0]:
            ultimo[km] = (am, v, medidas, _inteiro(r[i_col]), numero(r[i_err]), r[i_est].strip().upper() == "SIM", numero(r[i_li]), numero(r[i_ls]))
    for (serv, cod), d in indicadores.items():
        (sup, inf), _ = refs[(serv, cod)].most_common(1)[0]
        d["referencia_superior"], d["referencia_inferior"] = sup or None, inf or None
    ym = lambda n: f"{n // 100:04d}-{n % 100:02d}"      # noqa: E731
    dados_mun: dict[str, dict] = {}
    for (ibge, serv, prest, cod), (am, v, medidas, col, err, est, li, ls) in sorted(ultimo.items()):
        m = dados_mun.setdefault(ibge, {"nome": municipios[ibge][0], "uf": municipios[ibge][1], "itens": []})
        m["itens"].append({"servico": serv, "prestadora": prest, "indicador": cod, "mes": ym(am), "resultado": round(v, 4), "medidas": medidas, "coletores": col, "erro_amostral": err,
                           "estatistica": est, "limite_inferior": li, "limite_superior": ls})
    return {
        "resumo": {"linhas": linhas, "resultados_numericos": numericas, "sem_valor": dict(sem_valor), "municipios": len(municipios), "municipios_com_resultado": len(dados_mun),
                   "mes_inicial": ym(mes_min) if mes_min else None, "mes_final": ym(mes_max) if mes_max else None, "itens_municipais": len(ultimo)},
        "indicadores": sorted(indicadores.values(), key=lambda d: (d["servico"], d["codigo"])),
        "prestadoras": [{"servico": s, "prestadora": p, "municipios": len(m)} for (s, p), m in sorted(prest_mun.items())],
        "nacional": [{"servico": s, "prestadora": p, "indicador": c, "mes": ym(am), **e.saida()} for (s, p, c, am), e in sorted(nacional.items())],
        "uf": [{"uf": u, "servico": s, "prestadora": p, "indicador": c, "ano": a, **e.saida()} for (u, s, p, c, a), e in sorted(uf.items())],
        "municipios": dados_mun,
    }
