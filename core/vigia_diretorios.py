# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Vigia de diretórios do Registro.br e do LACNIC: detecta o arquivo novo, o padrão de nome novo e a mudança de cabeçalho, para achar no dia em que surgir a bitácora
pública da política LAC-2025-5 (aluguel de IPv4) e qualquer mudança de formato das listas que o Arandurapé lê.

A listagem é o índice HTML do Apache (`<a href="nome">`, data, tamanho). Nome com data (`AAAAMMDD`, `AAAA-MM-DD`) ou número de ASN vira **padrão** (`delegated-lacnic-AAAAMMDD`,
`<asn>v4.csv`): arquivo diário novo não é novidade, padrão novo é.
"""
from __future__ import annotations

import hashlib
import re
from typing import Optional

PADRAO_LINHA = re.compile(r'<a href="([^"?/][^"]*/?)">[^<]*</a></td><td[^>]*>\s*([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9:]+)?\s*</td><td[^>]*>\s*([^<]*?)\s*</td>')


def padrao(nome: str) -> str:
    n = re.sub(r"\d{4}-\d{2}-\d{2}", "AAAA-MM-DD", nome)
    n = re.sub(r"\d{8}T\d{6}Z", "AAAAMMDDTHHMMSSZ", n)
    n = re.sub(r"(?<!\d)\d{8}(?!\d)", "AAAAMMDD", n)
    n = re.sub(r"^\d{4}/$", "AAAA/", n)
    return re.sub(r"^\d+v([46])\.csv$", r"<asn>v\1.csv", n)


def parse_indice(html: str) -> list[dict]:
    itens = []
    for nome, data, tam in PADRAO_LINHA.findall(html):
        if nome.startswith("/"):
            continue
        itens.append({"nome": nome, "padrao": padrao(nome), "data": (data or "").strip() or None, "tamanho": tam.strip() or None})
    return itens


def cabecalho(conteudo: bytes, linhas: int = 6) -> dict:
    """Primeiras linhas de texto de um arquivo (comentários e cabeçalho) e o hash delas: a mudança de formato aparece como mudança do hash. JSON: as chaves do primeiro nível."""
    txt = conteudo[:4096].decode("utf-8", "replace")
    if txt.lstrip().startswith("{"):
        import json
        try:
            chaves = sorted(json.loads(conteudo.decode("utf-8")).keys())
            return {"chaves": chaves, "hash": hashlib.sha256(",".join(chaves).encode()).hexdigest()[:16]}
        except Exception:
            pass
    ls = txt.splitlines()
    topo = [ln for ln in ls if ln.startswith("#") and not ln.startswith("# Generated")][:linhas]            # a data de geração muda todo dia
    topo = [re.sub(r"\d{4}-\d{2}-\d{2}", "AAAA-MM-DD", re.sub(r"\d{8}", "AAAAMMDD", ln)) for ln in topo]
    dados = next((ln for ln in ls if ln and not ln.startswith("#")), "")
    topo.append(f"colunas={dados.count('|') + 1}")                                                        # linha de dados: só o número de colunas, não o conteúdo
    return {"linhas": topo, "hash": hashlib.sha256("\n".join(topo).encode()).hexdigest()[:16]}


def comparar(atual: dict, anterior: Optional[dict]) -> list[dict]:
    """Alertas entre duas varreduras: `padrao_novo`, `arquivo_novo` (nome sem data que não existia), `padrao_removido`, `cabecalho_mudou`. Sem varredura anterior, nada é novidade."""
    if not anterior:
        return []
    out: list[dict] = []
    for url, d in atual["diretorios"].items():
        ant = (anterior.get("diretorios") or {}).get(url)
        if ant is None:
            out.append({"tipo": "diretorio_novo", "url": url})
            continue
        pad_ant, nom_ant = {i["padrao"] for i in ant}, {i["nome"] for i in ant}
        for i in d:
            if i["padrao"] not in pad_ant:
                out.append({"tipo": "padrao_novo", "url": url, "nome": i["nome"], "padrao": i["padrao"], "data": i["data"], "tamanho": i["tamanho"]})
            elif i["padrao"] == i["nome"] and i["nome"] not in nom_ant:
                out.append({"tipo": "arquivo_novo", "url": url, "nome": i["nome"], "data": i["data"], "tamanho": i["tamanho"]})
        for p in pad_ant - {i["padrao"] for i in d}:
            out.append({"tipo": "padrao_removido", "url": url, "padrao": p})
    for url, h in atual["cabecalhos"].items():
        ant = (anterior.get("cabecalhos") or {}).get(url)
        if ant and h.get("hash") != ant.get("hash"):
            out.append({"tipo": "cabecalho_mudou", "url": url, "antes": ant, "depois": h})
    return out
