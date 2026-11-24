# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — feed Atom de O que mudou (`api/services/historico.feed_atom`): contagem no título, `updated` e links (TRANSV-E18)."""
import xml.etree.ElementTree as ET

from api.services import historico as h

NS = {"a": "http://www.w3.org/2005/Atom"}
BASE = "https://exemplo.test"


class _Repo:
    def __init__(self, eventos: dict[str, list[dict]]):
        self._ev = eventos

    def datas(self):
        return sorted(self._ev)

    def eventos(self, d):
        return self._ev.get(d, [])


def _ev(data, tipo, entidade, chave="", confirmado_em=None, estado="confirmado", **extra):
    e = {"data": data, "tipo": tipo, "entidade": entidade, "chave": chave, "estado": estado, **extra}
    if entidade.startswith("asn:"):
        e["asn"] = int(entidade[4:])
    if estado == "confirmado":
        e["confirmado_em"] = confirmado_em or data
    return e


def _entradas(xml: str) -> dict[str, ET.Element]:
    raiz = ET.fromstring(xml)
    return {e.find("a:title", NS).text: e for e in raiz.findall("a:entry", NS)}


def test_titulo_de_entrada_em_ptt_conta_eventos_e_ases_distintos():
    """Um AS que entra em três PTTs são três eventos e um AS: o título dizia "N ASes" com N eventos."""
    evs = [_ev("2026-11-22", "ixp_entrada", "asn:64500", c) for c in ("sp", "rj", "ce")] + [_ev("2026-11-22", "ixp_entrada", "asn:64501", "sp")]
    xml = h.feed_atom(_Repo({"2026-11-15": [], "2026-11-22": evs}), ["2026-11-15", "2026-11-22"], BASE)
    titulos = list(_entradas(xml))
    assert titulos == ["4 entradas de AS como membro de PTT (2 ASes) (2026-11-22)"]


def test_updated_e_a_data_em_que_o_evento_se_confirmou():
    """Evento de janela 2 nascido em 11-15 e confirmado em 11-22 entra no feed em 11-22, nunca com `updated` retroativo."""
    ev = _ev("2026-11-15", "mudanca_origem", "prefixo:2001:db8::/32", "64501", confirmado_em="2026-11-22", de=64500, para=64501)
    pendente = _ev("2026-11-22", "mudanca_origem", "prefixo:2001:db8:1::/48", "64501", estado="pendente", de=64500, para=64501)
    xml = h.feed_atom(_Repo({"2026-11-08": [], "2026-11-15": [ev], "2026-11-22": [pendente]}), ["2026-11-15", "2026-11-22"], BASE)
    (titulo, entrada), = _entradas(xml).items()
    assert titulo == "1 prefixos mudaram de origem (2026-11-22)"
    assert entrada.find("a:updated", NS).text == "2026-11-22T00:00:00Z"
    assert "2026-11-22" in entrada.find("a:id", NS).text


def test_evento_confirmado_na_data_atual_vindo_de_data_anterior_ao_recorte_entra():
    ev = _ev("2026-11-08", "asn_novo", "asn:64502", confirmado_em="2026-11-15")
    xml = h.feed_atom(_Repo({"2026-11-08": [ev], "2026-11-15": [], "2026-11-22": []}), ["2026-11-15", "2026-11-22"], BASE)
    assert list(_entradas(xml)) == ["1 ASes passaram a aparecer na tabela de roteamento (2026-11-15)"]


def test_links_por_entidade_e_categoria_do_tipo():
    evs = [_ev("2026-11-22", "roa_ganho", "asn:64500"), _ev("2026-11-22", "roa_ganho", "asn:64501"),
           _ev("2026-11-22", "outorga_nova", "cnpj:12345678000199", "scm")]
    xml = h.feed_atom(_Repo({"2026-11-22": evs}), ["2026-11-22"], BASE)
    ent = _entradas(xml)
    roa = ent["2 ASes passaram a ter ROA (2026-11-22)"]
    assert roa.find("a:category", NS).get("term") == "roa_ganho"
    corpo = roa.find("a:content", NS).text
    assert f'href="{BASE}/asn/64500"' in corpo and f'href="{BASE}/asn/64501"' in corpo
    outorga = ent["1 novas outorgas no cadastro da Anatel (2026-11-22)"]
    assert outorga.find("a:link", NS).get("href") == f"{BASE}/operadora/12345678000199"     # uma entidade só: o link vai a ela
    assert roa.find("a:link", NS).get("href") == f"{BASE}/mudancas"
