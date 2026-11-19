# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Inferência dos esquemas T3 a partir de um snapshot publicado (uso manual, para REVISÃO humana).

    python -m tests.contracts.infer --published data/published/2026-09-20 --out /tmp/esquemas

Para cada artefato: `required` = chaves presentes em TODOS os documentos observados; `type` = união dos
tipos observados. Os esquemas versionados em `tests/contracts/schemas/` partem desta saída e são
ajustados à mão; o teste `test_t3_schemas.py` valida o dataset sintético (sempre) e o snapshot real
(quando existir). `additionalProperties` fica livre: campo novo não quebra, remoção/mudança de tipo sim.
"""
from __future__ import annotations

import argparse
import gzip
import json
from collections import defaultdict
from pathlib import Path


def jtype(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, int):
        return "integer"
    if isinstance(v, float):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    return "object"


def infer_object(objs: list[dict]) -> dict:
    n = len(objs)
    seen: dict[str, int] = defaultdict(int)
    types: dict[str, set] = defaultdict(set)
    for o in objs:
        for k, v in o.items():
            seen[k] += 1
            types[k].add(jtype(v))
    props = {}
    for k in sorted(seen):
        t = sorted(types[k])
        # inteiro cabe em number (JSON não distingue 1 de 1.0 para quem consome)
        if "integer" in t and "number" in t:
            t.remove("integer")
        props[k] = {"type": t[0] if len(t) == 1 else t}
    return {"type": "object", "required": sorted(k for k, c in seen.items() if c == n), "properties": props}


def _load(p: Path):
    if p.name.endswith(".gz"):
        return json.load(gzip.open(p, "rt", encoding="utf-8"))
    return json.load(open(p, encoding="utf-8"))


def infer_published(pub: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    asn_files = [p for p in (pub / "asns").glob("*.json") if p.stem.isdigit()]
    docs = [_load(p) for p in asn_files]
    out["asn_doc"] = infer_object(docs)
    pres = [v for d in docs for v in (d.get("ixp_presence") or {}).values()]
    out["asn_doc"]["properties"]["ixp_presence"]["additionalProperties"] = infer_object(pres)
    out["asn_index_entry"] = infer_object(_load(pub / "asns" / "index.json"))
    ixps = [_load(p) for p in (pub / "ixps").glob("*.json") if p.stem not in ("index", "_aggregate")]
    out["ixp_doc"] = infer_object(ixps)
    for afi in ("v4", "v6"):
        out["ixp_doc"]["properties"][afi] = infer_object([d[afi] for d in ixps if afi in d])
    scm = _load(pub / "scm.json.gz")
    out["scm"] = infer_object([scm])
    out["scm"]["properties"]["scms"]["items"] = infer_object(scm["scms"])
    sici = _load(pub / "sici.json.gz")
    out["sici"] = infer_object([sici])
    out["sici"]["properties"]["cnpjs"]["additionalProperties"] = infer_object(list(sici["cnpjs"].values()))
    out["manifest"] = infer_object([_load(pub / "manifest.json")])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--published", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, schema in infer_published(Path(a.published)).items():
        (out / f"{name}.schema.json").write_text(json.dumps(schema, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(name, "required:", len(schema["required"]), "props:", len(schema["properties"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
