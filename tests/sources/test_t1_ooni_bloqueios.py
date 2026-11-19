# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — OONI (bucket aberto): listagem S3 → fluxo `.jsonl.gz` → agregado por ASN, sem rede e sem guardar nada por sonda."""
import gzip
import json

import httpx
import pytest
import respx

from core import ooni
from core.common import read_json_gz
from sources.ooni_bloqueios import collect as fonte

NS = "http://s3.amazonaws.com/doc/2006-03-01/"


def _linhas(fx, teste):
    return [json.loads(x) for x in fx("ooni", f"{teste}.jsonl").read_text(encoding="utf-8").splitlines()]


def _agregar(fx, teste):
    ag = ooni.Agregador()
    for m in _linhas(fx, teste):
        ag.add(teste, m)
    return ag


def test_whatsapp_veredito_por_componente_e_descartes(fx):
    ag = _agregar(fx, "whatsapp")
    d = ag.dados["whatsapp"]
    assert d["64496"] == {"n": 4, "anom": 1, "partes": {"web": 1}}
    assert d["64497"] == {"n": 2, "anom": 1, "partes": {"registro": 1, "endpoints": 1}}
    assert "64498" not in d and "0" not in d and ag.descartadas == 2            # outro país e ASN oculto


def test_signal_descarta_versao_com_falso_positivo_documentado(fx):
    d = _agregar(fx, "signal").dados["signal"]
    assert d == {"64496": {"n": 2, "anom": 1, "partes": {"backend": 1}}}


def test_telegram_facebook_psiphon_tor(fx):
    assert _agregar(fx, "telegram").dados["telegram"]["64497"]["partes"] == {"tcp": 1, "http": 1}
    assert _agregar(fx, "facebookmessenger").dados["facebookmessenger"]["64497"]["partes"] == {"dns": 1}
    assert _agregar(fx, "psiphon").dados["psiphon"]["64496"] == {"n": 2, "anom": 1, "partes": {"tunel": 1}}
    tor = _agregar(fx, "tor").dados["tor"]
    assert tor["64497"]["anom"] == 1 and tor["64496"]["anom"] == 0              # só anomalia quando nenhum alvo, de nenhum tipo, foi acessível
    assert tor["64496"]["alvos"]["obfs4"] == [28, 3] and tor["64496"]["alvos"]["dir_port"] == [20, 19]


def test_webconnectivity_blocking_da_sonda(fx):
    d = _agregar(fx, "webconnectivity").dados["webconnectivity"]
    assert d["64496"]["n"] == 4 and d["64496"]["anom"] == 2 and d["64496"]["partes"] == {"dns": 1, "http-diff": 1}
    assert d["64497"]["n"] == 3 and d["64497"]["sem_veredito"] == 1 and d["64497"]["inacessivel"] == 2


def test_nada_por_sonda_no_agregado(fx):
    """Nem `report_id`, nem `input`, nem IP, nem nome de rede, nem resolvedor chegam ao agregado."""
    todos = {}
    for t in ooni.TESTES_LEVES + (ooni.TESTE_WEB,):
        ooni.mesclar(todos, _agregar(fx, t).dados)
    txt = json.dumps(todos)
    for proibido in ("SINTETICO", "report_id", "exemplo.invalid", "127.0.0.1", "Rede Sintetica", "192.0.2.53", "android"):
        assert proibido not in txt


def _lista(chaves):
    itens = "".join(f"<Contents><Key>{k}</Key><Size>{n}</Size></Contents>" for k, n in chaves)
    return f'<?xml version="1.0"?><ListBucketResult xmlns="{NS}"><IsTruncated>false</IsTruncated>{itens}</ListBucketResult>'


def _montar(fx, dia="20261106", horas=24):
    """Servidor S3 falso: cada hora tem um arquivo por teste (mais um `.tar.gz` duplicado, que não pode ser baixado)."""
    baixados = []

    def listagem(request):
        prefixo = dict(request.url.params)["prefix"]
        h = int(prefixo.split("/")[2])
        if h >= horas:
            return httpx.Response(200, text=_lista([]))
        chaves = []
        for t in ooni.TESTES_LEVES + (ooni.TESTE_WEB,):
            chaves += [(f"{prefixo}{t}/{dia}{h:02d}_BR_{t}.n1.0.jsonl.gz", 100), (f"{prefixo}{t}/{dia}{h:02d}_BR_{t}.n1.0.tar.gz", 100)]
        return httpx.Response(200, text=_lista(chaves))

    def objeto(request):
        baixados.append(request.url.path)
        t = request.url.path.split("/")[5]
        return httpx.Response(200, content=gzip.compress(fx("ooni", f"{t}.jsonl").read_bytes()))

    respx.get(url__regex=r"https://ooni-data-eu-fra\.s3\.amazonaws\.com/raw/.+\.jsonl\.gz").mock(side_effect=objeto)
    respx.get(url__regex=r"https://ooni-data-eu-fra\.s3\.amazonaws\.com/\?.*").mock(side_effect=listagem)
    return baixados


@respx.mock
def test_run_agrega_dia_incremental_e_so_jsonl(base, log, fx, monkeypatch):
    monkeypatch.setattr(fonte, "HORAS_AMOSTRA", (2,))
    baixados = _montar(fx)
    r = fonte.run("2026-11-07", base, log, espera_s=0, dias_novos=1)
    assert r["dias_baixados"] == ["2026-11-06"] and r["requisicoes"] >= 24
    assert all(p.endswith(".jsonl.gz") for p in baixados)
    assert sum("webconnectivity" in p for p in baixados) == 1                    # só a hora da amostra
    assert sum("/whatsapp/" in p for p in baixados) == 24
    n = read_json_gz(base / "normalized" / "2026-11-07" / "summary" / "ooni_bloqueios.json.gz")
    dia = n["dias"]["2026-11-06"]
    assert dia["testes"]["whatsapp"]["64496"]["n"] == 4 * 24 and dia["web_amostra"]["arquivos"] == 1
    assert dia["web"]["64496"]["n"] == 4
    assert n["licenca"] == "CC BY-NC-SA 4.0" and "OONI" in n["atribuicao"]
    assert not list(base.rglob("*.jsonl*"))                                       # o bruto é descartado: nada em disco além do agregado
    baixados.clear()                                                              # uma semana depois: reaproveita o dia e baixa o seguinte
    r2 = fonte.run("2026-11-08", base, log, espera_s=0, dias_novos=1)
    assert r2["dias_baixados"] == ["2026-11-07"]
    n2 = read_json_gz(base / "normalized" / "2026-11-08" / "summary" / "ooni_bloqueios.json.gz")
    assert set(n2["dias"]) == {"2026-11-06", "2026-11-07"}


@respx.mock
def test_teto_de_bytes_corta_a_amostra_web(base, log, fx, monkeypatch):
    monkeypatch.setattr(fonte, "HORAS_AMOSTRA", (2, 10, 18))
    _montar(fx)
    fonte.run("2026-11-07", base, log, espera_s=0, dias_novos=1, teto_gb=250e-9)  # 250 bytes: cabem 2 arquivos de 100
    n = read_json_gz(base / "normalized" / "2026-11-07" / "summary" / "ooni_bloqueios.json.gz")
    a = n["dias"]["2026-11-06"]["web_amostra"]
    assert a["arquivos"] == 2 and a["arquivos_da_amostra"] == 3 and a["completa"] is False


@respx.mock
def test_sem_web_nao_baixa_webconnectivity(base, log, fx):
    baixados = _montar(fx)
    fonte.run("2026-11-07", base, log, espera_s=0, dias_novos=1, web=False)
    assert not any("webconnectivity" in p for p in baixados)
    n = read_json_gz(base / "normalized" / "2026-11-07" / "summary" / "ooni_bloqueios.json.gz")
    assert n["dias"]["2026-11-06"]["web"] is None and n["dias"]["2026-11-06"]["web_amostra"] is None


@respx.mock
def test_dia_incompleto_falha_alto(base, log, fx):
    _montar(fx, horas=5)
    with pytest.raises(RuntimeError):
        fonte.run("2026-11-07", base, log, espera_s=0, dias_novos=1)


@respx.mock
def test_interruptor_desliga_sem_requisicao(monkeypatch, base):
    """Com OONI_ATIVO=0 a etapa sai com 0 e não toca a rede (rollback barato)."""
    monkeypatch.setenv("OONI_ATIVO", "0")
    monkeypatch.setenv("DATA_DIR", str(base))
    rota = respx.get(url__regex=r"https://ooni-data-eu-fra.*").mock(return_value=httpx.Response(500))
    assert fonte.main(["--date", "2026-11-07"]) == 0 and rota.call_count == 0
    assert not list(base.rglob("ooni_bloqueios*"))


@respx.mock
def test_sem_a_variavel_a_coleta_vem_ligada(monkeypatch, base):
    """Sem OONI_ATIVO a fonte coleta, como a TeleGeography."""
    monkeypatch.delenv("OONI_ATIVO", raising=False)
    monkeypatch.setenv("DATA_DIR", str(base))
    rota = respx.get(url__regex=r"https://ooni-data-eu-fra.*").mock(return_value=httpx.Response(500))
    fonte.main(["--date", "2026-11-07", "--dias", "1"])
    assert rota.call_count > 0


def test_user_agent_identificado():
    assert fonte.HEADERS["User-Agent"].startswith("arandurape/") and fonte.ESPERA_S >= 1.0
