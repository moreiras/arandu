# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — APNIC Labs (ROV e DNSSEC por ASN): página de país → tabela → normalizado, sem rede."""
import gzip

import pytest
import respx

from core.common import read_json_gz
from sources.apnic_dnssec import collect as dnssec
from sources.apnic_irov import collect as irov
from sources.apnic_labs import tabela


def _h(fx, nome):
    return fx("apnic_labs", nome).read_text(encoding="utf-8")


def test_parse_rpki_le_valor_amostras_e_conta_linha_sem_medicao(fx):
    t = tabela.parse_tabela(_h(fx, "rpki_BR.html"), "rpki")
    assert t["asns"][64497] == {"valores": [0.26], "amostras": 290351}
    assert t["asns"][64496]["valores"] == [100.0] and 64499 not in t["asns"] and t["sem_valor"] == 1
    assert tabela.ultima_data_da_serie(_h(fx, "rpki_BR.html")) == "2026-10-30"


def test_parse_dnssec_le_validacao_total_e_parcial(fx):
    t = tabela.parse_tabela(_h(fx, "dnssec_BR.html"), "dnssec")
    assert t["asns"][64497] == {"valores": [7.69, 12.43], "amostras": 64897}
    assert t["asns"][64498]["valores"] == [94.84, 3.74] and t["sem_valor"] == 1


def test_cabecalho_diferente_falha_alto(fx):
    html = _h(fx, "rpki_BR.html").replace("RPKI Validates", "RPKI Filters")
    with pytest.raises(tabela.LayoutMudou, match="cabeçalho"):
        tabela.parse_tabela(html, "rpki")


def test_tabela_com_linha_ilegivel_falha_alto(fx):
    html = _h(fx, "rpki_BR.html").replace('"AS64498 - REDE DOCUMENTACAO ME",{v: 12.50, f:\'12.50%\'},86]', '"AS64498 - X",quebrado]')
    with pytest.raises(tabela.LayoutMudou, match="linhas na tabela"):
        tabela.parse_tabela(html, "rpki")


def test_pagina_sem_tabela_falha_alto():
    with pytest.raises(tabela.LayoutMudou, match="não encontrada"):
        tabela.parse_tabela("<html>manutenção</html>", "rpki")


@respx.mock
def test_run_irov_grava_bruto_e_normalizado(base, log, fx, date_str, monkeypatch):
    monkeypatch.setattr(irov, "MINIMO_LINHAS", 3)
    monkeypatch.setattr(irov, "MINIMO_COM_MEDICAO", 3)
    respx.get(irov.URL).respond(200, text=_h(fx, "rpki_BR.html"))
    r = irov.run(date_str, base, log)
    assert r["as_of"] == "2026-10-30" and r["total"] == 3 and r["asns_sem_medicao"] == 1 and r["janela_dias"] == 7
    n = read_json_gz(base / "normalized" / date_str / "summary" / "apnic_irov.json.gz")
    assert n["asns"]["64497"] == {"validates_pct": 0.26, "amostras": 290351} and "re-use with attribution" in n["copyright"]
    bruto = base / "raw" / date_str / "summary" / "apnic-rpki-BR-2026-10-30.html.gz"
    assert gzip.decompress(bruto.read_bytes()).decode() == _h(fx, "rpki_BR.html")


@respx.mock
def test_run_dnssec_grava_normalizado(base, log, fx, date_str, monkeypatch):
    monkeypatch.setattr(dnssec, "MINIMO_ASNS", 3)
    respx.get(dnssec.URL).respond(200, text=_h(fx, "dnssec_BR.html"))
    r = dnssec.run(date_str, base, log)
    assert r["as_of"] == "2026-10-30" and r["janela_dias"] == 1
    n = read_json_gz(base / "normalized" / date_str / "summary" / "apnic_dnssec.json.gz")
    assert n["asns"]["64497"] == {"validates_pct": 7.69, "parcial_pct": 12.43, "amostras": 64897}


@respx.mock
def test_poucos_asns_falha_alto_e_nao_grava(base, log, fx, date_str):
    respx.get(irov.URL).respond(200, text=_h(fx, "rpki_BR.html"))            # 3 ASNs < 3.000
    with pytest.raises(RuntimeError, match="ASNs com medição"):
        irov.run(date_str, base, log)
    assert not (base / "normalized" / date_str / "summary" / "apnic_irov.json.gz").exists()


def test_irov_aceita_muitos_asns_sem_valor_e_recusa_pagina_truncada(monkeypatch):
    """O APNIC deixa muitos ASNs sem valor (4.770 de 7.573 num dia): um limiar alto de ASNs com medição pararia o coletor sem a página estar truncada."""
    monkeypatch.setattr(irov, "MINIMO_LINHAS", 5)
    monkeypatch.setattr(irov, "MINIMO_COM_MEDICAO", 2)
    linhas = "".join(f"<tr><td>AS{64500 + i}</td><td>{'' if i >= 2 else '50.5'}</td><td>{300 if i < 2 else 0}</td></tr>" for i in range(8))
    html = f"<html>{linhas}</html>"
    monkeypatch.setattr(irov.tabela, "parse_tabela", lambda h, k: {"asns": {64500: {"valores": [50.5], "amostras": 300}, 64501: {"valores": [51.0], "amostras": 200}}, "sem_valor": 6})
    monkeypatch.setattr(irov.tabela, "ultima_data_da_serie", lambda h: "2026-11-09")
    ok = irov.normalizar(html, "2026-11-10")
    assert ok["total"] == 2 and ok["asns_sem_medicao"] == 6                          # 2 com valor e 6 sem valor: página inteira, cobertura menor
    monkeypatch.setattr(irov, "MINIMO_LINHAS", 20)
    with pytest.raises(RuntimeError, match="linhas"):
        irov.normalizar(html, "2026-11-10")                                          # poucas linhas: página truncada
