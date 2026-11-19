# SPDX-License-Identifier: AGPL-3.0-or-later
"""T0 — parser BGP (`products/bgp_routes/build.py`): os formatos de linha dos LGs do IX.br."""
import pytest

from products.bgp_routes.build import (
    _extract_aspath,
    _extract_prefix,
    _extract_status,
    _is_header_line,
    _is_route_line,
    _path_slice,
    compute_relationships,
    parse_bgp_output,
)

PATH_COL = 60
HEADER = (
    "   Network          Next Hop            Metric LocPrf Weight Path"
)
HEADER_COL = HEADER.rfind("Path")


def _line(left: str, path: str, metric: str = "10", weight: str = "0") -> str:
    """Linha de rota com o AS_PATH exatamente na coluna 'Path' do cabeçalho."""
    body = left.ljust(HEADER_COL - len(weight) - 1 - len(metric) - 1 - 8) + metric.rjust(len(metric))
    body = body.ljust(HEADER_COL - len(weight) - 1)
    return f"{body}{weight} {path}"


PREAMBLE = """BGP table version is 123, local router ID is 187.16.216.1, vrf id 0
Default local pref 100, local AS 26162
Status codes:  s suppressed, d damped, h history, * valid, > best, = multipath,
               i internal, r RIB-failure, S Stale, R Removed
Nexthop codes: @NNN nexthop's vrf id, < announce-nh-self
Origin codes:  i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found
"""


def table(*rows: str) -> str:
    return PREAMBLE + "\n" + HEADER + "\n" + "\n".join(rows) + "\n\nDisplayed 3 routes and 3 total paths\n"


# ── Formato IPv4 de linha única ────────────────────────────────────────────

def test_ipv4_linha_unica():
    routes = parse_bgp_output(table(_line("*> 1.0.0.0/24       200.192.108.14", "16735 22548 i")))
    assert routes == [
        {"prefix": "1.0.0.0/24", "status": "*>", "aspath": [16735, 22548], "origin": "i", "nexthop": ""}
    ]


def test_metric_locpref_weight_nao_viram_asn():
    r = parse_bgp_output(table(_line("*> 10.0.0.0/8       200.192.108.14", "65000 i", metric="200", weight="32768")))
    assert r[0]["aspath"] == [65000]


def test_continuation_herda_prefixo():
    rows = [
        _line("*> 1.0.4.0/22       200.192.108.14", "16735 4637 i"),
        _line("*                   200.192.108.20", "52925 i"),
    ]
    r = parse_bgp_output(table(*rows))
    assert [x["prefix"] for x in r] == ["1.0.4.0/22", "1.0.4.0/22"]
    assert [x["aspath"] for x in r] == [[16735, 4637], [52925]]
    assert [x["status"] for x in r] == ["*>", "*"]


def test_varias_rotas_prefixos_diferentes():
    rows = [
        _line("*> 1.0.0.0/24       200.192.108.14", "16735 22548 i"),
        _line("*> 2.0.0.0/16       200.192.108.14", "100 200 300 i"),
    ]
    r = parse_bgp_output(table(*rows))
    assert [x["prefix"] for x in r] == ["1.0.0.0/24", "2.0.0.0/16"]
    assert r[1]["aspath"] == [100, 200, 300]


@pytest.mark.parametrize("origin", ["i", "e", "?"])
def test_codigos_de_origem(origin):
    r = parse_bgp_output(table(_line("*> 1.0.0.0/24       200.192.108.14", f"65001 {origin}")))
    assert r[0]["origin"] == origin


def test_as_path_com_prepend():
    r = parse_bgp_output(table(_line("*> 1.0.0.0/24       200.192.108.14", "65001 65001 65001 65002 i")))
    assert r[0]["aspath"] == [65001, 65001, 65001, 65002]


# ── IPv6 em 2 e 3 linhas ───────────────────────────────────────────────────

def test_ipv6_duas_linhas():
    rows = [
        "*  2001:500:3::/48  2001:12f8:0:11::14",
        " " * (HEADER_COL - 2) + "0 16735 20144 i",
    ]
    r = parse_bgp_output(table(*rows))
    assert r == [{"prefix": "2001:500:3::/48", "status": "*", "aspath": [16735, 20144], "origin": "i", "nexthop": ""}]


def test_ipv6_tres_linhas():
    rows = [
        "*  2001:500:3::/48",
        "   2001:12f8:0:11::14",
        " " * (HEADER_COL - 2) + "0 16735 20144 i",
    ]
    r = parse_bgp_output(table(*rows))
    assert len(r) == 1
    assert r[0]["prefix"] == "2001:500:3::/48"
    assert r[0]["aspath"] == [16735, 20144]


def test_ipv6_continuation():
    rows = [
        "*> 2001:db8::/32   2001:12f8:0:11::14",
        " " * (HEADER_COL - 2) + "0 64500 i",
        "*                  2001:12f8:0:11::15",
        " " * (HEADER_COL - 2) + "0 64501 64502 i",
    ]
    r = parse_bgp_output(table(*rows))
    assert [x["prefix"] for x in r] == ["2001:db8::/32", "2001:db8::/32"]
    assert [x["aspath"] for x in r] == [[64500], [64501, 64502]]


# ── FRR 8.x: código RPKI antes dos flags ───────────────────────────────────

@pytest.mark.parametrize("code", ["V", "N", "I"])
def test_frr8_codigo_rpki(code):
    r = parse_bgp_output(table(_line(f"{code}*>i1.0.0.0/24    200.192.108.14", "16735 22548 i")))
    assert len(r) == 1
    assert r[0]["prefix"] == "1.0.0.0/24"
    assert r[0]["aspath"] == [16735, 22548]


# ── Cabeçalhos e lixo ──────────────────────────────────────────────────────

def test_texto_vazio():
    assert parse_bgp_output("") == []


def test_apenas_cabecalho():
    assert parse_bgp_output(PREAMBLE + HEADER + "\n") == []


def test_linha_sem_as_path_e_descartada_no_fim():
    assert parse_bgp_output(table("*> 1.0.0.0/24       200.192.108.14")) == []


def test_ordem_preservada():
    prefixes = [f"10.{i}.0.0/16" for i in range(5)]
    rows = [_line(f"*> {p}       200.192.108.14", "65000 i") for p in prefixes]
    assert [x["prefix"] for x in parse_bgp_output(table(*rows))] == prefixes


# ── Funções auxiliares ─────────────────────────────────────────────────────

@pytest.mark.parametrize("line, expected", [
    ("*> 1.0.0.0/24 200.1.1.1", "1.0.0.0/24"),
    ("V*>i1.0.0.0/24 200.1.1.1", "1.0.0.0/24"),
    ("*  2001:500:3::/48  2001:12f8::1", "2001:500:3::/48"),
    ("*> 192.0.2.0/24", "192.0.2.0/24"),
    ("sem prefixo aqui", None),
    ("", None),
])
def test_extract_prefix(line, expected):
    assert _extract_prefix(line) == expected


@pytest.mark.parametrize("line, expected", [
    ("0 16735 22548 i", ([0, 16735, 22548], "i")),
    ("65000 e", ([65000], "e")),
    ("1 2 3 ?", ([1, 2, 3], "?")),
    ("sem caminho", None),
    ("65000", None),
])
def test_extract_aspath(line, expected):
    assert _extract_aspath(line) == expected


@pytest.mark.parametrize("line, expected", [
    ("*> 1.0.0.0/24", "*>"),
    ("*  1.0.0.0/24", "*"),
    ("*>i1.0.0.0/24", "*>i"),
    ("1.0.0.0/24", ""),
])
def test_extract_status(line, expected):
    assert _extract_status(line) == expected


@pytest.mark.parametrize("stripped, expected", [
    ("*> 1.0.0.0/24", True),
    ("*  1.0.0.0/24", True),
    ("V*>i1.0.0.0/24", True),
    ("N*>i1.0.0.0/24", True),
    ("0 16735 i", False),
    ("", False),
])
def test_is_route_line(stripped, expected):
    assert _is_route_line(stripped) is expected


@pytest.mark.parametrize("line, expected", [
    ("", True),
    ("BGP table version is 123", True),
    ("Default local pref 100, local AS 26162", True),
    ("Status codes:  s suppressed", True),
    ("   Network          Next Hop            Metric LocPrf Weight Path", True),
    ("Displayed 3 routes and 3 total paths", True),
    ("*> 1.0.0.0/24 200.1.1.1 0 1 i", False),
])
def test_is_header_line(line, expected):
    assert _is_header_line(line) is expected


def test_path_slice_sem_coluna_devolve_linha_inteira():
    assert _path_slice("abc def", None) == "abc def"


def test_path_slice_recua_ate_inicio_da_palavra():
    assert _path_slice("aaa 12345 bbb", 6) == "12345 bbb"


def test_path_slice_linha_curta():
    assert _path_slice("abc", 10) == "abc"


# ── compute_relationships ──────────────────────────────────────────────────

def test_relationships_basico():
    routes = [
        {"prefix": "a", "aspath": [1, 2, 3]},
        {"prefix": "b", "aspath": [1, 4]},
        {"prefix": "c", "aspath": [5, 6]},
    ]
    rel = compute_relationships(routes)
    assert rel["asn_direct"] == [1, 5]
    assert rel["asn_origin"] == [3, 4, 6]
    assert rel["asn_relate"] == [(1, 3), (1, 4), (5, 6)]
    assert rel["asn_stub"] == [5]   # só o 5 tem uma única origem


def test_relationships_vazio_e_aspath_vazio():
    assert compute_relationships([]) == {"asn_direct": [], "asn_origin": [], "asn_relate": [], "asn_stub": []}
    assert compute_relationships([{"prefix": "a", "aspath": []}])["asn_direct"] == []


def test_relationships_origem_propria():
    rel = compute_relationships([{"prefix": "a", "aspath": [7]}])
    assert rel["asn_direct"] == [7] and rel["asn_origin"] == [7] and rel["asn_stub"] == [7]


def test_linha_sem_as_path_mantem_rota_pendente():
    """Linha intermediária sem AS_PATH (ex.: nexthop do formato de 3 linhas) não descarta a rota."""
    rows = [
        "*  2001:500:3::/48  2001:12f8:0:11::14",
        "linha-sem-caminho",
        " " * (HEADER_COL - 2) + "0 16735 20144 i",
    ]
    assert [r["aspath"] for r in parse_bgp_output(table(*rows))] == [[16735, 20144]]


def test_linha_solta_sem_rota_pendente_e_ignorada():
    assert parse_bgp_output(table("linha-que-nao-e-rota")) == []


def test_rota_antes_de_qualquer_prefixo_e_ignorada():
    assert parse_bgp_output(table(_line("*>                  200.192.108.14", "65000 i"))) == []
