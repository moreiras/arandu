# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Relação entre ASes lida da política declarada no IRR: segunda referência e evidência candidata.

Convenção de leitura (a mesma de Gao/RPSL na prática): o **cliente** importa tudo do provedor (`import: from P accept ANY`) e só anuncia a
si mesmo ou aos seus clientes (`export: to P announce AS-CLIENTE`); o **provedor** anuncia tudo ao cliente (`export: to C announce ANY`) e
só aceita dele o que é do cliente (`import: from C accept AS-CLIENTE`). Pares (peering) trocam só o que é próprio ou do cone, nos dois sentidos.

Rótulos por par (menor, maior):
  - `p2c_consistente`: os dois lados declaram, no mesmo sentido (provedor, cliente);
  - `p2c_unilateral`: só um dos lados declara (política declarada ≠ praticada, e um lado ausente é o caso comum);
  - `p2p_consistente`: os dois lados declaram, nos dois sentidos, só o que é próprio ou de conjunto;
  - `conflito`: as declarações apontam provedores opostos ou ambos mandam `ANY` um ao outro.
Declaração não é prática: IRR desatualizado é o risco principal e, por isso, só o `*_consistente` serve de referência (e ainda não é verdade).
Não faz parte do ARC publicado: é régua (validacao) e candidata a evidência, ligada só por `refino.irr`."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from core.common import read_json_gz

PROPRIOS = {"proprio", "as_set", "par"}


def com_politicas(base: Path) -> Optional[dict]:
    """O `irr_route_objects` mais recente que tenha `politicas`, de qualquer data: a política declarada muda devagar e o bruto de uma data
    fechada não é refeito (raw é imutável). A data usada (`snapshot_date`) vai no relatório."""
    raiz = base / "normalized"
    for d in sorted((x for x in raiz.iterdir() if x.is_dir()), reverse=True) if raiz.exists() else []:
        p = d / "summary" / "irr_route_objects.json.gz"
        if p.exists():
            doc = read_json_gz(p)
            if doc.get("politicas"):
                return doc
    return None


def valor(rel: dict[tuple[int, int], dict], a: int, b: int) -> str:
    """Característica do NB para `a` como candidato a provedor de `b`: `ab`/`ab+` (o IRR aponta a provedor; `+` quando os dois lados declaram),
    `ba`/`ba+` (aponta b), `pp` (par consistente), `conf` (declarações em conflito) ou `0` (sem declaração legível)."""
    r = rel.get((min(a, b), max(a, b)))
    if r is None:
        return "0"
    if r["rotulo"] == "conflito":
        return "conf"
    if r["rotulo"] == "p2p_consistente":
        return "pp"
    forte = "+" if r["rotulo"] == "p2c_consistente" else ""
    return ("ab" if r["provedor"] == a else "ba") + forte


def _declaracoes(politicas: dict[str, dict[str, list]]) -> dict[int, dict[tuple[str, int], set[str]]]:
    """`{asn: {(sentido, par): {classes}}}`, juntando os IRRs (TC e RADB)."""
    out: dict[int, dict[tuple[str, int], set[str]]] = {}
    for _irr, por_asn in politicas.items():
        for asn, linhas in por_asn.items():
            d = out.setdefault(int(asn), {})
            for sentido, par, classe in linhas:
                d.setdefault((sentido, int(par)), set()).add(classe)
    return out


def _lado(d: dict, quem: int, outro: int) -> str | None:
    """Papel de `quem` visto pelo que ele mesmo declara sobre `outro`: `cliente`, `provedor`, `par` ou None."""
    ent, sai = d.get(quem, {}).get(("in", outro), set()), d.get(quem, {}).get(("out", outro), set())
    if "any" in ent and "any" in sai:
        return "conflito"
    if "any" in ent:
        return "cliente"                       # quem importa tudo de `outro` é cliente dele
    if "any" in sai:
        return "provedor"                      # quem manda tudo a `outro` é provedor dele
    if ent and sai and ent <= PROPRIOS and sai <= PROPRIOS:
        return "par"
    return None


def relacoes(politicas: dict[str, dict[str, list]]) -> dict[tuple[int, int], dict]:
    """`{(menor, maior): {"rotulo", "provedor", "cliente"}}` dos pares com ao menos uma declaração legível."""
    d = _declaracoes(politicas)
    pares = {(min(a, p), max(a, p)) for a, v in d.items() for (_s, p) in v}
    out: dict[tuple[int, int], dict] = {}
    for a, b in sorted(pares):
        la, lb = _lado(d, a, b), _lado(d, b, a)          # papel de a (sobre b) e papel de b (sobre a)
        if la == "conflito" or lb == "conflito":
            out[(a, b)] = {"rotulo": "conflito"}
            continue
        prov_cli: list[tuple[int, int]] = []              # (provedor, cliente) que cada lado afirma
        if la == "cliente":
            prov_cli.append((b, a))
        if la == "provedor":
            prov_cli.append((a, b))
        if lb == "cliente":
            prov_cli.append((a, b))
        if lb == "provedor":
            prov_cli.append((b, a))
        if len(set(prov_cli)) > 1:
            out[(a, b)] = {"rotulo": "conflito"}
        elif prov_cli:
            p, c = prov_cli[0]
            out[(a, b)] = {"rotulo": "p2c_consistente" if len(prov_cli) == 2 else "p2c_unilateral", "provedor": p, "cliente": c}
        elif la == "par" and lb == "par":
            out[(a, b)] = {"rotulo": "p2p_consistente"}
    return out


def avaliar(vereditos: Iterable, rel: dict[tuple[int, int], dict]) -> dict:
    """Concordância dos vereditos do ARC com a política do IRR, por rótulo da referência (não é acurácia: a referência declara, não pratica).
    Conta só os elos que existem nos dois lados. `inverso` = o ARC aponta o provedor oposto ao do IRR."""
    res: dict[str, dict[str, int]] = {}
    for v in vereditos:
        k = (min(v.a, v.b), max(v.a, v.b))
        r = rel.get(k)
        if r is None or r["rotulo"] == "conflito":
            continue
        c = res.setdefault(r["rotulo"], {"concorda": 0, "inverso": 0, "tipo_diferente": 0})
        if r["rotulo"].startswith("p2c"):
            c["concorda" if (v.tipo == "p2c" and (v.a, v.b) == (r["provedor"], r["cliente"])) else
              "inverso" if (v.tipo == "p2c") else "tipo_diferente"] += 1
        else:
            c["concorda" if v.tipo == "p2p" else "tipo_diferente"] += 1
    for c in res.values():
        c["total"] = c["concorda"] + c["inverso"] + c["tipo_diferente"]
        c["concordancia"] = round(c["concorda"] / c["total"], 4) if c["total"] else None
    return {"rotulos": res, "pares_na_referencia": len(rel), "conflitos": sum(1 for r in rel.values() if r["rotulo"] == "conflito")}
