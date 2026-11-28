# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Orçamento anônimo: fingerprint em dois níveis (forte e estável) e teto do tempo somado por rede."""
import sqlite3

import pytest

from api.auth import anon_session as a

REDE = "rede-a"


@pytest.fixture(autouse=True)
def _zera(monkeypatch):
    monkeypatch.setattr(a, "_criacoes", {})
    monkeypatch.delenv("ANON_REDE_LIMIT_MULTIPLIER", raising=False)


def _cfg(**kw):
    cfg = a.load_anon_config()
    for k, v in kw.items():
        setattr(cfg, k, v)
    return cfg


def _forte(raw, rede=REDE):
    return a.hash_fingerprint(raw, rede)


def _est(raw, rede=REDE):
    return a.hash_fingerprint_estavel(raw, rede)


def _gasta(tmp, sid, segundos):
    with a._connect(tmp) as conn:
        conn.execute("UPDATE anon_sessions SET active_seconds = ? WHERE session_id = ?", (segundos, sid))


def test_janela_privada_acha_a_mesma_sessao_pelo_estavel(tmp_path):
    cfg = _cfg()
    sid, _, _, cookie = a.resolve_and_touch(tmp_path, cfg, None, _forte("forte-normal"), rede=REDE, fingerprint_estavel_hash=_est("est"))
    assert cookie
    _gasta(tmp_path, sid, 400)
    # janela privada: sem cookie, forte diferente (canvas/WebGL mudaram), estável igual
    sid2, seg, esgotado, cookie2 = a.resolve_and_touch(
        tmp_path, cfg, None, _forte("forte-privado"), rede=REDE, fingerprint_estavel_hash=_est("est"))
    assert sid2 == sid and seg >= 400 and not esgotado
    assert cookie2                                           # o cookie é reemitido com o id da sessão achada
    with a._connect(tmp_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM anon_sessions").fetchone()[0] == 1
        assert conn.execute("SELECT fingerprint_hash FROM anon_sessions").fetchone()[0] == _forte("forte-privado")
    # o pedido seguinte da janela privada já acha pelo forte novo, sem o estável
    assert a.resolve_and_touch(tmp_path, cfg, None, _forte("forte-privado"), rede=REDE)[0] == sid
    st = a.peek_state(tmp_path, cfg, None, _forte("forte-privado"), None, None, REDE)
    assert st.identity == "fingerprint" and st.found


def test_peek_acha_pelo_estavel_e_respeita_a_rede(tmp_path):
    cfg = _cfg()
    sid = a.resolve_and_touch(tmp_path, cfg, None, _forte("f"), rede=REDE, fingerprint_estavel_hash=_est("e"))[0]
    _gasta(tmp_path, sid, cfg.limit_seconds)
    st = a.peek_state(tmp_path, cfg, None, _forte("outro"), None, _est("e"), REDE)
    assert (st.found, st.limit_reached, st.identity) == (True, True, "fingerprint_estavel")
    # mesmo aparelho em outra rede: o hash é outro e não herda
    assert not a.peek_state(tmp_path, cfg, None, _forte("outro", "rede-b"), None, _est("e", "rede-b"), "rede-b").found


def test_forte_e_estavel_nao_se_confundem():
    assert _forte("x") != _est("x") and _est("x") != _est("x", "rede-b")


def test_cookie_continua_com_prioridade(tmp_path):
    cfg = _cfg()
    s1 = a.resolve_and_touch(tmp_path, cfg, None, _forte("f1"), rede=REDE, fingerprint_estavel_hash=_est("e1"))[0]
    s2 = a.resolve_and_touch(tmp_path, cfg, None, _forte("f2"), rede=REDE, fingerprint_estavel_hash=_est("e2"))[0]
    assert s1 != s2
    # cookie de s1 com os fingerprints de s2: vale o cookie
    r = a.resolver_sessao(tmp_path, cfg, s1, _forte("f2"), rede=REDE, fingerprint_estavel_hash=_est("e2"))
    assert r.session_id == s1 and not r.needs_cookie
    assert a.peek_state(tmp_path, cfg, s1, _forte("f2"), None, _est("e2"), REDE).identity == "cookie"


def test_forte_tem_prioridade_sobre_o_estavel(tmp_path):
    cfg = _cfg()
    s1 = a.resolve_and_touch(tmp_path, cfg, None, _forte("f1"), rede=REDE, fingerprint_estavel_hash=_est("comum"))[0]
    s2 = a.resolve_and_touch(tmp_path, cfg, None, _forte("f2"), rede=REDE, fingerprint_estavel_hash=_est("e2"))[0]
    assert a.resolve_and_touch(tmp_path, cfg, None, _forte("f2"), rede=REDE, fingerprint_estavel_hash=_est("comum"))[0] == s2 != s1


def test_cliente_antigo_sem_o_estavel_funciona(tmp_path):
    cfg = _cfg()
    sid = a.resolve_and_touch(tmp_path, cfg, None, _forte("f"), rede=REDE)[0]
    assert a.resolve_and_touch(tmp_path, cfg, None, _forte("f"), rede=REDE)[0] == sid
    assert a.peek_state(tmp_path, cfg, None, _forte("f"), None, None, REDE).identity == "fingerprint"
    # sessão criada por cliente antigo ganha o estável quando o cliente novo aparece com o forte conhecido
    a.resolve_and_touch(tmp_path, cfg, None, _forte("f"), rede=REDE, fingerprint_estavel_hash=_est("e"))
    with a._connect(tmp_path) as conn:
        assert conn.execute("SELECT fingerprint_estavel_hash FROM anon_sessions").fetchone()[0] == _est("e")


def test_teto_por_rede_soma_sessoes_distintas(tmp_path):
    cfg = _cfg(limit_minutes=10)
    assert cfg.rede_limit_seconds == 3 * 600
    ids = [a.resolve_and_touch(tmp_path, cfg, None, _forte(f"f{i}"), rede=REDE)[0] for i in range(4)]
    for sid in ids[:2]:
        _gasta(tmp_path, sid, 600)                            # 1200 s: abaixo de 1800
    assert not a.resolve_and_touch(tmp_path, cfg, ids[2], None, rede=REDE)[2]
    _gasta(tmp_path, ids[2], 600)                             # 1800 s: no teto
    r = a.resolver_sessao(tmp_path, cfg, ids[3], None, rede=REDE)
    assert r.limit_reached and r.bloqueio_rede and r.active_seconds < cfg.limit_seconds
    st = a.peek_state(tmp_path, cfg, ids[3], None, None, None, REDE)
    assert (st.limit_reached, st.bloqueio_rede) == (True, True)
    # a rede no teto também não cria sessão nova
    nova = a.resolver_sessao(tmp_path, cfg, None, _forte("novo"), rede=REDE)
    assert nova.session_id == "" and nova.limit_reached and nova.bloqueio_rede and not nova.needs_cookie
    st = a.peek_state(tmp_path, cfg, None, _forte("novo"), None, None, REDE)
    assert not st.found and st.limit_reached and st.bloqueio_rede


def test_teto_zero_desliga(tmp_path, monkeypatch):
    monkeypatch.setenv("ANON_REDE_LIMIT_MULTIPLIER", "0")
    cfg = a.load_anon_config()
    assert cfg.rede_limit_seconds == 0
    ids = [a.resolve_and_touch(tmp_path, cfg, None, _forte(f"f{i}"), rede=REDE)[0] for i in range(5)]
    for sid in ids:
        _gasta(tmp_path, sid, 599)
    r = a.resolver_sessao(tmp_path, cfg, ids[0], None, rede=REDE)
    assert not r.limit_reached and not r.bloqueio_rede
    assert not a.peek_state(tmp_path, cfg, ids[0], None, None, None, REDE).limit_reached
    assert a.resolver_sessao(tmp_path, cfg, None, _forte("novo"), rede=REDE).session_id


def test_multiplicador_vem_do_ambiente(monkeypatch):
    monkeypatch.setenv("ANON_SESSION_LIMIT_MINUTES", "10")
    monkeypatch.setenv("ANON_REDE_LIMIT_MULTIPLIER", "5")
    assert a.load_anon_config().rede_limit_seconds == 3000
    monkeypatch.delenv("ANON_REDE_LIMIT_MULTIPLIER")
    assert a.load_anon_config().rede_limit_seconds == 1800


def test_redes_diferentes_nao_se_somam(tmp_path):
    cfg = _cfg()
    a_ids = [a.resolve_and_touch(tmp_path, cfg, None, _forte(f"f{i}", "rede-a"), rede="rede-a")[0] for i in range(3)]
    for sid in a_ids:
        _gasta(tmp_path, sid, 600)
    b = a.resolve_and_touch(tmp_path, cfg, None, _forte("fb", "rede-b"), rede="rede-b")[0]
    assert b and not a.resolver_sessao(tmp_path, cfg, b, None, rede="rede-b").limit_reached
    assert not a.peek_state(tmp_path, cfg, b, None, None, None, "rede-b").limit_reached
    assert a.peek_state(tmp_path, cfg, a_ids[0], None, None, None, "rede-a").limit_reached


def test_o_custo_de_script_nao_entra_no_teto_da_rede(tmp_path):
    cfg = _cfg()
    for _ in range(3):
        a.charge_client(tmp_path, cfg, REDE, 300)
    sid = a.resolve_and_touch(tmp_path, cfg, None, _forte("f"), rede=REDE)[0]
    assert not a.resolver_sessao(tmp_path, cfg, sid, None, rede=REDE).bloqueio_rede


@pytest.mark.parametrize("gasto", [0, 599, 600, 1799, 1800, 2400])
def test_peek_e_resolve_concordam(tmp_path_factory, gasto):
    """Para cada estado do banco, peek_state e resolve_and_touch dão o mesmo veredito (individual ou de rede)."""
    tmp = tmp_path_factory.mktemp("c")
    cfg = _cfg()
    ids = [a.resolve_and_touch(tmp, cfg, None, _forte(f"f{i}"), rede=REDE)[0] for i in range(3)]
    _gasta(tmp, ids[0], min(gasto, 600))
    _gasta(tmp, ids[1], min(max(gasto - 600, 0), 600))
    _gasta(tmp, ids[2], min(max(gasto - 1200, 0), 600))
    for sid in ids:
        st = a.peek_state(tmp, cfg, sid, None, None, None, REDE)
        r = a.resolver_sessao(tmp, cfg, sid, None, rede=REDE)
        assert st.limit_reached == r.limit_reached and st.bloqueio_rede == r.bloqueio_rede, (gasto, sid)


def test_migracao_idempotente_sobre_banco_antigo(tmp_path, monkeypatch):
    (tmp_path / "auth").mkdir()
    antigo = sqlite3.connect(tmp_path / "auth" / "anon_sessions.db")
    antigo.executescript("""
        CREATE TABLE anon_sessions (session_id TEXT PRIMARY KEY, fingerprint_hash TEXT, active_seconds INTEGER NOT NULL DEFAULT 0,
            last_heartbeat_at TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL);
        INSERT INTO anon_sessions VALUES ('velho', 'fp', 50, '2999-01-01T00:00:00+00:00', '2999-01-01T00:00:00+00:00', '2999-01-02T00:00:00+00:00');
    """)
    antigo.commit()
    antigo.close()
    cfg = _cfg()
    for _ in range(2):                                        # o segundo ciclo simula outro processo (API e gate)
        monkeypatch.setattr(a, "_initialized", set())
        with a._connect(tmp_path) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(anon_sessions)")]
            idx = {r[1] for r in conn.execute("PRAGMA index_list(anon_sessions)")}
    assert {"ipua_hash", "fingerprint_estavel_hash", "rede_hash"} <= set(cols) and len(cols) == len(set(cols))
    assert {"idx_anon_sessions_fp_estavel", "idx_anon_sessions_rede", "idx_anon_sessions_ipua"} <= idx
    # a sessão antiga segue valendo e ganha estável e rede ao ser tocada
    r = a.resolver_sessao(tmp_path, cfg, "velho", None, rede=REDE, fingerprint_estavel_hash=_est("e"))
    assert r.session_id == "velho" and r.active_seconds >= 50
    with a._connect(tmp_path) as conn:
        assert conn.execute("SELECT fingerprint_estavel_hash, rede_hash FROM anon_sessions").fetchone() == (_est("e"), REDE)


def test_nao_grava_ip_no_banco(tmp_path):
    cfg = _cfg()
    rede = a.hash_rede("203.0.113.77", "segredo")
    a.resolve_and_touch(tmp_path, cfg, None, _forte("f", rede), rede=rede, fingerprint_estavel_hash=_est("e", rede))
    with a._connect(tmp_path) as conn:
        linhas = conn.execute("SELECT * FROM anon_sessions").fetchall()
    assert "203.0.113.77" not in repr(linhas)
    assert rede in linhas[0] and len(rede) == 64


# --- ponta a ponta: /auth/me, /auth/heartbeat e o gate com os cabeçalhos ---------------------------------------------------------------

def _gate(c, ip, headers=None, uri="/api/v1/map/asns"):
    return c.get("/auth/gate", headers={"X-Real-IP": ip, "X-Original-URI": uri, "X-Original-Method": "GET", **(headers or {})})


def test_me_e_gate_com_a_janela_privada(app_client, monkeypatch):
    monkeypatch.setenv("ACCESS_POLICY_MODE", "enforce")
    c, app, tmp = app_client
    h1 = {"X-Real-IP": "8.8.8.8", "X-Device-Fingerprint": "forte-1", "X-Device-Fingerprint-Estavel": "est"}
    r = c.get("/auth/me", headers=h1)
    assert r.json()["anon"]["bloqueio_rede"] is False
    sid = r.cookies.get("anon_sid") or c.cookies.get("anon_sid")
    c.cookies.clear()
    with sqlite3.connect(tmp / "auth" / "anon_sessions.db") as db:
        db.execute("UPDATE anon_sessions SET active_seconds = 600")
    h2 = {"X-Real-IP": "8.8.8.8", "X-Device-Fingerprint": "forte-2", "X-Device-Fingerprint-Estavel": "est"}
    assert _gate(c, "8.8.8.8", h2).status_code == 403                    # o gate acha pelo estável e vê o orçamento esgotado
    assert _gate(c, "8.8.8.8", {"X-Device-Fingerprint": "forte-2"}).status_code == 204   # cliente antigo, forte novo: sessão nova
    m = c.get("/auth/me", headers=h2).json()["anon"]
    assert m["limit_reached"] is True and m["bloqueio_rede"] is False
    assert c.cookies.get("anon_sid") == sid
    assert c.post("/auth/heartbeat", headers=h2).json()["anon"]["limit_reached"] is True


def test_teto_da_rede_no_gate_no_middleware_e_no_me(app_client, monkeypatch):
    monkeypatch.setenv("ACCESS_POLICY_MODE", "enforce")
    c, app, tmp = app_client
    cfg = app.state.anon_config
    ip = "198.51.100.9"
    for i in range(3):
        c.cookies.clear()
        c.get("/auth/me", headers={"X-Real-IP": ip, "X-Device-Fingerprint": f"f{i}"})
    with sqlite3.connect(tmp / "auth" / "anon_sessions.db") as db:
        db.execute("UPDATE anon_sessions SET active_seconds = 599")       # 1797 s somados, nenhuma esgotada
    c.cookies.clear()
    novo = {"X-Real-IP": ip, "X-Device-Fingerprint": "outra-janela"}
    assert _gate(c, ip, novo).status_code == 204
    with sqlite3.connect(tmp / "auth" / "anon_sessions.db") as db:
        db.execute("UPDATE anon_sessions SET active_seconds = 600")                  # 1800 s: no teto
    assert cfg.rede_limit_seconds == 1800
    assert _gate(c, ip, novo).status_code == 403                          # gate: rede no teto
    r = c.get("/api/v1/map/asns", headers={"X-Real-IP": ip})                # middleware: a mesma regra, 429 com Retry-After
    assert r.status_code == 429 and r.json()["anon_limit_reached"] is True and int(r.headers["Retry-After"]) > 0
    assert _gate(c, "198.51.100.10", {"X-Device-Fingerprint": "outra-janela"}).status_code == 204              # outra rede segue livre
    m = c.get("/auth/me", headers=novo).json()["anon"]
    assert m["limit_reached"] is True and m["bloqueio_rede"] is True
    # páginas de entrada (open) nunca bloqueiam, mesmo com a rede no teto
    assert _gate(c, ip, novo, uri="/api/v1/ixps").status_code == 204
