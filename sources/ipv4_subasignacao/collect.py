# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Bitácora de sub-asignações de IPv4 (política LAC-2025-5): **adaptador pronto e DESATIVADO**, com esquema hipotético (`core/ipv4_subasignacao.py`).

Fonte:       a bitácora pública que o LACNIC/Registro.br vão publicar; formato ainda desconhecido em 2026-11-02. O vigia (`sources/ipv4_vigia`) avisa quando surgir arquivo novo.
Ativação:    defina `ARANDU_SUBASIGNACAO_URL` (e `ARANDU_SUBASIGNACAO_FORMATO=json|csv`, padrão json) depois de conferir o formato real e ajustar o `parse`; sem a URL, nada é coletado.
Normalizado: data/normalized/{date}/summary/ipv4_subasignacoes.json.gz   {registros: [...], ignoradas, url, sha256}

Uso:
    ARANDU_SUBASIGNACAO_URL=https://... python -m sources.ipv4_subasignacao.collect --date 2026-11-02
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path
from typing import Optional

import httpx

from core import ipv4_subasignacao as S
from core.common import configure_logging, data_dir, normalized_path, now_iso, raw_path, today_str, write_json_gz
from core.site import USER_AGENT

HEADERS = {"User-Agent": USER_AGENT}


def run(date_str: str, base: Path, log, client: Optional[httpx.Client] = None, url: Optional[str] = None) -> dict:
    url = url if url is not None else os.environ.get("ARANDU_SUBASIGNACAO_URL", "").strip()
    if not url:
        log.info("ipv4_subasignacao desativada: sem ARANDU_SUBASIGNACAO_URL (aguardando a bitácora oficial da LAC-2025-5)")
        return {"ativa": False}
    formato = os.environ.get("ARANDU_SUBASIGNACAO_FORMATO", "json").lower()
    proprio = client is None
    client = client or httpx.Client(timeout=120, follow_redirects=True, headers=HEADERS)
    try:
        r = client.get(url)
        r.raise_for_status()
    finally:
        if proprio:
            client.close()
    bruto = raw_path(base, date_str, "summary")
    bruto.mkdir(parents=True, exist_ok=True)
    (bruto / f"ipv4-subasignacoes-{date_str}.raw").write_bytes(r.content)
    regs, ign = S.parse(r.content, formato)
    if ign:
        log.warning("ipv4_subasignacao: registros ignorados", n=len(ign), exemplo=ign[0][:160])
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / "ipv4_subasignacoes.json.gz", {"snapshot_date": date_str, "generated_at": now_iso(), "url": url, "formato": formato, "sha256": hashlib.sha256(r.content).hexdigest(),
                                                           "ignoradas": len(ign), "registros": regs})
    log.info("ipv4_subasignacao written", registros=len(regs), ignoradas=len(ign))
    return {"ativa": True, "registros": len(regs), "ignoradas": len(ign)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Bitácora de sub-asignações de IPv4 (adaptador desativado até haver fonte oficial)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        print(run(a.date, data_dir(), log))
    except Exception:
        log.exception("falha em ipv4_subasignacao")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
