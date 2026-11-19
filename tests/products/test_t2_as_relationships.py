# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T2 — produto `as_relationships` sobre o dataset sintético: rampa dos route servers + coletores com VP + ASPA + CAIDA."""
import dataclasses
import json
import shutil

import pytest

from core.common import configure_logging, read_json_gz, write_json_gz
from products.as_relationships import build, config as cf, refino
from tests.synth.world import T1, build_world

CFG = dataclasses.replace(cf.carregar(), descartar_asn=((0, 0), (23456, 23456)))     # o sintético usa 4,2 bilhões como "trânsito"


@pytest.fixture(scope="module")
def saida(pipeline, tmp_path_factory):
    base0, _ = pipeline
    base = tmp_path_factory.mktemp("rel") / "data"
    shutil.copytree(base0, base)                                         # o publicado do pipeline é compartilhado: escreve numa cópia
    world = build_world(T1, 1, 0)
    # CAIDA sintético: acerta os trânsitos (p2c) e erra um acesso (diz que 64500 e o trânsito são pares)
    p2c = [[t, a] for a, t in world.transit_of.items() if a != 64500]
    write_json_gz(base / "normalized" / T1 / "summary" / "caida_asrel.json.gz",
                  {"snapshot_date": T1, "as_of": "2026-09-01", "p2c": p2c, "p2p": [[min(64500, world.transit_of[64500]), max(64500, world.transit_of[64500])]]})
    assert build.run(T1, base, configure_logging(), cfg=CFG)
    doc = read_json_gz(base / "published" / T1 / "as_relationships.json.gz")
    return doc, world


def _por(doc):
    return {(r["a"], r["b"]) if r["tipo"] == "p2c" else (min(r["a"], r["b"]), max(r["a"], r["b"])): r for r in doc["relacoes"]}


def test_estrutura_do_documento(saida):
    doc, _ = saida
    assert doc["snapshot_date"] == T1 and doc["algoritmo"] == "ARC v2"
    assert doc["entradas"]["coletores"]["v4"] == ["rvT"] and doc["entradas"]["caida_as_of"] == "2026-09-01"
    assert doc["entradas"]["aspa_objetos"] == 1 and len(doc["clique"]["v4"]) == 3
    assert doc["diagnostico"]["v4"]["col_descartados"] == 1             # o caminho com laço
    for r in doc["relacoes"]:
        assert set(r) >= {"a", "b", "tipo", "p", "nivel", "afi", "evid", "n_vps", "n_ptt", "visto_em"}
        assert r["tipo"] in ("p2c", "p2p", "s2s", "sem_classificacao") and 0 < r["p"] <= 1
        assert r["visto_em"] == T1


def test_hierarquia_plantada_e_recuperada_com_nivel_alto(saida):
    doc, world = saida
    por = _por(doc)
    esperados = [(t, a) for a, t in world.transit_of.items() if (t, a) in por]
    assert len(esperados) >= 20
    # o acesso em que o CAIDA erra (diz par) é o custo conhecido do rebaixo por estrato: CAIDA contra e sem tripla forte (poucos votos no sintético) = `sem_evidencia` ou `conflito` → "possível"
    contestado = (world.transit_of[64500], 64500)
    ruim = [(par, por[par]["nivel"]) for par in esperados if par != contestado and por[par]["nivel"] not in ("declarado", "confirmado", "provavel")]
    assert not ruim, ruim
    assert por[contestado]["estrato"] in ("conflito", "sem_evidencia") and por[contestado]["nivel"] == "possivel"
    assert por[contestado]["evid"]["refino"]["rebaixado_por_estrato"] == por[contestado]["estrato"]
    # a rampa dos route servers e os coletores concordam: ao menos um elo confirmado (duas fontes independentes)
    assert any(por[par]["nivel"] in ("declarado", "confirmado") for par in esperados)


def test_aspa_declarado_e_caida_discorda_no_acesso_plantado(saida):
    doc, world = saida
    por = _por(doc)
    t = world.transit_of[64496]
    assert por[(t, 64496)]["nivel"] == "declarado" and por[(t, 64496)]["evid"].get("aspa") or por[(t, 64496)]["evid"]["v4"]["aspa"]
    # o CAIDA sintético diz par para 64500; a rampa/coletores mandam: continua provedor-cliente
    t5 = world.transit_of[64500]
    r = por.get((t5, 64500))
    assert r is not None and r["tipo"] == "p2c"


def test_clique_detectado_e_ninguem_acima(saida):
    doc, world = saida
    foreign = sorted(a.asn for a in world.ases.values() if a.role == "foreign")
    assert doc["clique"]["v4"] == foreign[10:13]                          # os 3 ASNs plantados, nada mais
    clique = set(doc["clique"]["v4"])
    assert not any(r["tipo"] == "p2c" and r["b"] in clique for r in doc["relacoes"])


def test_so_elos_com_asn_brasileiro(saida):
    doc, world = saida
    br = {a.asn for a in world.ases.values() if a.is_br}
    assert all(r["a"] in br or r["b"] in br for r in doc["relacoes"])


def test_sem_registro_br_falha_alto(tmp_path):
    assert build.run(T1, tmp_path, configure_logging(), cfg=CFG) is False


def test_resumo_confere_com_as_linhas(saida):
    doc, _ = saida
    from collections import Counter

    assert doc["resumo"] == dict(sorted(Counter(f"{r['tipo']}/{r['nivel']}" for r in doc["relacoes"]).items()))


def test_contrato_t3_do_documento(saida):
    from tests.products.test_t3_schemas import errors, validator

    doc, _ = saida
    assert errors(validator("as_relationships"), doc, "as_relationships.json.gz") == []


def test_regua_roda_no_sintetico_sem_usar_o_aspa_como_entrada(pipeline, tmp_path_factory, monkeypatch):
    from products.as_relationships import validacao

    base0, _ = pipeline
    base = tmp_path_factory.mktemp("regua") / "data"
    shutil.copytree(base0, base)
    world = build_world(T1, 1, 0)
    # ASPA de verdade para vários clientes: o algoritmo (sem ASPA) tem de recuperá-los pela rampa e pelos coletores
    aspa = [{"customer": a, "providers": [t], "tal": "lacnic"} for a, t in sorted(world.transit_of.items())[:12]]
    (base / "published" / T1 / "rpki").mkdir(parents=True, exist_ok=True)
    write_json_gz(base / "published" / T1 / "rpki" / "aspa_list.json.gz", aspa)
    r = validacao.rodar(base, T1, configure_logging(), cfg=CFG, ptts=2, coletores=1)
    v4 = r["v4"]
    assert r["aspa_objetos"] == 12 and v4["coletores"] == ["rvT"] and len(v4["clique"]) == 3
    assert v4["aspa"]["br"]["ate_possivel"]["recall"] == 1.0 and v4["aspa"]["br"]["ate_provavel"]["precisao"] >= 0.75
    assert [f["p_de"] for f in v4["calibracao"]] == [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
    assert set(v4["subconjuntos"]) == {"vp_adjacente", "poucos_vps", "stub_clique", "sem_cobertura"}
    assert set(v4["sem_ptt"]) == set(list(v4["sem_ptt"])[:2]) and len(v4["sem_ptt"]) == 2
    assert v4["sem_coletor"] == {}                                     # um coletor só: não há o que retirar
    assert r["estabilidade_entre_snapshots"]["estado"] == "indisponivel"
    v2 = v4["v2"]                                                       # ARC v2 sobre a mesma execução sem ASPA
    assert v2["aspa"]["br"]["ate_possivel"]["recall"] >= 0.9 and v2["treino"] > 0 and v2["iteracoes"]
    assert set(v2["ablacao_br_provavel"]) == set(refino.CARACTERISTICAS) and "cobertura_politica" in v2
    assert v2["calibracao_nb"].get("estado") == "indisponivel" or v2["calibracao_nb"]["temperatura_otima"] > 0
    assert (base / "ops" / "relacoes" / f"{T1}.json").exists()


def test_painel_mostra_a_regua(pipeline, tmp_path_factory):
    import importlib.util
    from pathlib import Path

    from products.as_relationships import validacao

    base0, _ = pipeline
    base = tmp_path_factory.mktemp("painel") / "data"
    shutil.copytree(base0, base)
    world = build_world(T1, 1, 0)
    (base / "published" / T1 / "rpki").mkdir(parents=True, exist_ok=True)
    write_json_gz(base / "published" / T1 / "rpki" / "aspa_list.json.gz",
                  [{"customer": a, "providers": [t]} for a, t in sorted(world.transit_of.items())[:6]])
    validacao.rodar(base, T1, configure_logging(), cfg=CFG, ptts=1, coletores=0)
    import dataclasses
    referencia = (base / "ops" / "relacoes" / f"{T1}.json").read_text()
    validacao.rodar(base, T1, configure_logging(), cfg=dataclasses.replace(CFG, refino=dataclasses.replace(CFG.refino, irr=True)), ptts=0, coletores=0)
    assert (base / "ops" / "relacoes" / f"{T1}.irr.json").exists()           # `--irr` não sobrescreve o relatório de referência
    assert (base / "ops" / "relacoes" / f"{T1}.json").read_text() == referencia
    spec = importlib.util.spec_from_file_location("scorecard", Path(__file__).resolve().parents[2] / "scripts" / "scorecard.py")
    sc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sc)
    secao = sc.secao_relacoes(base)
    assert secao["snapshot_date"] == T1
    md = sc._md_relacoes(secao)
    texto = "\n".join(md)
    assert "Relações entre ASNs" in texto and "Calibração" in texto and "Subconjuntos difíceis" in texto and "stub_clique" in texto
    assert sc.secao_relacoes(base / "inexistente")["estado"] == "indisponivel"


def test_caminhos_dos_coletores_recuam_para_a_coleta_semanal_anterior(pipeline, tmp_path_factory):
    """Nos dias em que a coleta dos RIBs não rodou (cadência semanal) o produto usa os caminhos da última coleta, até 10 dias."""
    base0, _ = pipeline
    base = tmp_path_factory.mktemp("recuo") / "data"
    shutil.copytree(base0, base)
    seguinte = "2026-09-24"                                                   # 4 dias depois de T1, sem aspaths próprios
    for sub in ("normalized", "published"):
        shutil.copytree(base / sub / T1, base / sub / seguinte)
        if sub == "normalized":
            shutil.rmtree(base / sub / seguinte / "summary" / "aspaths-v4")
            shutil.rmtree(base / sub / seguinte / "summary" / "aspaths-v6")
    assert build.run(seguinte, base, configure_logging(), cfg=CFG)
    doc = read_json_gz(base / "published" / seguinte / "as_relationships.json.gz")
    assert doc["entradas"]["coletores"]["v4"] == ["rvT"] and doc["entradas"]["coletores_coletados_em"]["v4"] == T1
    assert len(doc["clique"]["v4"]) == 3
    # velho demais: sem coletores, e o documento diz isso
    antigo = "2026-10-20"
    for sub in ("normalized", "published"):
        shutil.copytree(base / sub / seguinte, base / sub / antigo)
    assert build.run(antigo, base, configure_logging(), cfg=CFG)
    d2 = read_json_gz(base / "published" / antigo / "as_relationships.json.gz")
    assert d2["entradas"]["coletores"]["v4"] == [] and d2["entradas"]["coletores_coletados_em"]["v4"] is None and d2["clique"]["v4"] == []


def test_estratos_no_documento_e_na_linha(saida):
    doc, _ = saida
    e = doc["estratos"]
    assert e["ativo"] and e["rebaixar"] == ["conflito", "sem_evidencia"] and e["p_calibrada"]["ambos/v4"] == 0.9241
    assert sum(e["elos_por_estrato"].values()) == sum(1 for r in doc["relacoes"] if r.get("estrato"))
    for r in doc["relacoes"]:
        assert ("estrato" in r) == (r["tipo"] == "p2c")                  # só p2c tem estrato
        if r.get("estrato") in ("conflito", "sem_evidencia", "so_tripla"):
            assert r["p_calibrada"] is None
        if r["nivel"] == "possivel" and r["evid"].get("refino", {}).get("rebaixado_por_estrato"):
            assert r["estrato"] == r["evid"]["refino"]["rebaixado_por_estrato"]



def test_irr_desligado_nao_muda_o_documento_publicado(saida):
    doc, _ = saida
    assert "irr" not in doc and "politica_rs" in doc       # `refino.irr: false` por padrão


def test_irr_como_caracteristica_liga_pela_chave_e_registra_a_data_e_os_pares(pipeline, tmp_path_factory):
    base0, _ = pipeline
    base = tmp_path_factory.mktemp("irr") / "data"
    shutil.copytree(base0, base)
    world = build_world(T1, 1, 0)
    a, t = sorted(world.transit_of.items())[0]
    pol = {"TC": {str(a): [["in", t, "any"], ["out", t, "proprio"]], str(t): [["in", a, "proprio"], ["out", a, "any"]]}}
    write_json_gz(base / "normalized" / T1 / "summary" / "irr_route_objects.json.gz", {"snapshot_date": T1, "politicas": pol})
    cfg = dataclasses.replace(CFG, refino=dataclasses.replace(CFG.refino, irr=True))
    assert build.run(T1, base, configure_logging(), cfg=cfg)
    doc = read_json_gz(base / "published" / T1 / "as_relationships.json.gz")
    assert doc["irr"] == {"data": T1, "pares_na_referencia": 1}
