# SPDX-License-Identifier: AGPL-3.0-or-later
"""T1 — Registro.br (nicbr-asn-blk), LACNIC delegated e nomes de ASN (RIPE)."""
import gzip
import httpx
import pytest
import respx

from sources.asn_names import collect as asn_names
from sources.lacnic_delegated import collect as lacnic_delegated
from sources.registro_br import collect as registro_br
from tests.sources.conftest import read_gz, volatile

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


# ── Registro.br ────────────────────────────────────────────────────────────

@respx.mock
def test_registro_br_formato_original_para_normalizado(base, log, fx, date_str):
    respx.get(registro_br.SOURCE_URL).respond(200, text=fx("registro_br", "nicbr-asn-blk.sample.txt").read_text(encoding="utf-8"))
    r = registro_br.run(date_str, base, compute_diff=False, log=log)
    assert r["total_asns"] == 5 and r["snapshot_date"] == date_str
    by = {a["asn"]: a for a in r["asns"]}
    assert set(by) == {174, 1251, 2635, 2914, 28573}
    a = by[174]
    assert a["name"].startswith("COGENT BRASIL") and a["cnpj"] == "29484413000170"
    assert a["prefixes_v4"] == [] and a["prefixes_v6"] == ["2804:5330::/32"]
    assert by[2635]["prefixes_v4"] == ["200.9.112.0/23"] and by[2635]["prefixes_v6"] == ["2801:80:1610::/48"]
    assert r["total_prefixes_v4"] == sum(len(x["prefixes_v4"]) for x in r["asns"])
    assert len(r["source_sha256"]) == 64


@respx.mock
def test_registro_br_grava_bruto_imutavel_e_normalizado(base, log, fx, date_str):
    txt = fx("registro_br", "nicbr-asn-blk.sample.txt").read_text(encoding="utf-8")
    respx.get(registro_br.SOURCE_URL).respond(200, text=txt)
    registro_br.run(date_str, base, False, log)
    raw = base / "raw" / date_str / "summary" / f"nicbr-asn-blk-{date_str}.txt.gz"
    norm = base / "normalized" / date_str / "summary" / "registro_br.json.gz"
    assert gzip.decompress(raw.read_bytes()).decode("utf-8") == txt
    assert read_gz(norm)["total_asns"] == 5


@respx.mock
def test_registro_br_segunda_execucao_e_deterministica(base, log, fx, date_str):
    respx.get(registro_br.SOURCE_URL).respond(200, text=fx("registro_br", "nicbr-asn-blk.sample.txt").read_text(encoding="utf-8"))
    a = volatile(registro_br.run(date_str, base, False, log))
    b = volatile(registro_br.run(date_str, base, False, log))
    assert a == b


@respx.mock
def test_registro_br_http_500_levanta(base, log, date_str):
    respx.get(registro_br.SOURCE_URL).respond(503)
    with pytest.raises(httpx.HTTPStatusError):
        registro_br.run(date_str, base, False, log)
    assert not (base / "normalized").exists() or not list((base / "normalized").rglob("*.json.gz"))


@respx.mock
def test_registro_br_diff_com_snapshot_anterior(base, log, fx, date_str):
    txt = fx("registro_br", "nicbr-asn-blk.sample.txt").read_text(encoding="utf-8")
    respx.get(registro_br.SOURCE_URL).respond(200, text=txt)
    registro_br.run("2026-09-13", base, False, log)
    respx.get(registro_br.SOURCE_URL).respond(200, text=txt + "AS65000|NOVA LTDA|11.111.111/0001-11|10.0.0.0/24\n")
    registro_br.run(date_str, base, True, log)
    diff = read_gz(base / "normalized" / date_str / "summary" / "registro_br_diff.json.gz")
    assert diff["snapshot_date_prev"] == "2026-09-13"
    assert diff["summary"]["added"] == 1 and diff["summary"]["removed"] == 0


@pytest.mark.parametrize("line, expected", [
    ("AS65000|Org|11.111.111/0001-11|10.0.0.0/24|2001:db8::/32", {"asn": 65000, "cnpj": "11111111000111"}),
    ("as65001|Org||10.0.0.0/24", {"asn": 65001, "cnpj": ""}),
    ("AS65002|Org|1|lixo|10.0.0.0/33|10.1.0.0/16", {"asn": 65002}),
])
def test_registro_br_parse_line(line, expected):
    r = registro_br._parse_line(line)
    for k, v in expected.items():
        assert r[k] == v


@pytest.mark.parametrize("line", ["", "# comentário", "XX123|a|b", "ASabc|a|b"])
def test_registro_br_parse_line_ignora_lixo(line):
    assert registro_br._parse_line(line) is None


# ── LACNIC delegated ───────────────────────────────────────────────────────

@respx.mock
def test_lacnic_extrai_asns_br_alocados(base, log, fx, date_str):
    respx.get(lacnic_delegated.SOURCE_URL).respond(200, text=fx("lacnic_delegated", "delegated-lacnic-extended.sample.txt").read_text())
    r = lacnic_delegated.run(date_str, base, log)
    assert r["br_asns"] == [1251, 1916, 2715, 2716, 4230]
    assert r["total_br_asns"] == 5
    assert read_gz(base / "normalized" / date_str / "summary" / "lacnic_delegated.json.gz")["br_asns"] == r["br_asns"]


@pytest.mark.parametrize("line, expected", [
    ("lacnic|BR|asn|100|1|20200101|allocated|1", [100]),
    ("lacnic|BR|asn|101|1|20200101|assigned|1", [101]),
    ("lacnic|BR|asn|102|1|20200101|available|1", []),
    ("lacnic|AR|asn|103|1|20200101|allocated|1", []),
    ("lacnic|BR|ipv4|104|1|20200101|allocated|1", []),
    ("arin|BR|asn|105|1|20200101|allocated|1", []),
    ("lacnic|BR|asn|abc|1|20200101|allocated|1", []),
    ("# comentario", []),
    ("lacnic|BR|asn", []),
])
def test_lacnic_parse_text_regras(line, expected):
    assert lacnic_delegated.parse_text(line) == expected


def test_lacnic_parse_text_ordena():
    t = "lacnic|BR|asn|300|1|d|allocated|x\nlacnic|BR|asn|5|1|d|allocated|x\n"
    assert lacnic_delegated.parse_text(t) == [5, 300]


# ── asn.txt (RIPE) ─────────────────────────────────────────────────────────

@respx.mock
def test_asn_names_normaliza(base, fx, date_str):
    respx.get(asn_names.URL).respond(200, text=fx("asn_names", "asn.sample.txt").read_text())
    n = asn_names.run(date_str, base)
    assert n == 11
    d = read_gz(base / "normalized" / date_str / "summary" / "asn_names.json.gz")
    assert d["28573"].startswith("AS28573 - Claro") and d["15169"] == "GOOGLE - Google LLC, US"
    assert all(isinstance(k, str) for k in d)


@respx.mock
def test_asn_names_guarda_o_bruto_comprimido(base, fx, date_str):
    """Em 2026-10-11 a origem serviu o asn.txt em outro formato; o bruto permite provar a causa depois."""
    import gzip

    texto = fx("asn_names", "asn.sample.txt").read_text()
    respx.get(asn_names.URL).respond(200, text=texto)
    asn_names.run(date_str, base)
    bruto = base / "raw" / date_str / "summary" / f"asn-names-{date_str}.txt.gz"
    assert gzip.open(bruto, "rt", encoding="utf-8").read() == texto


@respx.mock
def test_asn_names_ignora_linhas_invalidas(base, date_str):
    respx.get(asn_names.URL).respond(200, text="# comentário\n\n10 TEN-NET\nabc xyz\n11\n")
    assert asn_names.run(date_str, base) == 1


@respx.mock
def test_asn_names_http_erro(base, date_str):
    respx.get(asn_names.URL).respond(500)
    with pytest.raises(httpx.HTTPStatusError):
        asn_names.run(date_str, base)
