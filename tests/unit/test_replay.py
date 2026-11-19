# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — scripts/replay.py: comparação e classificação das diferenças (sem pipeline)."""
import gzip
import json

from scripts import replay


def _w(p, obj, gz=False):
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(obj).encode()
    p.write_bytes(gzip.compress(raw) if gz else raw)
    return p


def test_campos_volateis_sao_ignorados_em_qualquer_nivel(tmp_path):
    a = _w(tmp_path / "a/m.json", {"generated_at": "x", "n": 1, "d": {"pipeline_version": "1", "checksums": {"a": 1}}})
    b = _w(tmp_path / "b/m.json", {"generated_at": "y", "n": 1, "d": {"pipeline_version": "2", "checksums": {"b": 2}}})
    assert replay.compare_file("m.json", a, b, [])["classe"] == "igual"


def test_so_ordem_de_lista_e_classe_propria(tmp_path):
    a = _w(tmp_path / "a/x.json", {"l": [{"k": 1}, {"k": 2}]})
    b = _w(tmp_path / "b/x.json", {"l": [{"k": 2}, {"k": 1}]})
    r = replay.compare_file("x.json", a, b, [])
    assert r["classe"] == "ordem"


def test_conteudo_diferente_e_nova_com_caminho(tmp_path):
    a = _w(tmp_path / "a/x.json.gz", {"a": {"b": [1, 2]}}, gz=True)
    b = _w(tmp_path / "b/x.json.gz", {"a": {"b": [1, 3]}}, gz=True)
    r = replay.compare_file("x.json.gz", a, b, [])
    assert r["classe"] == "nova" and r["caminhos"] == ["/a/b/1"]


def test_explicada_por_glob_e_por_caminhos_regex(tmp_path):
    a = _w(tmp_path / "a/asns/index.json", [{"asn": 1, "sici_acessos": 5}])
    b = _w(tmp_path / "b/asns/index.json", [{"asn": 1}])
    exp = [{"arquivo": "asns/index.json", "tipo": "conteudo", "caminhos_regex": r"^/\d+/sici_", "motivo": "ok"}]
    assert replay.compare_file("asns/index.json", a, b, exp)["classe"] == "explicada"
    # outra diferença no mesmo arquivo NÃO é coberta pela entrada
    c = _w(tmp_path / "b2/asns/index.json", [{"asn": 2}])
    assert replay.compare_file("asns/index.json", a, c, exp)["classe"] == "nova"


def test_arquivo_so_de_um_lado(tmp_path):
    a = _w(tmp_path / "a/x.json", {})
    assert replay.compare_file("x.json", a, None, [])["tipo"] == "so_original"
    assert replay.compare_file("x.json", None, a, [])["tipo"] == "so_replay"
    exp = [{"arquivo": "x.json", "tipo": "so_replay", "motivo": "m"}]
    assert replay.compare_file("x.json", None, a, exp)["classe"] == "explicada"


def test_compare_trees_conta_e_nao_compara_artefatos_copiados(tmp_path):
    for side, val in (("o", 1), ("r", 2)):
        _w(tmp_path / side / "igual.json", {"v": 1})
        _w(tmp_path / side / "muda.json", {"v": val})
        _w(tmp_path / side / "rpki" / "vrp_list.json.gz", {"v": val}, gz=True)
    rep = replay.compare_trees(tmp_path / "o", tmp_path / "r", expected=[])
    assert rep["contagem"] == {"igual": 1, "nova": 1, "copiado": 1}
