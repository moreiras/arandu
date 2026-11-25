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


def test_replay_expected_bem_formado():
    """Toda entrada tem arquivo, tipo válido, motivo e regex que compila; sem travessão na redação."""
    import re

    exp = replay.load_expected()
    assert exp, "replay_expected.json não carregou"
    for e in exp:
        assert e.get("arquivo") and e.get("motivo"), e
        assert e.get("tipo") in ("conteudo", "ordem", "so_original", "so_replay"), e
        if e.get("caminhos_regex"):
            re.compile(e["caminhos_regex"])
        assert "—" not in e["motivo"] and "–" not in e["motivo"], e["arquivo"]


def test_diferencas_dos_pacotes_obint_sao_explicadas_e_o_resto_continua_nova(tmp_path):
    """Fixture reduzida do replay de 2026-11-22: só os caminhos que cada pacote muda casam; outro campo do mesmo arquivo segue "nova"."""
    exp = replay.load_expected()
    casos = [
        ("summary.json", {"ixps_ok": 1, "ixps_partial": 0, "ixps_failed": ["a"]}, {"ixps_ok": 0, "ixps_partial": 1, "ixps_failed": []}),
        ("ixps/sp.json", {"asn_origin_union_count": 10}, {"asn_origin_union_count": 12}),
        ("rs_policy/linhas.json.gz", {"x": 1}, {"x": 1, "cobertura_total_nivel2": {"n": 1}}),
        ("external-ixps/decix-rj.json", {"member_count": 16, "portas": 16}, {"member_count": 14, "redes": 14, "portas": 16}),
        ("regulatorio/satelites.json.gz", {"ngeo": [{"cnpj": "1"}, {"cnpj": "1"}], "resumo": {"ngeo": 2}},
         {"ngeo": [{"cnpj": "1"}], "resumo": {"ngeo": 1, "ngeo_sistemas": 1}, "ngeo_sistemas": [{}]}),
        ("qualidade/rqual.json.gz", {"prestadoras": [{"raizes": ["1"]}]}, {"prestadoras": [{"raizes": ["1", "2"], "base_casamento": "x"}]}),
        ("mercado_grupos.json.gz", {"ufs": {"SP": {"hhi_cnpj": 1}}}, {"ufs": {"SP": {"hhi_cnpj": 1, "avisos_cnpj": [], "n_cnpjs": 3}}}),
        ("seguranca/asns.json.gz", {"brasil": {"rov": {"x": 1}}}, {"brasil": {"rov": {"x": 1, "avisos": [], "peso_top1": 0.2}}}),
        ("asns/1.json", {"asn": 1, "relacoes": {"provedores": []}}, {"asn": 1}),
        ("ipv4/mercado.json.gz", {"limites": "a"}, {"limites": "b"}),
    ]
    for rel, a, b in casos:
        pa, pb = _w(tmp_path / "a" / rel, a, gz=rel.endswith(".gz")), _w(tmp_path / "b" / rel, b, gz=rel.endswith(".gz"))
        r = replay.compare_file(rel, pa, pb, exp)
        assert r["classe"] == "explicada", (rel, r)
    for rel, a, b in [
        ("summary.json", {"ixps_ok": 1, "n_asns": 5}, {"ixps_ok": 0, "n_asns": 6}),
        ("ixps/sp.json", {"asn_origin_union_count": 1, "asn_direct_union_count": 3}, {"asn_origin_union_count": 2, "asn_direct_union_count": 4}),
        ("asns/1.json", {"asn": 1, "nome": "a", "relacoes": {}}, {"asn": 1, "nome": "b"}),
        ("seguranca/asns.json.gz", {"brasil": {"rov": {"pct": 1}}}, {"brasil": {"rov": {"pct": 2, "avisos": []}}}),
    ]:
        pa, pb = _w(tmp_path / "a2" / rel, a, gz=rel.endswith(".gz")), _w(tmp_path / "b2" / rel, b, gz=rel.endswith(".gz"))
        assert replay.compare_file(rel, pa, pb, exp)["classe"] == "nova", rel
    pa = _w(tmp_path / "a3/omissao_sici.json.gz", {}, gz=True)
    assert replay.compare_file("omissao_sici.json.gz", pa, None, exp)["classe"] == "explicada"
    assert replay.compare_file("outro.json.gz", pa, None, exp)["classe"] == "nova"
