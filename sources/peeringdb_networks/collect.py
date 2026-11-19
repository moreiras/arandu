# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`peeringdb_networks` — Coleta de metadados de redes BR via PeeringDB.

Para cada ASN alocado pelo Registro.br (conjunto lacnic_br_asns), consulta
GET /api/net?asn={asn} e extrai campos relevantes de política de peering,
tipo de rede e informações IRR.

Fonte:       https://www.peeringdb.com/api/net
Raw:         data/raw/{date}/summary/peeringdb-networks-{date}.json
Normalizado: data/normalized/{date}/summary/peeringdb_networks.json.gz

Uso:
    python -m sources.peeringdb_networks.collect
    python -m sources.peeringdb_networks.collect --date 2026-06-09

Variável de ambiente opcional:
    PEERINGDB_API_KEY  — aumenta o limite de rate de 250 para 1000 req/h

O coletor faz uma única requisição paginada filtrando por lista de ASNs ao invés
de consultar ASN a ASN. PeeringDB aceita ?asn__in=1,2,3 com limite de ~500 ASNs
por requisição; iteramos em lotes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import httpx

from core.common import (
    configure_logging,
    data_dir,
    normalized_path,
    now_iso,
    raw_path,
    read_json_gz,
    today_str,
    write_json_gz,
)
from core.site import USER_AGENT

PDB_BASE   = "https://www.peeringdb.com/api"
BATCH_SIZE = 500   # ASNs por requisição
_RETRY_WAIT = 65
_MAX_ATTEMPTS = 4          # ~4 min de espera acumulada em rate limit; depois falha em vez de gravar vazio
_MIN_REGISTERED_PCT = 20.0  # ~50% dos ASNs BR estão no PeeringDB; abaixo disto a coleta é suspeita


def _make_client() -> httpx.Client:
    api_key = os.environ.get("PEERINGDB_API_KEY", "")
    headers = {"User-Agent": USER_AGENT}
    if api_key:
        headers["Authorization"] = f"Api-Key {api_key}"
    return httpx.Client(headers=headers, timeout=30, follow_redirects=True)


class RateLimitedError(RuntimeError):
    """O PeeringDB continuou respondendo 429 depois de todas as retentativas."""


def _fetch_batch(client: httpx.Client, asns: list[int], log, attempts: int = _MAX_ATTEMPTS) -> list[dict]:
    """Busca metadados para um lote de ASNs. Retenta em 429 e, esgotadas as tentativas, FALHA.

    Devolver `[]` aqui (como fazia antes) corrompia o snapshot em silêncio: todo ASN ficava com
    `pdb_registered=False` (visto no snapshot de 2026-06-28)."""
    url    = f"{PDB_BASE}/net"
    params = {"asn__in": ",".join(str(a) for a in asns), "depth": 0, "status": "ok"}
    for attempt in range(attempts):
        try:
            resp = client.get(url, params=params)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            wait = 15 * (attempt + 1)
            log.warning("erro de rede", erro=type(exc).__name__, wait=wait, attempt=attempt + 1, of=attempts)
            time.sleep(wait)
            continue
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", _RETRY_WAIT))
            log.warning("rate limited", wait=wait, attempt=attempt + 1, of=attempts)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json().get("data", [])
    raise RateLimitedError(f"PeeringDB sem resposta útil (429 ou erro de rede) em {attempts} tentativas (lote de {len(asns)} ASNs)")


_BOOL_FIELDS = {"policy_ratio", "policy_contracts"}
_KEEP = {
    "asn", "name", "aka", "website",
    "info_type", "info_traffic", "info_ratio",
    "policy_general", "policy_ratio", "policy_contracts", "policy_locations",
    "irr_as_set", "info_prefixes4", "info_prefixes6",
}


def _normalize_net(raw: dict) -> dict:
    """Extrai apenas os campos relevantes de um registro /api/net do PeeringDB.

    Campos booleanos (policy_ratio, policy_contracts) são convertidos de qualquer
    truthy para bool explícito. Campos ausentes ou vazios são omitidos do resultado.
    Os campos mantidos estão definidos em _KEEP.
    """
    out: dict = {}
    for key in _KEEP:
        val = raw.get(key)
        if val is None or val == "":
            continue
        if key in _BOOL_FIELDS:
            out[key] = bool(val)
        else:
            out[key] = val
    return out


def run(date_str: str, base, log) -> dict:
    raw_dir  = raw_path(base, date_str, "summary")
    norm_dir = normalized_path(base, date_str, "summary")
    raw_dir.mkdir(parents=True, exist_ok=True)
    norm_dir.mkdir(parents=True, exist_ok=True)

    # Carrega lista de ASNs BR do LACNIC delegated
    lacnic_path = norm_dir / "lacnic_delegated.json.gz"
    if not lacnic_path.exists():
        log.error("lacnic_delegated.json.gz not found — run sources.lacnic_delegated.collect first")
        return {}

    lacnic_data = read_json_gz(lacnic_path)
    br_asns = sorted(lacnic_data.get("br_asns", []))
    log.info("br_asns loaded", total=len(br_asns))

    raw_results: list[dict] = []
    networks: dict[str, dict] = {}

    with _make_client() as client:
        for i in range(0, len(br_asns), BATCH_SIZE):
            batch = br_asns[i : i + BATCH_SIZE]
            records = _fetch_batch(client, batch, log)
            raw_results.extend(records)
            for rec in records:
                asn = rec.get("asn")
                if asn:
                    networks[str(asn)] = _normalize_net(rec)
            log.info("batch done", offset=i, fetched=len(records), total_so_far=len(networks))
            time.sleep(0.5)

    pct = round(len(networks) / len(br_asns) * 100, 1) if br_asns else 0
    if br_asns and pct < _MIN_REGISTERED_PCT:
        # Falha ALTO, antes de gravar o normalizado: os documentos de ASN tratariam um arquivo quase vazio como "ninguém
        # está no PeeringDB" e publicaria o snapshot inteiro com pdb_registered=False.
        raise RuntimeError(
            f"sanidade: apenas {len(networks)} de {len(br_asns)} ASNs BR no PeeringDB ({pct}% < "
            f"{_MIN_REGISTERED_PCT}%) — coleta descartada")

    # Raw
    raw_file = raw_dir / f"peeringdb-networks-{date_str}.json"
    raw_file.write_text(json.dumps(raw_results, ensure_ascii=False), encoding="utf-8")
    log.info("raw saved", path=str(raw_file), records=len(raw_results))

    # Normalizado
    normalized = {
        "snapshot_date": date_str,
        "generated_at":  now_iso(),
        "total_br_asns": len(br_asns),
        "pdb_registered": len(networks),
        "networks": networks,
    }
    norm_file = norm_dir / "peeringdb_networks.json.gz"
    write_json_gz(norm_file, normalized)
    log.info(
        "peeringdb_networks done",
        br_asns=len(br_asns),
        pdb_registered=len(networks),
        pct=pct,
    )
    return normalized


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="`peeringdb_networks` — coleta metadados de redes BR via PeeringDB"
    )
    parser.add_argument("--date", default=today_str(),
                        help="Data do snapshot (YYYY-MM-DD); padrão: hoje")
    args = parser.parse_args(argv)

    log  = configure_logging()
    base = data_dir()

    try:
        run(date_str=args.date, base=base, log=log)
    except httpx.HTTPStatusError as exc:
        log.error("http error", status=exc.response.status_code, url=str(exc.request.url))
        return 1
    except httpx.RequestError as exc:
        log.error("connection error", error=str(exc))
        return 1
    except Exception:
        log.exception("unexpected error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
