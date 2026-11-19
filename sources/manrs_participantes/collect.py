# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""MANRS: tabela pública de participantes do programa de operadores.

Fonte:       https://manrs.org/netops/participants/ (HTML; o botão "CSV" da página é gerado no navegador a partir da mesma tabela). `robots.txt` permite; termos em https://manrs.org/terms-of-service/
Bruto:       data/raw/{date}/summary/manrs-participantes-{date}.html.gz
Normalizado: data/normalized/{date}/summary/manrs_participantes.json.gz   {medido_em, participantes: [{org, aprovado, areas, asns, acoes}]}
**Nunca publicado:** os termos permitem divulgar dados de outras redes só de forma agregada, sem identificá-las. Só `products.manrs.build` lê este arquivo e só publica agregados com atribuição.
Uma requisição por coleta, com User-Agent identificado.

Uso:
    python -m sources.manrs_participantes.collect --date 2026-11-03
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import sys
import urllib.request
from pathlib import Path

from core import manrs
from core.common import configure_logging, data_dir, normalized_path, now_iso, raw_path, today_str
from core.jsonio import gravar_json_gz
from core.site import USER_AGENT

URL = "https://manrs.org/netops/participants/"
MINIMO_ORGANIZACOES = 500          # a tabela tem ~1.200; menos que isso é página truncada ou mudança de HTML
MINIMO_COM_BR = 100
ATRIBUICAO = "Provided by the MANRS with support from the Global Cyber Alliance"


def baixar(url: str = URL) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def run(date_str: str, base: Path, log, pagina: str | None = None) -> dict:
    pagina = pagina if pagina is not None else baixar()
    lista = manrs.participantes(pagina)
    com_br = sum(1 for p in lista if "BR" in p["areas"])
    if len(lista) < MINIMO_ORGANIZACOES or com_br < MINIMO_COM_BR:
        raise RuntimeError(f"manrs_participantes: {len(lista)} organizações e {com_br} com área BR (esperado ≥ {MINIMO_ORGANIZACOES} e ≥ {MINIMO_COM_BR}); página truncada ou HTML mudou?")
    bruto = raw_path(base, date_str, "summary")
    bruto.mkdir(parents=True, exist_ok=True)
    dados = pagina.encode("utf-8")
    with gzip.open(bruto / f"manrs-participantes-{date_str}.html.gz", "wb") as f:
        f.write(dados)
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "manrs_participantes.json.gz", {
        "snapshot_date": date_str, "fetched_at": now_iso(), "url": URL, "medido_em": manrs.medido_em(pagina), "atribuicao": ATRIBUICAO,
        "sha256": hashlib.sha256(dados).hexdigest(), "participantes": lista})
    log.info("manrs: lido", organizacoes=len(lista), com_area_br=com_br)
    return {"organizacoes": len(lista), "com_area_br": com_br, "medido_em": manrs.medido_em(pagina)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="MANRS: tabela pública de participantes (operadores de rede)")
    p.add_argument("--date", default=today_str())
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        print(run(a.date, data_dir(), log))
    except Exception:
        log.exception("falha na coleta de manrs_participantes")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
