# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T2 — originadores por PTT são a união IPv6 ∪ IPv4 (IXP-E3, IXPS-E1), não o maior dos dois."""
import gzip
import json

from tests.synth.world import T1


def _origem(base, code, afi):
    p = base / "normalized" / T1 / code / f"routes-{afi}.json.gz"
    if not p.exists():
        return set()
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return set((json.load(f).get("relationships") or {}).get("asn_origin", []))


def test_originadores_do_ptt_sao_a_uniao_das_familias(pipeline):
    base, _ = pipeline
    idx = json.loads((base / "published" / T1 / "ixps" / "index.json").read_text(encoding="utf-8"))
    assert idx
    algum_estrito = False
    for e in idx:
        v4, v6 = _origem(base, e["code"], "v4"), _origem(base, e["code"], "v6")
        n4 = e["v4"].get("asn_origin_count", 0) if "total_routes" in e["v4"] else 0
        n6 = e["v6"].get("asn_origin_count", 0) if "total_routes" in e["v6"] else 0
        u = e["asn_origin_union_count"]
        assert u == len(v4 | v6), e["code"]
        assert max(n4, n6) <= u <= n4 + n6, e["code"]
        assert e["br_asns_origin_union_count"] <= u, e["code"]                        # o subconjunto BR nunca passa do total
        algum_estrito |= u > max(n4, n6)
        doc = json.loads((base / "published" / T1 / "ixps" / f"{e['code']}.json").read_text(encoding="utf-8"))
        assert doc["asn_origin_union_count"] == u and "_asn_origin" not in doc["v4"] and "_asn_origin" not in doc["v6"]
    assert algum_estrito, "o dataset deveria ter um PTT com origens diferentes em IPv6 e IPv4"
    agg = json.loads((base / "published" / T1 / "ixps" / "_aggregate.json").read_text(encoding="utf-8"))
    todas = set().union(*(_origem(base, e["code"], afi) for e in idx for afi in ("v4", "v6")))
    assert agg["asn_origin_union_count"] == len(todas)
