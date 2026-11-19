# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T2 — paridade das regras de alerta: `products.alerts` dá exatamente os alertas da `api.asn_health` antiga."""
import json

import pytest

from api.asn_health import compute_asn_alerts
from api.store import Store
from products.alerts.registro import calcular_alertas
from tests.products.conftest import fake_pix
from tests.synth.world import T1
from tests.unit.test_alerts_regras import ASN, CENARIOS, FakeStore


NOVAS = {"sessao_rs_down", "import_limit_proximo"}      # regras sem equivalente em api/asn_health.py (sem paridade a comparar)


def _sem_versao(alertas):
    """A regra nova acrescenta `desde_versao`; o resto do alerta tem de ser idêntico ao da função antiga (sem as regras posteriores à paridade)."""
    return [{k: v for k, v in a.items() if k != "desde_versao"} for a in alertas if a["id"] not in NOVAS]


def test_regras_novas_iguais_as_antigas_nos_cenarios_plantados():
    for regra_id, (dispara, _, nao) in CENARIOS.items():
        for cen in (dispara, nao):
            store = cen.get("store") or FakeStore()
            assert _sem_versao(calcular_alertas(store, "2026-10-23", ASN, cen["doc"])) == compute_asn_alerts(store, "2026-10-23", ASN, cen["doc"]), regra_id


def test_regras_novas_iguais_as_antigas_em_todos_os_asns_do_dataset(pipeline, monkeypatch):
    base, _ = pipeline
    monkeypatch.setattr(Store, "_load_pix_config", lambda self: fake_pix())
    store = Store(base)
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in (base / "published" / T1 / "asns").glob("*.json") if p.stem.isdigit()]
    assert len(docs) > 50
    com_alerta = 0
    for doc in docs:
        antigo = compute_asn_alerts(store, T1, doc["asn"], doc)
        assert _sem_versao(calcular_alertas(store, T1, doc["asn"], doc)) == antigo, doc["asn"]
        com_alerta += bool(antigo)
    assert com_alerta > 5                      # o dataset exercita alertas de verdade (não é igualdade de listas vazias)


def test_manifesto_registra_rules_version_e_cada_alerta_a_versao_da_sua_regra(pipeline):
    from products.alerts.registro import regras_publicadas, rules_version

    base, _ = pipeline
    m = json.loads((base / "published" / T1 / "manifest.json").read_text(encoding="utf-8"))
    assert m["rules_version"] == rules_version() and m["rules"] == regras_publicadas()
    versoes = regras_publicadas()
    n = 0
    for p in (base / "published" / T1 / "asns").glob("*.json"):
        if not p.stem.isdigit():
            continue
        for a in json.loads(p.read_text(encoding="utf-8")).get("alerts", []):
            familia = a["id"] if a["id"] in versoes else next(f for f in versoes if a["id"].startswith(f + "_"))     # ex.: desagregacao_ipv4
            assert a["desde_versao"] == versoes[familia], a["id"]
            n += 1
    assert n > 5
