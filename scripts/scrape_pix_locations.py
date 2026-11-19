#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Scraping de localização dos PIX do IX.br e geolocalização.

Fonte: https://old.ix.br/adesao/{code}
Geocoding: BrasilAPI CEP v2 (primário) → Nominatim (fallback)
Saída: config/pix.yaml

Uso:
    python scripts/scrape_pix_locations.py
    python scripts/scrape_pix_locations.py --dry-run   # só imprime, não salva
"""

from __future__ import annotations

import argparse
import html as htmlmod
import re
import sys
import time
from pathlib import Path

import httpx
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.site import USER_AGENT  # noqa: E402

REPO_DIR   = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_DIR / "config"

BRASILAPI_CEP = "https://brasilapi.com.br/api/cep/v2/{cep}"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_UA  = USER_AGENT
DELAY         = 1.2   # Nominatim: 1 req/s


# ---------------------------------------------------------------------------
# Scraping
# ---------------------------------------------------------------------------

def _clean(text: str) -> str:
    """Remove tags HTML, &nbsp; e espaços extras."""
    text = re.sub(r'<[^>]+>', '', text)
    text = htmlmod.unescape(text)
    text = text.replace('\xa0', ' ').strip()
    return text


def _is_contact_line(line: str) -> bool:
    """Linha de contato/telefone/CNPJ — não faz parte do endereço."""
    if '@' in line:
        return True
    if re.match(r'^[\+\d\s\-\(\)\.\/]+$', line) and len(line) < 25:
        return True
    if re.search(r'CNPJ', line, re.I):
        return True
    return False


def _is_org_name(line: str, address_lines_so_far: list[str]) -> bool:
    """Heurística: linha de nome da org vem antes de qualquer linha de endereço."""
    if address_lines_so_far:
        return False
    # Endereço começa com rua/av/r./travessa/praça ou número
    starts_with_street = re.match(
        r'^(r\.|rua|av\.?|avenida|al\.|alameda|trav\.|travessa|pra[çc]|estrada|rod\.?|rodovia|espl\.?'
        r'|estrada|estr\.|setor|scs|sbs|sas|qd|quadra|lote|\d)',
        line, re.I,
    )
    if starts_with_street:
        return False
    return True


def scrape_pix(code: str, client: httpx.Client) -> list[dict]:
    """Retorna lista de PIX com name, address, cep para um IXP."""
    url = f"https://old.ix.br/adesao/{code}"
    try:
        r = client.get(url, timeout=20)
        r.raise_for_status()
    except Exception as exc:
        print(f"  [WARN] {code}: fetch failed: {exc}")
        return []

    text = r.text
    pix_list: list[dict] = []

    # Cada PIX aparece como: <ul><li><b>[PIX ...]</b>...</li></ul>
    # seguido de texto com informações de contato e endereço
    parts = re.split(r'<ul[^>]*>\s*<li[^>]*>\s*<b>(\[PIX[^\]]+\])[^<]*</b>', text)
    # parts[0]=pre, parts[1]=name1, parts[2]=content1, parts[3]=name2, ...

    for i in range(1, len(parts), 2):
        name = _clean(parts[i]).strip()
        block = parts[i + 1] if i + 1 < len(parts) else ""

        # Corta no próximo <ul> (próximo PIX ou rodapé)
        next_ul = block.find('<ul')
        if next_ul > 0:
            block = block[:next_ul]

        # Divide em linhas pelo <br>
        raw_lines = re.split(r'<br\s*/?>', block)
        lines = [_clean(l) for l in raw_lines]
        lines = [l for l in lines if l and not l.startswith('<!--')]

        # Separa endereço do restante
        address_lines: list[str] = []
        for line in lines:
            if _is_contact_line(line):
                continue
            if _is_org_name(line, address_lines):
                continue
            address_lines.append(line)

        # CEP: NNNNN-NNN ou NNNNNNNN
        cep: str | None = None
        for line in lines:
            m = re.search(r'\b(\d{5})-?(\d{3})\b', line)
            if m:
                cep = m.group(1) + m.group(2)
                break

        # Remove CEP da lista de endereço (vai em campo próprio)
        address_lines = [
            l for l in address_lines
            if not re.match(r'^\d{5}-?\d{3}$', l)
        ]

        address = ', '.join(address_lines) if address_lines else ''

        pix_list.append({'name': name, 'address': address, 'cep': cep})

    return pix_list


# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------

def _geocode_cep_brasilapi(cep: str, client: httpx.Client) -> tuple[float, float] | None:
    """BrasilAPI CEP v2 — retorna (lat, lon) se disponível."""
    try:
        r = client.get(BRASILAPI_CEP.format(cep=cep), timeout=10)
        if r.status_code == 200:
            d = r.json()
            coords = (d.get('location') or {}).get('coordinates') or {}
            lat = coords.get('latitude')
            lon = coords.get('longitude')
            if lat and lon:
                return float(lat), float(lon)
    except Exception:
        pass
    return None


_nom_cache: dict[str, tuple[float, float] | None] = {}


def _geocode_nominatim(params: dict, client: httpx.Client) -> tuple[float, float] | None:
    """Nominatim — com cache simples e rate limiting."""
    key = str(sorted(params.items()))
    if key in _nom_cache:
        return _nom_cache[key]
    time.sleep(DELAY)
    try:
        p = {**params, 'format': 'jsonv2', 'limit': 1, 'countrycodes': 'br'}
        r = client.get(NOMINATIM_URL, params=p, timeout=15)
        r.raise_for_status()
        results = r.json()
        if results:
            result = (float(results[0]['lat']), float(results[0]['lon']))
            _nom_cache[key] = result
            return result
    except Exception:
        pass
    _nom_cache[key] = None
    return None


def geocode_pix(pix: dict, cep_client: httpx.Client, nom_client: httpx.Client) -> dict | None:
    """Geolocaliza um PIX. Estratégia decrescente de precisão."""
    cep = pix.get('cep')
    address = pix.get('address', '')

    # 1. CEP via BrasilAPI (retorna coordenadas quando disponíveis)
    if cep:
        coords = _geocode_cep_brasilapi(cep, cep_client)
        if coords:
            return {'lat': round(coords[0], 6), 'lon': round(coords[1], 6), 'geo_source': 'brasilapi_cep'}

    # 2. CEP via Nominatim (postalcode search — muito mais confiável que endereço)
    if cep:
        coords = _geocode_nominatim({'postalcode': f'{cep[:5]}-{cep[5:]}', 'country': 'Brazil'}, nom_client)
        if coords:
            return {'lat': round(coords[0], 6), 'lon': round(coords[1], 6), 'geo_source': 'nominatim_cep'}

    # 3. Endereço completo via Nominatim
    if address:
        coords = _geocode_nominatim({'q': address + ', Brazil'}, nom_client)
        if coords:
            return {'lat': round(coords[0], 6), 'lon': round(coords[1], 6), 'geo_source': 'nominatim_addr'}

    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Scraping de PIX do IX.br + geolocalização")
    parser.add_argument('--dry-run', action='store_true', help="Imprime resultado sem salvar")
    parser.add_argument('codes', nargs='*', help="Códigos de IXP a processar (default: todos)")
    args = parser.parse_args()

    cfg_path = CONFIG_DIR / "ixps.yaml"
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    all_codes = [ixp['code'] for ixp in cfg.get('ixps', [])]
    codes = args.codes if args.codes else all_codes

    out_pix: dict[str, list] = {}

    scrape_headers = {'User-Agent': NOMINATIM_UA}
    nom_headers    = {'User-Agent': NOMINATIM_UA}

    with httpx.Client(headers=scrape_headers, follow_redirects=True, timeout=20) as scrape_client, \
         httpx.Client(headers=scrape_headers, follow_redirects=True, timeout=15) as cep_client, \
         httpx.Client(headers=nom_headers,    follow_redirects=True, timeout=15) as nom_client:

        for code in codes:
            print(f"\n[{code}] scraping...", flush=True)
            pix_entries = scrape_pix(code, scrape_client)
            if not pix_entries:
                print(f"  nenhum PIX encontrado")
                continue

            result_list = []
            for pix in pix_entries:
                print(f"  {pix['name']} | cep={pix['cep']} | addr={pix['address'][:60]}")
                geo = geocode_pix(pix, cep_client, nom_client)
                if geo:
                    print(f"    → lat={geo['lat']}, lon={geo['lon']} ({geo['geo_source']})")
                else:
                    print(f"    → não geolocalizou")

                entry: dict = {'name': pix['name']}
                if pix['address']:
                    entry['address'] = pix['address']
                if pix['cep']:
                    entry['cep'] = pix['cep']
                if geo:
                    entry['lat'] = geo['lat']
                    entry['lon'] = geo['lon']
                result_list.append(entry)

            out_pix[code] = result_list

    if not out_pix:
        print("\nNenhum dado coletado.")
        return 1

    pix_config = {'pix': out_pix}
    out_yaml = "# PIX (Pontos de Intercâmbio) do IX.br — localização física\n"
    out_yaml += "# Gerado por scripts/scrape_pix_locations.py\n"
    out_yaml += "# Fonte: https://old.ix.br/adesao/{code}\n\n"
    out_yaml += yaml.dump(pix_config, allow_unicode=True, default_flow_style=False, sort_keys=False)

    if args.dry_run:
        print("\n--- pix.yaml (dry-run) ---")
        print(out_yaml)
    else:
        out_path = CONFIG_DIR / "pix.yaml"
        out_path.write_text(out_yaml, encoding='utf-8')
        print(f"\nSalvo em: {out_path}")
        print(f"Total: {sum(len(v) for v in out_pix.values())} PIX em {len(out_pix)} IXPs")

    return 0


if __name__ == '__main__':
    sys.exit(main())
