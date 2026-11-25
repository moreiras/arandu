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
        ("asns/1.json", {"asn": 1, "relacoes": {"provedores": []}}, {"asn": 1}),  # `relacoes` ausente no replay já não é limitação: agora é recomposto
        ("seguranca/asns.json.gz", {"brasil": {"rov": {"pct": 1}}}, {"brasil": {"rov": {"pct": 2, "avisos": []}}}),
    ]:
        pa, pb = _w(tmp_path / "a2" / rel, a, gz=rel.endswith(".gz")), _w(tmp_path / "b2" / rel, b, gz=rel.endswith(".gz"))
        assert replay.compare_file(rel, pa, pb, exp)["classe"] == "nova", rel
    pa = _w(tmp_path / "a3/omissao_sici.json.gz", {}, gz=True)
    assert replay.compare_file("omissao_sici.json.gz", pa, None, exp)["classe"] == "explicada"
    assert replay.compare_file("outro.json.gz", pa, None, exp)["classe"] == "nova"


# ── recomposição do fragmento `relacoes` ───────────────────────────────────

DATA = "2026-11-22"
REL = {64500: {"provedores": [{"asn": 174, "nivel": "confirmado", "afi": ["v6", "v4"]}], "visibilidade": 0.9},
       64501: {"provedores": [], "clientes": [64502]}}


def _frag(base):
    from core import compose

    return compose.caminho(base, DATA, "relacoes")


def _publicado(src, como="dir"):
    import zipfile

    docs = {"index.json": [{"asn": 64500}, {"asn": 64501}, {"asn": 64502}],
            "64502.json": {"asn": 64502, "name": "sem relações"},
            "64501.json": {"asn": 64501, "relacoes": REL[64501]},
            "64500.json": {"asn": 64500, "name": "x", "relacoes": REL[64500]}}
    pub = src / "published" / DATA
    pub.mkdir(parents=True)
    if como == "dir":
        for nome, d in docs.items():
            _w(pub / "asns" / nome, d)
    else:
        with zipfile.ZipFile(pub / "asns.zip", "w") as z:
            for nome, d in docs.items():
                z.writestr(nome, json.dumps(d))


def test_relacoes_copia_o_fragmento_do_build_original(tmp_path):
    from core import compose

    src, work = tmp_path / "data", tmp_path / "work"
    with compose.gravar_fragmento(src, DATA, "relacoes") as w:
        w.escrever(64500, {"relacoes": {"x": 1}})
    _publicado(src)
    assert replay.restaurar_relacoes(src, work, DATA) == "copiado"
    assert _frag(work).read_bytes() == _frag(src).read_bytes()
    assert replay.restaurar_relacoes(src, work, DATA) == "presente"


def test_relacoes_recompoe_dos_documentos_publicados(tmp_path):
    from core import compose

    for como in ("dir", "zip"):
        src, work = tmp_path / como / "data", tmp_path / como / "work"
        _publicado(src, como)
        antes = {p: p.stat().st_mtime_ns for p in (src / "published").rglob("*") if p.is_file()}
        assert replay.restaurar_relacoes(src, work, DATA) == "recomposto"
        linhas = list(compose.ler_fragmento(_frag(work)))
        assert linhas == [(64500, {"relacoes": REL[64500]}), (64501, {"relacoes": REL[64501]})]   # ASN crescente, sem o doc sem `relacoes`
        with gzip.open(_frag(work), "rt", encoding="utf-8") as f:
            assert json.loads(f.readline()) == {"asn": 64500, "d": {"relacoes": REL[64500]}}
        assert not _frag(src).exists()                                                           # o data/ de origem não é tocado
        assert antes == {p: p.stat().st_mtime_ns for p in (src / "published").rglob("*") if p.is_file()}


def test_relacoes_refeitas_depois_que_o_base_apaga_os_derivados(tmp_path):
    from core import compose

    src, work = tmp_path / "data", tmp_path / "work"
    _publicado(src)
    replay.restaurar_relacoes(src, work, DATA)
    with compose.gravar_fragmento(work, DATA, "base") as w:      # metricas_ixp_asn regrava o base
        w.escrever(64500, {"asn": 64500})
    assert not _frag(work).exists()
    assert replay.restaurar_relacoes(src, work, DATA) == "recomposto"
    docs = dict(compose.iterar_documentos(work, DATA, ("base", "relacoes")))
    assert docs[64500] == {"asn": 64500, "relacoes": REL[64500]}


def test_relacoes_publicado_sem_o_campo_nao_deixa_fragmento(tmp_path):
    src, work = tmp_path / "data", tmp_path / "work"
    pub = src / "published" / DATA
    _w(pub / "asns" / "1.json", {"asn": 1})
    assert replay.restaurar_relacoes(src, work, DATA) is None
    assert not _frag(work).exists()
