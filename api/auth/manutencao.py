# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Manutenção diária das contas: apaga as contas cuja exclusão foi pedida há 30 dias ou mais e aplica a retenção do uso por conta.

    python -m api.auth.manutencao            # uma vez por dia (cron do servidor; idempotente)

Apaga: a conta, o e-mail do cadastro em CSV, a chave de MCP, o detalhe de uso e as linhas dela no log de acesso; as contagens agregadas
perdem o `conta_id`. Também aplica a retenção do log de acesso (`storage.RETENCAO_LOG_MESES`).
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog

from api import uso_conta
from api.auth import chaves_mcp, contas, storage

_log = structlog.get_logger(__name__)


def executar(data_dir: Path, agora: Optional[datetime] = None) -> dict:
    apagadas = 0
    for c in contas.vencidas(data_dir, agora):
        chaves_mcp.apagar_da_conta(data_dir, c.conta_id)
        uso_conta.apagar_conta(data_dir, c.conta_id)
        storage.remover_usuario(data_dir, c.email)
        storage.apagar_do_log_de_acesso(data_dir, {c.conta_id, c.email})     # linhas novas (conta_id) e antigas (e-mail)
        contas.apagar(data_dir, c.conta_id)
        apagadas += 1
        _log.info("conta_apagada", conta=c.conta_id[:8])      # só o começo do UUID; nunca e-mail
    ret = uso_conta.manutencao(data_dir, agora.date() if agora else None)
    ret["logs_de_acesso_apagados"] = storage.retencao_log_acesso(data_dir, agora.date() if agora else None)
    _log.info("manutencao_contas", contas_apagadas=apagadas, **ret)
    return {"contas_apagadas": apagadas, **ret}


def main() -> int:
    from core.common import data_dir

    executar(Path(data_dir()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
