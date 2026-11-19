# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Espaço IPv4 sem uso e hipóteses de uso por terceiros: classes e sinais plantados com resultado conhecido."""
import ipaddress

from products.ipv4_uso import build as U


def bloco(ini, q=256, status="allocated", data="20150101"):
    return {"inicio": ini, "quantidade": q, "status": status, "cc": "BR", "data": data, "opaque": "o"}


def tabela(*pares):
    return U.Tabela(pares)


IDX = {"10.0.0.0/24": {"asn": 100, "org": "ALFA LTDA", "cnpj": "111"}, "10.0.1.0/24": {"asn": 100, "org": "ALFA LTDA", "cnpj": "111"}, "10.0.2.0/24": {"asn": 200, "org": "BETA LTDA", "cnpj": "222"},
       "10.0.3.0/24": {"asn": 100, "org": "ALFA LTDA", "cnpj": "111"}}


def rodar(blocos, tab, roas=(), idx=IDX, recup=(), rel=(), cnpj=None, mudancas=(), transf=(), eventos=()):
    return {l["inicio"]: l for l in U.classificar(blocos, tab, U.Roas(list(roas)), idx, [ipaddress.ip_network(r) for r in recup], set(rel), cnpj or {100: "111", 200: "222", 300: "333"}, list(mudancas), list(transf), list(eventos))}


def test_tabela_cobertura_por_prefixo_cobrindo_mais_especifico_e_parcial():
    t = tabela(("10.0.0.0/23", 100), ("10.0.3.0/25", 100), ("10.0.9.0/24", 300))
    assert t.cobertura(int(ipaddress.IPv4Address("10.0.1.0")), int(ipaddress.IPv4Address("10.0.1.255"))) == (1.0, {100})        # coberto por um prefixo maior
    pct, o = t.cobertura(int(ipaddress.IPv4Address("10.0.3.0")), int(ipaddress.IPv4Address("10.0.3.255")))
    assert pct == 0.5 and o == {100}                                                                                            # só a metade anunciada
    assert t.cobertura(int(ipaddress.IPv4Address("10.0.2.0")), int(ipaddress.IPv4Address("10.0.2.255"))) == (0.0, set())


def test_classes_anunciado_parcial_roa_sem_anuncio_nao_anunciado_e_em_recuperacao():
    t = tabela(("10.0.0.0/24", 100), ("10.0.3.0/25", 100))
    bl = [bloco("10.0.0.0"), bloco("10.0.3.0"), bloco("10.0.1.0"), bloco("10.0.2.0"), bloco("10.0.4.0")]
    l = rodar(bl, t, roas=[{"prefix": "10.0.1.0/24", "asn": 100, "maxLength": 24}], recup=["10.0.4.0/24"])
    assert [l[i]["classe"] for i in ("10.0.0.0", "10.0.3.0", "10.0.1.0", "10.0.2.0", "10.0.4.0")] == ["anunciado", "parcial", "roa_sem_anuncio", "nao_anunciado", "em_recuperacao"]
    assert l["10.0.3.0"]["anunciado_pct"] == 50.0 and l["10.0.0.0"]["titular"] == {"asn": 100, "org": "ALFA LTDA", "cnpj": "111"}


def test_s1_origem_diferente_do_titular_com_confianca_baixa_se_relacionados_ou_mesmo_cnpj():
    t = tabela(("10.0.0.0/24", 300), ("10.0.1.0/24", 200), ("10.0.3.0/24", 400))
    l = rodar([bloco("10.0.0.0"), bloco("10.0.1.0"), bloco("10.0.3.0")], t, rel=[(100, 200)], cnpj={100: "111", 200: "222", 300: "333", 400: "111"})
    assert [s["id"] for s in l["10.0.0.0"]["sinais"]] == ["S1"] and l["10.0.0.0"]["sinais"][0]["confianca"] == "media" and l["10.0.0.0"]["confianca"] == "media"
    assert l["10.0.1.0"]["sinais"][0]["confianca"] == "baixa" and "relacionados" in l["10.0.1.0"]["sinais"][0]["evidencia"]           # AS200 é cliente ou provedor do titular
    assert l["10.0.3.0"]["sinais"][0]["confianca"] == "baixa"                                                                         # AS400 tem o mesmo CNPJ do titular


def test_titular_que_anuncia_o_proprio_bloco_nao_gera_sinal():
    l = rodar([bloco("10.0.0.0")], tabela(("10.0.0.0/24", 100)))
    assert l["10.0.0.0"]["sinais"] == [] and l["10.0.0.0"]["confianca"] is None


def test_s2_roa_de_outro_asn_e_dois_sinais_sobem_a_confianca():
    t = tabela(("10.0.0.0/24", 300))
    l = rodar([bloco("10.0.0.0")], t, roas=[{"prefix": "10.0.0.0/24", "asn": 300, "maxLength": 24}])
    assert [s["id"] for s in l["10.0.0.0"]["sinais"]] == ["S1", "S2"] and l["10.0.0.0"]["confianca"] == "alta"


def test_s3_bloco_sem_asn_titular_anunciado_por_terceiro_e_estrangeiro_sobe_para_media():
    t = tabela(("10.0.8.0/24", 300), ("10.0.9.0/24", 999))
    l = rodar([bloco("10.0.8.0"), bloco("10.0.9.0")], t)
    assert l["10.0.8.0"]["sinais"][0] == {"id": "S3", "confianca": "baixa", "evidencia": "sem ASN titular; anunciado por AS300"} and l["10.0.9.0"]["sinais"][0]["confianca"] == "media"


def test_s4_origem_mudou_sem_transferencia_e_some_com_transferencia_ou_titularidade_por_perto():
    t = tabela(("10.0.0.0/24", 100))
    mud = [{"data": "2026-10-01", "de": 100, "para": 300, "_i0": int(ipaddress.IPv4Address("10.0.0.0")), "_i1": int(ipaddress.IPv4Address("10.0.0.255"))}]
    assert [s["id"] for s in rodar([bloco("10.0.0.0")], t, mudancas=mud)["10.0.0.0"]["sinais"]] == ["S4"]
    assert rodar([bloco("10.0.0.0")], t, mudancas=mud, transf=[{"data": "2026-09-20", "blocos": ["10.0.0.0/24"]}])["10.0.0.0"]["sinais"] == []
    ev = [{"tipo": "titularidade", "data": "2026-10-10", "_i0": int(ipaddress.IPv4Address("10.0.0.0")), "_i1": int(ipaddress.IPv4Address("10.0.0.255"))}]
    assert rodar([bloco("10.0.0.0")], t, mudancas=mud, eventos=ev)["10.0.0.0"]["sinais"] == []
    assert [s["id"] for s in rodar([bloco("10.0.0.0")], t, mudancas=mud, transf=[{"data": "2025-01-01", "blocos": ["10.0.0.0/24"]}])["10.0.0.0"]["sinais"]] == ["S4"]


def test_resumo_soma_por_classe_e_uf_e_lista_os_maiores_titulares_sem_anuncio():
    t = tabela(("10.0.0.0/24", 100))
    ls = list(rodar([bloco("10.0.0.0"), bloco("10.0.1.0"), bloco("10.0.2.0"), bloco("10.0.3.0")], t).values())
    r = U.resumo(ls, {100: "SP", 200: "RJ"})
    assert r["total_blocos"] == 4 and r["por_classe"]["anunciado"]["blocos"] == 1 and r["por_classe"]["nao_anunciado"]["enderecos"] == 768
    assert r["por_uf"]["SP"]["nao_anunciado"] == 512 and r["por_uf"]["RJ"]["nao_anunciado"] == 256 and r["maiores_titulares_nao_anunciado"][0] == {"asn": 100, "org": "ALFA LTDA", "enderecos": 512}


def test_sinais_nao_avaliados_dizem_por_que():
    assert [k for k, v in U.SINAIS.items() if not v["avaliado"]] == ["S5", "S6", "S7"] and all(U.SINAIS[k]["motivo"] for k in ("S5", "S6", "S7"))
    assert all(U.SINAIS[k]["falsos_positivos"] for k in ("S1", "S2", "S3", "S4"))


def test_duracao_conta_tabelas_de_origem_distintas_e_nao_snapshots(tmp_path):
    from core.common import write_json_gz
    def grava(dia, tabela):
        write_json_gz(tmp_path / "normalized" / dia / "summary" / "origin-prefixes-v4.json.gz", tabela)
    a, b = {"100": ["10.0.9.0/24"]}, {"100": ["10.0.9.0/24"], "200": ["10.0.8.0/24"]}
    grava("2026-10-20", {"100": ["10.0.0.0/24"]})                                                    # tabela mais antiga: o bloco estava anunciado
    grava("2026-10-25", a); grava("2026-10-26", a); grava("2026-10-27", a)                           # a mesma tabela semanal repetida em 3 dias
    grava("2026-10-30", b); grava("2026-11-01", b)
    grava("2026-11-02", {"100": ["10.0.9.0/24"], "300": ["10.0.7.0/24"]})
    bl = [bloco("10.0.0.0")]
    ls = U.classificar(bl, U.Tabela([("10.0.9.0/24", 100)]), U.Roas([]), IDX, [], set(), {100: "111"}, [], [], [])
    assert ls[0]["classe"] == "nao_anunciado"
    d = U.duracao_sem_anuncio(tmp_path, "2026-11-02", bl, ls)
    assert ls[0]["tabelas_sem_anuncio"] == 3 and ls[0]["sem_anuncio_desde"] == "2026-10-25"          # hoje + a tabela b + a tabela a (3 dias iguais contam uma vez, desde o primeiro: 25/10); a de 20/10 o tinha anunciado
    assert d["tabelas_anteriores_consultadas"] == ["2026-11-01", "2026-10-27", "2026-10-20"] or d["tabelas_anteriores_consultadas"][:2] == ["2026-10-30", "2026-10-27"]
