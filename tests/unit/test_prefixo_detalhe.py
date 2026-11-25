# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`api.routes.prefixes.detalhe_prefixo` e `RpkiRepo.diagnosticar` (PT-07): os casos que o dataset sintético não tem.

Rota anunciada dentro de uma alocação do Registro.br, rota vista só nos route servers do IX.br e os três motivos de RPKI."""
import gzip
import json

import pytest

from api.repos.rpki import RpkiRepo
from api.routes import prefixes as pf

D = "2026-09-20"


class _Store:
    """O mínimo do `Store` que `detalhe_prefixo` usa."""

    def __init__(self, alocacoes, global_v4=None, rs=None, rpki=None):
        self._geo = {"features": [{"properties": {"prefix": p, "origin_asn": a, "uf": "SP", "country": "BR",
                                                  "geo_confidence": "city_centroid", "geo_source": "x", "lat": 1, "lon": 2}}
                                  for p, a in alocacoes.items()]}
        self._global = {"v4": dict(global_v4 or {}), "v6": {}}
        self._rs = dict(rs or {})
        self._rpki = rpki

    def geo_map(self, d, nome):
        return self._geo

    def origin_by_prefix(self, d, afi):
        return self._global[afi]

    def colunar(self, d, nome):
        return object() if self._rs is not None else None

    def query(self, d, colecao, corpo):
        p = corpo["filter"]["value"]
        return {"items": [{"prefix": p, "origin_asn": self._rs[p]}] if p in self._rs else []}

    def asn_names(self, d):
        return {"64500": "Detentor", "64501": "Cliente", "64502": "Outro"}

    def asn_detail(self, d, asn):
        return None

    def rpki_diagnostico(self, d, p, asn):
        return self._rpki.diagnosticar(d, p, asn) if self._rpki else None


@pytest.fixture(autouse=True)
def _limpa_indice():
    pf._INDICE_LPM.clear()
    yield
    pf._INDICE_LPM.clear()


@pytest.fixture
def rpki(tmp_path):
    destino = tmp_path / D / "rpki"
    destino.mkdir(parents=True)
    vrps = [{"asn": "AS64500", "prefix": "192.0.2.0/23", "maxLength": 24, "ta": "lacnic"},
            {"asn": "AS64501", "prefix": "198.51.100.0/24", "maxLength": 24, "ta": "lacnic"}]
    with gzip.open(destino / "vrp_list.json.gz", "wt", encoding="utf-8") as fh:
        json.dump(vrps, fh)
    return RpkiRepo(lambda d: tmp_path / d)


def test_rota_dentro_de_alocacao_tem_detentor_e_origem_proprios(rpki):
    st = _Store({"192.0.2.0/23": 64500}, global_v4={"192.0.2.128/25": 64501}, rpki=rpki)
    d = pf.detalhe_prefixo(st, D, "192.0.2.128/25")
    assert d["escopo"] == "rota_dentro_de_alocacao" and d["alocacao_registro_br"] == "192.0.2.0/23"
    assert (d["registro_asn"], d["observed_origin_asn"], d["observed_origin_fonte"]) == (64500, 64501, "tabela_global")
    assert d["uf"] is None                                                  # a UF é da alocação, não da rota
    assert d["rpki_observado"]["estado"] == "invalid" and d["rpki_observado"]["motivo"] == "origem_diferente"


def test_rota_so_nos_route_servers_abre_com_a_fonte(rpki):
    st = _Store({}, rs={"198.51.100.0/24": 64501}, rpki=rpki)
    d = pf.detalhe_prefixo(st, D, "198.51.100.0/24")
    assert d["escopo"] == "fora_do_registro_br" and d["observed_origin_fonte"] == "route_servers_ixbr"
    assert d["rpki_observado"]["estado"] == "valid" and d["rpki_observado"]["motivo"] is None


def test_ausente_e_grafia_invalida():
    st = _Store({"192.0.2.0/23": 64500})
    with pytest.raises(pf.PrefixoAusente, match="não prova"):
        pf.detalhe_prefixo(st, D, "203.0.113.0/24")
    for ruim in ("192.0.2.0", "192.0.2.0/33", "abc/8"):
        with pytest.raises(pf.PrefixoInvalido, match="Grafia não reconhecida"):
            pf.detalhe_prefixo(st, D, ruim)
    assert pf.detalhe_prefixo(st, D, " 192.0.3.7/23 ")["prefix"] == "192.0.2.0/23"


def test_motivos_do_rpki(rpki):
    assert rpki.diagnosticar(D, "192.0.2.0/24", 64500)["estado"] == "valid"
    mais = rpki.diagnosticar(D, "192.0.2.0/25", 64500)
    assert (mais["estado"], mais["motivo"]) == ("invalid", "maxlength_excedido")
    outro = rpki.diagnosticar(D, "192.0.2.0/24", 64502)
    assert (outro["estado"], outro["motivo"]) == ("invalid", "origem_diferente")
    assert outro["roas_que_cobrem"] == [{"prefix": "192.0.2.0/23", "asn": 64500, "maxLength": 24, "ta": "lacnic", "autoriza_origem": False}]
    assert rpki.diagnosticar(D, "203.0.113.0/24", 64500)["motivo"] == "sem_roa"
    sem = rpki.diagnosticar(D, "192.0.2.0/24", None)
    assert (sem["estado"], sem["motivo"]) == ("nao_avaliado", "sem_anuncio") and sem["roas_que_cobrem"][0]["autoriza_origem"] is None
    assert rpki.validar_prefixos(D, 64500, ["192.0.2.0/24", "192.0.2.0/25", "203.0.113.0/24"]) == {
        "192.0.2.0/24": "valid", "192.0.2.0/25": "invalid", "203.0.113.0/24": "not_found"}
