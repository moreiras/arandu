# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Serviços sobre o `Store`: cada um guarda os caches e a lógica de um assunto; o `Store` é a fachada."""


def delegar(cls, servico: str, *nomes: str) -> None:
    """Dá a `cls` os métodos `nomes` que repassam a chamada, sem mudar argumentos, ao atributo `servico` da instância."""
    for nome in nomes:
        def metodo(self, *args, _s=servico, _n=nome, **kwargs):
            return getattr(getattr(self, _s), _n)(*args, **kwargs)

        metodo.__name__ = metodo.__qualname__ = nome
        setattr(cls, nome, metodo)


def delegar_como(cls, servico: str, nomes: dict[str, str]) -> None:
    """Como `delegar`, para quando o método do repositório tem outro nome: `{nome no cls: nome no serviço}`."""
    for nome, destino in nomes.items():
        def metodo(self, *args, _s=servico, _n=destino, **kwargs):
            return getattr(getattr(self, _s), _n)(*args, **kwargs)

        metodo.__name__ = metodo.__qualname__ = nome
        setattr(cls, nome, metodo)
