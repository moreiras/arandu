# SPDX-License-Identifier: AGPL-3.0-or-later
"""T0 — esquema e validador do catálogo, sobre catálogos mínimos em tmp_path."""
from pathlib import Path

import pytest
import yaml

from core.catalog.loader import load_catalog, nao_verificados, pattern_matches, validate

BRUTA = {
    "id": "fonte_a", "nome": "Fonte A", "tipo": "bruta", "ativa": True, "modulo": "collector.a",
    "publicavel": True, "descricao": "x",
    "origem": {"url": "https://exemplo", "formato": "json", "licenca": "CC0", "uso_comercial": "permitido"},
    "cadencia": {"fonte_atualiza": "diaria", "coleta": "semanal", "coleta_atual": "semanal",
                 "frescor_maximo": "8d"},
    "politica_falha": "critica", "saidas": {"normalizado": ["a.json.gz"]}, "chaves": ["asn"],
    "campos": [{"nome": "asn", "tipo": "int", "significado": "Número do AS."}], "limites": "nenhum",
}
DERIVADA = {**BRUTA, "id": "fonte_d", "tipo": "derivada", "entradas": ["fonte_a"], "modulo": "enrich.d"}
DERIVADA.pop("origem")
PRODUTO = {"id": "prod", "nome": "P", "descricao": "d", "entradas": [{"source": "fonte_a"}],
           "saidas": {"publicado": ["p.json.gz"]}}


def _escreve(tmp: Path, fontes=(), produtos=()) -> Path:
    for kind, items in (("sources", fontes), ("products", produtos)):
        (tmp / kind).mkdir(parents=True, exist_ok=True)
        for it in items:
            (tmp / kind / f"{it['id']}.yaml").write_text(yaml.safe_dump(it, allow_unicode=True))
    return tmp


def test_catalogo_minimo_valido(tmp_path):
    cat = load_catalog(_escreve(tmp_path, [BRUTA, DERIVADA], [PRODUTO]))
    assert validate(cat) == []


def test_campo_obrigatorio_ausente(tmp_path):
    ruim = {k: v for k, v in BRUTA.items() if k != "publicavel"}
    erros = validate(load_catalog(_escreve(tmp_path, [ruim])))
    assert any("publicavel" in e for e in erros)


def test_extra_proibido_e_chave_fora_do_vocabulario(tmp_path):
    erros = validate(load_catalog(_escreve(tmp_path, [{**BRUTA, "chaves": ["banana"], "foo": 1}])))
    assert any("banana" in e for e in erros) and any("foo" in e for e in erros)


def test_entrada_inexistente_e_ciclo(tmp_path):
    a = {**DERIVADA, "id": "fonte_x", "entradas": ["fonte_y"]}
    b = {**DERIVADA, "id": "fonte_y", "entradas": ["fonte_x"]}
    erros = validate(load_catalog(_escreve(tmp_path, [a, b, {**DERIVADA, "id": "fonte_z", "entradas": ["nao_existe"]}])))
    assert any("ciclo" in e for e in erros) and any("nao_existe" in e for e in erros)


def test_id_difere_do_arquivo(tmp_path):
    _escreve(tmp_path, [BRUTA])
    (tmp_path / "sources" / "fonte_a.yaml").rename(tmp_path / "sources" / "outro.yaml")
    assert any("difere" in e for e in validate(load_catalog(tmp_path)))


def test_nao_verificado_exige_pendencia(tmp_path):
    f = {**BRUTA, "origem": {**BRUTA["origem"], "uso_comercial": "nao_verificado"}}
    cat = load_catalog(_escreve(tmp_path, [f]))
    assert nao_verificados(cat.sources["fonte_a"]) == 1
    assert any("pendencias" in e for e in validate(cat))
    f["pendencias"] = ["termos de uso não localizados"]
    assert validate(load_catalog(_escreve(tmp_path / "ok", [f]))) == []


def test_publicavel_false_nao_publica(tmp_path):
    f = {**BRUTA, "publicavel": False, "saidas": {"normalizado": ["a"], "publicado": ["x.json"]}}
    assert any("publicavel=false" in e for e in validate(load_catalog(_escreve(tmp_path, [f]))))


def test_curada_exige_arquivo(tmp_path):
    c = {**BRUTA, "tipo": "curada", "origem": None, "modulo": None}
    assert any("arquivo" in e for e in validate(load_catalog(_escreve(tmp_path, [c]))))


@pytest.mark.parametrize("pad,caminho,ok", [
    ("asns/{asn}.json", "asns/65000.json", True),
    ("asns/{asn}.json", "asns/sub/65000.json", False),
    ("maps/*.geojson", "maps/asns.geojson", True),
    ("summary.json", "summary.json", True),
    ("summary.json", "summaryXjson", False),
])
def test_pattern_matches(pad, caminho, ok):
    assert pattern_matches(pad, caminho) is ok
