# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Licenças do catálogo (item 5): a camada aberta não ganha fonte `nao_verificado` ou `restrito` sem decisão registrada.

`tests/contracts/licencas_baseline.json` guarda a dívida conhecida (fontes publicáveis cujo uso comercial efetivo não é `permitido`). Fonte nova
com licença não lida não passa; fonte da lista que ficou `permitido` tem de sair dela, então a dívida só diminui."""
import json
from pathlib import Path

import pytest

from core.catalog.loader import load_catalog, uso_comercial_efetivo

BASELINE = Path(__file__).resolve().parents[1] / "contracts" / "licencas_baseline.json"


@pytest.fixture(scope="module")
def cat():
    return load_catalog()


def _atual(cat) -> dict[str, str]:
    return {s.id: uso_comercial_efetivo(cat, s.id) for s in cat.sources.values() if s.publicavel and uso_comercial_efetivo(cat, s.id) != "permitido"}


def test_nenhuma_fonte_nova_nao_verificada_ou_restrita_na_camada_aberta(cat):
    base = json.loads(BASELINE.read_text(encoding="utf-8"))["fontes"]
    novas = sorted(set(_atual(cat)) - set(base))
    assert novas == [], (
        f"fonte(s) publicável(is) com licença não lida ou restrita: {novas}. Leia os termos e marque `permitido`, ou registre a autorização escrita em "
        "`pendencias` da fonte e acrescente a fonte a tests/contracts/licencas_baseline.json (decisão do mantenedor)")


def test_a_divida_de_licenca_so_diminui(cat):
    base = json.loads(BASELINE.read_text(encoding="utf-8"))["fontes"]
    atual = _atual(cat)
    resolvidas = sorted(i for i in base if i not in atual)
    assert resolvidas == [], f"licença resolvida: remova {resolvidas} de tests/contracts/licencas_baseline.json"
    for i, u in atual.items():
        assert base[i] in ("nao_verificado", "restrito") and u in ("nao_verificado", "restrito")


def test_manrs_participantes_segue_fora_da_camada_aberta(cat):
    """A lista nominal do MANRS é restrita (termos do GCA, cláusula 2): só agregado pode sair; a fonte bruta não é publicável."""
    s = cat.sources["manrs_participantes"]
    assert s.publicavel is False and s.origem.uso_comercial == "restrito"


def test_fonte_restrita_ou_nao_verificada_explica_a_pendencia(cat):
    sem = [s.id for s in cat.sources.values() if uso_comercial_efetivo(cat, s.id) != "permitido" and s.tipo == "bruta" and not (s.pendencias or (s.origem and s.origem.nota))]
    assert sem == [], f"sem pendência nem nota de licença: {sem}"
