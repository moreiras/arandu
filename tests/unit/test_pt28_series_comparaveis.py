# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""PT-28: a regra de comparabilidade aplicada a `/snapshots/diff`, `/history` (tendência), `/changes/summary` e `/history/brasil/series`."""
from __future__ import annotations

import gzip
import json

import pytest

from api.services import historico as h
from api.services import series_nacionais as sn


class _Repo:
    """Histórico mínimo: UFs, PTTs e eventos por data."""

    def __init__(self, datas, ufs=None, ixps=None, eventos=None, asns=None):
        self._d, self._ufs, self._ixps, self._ev, self._asns = datas, ufs or {}, ixps or {}, eventos or {}, asns or {}

    def datas(self):
        return list(self._d)

    def entradas(self):
        return {d: {} for d in self._d}

    def linhas_uf(self, d):
        return self._ufs.get(d, [])

    def linhas_ixp(self, d):
        return self._ixps.get(d, [])

    def eventos(self, d):
        return self._ev.get(d, [])

    def linha_asn(self, d, asn):
        return self._asns.get((d, asn))

    def linha_ixp(self, d, code):
        return next((i for i in self._ixps.get(d, []) if i["ixp"] == code), None)


def _uf(users, v6, roa=0):
    return [{"uf": "SP", "n_asns": 1, "users": users, "v6users": v6, "p4": 1, "p6": 1, "n_roa": roa, "rpki_valid": 0, "rpki_invalid": 0, "rpki_not_found": 0}]


def test_diff_razao_ipv6_em_pontos_percentuais_na_mesma_base():
    repo = _Repo(["2026-11-15", "2026-11-22"], ufs={"2026-11-15": _uf(1000, 602), "2026-11-22": _uf(1010, 611)})
    r = h.diferenca(repo, "2026-11-15", "2026-11-22")
    z = r["razoes"]["ipv6_pct_usuarios"]
    assert (z["a"], z["b"], z["comparavel"]) == (60.2, 60.5, True) and z["variacao_pp"] == 0.3
    assert r["totais"]["users"]["variacao"] == 10 and r["totais"]["users"]["comparavel"] is True
    assert "texto" in r["comparabilidade"] and r["comparabilidade"]["avisos"] == []


def test_diff_total_de_ptts_nao_compara_quando_a_coleta_mudou():
    ixps_a = [{"ixp": "sp", "status": "ok", "n_membros": 10}, {"ixp": "rj", "status": "ok", "n_membros": 5}, {"ixp": "ce", "status": "ok", "n_membros": 5}, {"ixp": "pe", "status": "ok", "n_membros": 5}]
    ixps_b = [{"ixp": "sp", "status": "ok", "n_membros": 11}, {"ixp": "rj", "status": "missing"}, {"ixp": "ce", "status": "missing"}, {"ixp": "pe", "status": "missing"}]
    repo = _Repo(["2026-11-15", "2026-11-22"], ufs={"2026-11-15": _uf(1, 1), "2026-11-22": _uf(1, 1)}, ixps={"2026-11-15": ixps_a, "2026-11-22": ixps_b})
    t = h.diferenca(repo, "2026-11-15", "2026-11-22")["totais"]
    assert t["ptts_membros"]["comparavel"] is False and t["ptts_membros"]["variacao"] is None
    assert t["ptts_membros"]["motivos"][0]["codigo"] == "cobertura_mudou"
    assert t["ptts_coletados"]["variacao"] == -3                      # a própria cobertura é dado, com variação
    assert t["users"]["comparavel"] is True                           # o que não depende dos PTTs continua comparável


def test_diff_avisa_semanas_sem_snapshot():
    repo = _Repo(["2026-07-05", "2026-07-26"], ufs={"2026-07-05": _uf(1, 1), "2026-07-26": _uf(1, 1)})
    r = h.diferenca(repo, "2026-07-05", "2026-07-26")
    assert [a["codigo"] for a in r["comparabilidade"]["avisos"]] == ["lacuna"]


def test_diff_marca_eventos_da_data_atipica_sem_apagar_a_contagem():
    ev = {"2026-07-05": [{"data": "2026-07-05", "tipo": "roa_perdido", "estado": "confirmado", "entidade": "asn:1", "chave": "", "asn": 1},
                         {"data": "2026-07-05", "tipo": "asn_novo", "estado": "confirmado", "entidade": "asn:2", "chave": "", "asn": 2}]}
    repo = _Repo(["2026-06-28", "2026-07-05"], ufs={"2026-06-28": _uf(1, 1), "2026-07-05": _uf(1, 1)}, eventos=ev)
    e = h.diferenca(repo, "2026-06-28", "2026-07-05")["eventos"]
    assert e["por_tipo"]["roa_perdido"]["confirmado"] == 1               # o evento fica
    assert list(e["datas_atipicas"]) == ["roa_perdido"] and e["datas_atipicas"]["roa_perdido"]["datas"] == ["2026-07-05"]


def test_resumo_de_mudancas_marca_a_data_atipica_so_nos_tipos_afetados():
    ev = [{"data": "2026-07-05", "tipo": "roa_perdido", "estado": "confirmado", "entidade": "asn:1", "chave": "", "asn": 1},
          {"data": "2026-07-05", "tipo": "asn_novo", "estado": "confirmado", "entidade": "asn:2", "chave": "", "asn": 2},
          {"data": "2026-07-12", "tipo": "roa_perdido", "estado": "confirmado", "entidade": "asn:3", "chave": "", "asn": 3}]
    repo = _Repo(["2026-07-05", "2026-07-12"], eventos={d: [e for e in ev if e["data"] == d] for d in ("2026-07-05", "2026-07-12")})
    r = h.mudancas_resumo(repo)
    assert list(r["datas_atipicas"]) == ["2026-07-05"] and r["datas_atipicas"]["2026-07-05"]["tipos"] == ["roa_perdido"]
    assert r["por_data"]["2026-07-05"] == 2                                 # a contagem não é alterada
    sem = h.mudancas_resumo(repo, "2026-07-12")
    assert "datas_atipicas" not in sem


def test_tendencia_de_asn_estrangeiro_nao_atravessa_a_data_atipica():
    asns = {("2026-06-21", 7): {"is_br": False, "n_roa": 5}, ("2026-06-28", 7): {"is_br": False, "n_roa": 5},
            ("2026-07-05", 7): {"is_br": False, "n_roa": 0}, ("2026-07-12", 7): {"is_br": False, "n_roa": 0}}
    repo = _Repo(["2026-06-21", "2026-06-28", "2026-07-05", "2026-07-12"], asns=asns)
    t = h.tendencia(repo, "asn:7", "n_roa")
    assert [p["comparavel_com_anterior"] for p in t["serie"]] == [None, True, False, False]
    assert "data_atipica" in t["serie"][2]["motivos"]
    assert t["variacao"]["calculada"] is False and t["variacao"]["absoluta"] is None
    assert "2026-07-05" in t["nota"]


def test_tendencia_de_asn_brasileiro_na_mesma_data_continua_comparavel():
    asns = {(d, 7): {"is_br": True, "n_roa": n} for d, n in (("2026-06-28", 5), ("2026-07-05", 6))}
    t = h.tendencia(_Repo(["2026-06-28", "2026-07-05"], asns=asns), "asn:7", "n_roa")
    assert t["variacao"]["calculada"] is True and t["variacao"]["absoluta"] == 1 and "nota" not in t


def test_tendencia_de_ptt_com_coleta_parcial_nao_compara():
    ixps = {"2026-11-15": [{"ixp": "sp", "status": "ok", "n_direct": 100}], "2026-11-22": [{"ixp": "sp", "status": "partial", "n_direct": 40}]}
    t = h.tendencia(_Repo(["2026-11-15", "2026-11-22"], ixps=ixps), "ixp:sp", "n_direct")
    assert t["variacao"]["calculada"] is False and t["serie"][1]["motivos"] == ["cobertura_mudou"]


# ── séries nacionais ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
class _Store:
    def __init__(self, base, datas):
        self.base, self._datas = base, datas

    def list_snapshots(self):
        return list(self._datas)

    def _pub(self, d):
        return self.base / "published" / d


def _grava(store, data, rel, doc):
    p = store._pub(data) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(gzip.compress(json.dumps(doc).encode()) if rel.endswith(".gz") else json.dumps(doc).encode())


def _resumo(valido_v6, definicao="P_BR regra 1", vrps=1000):
    est = lambda v: {"rotas": 100, "valid": v, "invalid": 1, "not_found": 100 - v - 1, "pct": {"valid": float(v), "invalid": 1.0, "not_found": float(99 - v)}}
    return {"definicao": definicao, "vrps": vrps, "rotas_br": {"v6": {"pbr_routes": 100, "br_origin_asns": 10}, "v4": {"pbr_routes": 200, "br_origin_asns": 20}},
            "rpki": {"v6": est(valido_v6), "v4": est(50)}}


@pytest.fixture(autouse=True)
def _limpa_cache():
    sn._PONTOS.clear()
    yield
    sn._PONTOS.clear()


def test_serie_de_roteamento_corta_na_mudanca_da_definicao_de_rota_brasileira(tmp_path):
    datas = ["2026-11-01", "2026-11-08", "2026-11-15", "2026-11-22"]
    st = _Store(tmp_path, datas)
    for d, v, defin in zip(datas, (50, 52, 60, 62), ("regra 1", "regra 1", "regra 2", "regra 2")):
        _grava(st, d, "routing_analysis_resumo.json", _resumo(v, defin))
    r = sn.serie(st, "roteamento")
    m = {x["id"]: x for x in r["metricas"]}
    v6 = m["rpki_valido_pct_v6"]
    assert [p["comparavel_com_anterior"] for p in v6["pontos"]] == [None, True, False, True]
    assert v6["pontos"][2]["motivos"] == ["metodo_mudou"] and v6["desenhar_linha"] is False
    assert v6["variacao"]["de"] == "2026-11-15" and v6["variacao"]["absoluta"] == 2 and v6["variacao"]["unidade"] == "pp"
    assert "2026-11-15" in v6["nota"]
    assert (v6["selo"], "RFC 6811" in v6["fonte"]) == ("fato", True) and r["regra"]["versao"]
    assert list(m)[0].endswith("_v6") and list(m)[4].endswith("_v4")                       # IPv6 antes de IPv4


def test_serie_de_roteamento_com_4_pontos_comparaveis_desenha_linha(tmp_path):
    datas = ["2026-11-01", "2026-11-08", "2026-11-15", "2026-11-22"]
    st = _Store(tmp_path, datas)
    for d, v in zip(datas, (50, 52, 53, 55)):
        _grava(st, d, "routing_analysis_resumo.json", _resumo(v))
    v6 = {x["id"]: x for x in sn.serie(st, "roteamento")["metricas"]}["rpki_valido_pct_v6"]
    assert v6["desenhar_linha"] is True and v6["variacao"]["absoluta"] == 5 and "nota" not in v6


def test_snapshot_sem_resumo_vira_lacuna_e_nao_zero(tmp_path):
    datas = ["2026-11-08", "2026-11-15", "2026-11-22"]
    st = _Store(tmp_path, datas)
    _grava(st, "2026-11-08", "routing_analysis_resumo.json", _resumo(50))
    _grava(st, "2026-11-22", "routing_analysis_resumo.json", _resumo(55))
    p = {x["id"]: x for x in sn.serie(st, "roteamento")["metricas"]}["rpki_valido_pct_v6"]["pontos"]
    assert p[1]["valor"] is None and p[1]["motivos"] == ["ausente"] and p[2]["motivos"] == ["ausente"]


def _prontidao(regras_hash, filtragem, pronto=40, total=100):
    return {"regras": {"hash": regras_hash}, "fontes": {"spoofer": {"janela": "2026"}, "irr": {"serial": {"x": 1}}},
            "brasil": {"asns": total, "classes": {"pronto": pronto}, "media_ponderada_usuarios": 55.5,
                       "cobertura_pilares": {"filtragem": filtragem, "anti_spoofing": 500, "coordenacao": 900, "validacao_global": 900}}}


def _seguranca(rov_asns, rov=70.0):
    return {"fontes": {"rov": {"as_of": "2026-11-20"}, "dnssec": {"as_of": "2026-11-21"}},
            "brasil": {"rov": {"asns": rov_asns, "media_ponderada_pct": rov, "mediana_pct": 10.0}, "dnssec": {"asns": 3000, "media_ponderada_pct": 33.0}}}


def test_serie_de_seguranca_nao_compara_quando_a_cobertura_de_filtragem_triplica(tmp_path):
    datas = ["2026-11-15", "2026-11-22"]
    st = _Store(tmp_path, datas)
    for d, cob, pronto in (("2026-11-15", 1407, 70), ("2026-11-22", 4144, 40)):
        _grava(st, d, "prontidao/asns.json.gz", _prontidao("abc", cob, pronto))
        _grava(st, d, "seguranca/asns.json.gz", _seguranca(cob))
    r = sn.serie(st, "seguranca")
    m = {x["id"]: x for x in r["metricas"]}
    pronto = m["prontidao_pronto_pct"]
    assert pronto["pontos"][1]["comparavel_com_anterior"] is False and "cobertura_mudou" in pronto["pontos"][1]["motivos"]
    assert pronto["variacao"]["calculada"] is False and pronto["variacao"]["absoluta"] is None and pronto["selo"] == "inferido"
    assert "1407 para 4144" in pronto["nota"]
    assert m["rov_media_ponderada_pct"]["pontos"][1]["comparavel_com_anterior"] is False      # cobertura do próprio ROV mudou
    assert m["dnssec_media_ponderada_pct"]["pontos"][1]["comparavel_com_anterior"] is True      # DNSSEC manteve 3000 ASNs medidos
    assert m["dnssec_media_ponderada_pct"]["pontos"][1]["meta"]["as_of"] == "2026-11-21" and m["rov_media_ponderada_pct"]["selo"] == "estimado"


def test_serie_de_seguranca_corta_quando_o_hash_das_regras_muda(tmp_path):
    datas = ["2026-11-15", "2026-11-22"]
    st = _Store(tmp_path, datas)
    for d, hh in zip(datas, ("aaa", "bbb")):
        _grava(st, d, "prontidao/asns.json.gz", _prontidao(hh, 4000))
    p = {x["id"]: x for x in sn.serie(st, "seguranca")["metricas"]}["prontidao_indice"]["pontos"]
    assert p[1]["motivos"] == ["metodo_mudou"]


def test_serie_valida_parametros(tmp_path):
    st = _Store(tmp_path, ["2026-11-22"])
    with pytest.raises(sn.SerieErro) as e:
        sn.serie(st, "mercado")
    assert e.value.status == 400
    with pytest.raises(sn.SerieErro) as e:
        sn.serie(st, "roteamento", de="ontem")
    assert e.value.status == 400
    with pytest.raises(sn.SerieErro) as e:
        sn.serie(st, "roteamento", de="2027-01-01")
    assert e.value.status == 404


# ── bloco `historico` dos perfis (Linha do tempo): a mesma regra, por coluna ─────────────────────────────────────────────────────────
class _RepoPerfil(_Repo):
    def eventos_de(self, tipo, chave):
        return [e for d in self._d for e in self._ev.get(d, []) if e.get("entidade", "").startswith(f"{tipo}:")]


def _metrica(bloco, mid):
    return next(m for m in bloco["metricas"] if m["id"] == mid)


def test_perfil_de_asn_estrangeiro_marca_o_corte_na_data_atipica_e_nao_calcula_a_variacao():
    datas = ["2026-06-21", "2026-06-28", "2026-07-05", "2026-07-12"]
    asns = {(d, 7): {"is_br": False, "n_roa": n, "p4": 3} for d, n in zip(datas, (5, 5, 0, 0))}
    b = h.perfil(_RepoPerfil(datas, asns=asns), "asn", "7", True, datas[-2:])
    roa = _metrica(b, "n_roa")
    assert [p["comparavel_com_anterior"] for p in roa["pontos"]] == [None, True, False, False]
    assert roa["variacao"]["calculada"] is False and roa["variacao"]["absoluta"] is None and "2026-07-05" in roa["nota"]
    assert _metrica(b, "p4")["variacao"]["calculada"] is True            # a data atípica só vale para as métricas marcadas
    assert b["regra"]["min_pontos_linha"] == 4 and b["regra"]["texto"]


def test_perfil_de_asn_brasileiro_na_mesma_data_continua_comparavel_e_so_desenha_linha_com_4_pontos():
    datas = ["2026-06-21", "2026-06-28", "2026-07-05", "2026-07-12"]
    asns = {(d, 7): {"is_br": True, "n_roa": n} for d, n in zip(datas, (5, 6, 7, 8))}
    b = h.perfil(_RepoPerfil(datas, asns=asns), "asn", "7", True, datas[-2:])
    assert _metrica(b, "n_roa")["desenhar_linha"] is True and _metrica(b, "n_roa")["variacao"]["absoluta"] == 3
    curto = h.perfil(_RepoPerfil(datas, asns=asns), "asn", "7", False, datas[-2:])           # anônimo: 2 snapshots
    assert _metrica(curto, "n_roa")["desenhar_linha"] is False and len(curto["serie"]) == 2
    assert _metrica(curto, "n_roa")["variacao"]["calculada"] is True


def test_perfil_de_ptt_com_coleta_parcial_nao_compara_e_status_nao_vira_metrica():
    datas = ["2026-11-15", "2026-11-22"]
    ixps = {datas[0]: [{"ixp": "sp", "status": "ok", "n_direct": 100}], datas[1]: [{"ixp": "sp", "status": "partial", "n_direct": 40}]}
    b = h.perfil(_RepoPerfil(datas, ixps=ixps), "ixp", "sp", True, datas)
    assert _metrica(b, "n_direct")["variacao"]["calculada"] is False
    assert "status" not in [m["id"] for m in b["metricas"]]


def test_perfil_marca_o_evento_de_data_atipica_sem_apagar_o_evento():
    datas = ["2026-06-28", "2026-07-05"]
    ev = {"2026-07-05": [{"data": "2026-07-05", "tipo": "roa_perdido", "entidade": "asn:7", "chave": "", "estado": "confirmado", "asn": 7}]}
    asns = {(d, 7): {"is_br": False, "n_roa": 1} for d in datas}
    b = h.perfil(_RepoPerfil(datas, asns=asns, eventos=ev), "asn", "7", True, datas)
    assert b["eventos_total"] == 1 and b["eventos"][0]["atipico"]
