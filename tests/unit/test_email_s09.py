# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""e-mail não confirmado pelo provedor é recusado; maiúsculas não criam outra conta."""
import pytest

from api.auth import contas
from api.auth.router import _email_confirmado


@pytest.mark.parametrize("userinfo,campo,esperado", [
    ({"email": "Fulano@Exemplo.org", "email_verified": True}, "email_verified", ("fulano@exemplo.org", None)),
    ({"email": "fulano@exemplo.org"}, "email_verified", ("fulano@exemplo.org", None)),                         # sem o campo: aceita
    ({"email": "fulano@exemplo.org", "email_verified": False}, "email_verified", (None, "email_nao_verificado")),
    ({"email": "fulano@exemplo.org", "email_verified": "false"}, "email_verified", (None, "email_nao_verificado")),
    ({"email": "fulano@exemplo.org", "verified_email": False}, "verified_email", (None, "email_nao_verificado")),   # PeeringDB
    ({"email": " fulano@exemplo.org ", "verified_email": True, "verified_user": False}, "verified_email", ("fulano@exemplo.org", None)),
    ({"email": ""}, "email_verified", (None, "no_email")), ({}, "verified_email", (None, "no_email")),
])
def test_email_confirmado(userinfo, campo, esperado):
    assert _email_confirmado(userinfo, campo) == esperado


def test_maiusculas_nao_criam_outra_conta_e_conta_antiga_continua_achada(tmp_path):
    with contas._db(tmp_path) as con:                     # conta antiga, gravada antes da normalização
        con.execute("INSERT INTO contas (conta_id, email, nome, provedor, criada_em, ultimo_acesso) VALUES "
                    "('c-antiga','Fulano@Exemplo.org','F','google','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')")
    c = contas.registrar_login(tmp_path, "fulano@exemplo.org", "F", "google")
    assert c.conta_id == "c-antiga"
    assert contas.por_email(tmp_path, "FULANO@exemplo.org").conta_id == "c-antiga"
    nova = contas.registrar_login(tmp_path, "Beltrano@Exemplo.org", "B", "linkedin")
    assert nova.email == "beltrano@exemplo.org" and contas.registrar_login(tmp_path, "beltrano@exemplo.org", "B", "google").conta_id == nova.conta_id
