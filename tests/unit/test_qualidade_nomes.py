# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`nomes_de`: CNPJ → nome da empresa para as tabelas de Qualidade; sem nome conhecido o CNPJ fica de fora (a tela cai para a raiz)."""
from types import SimpleNamespace

from api.routes.qualidade import nomes_de


class _Store:
    def resolve_date(self, d):
        return d or "2026-11-05"

    def _display_name_for_cnpj(self, d, cnpj):
        return {"1": "Empresa Um"}.get(cnpj, cnpj)        # a cadeia real devolve o próprio CNPJ quando não acha nome


def _req():
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(store=_Store())))


def test_nomes_so_dos_cnpjs_com_nome_e_sem_duplicar():
    assert nomes_de(_req(), None, ["1", "2", "1", "", None]) == {"1": "Empresa Um"}
