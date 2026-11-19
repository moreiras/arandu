# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cache de resultado do `query` (1.4.7.1): corpo igual (qualquer ordem de chaves) não reexecuta; datas e collections diferentes não se misturam."""
from api.services.consultas import ConsultasService


class _Loja:
    pass


def _servico():
    s = ConsultasService(_Loja())
    s.chamadas = []

    def executar(date, colecao, body):
        s.chamadas.append((date, colecao))
        return {"items": [{"x": 1}], "total": 1}

    s._executar = executar
    return s


def test_corpo_igual_nao_reexecuta_mesmo_com_outra_ordem_de_chaves():
    s = _servico()
    a = s.query("2026-10-30", "asns", {"limit": 5, "filter": {"a": 1}})
    b = s.query("2026-10-30", "asns", {"filter": {"a": 1}, "limit": 5})
    assert a is b and len(s.chamadas) == 1


def test_data_e_collection_diferentes_executam_de_novo():
    s = _servico()
    s.query("2026-10-30", "asns", {})
    s.query("2026-10-23", "asns", {})
    s.query("2026-10-30", "ixps", {})
    assert len(s.chamadas) == 3


def test_resultado_grande_nao_entra_no_cache():
    s = _servico()
    s._executar = lambda d, c, b: (s.chamadas.append(1), {"items": [{}] * 501})[1]
    s.query("2026-10-30", "asns", {})
    s.query("2026-10-30", "asns", {})
    assert len(s.chamadas) == 2
