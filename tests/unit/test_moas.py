# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""MOAS medido (PT-04b): análise a partir de `origins-multi-{afi}`, os três estados (com MOAS, zero observado, não medido) e o que a
API e o MCP servem de documentos antigos."""
import gzip
import json

from core import moas
from products.routing_analysis import build, resumo
from products.routing_analysis.cobertura import _moas_analysis
from products.routing_analysis.util import _PrefixTrie

D = "2026-11-22"


class _Log:
    def info(self, *a, **k): pass
    debug = warning = error = info


def _gz(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(obj, f)


def _trie(*prefixos):
    t = _PrefixTrie()
    for p in prefixos:
        t.insert(p, p)
    t._build()
    return t


def _om(prefixos, coletores=("rvA", "rvB")):
    return {"coletores": list(coletores), "prefixos": prefixos}


def test_moas_analysis_conta_global_e_lista_so_os_brasileiros():
    lista, r = _moas_analysis(
        {"v4": _om({"198.18.0.0/24": {"64500": ["rvA", "rvB"], "65001": ["rvB"]}, "203.0.113.0/24": {"1": ["rvA"], "2": ["rvB"]}}),
         "v6": _om({"2001:db8:1::/48": {"64500": ["rvA"], "65002": ["rvA"]}})},
        _trie("198.18.0.0/15"), _trie("2001:db8::/32"), {64500}, {65001: "EXTERIOR"})
    assert r["prefixos"] == {"v6": {"global": 1, "br": 1}, "v4": {"global": 2, "br": 1}}
    assert [m["prefix"] for m in lista] == ["2001:db8:1::/48", "198.18.0.0/24"]
    m = lista[1]
    assert m["br_origins"] == [64500] and m["origens"][1] == {"asn": 65001, "name": "EXTERIOR", "coletores": 1,
                                                              "coletores_nomes": ["rvB"], "asn_br": False}


def test_moas_analysis_familia_sem_artefato_fica_nula_e_nenhuma_devolve_nulo():
    lista, r = _moas_analysis({"v4": _om({}), "v6": None}, _trie(), _trie(), set())
    assert lista == [] and r["prefixos"] == {"v6": None, "v4": {"global": 0, "br": 0}} and r["coletores"]["v6"] is None
    assert _moas_analysis({"v4": None, "v6": None}, _trie(), _trie(), set()) == (None, None)


def test_moas_analysis_trunca_a_lista_e_avisa():
    pref = {f"198.18.{i}.0/24": {"1": ["rvA"], "2": ["rvB"]} for i in range(5)}
    lista, r = _moas_analysis({"v4": _om(pref), "v6": None}, _trie("198.18.0.0/15"), _trie(), set(), max_entries=3)
    assert len(lista) == 3 and r["lista_truncada"] is True and r["prefixos"]["v4"]["br"] == 5


def _build(tmp, origens_multi):
    norm = tmp / "normalized" / D / "summary"
    _gz(norm / "registro_br.json.gz", {"asns": [{"asn": 64500, "name": "PROVEDOR BR", "cnpj": "2",
                                                 "prefixes_v4": ["198.18.0.0/15"], "prefixes_v6": ["2001:db8::/32"]}]})
    _gz(norm / "origin-prefixes-v4.json.gz", {"64500": ["198.18.0.0/16"]})
    _gz(norm / "origin-prefixes-v6.json.gz", {"64500": ["2001:db8::/32"]})
    _gz(norm / "prefix-set-v4.json.gz", ["198.18.0.0/16"])
    _gz(norm / "prefix-set-v6.json.gz", ["2001:db8::/32"])
    for afi, doc in origens_multi.items():
        _gz(norm / f"origins-multi-{afi}.json.gz", doc)
    assert build.run(D, tmp, _Log())
    pub = tmp / "published" / D
    return json.loads((pub / "routing_analysis.json").read_text()), json.loads((pub / resumo.ARQUIVO).read_text())


def test_tres_estados_na_analise_e_no_resumo(tmp_path):
    com, rcom = _build(tmp_path / "com", {"v4": _om({"198.18.0.0/16": {"64500": ["rvA"], "65001": ["rvB"]}}), "v6": _om({})})
    assert len(com["moas"]) == 1 and com["moas_resumo"]["prefixos"]["v4"]["br"] == 1
    assert rcom["saude"]["moas"]["v4"] == {"prefixos": 1, "prefixos_br": 1, "coletores": 2}
    zero, rzero = _build(tmp_path / "zero", {"v4": _om({}), "v6": _om({})})
    assert zero["moas"] == [] and zero["moas_resumo"]["prefixos"]["v6"] == {"global": 0, "br": 0}       # zero observado, medido
    assert rzero["saude"]["moas"]["v6"]["prefixos"] == 0 and "moas_indisponivel" not in zero
    sem, rsem = _build(tmp_path / "sem", {})
    assert sem["moas"] is None and sem["moas_resumo"] is None and sem["moas_indisponivel"] == moas.MOTIVO
    assert rsem["saude"]["moas"] is None


def test_api_e_mcp_tratam_documento_antigo_como_nao_medido():
    """Snapshots publicados antes traziam `moas: []` (ou 0 no resumo) sem ter medido: saem nulos com o motivo."""
    antigo = moas.analise_publicada({"snapshot_date": D, "moas": []})
    assert antigo["moas"] is None and antigo["moas_resumo"] is None and antigo["moas_indisponivel"] == moas.MOTIVO
    medido = {"moas": [], "moas_resumo": {"prefixos": {"v6": {"global": 0, "br": 0}, "v4": None}}}
    assert moas.analise_publicada(medido) == medido                                     # zero medido passa como está
    r_antigo = moas.resumo_publicado({"saude": {"moas": {"prefixos": 0, "lista_truncada": False}}})
    assert r_antigo["saude"]["moas"] is None and "limite da coleta" in r_antigo["saude"]["moas_indisponivel"]
    r_novo = {"saude": {"moas": {"v6": None, "v4": {"prefixos": 0, "prefixos_br": 0, "coletores": 8}}}}
    assert moas.resumo_publicado(r_novo) == r_novo and moas.resumo_publicado(None) is None
