# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`lg_ixbr` — Coleta Telnet dos Looking Glasses do IX.br

Para cada IXP configurado em config/ixps.yaml, abre uma sessão Telnet,
executa os comandos BGP e salva o output bruto em:

    data/raw/{date}/{ixp}/bgp-v4-{ixp}-{date}.txt.gz
    data/raw/{date}/{ixp}/bgp-v6-{ixp}-{date}.txt.gz

Os 40 IXPs são coletados em paralelo com limite configurável de conexões
simultâneas (collection.parallel_workers em settings.yaml).

Saída adicional:
    data/raw/{date}/collection_manifest.json — resultado resumido de cada IXP

Variação de firmware:
    v4: "show ip bgp" funciona em todos os firmwares suportados
    v6: tenta FRR >= 7 → Quagga / FRR older → variante alternativa (primeiro válido)

Uso:
    python -m sources.lg_ixbr.collect
    python -m sources.lg_ixbr.collect --ixp cas laj sp
    python -m sources.lg_ixbr.collect --date 2026-06-01
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from core.common import (
    configure_logging,
    data_dir,
    gravar_texto_gz,
    load_ixps,
    load_settings,
    now_iso,
    raw_path,
    today_str,
)
from core.telnet import BGP_EMPTY_MARKER, collect_afi


# ---------------------------------------------------------------------------
# Coleta de um IXP (v4 + v6)
# ---------------------------------------------------------------------------

async def _collect_ixp(
    ixp: dict,
    date_str: str,
    base: Path,
    sem: asyncio.Semaphore,
    connect_timeout: float,
    log,
) -> dict:
    """Coleta tabelas BGP v4 e v6 de um único IXP via Telnet.

    Executado em paralelo com os demais IXPs, controlado pelo semáforo.
    Falha em um AFI não impede a coleta do outro.

    Args:
        ixp:             Entrada do ixps.yaml (code, telnet_host, timeout, ...)
        date_str:        Data do snapshot (YYYY-MM-DD)
        base:            Diretório raiz dos dados
        sem:             Semáforo para limitar conexões simultâneas
        connect_timeout: Timeout da conexão TCP (segundos)
        log:             Logger estruturado

    Returns:
        Dict com chaves "ixp", "host", "collected_at", "v4", "v6".
        Cada AFI contém {"status": "ok", "bytes": int, ...} ou {"status": "error", "error": str}.
    """
    code = ixp["code"]
    host = ixp["telnet_host"]
    port = int(ixp.get("telnet_port", 23))
    ixp_timeout = float(ixp.get("timeout", 60))
    # idle_timeout: ~1/8 do total (mín 8s) — IXPs pequenos completam rápido
    idle_timeout = max(8.0, ixp_timeout / 8)

    raw_dir = raw_path(base, date_str, code)
    raw_dir.mkdir(parents=True, exist_ok=True)

    result: dict = {
        "ixp": code,
        "host": host,
        "collected_at": now_iso(),
        "v4": {},
        "v6": {},
    }

    async with sem:
        for afi in ("v4", "v6"):
            log.info("collecting", ixp=code, afi=afi)
            afi_result = await collect_afi(
                host, port, afi, connect_timeout, idle_timeout, ixp_timeout
            )

            if afi_result["status"] == "ok":
                raw_file = raw_dir / f"bgp-{afi}-{code}-{date_str}.txt.gz"
                gravar_texto_gz(raw_file, afi_result["text"])      # ~24× menor que o texto
                size = len(afi_result["text"])
                log.info(
                    "collected",
                    ixp=code, afi=afi,
                    command=afi_result["command"],
                    bytes=size,
                )
                result[afi] = {
                    "status": "ok",
                    "command": afi_result["command"],
                    "bytes": size,
                    "path": str(raw_file),
                }
                if BGP_EMPTY_MARKER in afi_result["text"]:
                    # tabela vazia é coleta válida (0 rotas), distinta de falha
                    result[afi]["empty"] = True
            else:
                log.warning(
                    "collection failed",
                    ixp=code, afi=afi,
                    error=afi_result.get("error"),
                )
                result[afi] = {
                    "status": "error",
                    "error": afi_result.get("error", "unknown"),
                }

    return result


# ---------------------------------------------------------------------------
# Coleta de todos os IXPs em paralelo
# ---------------------------------------------------------------------------

async def run(
    date_str: str,
    base: Path,
    ixp_codes: list[str] | None = None,
    log=None,
) -> list[dict]:
    """Coleta todos os IXPs (ou subconjunto filtrado) em paralelo.

    Args:
        date_str:  Data do snapshot (YYYY-MM-DD)
        base:      Diretório raiz dos dados
        ixp_codes: Lista de códigos a coletar; None = todos os 40 IXPs
        log:       Logger estruturado

    Returns:
        Lista de resultados por IXP (ver _collect_ixp). Inclui entradas com
        status "exception" para IXPs que lançaram erros inesperados.
    """
    settings = load_settings()
    parallel_workers: int = int(
        settings.get("collection", {}).get("parallel_workers", 10)
    )
    connect_timeout: float = float(
        settings.get("collection", {}).get("connect_timeout", 15)
    )

    all_ixps = load_ixps()
    if ixp_codes:
        all_ixps = [ix for ix in all_ixps if ix["code"] in ixp_codes]

    if not all_ixps:
        if log:
            log.warning("no IXPs to collect", filter=ixp_codes)
        return []

    if log:
        log.info(
            "starting collection",
            total_ixps=len(all_ixps),
            date=date_str,
            parallel=parallel_workers,
        )

    sem = asyncio.Semaphore(parallel_workers)
    tasks = [
        _collect_ixp(ixp, date_str, base, sem, connect_timeout, log)
        for ixp in all_ixps
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    final: list[dict] = []
    for ixp, res in zip(all_ixps, results):
        if isinstance(res, Exception):
            if log:
                log.error("unexpected error", ixp=ixp["code"], error=str(res))
            final.append({"ixp": ixp["code"], "status": "exception", "error": str(res)})
        else:
            final.append(res)  # type: ignore[arg-type]

    ok = sum(
        1 for r in final
        if r.get("v4", {}).get("status") == "ok"
        or r.get("v6", {}).get("status") == "ok"
    )

    # Manifesto de coleta: usado para auditoria
    manifest_dir = raw_path(base, date_str, "")
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "snapshot_date": date_str,
        "collected_at": now_iso(),
        "total": len(final),
        "ok": ok,
        "failed": len(final) - ok,
        "ixps": final,
    }
    (manifest_dir / "collection_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if log:
        log.info("collection done", ok=ok, total=len(final))

    return final


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="`lg_ixbr` — coleta LGs do IX.br via Telnet")
    parser.add_argument("--date", default=today_str(),
                        help="Data do snapshot (YYYY-MM-DD); padrão: hoje")
    parser.add_argument("--ixp", nargs="+", metavar="CODE",
                        help="Coleta apenas estes IXPs (ex: --ixp sp rj ce)")
    args = parser.parse_args(argv)

    log = configure_logging()
    base = data_dir()

    results = asyncio.run(run(date_str=args.date, base=base, ixp_codes=args.ixp, log=log))

    ok = sum(
        1 for r in results
        if r.get("v4", {}).get("status") == "ok"
        or r.get("v6", {}).get("status") == "ok"
    )
    total = len(results)
    # Retorna 0 se ao menos 50% dos IXPs foram coletados com sucesso
    return 0 if (total == 0 or ok / total >= 0.5) else 1


if __name__ == "__main__":
    sys.exit(main())
