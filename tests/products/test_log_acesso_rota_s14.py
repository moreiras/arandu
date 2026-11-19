# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`/auth/log` usa a sessão revogável e grava o conta_id, nunca o e-mail."""


def test_rota_de_log_grava_conta_id_e_nao_email(api, monkeypatch):
    from api.auth import router, sessao
    gravado = []
    monkeypatch.setattr(sessao, "usuario_do_cookie", lambda tok, sec, d: {"email": "fulano@exemplo.org", "conta_id": "cid-9"} if tok == "ok" else None)
    monkeypatch.setattr(router, "log_access", lambda d, ip, ident, path: gravado.append(ident))
    api.cookies.set("auth_token", "ok")
    assert api.post("/auth/log", json={"path": "/asn/1"}).status_code == 200
    api.cookies.set("auth_token", "revogado")                 # JWT de conta excluída ou de "sair de todos": não registra
    assert api.post("/auth/log", json={"path": "/asn/2"}).status_code == 200
    api.cookies.delete("auth_token")
    assert gravado == ["cid-9"]


def test_diag_nao_conta_jwt_revogado_como_logado(api, monkeypatch):
    from api.auth import sessao
    monkeypatch.setattr(sessao, "usuario_do_cookie", lambda tok, sec, d: None)
    api.cookies.set("auth_token", "qualquer")
    r = api.get("/auth/diag")
    api.cookies.delete("auth_token")
    assert r.status_code == 200 and r.json()["tier"] in ("anon", "allowed")
