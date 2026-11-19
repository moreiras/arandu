# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`peeringdb_contacts` — Coleta de contatos de redes BR via PeeringDB (/poc).

Para cada ASN BR já presente em peeringdb_networks.json.gz, consulta
GET /api/poc?net__asn__in={asns}&depth=1
e extrai nome, telefone, e-mail, role e URL.

depth=1 inclui o objeto `net` completo com o campo `asn`, necessário para
correlacionar o contato ao ASN sem uma segunda round-trip.

Fonte:       https://www.peeringdb.com/api/poc
Raw:         data/raw/{date}/summary/peeringdb-contacts-requisicoes-{date}.json (só as requisições; os contatos não vão para raw/)
Normalizado: data/normalized/{date}/summary/peeringdb_contacts.json.gz

Uso:
    python -m sources.peeringdb_contacts.collect
    python -m sources.peeringdb_contacts.collect --date 2026-06-24

Variável de ambiente opcional:
    PEERINGDB_API_KEY  — aumenta limite de rate de 250 para 1000 req/h
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

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
BATCH_SIZE = 100   # ASNs por requisição (depth=1 gera respostas maiores)
_RETRY_WAIT = 65
_NET_WAIT = 15      # segundos × nº da tentativa após timeout/erro de rede
_MAX_ATTEMPTS = 4


def _make_client() -> httpx.Client:
    api_key = os.environ.get("PEERINGDB_API_KEY", "")
    headers = {"User-Agent": USER_AGENT}
    if api_key:
        headers["Authorization"] = f"Api-Key {api_key}"
    return httpx.Client(headers=headers, timeout=60, follow_redirects=True)


class RateLimitedError(RuntimeError):
    """O PeeringDB continuou limitando (429) ou sem responder depois de todas as retentativas."""


def _get(client: httpx.Client, url: str, params: dict, log, attempts: int = _MAX_ATTEMPTS) -> list[dict]:
    """GET que repete em 429 e em erro de rede/timeout e, esgotadas as tentativas, FALHA.

    Antes devolvia `[]` depois de dois 429: o lote inteiro de contatos sumia do snapshot em silêncio."""
    ultimo = "429"
    for attempt in range(attempts):
        try:
            resp = client.get(url, params=params)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            ultimo = type(exc).__name__
            wait = _NET_WAIT * (attempt + 1)
            log.warning("erro de rede", erro=ultimo, wait=wait, attempt=attempt + 1, of=attempts)
            time.sleep(wait)
            continue
        if resp.status_code == 429:
            ultimo = "429"
            wait = int(resp.headers.get("Retry-After", _RETRY_WAIT))
            log.warning("rate limited", wait=wait, attempt=attempt + 1, of=attempts)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json().get("data", [])
    raise RateLimitedError(f"PeeringDB sem resposta útil em {attempts} tentativas ({url}; último: {ultimo})")


def _fetch_net_id_map(client: httpx.Client, asns: list[int], log) -> dict[int, int]:
    """Mapa net_id → asn para um lote de ASNs (GET /api/net).

    Necessário porque /api/poc retorna apenas `net_id` (o objeto `net` não vem
    expandido), e o índice peeringdb_networks não guarda o id da rede.
    """
    data = _get(client, f"{PDB_BASE}/net", {
        "asn__in": ",".join(str(a) for a in asns),
        "fields": "id,asn",
    }, log)
    return {n["id"]: n["asn"] for n in data if n.get("id") and n.get("asn")}


def _fetch_batch(client: httpx.Client, asns: list[int], log) -> list[dict]:
    """Busca os contatos (POC) de visibilidade `Public` de um lote de ASNs.

    Só `Public`: `Users` é o que o dono da rede restringiu a usuários autenticados do PeeringDB, e o
    site tem uma classe única de usuário logado (Google, LinkedIn ou PeeringDB, sem distinção), então não há como honrar essa restrição aqui."""
    return _get(client, f"{PDB_BASE}/poc", {
        "net__asn__in": ",".join(str(a) for a in asns),
        "visible":      "Public",
    }, log)


# `visible` vai junto para a leitura (api/services/operadoras.py) conferir: só `Public` é servido, mesmo que a API mude o filtro.
_POC_KEEP = {"name", "phone", "email", "role", "url", "visible"}


def _normalize_poc(raw: dict, netid_to_asn: dict[int, int]) -> dict | None:
    """Extrai contato + ASN (via net_id). None se o net_id não mapeia para ASN."""
    asn = netid_to_asn.get(raw.get("net_id"))
    if not asn:
        return None
    out: dict = {"asn": asn}
    for k in _POC_KEEP:
        v = raw.get(k)
        if v:
            out[k] = v
    return out


def run(date_str: str, base: Path, log) -> dict:
    raw_dir  = raw_path(base, date_str, "summary")
    norm_dir = normalized_path(base, date_str, "summary")
    raw_dir.mkdir(parents=True, exist_ok=True)
    norm_dir.mkdir(parents=True, exist_ok=True)

    # Carrega lista de ASNs BR com registro no PeeringDB
    pdb_path = norm_dir / "peeringdb_networks.json.gz"
    if not pdb_path.exists():
        log.error("peeringdb_networks.json.gz not found — run sources.peeringdb_networks.collect first")
        return {}

    pdb_data = read_json_gz(pdb_path)
    br_asns  = [int(asn) for asn in pdb_data.get("networks", {}).keys()]
    log.info("br_asns with pdb loaded", total=len(br_asns))

    manifesto: list[dict] = []
    # contacts: {str(asn): [poc_dict, ...]}
    contacts: dict[str, list[dict]] = {}

    with _make_client() as client:
        for i in range(0, len(br_asns), BATCH_SIZE):
            batch = br_asns[i : i + BATCH_SIZE]
            netid_to_asn = _fetch_net_id_map(client, batch, log)
            pocs  = _fetch_batch(client, batch, log)
            manifesto.append({"recurso": "poc", "asns_no_lote": len(batch), "linhas": len(pocs)})

            for poc in pocs:
                normalized = _normalize_poc(poc, netid_to_asn)
                if normalized is None:
                    continue
                asn_str = str(normalized.pop("asn"))
                if asn_str not in contacts:
                    contacts[asn_str] = []
                contacts[asn_str].append(normalized)

            log.info("batch done", offset=i, fetched=len(pocs), asns_with_contacts=len(contacts))
            time.sleep(0.5)

    # O bruto NÃO é gravado (traria nome, e-mail e telefone para raw/, que é imutável): só o manifesto das requisições, como no peeringdb_fac.
    raw_file = raw_dir / f"peeringdb-contacts-requisicoes-{date_str}.json"
    raw_file.write_text(json.dumps(manifesto, ensure_ascii=False), encoding="utf-8")
    log.info("manifesto salvo", path=str(raw_file), requisicoes=len(manifesto))

    normalized_data = {
        "snapshot_date":       date_str,
        "generated_at":        now_iso(),
        "total_asns_queried":  len(br_asns),
        "asns_with_contacts":  len(contacts),
        "contacts":            contacts,
    }
    norm_file = norm_dir / "peeringdb_contacts.json.gz"
    write_json_gz(norm_file, normalized_data)
    log.info(
        "peeringdb_contacts done",
        asns_queried=len(br_asns),
        asns_with_contacts=len(contacts),
        pct=round(len(contacts) / len(br_asns) * 100, 1) if br_asns else 0,
    )
    return normalized_data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="`peeringdb_contacts` — coleta contatos PeeringDB (POC)")
    parser.add_argument("--date", default=today_str(),
                        help="Data do snapshot (YYYY-MM-DD); padrão: hoje")
    args = parser.parse_args(argv)

    log  = configure_logging()
    base = data_dir()

    try:
        run(date_str=args.date, base=base, log=log)
    except Exception:
        log.exception("unexpected error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
