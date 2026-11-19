#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Confere um snapshot publicado contra os critérios dos estratos de evidência: só lê `published/`, nunca consulta a rede nem grava.

    python3 scripts/conferir_estratos_snapshot.py --date 2026-11-13 [--anterior 2026-11-06] [--data-dir data]

Verifica no `as_relationships.json.gz` da data:
  1. o bloco `estratos` e os campos `estrato`/`p_calibrada` existem;
  2. o rebaixo: nenhum p2c `provavel` com estrato `conflito` ou `sem_evidencia` sobra (`declarado`, do ASPA, e `confirmado`, do route server, não mudam;
     a contagem deles sai em `mantidos_por_nivel`);
  3. cobertura: fração dos p2c de nível ≥ provável com `p_calibrada`, por família, contra o piso de 70% (item 1);
  4. com `--anterior`: estabilidade entre os dois snapshots (Jaccard dos provedores, mudança de classe, entradas e saídas) contra os limites
     (mudança de classe ≤ 2%, Jaccard ≥ 0,95, entradas e saídas ≤ 3% por sentido) e se o conjunto de coletores é o mesmo (regra do conjunto fixo).
Não mede precisão e recall do rebaixo contra o ASPA: isso é a régua (`python -m products.as_relationships.estratos`), que precisa dos brutos e roda no ambiente de teste.
Saída: texto no terminal e, com `--saida`, o JSON. Código 0 se tudo cumprido, 1 se algum critério falhou, 2 se o snapshot não tem esses campos."""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path
from typing import Optional

ACEITOS = ("declarado", "confirmado", "provavel")                  # nível ≥ provável
REBAIXADOS = ("conflito", "sem_evidencia")
PISO_COBERTURA = 0.70
LIM_MUDOU_PCT, LIM_JACCARD, LIM_ENTRADA_SAIDA_PCT = 2.0, 0.95, 3.0


def ler(p: Path) -> dict:
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return json.load(f)


def _p2c_aceitos(doc: dict, afi: Optional[str] = None) -> list[dict]:
    return [l for l in doc.get("relacoes", []) if l.get("tipo") == "p2c" and l.get("nivel") in ACEITOS and (afi is None or afi in l.get("afi", []))]


def rebaixo(doc: dict) -> dict:
    """p2c de nível ≥ provável por estrato; em `conflito`/`sem_evidencia` não pode sobrar `provavel` (`declarado` e `confirmado` não mudam)."""
    por_estrato: dict[str, int] = {}
    mantidos: dict[str, int] = {}
    indevidos = 0
    for l in _p2c_aceitos(doc):
        e = l.get("estrato") or "(sem estrato)"
        por_estrato[e] = por_estrato.get(e, 0) + 1
        if e in REBAIXADOS:
            mantidos[l["nivel"]] = mantidos.get(l["nivel"], 0) + 1
            if l["nivel"] == "provavel":
                indevidos += 1
    return {"por_estrato": dict(sorted(por_estrato.items())), "mantidos_por_nivel": dict(sorted(mantidos.items())), "indevidos": indevidos, "ok": indevidos == 0}


def cobertura(doc: dict) -> dict:
    """Fração dos p2c ≥ provável (por família) com `p_calibrada` não nula."""
    out = {}
    for afi in ("v4", "v6"):
        ls = _p2c_aceitos(doc, afi)
        com = sum(1 for l in ls if l.get("p_calibrada") is not None)
        frac = com / len(ls) if ls else None
        out[afi] = {"p2c_aceitos": len(ls), "com_p_calibrada": com, "fracao": round(frac, 4) if frac is not None else None, "ok": frac is not None and frac >= PISO_COBERTURA}
    return out


def _provedores(doc: dict) -> set[tuple[int, int]]:
    return {(l["a"], l["b"]) for l in _p2c_aceitos(doc)}


def _classes(doc: dict) -> dict[tuple[int, int], str]:
    out = {}
    for l in doc.get("relacoes", []):
        if l.get("nivel") in ACEITOS and l.get("tipo") in ("p2c", "p2p"):
            out[(min(l["a"], l["b"]), max(l["a"], l["b"]))] = f"p2c:{l['a']}" if l["tipo"] == "p2c" else "p2p"
    return out


def estabilidade(atual: dict, anterior: dict) -> dict:
    a, b = _provedores(anterior), _provedores(atual)
    uniao = a | b
    jaccard = len(a & b) / len(uniao) if uniao else None
    saiu = 100 * len(a - b) / len(a) if a else None
    entrou = 100 * len(b - a) / len(a) if a else None
    ca, cb = _classes(anterior), _classes(atual)
    comuns = ca.keys() & cb.keys()
    mudou = 100 * sum(1 for k in comuns if ca[k] != cb[k]) / len(comuns) if comuns else None
    colet = lambda d: {afi: sorted(set(x)) for afi, x in (d.get("entradas", {}).get("coletores") or {}).items()}   # noqa: E731
    mesmos = colet(anterior) == colet(atual)
    ok = (mesmos and jaccard is not None and jaccard >= LIM_JACCARD and mudou is not None and mudou <= LIM_MUDOU_PCT
          and saiu is not None and saiu <= LIM_ENTRADA_SAIDA_PCT and entrou is not None and entrou <= LIM_ENTRADA_SAIDA_PCT)
    r = lambda x: None if x is None else round(x, 4)   # noqa: E731
    return {"provedores_anterior": len(a), "provedores_atual": len(b), "jaccard": r(jaccard), "saiu_pct": r(saiu), "entrou_pct": r(entrou), "mudou_de_classe_pct": r(mudou),
            "elos_em_comum": len(comuns), "mesmos_coletores": mesmos,
            "limites": {"jaccard_min": LIM_JACCARD, "mudou_pct_max": LIM_MUDOU_PCT, "entrada_saida_pct_max": LIM_ENTRADA_SAIDA_PCT},
            "ok": ok, "nota": None if mesmos else "conjunto de coletores diferente: a comparação não vale pela regra do conjunto fixo (use `diagnostico --so-comuns`)"}


def conferir(atual: dict, anterior: Optional[dict] = None) -> dict:
    tem = bool(atual.get("estratos")) and any("estrato" in l for l in atual.get("relacoes", []))
    out: dict = {"snapshot": atual.get("snapshot_date"), "algoritmo": atual.get("algoritmo"), "tem_campos_v1_5_63": tem}
    if not tem:
        out["ok"] = False
        return out
    out["estratos"] = {"ativo": atual["estratos"].get("ativo"), "medido_em": atual["estratos"].get("medido_em"), "rebaixados": atual["estratos"].get("rebaixados"),
                       "elos_por_estrato": atual["estratos"].get("elos_por_estrato")}
    out["rebaixo"] = rebaixo(atual)
    out["cobertura"] = cobertura(atual)
    partes = [out["rebaixo"]["ok"], *(c["ok"] for c in out["cobertura"].values())]
    if anterior is not None:
        out["estabilidade"] = estabilidade(atual, anterior)
        out["estabilidade"]["anterior"] = anterior.get("snapshot_date")
        partes.append(out["estabilidade"]["ok"])
    out["ok"] = all(partes)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--date", required=True)
    p.add_argument("--anterior", help="data de um snapshot anterior para a estabilidade")
    p.add_argument("--data-dir", default="data")
    p.add_argument("--saida", help="grava o JSON neste caminho")
    a = p.parse_args(argv)
    base = Path(a.data_dir)
    atual = ler(base / "published" / a.date / "as_relationships.json.gz")
    ant = ler(base / "published" / a.anterior / "as_relationships.json.gz") if a.anterior else None
    r = conferir(atual, ant)
    txt = json.dumps(r, ensure_ascii=False, indent=1)
    print(txt)
    if a.saida:
        Path(a.saida).write_text(txt, encoding="utf-8")
    if not r["tem_campos_v1_5_63"]:
        return 2
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
