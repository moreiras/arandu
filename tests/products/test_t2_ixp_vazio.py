# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
"""T2 — IXP cujos route servers não têm nenhum prefixo (caso real: IX.br Macapá, 2026-10-11).

O LG responde só "No BGP prefixes displayed, 0 exist". O pipeline tem de publicar o IXP com 0 rotas,
sem quebrar os demais produtos, e o summary não pode contá-lo duas vezes.
"""
import json
import shutil

from tests.products.conftest import run_pipeline
from tests.synth.world import PTTS, T1

EMPTY = "No BGP prefixes displayed, 0 exist\n"


def test_ixp_com_tabela_vazia_e_publicado_com_zero_rotas(dataset, tmp_path, monkeypatch):
    base = tmp_path / "data"
    shutil.copytree(dataset, base)
    code = PTTS[-1][0]
    for afi in ("v4", "v6"):
        (base / "raw" / T1 / code / f"bgp-{afi}-{code}-{T1}.txt").write_text(EMPTY, encoding="utf-8")

    run_pipeline(base, T1, monkeypatch)

    pub = base / "published" / T1
    doc = json.loads((pub / "ixps" / f"{code}.json").read_text(encoding="utf-8"))
    assert doc["ixp"] == code
    summary = json.loads((pub / "summary.json").read_text(encoding="utf-8"))
    # Tabela vazia é coleta feita com zero rotas: nem "ok" (era "ok" com 0% de cobertura, IXP-E1) nem "missing" (IXP-E2).
    entrada = next(e for e in json.loads((pub / "ixps" / "index.json").read_text(encoding="utf-8")) if e["code"] == code)
    assert entrada["status"] == "partial"
    assert entrada["v6"]["coleta"] == entrada["v4"]["coleta"] == "vazia" and entrada["v6"]["total_routes"] == 0
    assert entrada["v6"]["br_prefix_coverage_pct"] is None
    assert summary["ixps_ok"] == len(PTTS) - 1 and summary["ixps_partial"] == 1
    assert summary["ixps_missing"] == 0 and summary["ixps_failed"] == [code]
