# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Bogons: espaço de IPv4/IPv6 e ASNs que não deveriam aparecer na tabela de rotas pública.

Fontes:
  * IANA, registros de uso especial (IPv4, IPv6 e números de AS): blocos com "Globally Reachable" = False e os ASNs reservados;
  * Team Cymru, fullbogons (IPv4 e IPv6): reservados + ainda não alocados por nenhum RIR (lista pública, "Free. Forever.").
Normalizado: data/normalized/{date}/summary/bogons.json.gz
             {snapshot_date, iana: {v4: [{bloco, nome, rfc}], v6: [...], asns: [{inicio, fim, motivo}]}, cymru: {as_of, v4: [cidr], v6: [cidr]}}

Uso:
    python -m sources.bogons.collect --date 2026-10-31
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import re
import sys
from pathlib import Path

import httpx

from core.common import configure_logging, data_dir, normalized_path, now_iso, today_str, write_json_gz
from core.site import USER_AGENT

HEADERS = {"User-Agent": USER_AGENT}
URLS = {
    "iana_v4": "https://www.iana.org/assignments/iana-ipv4-special-registry/iana-ipv4-special-registry-1.csv",
    "iana_v6": "https://www.iana.org/assignments/iana-ipv6-special-registry/iana-ipv6-special-registry-1.csv",
    "iana_as": "https://www.iana.org/assignments/iana-as-numbers-special-registry/special-purpose-as-numbers.csv",
    "cymru_v4": "https://www.team-cymru.org/Services/Bogons/fullbogons-ipv4.txt",
    "cymru_v6": "https://www.team-cymru.org/Services/Bogons/fullbogons-ipv6.txt",
}
MINIMO = {"iana_v4": 10, "iana_v6": 5, "iana_as": 5, "cymru_v4": 500, "cymru_v6": 3}      # abaixo disso a lista veio truncada
_CIDR = re.compile(r"^[0-9a-fA-F:.]+/\d{1,3}$")
_ATUALIZADO = re.compile(r"last updated (\d+)")


def parse_iana_ip(texto: str) -> list[dict]:
    """Blocos do registro de uso especial que NÃO são alcançáveis globalmente (um mesmo bloco pode listar várias linhas)."""
    out, vistos = [], set()
    for r in csv.DictReader(io.StringIO(texto)):
        bloco = (r.get("Address Block") or "").strip()
        # blocos com várias linhas separadas por vírgula/nota ("192.0.0.0/24 [1]") ficam só com o primeiro CIDR
        m = re.match(r"([0-9a-fA-F:.]+/\d{1,3})", bloco)
        if not m or (r.get("Globally Reachable") or "").strip().lower() != "false" or m.group(1) in vistos:
            continue
        vistos.add(m.group(1))
        out.append({"bloco": m.group(1), "nome": (r.get("Name") or "").strip().strip('"'), "rfc": (r.get("RFC") or "").strip()})
    return out


def parse_iana_as(texto: str) -> list[dict]:
    out = []
    for r in csv.DictReader(io.StringIO(texto)):
        faixa = (r.get("AS Number") or "").strip()
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", faixa)
        if m:
            out.append({"inicio": int(m.group(1)), "fim": int(m.group(2) or m.group(1)), "motivo": (r.get("Reason for Reservation") or "").strip()})
    return out


def parse_cymru(texto: str) -> tuple[list[str], int | None]:
    """(lista de CIDRs, instante `last updated` da lista em epoch)."""
    cidrs = [ln.strip() for ln in texto.splitlines() if ln.strip() and _CIDR.match(ln.strip())]
    m = _ATUALIZADO.search(texto)
    return cidrs, int(m.group(1)) if m else None


def run(date_str: str, base: Path, log) -> dict:
    with httpx.Client(timeout=120, follow_redirects=True, headers=HEADERS) as client:
        txt = {}
        for chave, url in URLS.items():
            r = client.get(url)
            r.raise_for_status()
            txt[chave] = r.text
    iana = {"v4": parse_iana_ip(txt["iana_v4"]), "v6": parse_iana_ip(txt["iana_v6"]), "asns": parse_iana_as(txt["iana_as"])}
    c4, t4 = parse_cymru(txt["cymru_v4"])
    c6, t6 = parse_cymru(txt["cymru_v6"])
    achados = {"iana_v4": len(iana["v4"]), "iana_v6": len(iana["v6"]), "iana_as": len(iana["asns"]), "cymru_v4": len(c4), "cymru_v6": len(c6)}
    for chave, n in achados.items():
        if n < MINIMO[chave]:
            raise RuntimeError(f"bogons: lista {chave} com {n} itens (esperado ≥ {MINIMO[chave]}); resposta truncada?")
    quando = max(t for t in (t4, t6) if t) if (t4 or t6) else None
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / "bogons.json.gz", {
        "snapshot_date": date_str, "generated_at": now_iso(), "iana": iana,
        "cymru": {"as_of": dt.datetime.fromtimestamp(quando, dt.timezone.utc).strftime("%Y-%m-%d") if quando else None, "v4": c4, "v6": c6}})
    log.info("bogons written", **achados)
    return achados


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Bogons (IANA e Team Cymru)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre refeita")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        run(a.date, data_dir(), log)
    except Exception:
        log.exception("falha na coleta de bogons")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
