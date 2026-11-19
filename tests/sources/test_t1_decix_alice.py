# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — Alice-LG do DE-CIX Rio e São Paulo: API → normalizado, sem rede, com servidor Alice falso (respx)."""
import copy
import json
import re

import httpx
import pytest
import respx

from core.common import read_json_gz
from sources.decix_alice import collect as decix
from core.site import USER_AGENT

SESS = "decix_rs_sessions.json.gz"
ROTAS = "decix_rs_rotas.json.gz"


def _j(fx, nome):
    return json.loads(fx("decix_alice", nome).read_text(encoding="utf-8"))


class Servidor:
    """Alice falso do DE-CIX: responde pelos fixtures, registra cada requisição (caminho, instante do relógio falso) e aceita falhas injetadas."""

    def __init__(self, fx, relogio=None):
        self.fx, self.relogio = fx, relogio
        self.pedidos: list[tuple[str, float, str]] = []
        self.falha = None                           # callable(caminho) -> httpx.Response | Exception | None
        self.mock = respx.mock(assert_all_called=False)
        self.mock.get(url__startswith=decix.BASE).mock(side_effect=self._responder)
        self.molde = _j(fx, "routes_received_molde.json")
        self.pequeno = _j(fx, "routes_received_pequeno.json")

    def caminho(self, request) -> str:
        return str(request.url)[len(decix.BASE) + 1:]

    def _responder(self, request):
        c = self.caminho(request)
        self.pedidos.append((c, self.relogio.t if self.relogio else 0.0, request.headers.get("user-agent", "")))
        if self.relogio:
            self.relogio.t += 0.2                   # a resposta leva 0,2 s
        if self.falha:
            f = self.falha(c)
            if isinstance(f, Exception):
                raise f
            if f is not None:
                return f
        if c == "status":
            return httpx.Response(200, json=_j(self.fx, "status.json"))
        if c == "routeservers":
            return httpx.Response(200, json=_j(self.fx, "routeservers.json"))
        m = re.fullmatch(r"routeservers/(rs\d_\w+?_ipv\d)_de-cix/neighbors", c)
        if m:
            return httpx.Response(200, json=_j(self.fx, f"neighbors_{m[1]}.json"))
        m = re.fullmatch(r"routeservers/([\w-]+)/neighbors/(\w+)/routes/received\?page=(\d+)&page_size=250", c)
        if m:
            return httpx.Response(200, json=self._pagina(m[2], int(m[3])))
        return httpx.Response(404)

    def _pagina(self, vizinho: str, pg: int) -> dict:
        if vizinho != "R93_2":
            return copy.deepcopy(self.pequeno)
        d = copy.deepcopy(self.molde)                # 600 rotas em 3 páginas (250 + 250 + 100), origens 64520 e 64521 alternadas por página
        n = 100 if pg == 2 else 250
        d["pagination"]["page"] = pg
        d["imported"] = [{**d["imported"][0], "network": f"10.{pg}.{i}.0/24", "bgp": {**d["imported"][0]["bgp"], "as_path": [64497, 64520 + (i % 2)]}} for i in range(n)]
        return d

    def n_rotas(self) -> int:
        return sum(1 for c, _, _ in self.pedidos if "/routes/" in c)


@pytest.fixture()
def srv(fx, monkeypatch):
    monkeypatch.setattr(decix, "PAUSA_S", 0)
    return Servidor(fx)


def _run(srv, base, log, date, **kw):
    with srv.mock:
        return decix.run(date, base, log, dormir=lambda s: None, **kw)


def test_run_normaliza_sessoes_so_do_escopo_e_le_as_rotas_por_vizinho(srv, base, log, date_str):
    res = _run(srv, base, log, date_str)
    summary = base / "normalized" / date_str / "summary"
    s = read_json_gz(summary / SESS)
    assert s["total_rs"] == 8 and s["versao_alice"] == "6.2.0" and not any("fra" in r["rs"] for r in s["rs"])            # Frankfurt nunca entra
    rs = {r["rs"]: r for r in s["rs"]}
    assert (rs["rs1_rio_ipv4_de-cix"]["ixp"], rs["rs1_rio_ipv4_de-cix"]["afi"], rs["rs1_rio_ipv4_de-cix"]["numero"]) == ("decix-rj", "v4", "rs1")
    assert (rs["rs2_sao_ipv6_de-cix"]["ixp"], rs["rs2_sao_ipv6_de-cix"]["afi"]) == ("decix-sp", "v6")
    assert rs["rs1_sao_ipv4_de-cix"]["estado_rotas"] == "BUSY" and rs["rs2_sao_ipv4_de-cix"]["estado_rotas"] == "READY"        # o estado do /status vem pelo nome do RS
    assert rs["rs1_rio_ipv4_de-cix"]["sessoes"] == 5 and rs["rs1_rio_ipv4_de-cix"]["sessoes_up"] == 4 and rs["rs1_rio_ipv4_de-cix"]["vizinhos_em"] == "2026-11-10T11:30:00.123456789Z"
    v = next(x for x in s["sessoes"] if x["rs"] == "rs1_rio_ipv4_de-cix" and x["asn"] == 64497)
    assert v["ixp"] == "decix-rj" and v["id_vizinho"] == "R93_2" and v["rotas"]["recebidas"] == 600 and v["estado"] == "up"
    # nível 3: um RS por (cidade, família); São Paulo vai pelo rs2 porque o cache de rotas do rs1 está BUSY
    r = read_json_gz(summary / ROTAS)
    por = {(v["ixp"], v["asn"]): v for v in r["vizinhos"]}
    assert set(por) == {("decix-rj", 64496), ("decix-rj", 64497), ("decix-rj", 64500), ("decix-sp", 64496)}               # sem rotas, down e fora do escopo: ninguém
    assert por[("decix-sp", 64496)]["rs"] == "rs2_sao_ipv4_de-cix" and por[("decix-rj", 64496)]["rs"] == "rs1_rio_ipv4_de-cix"
    a = por[("decix-rj", 64496)]
    assert a["origens"] == {"64496": 2, "64510": 1} and a["total"] == 3 and a["lidas"] == 3 and a["completo"] is True and a["paginas"] == 1
    b = por[("decix-rj", 64497)]
    assert (b["total"], b["lidas"], b["paginas"], b["completo"]) == (600, 600, 3, True) and b["origens"] == {"64520": 300, "64521": 300}
    assert r["cobertura_rodizio"]["total"] == {"elegiveis": 4, "lidos_na_rodada": 4, "herdados": 0, "sem_leitura": 0, "idade_max_dias": 0, "pulados_lentos": 0}
    assert res["requisicoes"] == 2 + 8 + 3 + 3 and srv.n_rotas() == 1 + 3 + 1 + 1 and res["nivel3"]["consultados"] == 4
    assert not (base / "raw").exists()                                                                                      # derivados apenas


def test_user_agent_identificado_em_toda_requisicao(srv, base, log, date_str):
    _run(srv, base, log, date_str)
    assert {ua for _, _, ua in srv.pedidos} == {USER_AGENT} and "@" not in decix.HEADERS["User-Agent"]


def test_paginas_max_marca_vizinho_parcial(srv, base, log, date_str):
    _run(srv, base, log, date_str, paginas_max=2)
    r = read_json_gz(base / "normalized" / date_str / "summary" / ROTAS)
    b = next(v for v in r["vizinhos"] if v["asn"] == 64497)
    assert (b["lidas"], b["paginas"], b["completo"], b["total"]) == (500, 2, False, 600)         # as origens contadas são um piso, e o documento diz que é parcial
    assert r["paginas_max_vizinho"] == 2


def test_pausa_minima_de_1s_entre_todas_as_requisicoes(fx, base, log, date_str, monkeypatch):
    monkeypatch.setattr(decix, "PAUSA_S", 1.0)
    from tests.sources.test_t1_ixbr_alice_rotas import _RelogioDormindo
    rel = _RelogioDormindo()
    srv = Servidor(fx, rel)
    with srv.mock:
        decix.run(date_str, base, log, dormir=rel.dormir, relogio=rel)
    ts = [t for _, t, _ in srv.pedidos]
    assert len(ts) == 2 + 8 + 6 and all(b - a >= 1.0 for a, b in zip(ts, ts[1:]))


def test_rodizio_cobre_todos_os_vizinhos_em_rodadas_e_herda_com_a_data_original(srv, base, log, monkeypatch):
    # orçamento de 11 requisições por rodada: 10 de níveis 0 e 1 e só 1 de rotas (uma página); o rodízio anda 1 vizinho por rodada
    lidos = []
    for dia in ("2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13"):
        srv.pedidos.clear()
        _run(srv, base, log, dia, orcamento=11)
        lidos.append([c for c, _, _ in srv.pedidos if "/routes/" in c])
    todos = [c for l in lidos for c in l]
    assert [len(l) for l in lidos] == [1, 1, 1, 1]
    assert len(set(todos)) == 4                                    # nenhum vizinho repetido antes de todos terem sido lidos
    # o vizinho de 600 rotas (3 páginas) não cabe no orçamento sozinho: sai parcial, e a leitura anterior não se perde por isso
    r = read_json_gz(base / "normalized" / "2026-11-13" / "summary" / ROTAS)
    assert {v["asn"] for v in r["vizinhos"]} == {64496, 64497, 64500}
    tot = r["cobertura_rodizio"]["total"]
    assert tot["elegiveis"] == 4 and tot["lidos_na_rodada"] == 1 and tot["sem_leitura"] == 0 and tot["herdados"] == 3 and tot["idade_max_dias"] == 3
    assert any(v.get("herdado") for v in r["vizinhos"]) and r["orcamento"] == 11


def test_bloqueio_429_para_na_hora_registra_e_a_proxima_rodada_nem_tenta(srv, base, log, date_str):
    srv.falha = lambda c: httpx.Response(429) if "/routes/" in c else None
    with srv.mock, pytest.raises(RuntimeError, match="bloqueio"):
        decix.run(date_str, base, log, dormir=lambda s: None)
    assert srv.n_rotas() == 1                                                                 # primeira resposta 429: nenhuma outra requisição de rotas
    r = read_json_gz(base / "normalized" / date_str / "summary" / ROTAS)
    assert r["bloqueio"]["motivo"] == "HTTP 429" and r["vizinhos"] == []
    assert (base / "normalized" / date_str / "summary" / SESS).exists()                         # o nível 0 e 1 já gravados não se perdem
    srv.pedidos.clear()
    with srv.mock, pytest.raises(RuntimeError, match="bloqueio registrado"):
        decix.run("2026-09-21", base, log, dormir=lambda s: None)
    assert srv.pedidos == []                                                                  # sem rede
    srv.falha = None
    with srv.mock:                                                                            # depois de avaliado pelo mantenedor: --ignorar-bloqueio
        decix.run("2026-09-22", base, log, dormir=lambda s: None, force=True)
    assert "bloqueio" not in read_json_gz(base / "normalized" / "2026-09-22" / "summary" / ROTAS)
    srv.pedidos.clear()
    with srv.mock:
        decix.run("2026-09-30", base, log, dormir=lambda s: None)                              # mais de 7 dias depois da rodada bloqueada (20/09) e a de 22/09 não bloqueou
    assert srv.pedidos


def test_bloqueio_403_no_nivel_0_nao_consulta_mais_nada(srv, base, log, date_str):
    srv.falha = lambda c: httpx.Response(403) if c == "status" else None
    with srv.mock, pytest.raises(RuntimeError, match="bloqueio"):
        decix.run(date_str, base, log, dormir=lambda s: None)
    assert [c for c, _, _ in srv.pedidos] == ["status"]
    s = read_json_gz(base / "normalized" / date_str / "summary" / SESS)
    assert s["bloqueio"]["motivo"] == "HTTP 403" and s["sessoes"] == [] and not (base / "normalized" / date_str / "summary" / ROTAS).exists()


def test_conexao_derrubada_duas_vezes_seguidas_conta_como_bloqueio(srv, base, log, date_str):
    srv.falha = lambda c: httpx.RemoteProtocolError("Server disconnected") if "/routes/" in c else None
    dormidas = []
    with srv.mock, pytest.raises(RuntimeError, match="bloqueio"):
        decix.run(date_str, base, log, dormir=dormidas.append)
    assert srv.n_rotas() == 2                                                                 # a queda e uma única repetição
    assert decix.ESPERA_CONEXAO_S in dormidas
    assert "conexão derrubada duas vezes" in read_json_gz(base / "normalized" / date_str / "summary" / ROTAS)["bloqueio"]["motivo"]


def test_queda_de_conexao_isolada_repete_uma_vez_e_segue_sem_bloqueio(srv, base, log, date_str):
    caiu = []

    def falha(c):
        if "/routes/" in c and not caiu:
            caiu.append(c)
            return httpx.ConnectError("sem rota")
        return None
    srv.falha = falha
    dormidas = []
    with srv.mock:
        decix.run(date_str, base, log, dormir=dormidas.append)
    assert len(caiu) == 1 and decix.ESPERA_CONEXAO_S in dormidas
    assert "bloqueio" not in read_json_gz(base / "normalized" / date_str / "summary" / ROTAS)


def test_liberar_bloqueio_mantem_o_registro_e_a_proxima_rodada_volta_a_coletar(srv, base, log, date_str):
    srv.falha = lambda c: httpx.Response(429) if "/routes/" in c else None
    with srv.mock, pytest.raises(RuntimeError, match="bloqueio"):
        decix.run(date_str, base, log, dormir=lambda s: None)
    assert decix.liberar_bloqueio(base, date_str, "queda de rede, não bloqueio") == [ROTAS]
    b = read_json_gz(base / "normalized" / date_str / "summary" / ROTAS)["bloqueio"]
    assert b["motivo"] == "HTTP 429" and b["liberado"]["motivo"] == "queda de rede, não bloqueio" and b["liberado"]["por"] == "mantenedor"
    assert decix.liberar_bloqueio(base, date_str, "de novo") == []                           # idempotente
    srv.falha = None
    srv.pedidos.clear()
    with srv.mock:
        decix.run("2026-09-21", base, log, dormir=lambda s: None)                              # sem --ignorar-bloqueio
    assert srv.pedidos


def test_erro_5xx_repete_com_recuo_e_falha_de_vizinho_nao_para_a_rodada(srv, base, log, date_str, monkeypatch):
    monkeypatch.setattr(decix, "MAX_FALHA", 1.0)
    monkeypatch.setattr(decix, "PAUSA_S", 0.5)
    estado = {"n": 0}

    def falha(c):
        if "/neighbors/R93_1/routes/" in c:
            return httpx.Response(500)                                                        # R93_1 nunca responde
        if c == "status":
            estado["n"] += 1
            return httpx.Response(503) if estado["n"] == 1 else None                           # o /status se recupera na repetição
        return None
    srv.falha = falha
    pausas = []
    with srv.mock:
        res = decix.run(date_str, base, log, dormir=pausas.append)
    assert res["nivel3"]["falhas"] == 1 and res["nivel3"]["consultados"] == 3 and max(pausas) > decix.PAUSA_S
    r = read_json_gz(base / "normalized" / date_str / "summary" / ROTAS)
    assert [f["asn"] for f in r["falhas"]] == [64496] and "bloqueio" not in r


def test_rs_do_escopo_insuficiente_falha_alto(srv, base, log, date_str, fx):
    srv.falha = lambda c: httpx.Response(200, json={"routeservers": [{"id": "rs1_fra_ipv4_de-cix", "name": "x", "group": "x"}]}) if c == "routeservers" else None
    with srv.mock, pytest.raises(RuntimeError, match="route servers de Rio e São Paulo"):
        decix.run(date_str, base, log, dormir=lambda s: None)
