#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Mede o ritmo seguro do RDAP do Registro.br: corrida sustentada e reconsulta dos incompletos.

Grava UMA linha JSON por consulta (asn, instante, status HTTP, bytes, ms, completo, nº de e-mails); NUNCA valores de contato.
Para ao primeiro 403/429. Sorteio com semente (reprodutível) sobre os ASNs de um `orgs.json.gz`.

Uso (em segundo plano):
    setsid nohup python scripts/medir_rdap_contatos.py --orgs data/normalized/AAAA-MM-DD/summary/orgs.json.gz \
        --n 150 --intervalo 10 --descanso 300 --reconsulta 20 --saida /caminho/saida.jsonl > /caminho/log.txt 2>&1 &
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import httpx

from core.common import read_json_gz
from sources.rdap_contatos.collect import BASE_URL, extrair

UA = {"User-Agent": "Arandurape-medicao/1.0 (pesquisa; projeto sem fins lucrativos)", "Accept": "application/rdap+json"}


def consulta(client: httpx.Client, asn: int, fase: str, intervalo: float, saida) -> dict:
    t0 = time.monotonic()
    reg = {"fase": fase, "asn": asn, "t": time.strftime("%H:%M:%S"), "intervalo_s": intervalo}
    try:
        r = client.get(BASE_URL + str(asn))
        reg.update(http=r.status_code, bytes=len(r.content), ms=round((time.monotonic() - t0) * 1000))
        if r.status_code == 200:
            rec = extrair(r.json())
            reg.update(completo=bool(rec and rec["completo"]), emails=len(rec["contatos"]) if rec else None)
    except httpx.HTTPError as exc:
        reg.update(http=None, erro=type(exc).__name__, ms=round((time.monotonic() - t0) * 1000))
    saida.write(json.dumps(reg) + "\n")
    saida.flush()
    return reg


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--orgs", required=True)
    p.add_argument("--n", type=int, default=150)
    p.add_argument("--intervalo", type=float, default=10)
    p.add_argument("--descanso", type=float, default=300, help="espera inicial para o balde encher")
    p.add_argument("--reconsulta", type=float, default=20, help="intervalo da reconsulta dos incompletos (0 = não reconsultar)")
    p.add_argument("--seed", type=int, default=20261110)
    p.add_argument("--saida", required=True)
    a = p.parse_args()
    asns = sorted(int(x) for x in read_json_gz(Path(a.orgs)).get("orgs", {}))
    amostra = random.Random(a.seed).sample(asns, min(a.n, len(asns)))
    print(f"universo={len(asns)} amostra={len(amostra)}; descanso {a.descanso:g} s", flush=True)
    time.sleep(a.descanso)
    with httpx.Client(headers=UA, timeout=httpx.Timeout(30, read=60)) as client, open(a.saida, "a", encoding="utf-8") as saida:
        incompletos: list[int] = []
        for fase, lista, intervalo in (("sustentada", amostra, a.intervalo), ("reconsulta", None, a.reconsulta)):
            if lista is None:
                lista = incompletos[:]
                if not lista or not a.reconsulta:
                    break
                print(f"reconsultando {len(lista)} incompletos a {a.reconsulta:g} s", flush=True)
            for asn in lista:
                reg = consulta(client, asn, fase, intervalo, saida)
                if reg.get("http") in (403, 429):
                    print("sinal de bloqueio; parando", flush=True)
                    return 2
                if fase == "sustentada" and (reg.get("http") != 200 or not reg.get("completo")):
                    incompletos.append(asn)
                time.sleep(intervalo)
    print("fim", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
