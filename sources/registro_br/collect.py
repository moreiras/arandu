# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`registro_br` — Download e parser do nicbr-asn-blk-latest.txt

Fonte:       https://ftp.registro.br/pub/numeracao/origin/nicbr-asn-blk-latest.txt
Raw:         data/raw/{date}/summary/nicbr-asn-blk-{date}.txt.gz
Normalizado: data/normalized/{date}/summary/registro_br.json.gz

Uso:
    python -m sources.registro_br.collect
    python -m sources.registro_br.collect --date 2026-06-01
    python -m sources.registro_br.collect --date 2026-06-01 --no-diff
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import sys

import httpx

from core.common import (
    configure_logging,
    data_dir,
    normalized_path,
    now_iso,
    raw_path,
    read_json_gz,
    today_str,
    write_json_gz,
    gravar_texto_gz,
)

SOURCE_URL = "https://ftp.registro.br/pub/numeracao/origin/nicbr-asn-blk-latest.txt"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _parse_line(line: str) -> dict | None:
    """Parse uma linha pipe-delimitada. Retorna None para linhas vazias/comentário.

    Formato: AS{num}|Nome da Org|CNPJ|prefix1|prefix2|...
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    parts = line.split("|")
    asn_field = parts[0].strip()
    if not asn_field.upper().startswith("AS"):
        return None
    try:
        asn = int(asn_field[2:])
    except ValueError:
        return None

    name = parts[1].strip() if len(parts) > 1 else ""
    cnpj_raw = parts[2].strip() if len(parts) > 2 else ""
    cnpj = "".join(c for c in cnpj_raw if c.isdigit())

    prefixes_v4: list[str] = []
    prefixes_v6: list[str] = []
    for raw_prefix in parts[3:]:
        p = raw_prefix.strip()
        if not p:
            continue
        try:
            net = ipaddress.ip_network(p, strict=False)
            if net.version == 4:
                prefixes_v4.append(p)
            else:
                prefixes_v6.append(p)
        except ValueError:
            pass  # prefixo malformado — ignora sem travar o pipeline

    return {
        "asn": asn,
        "name": name,
        "cnpj": cnpj,
        "prefixes_v4": prefixes_v4,
        "prefixes_v6": prefixes_v6,
    }


def parse_text(text: str) -> list[dict]:
    """Parseia o conteúdo completo do arquivo. Retorna lista de registros."""
    records = []
    for line in text.splitlines():
        record = _parse_line(line)
        if record is not None:
            records.append(record)
    return records


# ---------------------------------------------------------------------------
# Diff entre snapshots
# ---------------------------------------------------------------------------

def diff_snapshots(prev: dict, curr: dict) -> dict:
    """Compara dois snapshots normalizados. Retorna ASNs novos, removidos e alterados."""
    prev_by_asn = {r["asn"]: r for r in prev.get("asns", [])}
    curr_by_asn = {r["asn"]: r for r in curr.get("asns", [])}

    added = [curr_by_asn[a] for a in curr_by_asn if a not in prev_by_asn]
    removed = [prev_by_asn[a] for a in prev_by_asn if a not in curr_by_asn]

    changed = []
    for asn in curr_by_asn:
        if asn not in prev_by_asn:
            continue
        c, p = curr_by_asn[asn], prev_by_asn[asn]
        if (
            c["name"] != p["name"]
            or c["cnpj"] != p["cnpj"]
            or sorted(c["prefixes_v4"]) != sorted(p["prefixes_v4"])
            or sorted(c["prefixes_v6"]) != sorted(p["prefixes_v6"])
        ):
            changed.append({"asn": asn, "before": p, "after": c})

    return {
        "snapshot_date_prev": prev.get("snapshot_date"),
        "snapshot_date_curr": curr.get("snapshot_date"),
        "added": added,
        "removed": removed,
        "changed": changed,
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
        },
    }


def _find_previous_snapshot(base, date_str: str) -> dict | None:
    """Localiza o snapshot normalizado de registro_br mais recente anterior a date_str."""
    norm_base = base / "normalized"
    if not norm_base.exists():
        return None

    candidates = sorted(
        [d.name for d in norm_base.iterdir() if d.is_dir() and d.name < date_str],
        reverse=True,
    )
    for candidate in candidates:
        path = normalized_path(base, candidate, "summary", "registro_br.json.gz")
        if path.exists():
            return read_json_gz(path)
    return None


# ---------------------------------------------------------------------------
# Execução principal
# ---------------------------------------------------------------------------

def run(date_str: str, base, compute_diff: bool, log) -> dict:
    raw_dir = raw_path(base, date_str, "summary")
    norm_dir = normalized_path(base, date_str, "summary")
    raw_dir.mkdir(parents=True, exist_ok=True)
    norm_dir.mkdir(parents=True, exist_ok=True)

    raw_file = raw_dir / f"nicbr-asn-blk-{date_str}.txt.gz"
    norm_file = norm_dir / "registro_br.json.gz"

    # Download
    log.info("downloading", url=SOURCE_URL)
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        response = client.get(SOURCE_URL)
        response.raise_for_status()

    raw_text = response.text
    sha256 = hashlib.sha256(raw_text.encode()).hexdigest()

    # Salva raw imutável
    gravar_texto_gz(raw_file, raw_text)
    log.info("raw saved", path=str(raw_file), bytes=len(raw_text), sha256=sha256[:16] + "...")

    # Parseia
    records = parse_text(raw_text)
    total_v4 = sum(len(r["prefixes_v4"]) for r in records)
    total_v6 = sum(len(r["prefixes_v6"]) for r in records)
    log.info(
        "parsed",
        total_asns=len(records),
        total_prefixes_v4=total_v4,
        total_prefixes_v6=total_v6,
    )

    normalized = {
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "source_url": SOURCE_URL,
        "source_sha256": sha256,
        "total_asns": len(records),
        "total_prefixes_v4": total_v4,
        "total_prefixes_v6": total_v6,
        "asns": records,
    }

    write_json_gz(norm_file, normalized)
    log.info("normalized saved", path=str(norm_file))

    # Diff opcional
    if compute_diff:
        prev = _find_previous_snapshot(base, date_str)
        if prev:
            delta = diff_snapshots(prev, normalized)
            diff_file = norm_dir / "registro_br_diff.json.gz"
            write_json_gz(diff_file, delta)
            log.info(
                "diff computed",
                prev_date=delta["snapshot_date_prev"],
                added=delta["summary"]["added"],
                removed=delta["summary"]["removed"],
                changed=delta["summary"]["changed"],
            )
        else:
            log.info("diff skipped — no previous snapshot found")

    return normalized


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="`registro_br` — download nicbr-asn-blk-latest.txt")
    parser.add_argument(
        "--date",
        default=today_str(),
        help="Data do snapshot (YYYY-MM-DD); padrão: hoje",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        default=True,
        help="Comparar com snapshot anterior (padrão: sim)",
    )
    parser.add_argument("--no-diff", dest="diff", action="store_false")
    args = parser.parse_args(argv)

    log = configure_logging()
    base = data_dir()

    try:
        run(date_str=args.date, base=base, compute_diff=args.diff, log=log)
    except httpx.HTTPStatusError as exc:
        log.error("download failed", status=exc.response.status_code, url=SOURCE_URL)
        return 1
    except httpx.RequestError as exc:
        log.error("connection failed", error=str(exc), url=SOURCE_URL)
        return 1
    except Exception:
        log.exception("unexpected error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
