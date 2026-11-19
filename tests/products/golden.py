# SPDX-License-Identifier: AGPL-3.0-or-later
"""Comparação com arquivos de ouro (T2): normaliza campos voláteis e mostra o diff.

Atualização consciente: `pytest tests/products --update-golden` e REVISAR o diff do git antes de commitar.
"""
import gzip
import json
from pathlib import Path

EXPECTED = Path(__file__).resolve().parents[1] / "synth" / "expected"
VOLATILE = {"generated_at", "source_file", "pipeline_version", "checksums", "receita_socios_generated_at"}


def normalize(x):
    if isinstance(x, dict):
        return {k: normalize(v) for k, v in x.items() if k not in VOLATILE}
    if isinstance(x, list):
        return [normalize(v) for v in x]
    return x


def check(base: Path, date_label: str, date: str, rel: str, update: bool) -> None:
    """Compara `published/{date}/{rel}` com `expected/published/{date_label}/{rel}` (T0/T1)."""
    src = base / "published" / date / rel
    raw = gzip.open(src, "rt", encoding="utf-8").read() if src.suffix == ".gz" else src.read_text(encoding="utf-8")
    actual = normalize(json.loads(raw))
    gold = EXPECTED / "published" / date_label / (rel[:-3] if rel.endswith(".gz") else rel)
    if update:
        gold.parent.mkdir(parents=True, exist_ok=True)
        gold.write_text(json.dumps(actual, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return
    assert gold.exists(), f"arquivo de ouro ausente: {gold} (rode com --update-golden e revise)"
    expected = json.loads(gold.read_text(encoding="utf-8"))
    assert actual == expected, f"{rel} difere do ouro ({gold}); revise com --update-golden"
