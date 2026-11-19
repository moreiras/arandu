# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Máscara do CPF embutido em nomes empresariais (CPF de pessoa física sai mascarado).

A Receita e a Anatel publicam a razão social de empresário individual e de MEI como "NOME DA PESSOA 12345678901": o CPF inteiro, com dígito
verificador válido. Aqui ele vira `***456789**`, o mesmo formato que a Receita usa para o CPF de sócio pessoa física.

Só mexe em sequências de exatamente 11 dígitos (não encostadas em outro dígito, então CNPJ e telefone com DDD+9 de outra largura não casam) que
passam na conta dos dígitos verificadores, e só nos campos de nome (`e_campo_de_nome`). O resto do documento não é tocado: o número Fistel
e outros identificadores também têm 11 dígitos e servem de chave de junção.

O campo de nome é reconhecido pelo **padrão** da chave, não por uma lista fechada: uma lista fechada deixa passar campos como `sici_empresa`. Chaves de identificador (`cnpj`, `cpf`, `fistel`, `_id`, `codigo`…) ficam de fora mesmo que contenham
um termo de nome; listas de texto sob uma chave de nome (`nomes`, `marcas`) também são mascaradas.
"""
from __future__ import annotations

import re
from typing import Any

CAMPOS_DE_NOME = frozenset({"razao_social", "nome_fantasia", "nome", "name", "empresa", "nome_empresarial", "prestadora", "titular", "operadora",
                            "razao", "nome_empresa", "marca"})        # casos conhecidos; o critério é `e_campo_de_nome`
_TERMO_DE_NOME = re.compile(r"razao|nome|name|empresa|titular|prestadora|operadora|owner|holder|organizacao|organization|fantasia|marca|"
                            r"responsavel|socio|^org$|^org_")
_TERMO_DE_IDENTIFICADOR = re.compile(r"cnpj|cpf|fistel|identificador|(^|_)ids?($|_)|codigo|^cod_|^n_|^num|^qtd|^total|^data|^dt_|cep|ibge|telefone|fone|email")
_CACHE_CHAVES: dict[str, bool] = {}


_LETRA = re.compile(r"[A-Za-zÀ-ÿ]")


def e_campo_de_nome(chave: str) -> bool:
    """Chave cujo valor é nome de pessoa ou de empresa (onde a Receita e a Anatel embutem o CPF de EI/MEI)."""
    r = _CACHE_CHAVES.get(chave)
    if r is None:
        k = chave.lower()
        r = k in CAMPOS_DE_NOME or (_TERMO_DE_NOME.search(k) is not None and _TERMO_DE_IDENTIFICADOR.search(k) is None)
        if len(_CACHE_CHAVES) < 10_000:
            _CACHE_CHAVES[chave] = r
    return r


def _e_nome(chave, valor: str) -> bool:
    """Campo de nome, ou mapa por número (`asns/names.json`: {"266187": "NOME 12345678909"}) com texto que tem letra (prefixo e IP não têm)."""
    if not isinstance(chave, str):
        return False
    if chave.isdigit():
        return _LETRA.search(valor) is not None
    return e_campo_de_nome(chave)
_ONZE = re.compile(r"(?<![0-9])([0-9]{3})[.\s]?([0-9]{3})[.\s]?([0-9]{3})[-\s]?([0-9]{2})(?![0-9])")


_ONZE_BYTES = re.compile(rb"(?<![0-9])[0-9]{3}[.\s]?[0-9]{3}[.\s]?[0-9]{3}[-\s]?[0-9]{2}(?![0-9])")


def pode_ter_cpf(dados: bytes) -> bool:
    """Pré-filtro barato sobre o JSON bruto: sem nenhuma sequência com cara de CPF, o documento nem é percorrido."""
    return _ONZE_BYTES.search(dados) is not None


def cpf_valido(d: str) -> bool:
    """11 dígitos com os dois verificadores corretos (sequências repetidas como 11111111111 não contam)."""
    if len(d) != 11 or not d.isdigit() or d == d[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        if (soma * 10 % 11) % 10 != int(d[n]):
            return False
    return True


def mascarar_cpf(texto: Any) -> Any:
    """`texto` com cada CPF válido trocado por `***XXXXXX**` (os 6 dígitos do meio, como a Receita faz com sócio PF). Não-texto passa como está."""
    if not isinstance(texto, str) or len(texto) < 11:
        return texto

    def troca(m: re.Match) -> str:
        d = "".join(m.groups())
        return f"***{d[3:9]}**" if cpf_valido(d) else m.group(0)

    return _ONZE.sub(troca, texto)


def mascarar_cpf_em(doc: Any) -> Any:
    """Aplica `mascarar_cpf` aos campos de nome em qualquer profundidade, **no próprio objeto** (dicionários e listas); devolve o mesmo objeto.

    No lugar, e não cópia, porque roda uma vez na leitura do artefato (antes do cache), em documentos de dezenas de MB."""
    pilha = [doc]
    while pilha:
        x = pilha.pop()
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, str):
                    if _e_nome(k, v):
                        novo = mascarar_cpf(v)
                        if novo != v:
                            x[k] = novo
                elif isinstance(v, list) and v and isinstance(k, str) and e_campo_de_nome(k):
                    for i, e in enumerate(v):
                        if isinstance(e, str):
                            novo = mascarar_cpf(e)
                            if novo != e:
                                v[i] = novo
                        elif isinstance(e, (dict, list)):
                            pilha.append(e)
                elif isinstance(v, (dict, list)):
                    pilha.append(v)
        elif isinstance(x, list):
            for v in x:
                if isinstance(v, (dict, list)):
                    pilha.append(v)
    return doc


def sem_socios_pessoa_fisica(doc: Any) -> Any:
    """Tira dos grupos societários (`grupos_societarios.json`) o nome e o documento de todo sócio que não é pessoa jurídica, e deixa em
    `nomes_em_comum` só nomes de sócios pessoa jurídica; **no próprio objeto**, como `mascarar_cpf_em`.

    Dado de pessoa física não vai para rota pública nem para o MCP (AGENTS.md). Fica o que não identifica a
    pessoa: o tipo e a qualificação de cada sócio (a contagem do quadro continua certa) e `socios_em_comum`. Sócio estrangeiro também sai
    sem nome: a Receita não diz se é pessoa física ou jurídica. Roda no pipeline (snapshots novos) e na leitura (os já publicados)."""
    by_cnpj = (doc or {}).get("by_cnpj") if isinstance(doc, dict) else None
    if not isinstance(by_cnpj, dict):
        return doc
    pj = {s.get("nome") for r in by_cnpj.values() for s in r.get("socios") or [] if s.get("tipo") == "juridica" and s.get("nome")}
    for r in by_cnpj.values():
        if r.get("socios"):
            r["socios"] = [s if s.get("tipo") == "juridica" else {k: v for k, v in s.items() if k not in ("nome", "documento")}
                           for s in r["socios"]]
        for rel in r.get("relacionadas_parcial") or []:
            if "nomes_em_comum" in rel:
                rel["nomes_em_comum"] = [n for n in rel["nomes_em_comum"] or [] if n in pj]
    return doc
