# SPDX-License-Identifier: AGPL-3.0-or-later
"""T2 — camada de rede (PTTs, ASNs, prefixos, rotas, RPKI) do dataset sintético → published/.

O dataset ("Arandurápolis", ver tests/synth/world.py) tem dois instantes com diferenças plantadas.
"""
import hashlib
import json

import pytest

from tests.products import golden
from tests.synth.generate import generate
from tests.synth.world import T0, T1


def load(base, date, *parts):
    return json.loads((base / "published" / date).joinpath(*parts).read_text(encoding="utf-8"))


GOLDEN_T1 = ["summary.json", "manifest.json", "ixps/index.json", "ixps/za.json", "ixps/zc.json", "asns/index.json",
             "asns/names.json", "asns/64496.json", "asns/64497.json", "asns/64502.json", "asns/64503.json",
             "asns/4200000000.json", "asns/4200000100.json"]
GOLDEN_T0 = ["summary.json", "asns/64502.json", "asns/64503.json"]


def test_dataset_e_deterministico(tmp_path):
    def digest(d):
        h = hashlib.sha256()
        for p in sorted(d.rglob("*")):
            if p.is_file():
                h.update(p.relative_to(d).as_posix().encode())
                h.update(p.read_bytes() if p.suffix != ".gz" else b"")      # .gz tem mtime no cabeçalho
        return h.hexdigest()

    generate(tmp_path / "a", seed=1)
    generate(tmp_path / "b", seed=1)
    assert digest(tmp_path / "a") == digest(tmp_path / "b")


def test_pipeline_publica_o_esperado(pipeline):
    base, res = pipeline
    r = res[T1]
    assert r["ixps_indexed"] == 3 and r["asns_indexed"] == 61                  # 37 BR (com o AS da filial do cenário 10) + 24 de fora
    for name in ("summary.json", "manifest.json", "asns/index.json", "ixps/index.json", "hilbert_v4.json", "hilbert_v6.json"):
        assert (base / "published" / T1 / name).exists(), name


@pytest.mark.parametrize("rel", GOLDEN_T1)
def test_ouro_t1(pipeline, request, rel):
    golden.check(pipeline[0], "T1", T1, rel, request.config.getoption("--update-golden"))


@pytest.mark.parametrize("rel", GOLDEN_T0)
def test_ouro_t0(pipeline, request, rel):
    golden.check(pipeline[0], "T0", T0, rel, request.config.getoption("--update-golden"))


# ── cenários plantados ─────────────────────────────────────────────────────

def test_cenario_5_ptt_com_coleta_parcial(pipeline):
    base, _ = pipeline
    s = load(base, T1, "summary.json")
    assert (s["ixps_ok"], s["ixps_partial"], s["ixps_missing"]) == (2, 1, 0)
    zc = next(e for e in load(base, T1, "ixps", "index.json") if e["code"] == "zc")
    assert zc["status"] == "partial" and zc["v6"] == {"status": "missing", "coleta": "missing"} and zc["v4"]["unique_prefixes"] > 0


def test_cenario_1_moas_e_roa_invalido(pipeline):
    base, _ = pipeline
    a64497 = load(base, T1, "asns", "64497.json")
    assert a64497["rpki_validation"]["198.18.0.0/24"] == "invalid"
    ids = {a["id"] for a in a64497["alerts"]}
    assert "rpki_invalido" in ids
    a64496 = load(base, T1, "asns", "64496.json")
    assert a64496["rpki_validation"]["198.18.0.0/24"] == "valid"
    # o prefixo aparece com as duas origens nos PTTs (MOAS)
    assert "198.18.0.0/24" in a64496["ixp_presence"]["za"]["v4"]["prefixes"]
    assert "198.18.0.0/24" in a64497["ixp_presence"]["za"]["v4"]["prefixes"]
    assert "198.18.0.0/24" not in a64497["global_prefixes_v4"]          # a tabela global atribui a origem a 64496


def test_cenario_6_origem_do_prefixo_muda_entre_t0_e_t1(pipeline):
    base, _ = pipeline
    moving = "198.18.24.0/21"
    t0_old = load(base, T0, "asns", "64502.json")["global_prefixes_v4"]
    t0_new = load(base, T0, "asns", "64503.json")["global_prefixes_v4"]
    t1_old = load(base, T1, "asns", "64502.json")["global_prefixes_v4"]
    t1_new = load(base, T1, "asns", "64503.json")["global_prefixes_v4"]
    assert moving in t0_old and moving not in t0_new
    assert moving not in t1_old and moving in t1_new
    # em T1 o ROA continua em nome de 64502: o novo originador fica inválido
    assert load(base, T1, "asns", "64503.json")["rpki_validation"][moving] == "invalid"


def test_novo_membro_em_t1(pipeline):
    base, _ = pipeline
    idx0 = {e["code"]: e for e in load(base, T0, "ixps", "index.json")}
    idx1 = {e["code"]: e for e in load(base, T1, "ixps", "index.json")}
    assert idx1["zb"]["asn_direct_union_count"] == idx0["zb"]["asn_direct_union_count"] + 1
    assert idx1["za"]["asn_direct_union_count"] == idx0["za"]["asn_direct_union_count"]


def test_totais_do_summary(pipeline):
    base, _ = pipeline
    s = load(base, T1, "summary.json")
    assert s["total_asns_global"] == 61 and s["total_asns_br"] == 37
    assert s["fulltable_v4_status"] == "ok" and s["registro_br_status"] == "ok"
    assert s["pipeline_version"]                                           # vem do arquivo VERSION


# ═══ camada de mercado e regulatória (outorgas, SICI, grupos) ════════════════════════════════════════

import gzip

GOLDEN_T1_MERCADO = ["scm.json.gz", "smp.json.gz", "stfc.json.gz", "seac.json.gz", "sici.json.gz", "sici_municipios.json.gz",
                     "sici_movel.json.gz", "grupos_societarios.json.gz", "asns/64504.json", "asns/64505.json", "asns/64510.json",
                     "asns/64500.json", "asns/64501.json", "empresas/cadastro.json.gz", "financiamento/operadoras.json.gz", "radar/asns.json.gz", "contratos/operadoras.json.gz", "contratos/municipios.json.gz", "contratos/resumo.json.gz", "exposicao/asns.json.gz", "territorio/area_influencia_ptt.json.gz"]


def load_gz(base, date, name):
    return json.loads(gzip.open(base / "published" / date / name, "rt", encoding="utf-8").read())


@pytest.mark.parametrize("rel", GOLDEN_T1_MERCADO)
def test_ouro_mercado_t1(pipeline, request, rel):
    golden.check(pipeline[0], "T1", T1, rel, request.config.getoption("--update-golden"))


def test_publica_os_artefatos_de_mercado(pipeline):
    base, res = pipeline
    r = res[T1]
    assert r["scm_total"] == 43 and r["scm_matched_asns"] == 35      # 35 CNPJs com ASN + 8 sem ASN
    assert r["sici_cnpjs"] == 42 and r["sici_mes_referencia"] == "2026-08"
    assert (r["smp_total"], r["stfc_total"], r["seac_total"]) == (4, 3, 6)          # 3 outorgas SMP + o registro de credenciada de rede virtual (PT-05)
    assert r["sici_movel_cnpjs"] == 3 and r["grupos_societarios_total"] == 4


def test_cenario_2_outorga_scm_sem_sici_mas_com_usuarios_apnic(pipeline):
    base, _ = pipeline
    a = load(base, T1, "asns", "64510.json")
    cnpj = a["cnpj"]
    scm = load_gz(base, T1, "scm.json.gz")
    assert cnpj in scm["by_cnpj"] and 64510 in scm["cnpj_to_asns"][cnpj]
    assert cnpj not in load_gz(base, T1, "sici.json.gz")["cnpjs"]            # não declarou ao SICI
    assert "sici" not in a and a["apnic_users"] and a["apnic_users"] > 0


def test_cenario_3_cnpj_com_dois_asns_nao_duplica_acessos(pipeline):
    base, _ = pipeline
    a0, a1 = load(base, T1, "asns", "64500.json"), load(base, T1, "asns", "64501.json")
    assert a0["cnpj"] == a1["cnpj"]
    for a in (a0, a1):
        assert a["sici"]["acessos_compartilhados"] is True and a["sici"]["asns"] == [64500, 64501]
        assert a["sici"]["divergencia_apnic_anatel"] == {"classificacao": "nao_comparavel", "motivo": "acessos_compartilhados"}
    sici = load_gz(base, T1, "sici.json.gz")
    assert sici["cnpjs"][a0["cnpj"]]["acessos"] == a0["sici"]["acessos"] == a1["sici"]["acessos"]
    total = sum(c["acessos"] for c in sici["cnpjs"].values())
    assert total == sici["total_acessos"]                                    # o CNPJ conta uma única vez


@pytest.mark.parametrize("asn, classe", [(64504, "apnic_alto"), (64505, "apnic_baixo"), (64496, "normal")])
def test_divergencia_apnic_anatel(pipeline, asn, classe):
    base, _ = pipeline
    assert load(base, T1, "asns", f"{asn}.json")["sici"]["divergencia_apnic_anatel"]["classificacao"] == classe


def test_cenario_4_grupos_total_e_parcial(pipeline):
    base, _ = pipeline
    g = load_gz(base, T1, "grupos_societarios.json.gz")
    by = g["by_cnpj"]
    asn_cnpj = {a: load(base, T1, "asns", f"{a}.json")["cnpj"] for a in (64506, 64507, 64508, 64509, 64511, 65536)}
    # quadro idêntico → mesmo_grupo
    assert [m["tipo_relacao"] for m in by[asn_cnpj[64506]]["mesmo_grupo"]] == ["quadro_identico"]
    assert by[asn_cnpj[64506]]["mesmo_grupo"][0]["cnpj"] == asn_cnpj[64507]
    # holding externa em comum → relacionadas_parcial (e holding resolvida)
    parcial = by[asn_cnpj[64508]]["relacionadas_parcial"]
    assert parcial and parcial[0]["cnpj"] == asn_cnpj[64509] and parcial[0]["tipo_relacao"] == "socios_em_comum"
    assert by[asn_cnpj[64508]]["holdings_externas"][0]["cnpj_basico"] == "55500001"
    # controle exclusivo
    assert by[asn_cnpj[65536]]["mesmo_grupo"][0]["tipo_relacao"] == "controle_exclusivo_recebido"
    assert g["total_grupos"] == 4                                  # 3 do cenário 4 + a Ltda SemASN1 com a S.A. SemASN2 sócia (cenário 12, P8)


def test_cenario_7_nada_de_contato_peeringdb_nos_artefatos_publicados(pipeline):
    base, _ = pipeline
    for p in (base / "published" / T1).rglob("*"):
        if p.is_file():
            if p.suffix == ".col":                          # tabela colunar binária: vocabulário em JSON, lido como bytes
                data = p.read_bytes().decode("utf-8", errors="replace")
            else:
                data = gzip.open(p, "rt", encoding="utf-8").read() if p.suffix == ".gz" else p.read_text(encoding="utf-8")
            assert "peeringdb.example.org" not in data and "Contato 64" not in data and "+55 11 90000-0000" not in data, p.name


# ═══ camada geográfica/infraestrutura, IXP externo e cenário 8 ══════════════════════════════════════

GOLDEN_T1_GEO = ["maps/itu_transmission.geojson", "maps/submarine_cables.geojson", "maps/submarine_landing_points.geojson",
                 "maps/power_transmission_lines.geojson", "maps/ibge_rodovias.geojson", "maps/scms.geojson",
                 "maps/asns.geojson", "external-ixps/index.json", "external-ixps/zx.json"]


@pytest.mark.parametrize("rel", GOLDEN_T1_GEO)
def test_ouro_geo_t1(pipeline, request, rel):
    golden.check(pipeline[0], "T1", T1, rel, request.config.getoption("--update-golden"))


def test_camadas_de_infraestrutura_publicadas(pipeline):
    r = pipeline[1][T1]
    assert (r["itu_links"], r["submarine_cables"], r["submarine_landing_points"],
            r["power_transmission_lines"], r["ibge_rodovias"]) == (3, 1, 1, 1, 1)
    assert r["external_ixps"] == 1 and r["geo_global_prefixes"] > 50 and r["geo_asns"] == 61   # 37 BR (com o AS da filial do cenário 10) + 24 internacionais


def test_ixp_externo_cruza_membros_br_com_o_ixbr(pipeline):
    base, _ = pipeline
    zx = load(base, T1, "external-ixps", "zx.json")
    assert zx["code"] == "zx" and zx["member_count"] == 5
    br = [m for m in zx["members"] if m.get("is_br")]
    assert len(br) == 4                                                   # 3 redes BR, uma com duas portas


def test_ixp_externo_conta_redes_distintas_e_portas_a_parte(pipeline):
    """IXE-E1: uma rede com duas portas conta uma vez; `member_count`/`br_member_count` são alias de `redes`/`redes_br`."""
    base, _ = pipeline
    zx = load(base, T1, "external-ixps", "zx.json")
    assert (zx["redes"], zx["redes_br"], zx["portas"]) == (5, 3, 6)
    assert (zx["member_count"], zx["br_member_count"]) == (zx["redes"], zx["redes_br"])
    idx = next(i for i in load(base, T1, "external-ixps", "index.json")["ixps"] if i["code"] == "zx")
    assert (idx["redes"], idx["redes_br"], idx["portas"], idx["member_count"], idx["br_member_count"]) == (5, 3, 6, 5, 3)


def test_sem_vazamento_de_arquivos_inesperados(pipeline):
    """A lista de artefatos publicados é conhecida; algo novo precisa entrar de propósito (e ter classe de acesso)."""
    base, _ = pipeline
    nomes = sorted(p.relative_to(base / "published" / T1).as_posix() for p in (base / "published" / T1).rglob("*") if p.is_file())
    topo = {n.split("/")[0] for n in nomes}
    assert topo == {"asns", "cdns.json", "external-ixps", "grupos_societarios.json.gz", "hilbert_v4.json", "hilbert_v6.json",
                    "ixps", "manifest.json", "maps", "rpki", "scm.json.gz", "seac.json.gz", "sici.json.gz", "snapshot_detail.json",
                    "sici_indicadores.json.gz", "sici_serie_municipio.json.gz", "mercado_grupos.json.gz", "sem_declaracao_sici.json.gz", "territorio", "seguranca", "prontidao", "manrs", "route_servers", "as2org", "rs_policy", "qualidade", "consumidor", "empresas", "financiamento", "bloqueios", "radar", "contratos", "exposicao", "instalacoes", "abuso_agregado", "cetic", "mercado", "erbs", "regulatorio", "ipv4", "sici_movel.json.gz", "sici_movel_municipios.json.gz", "sici_municipios.json.gz", "smp.json.gz",
                    "stfc.json.gz", "summary.json"}
    assert not any("peeringdb_contacts" in n for n in nomes)                # contatos nunca vão para published/ (AUP)


def test_cenario_8_municipio_sem_ptt_a_menos_de_100_km(pipeline, monkeypatch):
    """Tabajara do Norte (AM) fica a milhares de km de qualquer PTT: os ASes de lá não aparecem no raio de nenhum PTT."""
    from api.geo import haversine_km
    from api.store import Store
    from tests.products.conftest import fake_pix
    from tests.synth.world import MUNICIPIOS, PTTS

    base, _ = pipeline
    monkeypatch.setattr(Store, "_load_pix_config", lambda self: fake_pix())
    store = Store(base)
    pix = [(m[3], m[4]) for m in MUNICIPIOS if m[1] in {n for _, n, _ in PTTS}]
    sem_ptt = [m[1] for m in MUNICIPIOS if all(haversine_km(m[3], m[4], la, lo) > 100 for la, lo in pix)]
    assert "Tabajara do Norte" in sem_ptt and "Arandurápolis" not in sem_ptt
    asn_de_tabajara = next(a for a in (64496 + i for i in range(16)) if load(base, T1, "asns", f"{a}.json")["geo_org"]["city"] == "Tabajara do Norte")
    cobertos = set()
    for code, _, _ in PTTS:
        cobertos |= {x["asn"] for x in store.ixp_nearby_breakdown(T1, code, radius_km=100)["asns"]}
    assert asn_de_tabajara not in cobertos and 64496 in cobertos


def test_store_enxerga_o_dataset_sintetico(pipeline):
    from api.store import Store

    base, _ = pipeline
    s = Store(base)
    assert s.list_snapshots() == [T0, T1] and s.latest() == T1


def test_cadastro_empresas_publica_mercado_e_operadoras_sem_dado_pessoal(pipeline):
    """O cadastro da Receita cruzado com o SICI, publicado em empresas/ (mercado + operadoras em faixas de CNPJ)."""
    base, _ = pipeline
    geral = load_gz(base, T1, "empresas/cadastro.json.gz")
    assert geral["natureza"] == "fato_cadastral" and geral["dump_reference"] == "2026-09" and "não prova" in geral["limites"]
    assert geral["resumo"]["operadoras_com_cadastro"] > 0 and geral["resumo"]["estabelecimentos_sem_ibge"] == 0
    assert {e["ano"] for e in geral["mercado"]["entradas_por_ano"]} >= {2019, 2021, 2022} and geral["mercado"]["baixas_por_ano"]
    faixas = sorted((base / "published" / T1 / "empresas" / "operadoras").glob("*.json.gz"))
    assert faixas and all(len(f.name.split(".")[0]) == 2 for f in faixas)
    docs = {r: d for f in faixas for r, d in load_gz(base, T1, f"empresas/operadoras/{f.name}")["operadoras"].items()}
    assert len(docs) == geral["resumo"]["operadoras_com_cadastro"]
    um = next(iter(docs.values()))
    assert um["matriz"]["ibge"] == "3205309" and {"3205309", "3205200"} <= {p["ibge"] for p in um["presenca"]}      # Vitória e Vila Velha casam com o IBGE por nome e UF
    assert any(p["acessos_fixo"] > 0 for d in docs.values() for p in d["presenca"])                              # e a presença traz também os municípios com acessos no SICI
    texto = json.dumps(docs, ensure_ascii=False) + json.dumps({k: v for k, v in geral.items() if k != "limites"}, ensure_ascii=False)      # `limites` cita o que NÃO entra
    for proibido in ("@", "logradouro", "telefone", "cep"):
        assert proibido not in texto.lower()


def test_financiamento_e_sancoes_por_operadora(pipeline):
    """BNDES e CEIS/CNEP por raiz de CNPJ, com a vigência calculada pela data do snapshot e sem pessoa física."""
    base, _ = pipeline
    doc = load_gz(base, T1, "financiamento/operadoras.json.gz")
    assert doc["natureza"] == "registro_de_fonte_oficial" and "não têm relação" in doc["limites"]
    r = doc["resumo"]
    assert r["operadoras_com_financiamento"] == 2 and r["operadoras_com_sancao"] == 3 and r["operadoras_com_sancao_vigente"] == 2 and r["bndes_presente"] and r["cgu_presente"]
    ops = doc["operadoras"]
    primeira = next(d for d in ops.values() if len(d.get("financiamento", {}).get("operacoes", [])) == 2)       # matriz e filial agrupadas na mesma raiz
    assert primeira["financiamento"]["contratado_total"] == 2300000.5 and primeira["financiamento"]["por_ano"][0]["ano"] == "2022"
    assert primeira["sancoes"]["vigentes"][0]["sem_prazo"] is True and primeira["sancoes"]["vigentes"][0]["fim"] is None
    segunda = next(d for d in ops.values() if len(d.get("sancoes", {}).get("encerradas", [])) == 1)
    assert segunda["sancoes"]["vigentes"][0]["cadastro"] == "CNEP" and segunda["sancoes"]["vigentes"][0]["multa"] == 36680.49
    terceira = next(d for d in ops.values() if "financiamento" not in d)
    assert not terceira["sancoes"]["vigentes"] and terceira["sancoes"]["futuras"][0]["situacao"] == "futura"


def test_exposicao_por_asn_e_uf_so_contagens_e_ausencia_nao_e_zero(pipeline):
    """Serviços do Shodan por ASN com a data da leitura, classes de risco, CVEs só com a faceta e agregado derivado por UF; sem lista de IPs."""
    import json

    base, _ = pipeline
    doc = load_gz(base, T1, "exposicao/asns.json.gz")
    assert "Shodan" in doc["fonte"]["atribuicao"] and "NÃO é prova de vulnerabilidade" in doc["aviso"] and doc["plano"]["facetas"]["vuln"] == "ok"
    br = sorted(int(a) for a in doc["asns"])
    x = doc["asns"][str(br[0])]
    assert x["lido_em"] == T1 and x["servicos_observados"] == 400 and x["risco"]["servicos_de_risco"] == 51 and x["risco"]["pct_dos_servicos_observados"] == 12.75
    assert x["risco"]["classes"]["acesso_remoto"]["total"] == 42 and [s["servico"] for s in x["risco"]["classes"]["acesso_remoto"]["servicos"]] == ["Telnet", "RDP"]
    assert x["risco"]["classes"]["gestao_de_equipamento"]["servicos"] == [{"porta": 7547, "servico": "TR-069 (CWMP)", "n": 9}]
    assert x["vulnerabilidades"] == {"disponivel": True, "cves_mais_vistas": [{"cve": "CVE-2099-0001", "n": 12}, {"cve": "CVE-2099-0002", "n": 5}]}
    assert doc["asns"][str(br[1])] == {"lido_em": T1, "servicos_observados": 0, "sem_servico_observado": True}                  # zero observado é dado, e diz o que é
    assert doc["asns"][str(br[2])]["risco"]["servicos_de_risco"] == 0 and doc["asns"][str(br[2])]["risco"]["classes"] == {}
    assert "64999" not in doc["asns"] and len(doc["asns"]) == 3 and doc["cobertura"]["asns_com_leitura"] == 3 and doc["cobertura"]["asns_com_servicos_observados"] == 2
    assert all(u["derivado"] is True for u in doc["por_uf"].values()) and doc["por_uf"]
    assert sum(u["servicos_de_risco"] for u in doc["por_uf"].values()) == 51
    texto = json.dumps(doc)
    assert "matches" not in texto and "ip_str" not in texto                                                                  # nunca host individual


def test_radar_por_asn_e_uf_ausencia_nao_e_zero(pipeline):
    """IPv6 com a data da leitura, tráfego e velocidade só dos ASNs de topo, papéis de BGP e agregado derivado por UF."""
    base, _ = pipeline
    doc = load_gz(base, T1, "radar/asns.json.gz")
    assert doc["licenca"] == "CC BY-NC 4.0" and "Cloudflare Radar" in doc["fonte"]["atribuicao"] and "não quer dizer zero" in doc["aviso"]
    br = sorted(int(a) for a in doc["asns"])
    a1 = str(br[0])
    x = doc["asns"][a1]
    assert x["ipv6"] == {"pct": 55.5, "em": T1} and x["trafego_pct_do_brasil"] == 8.0 and x["velocidade"]["testes"] == 321
    assert x["bgp"] == {"vazou": 1, "vitima_de_sequestro": 1}
    segundo = doc["asns"][str(br[1])]
    assert segundo["ipv6"]["pct"] == 0.0 and segundo["bgp"] == {"no_caminho_de_vazamento": 1, "sequestrou": 1}      # zero medido é dado
    assert "64999" not in doc["asns"] and "64998" not in doc["asns"]                                                    # ASN estrangeiro não entra
    sem_dado = [a for a, v in doc["asns"].items() if "ipv6" not in v]
    assert all("ipv6" not in doc["asns"][a] for a in sem_dado)                                                          # ASN sem leitura ou sem dado não tem ipv6 (nem zero)
    assert not any("velocidade" in v and v["velocidade"]["testes"] < 30 for v in doc["asns"].values())                  # abaixo do mínimo de testes não é publicado
    c = doc["cobertura"]
    assert c["asns_com_dado_ipv6"] == 2 and c["asns_com_leitura_ipv6"] == 3 and c["asns_no_topo_de_trafego"] == 1 and c["asns_com_velocidade"] == 1
    assert doc["quedas"]["anomalias"] == 0 and doc["quedas"]["consultado"] is True
    assert all(u["derivado"] is True for u in doc["por_uf"].values()) and doc["por_uf"]


def test_contratos_publicos_por_operadora_municipio_e_resumo(pipeline):
    """Valor sem itens cancelados, ausência com data (não zero), esfera só do que foi detalhado, município do órgão e cobertura do rodízio."""
    base, _ = pipeline
    ops_doc = load_gz(base, T1, "contratos/operadoras.json.gz")
    assert ops_doc["licenca"].startswith("dados abertos (Lei 12.527/2011") and "não é, por si" in ops_doc["aviso"] and "filial" in ops_doc["limites"]
    ops = ops_doc["operadoras"]
    primeira = next(d for d in ops.values() if d.get("resultado") == "com_resultado" and d["itens"] == 3)
    assert primeira["itens_cancelados"] == 1 and primeira["contratacoes"] == 3 and primeira["valor_homologado"] == 255500.25      # o item cancelado (99,90) não entra
    assert [e["esfera"] for e in primeira["por_esfera"]] == ["federal", "municipal"] and primeira["por_esfera"][0]["valor"] == 251500.0
    assert [a["ano"] for a in primeira["por_ano"]] == ["2025", "2026"] and primeira["recentes"][0]["data"] == "2026-08-03" and primeira["recentes"][0]["municipio"] == "Tupãnópolis"
    assert primeira["contratacoes_detalhadas"] == 3 and primeira["lida_em"] == T1 and primeira["idade_dias"] == 0
    sem_detalhe = next(d for d in ops.values() if d.get("resultado") == "com_resultado" and d["itens"] == 1)
    assert sem_detalhe["por_esfera"] == [{"esfera": "nao_detalhada", "itens": 1, "contratacoes": 1, "valor": 777.0}] and sem_detalhe["contratacoes_detalhadas"] == 0
    assert sem_detalhe["recentes"][0]["municipio"] == "Guaraniópolis" and sem_detalhe["recentes"][0]["orgao"] == "UNIDADE SINTETICA 3" and sem_detalhe["recentes"][0]["orgao_detalhado"] is False
    vazia = [d for d in ops.values() if d.get("resultado") == "sem_resultado_na_consulta"]
    assert len(vazia) == 2 and all(d["itens"] == 0 and d["lida_em"] for d in vazia)                                  # lida e sem resultado: dito, com a data
    assert any(d["faixa"] == "B" and d["idade_dias"] == 30 for d in vazia)
    muns = load_gz(base, T1, "contratos/municipios.json.gz")["municipios"]
    assert set(muns) == {"9900001", "9900002", "9900003"} and muns["9900001"]["contratacoes"] == 2 and muns["9900001"]["valor"] == 251500.0
    assert muns["9900001"]["fornecedores"][0]["itens"] == 2
    resumo = load_gz(base, T1, "contratos/resumo.json.gz")
    c = resumo["cobertura"]
    assert c["raizes_com_leitura"] == 4 and c["raizes_com_resultado"] == 2 and c["raizes_sem_leitura"] == c["raizes_no_universo"] - 4 and c["raizes_sem_leitura"] > 0
    assert c["contratacoes"] == 4 and c["contratacoes_com_detalhe"] == 3 and c["contratacoes_com_municipio"] == 4
    assert "ranking" not in json.dumps(resumo).lower() and resumo["valor_homologado"] == 256277.25
