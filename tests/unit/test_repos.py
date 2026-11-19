# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Repositórios de artefatos: ausência = None, invalidação, ilegível, gancho de validação e a fachada do Store."""
import gzip
import json
import logging

import pytest

from api.repos.base import ArtifactRepo
from api.repos.sici import SiciRepo
from api.store import Store


def _grava(pub, nome, doc):
    caminho = pub / nome
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if nome.endswith(".gz"):
        with gzip.open(caminho, "wt", encoding="utf-8") as f:
            json.dump(doc, f)
    else:
        caminho.write_text(json.dumps(doc), encoding="utf-8")


def test_ausente_e_none_e_fica_em_cache_ate_invalidar(tmp_path):
    pub = tmp_path / "2026-09-20"
    _grava(pub, "manifest.json", {"snapshot_date": "2026-09-20"})      # snapshot publicado: só nele o None fica guardado
    repo = ArtifactRepo(lambda d: tmp_path / d)
    assert repo.ler("2026-09-20", "x.json.gz") is None
    _grava(pub, "x.json.gz", {"a": 1})
    assert repo.ler("2026-09-20", "x.json.gz") is None            # o None ficou memorizado, como era no Store
    repo.invalidar("2026-09-20")
    assert repo.ler("2026-09-20", "x.json.gz") == {"a": 1}        # publicar num snapshot já servido não exige reiniciar a API


def test_lê_json_puro_e_gz_pela_extensao_e_invalida_so_um_arquivo(tmp_path):
    pub = tmp_path / "d"
    _grava(pub, "a.json", {"k": "json"})
    _grava(pub, "b.json.gz", {"k": "gz"})
    repo = ArtifactRepo(lambda d: tmp_path / d)
    assert repo.ler("d", "a.json") == {"k": "json"} and repo.ler("d", "b.json.gz") == {"k": "gz"}
    _grava(pub, "a.json", {"k": "novo"})
    _grava(pub, "b.json.gz", {"k": "novo"})
    repo.invalidar("d", "a.json")
    assert repo.ler("d", "a.json") == {"k": "novo"} and repo.ler("d", "b.json.gz") == {"k": "gz"}


def test_ilegivel_vira_none_com_aviso(tmp_path, caplog):
    pub = tmp_path / "d"
    pub.mkdir()
    (pub / "ruim.json.gz").write_bytes(b"isto nao e gzip")
    with caplog.at_level(logging.WARNING, logger="arandurape"):
        assert ArtifactRepo(lambda d: tmp_path / d).ler("d", "ruim.json.gz") is None
    assert "failed to load ruim.json.gz" in caplog.text


def test_gancho_de_validacao_roda_na_leitura(tmp_path):
    _grava(tmp_path / "d", "x.json", {"faltando": True})

    def validar(arquivo, doc):
        assert "cnpjs" in doc, f"{arquivo} sem cnpjs"

    with pytest.raises(AssertionError, match="x.json sem cnpjs"):
        ArtifactRepo(lambda d: tmp_path / d, validar).ler("d", "x.json")


def test_sici_repo_consultas_e_fachada_do_store(tmp_path):
    d = "2026-09-20"
    pub = tmp_path / "published" / d
    doc = {"mes_referencia": "2026-08", "meses_disponiveis": ["2026-08"], "total_acessos": 10, "total_cnpjs": 1, "fonte": "x",
           "cnpjs": {"11111111000111": {"acessos": 10, "pf": 7, "pj": 3}}, "asn_to_cnpj": {"64500": "11111111000111"},
           "serie_por_cnpj": {"11111111000111": [["2026-08", 10, 7, 3]]}, "serie_total": [{"mes": "2026-08", "acessos": 10}],
           "distrib_velocidade": {"SP": {"pf": {}, "pj": {}}}, "divergencia": {"64500": {"razao": 2.0}}}
    _grava(pub, "manifest.json", {})
    _grava(pub, "sici.json.gz", doc)
    _grava(pub, "sici_municipios.json.gz", {"municipios": {"3550308": {"acessos": 10}}})
    _grava(pub, "sici_movel.json.gz", {**doc, "distrib_modalidade": {"SP": {"pf": {"x": 1}, "pj": {}}}})
    repo = SiciRepo(lambda dd: tmp_path / "published" / dd, "sici")
    assert repo.meta(d)["mes_referencia"] == "2026-08" and repo.for_asn(d, 64500)["acessos"] == 10
    assert repo.cnpj_for_asn(d, 64500) == "11111111000111" and repo.for_asn(d, 1) is None
    assert repo.serie(d, "11111111000111") == [["2026-08", 10, 7, 3]] and repo.serie(d, "x") == []
    assert repo.municipio(d, "3550308") == {"acessos": 10} and repo.municipios(d) == {"3550308": {"acessos": 10}}
    assert repo.meta("2000-01-01") == {} and repo.for_cnpj("2000-01-01", "x") is None and repo.municipios("2000-01-01") == {}
    # a fachada devolve o que o repositório devolve, no fixo e no móvel
    store = Store(tmp_path)
    assert store.sici_meta(d) == repo.meta(d) and store.sici_for_cnpj(d, "11111111000111") == repo.for_cnpj(d, "11111111000111")
    assert store.sici_distrib_velocidade(d) == repo.distribuicao(d, "distrib_velocidade")
    assert store.sici_divergencia(d, 64500) == {"razao": 2.0} and store.sici_movel_distrib_modalidade(d)["SP"]["pf"] == {"x": 1}
    assert store.sici_movel_meta(d)["total_acessos"] == 10 and store.sici_movel_municipios(d) == {}
    store.invalidate_sici(d)
    _grava(pub, "sici_municipios.json.gz", {"municipios": {"1": {"acessos": 1}}})
    assert store.sici_municipios(d) == {"1": {"acessos": 1}}


def test_documentos_repo_normaliza_ausencia_e_tipos(tmp_path):
    from api.repos.documentos import DocumentosRepo
    pub = tmp_path / "d"
    _grava(pub, "ixps/index.json", [{"code": "sp"}])
    _grava(pub, "asns/names.json", {"1": "A"})
    _grava(pub, "asns/index.json", {"nao": "e lista"})
    r = DocumentosRepo(lambda d: tmp_path / d)
    assert r.ixp_index("d") == [{"code": "sp"}] and r.asn_names("d") == {"1": "A"}
    assert r.asn_index("d") == [] and r.ixp_index("x") == [] and r.asn_names("x") == {}      # tipo errado ou ausente = vazio, como o Store sempre devolveu
    assert r.manifest("d") is None and r.summary("d") is None and r.cdns("d") is None
    _grava(pub, "bgp_stability.json", {"as_stability": []})
    assert r.bgp_stability_em_memoria("d") is None                                           # só olha o cache
    assert r.bgp_stability("d") == {"as_stability": []} and r.bgp_stability_datas_em_memoria() == {"d"}
    r.soltar_bgp_stability("d")
    assert r.bgp_stability_datas_em_memoria() == set()


def test_rpki_valida_cobertura_e_nao_memoriza_a_ausencia_do_vrp(tmp_path):
    from api.repos.rpki import RpkiRepo
    repo = RpkiRepo(lambda d: tmp_path / d)
    assert repo.validar_prefixos("d", 64500, ["200.1.0.0/24"]) == {}       # sem VRP: nada a validar
    _grava(tmp_path / "d", "rpki/vrp_list.json.gz", [
        {"asn": "AS64500", "prefix": "200.1.0.0/16", "maxLength": 24, "ta": "lacnic"},
        {"asn": 64501, "prefix": "2001:db8::/32", "maxLength": 48, "ta": "lacnic"},
    ])
    r = repo.validar_prefixos("d", 64500, ["200.1.2.0/24", "200.1.2.0/25", "200.9.0.0/24", "2001:db8:1::/48"])
    assert r == {"200.1.2.0/24": "valid", "200.1.2.0/25": "invalid", "200.9.0.0/24": "not_found", "2001:db8:1::/48": "invalid"}
    assert [x["prefix"] for x in repo.vrps_do_asn("d", 64500)] == ["200.1.0.0/16"]   # o coletor publicou depois e a API viu


def test_aspa_indexa_por_customer_e_por_provider(tmp_path):
    from api.repos.rpki import RpkiRepo
    repo = RpkiRepo(lambda d: tmp_path / d)
    _grava(tmp_path / "d", "rpki/aspa_list.json.gz", [{"customer": 1, "providers": [2, 3], "tal": "ripe"}])
    assert repo.como_customer("d", 1) == [{"providers": [2, 3], "tal": "ripe"}]
    assert repo.como_provider("d", 3) == [{"customer": 1, "tal": "ripe"}]
    assert repo.como_provider("d", 9) == []
