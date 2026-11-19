# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T2 — escritas por arquivo publicado: baseline das mutações pós-publicação e meta final (1 escrita)."""
import json
import re
import shutil
from collections import Counter
from pathlib import Path

import pytest

from tests.products.conftest import run_pipeline
from tests.products.escritas import contar_escritas
from tests.synth.world import T1

BASELINE = Path(__file__).resolve().parents[1] / "contracts" / "escritas_por_arquivo.json"


@pytest.fixture(scope="module")
def escritas(dataset, tmp_path_factory):
    base = tmp_path_factory.mktemp("escritas") / "data"
    shutil.copytree(dataset, base)
    with pytest.MonkeyPatch.context() as mp, contar_escritas(base) as c:
        run_pipeline(base, T1, mp)
    return c


def _classe(rel: str) -> str:
    """Agrupa os arquivos em classes (asns/<n>.json → asns/{asn}.json)."""
    return re.sub(r"\d+", "{n}", rel.split("/", 1)[1]) if "/" in rel else rel


def resumo(c: Counter) -> dict:
    por_classe: dict[str, Counter] = {}
    for rel, n in c.items():
        por_classe.setdefault(_classe(rel), Counter())[n] += 1
    return {k: {"arquivos": sum(v.values()), "max_escritas": max(v), "distribuicao": {str(n): v[n] for n in sorted(v)}}
            for k, v in sorted(por_classe.items())}


def test_documento_de_asn_e_escrito_uma_vez_ou_mais_conforme_o_baseline(escritas):
    r = resumo(escritas)
    asn = r["asns/{n}.json"]
    esperado = json.loads(BASELINE.read_text())["asns/{n}.json"]["max_escritas"]
    assert asn["max_escritas"] <= esperado, (
        f"o documento de ASN passou a ser escrito até {asn['max_escritas']}× (baseline {esperado}×): "
        "o passo 1.2.6 só pode REDUZIR esse número")


def test_baseline_registrado_bate_com_a_medicao_ou_foi_reduzido(escritas):
    r = resumo(escritas)
    gravado = json.loads(BASELINE.read_text())
    for classe in ("asns/{n}.json", "asns/index.json", "scm.json.gz"):
        assert r[classe]["max_escritas"] <= gravado[classe]["max_escritas"], classe
