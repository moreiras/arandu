# SPDX-License-Identifier: AGPL-3.0-or-later
"""T0 — aritmética de prefixos, geografia e normalização (funções puras)."""
import ipaddress

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from api.geo import haversine_km
from api.store import _collapsed_nets, _first_ip, _normalize_city, _slash20_blocks, _space_gap_units
from products.sici.build import (
    DIVERGENCIA_ALTA,
    DIVERGENCIA_BAIXA,
    DIVERGENCIA_MIN_ACESSOS,
    DIVERGENCIA_MIN_USERS,
    _classify_divergencia,
)
from publish.snapshot_builder import (
    _prefix_to_16_density,
    _slash24_bitset,
    _slash24_set,
    compute_density,
)

N = ipaddress.ip_network


# ── haversine_km ───────────────────────────────────────────────────────────

def test_haversine_mesmo_ponto_e_zero():
    assert haversine_km(-23.5, -46.6, -23.5, -46.6) == 0


def test_haversine_sao_paulo_rio():
    assert haversine_km(-23.5505, -46.6333, -22.9068, -43.1729) == pytest.approx(360, abs=5)


def test_haversine_um_grau_de_latitude():
    assert haversine_km(0, 0, 1, 0) == pytest.approx(111.19, abs=0.1)


def test_haversine_antipodas():
    assert haversine_km(0, 0, 0, 180) == pytest.approx(20015, abs=5)


@given(st.floats(-90, 90), st.floats(-180, 180), st.floats(-90, 90), st.floats(-180, 180))
def test_haversine_simetrica_e_nao_negativa(a, b, c, d):
    ab = haversine_km(a, b, c, d)
    assert ab >= 0
    assert ab == pytest.approx(haversine_km(c, d, a, b))


# ── _normalize_city ────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw, expected", [
    ("São Paulo", "SAO PAULO"),
    ("Vitória", "VITORIA"),
    ("Brasília", "BRASILIA"),
    ("FOZ DO IGUAÇU", "FOZ DO IGUACU"),
    ("  porto alegre", "  PORTO ALEGRE"),
    ("", ""),
])
def test_normalize_city(raw, expected):
    assert _normalize_city(raw) == expected


# ── _slash20_blocks / _first_ip ────────────────────────────────────────────

@pytest.mark.parametrize("prefix, expected", [
    ("200.160.0.0/20", ["200.160.0.0/20"]),
    ("200.160.5.0/24", ["200.160.0.0/20"]),
    ("200.160.15.255/32", ["200.160.0.0/20"]),
    ("200.160.0.0/19", ["200.160.0.0/20", "200.160.16.0/20"]),
    ("10.0.0.0/7", []),
])
def test_slash20_blocks(prefix, expected):
    assert _slash20_blocks(prefix) == expected


def test_slash20_blocks_expande_slash16():
    assert len(_slash20_blocks("200.160.0.0/16")) == 16


def test_first_ip():
    assert _first_ip("200.160.5.0/24") == "200.160.5.0"
    assert _first_ip("2001:db8::/32") == "2001:db8::"


# ── _collapsed_nets / _space_gap_units ─────────────────────────────────────

def test_collapsed_nets_agrupa_adjacentes():
    assert _collapsed_nets(["10.0.0.0/25", "10.0.0.128/25"], 4) == [N("10.0.0.0/24")]


def test_collapsed_nets_separa_familias_e_ignora_lixo():
    assert _collapsed_nets(["10.0.0.0/24", "2001:db8::/32", "lixo"], 4) == [N("10.0.0.0/24")]
    assert _collapsed_nets(["10.0.0.0/24", "2001:db8::/32"], 6) == [N("2001:db8::/32")]


def test_collapsed_nets_vazio():
    assert _collapsed_nets([], 4) == []
    assert _collapsed_nets(None, 4) == []


def test_collapsed_nets_remove_sobreposicao():
    assert _collapsed_nets(["10.0.0.0/16", "10.0.1.0/24"], 4) == [N("10.0.0.0/16")]


def test_space_gap_tudo_anunciado_e_zero():
    assert _space_gap_units([N("10.0.0.0/22")], [N("10.0.0.0/22")], 24) == 0


def test_space_gap_nada_anunciado():
    assert _space_gap_units([N("10.0.0.0/22")], [], 24) == 4


def test_space_gap_parcial():
    assert _space_gap_units([N("10.0.0.0/22")], [N("10.0.0.0/23")], 24) == 2


def test_space_gap_sem_alocado():
    assert _space_gap_units([], [N("10.0.0.0/24")], 24) == 0


def test_space_gap_ignora_outra_familia():
    assert _space_gap_units([N("10.0.0.0/24")], [N("2001:db8::/32")], 24) == 1


# ── densidade /16 e conjuntos de /24 ───────────────────────────────────────

@pytest.mark.parametrize("prefix, expected", [
    ("10.0.0.0/24", [(10 * 256, 1)]),
    ("10.1.2.0/25", [(10 * 256 + 1, 1)]),
    ("10.1.0.0/16", [(10 * 256 + 1, 1 << 8)]),
    ("10.1.0.0/17", [(10 * 256 + 1, 128)]),
    ("10.0.0.0/15", [(10 * 256, 256), (10 * 256 + 1, 256)]),
    ("2001:db8::/32", []),
    ("lixo", []),
])
def test_prefix_to_16_density(prefix, expected):
    assert _prefix_to_16_density(prefix) == expected


def test_compute_density_satura_em_256():
    d = compute_density(["10.0.0.0/16", "10.0.0.0/16"])
    assert d[10 * 256] == 256
    assert len(d) == 65536


def test_slash24_set():
    s = _slash24_set(["10.0.0.0/23", "10.0.5.0/24", "2001:db8::/32", "lixo", "4.0.0.0/7"])
    assert s == {(10 << 16), (10 << 16) + 1, (10 << 16) + 5}


def test_slash24_set_e_bitset_concordam():
    prefixes = ["10.0.0.0/22", "192.0.2.0/24", "198.51.100.0/23"]
    bits = _slash24_bitset(prefixes)
    s = _slash24_set(prefixes)
    for idx in s:
        assert bits[idx >> 3] >> (idx & 7) & 1
    assert sum(bin(b).count("1") for b in bits) == len(s)


@settings(max_examples=60, deadline=None)
@given(st.lists(st.tuples(st.integers(0, 2**24 - 1), st.integers(8, 24)), min_size=1, max_size=8))
def test_propriedade_cobertura_slash24_nao_perde_espaco(items):
    """Agregação não perde espaço: todo /24 de cada prefixo está no conjunto coberto."""
    prefixes = [str(ipaddress.ip_network((base << 8, plen), strict=False)) for base, plen in items]
    covered = _slash24_set(prefixes)
    for p in prefixes:
        n = N(p)
        first = int(n.network_address) >> 8
        assert all(first + i in covered for i in range(1 << (24 - n.prefixlen)))


@given(st.integers(0, 2**32 - 1), st.integers(0, 32))
def test_propriedade_prefixo_roundtrip(addr, plen):
    net = ipaddress.ip_network((addr, plen), strict=False)
    assert ipaddress.ip_network(str(net)) == net
    assert net.prefixlen == plen


@given(st.integers(0, 2**128 - 1), st.integers(0, 128))
def test_propriedade_prefixo_ipv6_roundtrip(addr, plen):
    net = ipaddress.ip_network((addr, plen), strict=False)
    assert ipaddress.ip_network(str(net)) == net


# ── _classify_divergencia ──────────────────────────────────────────────────

def test_divergencia_compartilhado_nao_comparavel():
    assert _classify_divergencia(10000, 5000, True) == {
        "classificacao": "nao_comparavel", "motivo": "acessos_compartilhados"}


@pytest.mark.parametrize("users, acessos", [
    (None, 1000), (0, 1000),
    (DIVERGENCIA_MIN_USERS - 1, 1000),
    (1000, DIVERGENCIA_MIN_ACESSOS - 1),
])
def test_divergencia_sem_dados(users, acessos):
    assert _classify_divergencia(users, acessos, False) == {"classificacao": "sem_dados"}


@pytest.mark.parametrize("users, acessos, expected", [
    (500, 1000, "apnic_baixo"),
    (4000, 1000, "normal"),
    (1000, 1000, "normal"),
    (20000, 1000, "normal"),
    (25000, 1000, "apnic_alto"),
])
def test_divergencia_classes(users, acessos, expected):
    assert _classify_divergencia(users, acessos, False)["classificacao"] == expected


def test_divergencia_campos():
    r = _classify_divergencia(4000, 1000, False)
    assert r["razao"] == 4.0 and r["apnic_users"] == 4000 and r["acessos_sici"] == 1000
    assert r["faixa_normal"] == [DIVERGENCIA_BAIXA, DIVERGENCIA_ALTA]
