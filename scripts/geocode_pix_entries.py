#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Geocodifica entradas de pix.yaml que ainda não têm lat/lon.
Usa CEP via Nominatim (postalcode search) → Nominatim address → desiste.

Uso:
    python scripts/geocode_pix_entries.py
"""

from __future__ import annotations
import sys, time
from pathlib import Path
import httpx
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.site import USER_AGENT  # noqa: E402

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_UA  = USER_AGENT
DELAY         = 1.2

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _nom(params: dict, client: httpx.Client) -> tuple[float, float] | None:
    time.sleep(DELAY)
    try:
        r = client.get(NOMINATIM_URL,
                       params={**params, 'format': 'jsonv2', 'limit': 1, 'countrycodes': 'br'},
                       timeout=15)
        r.raise_for_status()
        res = r.json()
        if res:
            return float(res[0]['lat']), float(res[0]['lon'])
    except Exception:
        pass
    return None


def main() -> int:
    pix_path = CONFIG_DIR / "pix.yaml"
    if not pix_path.exists():
        print("pix.yaml não encontrado")
        return 1

    cfg = yaml.safe_load(pix_path.read_text()) or {}
    raw: dict = cfg.get("pix") or {}

    changed = 0
    with httpx.Client(headers={"User-Agent": NOMINATIM_UA}, follow_redirects=True) as client:
        for code, entries in raw.items():
            for entry in (entries or []):
                if entry.get("lat") is not None:
                    continue
                name = entry.get("name", "")
                cep = str(entry.get("cep") or "").replace("-", "").strip()
                addr = entry.get("address", "")

                coords = None
                if len(cep) == 8:
                    coords = _nom({'postalcode': f'{cep[:5]}-{cep[5:]}', 'country': 'Brazil'}, client)
                if coords is None and addr:
                    coords = _nom({'q': addr + ', Brazil'}, client)

                if coords:
                    entry["lat"] = round(coords[0], 6)
                    entry["lon"] = round(coords[1], 6)
                    print(f"  [{code}] {name}: {coords[0]:.4f}, {coords[1]:.4f}")
                    changed += 1
                else:
                    print(f"  [{code}] {name}: não geolocalizou")

    if changed:
        out = "# PIX (Pontos de Intercâmbio) do IX.br — localização física\n"
        out += "# Gerado por scripts/scrape_pix_locations.py\n"
        out += "# Fonte: https://old.ix.br/adesao/{code}\n\n"
        out += yaml.dump(cfg, allow_unicode=True, default_flow_style=False, sort_keys=False)
        pix_path.write_text(out)
        print(f"\n{changed} entradas geocodificadas. Salvo em {pix_path}")
    else:
        print("Nenhuma entrada nova para geocodificar.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
