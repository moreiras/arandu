# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""o código de IXP, usado como nome de arquivo, não pode sair de `published/`."""
from __future__ import annotations

import json

import pytest

from core import layout
from core.common import codigo_valido

CODIGOS_DO_PROJETO = ["sp", "rj", "to-old", "rr-old", "decix-rj", "4b42-ixp", "any2-west", "amsix", "a"]
MALICIOSOS = ["../x", "..", "a/b", "/etc/passwd", "a\\b", "", "SP", "a.b", "a\0b", "../../../raw/2026-09-20/summary/peeringdb-contacts", "%2e%2e/x", " sp", "a" * 65, "-sp", None, 12]


@pytest.mark.parametrize("code", CODIGOS_DO_PROJETO)
def test_codigos_reais_passam(code):
    assert codigo_valido(code)


@pytest.mark.parametrize("code", MALICIOSOS)
def test_codigos_que_saem_da_pasta_ou_fogem_do_padrao_nao_passam(code):
    assert not codigo_valido(code)


def test_layout_nao_le_fora_do_snapshot(tmp_path):
    """Mesmo que um chamador passe o `..` adiante, o leitor do layout recusa: protege todas as rotas de uma vez."""
    pub = tmp_path / "published" / "2026-09-20"
    (pub / "ixps").mkdir(parents=True)
    (pub / "ixps" / "sp.json").write_text(json.dumps({"code": "sp"}))
    segredo = tmp_path / "raw" / "2026-09-20" / "summary"
    segredo.mkdir(parents=True)
    (segredo / "peeringdb-contacts.json").write_text(json.dumps({"email": "a@b.c"}))

    assert json.loads(layout.ler_bytes(pub, "ixps/sp.json")) == {"code": "sp"}
    for rel in ("ixps/../../../raw/2026-09-20/summary/peeringdb-contacts.json", "../../raw/2026-09-20/summary/peeringdb-contacts.json", "/etc/hostname", "ixps\\..\\x.json", "ixps/sp.json\0"):
        assert layout.ler_bytes(pub, rel) is None, rel
        assert layout.caminho(pub, rel) is None and layout.existe(pub, rel) is False, rel
    atravessado = pub / "ixps" / ".." / ".." / ".." / "raw" / "2026-09-20" / "summary" / "peeringdb-contacts.json"
    assert atravessado.exists()                                              # o arquivo existe: só a barreira o protege
    assert layout.ler_bytes_de_caminho(atravessado) is None
