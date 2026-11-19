# SPDX-License-Identifier: AGPL-3.0-or-later
"""Módulo-etapa de mentira para testar o SubprocessRunner do arandu: sai com o código de ARANDU_TESTE_RC."""
import os
import sys


def main(argv=None) -> int:
    print("step_falso", argv if argv is not None else sys.argv[1:])
    return int(os.environ.get("ARANDU_TESTE_RC", "0"))


if __name__ == "__main__":
    sys.exit(main())
