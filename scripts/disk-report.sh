#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
# Relatório de uso de disco: `du` por tipo e por data, `df` (espaço) e
# `df -i` (inodes) → data/ops/disk/AAAA-MM-DD.json. Somente leitura sobre data/.
#
# Uso: bash scripts/disk-report.sh [--date AAAA-MM-DD] [--data-dir DIR] [--out-dir DIR]
# Roda ao fim do pipeline (etapa host_disk_report, scripts/host-steps.sh); pode ser executado a qualquer hora.
set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATE="$(date -u +%F)"
DATA_DIR="$REPO_DIR/data"
OUT_DIR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --date) DATE="$2"; shift 2 ;;
        --data-dir) DATA_DIR="$2"; shift 2 ;;
        --out-dir) OUT_DIR="$2"; shift 2 ;;
        *) echo "uso: $0 [--date AAAA-MM-DD] [--data-dir DIR] [--out-dir DIR]" >&2; exit 2 ;;
    esac
done
OUT_DIR="${OUT_DIR:-$DATA_DIR/ops/disk}"

[[ -d "$DATA_DIR" ]] || { echo "ERRO: $DATA_DIR não existe" >&2; exit 1; }
mkdir -p "$OUT_DIR"

# Tamanho em KiB de cada subdiretório de primeiro nível e, para os tipos datados,
# de cada data. `du -sk` e `df -Pk/-Pi` existem em Linux e macOS.
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

for d in "$DATA_DIR"/*/; do
    [[ -d "$d" ]] || continue
    name="$(basename "$d")"
    printf '%s\t%s\n' "$name" "$(du -sk "$d" 2>/dev/null | cut -f1)" >> "$TMP/by_type.tsv"
done
for t in raw normalized published; do
    [[ -d "$DATA_DIR/$t" ]] || continue
    for d in "$DATA_DIR/$t"/*/; do
        [[ -d "$d" ]] || continue
        printf '%s\t%s\t%s\n' "$t" "$(basename "$d")" "$(du -sk "$d" 2>/dev/null | cut -f1)" >> "$TMP/by_date.tsv"
    done
done
df -Pk "$DATA_DIR" 2>/dev/null | tail -1 > "$TMP/df.txt"
df -Pi "$DATA_DIR" 2>/dev/null | tail -1 > "$TMP/dfi.txt"

python3 - "$TMP" "$DATE" "$DATA_DIR" "$OUT_DIR/$DATE.json" <<'PY'
import json, os, re, sys, datetime
tmp, date, data_dir, out = sys.argv[1:5]

def read(name):
    p = os.path.join(tmp, name)
    return open(p).read() if os.path.exists(p) else ""

def to_int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None

def pct(x):
    try:
        return int(str(x).rstrip("%"))
    except (TypeError, ValueError):
        return None

by_type = {}
for ln in read("by_type.tsv").splitlines():
    name, kb = ln.split("\t")
    by_type[name] = to_int(kb)

# `by_date` só com diretórios AAAA-MM-DD; caches e pastas por fonte (geolite2, sici_cache,
# nomes fora do padrão) ficam em `outros`, para não passarem por "última data".
by_date, outros = {}, {}
for ln in read("by_date.tsv").splitlines():
    t, d, kb = ln.split("\t")
    alvo = by_date if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) else outros
    alvo.setdefault(t, {})[d] = to_int(kb)

df = read("df.txt").split()
# df -P: Filesystem 1024-blocks Used Available Capacity Mounted-on
disk = {}
if len(df) >= 6:
    disk = {"filesystem": df[0], "size_kb": to_int(df[1]), "used_kb": to_int(df[2]),
            "avail_kb": to_int(df[3]), "use_pct": pct(df[4]), "mounted_on": df[5]}
dfi = read("dfi.txt").split()
inodes = {}
if len(dfi) >= 5:
    # df -Pi: Filesystem Inodes IUsed IFree IUse% Mounted-on (macOS acrescenta colunas)
    inodes = {"total": to_int(dfi[1]), "used": to_int(dfi[2]), "free": to_int(dfi[3]),
              "use_pct": pct(dfi[4])}

doc = {
    "date": date,
    "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "data_dir": data_dir,
    "unit": "KiB",
    "data_total_kb": sum(v for v in by_type.values() if v is not None),
    "by_type": by_type,
    "by_date": by_date,
    "outros": outros,
    "df": disk,
    "inodes": inodes,
}
tmpf = out + ".tmp"
with open(tmpf, "w") as f:
    json.dump(doc, f, indent=2, sort_keys=True)
    f.write("\n")
os.replace(tmpf, out)
print(out)
PY
