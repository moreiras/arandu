# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — CAIDA as-rel2: listagem → arquivo mensal ≤ data → bruto comprimido → normalizado, sem rede."""
import bz2
import gzip

import pytest
import respx

from core.common import read_json_gz
from sources.caida_asrel import collect as fonte


def _texto(fx):
    return fx("caida_asrel", "20261001.as-rel2.txt").read_text(encoding="utf-8")


def test_escolhe_o_arquivo_mais_recente_ate_a_data(fx):
    lista = fx("caida_asrel", "index.html").read_text(encoding="utf-8")
    assert fonte.escolher_arquivo(lista, "2026-10-24") == "20261001.as-rel2.txt.bz2"
    assert fonte.escolher_arquivo(lista, "2026-11-01") == "20261101.as-rel2.txt.bz2"
    assert fonte.escolher_arquivo(lista, "2026-08-31") is None


def test_parse_separa_p2c_p2p_e_ignora_comentarios_e_lixo(fx):
    r = fonte.parse_asrel(_texto(fx) + "lixo|x|-1\n1|2|7\n")
    assert [64496, 64497] in r["p2c"] and len(r["p2c"]) == 5
    assert r["p2p"] == [[64496, 64500], [64497, 64498]]            # par normalizado (menor, maior)
    assert r["ignoradas"] == 2


@respx.mock
def test_run_grava_bruto_e_normalizado(base, log, fx):
    date_str = "2026-10-24"
    respx.get(fonte.URL).respond(200, text=fx("caida_asrel", "index.html").read_text(encoding="utf-8"))
    respx.get(fonte.URL + "20261001.as-rel2.txt.bz2").respond(200, content=bz2.compress(_texto(fx).encode()))
    r = fonte.run(date_str, base, log)
    assert r["as_of"] == "2026-10-01" and r["total"] == 7
    norm = read_json_gz(base / "normalized" / date_str / "summary" / "caida_asrel.json.gz")
    assert norm["p2c"] == r["p2c"] and norm["arquivo"] == "20261001.as-rel2.txt.bz2"
    bruto = base / "raw" / date_str / "summary" / "caida-asrel-20261001.txt.gz"
    assert gzip.decompress(bruto.read_bytes()).decode() == _texto(fx)


@respx.mock
def test_run_sem_arquivo_ou_vazio_falha_alto(base, log, fx, date_str):
    respx.get(fonte.URL).respond(200, text="<html></html>")
    with pytest.raises(RuntimeError):
        fonte.run(date_str, base, log)
