# SPDX-License-Identifier: AGPL-3.0-or-later
"""Identificação do cliente e allowlist (api/auth/deps.py)."""
import pytest

from api.auth.deps import ip_in_allowlist, normalize_ip

ALLOW = ["127.0.0.1", "::1", "10.0.0.0/8", "203.0.113.128/25", "2001:db8:a110::/48"]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("203.0.113.129", "203.0.113.129"),
        (" 203.0.113.129 ", "203.0.113.129"),
        ("203.0.113.129, 10.0.0.1", "203.0.113.129"),
        ("203.0.113.129:5555", "203.0.113.129"),
        ("::ffff:203.0.113.129", "203.0.113.129"),
        ("[2001:db8:a110::1]:443", "2001:db8:a110::1"),
        ("2001:DB8:A110:0::1", "2001:db8:a110::1"),
        ("", ""),
        ("lixo", "lixo"),
    ],
)
def test_normalize_ip(raw, expected):
    assert normalize_ip(raw) == expected


@pytest.mark.parametrize(
    "ip,expected",
    [
        ("203.0.113.255", True),
        ("203.0.113.127", False),
        ("2001:db8:a110:ffff::1", True),
        ("2001:db8:a111::1", False),
        ("8.8.8.8", False),
        ("::1", True),
        ("lixo", False),
        ("", False),
    ],
)
def test_allowlist(ip, expected):
    assert ip_in_allowlist(normalize_ip(ip), ALLOW) is expected


def test_mapped_ipv4_matches_after_normalize():
    assert ip_in_allowlist("::ffff:203.0.113.129", ALLOW) is False  # regressão documentada
    assert ip_in_allowlist(normalize_ip("::ffff:203.0.113.129"), ALLOW) is True


def test_open_allowlist_matches_both_families():
    assert ip_in_allowlist("8.8.8.8", ["0.0.0.0/0", "2000::/3"]) is True
    assert ip_in_allowlist("2001:db8::1", ["0.0.0.0/0", "2000::/3"]) is True
