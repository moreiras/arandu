# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Segurança de roteamento A: valores plantados com resultado conhecido."""
import gzip
import json

from products.seguranca.build import Intervalos, calcular, faixa_acessos_sici, faixa_porte, publicar_seguranca, prefixos_em_bogon, asn_reservado


class _Log:
    def info(self, *a, **k): pass
    warning = info


def test_intervalos_contem_prefixo_inteiro_e_funde_blocos_vizinhos():
    iv = Intervalos(["10.0.0.0/9", "10.128.0.0/9", "192.0.2.0/24"])
    assert iv.contem("10.1.2.0/24") and iv.contem("10.0.0.0/8") and iv.contem("192.0.2.128/25")     # 10/8 vem de duas metades vizinhas
    assert not iv.contem("11.0.0.0/24") and not iv.contem("192.0.0.0/22")                           # o bloco maior que o bogon não é bogon
    assert Intervalos(["2001:db8::/32"]).contem("2001:db8:1::/48")


def test_prefixos_em_bogon_marca_a_lista_e_ignora_o_resto():
    listas = {"iana": {4: Intervalos(["100.64.0.0/10"]), 6: Intervalos([])}, "cymru": {4: Intervalos(["5.0.0.0/16"]), 6: Intervalos(["::/10"])}}
    r = prefixos_em_bogon(["100.80.0.0/18", "5.0.1.0/24", "8.8.8.0/24", "::/16"], listas)
    assert r == [{"prefixo": "100.80.0.0/18", "lista": "iana"}, {"prefixo": "5.0.1.0/24", "lista": "cymru"}, {"prefixo": "::/16", "lista": "cymru"}]


def test_asn_reservado_e_faixas_de_porte():
    faixas = [{"inicio": 64496, "fim": 64511, "motivo": "doc"}, {"inicio": 0, "fim": 0, "motivo": "zero"}]
    assert asn_reservado(64500, faixas) == "doc" and asn_reservado(0, faixas) == "zero" and asn_reservado(28573, faixas) is None
    assert [faixa_acessos_sici(x) for x in (None, 0, 500, 1000, 5000, 100000, 100001)] == ["sem_acessos", "sem_acessos", "ate_1000", "ate_1000", "de_1000_a_10000", "de_10000_a_100000", "acima_de_100000"]
    assert [faixa_porte(x) for x in (None, 0, 500, 1000, 5000, 100000, 100001, 1000000, 1000001)] == ["sem_usuarios", "sem_usuarios", "ate_1000", "ate_1000", "de_1000_a_10000", "de_10000_a_100000", "de_100000_a_1000000", "de_100000_a_1000000", "acima_de_1000000"]


IROV = {"asns": {"1": {"validates_pct": 0.5, "amostras": 500}, "2": {"validates_pct": 95.0, "amostras": 300}, "3": {"validates_pct": 50.0, "amostras": 10},
                 "4": {"validates_pct": 0.0, "amostras": 1000}}}
DNSSEC = {"asns": {"1": {"validates_pct": 90.0, "parcial_pct": 2.0, "amostras": 200}, "2": {"validates_pct": 20.0, "parcial_pct": 1.0, "amostras": 150}}}
ASRANK = {"asns": {"1": {"rank": 10, "clique": True, "cone": {"asns": 5}}, "9": {"rank": 99}}}
BOGONS = {"iana": {"v4": [{"bloco": "10.0.0.0/8"}], "v6": [], "asns": [{"inicio": 64496, "fim": 64511, "motivo": "doc"}]}, "cymru": {"as_of": "2026-10-31", "v4": [], "v6": []}}
DOCS = {1: {"uf": "SP", "cnpj": "A", "prefixos": ["10.1.0.0/16", "200.1.0.0/16"], "usuarios": 500}, 2: {"uf": "SP", "cnpj": "B", "prefixos": [], "usuarios": 50000}, 3: {"uf": "RJ", "cnpj": "C", "prefixos": [], "usuarios": 0},
        4: {"uf": "RJ", "cnpj": "", "prefixos": []}}


def test_sinais_por_asn_e_agregados_por_uf_sem_contar_amostra_pequena():
    r = calcular(IROV, DNSSEC, ASRANK, BOGONS, DOCS, {"A": 50, "B": 20000, "C": 0})
    a1 = r["asns"]["1"]
    assert a1["rov"] == {"validates_pct": 0.5, "amostras": 500} and a1["dnssec"]["parcial_pct"] == 2.0 and a1["asrank"] == {"rank": 10, "cone": {"asns": 5}}
    assert a1["prefixos_em_bogon"] == [{"prefixo": "10.1.0.0/16", "lista": "iana"}] and a1["n_prefixos_bogon"] == 1
    assert a1["uf"] == "SP" and a1["faixa_porte"] == "ate_1000" and a1["faixa_acessos_sici"] == "ate_1000" and "uf" not in r["asns"]["9"]
    assert r["asns"]["2"]["faixa_porte"] == "de_10000_a_100000" and r["asns"]["2"]["faixa_acessos_sici"] == "de_10000_a_100000" and r["asns"]["3"]["faixa_porte"] == "sem_usuarios" and r["asns"]["3"]["faixa_acessos_sici"] == "sem_acessos"
    assert "9" in r["asns"] and "9" not in r["por_uf"]                          # ASN só do AS Rank tem registro, mas fora dos agregados do Brasil (não está nos docs BR)
    sp, rj = r["por_uf"]["SP"], r["por_uf"]["RJ"]
    assert sp["asns"] == 2 and sp["rov"]["asns"] == 2 and sp["rov"]["faixas"] == {"ate_10": 1, "de_10_a_90": 0, "acima_de_90": 1}
    assert sp["rov"]["media_ponderada_pct"] == round((0.5 * 500 + 95 * 300) / 800, 2) and sp["dnssec"]["asns"] == 2 and sp["asns_com_prefixo_bogon"] == 1
    assert rj["rov"]["asns"] == 1 and rj["dnssec"] == {"asns": 0}                # ASN 3 tem só 10 amostras: fora; ASN 4 entra com 0%
    assert r["brasil"]["rov"]["asns"] == 3
    assert r["por_faixa_porte"]["sem_usuarios"]["asns"] == 2 and r["por_faixa_porte"]["de_10000_a_100000"]["asns"] == 1 and r["por_faixa_porte"]["ate_1000"]["asns"] == 1


def test_sem_listas_de_bogons_nao_inventa_sinal():
    r = calcular(IROV, None, None, None, DOCS, {})
    assert "prefixos_em_bogon" not in r["asns"]["1"] and "dnssec" not in r["asns"]["1"]


def _gz(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(obj, f)


def test_publicar_grava_artefato_com_fontes_e_limites(tmp_path):
    d = "2026-10-31"
    n = tmp_path / "normalized" / d / "summary"
    _gz(n / "apnic_irov.json.gz", {**IROV, "as_of": "2026-10-30", "janela_dias": 7, "copyright": "c"})
    _gz(n / "bogons.json.gz", BOGONS)
    pub = tmp_path / "published" / d
    (pub / "asns").mkdir(parents=True)
    (pub / "asns" / "index.json").write_text(json.dumps([{"asn": 1, "is_br": True}, {"asn": 2, "is_br": True}]))
    (pub / "asns" / "1.json").write_text(json.dumps({"cnpj": "A", "geo_org": {"uf": "SP"}, "global_prefixes_v4": ["10.1.0.0/16"], "global_prefixes_v6": []}))
    (pub / "asns" / "2.json").write_text(json.dumps({"cnpj": "B", "geo_org": None, "global_prefixes_v4": [], "global_prefixes_v6": []}))
    assert publicar_seguranca(tmp_path, d, _Log()) == {"asns": 4, "ufs": 1, "com_bogon": 1}
    out = json.loads(gzip.open(pub / "seguranca" / "asns.json.gz").read())
    assert out["fontes"]["rov"]["as_of"] == "2026-10-30" and out["fontes"]["bogons"]["lista_cymru_em"] == "2026-10-31" and "Spamhaus" in out["limites"]
    assert out["asns"]["1"]["n_prefixos_bogon"] == 1 and out["parametros"]["min_amostras"] == 100


def test_sem_nenhuma_fonte_nao_grava(tmp_path):
    (tmp_path / "published" / "2026-10-31").mkdir(parents=True)
    assert publicar_seguranca(tmp_path, "2026-10-31", _Log()) == {}
    assert not (tmp_path / "published" / "2026-10-31" / "seguranca").exists()
