# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
RPKI — VRPs (Validated ROA Payloads) e objetos ASPA validados pelo Routinator

Lê a saída do Routinator em modo avulso (`scripts/rpki-avulso.sh`) e salva em:

    published/{date}/rpki/vrp_list.json.gz   — lista de VRPs (ROAs validados)
    published/{date}/rpki/aspa_list.json.gz  — lista de objetos ASPA validados

Um VRP (Validated ROA Payload) é o produto de uma ROA (Route Origin Authorization)
validada contra os Trust Anchors RPKI dos cinco RIRs. Cada VRP especifica:
  - O ASN autorizado a originar o prefixo
  - O prefixo (ex: "177.220.0.0/16")
  - O maxLength permitido (prefixos mais específicos até este comprimento são cobertos)
  - O Trust Anchor (ta) que emitiu a ROA (ex: "lacnic", "ripe")

Um objeto ASPA (Autonomous System Provider Authorization) especifica:
  - O ASN customer (quem publicou o objeto)
  - A lista de ASNs providers (upstreams autorizados)
  - O Trust Anchor (tal) que emitiu o objeto

Esses dados são usados pela API para indicar se um prefixo anunciado por um ASN
tem cobertura ROA válida (status RPKI: valid / invalid / not-found), e para exibir
as relações de provedor declaradas via ASPA.

De onde vem o arquivo:
    O Routinator não roda como serviço permanente: o único consumidor faz uma leitura por dia, e o serviço revalidaria o repositório
    a cada 10 min. `scripts/rpki-avulso.sh` roda `routinator vrps -f json` antes do worker e grava `data/cache/rpki/vrps.json` (mesmo formato do `/json`). Arquivo mais velho que RPKI_MAX_IDADE_H
    (padrão 12) é recusado: a etapa falha (política opcional) em vez de publicar RPKI de outro dia como se fosse de hoje.

Uso:
    bash scripts/rpki-avulso.sh
    docker compose run --rm worker python -m sources.rpki_collector.collect [--date 2026-06-01]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from core.common import (
    configure_logging,
    data_dir,
    published_path,
    today_str,
    write_json_gz,
)

MAX_IDADE_H_PADRAO = 12


def arquivo_rpki(base: Path) -> Path:
    return Path(os.environ.get("RPKI_JSON") or base / "cache" / "rpki" / "vrps.json")


def ler_rpki_json(caminho: Path, log, max_idade_h: float | None = None) -> dict | None:
    """Lê a saída do Routinator avulso. None se faltar, estiver velha ou não for o JSON esperado.

    Returns:
        Dict com chaves "roas" e opcionalmente "aspas", ou None.
    """
    if max_idade_h is None:
        max_idade_h = float(os.environ.get("RPKI_MAX_IDADE_H", MAX_IDADE_H_PADRAO))
    if not caminho.is_file():
        log.error("rpki_json_ausente", path=str(caminho), dica="rode scripts/rpki-avulso.sh")
        return None
    idade_h = (time.time() - caminho.stat().st_mtime) / 3600
    if idade_h > max_idade_h:
        log.error("rpki_json_velho", path=str(caminho), idade_h=round(idade_h, 1), max_idade_h=max_idade_h,
                  dica="rode scripts/rpki-avulso.sh")
        return None
    try:
        data = json.loads(caminho.read_text())
    except (OSError, ValueError) as exc:
        log.error("rpki_json_invalido", path=str(caminho), error=str(exc))
        return None
    if not isinstance(data, dict) or not data.get("roas"):
        log.error("rpki_json_sem_roas", path=str(caminho))
        return None
    log.info("rpki_json_lido", path=str(caminho), idade_h=round(idade_h, 1),
             roas=len(data["roas"]), aspas=len(data.get("aspas") or []))
    return data


def normalize_vrps(vrps: list[dict]) -> list[dict]:
    """Normaliza a lista de VRPs do Routinator para o formato do pipeline.

    Conversões aplicadas:
      - asn: "AS12345" ou 12345 → int 12345
      - maxLength: preservado como int
      - ta: string do Trust Anchor ("lacnic", "ripe", "arin", "apnic", "afrinic")
      - prefixos sem prefixo são descartados

    Returns:
        Lista de dicts {"asn": int, "prefix": str, "maxLength": int, "ta": str}
    """
    result = []
    for roa in vrps:
        asn_raw = roa.get("asn", 0)
        try:
            asn = int(str(asn_raw).removeprefix("AS"))
        except (ValueError, AttributeError):
            continue
        prefix = roa.get("prefix", "")
        if not prefix:
            continue
        max_length = roa.get("maxLength", roa.get("max_length", 0))
        ta = roa.get("ta", "")
        result.append({"asn": asn, "prefix": prefix, "maxLength": max_length, "ta": ta})
    return result


def normalize_aspas(aspas: list[dict]) -> list[dict]:
    """Normaliza a lista de objetos ASPA do Routinator para o formato do pipeline.

    Conversões aplicadas:
      - customer: "AS12345" ou 12345 → int 12345
      - providers: lista de "AS456" → lista de int 456 (entradas inválidas descartadas)
      - tal: string do Trust Anchor

    Returns:
        Lista de dicts {"customer": int, "providers": [int, ...], "tal": str}
    """
    result = []
    for aspa in aspas:
        customer_raw = aspa.get("customer", 0)
        try:
            customer = int(str(customer_raw).removeprefix("AS"))
        except (ValueError, AttributeError):
            continue
        providers_raw = aspa.get("providers") or []
        providers: list[int] = []
        for p in providers_raw:
            # Providers podem ser strings "AS123" ou ints ou dicts {"asn": "AS123"}
            if isinstance(p, dict):
                p = p.get("asn", 0)
            try:
                providers.append(int(str(p).removeprefix("AS")))
            except (ValueError, AttributeError):
                continue
        tal = aspa.get("tal", aspa.get("ta", ""))
        result.append({"customer": customer, "providers": providers, "tal": tal})
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="RPKI — publica os VRPs e ASPAs do Routinator avulso (scripts/rpki-avulso.sh)"
    )
    parser.add_argument("--date", default=today_str(),
                        help="Data do snapshot (YYYY-MM-DD); padrão: hoje")
    parser.add_argument("--no-wait", action="store_true",
                        help="Sem efeito (não há serviço a esperar); aceito por compatibilidade")
    args = parser.parse_args(argv)

    log      = configure_logging()
    base     = data_dir()
    date_str = args.date

    log.info("rpki_collector_start", date=date_str)

    rpki_data = ler_rpki_json(arquivo_rpki(base), log)
    if rpki_data is None:
        return 1

    normalized_vrps = normalize_vrps(rpki_data.get("roas") or [])
    vrp_path = published_path(base, date_str, "rpki", "vrp_list.json.gz")
    write_json_gz(vrp_path, normalized_vrps)
    log.info("vrp_list_saved", path=str(vrp_path), count=len(normalized_vrps))

    normalized_aspas = normalize_aspas(rpki_data.get("aspas") or [])
    aspa_path = published_path(base, date_str, "rpki", "aspa_list.json.gz")
    write_json_gz(aspa_path, normalized_aspas)
    log.info("aspa_list_saved", path=str(aspa_path), count=len(normalized_aspas))

    return 0


if __name__ == "__main__":
    sys.exit(main())
