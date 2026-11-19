# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — MANRS, tabela de participantes: HTML sintético no formato do site, sem rede."""
import pytest

from core import manrs
from core.common import read_json_gz
from sources.manrs_participantes import collect as fonte


class _Log:
    def info(self, *a, **k): pass
    warning = info


def _html(fx):
    return fx("manrs_participantes", "participantes.sample.html").read_text(encoding="utf-8")


def test_parser_le_organizacoes_asns_e_acoes(fx):
    p = manrs.participantes(_html(fx))
    assert [x["org"] for x in p][:2] == ["Provedor Sintetico Um & Cia", "Provedor Sintetico Dois"]          # entidade HTML decodificada
    um, dois, mista, nova, exterior, vazio = p
    assert um["asns"] == [64500] and um["areas"] == ["BR"] and um["aprovado"] == "2026-09-14"
    assert um["acoes"]["filtragem"] == {"marca": True, "pct": None} and um["acoes"]["anti_spoofing"] == {"marca": None, "pct": 100.0}
    assert um["acoes"]["roteamento"]["irr"] == 100.0 and um["acoes"]["roteamento"]["rpki"] == 97.0
    assert dois["asns"] == [64501, 64502] and dois["acoes"]["anti_spoofing"] == {"marca": None, "pct": None}          # No data
    assert mista["areas"] == ["BR", "US"] and mista["asns"] == [15169, 64503] and mista["acoes"]["anti_spoofing"]["pct"] == 49.0
    assert nova["acoes"]["anti_spoofing"] == {"marca": False, "pct": None} and nova["acoes"]["roteamento"]["marca"] is True
    assert exterior["areas"] == ["US"] and vazio["acoes"]["roteamento"] == {"irr": None, "rpki": None, "marca": None}


def test_data_da_medicao_e_html_sem_tabela(fx):
    assert manrs.medido_em(_html(fx)) == "2026-10-01"
    with pytest.raises(ValueError):
        manrs.participantes("<html><body>Just a moment...</body></html>")


def test_coleta_grava_bruto_e_normalizado_e_falha_com_pagina_truncada(fx, base, monkeypatch):
    with pytest.raises(RuntimeError, match="truncada"):
        fonte.run("2026-11-03", base, _Log(), pagina=_html(fx))                       # 6 organizações < mínimo
    monkeypatch.setattr(fonte, "MINIMO_ORGANIZACOES", 5)
    monkeypatch.setattr(fonte, "MINIMO_COM_BR", 3)
    r = fonte.run("2026-11-03", base, _Log(), pagina=_html(fx))
    assert r == {"organizacoes": 6, "com_area_br": 4, "medido_em": "2026-10-01"}
    doc = read_json_gz(base / "normalized" / "2026-11-03" / "summary" / "manrs_participantes.json.gz")
    assert len(doc["participantes"]) == 6 and doc["atribuicao"].startswith("Provided by the MANRS") and doc["medido_em"] == "2026-10-01"
    assert (base / "raw" / "2026-11-03" / "summary" / "manrs-participantes-2026-11-03.html.gz").exists()
