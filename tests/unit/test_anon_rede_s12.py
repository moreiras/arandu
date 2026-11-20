# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""quem não tem sessão emitida pelo servidor é contado pela rede do IP; criar sessões tem teto."""
from api.auth import anon_session as a


def test_rede_do_ip():
    assert a.rede_do_ip("203.0.113.7") == "203.0.113.7"
    assert a.rede_do_ip("2001:db8:1:2:aaaa::1") == a.rede_do_ip("2001:db8:1:2:ffff::9") == "2001:db8:1:2::/64"
    assert a.rede_do_ip("lixo") == "lixo"


def test_hash_rede_tem_sal_e_e_estavel_no_dia():
    h = a.hash_rede("203.0.113.7", "segredo-1")
    assert h == a.hash_rede("203.0.113.7", "segredo-1") and h != a.hash_rede("203.0.113.7", "segredo-2")
    assert a.hash_rede("2001:db8::1", "s") == a.hash_rede("2001:db8::2", "s")          # mesmo /64
    import hashlib
    assert h != hashlib.sha256(b"203.0.113.7|").hexdigest()                             # não é o hash sem sal


def test_teto_de_sessoes_novas_por_rede(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "_criacoes", {})
    cfg = a.load_anon_config()
    criadas = [a.resolve_and_touch(tmp_path, cfg, None, None, rede="r1") for _ in range(a.MAX_SESSOES_NOVAS_POR_HORA)]
    assert all(c[0] and c[3] for c in criadas)
    sid, seg, esgotado, cookie = a.resolve_and_touch(tmp_path, cfg, None, None, rede="r1")
    assert sid == "" and esgotado and not cookie
    assert a.resolve_and_touch(tmp_path, cfg, None, None, rede="r2")[0]                   # outra rede segue criando
    assert a.resolve_and_touch(tmp_path, cfg, criadas[0][0], None, rede="r1")[0] == criadas[0][0]   # sessão existente segue valendo


def test_relogio_para_no_limite(tmp_path, monkeypatch):
    """Depois do limite o tempo não segue somando (cada /auth/me de quem só vê o painel de login somava)."""
    monkeypatch.setattr(a, "_criacoes", {})
    cfg = a.load_anon_config()
    sid = a.resolve_and_touch(tmp_path, cfg, None, None, rede="r1")[0]
    with a._connect(tmp_path) as conn:
        conn.execute("UPDATE anon_sessions SET active_seconds = ?, last_heartbeat_at = '2000-01-01T00:00:00+00:00' WHERE session_id = ?",
                     (cfg.limit_seconds - 5, sid))
    _, seg, esgotado, _ = a.resolve_and_touch(tmp_path, cfg, sid, None, rede="r1")
    assert esgotado and seg == cfg.limit_seconds
    with a._connect(tmp_path) as conn:
        conn.execute("UPDATE anon_sessions SET last_heartbeat_at = '2000-01-01T00:00:00+00:00' WHERE session_id = ?", (sid,))
    assert a.resolve_and_touch(tmp_path, cfg, sid, None, rede="r1")[1] == cfg.limit_seconds
