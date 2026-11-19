# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Leitura de dumps de IRR (RPSL) para o Arandurapé: objetos `route`/`route6` e `aut-num` dos ASNs brasileiros, em fluxo.

Um dump é texto RPSL: objetos separados por linha em branco, `atributo: valor`, linhas de continuação começando por espaço, `+` ou tabulação. Os dumps do TC e do RADB têm 1,1 a 1,3 milhão de objetos (RADB, 25 MB comprimidos):
aqui só se guardam os objetos cuja **origem** é um ASN brasileiro, e só o par prefixo/origem (não o mantenedor, o contato nem o texto do objeto). O que o objeto *declara* é política ou intenção de roteamento;
não é autorização de origem nem prova de que o ASN criou o objeto (o RADB aceita objetos de terceiros, o TC não).
"""
from __future__ import annotations

import gzip
import ipaddress
import re
from collections import defaultdict
from typing import IO, Iterator


def objetos(f: IO[str], juntar: bool = False) -> Iterator[dict[str, list[str]]]:
    """Objetos RPSL como `{atributo_minúsculo: [valores]}`. Comentários (`%`, `#`) são ignorados; continuações também, a menos que
    `juntar=True` (política do `aut-num`, que costuma quebrar linha: `import: from AS1\n action pref=10;\n accept ANY`)."""
    atual: dict[str, list[str]] = {}
    ultimo: tuple[str, int] | None = None
    for linha in f:
        if linha.startswith(("%", "#")):
            continue
        if not linha.strip():
            if atual:
                yield atual
                atual = {}
            continue
        if linha[0] in " +\t":
            if juntar and ultimo is not None:
                k, i = ultimo
                atual[k][i] = (atual[k][i] + " " + linha.lstrip(" +\t").strip()).strip()
            continue
        chave, _, valor = linha.partition(":")
        k = chave.strip().lower()
        atual.setdefault(k, []).append(valor.strip())
        ultimo = (k, len(atual[k]) - 1)
    if atual:
        yield atual


def _asn(valor: str) -> int | None:
    v = valor.strip().upper()
    if v.startswith("AS") and v[2:].isdigit():
        return int(v[2:])
    return None


def prefixo(valor: str) -> str | None:
    try:
        return str(ipaddress.ip_network(valor.strip(), strict=False))
    except ValueError:
        return None


_FROM = re.compile(r"\bfrom\s+(AS\d+)\b.*?\baccept\s+(.+)$", re.I)
_TO = re.compile(r"\bto\s+(AS\d+)\b.*?\bannounce\s+(.+)$", re.I)


def classe_filtro(filtro: str, proprio: int, par: int) -> str:
    """Resume o filtro RPSL de uma linha `import`/`export` em uma classe: `any` (tudo), `proprio` (só o AS dono), `par` (só o AS do outro lado),
    `as_set` (conjunto de ASes, em geral os clientes) ou `outro`. Só a classe é guardada, nunca o texto."""
    f = filtro.strip().rstrip(";").strip().upper()
    if f in ("ANY", "AS-ANY", "{ 0.0.0.0/0^0-32 }", "ANY AND NOT { 0.0.0.0/0 }"):
        return "any"
    if f == f"AS{proprio}":
        return "proprio"
    if f == f"AS{par}":
        return "par"
    if re.search(r"(^|:)AS-[A-Z0-9_-]+", f):
        return "as_set"
    return "outro"


def politicas_aut_num(o: dict[str, list[str]], proprio: int) -> list[tuple[str, int, str]]:
    """`[(sentido, asn_do_par, classe)]` das linhas `import`/`export` (e `mp-`) de um `aut-num` com par ASN explícito (`from AS1 ... accept ...`,
    `to AS1 ... announce ...`). Linhas com conjunto no lugar do par, `refine`/`except` e fatores múltiplos ficam de fora: mais vale perder
    uma política do que lê-la errado."""
    out: list[tuple[str, int, str]] = []
    for attr, rx, sentido in (("import", _FROM, "in"), ("mp-import", _FROM, "in"), ("export", _TO, "out"), ("mp-export", _TO, "out")):
        for linha in o.get(attr, []):
            if re.search(r"\b(refine|except)\b", linha, re.I) or len(re.findall(r"\b(?:from|to)\s+AS\d+", linha, re.I)) != 1:
                continue
            m = rx.search(linha)
            if m:
                par = int(m.group(1)[2:])
                out.append((sentido, par, classe_filtro(m.group(2), proprio, par)))
    return sorted(set(out))


def ler_dump(caminho, br: set[int]) -> tuple[dict[int, set[str]], set[int], dict[str, int]]:
    """`(rotas, aut_nums, contagem)` de um dump `.gz`: prefixos por ASN de origem brasileiro, ASNs brasileiros com `aut-num` e a contagem de objetos por classe (todos, não só os brasileiros)."""
    rotas, aut, contagem, _ = ler_dump_completo(caminho, br)
    return rotas, aut, contagem


def ler_dump_completo(caminho, br: set[int]) -> tuple[dict[int, set[str]], set[int], dict[str, int], dict[int, list[tuple[str, int, str]]]]:
    """Como `ler_dump`, mais a política (`politicas_aut_num`) dos `aut-num` brasileiros, na mesma passada."""
    politicas: dict[int, list[tuple[str, int, str]]] = {}
    rotas: dict[int, set[str]] = defaultdict(set)
    aut: set[int] = set()
    contagem: dict[str, int] = defaultdict(int)
    invalidos = 0
    with gzip.open(caminho, "rt", encoding="latin-1") as f:
        for o in objetos(f, juntar=True):
            classe = next(iter(o))
            if classe in ("route", "route6", "aut-num"):
                contagem[classe] += 1
            if classe in ("route", "route6"):
                a = _asn(o.get("origin", [""])[0])
                if a in br:
                    p = prefixo(o[classe][0])
                    if p:
                        rotas[a].add(p)
                    else:
                        invalidos += 1
            elif classe == "aut-num":
                a = _asn(o["aut-num"][0])
                if a in br:
                    aut.add(a)
                    pol = politicas_aut_num(o, a)
                    if pol:
                        politicas[a] = pol
    contagem["invalidos_br"] = invalidos
    contagem["aut_num_br_com_politica"] = len(politicas)
    return rotas, aut, dict(contagem), politicas
