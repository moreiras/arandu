# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — registro técnico do aceite da política (D10): migração do SQLite, gravação no login e ausência de dado pessoal novo."""
import sqlite3

from api.auth import contas
from api.auth.politica import POLITICA_NAO_REGISTRADA, POLITICA_VERSAO_VIGENTE

_SCHEMA_ANTIGO = """
CREATE TABLE contas (
    conta_id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, nome TEXT, provedor TEXT,
    criada_em TEXT NOT NULL, ultimo_acesso TEXT NOT NULL, sessao_valida_desde TEXT, exclusao_solicitada_em TEXT
);
"""


def _base_antiga(tmp_path, n=2):
    (tmp_path / "auth").mkdir()
    con = sqlite3.connect(tmp_path / "auth" / "contas.db")
    con.executescript(_SCHEMA_ANTIGO)
    for i in range(n):
        con.execute("INSERT INTO contas VALUES (?,?,?,?,?,?,NULL,NULL)", (f"id-{i}", f"u{i}@example.org", f"U{i}", "google", "2026-01-01T00:00:00.000000+00:00", "2026-02-01T00:00:00.000000+00:00"))
    con.commit()
    con.close()


def _linhas(tmp_path):
    con = sqlite3.connect(tmp_path / "auth" / "contas.db")
    try:
        return con.execute("SELECT * FROM contas ORDER BY conta_id").fetchall()
    finally:
        con.close()


def _colunas(tmp_path):
    con = sqlite3.connect(tmp_path / "auth" / "contas.db")
    try:
        return [r[1] for r in con.execute("PRAGMA table_info(contas)")]
    finally:
        con.close()


def test_conta_antiga_ganha_colunas_como_nao_registrada(tmp_path):
    _base_antiga(tmp_path)
    c = contas.por_id(tmp_path, "id-0")
    assert {"politica_versao", "aceite_em"} <= set(_colunas(tmp_path))
    assert c.politica_versao == POLITICA_NAO_REGISTRADA and c.aceite_em is None
    assert (c.email, c.nome, c.provedor, c.criada_em) == ("u0@example.org", "U0", "google", "2026-01-01T00:00:00.000000+00:00")


def test_migracao_idempotente_e_sem_perda(tmp_path):
    _base_antiga(tmp_path)
    contas.por_id(tmp_path, "id-0")
    antes = _linhas(tmp_path)
    for _ in range(3):
        contas.por_id(tmp_path, "id-0")
    assert _linhas(tmp_path) == antes and len(antes) == 2
    assert _colunas(tmp_path).count("politica_versao") == 1


def test_login_grava_versao_vigente_e_data_na_conta_migrada(tmp_path):
    _base_antiga(tmp_path)
    c = contas.registrar_login(tmp_path, "u0@example.org", "U0", "google")
    assert c.conta_id == "id-0" and c.politica_versao == POLITICA_VERSAO_VIGENTE and c.aceite_em
    # a mesma versão no login seguinte mantém a data do aceite
    c2 = contas.registrar_login(tmp_path, "u0@example.org", "U0", "google")
    assert c2.aceite_em == c.aceite_em
    # a outra conta continua não registrada até o login dela
    assert contas.por_id(tmp_path, "id-1").politica_versao == POLITICA_NAO_REGISTRADA


def test_conta_nova_grava_versao_e_data(tmp_path):
    c = contas.registrar_login(tmp_path, "n@example.org", "N", "linkedin")
    assert c.politica_versao == POLITICA_VERSAO_VIGENTE and c.aceite_em == c.criada_em


def test_nova_versao_da_politica_regrava_no_proximo_login(tmp_path, monkeypatch):
    c = contas.registrar_login(tmp_path, "n@example.org", "N", "google")
    monkeypatch.setattr(contas, "POLITICA_VERSAO_VIGENTE", "2099-01-01")
    c2 = contas.registrar_login(tmp_path, "n@example.org", "N", "google")
    assert c2.politica_versao == "2099-01-01" and c2.aceite_em > c.aceite_em


def test_conta_em_exclusao_nao_tem_aceite_atualizado(tmp_path):
    _base_antiga(tmp_path, 1)
    contas.solicitar_exclusao(tmp_path, "id-0")
    assert contas.registrar_login(tmp_path, "u0@example.org", "U0", "google") is None
    assert contas.por_id(tmp_path, "id-0").politica_versao == POLITICA_NAO_REGISTRADA


def test_registro_do_aceite_nao_guarda_ip_email_nem_cookie(tmp_path):
    contas.registrar_login(tmp_path, "n@example.org", "N", "google")
    esperado = {"conta_id", "email", "nome", "provedor", "criada_em", "ultimo_acesso", "sessao_valida_desde", "exclusao_solicitada_em", "politica_versao", "aceite_em"}
    assert set(_colunas(tmp_path)) == esperado          # só as duas colunas do aceite; nada de ip, cookie, user-agent
    c = contas.por_email(tmp_path, "n@example.org")
    assert c.politica_versao == POLITICA_VERSAO_VIGENTE and "@" not in c.politica_versao
