# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Armazém de versões de fonte: `data/sources/<id>/<as_of>/`.

Cada coleta bem-sucedida de uma fonte vira uma **versão imutável** com `meta.json` (as_of, coletado_em, hash, tamanho,
arquivos) e uma cópia dos arquivos em `data/`. O snapshot semanal passa a *compor* a melhor versão disponível de cada
fonte (`resolver`), em vez de supor que tudo foi coletado no mesmo dia.
"""
from core.store.versions import Versao, listar, registrar, resolver, ultima_verificacao  # noqa: F401
from core.store.fontes import arquivos_da_fonte, as_of_do_dado, materializar, registrar_da_fonte  # noqa: F401
from core.store.legado import escrever_indice_legado, indice_legado, ler_indice  # noqa: F401
from core.store.manifesto import LAYOUT_VERSION, compor_fontes, fontes_do_legado  # noqa: F401
