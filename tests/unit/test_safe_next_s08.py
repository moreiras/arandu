# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""o `next` do login só pode levar a uma rota deste site."""
import pytest

from api.auth.router import _safe_next


@pytest.mark.parametrize("url", ["/", "/asn/28573", "/operadora/00000000000191?aba=mercado", "/ixp/sp#bloco-peers", "/busca?q=a%2Fb"])
def test_rotas_do_site_passam(url):
    assert _safe_next(url) == url


@pytest.mark.parametrize("url", ["//exemplo.org", "//exemplo.org/x", "/\\exemplo.org", "/\\/exemplo.org", "https://exemplo.org", "http:/x", "javascript:alert(1)",
                                 "exemplo.org", "", None, "/\t/exemplo.org", "/\n/exemplo.org", "/\x00x", "\\\\exemplo.org"])
def test_destinos_fora_do_site_viram_raiz(url):
    assert _safe_next(url) == "/"
