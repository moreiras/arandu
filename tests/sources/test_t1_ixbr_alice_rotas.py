# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — Alice-LG do IX.br, rotas por vizinho (níveis 2 e 3): API → normalizado, sem rede, com servidor Alice falso (respx)."""
import json

import httpx
import pytest
import respx

from core.common import read_json_gz, write_json_gz
from sources.ixbr_alice_rotas import collect as rotas


def _j(fx, nome):
    return json.loads(fx("ixbr_alice_rotas", nome).read_text(encoding="utf-8"))


def _s(rs, ixp, asn, ip, filtradas=0, recebidas=10, afi="v4", estado="up"):
    return {"rs": rs, "ixp": ixp, "afi": afi, "neighbor_ip": ip, "asn": asn, "estado": estado,
            "rotas": {"recebidas": recebidas, "aceitas": recebidas - filtradas, "filtradas": filtradas, "exportadas": 5}}


@pytest.fixture()
def entrada(base, fx, date_str):
    """rs_sessions e dicionário do `ixbr_alice` já normalizados: SP rs1 (READY) e rs2 (READY) com os mesmos vizinhos, RJ rs1 (ERROR) e rs2, e um PTT fora do N3."""
    sessoes = [
        _s("SP-rs1-v4", "sp", 64496, "203.0.113.10", filtradas=7), _s("SP-rs2-v4", "sp", 64496, "203.0.113.10", filtradas=7),      # mesmo vizinho nos dois RS: 1 consulta
        _s("SP-rs1-v4", "sp", 64497, "203.0.113.20"), _s("SP-rs2-v4", "sp", 64497, "203.0.113.20"),
        _s("SP-rs1-v4", "sp", 64498, "203.0.113.30"),
        _s("SP-rs1-v4", "sp", 64499, "203.0.113.40", estado="down", filtradas=3),                                                    # down: não entra
        _s("RJ-rs1-v4", "rj", 64496, "198.18.0.10"), _s("RJ-rs2-v4", "rj", 64496, "198.18.0.10"),                                    # rs1 em ERROR: usa o rs2
        _s("PR-rs1-v4", "pr", 64496, "198.18.1.10", filtradas=2),                                                                    # fora do N3, mas no N2
    ]
    rs = [{"rs": "SP-rs1-v4", "estado_rotas": "READY"}, {"rs": "SP-rs2-v4", "estado_rotas": "READY"}, {"rs": "RJ-rs1-v4", "estado_rotas": "ERROR"},
          {"rs": "RJ-rs2-v4", "estado_rotas": "READY"}, {"rs": "PR-rs1-v4", "estado_rotas": "READY"}]
    destino = base / "normalized" / date_str / "summary"
    destino.mkdir(parents=True)
    write_json_gz(destino / "rs_sessions.json.gz", {"versao_alice": "6.1.0", "rs": rs, "sessoes": sessoes})
    write_json_gz(destino / "ixbr_communities.json.gz", _j(fx, "dicionario.json"))
    return destino


@pytest.fixture()
def api(fx, monkeypatch):
    monkeypatch.setattr(rotas, "PAUSA_S", 0)
    r = respx.mock(assert_all_called=False)
    r.get(url__regex=r".*/routeservers/SP-rs1-v4/neighbors/AS64496_203_0_113_10/routes/filtered.*").respond(200, json=_j(fx, "filtered_SP-rs1-v4_AS64496.json"))
    r.get(url__regex=r".*/routeservers/PR-rs1-v4/neighbors/AS64496_198_18_1_10/routes/filtered.*").respond(200, json=_j(fx, "filtered_SP-rs1-v4_AS64496.json"))
    r.get(url__regex=r".*/routeservers/SP-rs1-v4/neighbors/AS6449[67]_203_0_113_(10|20)/routes/received.*").respond(200, json=_j(fx, "received_SP-rs1-v4_AS64497.json"))
    r.get(url__regex=r".*/routeservers/SP-rs1-v4/neighbors/AS64498_203_0_113_30/routes/received.*").respond(200, json=_j(fx, "received_SP-rs1-v4_AS64498.json"))
    r.get(url__regex=r".*/routeservers/RJ-rs2-v4/neighbors/AS64496_198_18_0_10/routes/received.*").respond(404)
    return r


def test_id_do_vizinho_e_escolha_de_um_route_server_por_vizinho(entrada):
    assert rotas.id_vizinho(64496, "203.0.113.10") == "AS64496_203_0_113_10"
    assert rotas.id_vizinho(6939, "2001:12f8:0:9::214") == "AS6939_2001_12f8_0_9__214"
    doc = read_json_gz(entrada / "rs_sessions.json.gz")
    n2 = rotas.elegiveis(doc, 2)
    assert [(s["rs"], s["asn"]) for s in n2] == [("SP-rs1-v4", 64496), ("PR-rs1-v4", 64496)]          # prioridade: SP antes dos demais; só up com filtradas > 0; 1 RS por vizinho
    n3 = rotas.elegiveis(doc, 3, ("sp", "rj"))
    assert [(s["rs"], s["asn"]) for s in n3] == [("SP-rs1-v4", 64496), ("SP-rs1-v4", 64497), ("SP-rs1-v4", 64498), ("RJ-rs2-v4", 64496)]     # RJ rs1 em ERROR: vai pelo rs2
    assert {s["ixp"] for s in rotas.elegiveis(doc, 3, ("todos",))} == {"sp", "rj", "pr"}


def test_nivel_2_conta_motivos_exatos_e_guarda_amostra(entrada, api, base, log, date_str):
    with api:
        res = rotas.run(date_str, base, log, dormir=lambda s: None, niveis=(2,))
    assert res["requisicoes"] == 2 and res["nivel2"] == {"elegiveis": 2, "consultados": 2, "falhas": 0, "herdados": 0} and "nivel3" not in res
    d = read_json_gz(entrada / "rs_filtered.json.gz")
    assert d["nivel"] == 2 and d["page_size"] == 250 and not (entrada / "rs_communities.json.gz").exists()
    v = d["vizinhos"][1]                                    # ordenado por (ixp, afi, asn, ip): PR vem antes de SP
    v = next(x for x in d["vizinhos"] if x["ixp"] == "sp")
    assert v["total"] == 7 and v["contagem"] == "exata"        # o total vem da paginação, não do tamanho da página (3 rotas)
    assert v["motivos"] == {"26162:300:0": 4, "26162:190:1": 2} and v["sem_motivo"] == 1
    assert [(a["p"], a["o"], a["m"]) for a in v["amostra"]][0] == ("198.51.100.0/24", 64511, ["26162:300:0"])
    assert d["cobertura"]["sp"] == {"elegiveis": 1, "coletados": 1, "herdados": 0}
    assert not (base / "raw").exists()                      # derivados apenas


def test_nivel_3_usa_as_contagens_exatas_de_communities(entrada, api, base, log, date_str, monkeypatch):
    monkeypatch.setattr(rotas, "MAX_FALHA", 0.5)               # 1 de 4 vizinhos falha de propósito (RJ: 404)
    with api:
        res = rotas.run(date_str, base, log, dormir=lambda s: None, niveis=(3,), ptts_n3=("sp", "rj"))
    assert res["nivel3"] == {"elegiveis": 4, "consultados": 3, "falhas": 1, "herdados": 0} and res["requisicoes"] == 4      # RJ: 404 (1 tentativa, sem repetição)
    d = read_json_gz(entrada / "rs_communities.json.gz")
    por = {v["asn"]: v for v in d["vizinhos"] if v["ixp"] == "sp"}
    a = por[64497]
    assert a["total"] == 100 and a["contagem"] == "exata" and a["comunidades"]["65000:64510"] == 30 and a["comunidades"]["65004:0:65021"] == 12
    assert a["comunidades"]["rt:65000:64510"] == 30 and a["comunidades"]["65535:666"] == 2
    b = por[64498]                                           # Alice sem filters_available: contagem pela amostra, rotulada
    assert b["contagem"] == "amostra" and b["comunidades"]["65001:64496"] == 2 and b["comunidades"]["26162:300:1"] == 1
    assert d["cobertura"]["sp"] == {"elegiveis": 3, "coletados": 3, "herdados": 0} and d["cobertura"]["rj"]["coletados"] == 0


def test_orcamento_limita_as_requisicoes_e_nivel_2_usa_no_maximo_metade(entrada, api, base, log, date_str):
    with api:
        res = rotas.run(date_str, base, log, dormir=lambda s: None, orcamento=3, ptts_n3=("sp",))
        assert api.calls.call_count == 3
    assert res["requisicoes"] == 3 and res["nivel2"]["consultados"] == 1 and res["nivel3"]["consultados"] == 2      # metade (3 // 2 = 1) ao nível 2; o resto ao 3


def test_sobra_do_nivel_2_vai_ao_nivel_3(entrada, api, base, log, date_str):
    with api:
        res = rotas.run(date_str, base, log, dormir=lambda s: None, orcamento=8, ptts_n3=("sp",))
    assert res["nivel2"]["consultados"] == 2 and res["nivel3"]["consultados"] == 3 and res["requisicoes"] == 5


def test_rodizio_herda_o_que_nao_coube_e_prioriza_o_mais_antigo(entrada, api, base, log, date_str):
    # rodada anterior: 64497 coletado há 9 dias (20/09) (herdável), 64498 há 2 dias, 64496 nunca: com orçamento 1, o nunca coletado vai primeiro
    anterior = base / "normalized" / "2026-09-13" / "summary"
    anterior.mkdir(parents=True)
    velho = {"rs": "SP-rs1-v4", "ixp": "sp", "afi": "v4", "ip": "203.0.113.20", "total": 90, "comunidades": {"65000:1": 1}}
    write_json_gz(anterior / "rs_communities.json.gz", {"vizinhos": [
        {**velho, "asn": 64497, "coletado_em": "2026-09-11T10:00:00Z"}, {**velho, "asn": 64498, "ip": "203.0.113.30", "coletado_em": "2026-09-18T10:00:00Z"},
        {**velho, "asn": 64111, "ip": "203.0.113.99", "coletado_em": "2026-09-18T10:00:00Z"},                 # sem sessão up hoje: não é herdado
        {**velho, "asn": 64222, "ip": "203.0.113.98", "coletado_em": "2026-07-01T10:00:00Z"}]})              # velho demais
    with api:
        res = rotas.run(date_str, base, log, dormir=lambda s: None, niveis=(3,), orcamento=1, ptts_n3=("sp",))
    assert res["nivel3"] == {"elegiveis": 3, "consultados": 1, "falhas": 0, "herdados": 2}
    d = read_json_gz(entrada / "rs_communities.json.gz")
    assert [(v["asn"], bool(v.get("herdado"))) for v in d["vizinhos"]] == [(64496, False), (64497, True), (64498, True)]
    assert next(v for v in d["vizinhos"] if v["asn"] == 64497)["coletado_em"] == "2026-09-11T10:00:00Z"          # a data original é preservada


class _RelogioDormindo:
    """Relógio falso em que dormir adianta o tempo; guarda o instante de cada requisição."""

    def __init__(self):
        self.t = 0.0
        self.pedidos: list[float] = []

    def __call__(self):
        return self.t

    def dormir(self, s):
        self.t += s


def test_respeita_a_pausa_minima_em_toda_requisicao_e_repete_com_recuo_so_em_erro_transitorio(entrada, fx, base, log, date_str, monkeypatch):
    monkeypatch.setattr(rotas, "PAUSA_S", 1.0)
    rel = _RelogioDormindo()
    chamadas = {"n": 0}

    def flaky(request):
        chamadas["n"] += 1
        rel.pedidos.append(rel.t)
        rel.t += 0.2                                                                       # a resposta leva 0,2 s
        return httpx.Response(503) if chamadas["n"] == 1 else httpx.Response(200, json=_j(fx, "filtered_SP-rs1-v4_AS64496.json"))

    def outro(request):
        rel.pedidos.append(rel.t)
        rel.t += 0.2
        return httpx.Response(200, json=_j(fx, "filtered_SP-rs1-v4_AS64496.json"))
    with respx.mock(assert_all_called=False) as r:
        r.get(url__regex=r".*/neighbors/AS64496_203_0_113_10/routes/filtered.*").mock(side_effect=flaky)
        r.get(url__regex=r".*/neighbors/AS64496_198_18_1_10/routes/filtered.*").mock(side_effect=outro)
        res = rotas.run(date_str, base, log, dormir=rel.dormir, niveis=(2,), relogio=rel)
    assert chamadas["n"] == 2 and res["requisicoes"] == 3 and res["falhas"] == 0       # a tentativa que falhou também gasta orçamento
    assert len(rel.pedidos) == 3 and all(b - a >= 1.0 for a, b in zip(rel.pedidos, rel.pedidos[1:]))      # nunca menos de 1 s entre duas requisições
    assert rel.pedidos[1] - rel.pedidos[0] >= 2.0                                        # o recuo depois do 503 é maior que a pausa


def test_falha_alto_e_para_a_rodada_quando_o_alice_nao_responde(entrada, base, log, date_str):
    with respx.mock(assert_all_called=False) as r:
        r.get(url__regex=r".*/routes/filtered.*").respond(500)
        with pytest.raises(RuntimeError, match="vizinhos falharam"):
            rotas.run(date_str, base, log, dormir=lambda s: None, niveis=(2,))
    d = read_json_gz(entrada / "rs_filtered.json.gz")                                    # o que se tinha foi gravado antes de falhar alto
    assert d["vizinhos"] == []


def test_sem_rs_sessions_falha(base, log, date_str):
    with pytest.raises(RuntimeError, match="rs_sessions"):
        rotas.run(date_str, base, log, dormir=lambda s: None)


def test_sem_orcamento_para_o_nivel_3_o_documento_sai_so_com_os_herdados(entrada, api, base, log, date_str):
    anterior = base / "normalized" / "2026-09-13" / "summary"
    anterior.mkdir(parents=True)
    write_json_gz(anterior / "rs_communities.json.gz", {"vizinhos": [{"rs": "SP-rs1-v4", "ixp": "sp", "afi": "v4", "asn": 64497, "ip": "203.0.113.20", "coletado_em": "2026-09-11T10:00:00Z", "total": 90, "comunidades": {}}]})
    with api:
        res = rotas.run(date_str, base, log, dormir=lambda s: None, orcamento=0, niveis=(3,), ptts_n3=("sp",))
    assert res["nivel3"] == {"elegiveis": 3, "consultados": 0, "falhas": 0, "herdados": 1}
    d = read_json_gz(entrada / "rs_communities.json.gz")
    assert [(v["asn"], v["herdado"]) for v in d["vizinhos"]] == [(64497, True)]


class _Relogio:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


@pytest.fixture()
def lenta(base, fx, date_str):
    """5 vizinhos do SP rs1 com rotas rejeitadas, numa rodada em que cada consulta leva 30 s no relógio falso (como o CE rs2 IPv4, ~66 s por vizinho)."""
    destino = base / "normalized" / date_str / "summary"
    destino.mkdir(parents=True)
    sessoes = [_s("SP-rs1-v4", "sp", 64500 + i, f"203.0.113.{50 + i}", filtradas=2) for i in range(5)] + [_s("PR-rs1-v4", "pr", 64496, "198.18.1.10", filtradas=2)]
    write_json_gz(destino / "rs_sessions.json.gz", {"versao_alice": "6.1.0", "rs": [{"rs": "SP-rs1-v4", "estado_rotas": "READY"}, {"rs": "PR-rs1-v4", "estado_rotas": "READY"}], "sessoes": sessoes})
    write_json_gz(destino / "ixbr_communities.json.gz", _j(fx, "dicionario.json"))
    rel = _Relogio()

    def lento(request):
        rel.t += 30.0 if "SP-rs1-v4" in str(request.url) else 1.0
        return httpx.Response(200, json=_j(fx, "filtered_SP-rs1-v4_AS64496.json"))
    r = respx.mock(assert_all_called=False)
    r.get(url__regex=r".*/routes/filtered.*").mock(side_effect=lento)
    return destino, rel, r


def test_route_server_lento_sai_da_rodada_e_o_tempo_por_rs_fica_registrado(lenta, base, log, date_str, monkeypatch):
    destino, rel, api = lenta
    monkeypatch.setattr(rotas, "PAUSA_S", 0)
    with api:
        res = rotas.run(date_str, base, log, dormir=lambda s: None, niveis=(2,), relogio=rel, lento_s=20, tempo_max_s=0)
        assert api.calls.call_count == 4                       # 3 do SP (a 3ª lenta tira o route server) + 1 do PR
    assert res["nivel2"]["consultados"] == 4 and [p["rs"] for p in res["rs_pulados"]] == ["SP-rs1-v4"]
    d = read_json_gz(destino / "rs_filtered.json.gz")
    assert d["tempo_por_rs"]["SP-rs1-v4"]["consultas"] == 3 and d["tempo_por_rs"]["SP-rs1-v4"]["s_medio"] == 30.0 and d["tempo_por_rs"]["PR-rs1-v4"]["consultas"] == 1
    assert d["cobertura"]["sp"] == {"elegiveis": 5, "coletados": 3, "herdados": 0, "pulados_lentos": 2} and d["rs_pulados"][0]["motivo"].startswith("3 consultas seguidas")


def test_tempo_maximo_da_rodada_para_a_coleta(lenta, base, log, date_str, monkeypatch):
    destino, rel, api = lenta
    with api:
        res = rotas.run(date_str, base, log, dormir=lambda s: None, niveis=(2,), relogio=rel, lento_s=1000, tempo_max_s=50)
        assert api.calls.call_count == 2                       # 30 s e 60 s: passou de 50 s, a rodada para
    assert res["nivel2"]["consultados"] == 2 and res["segundos"] == 60.0


def test_ptts_do_nivel_2_podem_ser_limitados(lenta, base, log, date_str):
    destino, rel, api = lenta
    with api:
        res = rotas.run(date_str, base, log, dormir=lambda s: None, niveis=(2,), relogio=rel, ptts_n2=("pr",))
        assert api.calls.call_count == 1
    assert res["nivel2"]["elegiveis"] == 1 and read_json_gz(destino / "rs_filtered.json.gz")["ptts"] == ["pr"]


# --- rodízio por vizinho em todos os PTTs ---------------------------------------------------------------------------------------------------------

def _escreve_rodada(base, fx, data, ptts: dict[str, int]):
    """rs_sessions de `data`: por PTT, `n` vizinhos up no rs1 (READY), todos com rotas recebidas."""
    destino = base / "normalized" / data / "summary"
    destino.mkdir(parents=True, exist_ok=True)
    sessoes = [_s(f"{p.upper()}-rs1-v4", p, 64600 + i, f"192.0.2.{i + 1}") for p, n in ptts.items() for i in range(n)]
    write_json_gz(destino / "rs_sessions.json.gz", {"versao_alice": "6.1.0", "rs": [{"rs": f"{p.upper()}-rs1-v4", "estado_rotas": "READY"} for p in ptts], "sessoes": sessoes})
    write_json_gz(destino / "ixbr_communities.json.gz", _j(fx, "dicionario.json"))
    return destino


def _servidor(fx, chamadas: list, falha=None, dia: str = "2026-09-20"):
    """Alice falso: o `cached_at` da resposta é o dia da rodada (o do fixture é fixo, de 2026-11-06)."""
    r = respx.mock(assert_all_called=False)

    def resp(request):
        chamadas.append(str(request.url))
        if falha and falha(str(request.url)):
            return httpx.Response(404)
        corpo = _j(fx, "received_SP-rs1-v4_AS64497.json")
        corpo["api"]["cache_status"]["cached_at"] = f"{dia}T12:00:00Z"
        return httpx.Response(200, json=corpo)
    r.get(url__regex=r".*/routes/received.*").mock(side_effect=resp)
    return r


def test_rodizio_cobre_todos_os_vizinhos_de_todos_os_ptts_em_tres_rodadas(base, fx, log, monkeypatch):
    monkeypatch.setattr(rotas, "PAUSA_S", 0)
    ptts = {"sp": 4, "rj": 3, "pa": 2}                                           # 9 vizinhos; orçamento de 3 por rodada: 3 rodadas, e nenhum PTT fica de fora
    lidos_por_rodada = []
    for dia in ("2026-09-20", "2026-09-21", "2026-09-22"):
        destino = _escreve_rodada(base, fx, dia, ptts)
        chamadas: list = []
        with _servidor(fx, chamadas, dia=dia):
            res = rotas.run(dia, base, log, dormir=lambda s: None, niveis=(3,), orcamento=3)
        lidos_por_rodada.append(set(chamadas))
        assert len(chamadas) == 3 and res["nivel3"]["consultados"] == 3
    todos = set().union(*lidos_por_rodada)
    assert len(todos) == 9 and sum(len(x) for x in lidos_por_rodada) == 9      # ninguém repetido antes de todos terem sido lidos
    d = read_json_gz(destino / "rs_communities.json.gz")
    assert d["ptts"] == ["todos"] and len(d["vizinhos"]) == 9
    tot = d["cobertura_rodizio"]["total"]
    assert tot == {"elegiveis": 9, "lidos_na_rodada": 3, "herdados": 6, "sem_leitura": 0, "idade_max_dias": 2, "pulados_lentos": 0}
    assert set(d["cobertura_rodizio"]["por_ptt"]) == {"sp", "rj", "pa"} and d["cobertura_rodizio"]["por_ptt"]["pa"]["elegiveis"] == 2
    assert sum(1 for v in d["vizinhos"] if v.get("herdado")) == 6
    assert d["cobertura"]["sp"]["elegiveis"] == 4                                 # o campo antigo continua igual (aditivo)


def test_quarta_rodada_volta_a_ler_o_mais_antigo(base, fx, log, monkeypatch):
    monkeypatch.setattr(rotas, "PAUSA_S", 0)
    ptts = {"sp": 2, "rj": 2}
    ordem = []
    for dia in ("2026-09-20", "2026-09-21", "2026-09-22"):
        _escreve_rodada(base, fx, dia, ptts)
        chamadas: list = []
        with _servidor(fx, chamadas):
            rotas.run(dia, base, log, dormir=lambda s: None, niveis=(3,), orcamento=2)
        ordem.append(chamadas)
    assert set(ordem[0]).isdisjoint(ordem[1]) and set(ordem[2]) == set(ordem[0])     # 4 vizinhos, 2 por rodada: a 3ª rodada recomeça pelos de 20/09


def test_vizinho_que_falha_vai_para_o_fim_da_fila_e_a_falha_e_publicada(base, fx, log, monkeypatch):
    monkeypatch.setattr(rotas, "PAUSA_S", 0)
    monkeypatch.setattr(rotas, "MAX_FALHA", 1.0)
    _escreve_rodada(base, fx, "2026-09-20", {"sp": 3})
    ruim = "AS64600_192_0_2_1"
    with _servidor(fx, [], falha=lambda u: ruim in u):
        res = rotas.run("2026-09-20", base, log, dormir=lambda s: None, niveis=(3,), orcamento=1)
    assert res["nivel3"]["falhas"] == 1 and res["nivel3"]["consultados"] == 0              # a primeira da fila falhou e gastou a requisição
    d = read_json_gz(base / "normalized" / "2026-09-20" / "summary" / "rs_communities.json.gz")
    assert [f["asn"] for f in d["falhas"]] == [64600] and d["cobertura_rodizio"]["total"]["sem_leitura"] == 3
    _escreve_rodada(base, fx, "2026-09-21", {"sp": 3})
    chamadas: list = []
    with _servidor(fx, chamadas, falha=lambda u: ruim in u):
        rotas.run("2026-09-21", base, log, dormir=lambda s: None, niveis=(3,), orcamento=1)
    assert ruim not in chamadas[0] and "AS64601" in chamadas[0]                        # quem nunca foi tentado passa na frente do que acabou de falhar


def test_cobertura_do_rodizio_conta_idade_maxima_dos_herdados(base, fx, log, monkeypatch):
    monkeypatch.setattr(rotas, "PAUSA_S", 0)
    destino = _escreve_rodada(base, fx, "2026-09-20", {"sp": 2})
    anterior = base / "normalized" / "2026-09-10" / "summary"
    anterior.mkdir(parents=True)
    base_v = {"rs": "SP-rs1-v4", "ixp": "sp", "afi": "v4", "total": 5, "comunidades": {}}
    write_json_gz(anterior / "rs_communities.json.gz", {"vizinhos": [{**base_v, "asn": 64600, "ip": "192.0.2.1", "coletado_em": "2026-09-08T00:00:00Z"}]})
    with _servidor(fx, []):
        rotas.run("2026-09-20", base, log, dormir=lambda s: None, niveis=(3,), orcamento=1)
    cob = read_json_gz(destino / "rs_communities.json.gz")["cobertura_rodizio"]["por_ptt"]["sp"]
    assert cob == {"elegiveis": 2, "lidos_na_rodada": 1, "herdados": 1, "sem_leitura": 0, "idade_max_dias": 12, "pulados_lentos": 0}


def test_route_server_com_falhas_seguidas_sai_da_rodada_e_a_coleta_falha_alto(base, fx, log, monkeypatch):
    monkeypatch.setattr(rotas, "PAUSA_S", 0)
    _escreve_rodada(base, fx, "2026-09-20", {"sp": 15})
    chamadas: list = []
    with _servidor(fx, chamadas, falha=lambda u: True):
        with pytest.raises(RuntimeError, match="vizinhos falharam"):
            rotas.run("2026-09-20", base, log, dormir=lambda s: None, niveis=(3,), orcamento=100)
    assert len(chamadas) == rotas.FALHAS_SEGUIDAS_POR_RS                                 # o route server sai na 5ª falha seguida; 404 não repete; os outros 10 ficam para outra rodada


def test_um_route_server_com_falhas_nao_para_os_outros_ptts(base, fx, log, monkeypatch):
    """Um route server com HTTP 500 em 10 vizinhos sai da rodada; a rodada não para nem deixa os PTTs seguintes sem leitura."""
    monkeypatch.setattr(rotas, "PAUSA_S", 0)
    destino = _escreve_rodada(base, fx, "2026-09-20", {"sp": 6, "rj": 40})
    chamadas: list = []
    with _servidor(fx, chamadas, falha=lambda u: "SP-rs1-v4" in u):
        rotas.run("2026-09-20", base, log, dormir=lambda s: None, niveis=(3,), orcamento=100)
    assert sum("SP-rs1-v4" in u for u in chamadas) == rotas.FALHAS_SEGUIDAS_POR_RS
    assert sum("RJ-rs1-v4" in u for u in chamadas) == 40                                  # o rj foi lido inteiro depois de o sp sair
    doc = read_json_gz(destino / "rs_communities.json.gz")
    assert [x["rs"] for x in doc["rs_pulados"]] == ["SP-rs1-v4"] and "falhas seguidas" in doc["rs_pulados"][0]["motivo"]
    assert doc["cobertura_rodizio"]["por_ptt"]["rj"]["sem_leitura"] == 0 and doc["cobertura_rodizio"]["por_ptt"]["sp"]["pulados_lentos"] == 6      # conta todo vizinho de route server tirado da rodada, por lentidão ou por falhas


def test_falhas_seguidas_em_route_servers_diferentes_param_a_rodada(base, fx, log, monkeypatch):
    """O Alice todo fora: 10 falhas seguidas espalhadas em vários route servers ainda interrompem a rodada."""
    monkeypatch.setattr(rotas, "PAUSA_S", 0)
    ptts = {p: 3 for p in ("sp", "rj", "ce", "df", "pr", "rs")}                          # 3 vizinhos por PTT: nenhum chega a 5 falhas seguidas
    _escreve_rodada(base, fx, "2026-09-20", ptts)
    chamadas: list = []
    with _servidor(fx, chamadas, falha=lambda u: True):
        with pytest.raises(RuntimeError, match="vizinhos falharam"):
            rotas.run("2026-09-20", base, log, dormir=lambda s: None, niveis=(3,), orcamento=100)
    assert len(chamadas) == rotas.FALHAS_SEGUIDAS_PARA_PARAR
