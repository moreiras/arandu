# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — CAIDA Spoofer: páginas sintéticas no formato Hydra, sem rede. O /24 do cliente nunca pode chegar ao disco."""
import datetime as dt
import gzip
import json

import httpx
import pytest
import respx

from core import spoofer
from core.common import read_json_gz
from sources.caida_spoofer import collect as fonte


class _Log:
    def info(self, *a, **k): pass
    warning = info


def _paginas(fx):
    return [json.loads(fx("caida_spoofer", f"pagina{i}.json").read_text()) for i in (1, 2)]


def _mock(fx):
    p1, p2 = _paginas(fx)
    return respx.get(f"{fonte.BASE_URL}/sessions").mock(side_effect=lambda req: httpx.Response(200, json=p2 if req.url.params.get("page") == "2" else p1))


def _sessoes(fx):
    return [spoofer.sanear(s) for p in _paginas(fx) for s in p["hydra:member"]]


def test_sanear_descarta_o_endereco_do_cliente(fx):
    cru = _paginas(fx)[0]["hydra:member"][0]
    assert cru["client4"] == "192.0.2.0/24"
    s = spoofer.sanear(cru)
    assert "client4" not in s and "client6" not in s and "@id" not in s and s["asn4"] == 64500 and s["session"] == 1


def test_agregar_conta_so_conclusivas_fora_de_nat_e_ipv6(fx):
    asns, resumo = spoofer.agregar(_sessoes(fx), dt.date(2026, 11, 2))
    a = asns["64500"]
    assert a["sessoes"] == 7 and a["conclusivas_v4"] == 5 and a["conclusivas_v6"] == 0 and a["conclusivas"] == 5 and a["suficiente"] is True      # rewritten e unknown não contam
    assert a["pct_bloqueado"] == 80.0 and a["pct_recebido_roteado"] == 20.0 and a["pct_recebido_privado"] == 0.0 and a["ultima_sessao"] == "2026-07-11" and a["pct_nat_v4"] == 0.0
    nat = asns["64501"]
    assert nat["sessoes"] == 2 and nat["conclusivas"] == 0 and nat["suficiente"] is False and nat["pct_bloqueado"] is None and nat["pct_nat_v4"] == 100.0       # atrás de NAT não é conclusivo
    v6 = asns["64502"]
    assert v6["conclusivas_v4"] == 0 and v6["conclusivas_v6"] == 3 and v6["sessoes_v4"] == 2 and v6["sessoes_v6"] == 3 and v6["pct_recebido_privado"] == 33.3
    assert asns["64503"]["sessoes"] == 2 and asns["64503"]["conclusivas"] == 1 and asns["64503"]["suficiente"] is False
    assert resumo["sessoes_na_janela"] == 14 and resumo["asns"] == 4 and resumo["asns_suficientes"] == 1 and resumo["janela"] == {"inicio": "2025-11-02", "fim": "2026-11-02", "dias": 365}


def test_agregar_ignora_sessao_fora_da_janela(fx):
    antiga = {**_sessoes(fx)[0], "session": 99, "timestamp": "2024-01-01T00:00:00+00:00"}
    asns, resumo = spoofer.agregar(_sessoes(fx) + [antiga], dt.date(2026, 11, 2))
    assert asns["64500"]["sessoes"] == 7 and resumo["sessoes_na_janela"] == 14


@respx.mock
def test_run_segue_a_paginacao_e_nao_grava_o_cliente(fx, tmp_path, monkeypatch):
    rota = _mock(fx)
    monkeypatch.setattr(fonte, "MINIMO_SESSOES", 10)
    r = fonte.run("2026-11-02", tmp_path, _Log(), espera=0)
    assert rota.call_count == 2 and r["novas_sessoes"] == 14 and r["asns"] == 4 and r["asns_suficientes"] == 1
    doc = read_json_gz(tmp_path / "normalized" / "2026-11-02" / "summary" / "caida_spoofer.json.gz")
    assert doc["asns"]["64500"]["suficiente"] is True and "CAIDA" in doc["citacao"]
    for arq in [tmp_path / "spoofer" / "sessoes.json.gz", tmp_path / "normalized" / "2026-11-02" / "summary" / "caida_spoofer.json.gz"]:
        conteudo = gzip.decompress(arq.read_bytes()).decode()
        assert "192.0.2" not in conteudo and "2001:db8" not in conteudo and "client4" not in conteudo
    assert not (tmp_path / "raw").exists()


@respx.mock
def test_segunda_execucao_so_pede_o_que_veio_depois(fx, tmp_path, monkeypatch):
    monkeypatch.setattr(fonte, "MINIMO_SESSOES", 10)
    _mock(fx)
    fonte.run("2026-11-02", tmp_path, _Log(), espera=0)
    pedidos = []
    respx.get(f"{fonte.BASE_URL}/sessions").mock(side_effect=lambda req: (pedidos.append(str(req.url)), httpx.Response(200, json={"hydra:member": [], "hydra:view": {}}))[1])
    r = fonte.run("2026-11-03", tmp_path, _Log(), espera=0)
    assert r["novas_sessoes"] == 0 and r["asns"] == 4
    assert "2026-10-11T10%3A00%3A00%2B00%3A00" in pedidos[0]           # depois da última sessão guardada


@respx.mock
def test_coleta_truncada_falha_alto(fx, tmp_path):
    _mock(fx)
    with pytest.raises(RuntimeError, match="truncada"):
        fonte.run("2026-11-02", tmp_path, _Log(), espera=0)
