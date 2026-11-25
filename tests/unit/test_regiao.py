# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Região: os três vínculos município–ASN, a participação nos PTTs, o trânsito e os carregadores."""
import pytest

from api.services import regiao as s
from products.regiao import build as b

POR_NOME = {("ES", "VITORIA"): "3205309", ("ES", "VILA VELHA"): "3205200"}


def doc(asn, nome, *, br=True, d=(), o=(), up=(), prov=(), sede=None, geo=None):
    return asn, {"name": nome, "is_br": br, "ixps_direct": list(d), "ixps_origin": list(o), "upstreams": list(up) + [asn],
                 "relacoes": {"provedores": [{"asn": p, "p": 0.9, "nivel": n, "nome": f"AS{p} - Prov {p}, BR"} for p, n in prov]},
                 "geo_org": {"codigo_municipio_ibge": sede} if sede else {},
                 "geo_prefixes_v4": {f"10.0.{i}.0/24": {"city": c, "uf": "ES", "country": "BR"} for i, c in enumerate(geo or [])}, "geo_prefixes_v6": {}}


DOCS = [
    doc(100, "Fibra Vix", d=["vix", "sp"], o=["vix", "sp"], prov=[(3356, "confirmado"), (200, "provavel")], sede=3205309, geo=["Vitória", "Vitória", "Vila Velha"]),
    doc(150, "Só IPs", o=["vix"], up=[100], prov=[(200, "possivel")], geo=["Vitória"]),         # nenhum SICI, nenhuma sede: entra só por IPs geolocalizados
    doc(160, "Indireto", o=["vix"], up=[100, 999], prov=[(100, "provavel"), (3356, "provavel")]),
    doc(170, "Sem PTT", prov=[(3356, "provavel")]),
    doc(200, "Trânsito BR", d=["sp"], o=["sp"]),
    doc(3356, "Level 3", br=False, d=["sp"], o=["sp"]),
    doc(999, "Vizinho fora de PTT", o=[]),
    doc(300, "Estrangeiro com IPs aqui", br=False, geo=["Vitória"]),
]
SICI = {"municipios": {"3205309": {"operadores": [{"cnpj": "1", "acessos": 600, "asns": [100]}, {"cnpj": "2", "acessos": 40, "asns": [160]}]},
                       "3205200": {"operadores": [{"cnpj": "2", "acessos": 10, "asns": [160]}, {"cnpj": "3", "acessos": 5, "asns": [170, 3356]}]}}}
MOVEL = {"municipios": {"3205309": {"operadores": [{"cnpj": "1", "acessos": 1000, "asns": [100]}]}}}


@pytest.fixture(scope="module")
def artefato():
    return {"snapshot_date": "2026-11-03", "natureza": "inferido", "limites": "l", "fontes": {}, "ptts_nomes": {"vix": "Vitória", "sp": "São Paulo"}, **b.calcular(DOCS, SICI, MOVEL, POR_NOME)}


def test_tres_vinculos_entram_no_municipio(artefato):
    vix = artefato["municipios"]["3205309"]
    assert vix["s"]["100"] == [600, 1000]                       # fixo e móvel
    assert vix["h"] == [100]                                     # sede
    assert vix["g"] == {"100": 2, "150": 1}                      # só contagem de prefixos, por ASN; o estrangeiro não entra
    assert "300" not in vix["g"]
    assert artefato["municipios"]["3205200"]["g"] == {"100": 1}


def test_asn_estrangeiro_so_entra_na_tabela_como_transito_ou_carregador(artefato):
    assert artefato["asns"]["3356"]["m"] == 0 and artefato["asns"]["3356"]["d"] == ["sp"]
    assert artefato["asns"]["100"]["m"] == 1
    assert "300" not in artefato["asns"]


def test_agregado_participacao_nos_ptts(artefato):
    r = s.agregar(artefato, ["3205309"])
    assert r["asns"]["total"] == 3                               # 100 (sici+sede+geo), 150 (só IPs), 160 (sici); 170 só aparece em Vila Velha
    assert r["asns"]["por_vinculo"] == {"sici": 2, "sede": 1, "geo": 2}
    p = r["participacao_ptts"]
    assert (p["com_ptt_direto"], p["so_indireto"], p["sem_ptt"]) == (1, 2, 0)
    assert (p["pct_direto"], p["pct_indireto"], p["pct_sem_ptt"]) == (33.3, 66.7, 0.0)
    vix = next(x for x in p["ptts"] if x["codigo"] == "vix")
    assert (vix["direto"], vix["indireto"], vix["total"]) == (1, 2, 3)


def test_conjunto_une_asns_sem_contar_duas_vezes(artefato):
    um = s.agregar(artefato, ["3205309"])
    dois = s.agregar(artefato, ["3205309", "3205200"])
    assert um["asns"]["total"] == 3 and dois["asns"]["total"] == 4     # + 170 (SICI de Vila Velha); o 3356 é de fora do Brasil e não entra; 100 e 160 não contam duas vezes
    assert dois["asns"]["total"] == len({p["asn"] for p in dois["provedores"]})
    com_100 = [p for p in dois["provedores"] if p["asn"] == 100]
    assert len(com_100) == 1 and com_100[0]["acessos_fixo"] == 600 and com_100[0]["prefixos_geo"] == 3


def test_transito_ordena_por_confianca_e_marca_quem_e_da_regiao(artefato):
    r = s.agregar(artefato, ["3205309", "3205200"])
    t = {x["asn"]: x for x in r["transito"]}
    assert t[3356]["niveis"]["confirmado"] == 1 and t[3356]["niveis"]["provavel"] >= 1
    assert t[3356]["na_regiao"] is False and t[3356]["ptts_diretos"] == ["sp"]
    assert t[100]["na_regiao"] is True
    assert r["transito"][0]["asn"] == 3356                       # mais ASNs com confiança confirmada ou provável


def test_carregadores_so_dos_indiretos_e_so_se_o_vizinho_tem_sessao(artefato):
    r = s.agregar(artefato, ["3205309"])
    assert any(c["asn"] == 100 and c["na_regiao"] for c in r["carregadores"])
    assert all(c["asn"] != 999 for c in r["carregadores"])        # 999 não está em nenhum PTT: não leva a lugar nenhum
    assert r["indiretos_sem_carregador"] == 0


def test_regras_da_consulta():
    assert s.ibges_da_consulta("3205309, 3205200,3205309") == ["3205309", "3205200"]
    for ruim in ("", "abc", "123", ",".join(str(3200000 + i) for i in range(51))):
        with pytest.raises(s.RegiaoErro):
            s.ibges_da_consulta(ruim)


def test_municipio_sem_dado_nao_quebra(artefato):
    r = s.agregar(artefato, ["1100015"])
    assert r["asns"]["total"] == 0 and r["participacao_ptts"]["pct_direto"] is None and r["municipios_com_dados"] == 0


def _pront(*asns):
    """Documento mínimo da prontidão: ASN com ROV e ROA, no formato de `prontidao/asns.json.gz`."""
    def a(total, rov, roa):
        return {"total": total, "classe": "pronto" if total >= 80 else "atrasado", "usuarios": 100, "pilares": {
            "filtragem": {"score": rov, "peso": 25, "componentes": {"rov": {"valor": rov, "peso": 3, "detalhe": None}}},
            "validacao_global": {"score": roa, "peso": 30, "componentes": {"roa": {"valor": roa, "peso": 3, "detalhe": None}}}}}
    return {"asns": {str(n): a(*v) for n, v in asns}, "brasil": {"asns": 9}, "regras": {"hash": "x"}, "limites": "l", "fontes": {}}


def test_prontidao_da_regiao_vale_com_um_asn_e_diz_quantos_sustentam(artefato):
    pd = _pront((100, (90, 100, 80)), (999, (10, 0, 0)))
    r = s.agregar(artefato, ["3205309"], pd)["prontidao"]                    # 3205309 tem 100, 150, 160 (e 999 não é do município)
    assert r["asns_no_indice"] == 1 and r["agregado"]["asns"] == 1
    rov = r["agregado"]["medicoes"]["rov"]
    assert {k: rov[k] for k in ("pilar", "asns", "media", "media_ponderada_usuarios")} == {"pilar": "filtragem", "asns": 1, "media": 100.0, "media_ponderada_usuarios": 100.0}
    assert rov["n_asns_com_dado"] == 1 and "poucos_casos" in rov["avisos"]
    assert r["agregado"]["medicoes"]["roa"]["media"] == 80.0
    assert r["brasil"] == {"asns": 9} and r["regras"]["hash"] == "x"


def test_prontidao_da_regiao_sem_asn_no_indice_ou_sem_produto(artefato):
    assert s.agregar(artefato, ["3205309"], None)["prontidao"] is None
    vazio = s.agregar(artefato, ["3205309"], _pront((999, (10, 0, 0))))["prontidao"]
    assert vazio["agregado"] is None and vazio["asns_no_indice"] == 0
