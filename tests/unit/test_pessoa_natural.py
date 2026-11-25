# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Pessoa natural (EI/MEI, D1 do mantenedor): critério, nome público, posição reduzida, percurso sem alterar o original, índice do snapshot."""
import gzip
import json
from pathlib import Path

from core import pessoa_natural as pn
from core.cpf import mascarar_snapshot

RAIZ, CNPJ = "12345678", "12345678000195"
CENTROIDE_VITORIA = (-20.2839, -40.2902)             # config/municipios-centroides.json, 3205309


def _indice(fantasia=None, civis=("FULANO DE TAL",)) -> pn.Indice:
    idx = pn.Indice()
    idx.adicionar(RAIZ, 265061, CNPJ, fantasia, civis)
    return idx


def test_criterio_e_a_natureza_juridica_da_receita():
    assert pn.e_empresario_individual("2135") and pn.e_empresario_individual(2135) and pn.e_empresario_individual("213-5")
    assert pn.e_empresario_individual(texto="Empresário (Individual)") and pn.e_empresario_individual(mei=True)
    assert not pn.e_empresario_individual(2062, "Sociedade Empresária Limitada")       # Ltda é pessoa jurídica
    assert not pn.e_empresario_individual(2305, "Empresa Individual de Responsabilidade Limitada (de Natureza Empresária)")
    assert not pn.e_empresario_individual(None, None)


def test_rotulo_leva_asn_e_cnpj_mascarado():
    assert pn.rotulo(265061, CNPJ) == "Empresário individual (AS265061, CNPJ **.***.678/0001-**)"
    assert pn.rotulo(None, CNPJ) == "Empresário individual (CNPJ **.***.678/0001-**)"
    assert pn.rotulo() == "Empresário individual"
    assert "12345678" not in pn.rotulo(265061, CNPJ)


def test_nome_publico_fantasia_ou_rotulo_e_fantasia_igual_ao_nome_civil_nao_vale():
    assert _indice("Rede Boa Vista").nome_publico(RAIZ, 265061, CNPJ) == "Rede Boa Vista"
    assert _indice(None).nome_publico(RAIZ, 265061, CNPJ) == pn.rotulo(265061, CNPJ)
    assert _indice("Fulano de Tal").nome_publico(RAIZ, 265061, CNPJ) == pn.rotulo(265061, CNPJ)        # a fantasia é o nome da pessoa


def test_percurso_troca_nome_por_cnpj_asn_chave_do_pai_e_nome_conhecido_sem_alterar_o_original():
    idx = _indice()
    rotulo = pn.rotulo(265061, CNPJ)
    doc = {
        "asn": 265061, "name": "FULANO DE TAL 52998224725",
        "scms": [{"cnpj": CNPJ, "razao_social": "FULANO DE TAL", "nome_fantasia": "", "uf": "ES"}],
        "by_cnpj": {CNPJ: [{"razao_social": "FULANO DE TAL"}]},
        "nearby": [{"asn": 265061, "name": "FULANO DE TAL"}, {"asn": 3356, "name": "LEVEL3"}],
        "names": {"265061": "FULANO DE TAL, BR", "3356": "LEVEL3, US"},
        "alt_names": [{"name": "FULANO DE TAL", "source": "Anatel"}],
        "vizinho": {"peer_name": "Fulano de Tal"},
    }
    copia = json.loads(json.dumps(doc))
    out = pn.aplicar(doc, idx)
    assert doc == copia                                                 # o original (documento do Store) não muda
    assert out["name"] == rotulo
    assert out["scms"][0]["razao_social"] == rotulo and out["scms"][0]["nome_fantasia"] == "" and out["scms"][0]["uf"] == "ES"
    assert out["by_cnpj"][CNPJ][0]["razao_social"] == pn.rotulo(265061, CNPJ)
    assert out["nearby"][0]["name"] == rotulo and out["nearby"][1]["name"] == "LEVEL3"
    assert out["names"] == {"265061": rotulo + ", BR", "3356": "LEVEL3, US"}
    assert out["alt_names"][0]["name"] == rotulo
    assert out["vizinho"]["peer_name"] == rotulo                        # nome civil conhecido em campo de nome sem identificador
    assert "FULANO" not in json.dumps(out, ensure_ascii=False).upper()
    assert pn.aplicar(out, idx) == out                                  # idempotente


def test_pj_e_chaves_sem_titular_nao_mudam_e_sem_indice_o_documento_volta_o_mesmo():
    idx = _indice()
    pj = {"asn": 3356, "cnpj": "00000000000191", "razao_social": "LEVEL 3 LTDA", "lat": -23.5, "lon": -46.6, "logradouro": "Rua X", "cep": "01000000"}
    assert pn.aplicar(pj, idx) is pj
    assert pn.aplicar(pj, None) is pj and pn.aplicar(pj, pn.Indice()) is pj


def test_socios_e_holdings_ficam_como_estao():
    idx = _indice()
    doc = {"cnpj": CNPJ, "razao_social": "FULANO DE TAL", "socios": [{"nome": "FULANO DE TAL", "tipo": "juridica"}],
           "holdings_externas": [{"razao_social": "FULANO DE TAL"}]}
    out = pn.aplicar(doc, idx)
    assert out["razao_social"] == pn.rotulo(265061, CNPJ)
    assert out["socios"] == doc["socios"] and out["holdings_externas"] == doc["holdings_externas"]


def test_posicao_vai_ao_centroide_do_municipio_ou_some_e_o_endereco_sai():
    idx = _indice()
    reg = {"cnpj": CNPJ, "lat": -20.27112, "lon": -40.26223, "codigo_municipio_ibge": 3205309, "municipio": "Vitória", "uf": "ES",
           "geo_confidence": "exact_address", "logradouro": "Rua X", "numero": "1", "cep": "29010123"}
    out = pn.aplicar(reg, idx)
    assert (round(out["lat"], 4), round(out["lon"], 4)) == CENTROIDE_VITORIA
    assert out["geo_confidence"] == "city_centroid" and out["municipio"] == "Vitória" and out["uf"] == "ES"
    assert not {"logradouro", "numero", "cep"} & set(out)
    por_nome = pn.aplicar({"cnpj": CNPJ, "lat": 1.0, "lon": 2.0, "municipio": "Vitória", "uf": "ES"}, idx)
    assert (round(por_nome["lat"], 4), round(por_nome["lon"], 4)) == CENTROIDE_VITORIA
    sem_municipio = pn.aplicar({"cnpj": CNPJ, "lat": 1.0, "lon": 2.0, "municipio": "Arandurápolis", "uf": "SP"}, idx)
    assert sem_municipio["lat"] is None and sem_municipio["lon"] is None            # nunca fica o ponto exato
    assert pn.aplicar(reg, idx, pontos=False)["lat"] == -20.27112                   # camadas de prefixo (posição do IP): só o nome


def test_feicao_geojson_de_ei_ganha_o_centroide_e_a_de_pj_nao_muda():
    idx = _indice()
    ei = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-40.26223, -20.27112]},
          "properties": {"cnpj": CNPJ, "razao_social": "FULANO DE TAL", "municipio": "Vitória", "uf": "ES", "cep": "29010123"}}
    pj = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-46.6, -23.5]}, "properties": {"cnpj": "00000000000191", "razao_social": "X LTDA"}}
    out = pn.aplicar({"type": "FeatureCollection", "features": [ei, pj]}, idx)
    f = out["features"][0]
    assert [round(c, 4) for c in f["geometry"]["coordinates"]] == [CENTROIDE_VITORIA[1], CENTROIDE_VITORIA[0]]
    assert f["properties"]["razao_social"] == pn.rotulo(265061, CNPJ) and "cep" not in f["properties"]
    assert out["features"][1] is pj


def test_texto_json_de_resource_do_mcp():
    idx = _indice()
    texto = json.dumps({"asn": 265061, "name": "FULANO DE TAL"}, indent=2, ensure_ascii=False)
    novo = pn.na_saida(texto, idx)
    assert "FULANO" not in novo and novo.startswith("{\n  ")
    assert pn.na_saida("# markdown FULANO DE TAL", idx) == "# markdown FULANO DE TAL"
    assert pn.na_saida({"asn": 265061, "name": "FULANO DE TAL"}, idx)["name"] == pn.rotulo(265061, CNPJ)


def _gz(p: Path, doc) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(doc, f)


def test_indice_do_snapshot_junta_receita_cadastro_por_asn_e_outorgas(tmp_path):
    r = tmp_path / "normalized" / "2026-11-01" / "summary"
    _gz(r / "receita_cnpj.json.gz", {
        "empresa": {"11111111": {"nat": "2135"}, "22222222": {"nat": "2135"}, "33333333": {"nat": "2062", "razao": "X LTDA"}},
        "simples": {"22222222": {"mei": True}, "33333333": {"mei": False}},
        "estabelecimentos": {"22222222": [{"c": "22222222000100", "m": 1, "n": "Fibra Dois"}], "11111111": [{"c": "11111111000100", "m": 1}]}})
    _gz(r / "geo_orgs.json.gz", {"orgs": {
        "65001": {"cnpj": "11111111000100", "razao_social": "UM DA SILVA 52998224725", "name": "UM DA SILVA"},
        "65002": {"cnpj": "44444444000100", "razao_social": "QUATRO", "codigo_natureza_juridica": 2135, "nome_fantasia": "Quatro Net"},
        "65003": {"cnpj": "33333333000100", "razao_social": "X LTDA", "codigo_natureza_juridica": 2062}}})
    _gz(r / "anatel_scm.json.gz", {"by_cnpj": {"22222222000100": [{"razao_social": "DOIS DE TAL", "nome_fantasia": "Fibra Dois"}]}})
    _gz(r / "asn_names.json.gz", {"65001": "UM DA SILVA, BR", "65003": "X LTDA, BR"})
    idx = pn.indice_do_snapshot(tmp_path, "2026-11-01")
    assert set(idx.raizes) == {"11111111", "22222222", "44444444"}              # MEI pela opção do Simples, EI pela natureza; Ltda fora
    assert idx.raizes["22222222"] == "Fibra Dois" and idx.raizes["44444444"] == "Quatro Net" and idx.raizes["11111111"] is None
    assert idx.asn_cnpj == {65001: "11111111000100", 65002: "44444444000100"}
    assert idx.raiz_do_nome("UM DA SILVA, BR") == ("11111111", ", BR") and idx.raiz_do_nome("DOIS DE TAL")[0] == "22222222"
    assert idx.raiz_do_nome("X LTDA") is None
    assert not pn.indice_do_snapshot(tmp_path, "2026-12-01")                    # sem fontes: índice vazio, sem erro


def test_mascarar_snapshot_aplica_a_regra_em_todo_documento_e_so_com_indice(tmp_path):
    pub = tmp_path / "2026-11-01"
    (pub / "maps").mkdir(parents=True)
    (pub / "asns").mkdir()
    (pub / "asns" / "265061.json").write_text(json.dumps({"asn": 265061, "name": "FULANO DE TAL"}), encoding="utf-8")
    _gz(pub / "scm.json.gz", {"scms": [{"cnpj": CNPJ, "razao_social": "FULANO DE TAL", "lat": 1.0, "lon": 2.0, "municipio": "Vitória", "uf": "ES"}]})
    (pub / "maps" / "x.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8")
    assert mascarar_snapshot(pub, gravar=False) == {}                           # sem índice, só CPF: nada a fazer
    alterados = mascarar_snapshot(pub, indice=_indice())
    assert set(alterados) == {"asns/265061.json", "scm.json.gz"}
    assert "FULANO" not in (pub / "asns" / "265061.json").read_text(encoding="utf-8")
    with gzip.open(pub / "scm.json.gz", "rt", encoding="utf-8") as f:
        linha = json.load(f)["scms"][0]
    assert (round(linha["lat"], 4), round(linha["lon"], 4)) == CENTROIDE_VITORIA and linha["razao_social"] == pn.rotulo(265061, CNPJ)
    assert mascarar_snapshot(pub, indice=_indice()) == {}                       # idempotente
