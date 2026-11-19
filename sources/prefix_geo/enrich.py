# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`prefix_geo` — Geolocalização de prefixos via DB-IP City Lite

Baixa o banco DB-IP City Lite (CC BY 4.0, sem chave) uma vez por mês e o armazena em
data/raw/dbip/dbip-city-lite-{YYYY-MM}.mmdb. Se o arquivo do mês ainda não foi publicado,
usa o do mês anterior.

Por padrão, geolocaliza apenas os prefixos declarados no Registro.br (`registro_br`),
mantendo o arquivo de saída em ~22k entradas (v4 + v6). Isso cobre o mapa
de prefixos BR e os dados geo exibidos nas páginas de ASN e IXP.

Para cada prefixo, consulta o banco local com o primeiro endereço IP e
produz {prefix: {lat, lon, city, country, uf, geo_confidence, geo_source}}.
A "cidade" do DB-IP às vezes é bairro: `core.geoip` a transforma em município.

Entrada:
  normalized/{date}/summary/registro_br.json.gz  (`registro_br`)

Saída:
  normalized/{date}/summary/geo_prefixes.json.gz

  geo_confidence sempre "city_centroid"
  geo_source: "dbip-lite-{YYYY-MM}"

Atribuição exigida pela licença: "IP Geolocation by DB-IP" (https://db-ip.com), nas páginas que exibem o resultado.

Uso:
    python -m sources.prefix_geo.enrich --date 2026-06-12
    python -m sources.prefix_geo.enrich --date 2026-06-12 --mmdb-month 2026-05
"""

from __future__ import annotations

import argparse
import gzip
import shutil
import sys
from ipaddress import ip_network
from pathlib import Path

import httpx
import maxminddb

from core.common import (
    configure_logging,
    data_dir,
    normalized_path,
    now_iso,
    read_json_gz,
    today_str,
    write_json_gz,
)
from core.geoip import extrair_geo
from core.site import USER_AGENT

DBIP_DOWNLOAD_URL = "https://download.db-ip.com/free/dbip-city-lite-{month}.mmdb.gz"


def _mmdb_month(date_str: str) -> str:
    """Retorna YYYY-MM a partir de YYYY-MM-DD."""
    return date_str[:7]


def _mes_anterior(month: str) -> str:
    ano, mes = int(month[:4]), int(month[5:7])
    return f"{ano - 1}-12" if mes == 1 else f"{ano}-{mes - 1:02d}"


def _mmdb_path(base: Path, month: str) -> Path:
    return base / "raw" / "dbip" / f"dbip-city-lite-{month}.mmdb"


def _download_mmdb(base: Path, month: str, log) -> tuple[Path, str]:
    """Garante o DB-IP City Lite do mês (ou do anterior, se o do mês ainda não saiu). Retorna (caminho, mês usado)."""
    for mes in (month, _mes_anterior(month)):
        path = _mmdb_path(base, mes)
        if path.exists():
            log.info("mmdb cache hit", path=str(path))
            return path, mes

        log.info("downloading DB-IP City Lite", month=mes)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".mmdb.tmp")
        with httpx.Client(timeout=300, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            r = client.get(DBIP_DOWNLOAD_URL.format(month=mes))
            if r.status_code == 404 and mes == month:
                log.warning("mmdb do mês ainda não publicado; usando o anterior", month=mes)
                continue
            r.raise_for_status()
            tmp.write_bytes(gzip.decompress(r.content))
        tmp.replace(path)                                    # escrita atômica
        log.info("mmdb saved", path=str(path), bytes=path.stat().st_size)
        return path, mes
    raise FileNotFoundError(f"DB-IP City Lite de {month} e do mês anterior indisponíveis")


def _first_ip(prefix: str) -> str:
    return str(ip_network(prefix, strict=False).network_address)


def _lookup(reader: maxminddb.Reader, prefix: str) -> dict | None:
    """Consulta o banco para o primeiro IP do prefixo. Retorna None se não encontrado."""
    try:
        return extrair_geo(reader.get(_first_ip(prefix)))
    except Exception:
        return None


def run(date_str: str, base: Path, mmdb_month: str | None, log) -> dict:
    mmdb, month = _download_mmdb(base, mmdb_month or _mmdb_month(date_str), log)

    # Carrega prefixos BR declarados no Registro.br (`registro_br`)
    registro_br_path = normalized_path(base, date_str, "summary", "registro_br.json.gz")
    if not registro_br_path.exists():
        raise FileNotFoundError(
            f"registro_br.json.gz não encontrado: {registro_br_path}. Rode a coleta registro_br primeiro."
        )

    reg = read_json_gz(registro_br_path)
    prefixes: set[str] = set()
    for asn_entry in reg.get("asns", []):
        prefixes.update(asn_entry.get("prefixes_v4", []))
        prefixes.update(asn_entry.get("prefixes_v6", []))

    if not prefixes:
        raise FileNotFoundError(
            f"Nenhum prefixo encontrado em registro_br.json.gz para {date_str}."
        )

    log.info("geolocating prefixes", total=len(prefixes), mmdb_month=month)

    geo_source = f"dbip-lite-{month}"
    result: dict[str, dict] = {}
    found = 0

    with maxminddb.open_database(str(mmdb)) as reader:
        for prefix in prefixes:
            geo = _lookup(reader, prefix)
            if geo:
                result[prefix] = {**geo,
                                   "geo_confidence": "city_centroid",
                                   "geo_source": geo_source}
                found += 1
            else:
                result[prefix] = {"lat": None, "lon": None,
                                   "geo_confidence": "unknown",
                                   "geo_source": geo_source}

    output = {
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "mmdb_month": month,
        "geo_source": geo_source,
        "total": len(result),
        "geolocated": found,
        "unknown": len(result) - found,
        "prefixes": result,
    }

    dst = normalized_path(base, date_str, "summary", "geo_prefixes.json.gz")
    write_json_gz(dst, output)
    log.info("geo_prefixes saved",
             path=str(dst), total=len(result), geolocated=found)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="`prefix_geo` — geolocalização de prefixos via DB-IP City Lite")
    parser.add_argument("--date", default=today_str())
    parser.add_argument(
        "--mmdb-month",
        default=None,
        metavar="YYYY-MM",
        help="Versão do banco DB-IP a usar (padrão: mês corrente do snapshot)",
    )
    args = parser.parse_args(argv)

    log = configure_logging()
    base = data_dir()

    try:
        run(date_str=args.date, base=base, mmdb_month=args.mmdb_month, log=log)
    except FileNotFoundError as e:
        log.error("input not found", error=str(e))
        return 1
    except Exception:
        log.exception("unexpected error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
