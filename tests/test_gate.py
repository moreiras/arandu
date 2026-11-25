# SPDX-License-Identifier: AGPL-3.0-or-later
"""GET /auth/gate (auth_request do nginx) e o middleware usam a mesma decisão."""
import sqlite3

from api.auth.anon_session import resolve_and_touch


def _exhaust(app, tmp_path) -> str:
    """Cria uma sessão anônima e a leva ao limite; devolve o session_id."""
    sid, *_ = resolve_and_touch(tmp_path, app.state.anon_config, None, None)
    db = sqlite3.connect(tmp_path / "auth" / "anon_sessions.db")
    db.execute("UPDATE anon_sessions SET active_seconds = 999999 WHERE session_id = ?", (sid,))
    db.commit()
    db.close()
    return sid


def gate(client, ip, path="/api/v1/ixps", cookies=None):
    return client.get(
        "/auth/gate",
        headers={"X-Real-IP": ip, "X-Original-URI": path},
        cookies=cookies or {},
    )


def test_anon_novo_passa(app_client):
    c, app, _ = app_client
    assert gate(c, "8.8.8.8").status_code == 204


def test_esgotado_bloqueia(app_client):
    c, app, tmp = app_client
    sid = _exhaust(app, tmp)
    r = gate(c, "8.8.8.8", cookies={"anon_sid": sid})
    assert r.status_code == 403


def test_allowlist_nunca_bloqueia_mesmo_com_cookie_esgotado(app_client):
    c, app, tmp = app_client
    sid = _exhaust(app, tmp)
    assert gate(c, "203.0.113.129", cookies={"anon_sid": sid}).status_code == 204
    assert gate(c, "2001:db8:a110::1", cookies={"anon_sid": sid}).status_code == 204
    assert gate(c, "::ffff:203.0.113.129", cookies={"anon_sid": sid}).status_code == 204


def test_rotas_isentas_nao_bloqueiam(app_client):
    c, app, tmp = app_client
    sid = _exhaust(app, tmp)
    for path in ("/health", "/auth/me", "/api/v1/docs"):
        assert gate(c, "8.8.8.8", path=path, cookies={"anon_sid": sid}).status_code == 204


def test_gate_nao_e_limitado_por_taxa(app_client):
    c, app, _ = app_client
    codes = {gate(c, "8.8.8.8").status_code for _ in range(150)}
    assert codes == {204}


def test_middleware_e_gate_concordam(app_client):
    c, app, tmp = app_client
    sid = _exhaust(app, tmp)
    r = c.get("/api/v1/map/asns", headers={"X-Real-IP": "8.8.8.8"}, cookies={"anon_sid": sid})
    assert r.status_code == 429                                  # D9: orçamento esgotado é 429 com Retry-After, o gate (nginx) segue em 403
    assert r.json()["anon_limit_reached"] is True
    assert r.headers["X-Anon-Limit-Reached"] == "true"


# ── política nova (ACCESS_POLICY_MODE) ───────────────────────────────────────

def _gate(client, ip, path, query="", method="GET", cookies=None):
    return client.get(
        "/auth/gate",
        headers={"X-Real-IP": ip, "X-Original-URI": path + (("?" + query) if query else ""),
                 "X-Original-Method": method},
        cookies=cookies or {},
    )


def test_enforce_entrada_aberta_mesmo_esgotado(app_client, monkeypatch):
    monkeypatch.setenv("ACCESS_POLICY_MODE", "enforce")
    c, app, tmp = app_client
    sid = _exhaust(app, tmp)
    ck = {"anon_sid": sid}
    assert _gate(c, "8.8.8.8", "/api/v1/ixps", cookies=ck).status_code == 204          # entrada
    assert _gate(c, "8.8.8.8", "/api/v1/asns", "limit=8&q=claro", cookies=ck).status_code == 204
    assert _gate(c, "8.8.8.8", "/api/v1/map/asns", cookies=ck).status_code == 403       # medida
    assert _gate(c, "8.8.8.8", "/api/v1/asns", "page=2", cookies=ck).status_code == 401  # login


def test_enforce_login_vale_mesmo_com_orcamento(app_client, monkeypatch):
    monkeypatch.setenv("ACCESS_POLICY_MODE", "enforce")
    c, *_ = app_client
    assert _gate(c, "8.8.8.8", "/api/v1/scms", "page=2").status_code == 401
    assert _gate(c, "8.8.8.8", "/api/v1/map/asns").status_code == 204   # medida com orçamento
    assert _gate(c, "8.8.8.8", "/api/v1/asns/3356/contacts").status_code == 401


def test_enforce_allowlist_e_usuario_nunca_bloqueiam(app_client, monkeypatch):
    monkeypatch.setenv("ACCESS_POLICY_MODE", "enforce")
    c, *_ = app_client
    assert _gate(c, "203.0.113.129", "/api/v1/asns", "page=9").status_code == 204


def test_shadow_preserva_comportamento_legado(app_client, monkeypatch):
    monkeypatch.setenv("ACCESS_POLICY_MODE", "shadow")
    c, app, tmp = app_client
    sid = _exhaust(app, tmp)
    ck = {"anon_sid": sid}
    assert _gate(c, "8.8.8.8", "/api/v1/ixps", cookies=ck).status_code == 403   # legado bloqueia tudo
    assert _gate(c, "8.8.8.8", "/api/v1/asns", "page=2").status_code == 204     # legado não pede login


def test_historico_pede_login(app_client, monkeypatch):
    monkeypatch.setenv("ACCESS_POLICY_MODE", "enforce")
    c, app, _ = app_client
    app.state.store = type("S", (), {"list_snapshots": lambda self: ["2026-09-27", "2026-10-04"]})()
    import api.auth.access as acc
    acc._recent_cache = (0.0, [])
    assert _gate(c, "8.8.8.8", "/api/v1/ixps", "date=2026-10-04").status_code == 204
    assert _gate(c, "8.8.8.8", "/api/v1/ixps", "date=2026-08-01").status_code == 401
    app.state.store = None
    acc._recent_cache = (0.0, [])


def test_heartbeat_em_area_open_nao_soma(app_client):
    c, app, tmp = app_client
    h = {"X-Real-IP": "8.8.8.8", "X-Device-Fingerprint": "fp-teste"}
    r0 = c.get("/auth/me", headers=h)
    assert r0.json()["anon"]["active_seconds"] == 0
    import time
    from api.auth import anon_session as an
    # força last_heartbeat_at 20 s no passado para ter delta mensurável
    import sqlite3
    from datetime import datetime, timedelta, timezone
    db = sqlite3.connect(tmp / "auth" / "anon_sessions.db")
    past = (datetime.now(timezone.utc) - timedelta(seconds=20)).isoformat()
    db.execute("UPDATE anon_sessions SET last_heartbeat_at = ?", (past,)); db.commit()
    r = c.post("/auth/heartbeat", headers={**h, "X-Arandu-Area": "open"})
    assert r.json()["anon"]["active_seconds"] == 0
    db.execute("UPDATE anon_sessions SET last_heartbeat_at = ?", (past,)); db.commit()
    r = c.post("/auth/heartbeat", headers={**h, "X-Arandu-Area": "metered"})
    assert 15 <= r.json()["anon"]["active_seconds"] <= 25


def test_identidade_por_fingerprint_no_gate(app_client, monkeypatch):
    """Cliente sem cookie mas com fingerprint (cookie bloqueado) é reconhecido."""
    monkeypatch.setenv("ACCESS_POLICY_MODE", "enforce")
    c, app, tmp = app_client
    from api.auth.anon_session import hash_fingerprint, hash_rede, resolve_and_touch
    rede = hash_rede("8.8.8.8", app.state.auth_config.jwt_secret)
    sid, *_ = resolve_and_touch(tmp, app.state.anon_config, None, hash_fingerprint("fp-x", rede))
    import sqlite3
    db = sqlite3.connect(tmp / "auth" / "anon_sessions.db")
    db.execute("UPDATE anon_sessions SET active_seconds = 999999"); db.commit()
    r = c.get("/auth/gate", headers={"X-Real-IP": "8.8.8.8", "X-Device-Fingerprint": "fp-x",
                                      "X-Original-URI": "/api/v1/map/asns", "X-Original-Method": "GET"})
    assert r.status_code == 403
    r = c.get("/auth/gate", headers={"X-Real-IP": "8.8.8.8", "X-Device-Fingerprint": "outro",
                                      "X-Original-URI": "/api/v1/map/asns", "X-Original-Method": "GET"})
    assert r.status_code == 204
    # mesmo aparelho (mesmo fingerprint) em outra rede é outra pessoa: não herda o orçamento esgotado
    r = c.get("/auth/gate", headers={"X-Real-IP": "1.1.1.1", "X-Device-Fingerprint": "fp-x",
                                      "X-Original-URI": "/api/v1/map/asns", "X-Original-Method": "GET"})
    assert r.status_code == 204


def test_cliente_sem_cookie_nem_fingerprint_com_custo(app_client, monkeypatch):
    monkeypatch.setenv("ACCESS_POLICY_MODE", "enforce")
    monkeypatch.setenv("ANON_API_CLIENT_COST_SECONDS", "300")
    from api.auth.anon_session import load_anon_config
    c, app, _ = app_client
    app.state.anon_config = load_anon_config()
    h = {"X-Real-IP": "9.9.9.9", "User-Agent": "curl/8", "X-Original-URI": "/api/v1/map/asns", "X-Original-Method": "GET"}
    assert c.get("/auth/gate", headers=h).status_code == 204   # 300 s
    assert c.get("/auth/gate", headers=h).status_code == 403   # 600 s ≥ limite
    # entrada continua aberta para o mesmo cliente
    h["X-Original-URI"] = "/api/v1/ixps"
    assert c.get("/auth/gate", headers=h).status_code == 204


def test_diag_explica_a_classe_da_rota(app_client):
    c, *_ = app_client
    r = c.get("/auth/diag", params={"path": "/api/v1/asns", "query": "page=2"}, headers={"X-Real-IP": "8.8.8.8"})
    assert r.json()["rota"]["classe"] == "login"
    assert r.json()["politica_modo"] in ("off", "shadow", "enforce")


def test_sessoes_expiradas_sao_apagadas(app_client):
    c, app, tmp = app_client
    import sqlite3
    from api.auth import anon_session as an
    sid, *_ = an.resolve_and_touch(tmp, app.state.anon_config, None, None)
    db = sqlite3.connect(tmp / "auth" / "anon_sessions.db")
    db.execute("UPDATE anon_sessions SET expires_at = '2000-01-01T00:00:00+00:00'"); db.commit()
    an._last_purge = 0.0
    an.peek_state(tmp, app.state.anon_config, None)
    assert db.execute("SELECT count(*) FROM anon_sessions").fetchone()[0] == 0


def test_gate_app_processo_dedicado(tmp_path, monkeypatch):
    """api/gate_app.py: mesmo veredito do gate da API, sem carregar a API/Store."""
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "a")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "b")
    monkeypatch.setenv("ALLOWED_IPS", "203.0.113.128/25")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ACCESS_POLICY_MODE", "enforce")
    from starlette.testclient import TestClient

    from api.gate_app import app

    with TestClient(app) as c:
        h = {"X-Original-Method": "GET"}
        assert c.get("/health").json()["service"] == "gate"
        r = c.get("/auth/gate", headers={**h, "X-Real-IP": "8.8.8.8", "X-Original-URI": "/api/v1/ixps"})
        assert r.status_code == 204
        r = c.get("/auth/gate", headers={**h, "X-Real-IP": "8.8.8.8", "X-Original-URI": "/api/v1/asns?page=2"})
        assert r.status_code == 401
        r = c.get("/auth/gate", headers={**h, "X-Real-IP": "203.0.113.129", "X-Original-URI": "/api/v1/asns?page=2"})
        assert r.status_code == 204


def test_purga_de_sessoes_roda_mesmo_com_monotonic_pequeno(app_client, monkeypatch):
    """Em máquina recém-iniciada `time.monotonic()` < 600 s: a limpeza de sessões expiradas não pode ser adiada
    porque `_last_purge` começa em 0.0."""
    c, app, tmp = app_client
    import sqlite3

    from api.auth import anon_session as an

    sid, *_ = an.resolve_and_touch(tmp, app.state.anon_config, None, None)
    db = sqlite3.connect(tmp / "auth" / "anon_sessions.db")
    db.execute("UPDATE anon_sessions SET expires_at = '2000-01-01T00:00:00+00:00'"); db.commit()
    import time

    monkeypatch.setattr(time, "monotonic", lambda: 5.0)          # 5 s depois do boot (a função importa `time` local)
    monkeypatch.setattr(an, "_last_purge", 0.0)
    an.peek_state(tmp, app.state.anon_config, None)
    assert db.execute("SELECT count(*) FROM anon_sessions").fetchone()[0] == 0


# ── PT-12 / D9 (DADOS-E1): 429 com Retry-After e corpo explicativo ─────────────────────────────────────────

def test_orcamento_esgotado_e_429_com_retry_after_ate_a_meia_noite_utc(app_client, monkeypatch):
    from datetime import datetime, timezone

    monkeypatch.setenv("ACCESS_POLICY_MODE", "enforce")
    c, app, tmp = app_client
    sid = _exhaust(app, tmp)
    antes = datetime.now(timezone.utc)
    r = c.get("/api/v1/map/asns", headers={"X-Real-IP": "8.8.8.8"}, cookies={"anon_sid": sid})
    assert r.status_code == 429
    espera = int(r.headers["Retry-After"])
    seg_do_dia = antes.hour * 3600 + antes.minute * 60 + antes.second
    assert abs(espera - (86400 - seg_do_dia)) <= 5                # até a próxima 00:00 UTC (folga para o relógio entre as duas leituras)
    assert r.headers["Cache-Control"] == "private, no-store" and r.headers["X-Anon-Limit-Reached"] == "true"
    corpo = r.json()
    assert corpo["anon_limit_reached"] is True and corpo["janela"] == "dia" and corpo["retry_after"] == espera
    assert "meia-noite UTC" in corpo["detail"] and "IPv6 /64" in corpo["detail"]
    assert any("conta" in a for a in corpo["alternativas"])
    assert not any("MCP" in a for a in corpo["alternativas"])           # chave de MCP desligada (padrão): não é sugerida


def test_429_so_sugere_a_chave_de_mcp_com_a_chave_ligada(app_client, monkeypatch):
    """A sugestão segue a regra de `/api/v1/limites` (`MCP_KEY_ATIVA` e `MCP_KEY_PEPPER`), na API e no processo do gate (`/auth/limite`)."""
    from api.auth import chaves_mcp
    from api.auth.access import ALTERNATIVA_CHAVE_MCP

    monkeypatch.setenv("ACCESS_POLICY_MODE", "enforce")
    c, app, tmp = app_client
    sid = _exhaust(app, tmp)
    from starlette.testclient import TestClient

    from api.gate_app import app as gate_app

    def corpos():
        r = c.get("/api/v1/map/asns", headers={"X-Real-IP": "8.8.8.8"}, cookies={"anon_sid": sid})
        with TestClient(gate_app) as g:
            return r.status_code, r.json()["alternativas"], g.get("/auth/limite").json()["alternativas"]

    monkeypatch.setenv("MCP_KEY_ATIVA", "1")
    monkeypatch.setenv("MCP_KEY_PEPPER", "p" * 32)
    assert chaves_mcp.ativa()
    status, api_alt, gate_alt = corpos()
    assert status == 429 and ALTERNATIVA_CHAVE_MCP in api_alt and api_alt == gate_alt
    monkeypatch.setenv("MCP_KEY_ATIVA", "0")
    status, api_alt, gate_alt = corpos()
    assert status == 429 and ALTERNATIVA_CHAVE_MCP not in api_alt and api_alt == gate_alt and len(api_alt) == 1
    monkeypatch.setenv("MCP_KEY_ATIVA", "1")                              # ligada sem o pepper: a chave fica desligada, como em /limites
    monkeypatch.setenv("MCP_KEY_PEPPER", "curto")
    assert corpos()[1] == corpos()[2] and ALTERNATIVA_CHAVE_MCP not in corpos()[1]


def test_retry_after_no_fim_do_dia_e_de_pelo_menos_um_segundo():
    from datetime import datetime, timezone

    from api.auth.access import segundos_ate_meia_noite_utc
    assert segundos_ate_meia_noite_utc(datetime(2026, 11, 25, 0, 0, 0, tzinfo=timezone.utc)) == 86400
    assert segundos_ate_meia_noite_utc(datetime(2026, 11, 25, 23, 59, 59, tzinfo=timezone.utc)) == 1
    assert segundos_ate_meia_noite_utc(datetime(2026, 12, 31, 12, 0, 0, tzinfo=timezone.utc)) == 43200     # vira o ano


def test_entrada_nao_debita_nem_vira_429_com_o_orcamento_esgotado(app_client, monkeypatch):
    monkeypatch.setenv("ACCESS_POLICY_MODE", "enforce")
    c, app, tmp = app_client
    sid = _exhaust(app, tmp)
    for rota in ("/api/v1/ixps", "/api/v1/brasil/snapshots", "/api/v1/rpki/summary", "/api/v1/prontidao/resumo"):
        assert _gate(c, "8.8.8.8", rota, cookies={"anon_sid": sid}).status_code == 204, rota        # o gate libera: nada a debitar nem a recusar


def test_gate_app_serve_o_429_que_o_nginx_repassa(tmp_path, monkeypatch):
    """O `auth_request` do nginx só distingue 401 e 403; o `@anon_limit` pede a resposta pronta ao gate (`/auth/limite`)."""
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "a")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "b")
    monkeypatch.setenv("ALLOWED_IPS", "")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from starlette.testclient import TestClient

    from api.gate_app import app

    with TestClient(app) as c:
        r = c.get("/auth/limite")
        assert r.status_code == 429 and 1 <= int(r.headers["Retry-After"]) <= 86400
        assert r.json()["anon_limit_reached"] is True and r.headers["X-Anon-Limit-Reached"] == "true"


def test_nginx_troca_o_403_do_gate_por_429_com_retry_after():
    """O gate responde 403; `docker/nginx-frontend.conf` deve devolver 429 ao cliente (o teste com nginx de verdade é `tests/nginx/test_gate.sh`)."""
    from pathlib import Path
    conf = (Path(__file__).resolve().parents[1] / "docker" / "nginx-frontend.conf").read_text(encoding="utf-8")
    assert "error_page 403 = @anon_limit;" in conf
    bloco = conf[conf.index("location @anon_limit {"):conf.index("location @anon_limit_estatico {")]
    assert "rewrite ^ /auth/limite break;" in bloco and "proxy_pass              http://api:8001;" in bloco
    estatico = conf[conf.index("location @anon_limit_estatico {"):]
    assert "return 429" in estatico.split("}")[0] and 'add_header Retry-After' in estatico.split("}")[0] and "return 403" not in estatico.split("}")[0]
