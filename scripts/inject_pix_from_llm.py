#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Injeta dados de PIX extraídos manualmente (via LLM) no pix.yaml
para IXPs que o scraper não conseguiu processar.

Edite o dict LLM_DATA abaixo com os dados extraídos, depois rode:
    python scripts/inject_pix_from_llm.py
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
DELAY = 1.2
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

# Dados extraídos via LLM para IXPs que o scraper não conseguiu parsear
LLM_DATA: dict[str, list[dict]] = {
    "mg": [
        {"name": "[PIX RNP / POP-MG]",      "address": "Av. Antônio Carlos, 6627 - Pampulha, Belo Horizonte, MG",    "cep": "31270010"},
        {"name": "[PIX PRODABEL]",           "address": "Rua Espírito Santo, 605 - Centro, Belo Horizonte, MG",       "cep": "30160919"},
        {"name": "[PIX ALGAR]",              "address": "Rua Pirapetinga, 322 - Serra, Belo Horizonte, MG",           "cep": "30220150"},
        {"name": "[PIX CENTURY TELECOM]",    "address": "Rua José Permínio da Silva, 80 - Contagem, MG",             "cep": "32341590"},
        {"name": "[PIX SEMPRE TELEPORTO]",   "address": "Av. Marcelo Diniz Xavier, 649 - Califórnia, Belo Horizonte, MG", "cep": "30855075"},
        {"name": "[PIX ELETRONET]",          "address": "Rua Falcão, 722 - Barreiro, Belo Horizonte, MG",            "cep": "30624200"},
    ],
    "lda": [
        {"name": "[PIX UEL]",           "address": "Rodovia Celso Garcia Cid - PR 445 Km 380 - Campus Universitário, Londrina - PR", "cep": "86055900"},
        {"name": "[PIX PERSIS TELECOM]","address": "Av. Jules Verne, 1111 - Pq Industrial Cacique, Londrina - PR",   "cep": "86072450"},
        {"name": "[PIX SERCOMTEL]",     "address": "Rua Prof. João Cândido, 555 - Centro, Londrina - PR",            "cep": "86010000"},
    ],
    "pr": [
        {"name": "[PIX RNP / POP-PR]",  "address": "R. Francisco H. dos Santos, 100, Jardim das Américas, Curitiba - PR", "cep": "81530900"},
        {"name": "[PIX Cirion]",        "address": "Rua do Semeador, 350, C.I.C, Curitiba - PR",                     "cep": "81270050"},
        {"name": "[PIX Elea-CTA1]",     "address": "Tv. Teixeira de Freitas, 75, Mercês, Curitiba - PR",             "cep": "80410905"},
        {"name": "[PIX LIGGA TELECOM]", "address": "Rua Augusto Stresser, 453, Alto da Glória, Curitiba - PR",       "cep": "80040310"},
        {"name": "[PIX CELEPAR]",       "address": "R. Mateus Leme, 1561, Bom Retiro, Curitiba - PR",                "cep": "80530010"},
        {"name": "[PIX BR.Digital]",    "address": "Rua Professor Rubens Elke Braga, 107, Bairro Parolin, Curitiba - PR", "cep": "80220320"},
        {"name": "[PIX DBUG]",          "address": "Rua José de Alencar, 60, Cristo Rei, Curitiba - PR",             "cep": "80050240"},
    ],
}


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


def geocode_entry(entry: dict, client: httpx.Client) -> None:
    if entry.get("lat") is not None:
        return
    cep  = str(entry.get("cep") or "").replace("-", "").strip()
    addr = entry.get("address", "")
    coords = None
    if len(cep) == 8:
        coords = _nom({'postalcode': f'{cep[:5]}-{cep[5:]}', 'country': 'Brazil'}, client)
    if coords is None and addr:
        coords = _nom({'q': addr + ', Brazil'}, client)
    if coords:
        entry["lat"] = round(coords[0], 6)
        entry["lon"] = round(coords[1], 6)
        print(f"    → {coords[0]:.4f}, {coords[1]:.4f}")
    else:
        print(f"    → não geolocalizou")


def main() -> int:
    pix_path = CONFIG_DIR / "pix.yaml"
    if not pix_path.exists():
        print("pix.yaml não encontrado — execute scrape_pix_locations.py primeiro")
        return 1

    cfg = yaml.safe_load(pix_path.read_text()) or {}
    raw: dict = cfg.setdefault("pix", {})

    with httpx.Client(headers={"User-Agent": NOMINATIM_UA}, follow_redirects=True) as client:
        for code, entries in LLM_DATA.items():
            if code in raw and raw[code]:
                print(f"[{code}] já tem {len(raw[code])} entradas — pulando")
                continue
            print(f"\n[{code}] injetando {len(entries)} entradas...")
            geocoded = []
            for entry in entries:
                entry = dict(entry)  # cópia
                print(f"  {entry['name']}")
                geocode_entry(entry, client)
                geocoded.append(entry)
            raw[code] = geocoded

    out = "# PIX (Pontos de Intercâmbio) do IX.br — localização física\n"
    out += "# Gerado por scripts/scrape_pix_locations.py\n"
    out += "# Fonte: https://old.ix.br/adesao/{code}\n\n"
    out += yaml.dump(cfg, allow_unicode=True, default_flow_style=False, sort_keys=False)
    pix_path.write_text(out)
    print(f"\nSalvo em: {pix_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
