# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Reclamações da Anatel, a partir de `reclamacoes_contexto.csv` (2020-09 em diante) e `reclamacoes.csv` (2015 a 2020, o legado).

Cada linha do arquivo já é um **agregado** da própria Anatel (mês × município × canal × serviço × marca × assunto × problema, com a coluna de solicitações); não há texto livre nem dado de quem
reclamou. Mesmo assim só saem totais por marca, serviço, município, UF, assunto e período. Os dois arquivos se sobrepõem no tempo; vale o `contexto` a partir do primeiro mês dele e o
legado só antes disso. As taxonomias de assunto e problema mudaram entre os dois, então assuntos são publicados só a partir do `contexto`.

O que a fonte chama de "marca" é um nome de empresa escolhido pelo consumidor; "NÃO LOCALIZEI A MINHA EMPRESA" e "Outros" não identificam ninguém. A ligação marca → CNPJ está em
`core/marcas.py` e na tabela curada `config/curada_marcas_operadoras.yaml`.
"""
from __future__ import annotations

import csv
import io
from collections import Counter, defaultdict
from typing import IO, Iterable

COLUNAS = ("DataExtracao", "SOLICITAÇÕES", "Ano", "Mês", "AnoMês", "UF", "Cidade", "CO_MUNICIPIO", "TipoAtendimento", "Serviço", "Marca", "Assunto")
SEM_MARCA = ("NÃO LOCALIZEI A MINHA EMPRESA", "OUTROS", "OUTRAS", "")
TIPO_RECLAMACAO = "Reclamação"


def _linhas(arq: IO[bytes]) -> Iterable[dict]:
    leitor = csv.reader(io.TextIOWrapper(arq, encoding="utf-8-sig", newline=""), delimiter=";")
    cab = next(leitor)
    faltam = [c for c in COLUNAS if c not in cab]
    if faltam:
        raise RuntimeError(f"anatel_reclamacoes: colunas ausentes {faltam}; o leiaute mudou")
    ix = {c: cab.index(c) for c in COLUNAS}
    n = len(cab)
    for r in leitor:
        if len(r) < n:
            continue
        try:
            qtd = int(r[ix["SOLICITAÇÕES"]] or 0)
        except ValueError:
            continue
        yield {"extracao": r[ix["DataExtracao"]].strip(), "qtd": qtd, "ano": int(r[ix["Ano"]]), "ym": r[ix["AnoMês"]].strip(), "uf": r[ix["UF"]].strip(), "cidade": r[ix["Cidade"]].strip(), "ibge": r[ix["CO_MUNICIPIO"]].strip(),
               "tipo": r[ix["TipoAtendimento"]].strip(), "servico": r[ix["Serviço"]].strip(), "marca": r[ix["Marca"]].strip().upper(), "assunto": r[ix["Assunto"]].strip()}


class Acumulador:
    """Soma em fluxo, sem guardar linhas. `leitura` conta o que entrou de cada arquivo."""

    def __init__(self) -> None:
        self.mes: Counter = Counter()            # (ym, servico, tipo)
        self.marca: Counter = Counter()          # (marca, servico, ano) — só reclamações
        self.marca_mun: dict = defaultdict(set)  # (marca, servico, ano) → municípios
        self.marca_ym: Counter = Counter()       # (marca, servico, ym) — só reclamações
        self.uf: Counter = Counter()             # (uf, servico, ano)
        self.marca_uf: Counter = Counter()       # (marca, uf, ano) — só reclamações
        self.mun: Counter = Counter()            # (ibge, servico, marca, ano)
        self.mun_nome: dict = {}
        self.assunto: Counter = Counter()        # (ano, servico, assunto) — só do contexto
        self.marca_assunto: Counter = Counter()  # (marca, servico, ano, assunto) — só do contexto
        self.leitura: dict = {}

    def ler(self, arq: IO[bytes], nome: str, ym_min: str | None = None, ym_max_exclusivo: str | None = None, assuntos: bool = False) -> dict:
        linhas = usadas = soma = 0
        meses: set[str] = set()
        extracao = ""
        for r in _linhas(arq):
            linhas += 1
            if ym_max_exclusivo and r["ym"] >= ym_max_exclusivo:
                continue
            if ym_min and r["ym"] < ym_min:
                continue
            usadas += 1
            extracao = max(extracao, r["extracao"])
            soma += r["qtd"]
            meses.add(r["ym"])
            q, s = r["qtd"], r["servico"]
            self.mes[(r["ym"], s, r["tipo"])] += q
            if r["tipo"] != TIPO_RECLAMACAO:
                continue
            ano, marca = r["ano"], r["marca"]
            self.marca[(marca, s, ano)] += q
            self.marca_ym[(marca, s, r["ym"])] += q
            self.uf[(r["uf"], s, ano)] += q
            self.marca_uf[(marca, r["uf"], ano)] += q
            if r["ibge"]:
                self.marca_mun[(marca, s, ano)].add(r["ibge"])
                self.mun[(r["ibge"], s, marca, ano)] += q
                self.mun_nome.setdefault(r["ibge"], (r["cidade"], r["uf"]))
            if assuntos:
                self.assunto[(ano, s, r["assunto"])] += q
                self.marca_assunto[(marca, s, ano, r["assunto"])] += q
        self.leitura[nome] = {"linhas": linhas, "linhas_usadas": usadas, "solicitacoes": soma, "mes_inicial": min(meses, default=None), "mes_final": max(meses, default=None), "data_extracao": extracao or None}
        return self.leitura[nome]


def consolidar_zip(abrir, anos_municipio: int = 3) -> dict:
    """`abrir(nome)` devolve o arquivo binário de dentro do zip. Lê o contexto, acha o primeiro mês dele e só então o legado (antes desse mês)."""
    ac = Acumulador()
    with abrir("reclamacoes_contexto.csv") as f:
        ctx = ac.ler(f, "reclamacoes_contexto.csv", assuntos=True)
    corte = ctx["mes_inicial"]
    with abrir("reclamacoes.csv") as f:
        ac.ler(f, "reclamacoes.csv", ym_max_exclusivo=corte)
    return montar(ac, corte, anos_municipio)


def montar(ac: Acumulador, corte: str | None, anos_municipio: int = 3) -> dict:
    anos = sorted({a for (_, _, a) in ac.marca})
    ano_min_mun = (anos[-1] - anos_municipio + 1) if anos else 0
    municipios: dict[str, dict] = {}
    for (ibge, s, marca, ano), q in sorted(ac.mun.items()):
        if ano < ano_min_mun:
            continue
        m = municipios.setdefault(ibge, {"nome": ac.mun_nome[ibge][0], "uf": ac.mun_nome[ibge][1], "itens": []})
        m["itens"].append({"ano": ano, "servico": s, "marca": marca, "reclamacoes": q})
    marcas = [{"marca": m, "servico": s, "ano": a, "reclamacoes": q, "municipios": len(ac.marca_mun[(m, s, a)])} for (m, s, a), q in sorted(ac.marca.items())]
    return {
        "resumo": {"arquivos": ac.leitura, "corte_contexto": corte, "anos": anos, "marcas": len({m for (m, _, _) in ac.marca}), "municipios": len(ac.mun_nome),
                   "reclamacoes": sum(ac.marca.values()), "sem_marca": sum(q for (m, _, _), q in ac.marca.items() if m in SEM_MARCA), "anos_municipio": anos_municipio},
        "por_mes": [{"mes": ym, "servico": s, "tipo": t, "total": q} for (ym, s, t), q in sorted(ac.mes.items())],
        "marcas": marcas,
        "marca_mensal": [{"marca": m, "servico": s, "mes": ym, "reclamacoes": q} for (m, s, ym), q in sorted(ac.marca_ym.items()) if ym >= f"{ano_min_mun}-01"],
        "marca_uf": [{"marca": m, "uf": u, "ano": a, "reclamacoes": q} for (m, u, a), q in sorted(ac.marca_uf.items()) if a >= ano_min_mun],
        "uf": [{"uf": u, "servico": s, "ano": a, "reclamacoes": q} for (u, s, a), q in sorted(ac.uf.items())],
        "assuntos": [{"ano": a, "servico": s, "assunto": x, "reclamacoes": q} for (a, s, x), q in sorted(ac.assunto.items())],
        "marca_assuntos": [{"marca": m, "servico": s, "ano": a, "assunto": x, "reclamacoes": q} for (m, s, a, x), q in sorted(ac.marca_assunto.items()) if a >= ano_min_mun],
        "municipios": municipios,
    }
