# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — RDAP de contatos do Registro.br: completude por resposta, rodízio, recuo, conexão derrubada e bloqueio, sem rede (respx, dados sintéticos)."""
import json

import httpx
import pytest
import respx

from core.common import read_json_gz, write_json_gz
from sources.rdap_contatos import collect as fonte

URL = fonte.BASE_URL


@pytest.fixture
def respostas(fx):
    def _r(nome):
        return json.loads(fx("rdap_contatos", nome).read_text(encoding="utf-8"))
    return {"completa": _r("autnum_64496.json"), "completa2": _r("autnum_64497.json"), "incompleta": _r("autnum_64497_incompleto.json")}


def _universo(tmp_path, asns, data="2026-11-10"):
    write_json_gz(tmp_path / "normalized" / data / "summary" / "orgs.json.gz", {"orgs": {str(a): {"name": "x"} for a in asns}})


def _doc(tmp_path, d):
    return read_json_gz(tmp_path / "normalized" / d / "summary" / "rdap_contatos.json.gz")


def _run(tmp_path, log, d, **kw):
    kw.setdefault("intervalo_s", 0)
    kw.setdefault("dormir", lambda s: None)
    return fonte.run(d, tmp_path, log, **kw)


def _mock(roteiro):
    """`roteiro`: função asn -> httpx.Response | Exception."""
    pedidos = []

    def despachar(request: httpx.Request):
        assert request.headers["user-agent"].startswith("arandurape/")
        asn = int(request.url.path.rsplit("/", 1)[1])
        pedidos.append(asn)
        r = roteiro(asn)
        if isinstance(r, Exception):
            raise r
        return r

    m = respx.mock(assert_all_called=False)
    m.route(url__startswith=URL).mock(side_effect=despachar)
    return m, pedidos


def test_extrair_completa_aninhada_incompleta_e_nao_autnum(respostas):
    rec = fonte.extrair(respostas["completa"])
    assert rec["completo"] and {c["papel"] for c in rec["contatos"]} == {"administrative", "abuse"}      # administrative aninhado no registrant conta
    assert set(rec["contatos"][0]) == {"papel", "email", "handle"}                                         # recorte mínimo: sem nome, endereço, representante
    assert fonte.extrair(respostas["completa2"])["contatos"][0]["email"] == "admin2@example.net"           # normaliza caixa
    inc = fonte.extrair(respostas["incompleta"])
    assert inc == {"contatos": [], "completo": False}
    assert fonte.extrair({"errorCode": 404}) is None and fonte.extrair("x") is None


def test_rodada_completa_guarda_so_o_recorte_e_declara_cobertura(tmp_path, log, respostas):
    _universo(tmp_path, [64496, 64497, 64498])
    m, pedidos = _mock(lambda a: httpx.Response(404) if a == 64498 else httpx.Response(200, json=respostas["completa"]))
    with m:
        med = _run(tmp_path, log, "2026-11-10")
    assert pedidos == [64496, 64497, 64498] and med["validas"] == 2 and med["nao_encontrado"] == 1 and med["parou"] is None
    d = _doc(tmp_path, "2026-11-10")
    assert d["cobertura"]["asns_no_universo"] == 3 and d["cobertura"]["com_leitura_valida"] == 3 and d["cobertura"]["completos"] == 2
    assert d["cobertura"]["leitura_mais_antiga"] == d["cobertura"]["leitura_mais_recente"] == "2026-11-10"
    assert d["contatos"]["64496"]["status"] == "completo" and d["contatos"]["64498"] == {"em": "2026-11-10", "tentou_em": "2026-11-10", "status": "nao_encontrado", "contatos": [], "incompletas": 0}
    texto = json.dumps(d)
    for proibido in ("Ficticio", "Rua Ficticia", "legalRepresentative", "00000-000"):
        assert proibido not in texto                                          # sem nome, endereço nem representante legal


def test_resposta_incompleta_nao_conta_como_leitura_e_mantem_a_anterior(tmp_path, log, respostas):
    _universo(tmp_path, [64496])
    m, _ = _mock(lambda a: httpx.Response(200, json=respostas["completa"]))
    with m:
        _run(tmp_path, log, "2026-11-10")
    _universo(tmp_path, [64496], "2026-11-11")
    m, _ = _mock(lambda a: httpx.Response(200, json=respostas["incompleta"]))
    with m:
        med = _run(tmp_path, log, "2026-11-11")
    assert med["incompletas"] == 1 and med["validas"] == 0
    v = _doc(tmp_path, "2026-11-11")["contatos"]["64496"]
    assert v["em"] == "2026-11-10" and v["tentou_em"] == "2026-11-11" and v["status"] == "completo" and len(v["contatos"]) == 2     # a leitura válida segue, com a data dela


def test_so_incompleto_fica_fora_da_cobertura_e_entra_depois_dos_nunca_vistos(tmp_path, log, respostas):
    _universo(tmp_path, [64496, 64497, 64498])
    m, pedidos = _mock(lambda a: httpx.Response(200, json=respostas["incompleta"] if a == 64496 else respostas["completa"]))
    with m:
        _run(tmp_path, log, "2026-11-10", asns_por_execucao=1)
        d = _doc(tmp_path, "2026-11-10")
        assert d["cobertura"]["so_incompletos"] == 1 and d["cobertura"]["com_leitura_valida"] == 0 and d["contatos"]["64496"]["em"] is None
        _run(tmp_path, log, "2026-11-11", asns_por_execucao=2)             # os nunca vistos antes do que já veio incompleto
    assert pedidos == [64496, 64497, 64498]
    assert _doc(tmp_path, "2026-11-11")["cobertura"]["com_leitura_valida"] == 2


def test_rodizio_idempotente_na_mesma_data_continua_de_onde_parou(tmp_path, log, respostas):
    _universo(tmp_path, [64496, 64497, 64498, 64499])
    m, pedidos = _mock(lambda a: httpx.Response(200, json=respostas["completa"]))
    with m:
        _run(tmp_path, log, "2026-11-10", asns_por_execucao=2)
        _run(tmp_path, log, "2026-11-10", asns_por_execucao=2)             # repetir com --force: não relê os dois primeiros
    assert pedidos == [64496, 64497, 64498, 64499]
    d = _doc(tmp_path, "2026-11-10")
    assert d["cobertura"]["com_leitura_valida"] == 4 and not [p for p in d["contatos"].values() if p.get("herdado")]


def test_ausencia_real_so_e_confirmada_com_fonte_saudavel_e_duas_vezes(tmp_path, log, respostas):
    asns = list(range(64500, 64510))
    alvo = 64509                                                          # o último: a janela já tem 9 respostas completas
    _universo(tmp_path, asns)
    m, _ = _mock(lambda a: httpx.Response(200, json=respostas["incompleta"] if a == alvo else respostas["completa"]))
    with m:
        _run(tmp_path, log, "2026-11-10")
        assert _doc(tmp_path, "2026-11-10")["contatos"][str(alvo)]["status"] == "incompleto"        # uma vez só: não conclui
        _universo(tmp_path, asns, "2026-11-11")
        med = _run(tmp_path, log, "2026-11-11", asns_por_execucao=10)
    v = _doc(tmp_path, "2026-11-11")["contatos"][str(alvo)]
    assert v["status"] == "parcial_confirmado" and v["em"] == "2026-11-11" and med["confirmadas_sem_email"] == 1


def test_degradacao_recua_dobrando_o_intervalo_e_encerra_se_persistir(tmp_path, log, respostas):
    asns = list(range(64500, 64530))
    _universo(tmp_path, asns)
    dormiu = []
    m, pedidos = _mock(lambda a: httpx.Response(200, json=respostas["incompleta"]))
    with m:
        med = _run(tmp_path, log, "2026-11-10", intervalo_s=10, dormir=dormiu.append, relogio=lambda: 0.0)
    assert med["recuos"] == 2 and med["intervalo_s"] == 40 and "degradação persistente" in med["parou"]
    assert len(pedidos) == 15 and _doc(tmp_path, "2026-11-10")["ultima_execucao"]["parou"] == med["parou"]    # 5 por janela, 3 janelas
    assert all(c["status"] == "incompleto" for c in _doc(tmp_path, "2026-11-10")["contatos"].values())      # nada vira leitura válida


def test_conexao_derrubada_recua_e_encerra_apos_falhas_seguidas(tmp_path, log, respostas):
    _universo(tmp_path, [64496, 64497, 64498, 64499, 64500])
    m, pedidos = _mock(lambda a: httpx.RemoteProtocolError("Server disconnected without sending a response"))
    with m:
        med = _run(tmp_path, log, "2026-11-10", intervalo_s=10, relogio=lambda: 0.0)
    assert len(pedidos) == 3 and "3 falhas seguidas" in med["parou"] and med["recuos"] == 2 and med["intervalo_s"] == 40
    d = _doc(tmp_path, "2026-11-10")
    assert d["contatos"] == {} and d["cobertura"]["com_leitura_valida"] == 0           # queda de conexão não vira dado


def test_bloqueio_429_encerra_na_hora_e_guarda_o_que_ja_leu(tmp_path, log, respostas):
    _universo(tmp_path, [64496, 64497, 64498])
    m, pedidos = _mock(lambda a: httpx.Response(429) if a == 64497 else httpx.Response(200, json=respostas["completa"]))
    with m:
        med = _run(tmp_path, log, "2026-11-10")
    assert pedidos == [64496, 64497] and "bloqueio" in med["parou"]
    assert list(_doc(tmp_path, "2026-11-10")["contatos"]) == ["64496"]


def test_idade_e_universo_acompanham_a_rodada_anterior(tmp_path, log, respostas):
    _universo(tmp_path, [64496, 64497])
    m, _ = _mock(lambda a: httpx.Response(200, json=respostas["completa"]))
    with m:
        _run(tmp_path, log, "2026-11-10")
        _universo(tmp_path, [64496], "2026-11-12")                               # 64497 saiu do Registro.br
        _run(tmp_path, log, "2026-11-12", asns_por_execucao=1)
    d = _doc(tmp_path, "2026-11-12")
    assert list(d["contatos"]) == ["64496"] and d["contatos"]["64496"]["em"] == "2026-11-12"
