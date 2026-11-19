# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T3 — contrato dos artefatos publicados (esquemas JSON em tests/contracts/schemas/).

Valida o publicado do dataset sintético (sempre) e, quando existir, uma amostra do snapshot real
(`ARANDU_REAL_PUBLISHED`, padrão o mais recente em `data/published/`; pulado se ausente — o CI não tem `data/`).
Campo novo é permitido; remoção de campo exigido ou mudança de tipo falha.
"""
import copy
import gzip
import json
import os
import random
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tests.synth.world import T0, T1

SCHEMAS = Path(__file__).resolve().parents[1] / "contracts" / "schemas"
ROOT = Path(__file__).resolve().parents[2]


def schema(name):
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))


def validator(name):
    s = schema(name)
    Draft202012Validator.check_schema(s)
    return Draft202012Validator(s)


def load(p: Path):
    if p.name.endswith(".gz"):
        return json.load(gzip.open(p, "rt", encoding="utf-8"))
    return json.loads(p.read_text(encoding="utf-8"))


def errors(v, doc, label):
    out = [f"{label}: {'/'.join(map(str, e.absolute_path)) or '/'} — {e.message[:140]}" for e in v.iter_errors(doc)]
    return out[:5]


def check_published(pub: Path, sample_asns: int | None = None) -> list[str]:
    errs: list[str] = []
    asn_files = sorted(p for p in (pub / "asns").glob("*.json") if p.stem.isdigit())
    if sample_asns and len(asn_files) > sample_asns:
        asn_files = random.Random(7).sample(asn_files, sample_asns)
    va = validator("asn_doc")
    for p in asn_files:
        errs += errors(va, load(p), f"asns/{p.name}")
    vi = validator("asn_index_entry")
    index = load(pub / "asns" / "index.json")
    for row in (index if not sample_asns else index[:2000]):
        errs += errors(vi, row, f"asns/index.json asn={row.get('asn')}")
        if len(errs) > 20:
            break
    vx = validator("ixp_doc")
    for p in sorted((pub / "ixps").glob("*.json")):
        if p.stem not in ("index", "_aggregate"):
            errs += errors(vx, load(p), f"ixps/{p.name}")
    for name, rel in (("scm", "scm.json.gz"), ("sici", "sici.json.gz"), ("manifest", "manifest.json")):
        errs += errors(validator(name), load(pub / rel), rel)
    return errs


@pytest.mark.parametrize("data", [T0, T1])
def test_publicado_sintetico_cumpre_os_esquemas(pipeline, data):
    base, _ = pipeline
    assert check_published(base / "published" / data) == []


def test_publicado_real_cumpre_os_esquemas():
    env = os.environ.get("ARANDU_REAL_PUBLISHED")
    if env:
        pub = Path(env)
    else:                                           # o snapshot real mais recente que existir em data/published
        datas = sorted(p for p in (ROOT / "data" / "published").glob("20??-??-??") if (p / "manifest.json").exists()) \
            if (ROOT / "data" / "published").exists() else []
        pub = datas[-1] if datas else ROOT / "data" / "published" / "ausente"
    if not (pub / "manifest.json").exists():
        pytest.skip("snapshot real ausente (data/published/…); T3 sobre dado real roda só localmente")
    assert check_published(pub, sample_asns=1500) == []


def _amostra(pub: Path, name: str):
    if name == "asn_doc":
        return load(sorted(p for p in (pub / "asns").glob("*.json") if p.stem.isdigit())[0])
    if name == "asn_index_entry":
        return load(pub / "asns" / "index.json")[0]
    if name == "ixp_doc":
        return load(sorted(p for p in (pub / "ixps").glob("*.json") if p.stem not in ("index", "_aggregate"))[0])
    return load(pub / {"scm": "scm.json.gz", "sici": "sici.json.gz", "manifest": "manifest.json"}[name])


@pytest.mark.parametrize("name,campo", [
    ("asn_doc", "ixp_presence"), ("asn_doc", "global_prefixes_v4"), ("asn_index_entry", "has_rpki"),
    ("ixp_doc", "snapshot_date"), ("scm", "scms"), ("sici", "cnpjs"), ("manifest", "ixps_collected"),
])
def test_esquema_barra_remocao_de_campo_exigido(pipeline, name, campo):
    base, _ = pipeline
    doc = _amostra(base / "published" / T1, name)
    v = validator(name)
    assert not list(v.iter_errors(doc)), "amostra sintética deveria cumprir o esquema"
    assert campo in doc and campo in schema(name)["required"]
    sem = {k: x for k, x in doc.items() if k != campo}
    assert any("required property" in e.message for e in v.iter_errors(sem))


def test_esquema_barra_mudanca_de_tipo(pipeline):
    base, _ = pipeline
    doc = load(base / "published" / T1 / "manifest.json")
    ruim = copy.deepcopy(doc)
    ruim["total_asns_br"] = "muitos"
    assert errors(validator("manifest"), doc, "m") == []
    assert errors(validator("manifest"), ruim, "m")
