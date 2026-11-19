#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
"""
Gera config/municipios-referencia.json ({"3550308": ["São Paulo", "SP", 1523.3], ...}: nome, UF e área em km²) a partir
das APIs de localidades e de agregados (área territorial, Censo 2010) do IBGE.

Serve para transformar a "cidade" do DB-IP (que às vezes é bairro ou distrito) em município:
`core/geoip.py` casa o nome na UF e, se não casar, usa o centroide mais próximo de `municipios-centroides.json`.
Roda UMA VEZ (e de novo só quando a divisão territorial mudar). Fonte: IBGE, dados públicos.

Uso:
    python3 scripts/build-municipios-referencia.py
"""
from __future__ import annotations

import gzip
import json
import sys
import urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.site import USER_AGENT  # noqa: E402

URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
URL_AREA = "https://servicodados.ibge.gov.br/api/v3/agregados/1301/periodos/2010/variaveis/615?localidades=N6[all]"
OUT = Path(__file__).parent.parent / "config" / "municipios-referencia.json"


def _uf(m: dict) -> str:
    # Municípios têm a UF por microrregião (clássica) ou por região imediata (nova divisão).
    micro = m.get("microrregiao") or {}
    imed = m.get("regiao-imediata") or {}
    return (((micro.get("mesorregiao") or {}).get("UF") or {}).get("sigla")
            or (((imed.get("regiao-intermediaria") or {}).get("UF") or {}).get("sigla")) or "")


def _baixa(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = resp.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw)


def main() -> int:
    dados = _baixa(URL)
    areas = {e["localidade"]["id"]: float(e["serie"]["2010"])
             for e in _baixa(URL_AREA)[0]["resultados"][0]["series"] if e["serie"].get("2010", "").replace(".", "").isdigit()}
    out = {str(m["id"]): [m["nome"], _uf(m), areas.get(str(m["id"]), 0)] for m in dados if _uf(m)}
    if len(out) < 5500 or len(areas) < 5500:
        print(f"ERRO: {len(out)} municípios e {len(areas)} áreas; esperado ~5.570.", file=sys.stderr)
        return 1
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    print(f"escrito {OUT} — {len(out)} municípios, {OUT.stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
