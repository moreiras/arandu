# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Estimativas por UF a partir dos microdados da TIC Domicílios: proporção, total e erro-padrão por réplicas.

O Cetic.br publica nas tabelas só Brasil, região, área, renda e classe. A base de microdados (desidentificada, CC BY 4.0) traz a UF e 200 pesos de réplica; o
erro amostral sai deles, como descreve o relatório metodológico da pesquisa: variância = média dos quadrados dos desvios das 200 réplicas em torno da
estimativa pontual, erro-padrão = raiz da variância, margem de erro = 1,96 × erro-padrão (95%). O número é **estimativa do Arandurapé**, não o publicado pelo
Cetic.br: a estimativa pontual coincide com a das tabelas oficiais (diferença abaixo de 0,01 ponto percentual), mas a margem oficial é de 1,08 a 1,14 vez a
estimada aqui nos recortes que as tabelas trazem (os pesos de réplica da base pública não reproduzem a calibração das tabelas), e a saída diz isso (`validacao`).

Só agregados saem daqui: a base de domicílios nunca é gravada no normalizado nem publicada.
"""
from __future__ import annotations

import csv
import io
import math
from operator import add
from typing import Optional

REPLICAS = 200
Z95 = 1.96
N_MINIMO = 30                    # grupo com menos domicílios entrevistados que isso é suprimido (sem proporção nem total)
CV_BAIXO = 0.30                  # erro-padrão ÷ proporção acima disso: precisão baixa (a estimativa sai, rotulada)

# id → (coluna da base, valor que conta, rótulo, definição)
INDICADORES = {
    "internet": ("A4", "1", "Domicílios com acesso à Internet", "A4 = Sim (o domicílio tem acesso à Internet), sobre todos os domicílios."),
    "computador": ("A1_AGREG", "1", "Domicílios com computador", "Computador de mesa, notebook ou tablet (A1 agregado), sobre todos os domicílios."),
    "banda_larga_fixa": ("A7_AGREG", "1", "Domicílios com banda larga fixa", "Principal conexão de banda larga fixa entre os domicílios com Internet (A7 agregado), sobre todos os domicílios."),
}
REGIOES = {"1": "Sudeste", "2": "Nordeste", "3": "Sul", "4": "Norte", "5": "Centro-Oeste"}
UFS = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE",
    "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}
REGIOES_UF = {"RO": "Norte", "AC": "Norte", "AM": "Norte", "RR": "Norte", "PA": "Norte", "AP": "Norte", "TO": "Norte", "MA": "Nordeste", "PI": "Nordeste", "CE": "Nordeste", "RN": "Nordeste", "PB": "Nordeste", "PE": "Nordeste", "AL": "Nordeste", "SE": "Nordeste", "BA": "Nordeste", "MG": "Sudeste", "ES": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste", "PR": "Sul", "SC": "Sul", "RS": "Sul", "MS": "Centro-Oeste", "MT": "Centro-Oeste", "GO": "Centro-Oeste", "DF": "Centro-Oeste"}
COLUNAS_FIXAS = ("COD_UF", "COD_REGIAO_2", "PESO") + tuple(c for c, *_ in INDICADORES.values())


def _num(v: str) -> float:
    return float(v.replace(",", "."))


class _Grupo:
    def __init__(self):
        self.n = 0
        self.den = [0.0] * (REPLICAS + 1)                       # [0] = peso amostral; [1..200] = réplicas
        self.num = {i: [0.0] * (REPLICAS + 1) for i in INDICADORES}


def _se(reps: list[float], ponto: float) -> float:
    return math.sqrt(sum((x - ponto) ** 2 for x in reps) / len(reps))


def _estimar(g: _Grupo, tipo: str, nome: str) -> dict:
    d = g.den
    out = {"tipo": tipo, "nome": nome, "n": g.n, "domicilios": round(d[0]), "domicilios_se": round(_se(d[1:], d[0]))}
    inds = {}
    for i, num in g.num.items():
        if g.n < N_MINIMO or d[0] <= 0:
            inds[i] = {"suprimido": f"menos de {N_MINIMO} domicílios entrevistados"}
            continue
        p = 100 * num[0] / d[0]
        reps_p = [100 * a / b for a, b in zip(num[1:], d[1:]) if b > 0]
        se = _se(reps_p, p)
        reps_t = num[1:]
        se_t = _se(reps_t, num[0])
        cv = se / p if p > 0 else None
        inds[i] = {"proporcao": round(p, 3), "erro_padrao": round(se, 3), "margem": round(Z95 * se, 3), "cv": None if cv is None else round(cv, 4),
                   "total": round(num[0]), "total_erro_padrao": round(se_t), "precisao": "baixa" if (cv is None or cv > CV_BAIXO) else "adequada"}
    out["indicadores"] = inds
    return out


def estimar(csv_bytes: bytes) -> tuple[dict, int]:
    """({'BR'|região|UF: estimativas}, linhas lidas). A base é lida em fluxo: nada dela fica na memória além dos acumuladores por grupo."""
    texto = io.StringIO(csv_bytes.decode("latin-1"))
    leitor = csv.DictReader(texto, delimiter=";")
    cab = leitor.fieldnames or []
    faltam = [c for c in COLUNAS_FIXAS + ("REP1", f"REP{REPLICAS}") if c not in cab]
    if faltam:
        raise RuntimeError(f"cetic microdados: colunas ausentes {faltam} (o layout da base mudou?)")
    cols_rep = [f"REP{i}" for i in range(1, REPLICAS + 1)]
    grupos: dict[tuple[str, str], _Grupo] = {}
    lidas = 0
    for r in leitor:
        uf, reg = UFS.get(r["COD_UF"]), REGIOES.get(r["COD_REGIAO_2"])
        if uf is None or reg is None:
            continue
        lidas += 1
        pesos = [_num(r["PESO"])] + [_num(r[c]) for c in cols_rep]
        for chave in (("brasil", "BR"), ("regiao", reg), ("uf", uf)):
            g = grupos.get(chave)
            if g is None:
                g = grupos[chave] = _Grupo()
            g.n += 1
            g.den[:] = map(add, g.den, pesos)
            for i, (coluna, valor, *_) in INDICADORES.items():
                if r[coluna] == valor:
                    g.num[i][:] = map(add, g.num[i], pesos)
    if lidas == 0:
        raise RuntimeError("cetic microdados: nenhuma linha válida")
    out = {}
    for (tipo, nome), g in sorted(grupos.items(), key=lambda kv: ({"brasil": 0, "regiao": 1, "uf": 2}[kv[0][0]], kv[0][1])):
        out[nome] = _estimar(g, tipo, nome)
    return out, lidas


def validar(grupos: dict, oficial: Optional[dict]) -> Optional[dict]:
    """Compara as estimativas com as tabelas oficiais (A1 computador e A4 Internet; Brasil e regiões): maior diferença da proporção, em pontos percentuais,
    e a faixa da razão (margem oficial ÷ margem estimada). `oficial` é o documento `cetic_tic_domicilios` (formato longo)."""
    if not oficial:
        return None
    por = {}
    for l in oficial["linhas"]:
        if l["resposta"] == "Sim" and l["tabela"] in ("A1", "A4") and l["dimensao"] in ("Total", "Região") and l["proporcao"] is not None:
            por[(l["tabela"], "BR" if l["dimensao"] == "Total" else l["recorte"])] = l
    pares = {"A1": "computador", "A4": "internet"}
    difs, razoes = [], []
    for (tab, nome), l in por.items():
        e = (grupos.get(nome) or {}).get("indicadores", {}).get(pares[tab], {})
        if "proporcao" not in e:
            continue
        difs.append(abs(e["proporcao"] - l["proporcao"]))
        if e["margem"] and l.get("margem_proporcao"):
            razoes.append(l["margem_proporcao"] / e["margem"])
    if not difs:
        return None
    return {"comparados": len(difs), "diferenca_max_proporcao_pp": round(max(difs), 3), "razao_margem_oficial_min": round(min(razoes), 3) if razoes else None,
            "razao_margem_oficial_max": round(max(razoes), 3) if razoes else None, "tabelas": ["A1", "A4"], "recortes": "Brasil e grandes regiões"}
