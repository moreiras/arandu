# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cota de contatos (api/contatos_cota.py): janelas por conta, rede e global, custo, conta nova, suspensão, exceção e persistência."""
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from api import contatos_cota as cc

T0 = 1_800_000_000.0


@pytest.fixture(autouse=True)
def tetos(monkeypatch):
    for k, v in cc.PADROES.items():
        monkeypatch.setenv(k, str(v))


def _velha():
    return (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()


def test_rajada_por_conta_e_espera(tmp_path):
    for i in range(10):
        assert cc.consumir(tmp_path, "c1", "r1", 1, _velha(), agora=T0 + i).ok
    r = cc.consumir(tmp_path, "c1", "r1", 1, _velha(), agora=T0 + 20)
    assert not r.ok and r.motivo == "conta_rajada" and 0 < r.espera_s <= 600
    assert cc.consumir(tmp_path, "c1", "r1", 1, _velha(), agora=T0 + 601).ok        # a janela de 10 min andou


def test_custo_da_operadora_conta_por_asn(tmp_path):
    assert cc.consumir(tmp_path, "c1", "r1", 8, _velha(), agora=T0).ok
    r = cc.consumir(tmp_path, "c1", "r1", 3, _velha(), agora=T0 + 1)
    assert not r.ok and r.motivo == "conta_rajada"
    assert cc.consumir(tmp_path, "c1", "r1", 2, _velha(), agora=T0 + 2).ok           # 8 + 2 = 10 cabe


def test_teto_diario_e_restante(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTATOS_CONTA_RAJADA", "0")
    monkeypatch.setenv("CONTATOS_CONTA_HORA", "0")
    monkeypatch.setenv("CONTATOS_REDE_DIA", "0")
    monkeypatch.setenv("CONTATOS_REDE_HORA", "0")
    monkeypatch.setenv("CONTATOS_REDE_RAJADA", "0")
    r = cc.consumir(tmp_path, "c1", "r1", 39, _velha(), agora=T0)
    assert r.ok and r.restante_dia == 1
    assert cc.consumir(tmp_path, "c1", "r1", 1, _velha(), agora=T0 + 1).restante_dia == 0
    r = cc.consumir(tmp_path, "c1", "r1", 1, _velha(), agora=T0 + 2)
    assert not r.ok and r.motivo == "conta_dia" and r.espera_s > 80000


def test_conta_nova_tem_teto_menor(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTATOS_CONTA_RAJADA", "0")
    nova = datetime.fromtimestamp(T0 - 3600, timezone.utc).isoformat()
    assert cc.consumir(tmp_path, "nova", "r1", 10, nova, agora=T0).ok
    r = cc.consumir(tmp_path, "nova", "r1", 1, nova, agora=T0 + 1)
    assert not r.ok and r.motivo in ("conta_dia", "conta_hora")


def test_muitas_contas_na_mesma_rede_somam(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTATOS_REDE_RAJADA", "15")
    assert cc.consumir(tmp_path, "a", "r1", 10, _velha(), agora=T0).ok
    r = cc.consumir(tmp_path, "b", "r1", 10, _velha(), agora=T0 + 1)
    assert not r.ok and r.motivo == "rede_rajada"
    assert cc.consumir(tmp_path, "b", "r2", 10, _velha(), agora=T0 + 2).ok


def test_teto_global_vale_para_todas_as_contas(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTATOS_GLOBAL_DIA", "25")
    assert cc.consumir(tmp_path, "a", "r1", 10, _velha(), agora=T0).ok
    assert cc.consumir(tmp_path, "b", "r2", 10, _velha(), agora=T0 + 1).ok
    r = cc.consumir(tmp_path, "c", "r3", 10, _velha(), agora=T0 + 2)
    assert not r.ok and r.motivo == "global" and "serviço" in cc.mensagem(r)


def test_suspensao_apos_dias_no_teto_e_liberacao(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTATOS_SUSPENDER_APOS", "1")
    for k in ("CONTATOS_CONTA_RAJADA", "CONTATOS_CONTA_HORA", "CONTATOS_REDE_RAJADA", "CONTATOS_REDE_HORA", "CONTATOS_REDE_DIA"):
        monkeypatch.setenv(k, "0")
    assert cc.consumir(tmp_path, "abusa", "r1", 40, _velha(), agora=T0).ok
    assert cc.consumir(tmp_path, "abusa", "r1", 1, _velha(), agora=T0 + 1).motivo == "conta_dia"
    r = cc.consumir(tmp_path, "abusa", "r1", 1, _velha(), agora=T0 + 2 * 86400)
    assert not r.ok and r.motivo == "suspensao" and "suspenso" in cc.mensagem(r)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert cc.main(["--liberar", "abusa"]) == 0
    assert cc.consumir(tmp_path, "abusa", "r1", 1, _velha(), agora=T0 + 2 * 86400 + 1).ok


def test_excecao_concedida_multiplica_os_tetos(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert cc.main(["--conceder", "noc", "2"]) == 0
    assert cc.consumir(tmp_path, "noc", "r1", 20, _velha(), agora=T0).ok                # rajada 10 × 2
    assert not cc.consumir(tmp_path, "noc", "r1", 1, _velha(), agora=T0 + 1).ok


def test_persistente_e_sem_ip(tmp_path):
    assert cc.consumir(tmp_path, "c1", cc.hash_rede("200.160.2.3", "s" * 32), 1, _velha(), agora=T0).ok
    con = sqlite3.connect(tmp_path / "auth" / "contatos_uso.db")
    linhas = con.execute("SELECT conta, rede, custo FROM eventos").fetchall()
    assert linhas[0][0] == "c1" and "200.160" not in linhas[0][1] and len(linhas[0][1]) == 24


def test_tetos_zerados_nao_barram(tmp_path, monkeypatch):
    for k in cc.PADROES:
        monkeypatch.setenv(k, "0")
    assert all(cc.consumir(tmp_path, "c1", "r1", 50, _velha(), agora=T0 + i).ok for i in range(10))
