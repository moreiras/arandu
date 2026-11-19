# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Janela de publicação do snapshot: coleta por fonte todo dia, snapshot publicado só a cada N dias.

No modo `--due` as etapas de coleta seguem a cadência de cada fonte; sem a janela, as etapas sem fonte (análises, produtos, manifesto,
histórico) rodariam a cada execução, e o cron diário publicaria um snapshot por dia. Com ela, só rodam quando o último snapshot
publicado **antes** da data pedida tem pelo menos `intervalo` dias (ou não existe). Rodar de novo a própria data de publicação
(retomada depois de falha) continua dentro da janela, porque o que conta é o snapshot anterior, não o do dia.
"""
from __future__ import annotations

import datetime as dt
import os
import re
from pathlib import Path
from typing import Mapping, Optional

INTERVALO_PADRAO = 7
_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def intervalo_dias(env: Optional[Mapping[str, str]] = None) -> int:
    """`ARANDU_PUBLICACAO_DIAS` (padrão 7). 0 ou 1 = um snapshot a cada execução (comportamento anterior)."""
    bruto = (env if env is not None else os.environ).get("ARANDU_PUBLICACAO_DIAS", "")
    try:
        return max(0, int(bruto)) if str(bruto).strip() else INTERVALO_PADRAO
    except ValueError:
        return INTERVALO_PADRAO


def ultimo_publicado_antes(data_dir: Path, date: str) -> Optional[str]:
    """Data do snapshot publicado (pasta com manifest.json) mais recente e estritamente anterior a `date`."""
    pub = Path(data_dir) / "published"
    if not pub.is_dir():
        return None
    datas = sorted(d.name for d in pub.iterdir() if d.is_dir() and _DATA.match(d.name) and d.name < date and (d / "manifest.json").exists())
    return datas[-1] if datas else None


def janela_aberta(data_dir: Path, date: str, env: Optional[Mapping[str, str]] = None) -> tuple[bool, str]:
    """(aberta?, motivo): as etapas sem fonte rodam nesta execução?"""
    n = intervalo_dias(env)
    if n <= 1:
        return True, f"publicação a cada execução (ARANDU_PUBLICACAO_DIAS={n})"
    ult = ultimo_publicado_antes(data_dir, date)
    if ult is None:
        return True, "nenhum snapshot anterior publicado"
    dias = (dt.date.fromisoformat(date) - dt.date.fromisoformat(ult)).days
    if dias >= n:
        return True, f"último snapshot publicado em {ult} ({dias} dias; intervalo {n})"
    return False, f"fora da janela de publicação: último snapshot em {ult} ({dias} dia(s)), intervalo de {n}; a coleta por fonte segue pela cadência"


if __name__ == "__main__":
    # Para o host (scripts/arandu-weekly.sh decide se roda o Routinator avulso), sem importar o pacote: só biblioteca padrão.
    # Saída 0 = janela aberta, 1 = fechada.
    import argparse
    ap = argparse.ArgumentParser(description="a janela de publicação está aberta nesta data?")
    ap.add_argument("--date", required=True)
    ap.add_argument("--data", default=os.environ.get("DATA_DIR", "data"))
    a = ap.parse_args()
    aberta, porque = janela_aberta(Path(a.data), a.date)
    print(porque)
    raise SystemExit(0 if aberta else 1)
