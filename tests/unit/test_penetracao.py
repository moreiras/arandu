# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Penetração e mercado não visto: valores plantados com resultado conhecido."""
import gzip
import json

from products.penetracao.build import calcular, publicar_penetracao


class _Log:
    def info(self, *a, **k): pass
    warning = info


IBGE = {
    "1": {"nome": "Alfa", "uf": "AA", "populacao": 3000, "populacao_estimada": 3300, "area_km2": 10.0, "domicilios": 1000},
    "2": {"nome": "Beta", "uf": "AA", "populacao": 600, "populacao_estimada": 640, "domicilios": 200},
    "3": {"nome": "Gama", "uf": "BB", "populacao": 900},                       # sem domicílios (SIDRA "...")
    "4": {"nome": "Delta", "uf": "BB", "populacao": 900, "domicilios": 300},   # sem declaração no SICI
    "5": {"nome": "Epsilon", "uf": "AA", "populacao_estimada": 500},           # criado depois do Censo: só a estimativa
}
TAXAS = {"AA": {"taxa": 0.9, "cv_domicilios_pct": 0.8, "domicilios_mil_por_ano": {"2022": 100.0, "2025": 110.0}},      # domicílios da UF cresceram 10%
         "BB": {"taxa": 0.5, "domicilios_mil_por_ano": {"2022": 200.0, "2025": 200.0}}}
SICI = {"1": {"acessos": 700, "pf": 600, "pj": 100}, "2": {"acessos": 400, "pf": 300, "pj": 100}, "3": {"acessos": 50, "pf": 50, "pj": 0}}


def test_domicilios_projetados_pela_uf_e_penetracao_sobre_eles():
    m = calcular(IBGE, TAXAS, SICI)["municipios"]
    assert m["1"]["domicilios"] == 1000 and m["1"]["domicilios_projetados"] == 1100 and m["1"]["fator_projecao_uf"] == 1.1
    assert m["1"]["penetracao"] == round(700 / 1100, 4) and m["1"]["penetracao_pf"] == round(600 / 1100, 4)
    assert m["1"]["penetracao_censo"] == 0.7                                  # a razão contra o Censo continua exposta
    assert m["4"]["domicilios_projetados"] == 300 and m["4"]["fator_projecao_uf"] == 1.0
    assert m["1"]["populacao_estimada"] == 3300


def test_nao_visto_usa_domicilios_projetados_e_nunca_fica_negativo():
    m = calcular(IBGE, TAXAS, SICI)["municipios"]
    assert m["1"]["domicilios_com_internet_est"] == 990 and m["1"]["nao_visto"] == 390 and m["1"]["nao_visto_pct"] == round(390 / 1100, 4)
    assert m["2"]["penetracao"] == round(400 / 220, 4)                         # acesso não é domicílio: pode passar de 1
    assert m["2"]["nao_visto"] == 0                                           # 220 × 0,9 − 300 < 0 → zero, nunca negativo
    assert "penetracao" not in m["3"] and "nao_visto" not in m["3"]           # sem domicílios, sem razão inventada
    assert m["4"]["sem_declaracao_sici"] is True and m["4"]["acessos"] == 0 and m["4"]["penetracao"] == 0.0
    assert m["4"]["nao_visto"] == 150                                         # 300 × 0,5 − 0


def test_municipio_criado_depois_do_censo_tem_so_populacao_estimada():
    m = calcular(IBGE, TAXAS, SICI)["municipios"]["5"]
    assert m["populacao_estimada"] == 500 and "domicilios" not in m and "penetracao" not in m and "nao_visto" not in m


def test_sem_serie_da_pnad_fica_no_nivel_do_censo_e_sem_fator():
    m = calcular(IBGE, {"AA": {"taxa": 0.9}, "BB": {"taxa": 0.5}}, SICI)["municipios"]["1"]
    assert m["domicilios_projetados"] == 1000 and "fator_projecao_uf" not in m


def test_uf_e_pais_somam_os_municipios_e_nao_visto_usa_a_taxa_da_uf():
    r = calcular(IBGE, TAXAS, SICI)
    aa = r["ufs"]["AA"]
    assert aa["municipios"] == 3 and aa["domicilios"] == 1200 and aa["domicilios_projetados"] == 1320 and aa["acessos"] == 1100 and aa["acessos_pf"] == 900
    assert aa["populacao_estimada"] == 3300 + 640 + 500
    assert aa["nao_visto"] == round(1320 * 0.9 - 900) == 288                  # no nível da UF, não a soma dos municípios (390 + 0)
    assert aa["cv_domicilios_pnad_pct"] == 0.8 and aa["taxa_internet_pnad"] == 0.9 and aa["fator_projecao_uf"] == 1.1
    b = r["brasil"]
    assert b["municipios"] == 5 and b["populacao"] == 5400 and b["acessos"] == 1150
    assert b["nao_visto"] == aa["nao_visto"] + r["ufs"]["BB"]["nao_visto"]


def _gz(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(obj, f)


def test_publicar_grava_casamento_e_municipio_do_sici_sem_codigo_no_ibge(tmp_path):
    d = "2026-10-11"
    _gz(tmp_path / "normalized" / d / "summary" / "ibge_municipios.json.gz", {"censo_ano": "2022", "estimativa_ano": "2026", "municipios": IBGE})
    _gz(tmp_path / "normalized" / d / "summary" / "ibge_taxa_internet.json.gz", {"pnad_ano": "2025", "ufs": TAXAS})
    _gz(tmp_path / "published" / d / "sici_municipios.json.gz", {"mes_referencia": "2026-08", "municipios": {**SICI, "9": {"acessos": 10, "pf": 10, "pj": 0}}})
    assert publicar_penetracao(tmp_path, d, _Log()) == {"municipios": 5, "casados": 3, "sem_codigo_no_ibge": 1}
    out = json.loads(gzip.open(tmp_path / "published" / d / "territorio" / "municipios.json.gz").read())
    assert out["casamento"] == {"sici_municipios": 4, "casados_com_ibge": 3, "sem_codigo_no_ibge": ["9"], "ibge_municipios": 5}
    assert out["censo_ano"] == "2022" and out["estimativa_ano"] == "2026" and out["pnad_ano"] == "2025" and out["ano_projecao_domicilios"] == "2025"
    assert "celular" in out["limites"] and "projetados" in out["limites"]


def test_sem_ibge_nao_grava(tmp_path):
    _gz(tmp_path / "published" / "2026-10-11" / "sici_municipios.json.gz", {"mes_referencia": "2026-08", "municipios": SICI})
    assert publicar_penetracao(tmp_path, "2026-10-11", _Log()) == {}
    assert not (tmp_path / "published" / "2026-10-11" / "territorio").exists()


class _LojaFalsa:
    def __init__(self, doc):
        self._doc = doc

    def territorio_doc(self, date_str):
        return self._doc


def test_centroides_vem_de_config_na_raiz_do_repositorio():
    """O caminho do config é o da raiz (não api/config): sem ele, todo município ficaria sem distância ao PTT."""
    from api.services.perfis import PerfisService

    s = PerfisService(_LojaFalsa({}))
    lon, lat = s.municipio_centroide("3550308")                     # São Paulo
    assert -47 < lon < -46 and -24 < lat < -23


def test_territorio_linhas_traz_ptt_proximo_e_marca_quem_esta_a_mais_de_100_km():
    from api.services.perfis import PerfisService

    doc = {"municipios": {"3550308": {"nome": "São Paulo", "uf": "SP", "domicilios": 10}, "1100015": {"nome": "Alta Floresta D'Oeste", "uf": "RO", "domicilios": 5}}}
    serv = PerfisService(_LojaFalsa(doc))
    serv.ptt_mais_proximo = lambda d, lon, lat: {"codigo": "sp", "km": 0.0 if abs(lat + 23.55) < 0.5 else 250.0}      # type: ignore[method-assign]
    linhas = {x["ibge"]: x for x in serv.territorio_linhas("2026-10-31")}
    assert linhas["3550308"]["km_ptt"] == 0.0 and linhas["3550308"]["sem_ptt_proximo"] is False
    assert linhas["1100015"]["km_ptt"] == 250.0 and linhas["1100015"]["sem_ptt_proximo"] is True and linhas["1100015"]["ptt_proximo"] == "sp"


def test_territorio_linhas_traz_o_nome_do_pix_mais_proximo_alem_do_ptt():
    """PT-25 / municipios 5.3: o PTT sozinho esconde que o ponto mais próximo é o PIX de outra cidade (Monte Carlo/SC aponta para Nova Prata)."""
    from api.services.perfis import PerfisService

    doc = {"municipios": {"3550308": {"nome": "São Paulo", "uf": "SP", "domicilios": 10}}}
    serv = PerfisService(_LojaFalsa(doc))
    serv.ptt_mais_proximo = lambda d, lon, lat: {"codigo": "rs", "nome": "Porto Alegre", "pix": "[PIX ADYLNET]", "km": 191.0}      # type: ignore[method-assign]
    ln = serv.territorio_linhas("2026-10-31")[0]
    assert (ln["ptt_proximo"], ln["ptt_proximo_nome"], ln["pix_proximo"]) == ("rs", "Porto Alegre", "[PIX ADYLNET]")


def test_territorio_linhas_traz_redes_com_sede_e_a_interligacao_delas():
    """PT-25 / municipios 5.3: a distância ao PIX não diz se as redes do município já estão interligadas; sem o produto `regiao`, o campo não existe (não vira zero)."""
    from api.services.perfis import PerfisService

    class Loja(_LojaFalsa):
        def regiao_doc(self, date_str):
            return {"asns": {"1": {"d": ["sp"], "o": ["sp"]}, "2": {"d": [], "o": ["sp"]}, "3": {"d": [], "o": []}}, "municipios": {"3550308": {"h": [1, 2, 3]}}}

    doc = {"municipios": {"3550308": {"nome": "São Paulo", "uf": "SP", "domicilios": 10}, "1100015": {"nome": "Alta Floresta D'Oeste", "uf": "RO", "domicilios": 5}}}
    com, sem = PerfisService(Loja(doc)), PerfisService(_LojaFalsa(doc))
    for serv in (com, sem):
        serv.ptt_mais_proximo = lambda d, lon, lat: {"codigo": "sp", "km": 1.0}      # type: ignore[method-assign]
    linhas = {x["ibge"]: x for x in com.territorio_linhas("2026-10-31")}
    assert linhas["3550308"]["redes_sede"] == {"asns": 3, "sessao_ptt": 1, "rotas_ptt": 2}
    assert linhas["1100015"]["redes_sede"] == {"asns": 0, "sessao_ptt": 0, "rotas_ptt": 0}
    assert all("redes_sede" not in x for x in sem.territorio_linhas("2026-10-31"))


def test_todo_ptt_do_pix_yaml_tem_ao_menos_um_pix_com_coordenada():
    """PT-25 / MAPA-E1: PTT sem nenhum PIX com lat/lon some do mapa e da distância municipal (Foz do Iguaçu apontava para `cac` por falta de `igu`)."""
    import yaml
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[2]
    pix = (yaml.safe_load((raiz / "config" / "pix.yaml").read_text(encoding="utf-8")) or {}).get("pix") or {}
    sem = sorted(c for c, es in pix.items() if not any(e.get("lat") is not None and e.get("lon") is not None for e in (es or [])))
    assert pix and not sem, f"PTT sem nenhum PIX com coordenada: {sem}"


def test_pix_config_vem_de_config_na_raiz_do_repositorio():
    """Sem pix.yaml (mesmo caminho dos centróides) nenhum PTT teria coordenadas e a distância ao PTT mais próximo não existiria."""
    from api.services.geolocalizacao import GeolocalizacaoService

    pix = GeolocalizacaoService(_LojaFalsa({})).pix_config()
    assert "sp" in pix and pix["sp"][0]["lat"] < -20
