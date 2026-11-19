# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — Anatel, compromissos do FUST: amostra sintética no layout real, sem rede."""
import io
import zipfile

import httpx
import pytest
import respx

from core import fust
from core.common import read_json_gz
from sources.anatel_fust import collect as fonte


class _Log:
    def info(self, *a, **k): pass
    warning = info


def _csv(fx) -> io.BytesIO:
    with zipfile.ZipFile(fx("anatel_fust", "fust_sintetico.zip")) as z:
        return io.BytesIO(z.read("Base_FUST.csv"))


def test_consolida_municipio_valor_e_prazo(fx):
    itens, resumo = fust.consolidar(_csv(fx))
    por_id = {i["id"]: i for i in itens}
    assert resumo["compromissos"] == 6 and resumo["sem_ibge"] == 0 and resumo["sem_investimento"] == 2 and resumo["status_desconhecido"] == 0
    assert por_id["1"]["ibge"] == "3550308" and por_id["1"]["investimento"] == pytest.approx(38717.78) and por_id["1"]["prazo"] == "2025-12-23"
    assert por_id["4"]["programa"] == "1.3 - Conectividade para Escolas Públicas" and por_id["4"]["investimento"] is None     # tabulação e N/A
    assert por_id["6"]["prazo"] is None and por_id["6"]["investimento"] is None                                           # prazo inválido, valor vazio
    assert por_id["5"]["nivel"] == "Localidade" and resumo["status"] == {"Atendido": 2, "Em apuração": 1, "A vencer": 3}


def test_leiaute_mudou_falha_alto():
    ruim = io.BytesIO("ID_LINHA;ORIGEM\n1;x\n".encode())
    with pytest.raises(RuntimeError, match="leiaute mudou"):
        fust.consolidar(ruim)


@respx.mock
def test_run_grava_normalizado_e_bruto(fx, tmp_path):
    corpo = fx("anatel_fust", "fust_sintetico.zip").read_bytes()
    respx.get(fonte.URL).mock(return_value=httpx.Response(200, content=corpo, headers={"last-modified": "Mon, 02 Nov 2026 10:30:15 GMT"}))
    monkey_min = fonte.MINIMO_COMPROMISSOS
    fonte.MINIMO_COMPROMISSOS = 3
    try:
        r = fonte.run("2026-11-02", tmp_path, _Log())
    finally:
        fonte.MINIMO_COMPROMISSOS = monkey_min
    assert r["compromissos"] == 6
    doc = read_json_gz(tmp_path / "normalized" / "2026-11-02" / "summary" / "anatel_fust.json.gz")
    assert len(doc["compromissos"]) == 6 and doc["data_arquivo"].startswith("Mon, 02 Nov 2026") and len(doc["sha256"]) == 64
    assert (tmp_path / "raw" / "2026-11-02" / "summary" / "fust-2026-11-02.zip").exists()


@respx.mock
def test_arquivo_pequeno_demais_falha(fx, tmp_path):
    respx.get(fonte.URL).mock(return_value=httpx.Response(200, content=fx("anatel_fust", "fust_sintetico.zip").read_bytes()))
    with pytest.raises(RuntimeError, match="truncado"):
        fonte.run("2026-11-02", tmp_path, _Log())
