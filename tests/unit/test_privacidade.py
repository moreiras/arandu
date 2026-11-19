# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Filtro de contatos do MCP: remove telefone e e-mail em qualquer profundidade e deixa o resto."""
from api.privacidade import e_chave_de_contato, sem_contatos


def test_chaves_de_contato_e_falsos_positivos():
    for k in ("email", "e-mail", "telefone", "phone", "ddd_telefone_1", "ddd_telefone_2", "fax", "whatsapp", "correio_eletronico", "celular", "Email"):
        assert e_chave_de_contato(k), k
    for k in ("contacts_available", "razao_social", "telefonia_movel", "cnpj", "total", "peeringdb", "receita"):
        assert not e_chave_de_contato(k), k


def test_remove_em_qualquer_profundidade_sem_alterar_o_original():
    doc = {"asn": 1, "geo_org": {"razao_social": "X", "ddd_telefone_1": "11", "socios": [{"nome": "A", "email": "a@x"}]},
           "contacts_available": {"total": 2}, "lista": [{"telefone": "1", "ok": 2}]}
    limpo = sem_contatos(doc)
    assert limpo == {"asn": 1, "geo_org": {"razao_social": "X", "socios": [{"nome": "A"}]}, "contacts_available": {"total": 2}, "lista": [{"ok": 2}]}
    assert doc["geo_org"]["ddd_telefone_1"] == "11"
