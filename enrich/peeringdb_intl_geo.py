# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Atalho de compatibilidade: este módulo foi movido para `sources.peeringdb_intl_geo.enrich`.

Use o nome novo.
"""
import importlib
import sys
import warnings

warnings.warn("enrich.peeringdb_intl_geo foi movido para sources.peeringdb_intl_geo.enrich; use o nome novo",
              DeprecationWarning, stacklevel=2)

if __name__ == "__main__":
    import runpy

    runpy.run_module("sources.peeringdb_intl_geo.enrich", run_name="__main__")
else:
    sys.modules[__name__] = importlib.import_module("sources.peeringdb_intl_geo.enrich")
