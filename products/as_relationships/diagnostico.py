# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Diagnóstico de estabilidade: mede sem mudar o algoritmo e sem escrever em `published/`.

    python -m products.as_relationships.diagnostico --de 2026-11-05 --ate 2026-11-06

Estabilidade entre duas datas com **coletas de BGP diferentes**, separando duas causas que a comparação dos snapshots publicados mistura (entre duas datas
podem mudar tanto a versão do algoritmo quanto a coleta):
  - `coleta`: a mesma versão do algoritmo nas duas datas (v1 contra v1, v2 contra v2): o que a coleta nova muda;
  - `algoritmo`: v1 contra v2 na mesma data: o que o refino muda.
A medida é a fração dos provedores (p2c de nível ≥ provável) em comum (Jaccard), mais o que saiu e o que entrou. Referência da literatura: 2,6 a 5,6% dos
elos mudam sem causa entre coletas no AS Rank (Jin et al., 2019). Saída: `data/ops/relacoes/diagnostico-AAAA-MM-DD.json`."""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path
from typing import Optional

from core.common import configure_logging, data_dir, today_str
from products.as_relationships import build, refino, regua, validacao
from products.as_relationships.config import Config, carregar


def analisar(base: Path, date_str: str, cfg: Config, afi: str, so_coletores: Optional[set] = None) -> tuple[set[tuple[int, int]], dict[tuple[int, int], str]]:
    """`(provedores, classes)` da execução sem ASPA (holdout) com a versão do algoritmo de `cfg`: os p2c de nível ≥ provável e a classe de cada elo
    de nível ≥ provável (`p2c:<provedor>` ou `p2p`), chaveada por (menor, maior). Uma execução do ARC serve às duas medidas."""
    e = validacao._entradas(base, date_str)
    ctx: dict = {}
    vs, _ = validacao._rodar(base, date_str, e, dataclasses.replace(cfg, versao=1), afi, contexto=ctx, so_coletores=so_coletores)
    if cfg.versao >= 2:
        perfil, restr = build._politica(base, date_str)
        vs, _ = refino.refinar(vs, ctx, cfg, afi, perfil, restr, usar_aspa=False)
    return regua.provedores_inferidos(vs, "provavel"), classes_dos_vereditos(vs)


def classes_dos_vereditos(vs: list) -> dict[tuple[int, int], str]:
    aceitos = set(regua.NIVEIS[:regua.NIVEIS.index("provavel") + 1])
    out = {}
    for v in vs:
        if v.nivel in aceitos and v.tipo in ("p2c", "p2p"):
            out[(min(v.a, v.b), max(v.a, v.b))] = f"p2c:{v.a}" if v.tipo == "p2c" else "p2p"
    return out


def provedores(base: Path, date_str: str, cfg: Config, afi: str) -> set[tuple[int, int]]:
    return analisar(base, date_str, cfg, afi)[0]


def comparar_classes(a: dict, b: dict) -> dict:
    """Entre duas datas: elos que entraram ou saíram do conjunto classificado (≥ provável) × elos presentes nas duas que **mudaram de classe**
    (o que Jin et al. 2019 chamam de instabilidade). `mudou_pct` é sobre os elos em comum."""
    comuns = a.keys() & b.keys()
    mudou = sum(1 for k in comuns if a[k] != b[k])
    inverteu = sum(1 for k in comuns if a[k] != b[k] and a[k].startswith("p2c") and b[k].startswith("p2c"))
    return {"a": len(a), "b": len(b), "em_comum": len(comuns), "mudaram_de_classe": mudou, "mudou_pct": round(100 * mudou / len(comuns), 2) if comuns else None,
            "p2c_que_inverteu": inverteu, "so_em_a": len(a.keys() - b.keys()), "so_em_b": len(b.keys() - a.keys())}


def comparar(a: set, b: set) -> dict:
    """Jaccard e o que saiu/entrou, em contagem e em fração do conjunto de partida."""
    ambos = a & b
    uniao = a | b
    return {"a": len(a), "b": len(b), "iguais": len(ambos), "so_em_a": len(a - b), "so_em_b": len(b - a),
            "saiu_pct": round(100 * len(a - b) / len(a), 2) if a else None, "entrou_pct": round(100 * len(b - a) / len(a), 2) if a else None,
            "jaccard": round(len(ambos) / len(uniao), 4) if uniao else None}


def coletores_em_comum(base: Path, de: str, ate: str, afi: str) -> set:
    """Coletores presentes nas duas datas: a comparação só é justa se os dois lados veem pelos mesmos pontos de vista."""
    return set(build._colecao(base, de, afi)[1]) & set(build._colecao(base, ate, afi)[1])


def estabilidade_entre_coletas(base: Path, de: str, ate: str, log=None, cfg: Optional[Config] = None, afis: tuple[str, ...] = tuple(build.AFIS),
                               versoes: tuple[int, ...] = (1, 2), so_comuns: bool = False) -> dict:
    cfg = cfg or carregar()
    out: dict = {"de": de, "ate": ate, "versoes": list(versoes),
                 "nota": "execuções sem o ASPA como entrada; mesma versão do algoritmo nas duas datas isola o efeito da coleta, a mesma data com versões diferentes isola o do algoritmo"}
    for afi in afis:
        comuns = coletores_em_comum(base, de, ate, afi) if so_comuns else None
        if so_comuns:
            out.setdefault("coletores_em_comum", {})[afi] = sorted(comuns)
        conj: dict[tuple[int, str], set] = {}
        cls: dict[tuple[int, str], dict] = {}
        for v in versoes:
            for d in (de, ate):
                conj[(v, d)], cls[(v, d)] = analisar(base, d, dataclasses.replace(cfg, versao=v), afi, comuns)
                if log:
                    log.info("diagnostico: provedores", afi=afi, versao=v, data=d, n=len(conj[(v, d)]))
        r: dict = {"coleta": {f"v{v}": comparar(conj[(v, de)], conj[(v, ate)]) for v in versoes}}
        r["classe"] = {f"v{v}": comparar_classes(cls[(v, de)], cls[(v, ate)]) for v in versoes}
        if len(versoes) > 1:
            v0, v1 = versoes[0], versoes[-1]
            r["algoritmo"] = {de: comparar(conj[(v0, de)], conj[(v1, de)]), ate: comparar(conj[(v0, ate)], conj[(v1, ate)])}
        out[afi] = r
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Diagnóstico: estabilidade entre coletas, separada do efeito do algoritmo")
    p.add_argument("--de", required=True, help="data anterior (AAAA-MM-DD)")
    p.add_argument("--ate", required=True, help="data posterior, com coleta de BGP diferente")
    p.add_argument("--so-comuns", action="store_true", help="só os coletores presentes nas duas datas (isola a mudança do conjunto de coletores)")
    p.add_argument("--versoes", nargs="+", type=int, default=[1, 2])
    a = p.parse_args(argv)
    base, log = data_dir(), configure_logging()
    rel = estabilidade_entre_coletas(base, a.de, a.ate, log, versoes=tuple(a.versoes), so_comuns=a.so_comuns)
    destino = base / "ops" / "relacoes" / f"diagnostico-{a.ate}{'-comuns' if a.so_comuns else ''}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info("diagnostico written", path=str(destino))
    return 0


if __name__ == "__main__":
    sys.exit(main())
