# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Estações do SMP licenciadas na Anatel: do CSV de uma linha por estação × setor × frequência para uma linha por **estação licenciada**.

O arquivo `estacoes_smp.zip` (dados abertos da Anatel) tem ~3,3 milhões de linhas para ~114 mil estações, por duas razões medidas em 2026-11-02:
  * variação real: cada estação tem vários setores, faixas e tecnologias (mediana de 7 combinações tecnologia × frequência × setor);
  * repetição da junção: cada registro vem ~3 vezes e **só uma das cópias traz o código IBGE** (as outras vêm com o município em branco).
Por isso o município da estação é o valor preenchido em qualquer de suas linhas, não o da primeira. A chave da estação é (Número Fistel, Número Estação). "Estação"
aqui é cadastro de licenciamento, não torre física: a mesma torre pode ter mais de um número de estação.

A consolidação é em fluxo (o CSV tem ~1 GB): guarda só os contadores por estação. A operadora vem da coluna "Empresa Estação" (marca); o CNPJ é o mais frequente
dessa marca no arquivo, porque a coluna de CNPJ vem em branco em ~44% das linhas.
"""
from __future__ import annotations

import csv
import io
from collections import Counter
from typing import BinaryIO

COLUNAS = {
    "fistel": "Número Fistel", "estacao": "Número Estação", "cnpj": "NumCnpjCpf", "marca": "Empresa Estação", "entidade": "Entidade", "tecnologia": "Tecnologia",
    "geracao": "Geração", "tipo_5g": "Tipo de Tecnologia 5G", "faixa": "Faixa Estação", "setor": "NumSetor", "lat": "Latitude decimal", "lon": "Longitude decimal",
    "ibge": "Código IBGE", "uf": "UF", "infra": "ClassInfraFisica", "primeira": "Data Primeiro Licenciamento", "situacao": "Situacao", "freq_tx": "FreqTxMHz",
}
GERACOES = ("2G", "3G", "4G", "5G")
BRASIL = (-34.0, 6.0, -74.5, -32.0)                       # lat mín., lat máx., lon mín., lon máx. (com folga)


class _Estacao:
    __slots__ = ("pos", "ibge", "uf", "marca", "entidade", "cnpj", "geracoes", "tecnologias", "tipo_5g", "faixas", "setores", "infra", "primeira", "linhas", "combos")

    def __init__(self) -> None:
        self.pos: Counter = Counter()
        self.ibge: Counter = Counter()
        self.uf: Counter = Counter()
        self.marca = self.entidade = ""
        self.cnpj: Counter = Counter()
        self.geracoes: set = set()
        self.tecnologias: set = set()
        self.tipo_5g: set = set()
        self.faixas: set = set()
        self.setores: set = set()
        self.infra: Counter = Counter()
        self.primeira: str = ""
        self.linhas = 0
        self.combos: set = set()


def _ano(data: str) -> int | None:
    """`dd/mm/aaaa` → ano."""
    try:
        return int(data.strip()[-4:])
    except ValueError:
        return None


def _num(v: str) -> float | None:
    try:
        return float(v.strip().replace(",", "."))
    except ValueError:
        return None


def consolidar(csv_bytes: BinaryIO) -> tuple[list[dict], dict]:
    """Devolve (estações, resumo da leitura). `csv_bytes`: arquivo binário do CSV (UTF-8, com ou sem BOM, separador `;`)."""
    leitor = csv.reader(io.TextIOWrapper(csv_bytes, encoding="utf-8-sig", newline=""), delimiter=";")
    cab = next(leitor)
    ix = {k: cab.index(v) for k, v in COLUNAS.items() if v in cab}
    faltam = [COLUNAS[k] for k in ("fistel", "estacao", "marca", "tecnologia", "geracao", "lat", "lon", "ibge") if k not in ix]
    if faltam:
        raise ValueError(f"colunas ausentes no CSV de estações do SMP: {faltam}")
    est: dict[tuple[str, str], _Estacao] = {}
    marca_cnpj: dict[str, Counter] = {}
    linhas = incompletas = 0
    for x in leitor:
        if len(x) < len(cab):
            incompletas += 1
            continue
        linhas += 1
        g = lambda k: x[ix[k]].strip() if k in ix else ""                  # noqa: E731
        e = est.get((g("fistel"), g("estacao")))
        if e is None:
            e = est[(g("fistel"), g("estacao"))] = _Estacao()
        e.linhas += 1
        e.marca = e.marca or g("marca")
        e.entidade = e.entidade or g("entidade")
        if g("cnpj"):
            e.cnpj[g("cnpj")] += 1
            marca_cnpj.setdefault(g("marca"), Counter())[g("cnpj")] += 1
        if g("lat") and g("lon"):
            e.pos[(g("lat"), g("lon"))] += 1
        if g("ibge"):
            e.ibge[g("ibge")] += 1
        if g("uf"):
            e.uf[g("uf")] += 1
        if g("geracao") in GERACOES:
            e.geracoes.add(g("geracao"))
        if g("tecnologia"):
            e.tecnologias.add(g("tecnologia"))
        if g("tipo_5g"):
            e.tipo_5g.add(g("tipo_5g"))
        if g("faixa"):
            e.faixas.add(g("faixa"))
        if g("setor"):
            e.setores.add(g("setor"))
        if g("infra"):
            e.infra[g("infra")] += 1
        a = _ano(g("primeira"))
        if a and (not e.primeira or a < int(e.primeira)):
            e.primeira = str(a)
        e.combos.add((g("tecnologia"), g("freq_tx"), g("setor")))
    cnpj_da_marca = {m: c.most_common(1)[0][0] for m, c in marca_cnpj.items()}
    saida: list[dict] = []
    sem_pos = fora = pos_var = sem_ibge = 0
    for (fistel, num), e in est.items():
        lat = lon = None
        if e.pos:
            la, lo = e.pos.most_common(1)[0][0]
            lat, lon = _num(la), _num(lo)
            if len(e.pos) > 1:
                pos_var += 1
        if lat is None or lon is None:
            sem_pos += 1
            lat = lon = None
        elif not (BRASIL[0] <= lat <= BRASIL[1] and BRASIL[2] <= lon <= BRASIL[3]):
            fora += 1
            lat = lon = None
        ibge = e.ibge.most_common(1)[0][0] if e.ibge else None
        sem_ibge += ibge is None
        saida.append({
            "fistel": fistel, "estacao": num, "marca": e.marca, "entidade": e.entidade, "cnpj": (e.cnpj.most_common(1)[0][0] if e.cnpj else cnpj_da_marca.get(e.marca)),
            "ibge": ibge, "uf": e.uf.most_common(1)[0][0] if e.uf else None, "lat": lat, "lon": lon, "posicao_variavel": len(e.pos) > 1,
            "geracoes": [g for g in GERACOES if g in e.geracoes], "tecnologias": sorted(e.tecnologias), "tipo_5g": sorted(e.tipo_5g), "faixas": sorted(e.faixas, key=lambda f: (len(f), f)),
            "setores": len(e.setores), "combinacoes": len(e.combos), "infra": e.infra.most_common(1)[0][0] if e.infra else None,
            "primeira_licenca": int(e.primeira) if e.primeira else None, "linhas": e.linhas,
        })
    saida.sort(key=lambda s: (s["fistel"], s["estacao"]))
    resumo = {"linhas": linhas, "linhas_incompletas": incompletas, "estacoes": len(saida), "sem_posicao": sem_pos, "fora_do_brasil": fora, "posicao_variavel": pos_var,
              "sem_ibge": sem_ibge, "cnpj_da_marca": cnpj_da_marca}
    return saida, resumo
