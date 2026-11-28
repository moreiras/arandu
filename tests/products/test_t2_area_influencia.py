# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T2 — área de influência dos PTTs: invariantes do artefato publicado sobre o dataset sintético (contas fecham com o SICI, percentis, PIX aproximado, privacidade)."""
import gzip
import json

from tests.synth.world import T1

ARQUIVO = "territorio/area_influencia_ptt.json.gz"


def _doc(base):
    return json.loads(gzip.open(base / "published" / T1 / ARQUIVO, "rt", encoding="utf-8").read())


def _sici(base):
    return json.loads(gzip.open(base / "published" / T1 / "sici_municipios.json.gz", "rt", encoding="utf-8").read())["municipios"]


def test_contas_fecham_com_o_sici_e_cada_acesso_conta_uma_vez(pipeline):
    base, _ = pipeline
    d, sici = _doc(base), _sici(base)
    total_sici = sum(op["acessos"] for m in sici.values() for op in m["operadores"])
    for v in ("diretos", "todos"):
        t = d["totais"][v]
        assert t["acessos"] == total_sici
        assert t["acessos_atribuidos"] + t["acessos_sem_ptt"] + t["acessos_sem_centroide"] == t["acessos"]
        assert sum((p["visoes"][v] or {}).get("acessos", 0) for p in d["ptts"].values()) == t["acessos_atribuidos"]       # nenhum acesso em dobro
        assert sum(x[3] for x in d["municipios"][v].values()) == t["acessos_atribuidos"]
        for ibge, (principal, faixa, ac_principal, ac_mun, n) in d["municipios"][v].items():
            assert faixa in (1, 2, 3) and ac_principal <= ac_mun and 1 <= n <= len(d["ptts"])
            assert d["ptts"][principal]["visoes"][v]["municipios_faixa"][ibge] == [ac_principal, faixa]
    assert d["totais"]["todos"]["cnpjs_com_varios_asns"] >= 1                            # cenário 3: um CNPJ com dois ASNs


def test_percentis_em_ordem_e_faixas_somam_o_ptt(pipeline):
    base, _ = pipeline
    for code, p in _doc(base)["ptts"].items():
        for v, r in p["visoes"].items():
            if not r:
                continue
            assert 0 <= r["p50_km"] <= r["p80_km"] <= r["p90_km"] and r["mediana_operadora_km"] >= 0
            assert sum(f["municipios"] for f in r["faixas"].values()) == r["municipios"] == len(r["municipios_faixa"])
            assert sum(f["acessos"] for f in r["faixas"].values()) == r["acessos"]
            assert {f for _, f in r["municipios_faixa"].values()} <= {1, 2, 3}


def test_diretos_nunca_enxerga_mais_do_que_todos_e_os_pix_aproximados_ficam_registrados(pipeline):
    base, _ = pipeline
    d = _doc(base)
    assert d["ptts_com_pix_aproximado"] == ["zb", "zc"]                                   # zb com um PIX sem endereço (sede), zc só com endereço
    assert d["ptts"]["za"]["pix"]["aproximado"] is False and d["ptts"]["za"]["pix"]["coordenada"] == 1
    assert d["ptts"]["zb"]["pix"]["sede"] == 1 and d["ptts"]["zb"]["pix"]["coordenada"] == 1
    assert d["ptts"]["zc"]["pix"]["endereco"] == 1 and d["ptts"]["zc"]["pix"]["pontos"][0][:2] == [-24.95, -53.45]     # centroide de Mbaracayú Novo
    ops = lambda v: sum((p["visoes"][v] or {}).get("operadoras", 0) for p in d["ptts"].values())
    assert d["totais"]["diretos"]["acessos_atribuidos"] <= d["totais"]["todos"]["acessos_atribuidos"]
    assert ops("diretos") > 0 and ops("todos") > 0


def test_artefato_nao_traz_cnpj_nem_nome_de_operadora(pipeline):
    base, _ = pipeline
    texto = gzip.open(base / "published" / T1 / ARQUIVO, "rt", encoding="utf-8").read()
    sici = _sici(base)
    assert not any(op["cnpj"] in texto or (op["empresa"] and op["empresa"] in texto) for m in sici.values() for op in m["operadores"])
    assert '"cnpj"' not in texto and '"empresa"' not in texto and '"asns"' not in texto
