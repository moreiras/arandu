# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — listas diárias de numeração do Registro.br e do LACNIC: só guardam o bruto comprimido."""
import gzip

import httpx
import pytest
import respx

from core import listas_numeracao as ln


def _rotas(fx, grupo):
    if grupo == "registrobr_listas":
        mapa = {"transferencias-diretas-latest": "transferencias-diretas-latest.sample.txt",
                "transferencias-diretas-lacnic-latest": "transferencias-diretas-latest.sample.txt",
                "recuperacao-latest": "recuperacao-latest.sample.txt", "recuperados-latest": "recuperacao-latest.sample.txt"}
        for fim, amostra in mapa.items():
            respx.get(ln.REGISTROBR + fim).respond(200, content=fx("listas_numeracao", amostra).read_bytes())
    else:
        respx.get(ln.LACNIC + "transfers/transfers_latest.json").respond(200, content=fx("listas_numeracao", "transfers_latest.sample.json").read_bytes())
        respx.get(ln.LACNIC + "critical_infra/").respond(200, text=fx("listas_numeracao", "index.sample.html").read_text())
        respx.get(ln.LACNIC + "critical_infra/critical-infra-20261022").respond(200, content=fx("listas_numeracao", "critical-infra.sample.csv").read_bytes())


@pytest.mark.parametrize("grupo", sorted(ln.GRUPOS))
@respx.mock
def test_grava_o_bruto_comprimido_com_os_bytes_originais(grupo, base, log, fx, date_str):
    _rotas(fx, grupo)
    r = ln.run(grupo, date_str, base, log)
    assert set(r) == {n for n, _ in ln.GRUPOS[grupo]}
    for nome in r:
        gz = base / "raw" / date_str / "summary" / ln.nome_bruto(grupo, nome, date_str)
        assert gzip.decompress(gz.read_bytes())
    if grupo == "lacnic_listas":
        crit = base / "raw" / date_str / "summary" / ln.nome_bruto(grupo, "critical-infra", date_str)
        assert gzip.decompress(crit.read_bytes()) == fx("listas_numeracao", "critical-infra.sample.csv").read_bytes()


def test_pega_o_critical_infra_mais_recente_do_indice(fx):
    assert ln.ultimo_critical_infra(fx("listas_numeracao", "index.sample.html").read_text()) == "critical-infra-20261022"
    with pytest.raises(RuntimeError, match="nenhum critical-infra"):
        ln.ultimo_critical_infra("<html></html>")


@respx.mock
def test_falha_de_um_arquivo_nao_deixa_conjunto_parcial(base, log, fx, date_str):
    respx.get(ln.REGISTROBR + "transferencias-diretas-latest").respond(200, content=b"a|b\n1|2\n")
    respx.get(ln.REGISTROBR + "transferencias-diretas-lacnic-latest").respond(503)
    with pytest.raises(httpx.HTTPStatusError):
        ln.run("registrobr_listas", date_str, base, log)
    assert not list((base / "raw" / date_str / "summary").glob("*.gz"))


@respx.mock
def test_arquivo_vazio_falha_alto(base, log, date_str):
    for fim in ("transferencias-diretas-latest", "transferencias-diretas-lacnic-latest", "recuperacao-latest", "recuperados-latest"):
        respx.get(ln.REGISTROBR + fim).respond(200, content=b"  \n")
    with pytest.raises(RuntimeError, match="vazio"):
        ln.run("registrobr_listas", date_str, base, log)


def test_gz_deterministico(tmp_path):
    import time
    a, b = tmp_path / "a.gz", tmp_path / "b.gz"
    ln._gravar_gz(a, b"x" * 500)
    time.sleep(1.1)
    ln._gravar_gz(b, b"x" * 500)
    assert a.read_bytes() == b.read_bytes()


def test_cada_grupo_tem_seu_modulo_e_so_o_seu_grupo(base, log, monkeypatch):
    import importlib
    chamadas = []
    for g in sorted(ln.GRUPOS):
        mod = importlib.import_module(f"sources.{g}.collect")
        monkeypatch.setattr(mod, "run", lambda grupo, date, d, lg, _g=g: chamadas.append((grupo, date)))
        assert mod.main(["--date", "2026-10-23"]) == 0 and mod.GRUPO == g
    assert chamadas == [(g, "2026-10-23") for g in sorted(ln.GRUPOS)]
