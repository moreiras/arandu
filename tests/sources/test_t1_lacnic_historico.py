# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — backfill do histórico do LACNIC: retomável, conferido e gentil."""
import datetime as dt
import gzip
import hashlib

import httpx
import pytest
import respx

from sources.lacnic_historico import collect as lh

B = lh.BASE


def _rotas(fx, md5_ok=True):
    arq = fx("lacnic_historico", "delegated-lacnic-extended.sample.txt").read_bytes()
    respx.get(B + "archive/2020/").respond(200, text=fx("lacnic_historico", "indice-archive-2020.sample.html").read_text())
    for dia in ("20200101", "20200102", "20200103"):
        respx.get(B + f"archive/2020/delegated-lacnic-extended-{dia}").respond(200, content=arq)
    boa = hashlib.md5(arq).hexdigest()
    respx.get(B + "archive/2020/delegated-lacnic-extended-20200101.md5").respond(200, text=f"{boa}  delegated-lacnic-extended-20200101\n")
    respx.get(B + "archive/2020/delegated-lacnic-extended-20200102.md5").respond(200, text=("0" * 32 if not md5_ok else boa))
    respx.get(B + "archive/2020/delegated-lacnic-extended-20200103.md5").respond(404)       # sem md5: segue, com aviso
    return arq


class _Log:
    avisos = []

    def info(self, *a, **k): pass
    def warning(self, *a, **k): self.avisos.append((a, k))
    exception = error = info


@respx.mock
def test_baixa_comprime_confere_md5_e_e_retomavel(tmp_path, fx):
    arq = _rotas(fx)
    r = lh.run("delegated", tmp_path, dt.date(2020, 1, 1), dt.date(2020, 12, 31), 100, 0, _Log(), dormir=lambda s: None)
    assert r == {"tipo": "delegated", "novos": 3, "ja_tinha": 0, "falhas": 0, "vazios_na_origem": 0, "parou_no_limite": False}
    f = tmp_path / "historico" / "lacnic" / "delegated-extended" / "2020" / "delegated-lacnic-extended-20200102.gz"
    assert gzip.decompress(f.read_bytes()) == arq
    r2 = lh.run("delegated", tmp_path, dt.date(2020, 1, 1), dt.date(2020, 12, 31), 100, 0, _Log(), dormir=lambda s: None)
    assert r2["novos"] == 0 and r2["ja_tinha"] == 3                                   # retomável: nada de novo, nada refeito


@respx.mock
def test_md5_errado_vira_falha_e_nao_grava(tmp_path, fx):
    _rotas(fx, md5_ok=False)
    r = lh.run("delegated", tmp_path, dt.date(2020, 1, 1), dt.date(2020, 12, 31), 100, 0, _Log(), dormir=lambda s: None)
    assert r["falhas"] == 1 and r["novos"] == 2
    assert not (tmp_path / "historico" / "lacnic" / "delegated-extended" / "2020" / "delegated-lacnic-extended-20200102.gz").exists()
    assert lh.main.__name__ == "main"


@respx.mock
def test_limite_por_execucao_e_filtro_de_datas(tmp_path, fx):
    _rotas(fx)
    r = lh.run("delegated", tmp_path, dt.date(2020, 1, 2), dt.date(2020, 1, 3), 1, 0, _Log(), dormir=lambda s: None)
    assert r["novos"] == 1 and r["parou_no_limite"] is True                           # 01/01 fora do filtro; 1 por vez


@respx.mock
def test_transfers_exige_json_valido(tmp_path, fx):
    respx.get(B + "transfers/2016/").respond(200, text=fx("lacnic_historico", "indice-transfers-2016.sample.html").read_text())
    respx.get(B + "transfers/2016/transfers_20160830T212000Z.json").respond(200, content=fx("lacnic_historico", "transfers.sample.json").read_bytes())
    respx.get(B + "transfers/2016/transfers_20160831T212000Z.json").respond(200, content=b"<html>erro</html>")
    r = lh.run("transfers", tmp_path, dt.date(2016, 8, 30), dt.date(2016, 12, 31), 10, 0, _Log(), dormir=lambda s: None)
    assert r["novos"] == 1 and r["falhas"] == 1
    assert (tmp_path / "historico" / "lacnic" / "transfers" / "2016" / "transfers_20160830T212000Z.json.gz").exists()


@respx.mock
def test_ano_sem_diretorio_e_ignorado(tmp_path):
    respx.get(B + "archive/2027/").respond(404)
    assert lh.listar_ano(httpx.Client(), "delegated", 2027) == []


@respx.mock
def test_arquivo_vazio_na_origem_nao_e_falha(tmp_path, fx):
    respx.get(B + "transfers/2016/").respond(200, text=fx("lacnic_historico", "indice-transfers-2016.sample.html").read_text())
    respx.get(B + "transfers/2016/transfers_20160830T212000Z.json").respond(200, content=b"")
    respx.get(B + "transfers/2016/transfers_20160831T212000Z.json").respond(200, content=fx("lacnic_historico", "transfers.sample.json").read_bytes())
    r = lh.run("transfers", tmp_path, dt.date(2016, 8, 30), dt.date(2016, 12, 31), 10, 0, _Log(), dormir=lambda s: None)
    assert r["novos"] == 1 and r["vazios_na_origem"] == 1 and r["falhas"] == 0                  # o exit code do módulo fica 0
    assert not (tmp_path / "historico" / "lacnic" / "transfers" / "2016" / "transfers_20160830T212000Z.json.gz").exists()
