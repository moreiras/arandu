# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Resposta JSON da API com o nome do site no lugar do nome do software.

Os artefatos do pipeline trazem textos como "n_redes conta os vínculos que o Arandurapé coletou" (limitações, metodologia, fonte), e os
snapshots publicados são imutáveis: a troca é feita na saída. É a classe padrão do app (`default_response_class`) e a que as rotas usam
quando montam a resposta à mão. Corpo sem o nome não é tocado (busca em bytes, sem decodificar).
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi.responses import JSONResponse as _JSONResponse

from core import pessoa_natural
from core.site import com_identidade_json

#: quem devolve os titulares EI/MEI do snapshot mais recente (`Store.pessoa_natural_indice`); `api.main` o liga ao `Store` do app
provedor_de_indice: Optional[Callable[[], Optional[pessoa_natural.Indice]]] = None


class JSONResponse(_JSONResponse):
    def render(self, content: Any) -> bytes:
        # D1 (PT-11): última barreira. O nome civil de empresário individual e de MEI e o ponto exato da sede não saem em resposta nenhuma, mesmo que
        # o documento lido do disco os traga (snapshots anteriores à regra, cadastro cru). Cópia: o documento do `Store` não é alterado.
        if provedor_de_indice is not None:
            content = pessoa_natural.aplicar(content, provedor_de_indice())
        corpo = super().render(content)
        if b"randurap" not in corpo and b"RANDURAP" not in corpo:
            return corpo
        return com_identidade_json(corpo.decode("utf-8")).encode("utf-8")
