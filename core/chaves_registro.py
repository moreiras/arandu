# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Nomes das contagens do Registro.br no `summary.json`, no `manifest.json` e no detalhe do snapshot.

O nome com prefixo `registro_br_` é o atual; o com prefixo `m3_` segue gravado e servido ao lado dele, porque snapshots já
publicados (imutáveis) só têm o nome `m3_` e quem consome a API pode depender dele. O pipeline grava os dois; a API completa
o que faltar na leitura, para toda resposta trazer os dois nomes com o mesmo valor.
"""
from __future__ import annotations

from typing import Optional

# nome com prefixo m3_ → nome atual
PARES = {
    "m3_asns": "registro_br_asns",
    "m3_prefixes_v4": "registro_br_prefixes_v4",
    "m3_prefixes_v6": "registro_br_prefixes_v6",
    "m3_declared_space_v4": "registro_br_declared_space_v4",
    "m3_declared_space_v6": "registro_br_declared_space_v6",
    "m3_declared_space_v4_24": "registro_br_declared_space_v4_24",
    "m3_declared_space_v6_48": "registro_br_declared_space_v6_48",
}


def com_os_dois_nomes(doc: Optional[dict]) -> Optional[dict]:
    """Cópia rasa de `doc` com os dois nomes de cada par presentes (o que faltar recebe o valor do outro). Não altera `doc`;
    sem nenhum dos dois nomes de um par, o par fica de fora. `None` e não-dicionário voltam como vieram."""
    if not isinstance(doc, dict):
        return doc
    faltam = {}
    for antigo, novo in PARES.items():
        if novo in doc and antigo not in doc:
            faltam[antigo] = doc[novo]
        elif antigo in doc and novo not in doc:
            faltam[novo] = doc[antigo]
    return {**doc, **faltam} if faltam else doc
