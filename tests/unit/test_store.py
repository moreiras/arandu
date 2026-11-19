# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — armazém de versões de fonte: registro, idempotência, revisões, resolução, materialização, índice legado."""
import gzip
import json
from pathlib import Path

import pytest

from core.catalog.loader import load_catalog
from core.store import (arquivos_da_fonte, as_of_do_dado, escrever_indice_legado, indice_legado, listar, materializar,
                        registrar, registrar_da_fonte, resolver, ultima_verificacao)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def cat():
    return load_catalog(ROOT / "catalog")


def _arq(tmp_path, nome, texto):
    p = tmp_path / "ori" / nome
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texto)
    return p


def test_registrar_cria_versao_imutavel_com_meta_e_copia(tmp_path):
    a = _arq(tmp_path, "a.json", "{}")
    v, ev = registrar(tmp_path, "fonte_x", "2026-10-18", {"normalized/summary/a.json": a}, origem="http://x", coletado_em="2026-10-18T05:00:00Z")
    assert ev == "nova" and v.nome == "2026-10-18" and v.revisao == 1 and v.ok
    assert (v.data_dir / "normalized/summary/a.json").read_text() == "{}"
    meta = json.loads((v.caminho / "meta.json").read_text())
    assert meta["hash"] == v.hash and meta["tamanho"] == 2 and meta["arquivos"][0]["caminho"] == "normalized/summary/a.json"
    a.write_text("alterado depois")                                    # a cópia não acompanha o original
    assert (v.data_dir / "normalized/summary/a.json").read_text() == "{}"


def test_mesmo_conteudo_confirma_sem_criar_pasta_e_atualiza_a_ultima_verificacao(tmp_path):
    a = _arq(tmp_path, "a.json", "{}")
    v1, _ = registrar(tmp_path, "f", "2026-10-18", {"n/a": a})
    v2, ev = registrar(tmp_path, "f", "2026-10-18", {"n/a": a})
    assert ev == "confirmada" and v2.nome == v1.nome and len(listar(tmp_path, "f")) == 1
    assert ultima_verificacao(tmp_path, "f") is not None
    eventos = [json.loads(l)["evento"] for l in (tmp_path / "sources/f/_log.jsonl").read_text().splitlines()]
    assert eventos == ["nova", "confirmada"]


def test_conteudo_diferente_na_mesma_as_of_vira_revisao_e_a_antiga_nao_muda(tmp_path):
    a = _arq(tmp_path, "a.json", "um")
    v1, _ = registrar(tmp_path, "f", "2026-10-18", {"n/a": a})
    a.write_text("dois")
    v2, ev = registrar(tmp_path, "f", "2026-10-18", {"n/a": a})
    assert ev == "revisao" and v2.nome == "2026-10-18.r2" and v2.revisao == 2
    assert (v1.data_dir / "n/a").read_text() == "um" and (v2.data_dir / "n/a").read_text() == "dois"
    assert [v.nome for v in listar(tmp_path, "f")] == ["2026-10-18", "2026-10-18.r2"]


def test_resolver_devolve_a_ultima_valida_ate_a_data_do_snapshot(tmp_path):
    for dia, txt in (("2026-10-04", "a"), ("2026-10-11", "b"), ("2026-10-18", "c")):
        registrar(tmp_path, "f", dia, {"n/a": _arq(tmp_path, f"{dia}.json", txt)}, coletado_em=f"{dia}T05:00:00Z")
    assert resolver(tmp_path, "f", "2026-10-12").as_of == "2026-10-11"
    assert resolver(tmp_path, "f", "2026-10-18").as_of == "2026-10-18"
    assert resolver(tmp_path, "f", "2026-10-03") is None and resolver(tmp_path, "outra", "2026-10-18") is None


def test_resolver_ignora_versao_invalida(tmp_path):
    registrar(tmp_path, "f", "2026-10-04", {"n/a": _arq(tmp_path, "1", "a")}, coletado_em="2026-10-04T05:00:00Z")
    registrar(tmp_path, "f", "2026-10-11", {"n/a": _arq(tmp_path, "2", "b")}, coletado_em="2026-10-11T05:00:00Z", ok=False)
    assert resolver(tmp_path, "f", "2026-10-18").as_of == "2026-10-04"


def test_as_of_mensal_e_disponibilidade_pela_coleta(tmp_path):
    """SICI: as_of é o mês de referência, mas a versão só existe para snapshots a partir do dia em que foi coletada."""
    registrar(tmp_path, "sici", "2026-08", {"n/a": _arq(tmp_path, "s", "x")}, coletado_em="2026-09-20T05:00:00Z")
    assert resolver(tmp_path, "sici", "2026-09-13") is None
    assert resolver(tmp_path, "sici", "2026-09-27").as_of == "2026-08"


def test_as_of_invalida_e_arquivo_ausente_falham(tmp_path):
    with pytest.raises(ValueError):
        registrar(tmp_path, "f", "ontem", {"n/a": _arq(tmp_path, "a", "x")})
    with pytest.raises(FileNotFoundError):
        registrar(tmp_path, "f", "2026-10-18", {"n/a": tmp_path / "nao_existe"})


def test_nenhuma_pasta_temporaria_sobra_apos_falha(tmp_path, monkeypatch):
    import core.store.versions as vs

    monkeypatch.setattr(vs.os, "rename", lambda *a: (_ for _ in ()).throw(OSError("falha simulada")))
    with pytest.raises(OSError):
        registrar(tmp_path, "f", "2026-10-18", {"n/a": _arq(tmp_path, "a", "x")})
    assert [p.name for p in (tmp_path / "sources" / "f").iterdir()] == []


# ── ponte com o catálogo ───────────────────────────────────────────────────────

def _normalizado(tmp_path, date, nome, conteudo):
    p = tmp_path / "normalized" / date / "summary" / nome
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(conteudo, f)
    return p


def test_registrar_da_fonte_usa_os_arquivos_declarados_no_catalogo(cat, tmp_path):
    _normalizado(tmp_path, "2026-10-18", "registro_br.json.gz", {"asns": []})
    _normalizado(tmp_path, "2026-10-18", "registro_br_diff.json.gz", {"added": []})
    _normalizado(tmp_path, "2026-10-18", "outra_coisa.json.gz", {})
    v, ev = registrar_da_fonte(cat, tmp_path, "registro_br", "2026-10-18")
    assert ev == "nova" and sorted(v.arquivos) == ["normalized/summary/registro_br.json.gz", "normalized/summary/registro_br_diff.json.gz"]
    assert registrar_da_fonte(cat, tmp_path, "lacnic_delegated", "2026-10-18") is None        # sem arquivos
    assert registrar_da_fonte(cat, tmp_path, "curada_cdns", "2026-10-18") is None             # curada não é versionada


def test_armazem_incluir_substitui_o_padrao(cat, tmp_path):
    raw = tmp_path / "raw" / "2026-10-18"
    (raw / "sp").mkdir(parents=True)
    (raw / "sp" / "bgp-v4-sp-2026-10-18.txt").write_text("x" * 100)
    (raw / "collection_manifest.json").write_text("{}")
    assert sorted(arquivos_da_fonte(cat, tmp_path, "lg_ixbr", "2026-10-18")) == ["raw/collection_manifest.json"]   # o bruto grande fica de fora
    (raw / "sp" / "ixbr_members.json").write_text("{}")
    assert sorted(arquivos_da_fonte(cat, tmp_path, "ixbr_api", "2026-10-18")) == ["raw/sp/ixbr_members.json"]


def test_as_of_do_sici_e_dos_socios_vem_do_proprio_arquivo(cat, tmp_path):
    p = _normalizado(tmp_path, "2026-10-18", "sici_acessos.json.gz", {"mes_referencia": "2026-08"})
    assert as_of_do_dado("anatel_sici", {"normalized/summary/sici_acessos.json.gz": p}, "2026-10-18") == "2026-08"
    q = _normalizado(tmp_path, "2026-10-18", "receita_socios.json.gz", {"dump_reference": "2026-09"})
    assert as_of_do_dado("receita_socios", {"normalized/summary/receita_socios.json.gz": q}, "2026-10-18") == "2026-09"
    assert as_of_do_dado("registro_br", {}, "2026-10-18") == "2026-10-18"


def test_materializar_restaura_nos_caminhos_de_sempre_sem_sobrescrever(cat, tmp_path):
    _normalizado(tmp_path, "2026-10-11", "registro_br.json.gz", {"asns": [1]})
    v, _ = registrar_da_fonte(cat, tmp_path, "registro_br", "2026-10-11")
    feitos = materializar(tmp_path, v, "2026-10-18")
    destino = tmp_path / "normalized" / "2026-10-18" / "summary" / "registro_br.json.gz"
    assert feitos == ["normalized/summary/registro_br.json.gz"] and destino.exists()
    destino.write_bytes(b"outro")
    assert materializar(tmp_path, v, "2026-10-18") == [] and destino.read_bytes() == b"outro"
    assert materializar(tmp_path, v, "2026-10-18", sobrescrever=True) and destino.read_bytes() != b"outro"


def test_indice_legado_registra_as_of_inferida_e_nao_altera_nada(cat, tmp_path):
    _normalizado(tmp_path, "2026-10-04", "registro_br.json.gz", {})
    _normalizado(tmp_path, "2026-10-04", "sici_acessos.json.gz", {"mes_referencia": "2026-08"})
    antes = sorted(str(p) for p in tmp_path.rglob("*"))
    idx = indice_legado(cat, tmp_path, "2026-10-04")
    por_id = {f["id"]: f for f in idx["fontes"]}
    assert idx["legado"] is True and por_id["registro_br"]["as_of"] == "2026-10-04" and por_id["anatel_sici"]["as_of"] == "2026-08"
    assert all(f["legado"] for f in idx["fontes"]) and sorted(str(p) for p in tmp_path.rglob("*")) == antes
    destino = escrever_indice_legado(cat, tmp_path, "2026-10-04")
    assert destino == tmp_path / "catalog" / "snapshots" / "2026-10-04.json" and json.loads(destino.read_text())["snapshot"] == "2026-10-04"


def test_execucao_tardia_de_uma_data_vale_para_aquela_data(cat, tmp_path):
    """Pipeline de 2026-10-17 rodado dias depois: a versão é do snapshot 17, mesmo com o relógio em outro dia."""
    _normalizado(tmp_path, "2026-10-17", "registro_br.json.gz", {"asns": []})
    v, _ = registrar_da_fonte(cat, tmp_path, "registro_br", "2026-10-17", coletado_em="2026-10-25T03:00:00Z")
    assert v.disponivel_desde == "2026-10-17" and v.coletado_dia == "2026-10-25"
    assert resolver(tmp_path, "registro_br", "2026-10-17") == v and resolver(tmp_path, "registro_br", "2026-10-16") is None


def _json_gz(tmp_path, nome, dado):
    p = tmp_path / "ori" / nome
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(dado, f)
    return p


def test_campos_volateis_nao_mudam_o_hash_e_a_reexecucao_so_confirma(tmp_path):
    """`generated_at` não muda o hash: senão cada coleta teria hash novo e cada reexecução do dia viraria uma revisão (.r2, .r3…)."""
    a = _json_gz(tmp_path, "a.json.gz", {"generated_at": "2026-10-19T04:00:00Z", "snapshot_date": "2026-10-19", "asns": [1, 2]})
    v1, e1 = registrar(tmp_path, "f", "2026-10-19", {"n/a.json.gz": a})
    b = _json_gz(tmp_path, "b.json.gz", {"generated_at": "2026-10-19T12:00:00Z", "snapshot_date": "2026-10-19", "asns": [1, 2]})
    v2, e2 = registrar(tmp_path, "f", "2026-10-19", {"n/a.json.gz": b})
    assert (e1, e2) == ("nova", "confirmada") and v1.nome == v2.nome and len(listar(tmp_path, "f")) == 1


def test_mudanca_real_de_conteudo_continua_gerando_revisao(tmp_path):
    a = _json_gz(tmp_path, "a.json.gz", {"generated_at": "x", "asns": [1, 2]})
    registrar(tmp_path, "f", "2026-10-19", {"n/a.json.gz": a})
    b = _json_gz(tmp_path, "b.json.gz", {"generated_at": "y", "asns": [1, 2, 3]})
    assert registrar(tmp_path, "f", "2026-10-19", {"n/a.json.gz": b})[1] == "revisao"


def test_fonte_mensal_nao_ganha_revisao_a_cada_coleta_semanal(tmp_path):
    for dia in ("2026-10-05", "2026-10-12", "2026-10-19"):
        p = _json_gz(tmp_path, f"s{dia}.json.gz", {"generated_at": dia, "mes_referencia": "2026-08", "total": 10})
        v, ev = registrar(tmp_path, "sici", "2026-08", {"n/s.json.gz": p}, disponivel_desde=dia)
    assert [x.nome for x in listar(tmp_path, "sici")] == ["2026-08"] and ev == "confirmada"


def test_raw_bgp_ixp_usa_o_bruto_restaurado_de_data_anterior(tmp_path):
    """Coleta diária: o armazém restaura o bruto do LG com a data de origem no nome; o `bgp_ixp` e o resumo do PTT o acham."""
    from core.common import raw_bgp_ixp

    rd = tmp_path / "sp"
    rd.mkdir()
    (rd / "bgp-v4-sp-2026-10-17.txt.gz").write_bytes(b"x")
    (rd / "bgp-v4-sp-2026-10-24.txt.gz").write_bytes(b"x")
    (rd / "bgp-v4-sp-2026-10-30.txt.gz").write_bytes(b"x")          # posterior ao snapshot: ignorado
    assert raw_bgp_ixp(rd, "v4", "sp", "2026-10-25").name == "bgp-v4-sp-2026-10-24.txt.gz"
    assert raw_bgp_ixp(rd, "v4", "sp", "2026-10-24").name == "bgp-v4-sp-2026-10-24.txt.gz"
    assert not raw_bgp_ixp(rd, "v6", "sp", "2026-10-25").exists()
