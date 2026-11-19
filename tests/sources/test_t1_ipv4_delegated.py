# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — eventos do ciclo de vida do IPv4 a partir do `delegated`: três dias sintéticos com mudanças plantadas, sem rede."""
import gzip
import shutil

import pytest

from core import ipv4_eventos as E
from core.ipv4_listas import parse_delegated_ipv4
from sources.ipv4_delegated import enrich as dg


class _Log:
    def info(self, *a, **k): pass
    def warning(self, *a, **k): pass


def _foto(fx, dia):
    return parse_delegated_ipv4(gzip.decompress(fx("ipv4_listas", f"delegated-lacnic-extended-{dia}.gz").read_bytes()).decode())[0]


def _blocos(kv):
    return {f"{i}/{q}": {"cc": cc, "status": st, "data": "20200101", "opaque": op, "inicio": i, "quantidade": q} for (i, q), (cc, st, op) in kv.items()}


def test_diff_classifica_titularidade_recuperacao_liberacao_novo_removido_e_pais(fx):
    ev, c = E.diff(_foto(fx, "20261031"), _foto(fx, "20261101"), "2026-11-01")
    assert {(e["tipo"], e["inicio"]) for e in ev} == {("novo", "198.19.12.0"), ("recuperacao", "198.19.4.0"), ("titularidade", "198.18.0.0")} and c["iguais"] == 3
    t = next(e for e in ev if e["tipo"] == "titularidade")
    assert t["de"]["opaque"] == "org-alfa" and t["para"]["opaque"] == "org-beta" and t["blocos"] == ["198.18.0.0/22"]
    ev2, _ = E.diff(_foto(fx, "20261101"), _foto(fx, "20261102"), "2026-11-02")
    assert {(e["tipo"], e["inicio"]) for e in ev2} == {("liberacao", "198.19.4.0"), ("pais", "198.19.8.0"), ("removido", "198.19.9.0")}


def test_dividir_ou_juntar_blocos_da_mesma_organizacao_nao_e_evento():
    antes = _blocos({("10.0.0.0", 512): ("BR", "allocated", "org-a")})
    depois = _blocos({("10.0.0.0", 256): ("BR", "allocated", "org-a"), ("10.0.1.0", 256): ("BR", "allocated", "org-a")})
    ev, c = E.diff(antes, depois, "2026-01-01")
    assert ev == [] and c["reorganizacoes"] == 2
    ev2, c2 = E.diff(depois, antes, "2026-01-02")
    assert ev2 == [] and c2["reorganizacoes"] == 1
    ev3, _ = E.diff(antes, _blocos({("10.0.0.0", 256): ("BR", "allocated", "org-b"), ("10.0.1.0", 256): ("BR", "allocated", "org-a")}), "2026-01-03")
    assert [(e["tipo"], e["inicio"]) for e in ev3] == [("titularidade", "10.0.0.0")]                   # só a metade que mudou de dono


def test_operacao_agrupa_lote_da_mesma_data_e_par_de_organizacoes():
    mk = lambda i: {"data": "2026-01-01", "tipo": "titularidade", "quantidade": 256, "blocos": [f"10.0.{i}.0/24"], "de": {"opaque": "a", "cc": "BR"}, "para": {"opaque": "b", "cc": "BR"}}      # noqa: E731
    ops = E.operacoes([mk(0), mk(1), mk(2), {**mk(9), "para": {"opaque": "c", "cc": "BR"}}])
    assert len(ops) == 2 and sorted(o["registros"] for o in ops) == [1, 3] and max(o["enderecos"] for o in ops) == 768


@pytest.fixture
def base(fx, tmp_path, monkeypatch):
    monkeypatch.setattr(dg, "MINIMO_BLOCOS", 1)
    for dia in ("20261031", "20261101", "20261102"):
        destino = tmp_path / "historico" / "lacnic" / "delegated-extended" / dia[:4]
        destino.mkdir(parents=True, exist_ok=True)
        shutil.copy(fx("ipv4_listas", f"delegated-lacnic-extended-{dia}.gz"), destino / f"delegated-lacnic-extended-{dia}.gz")
    return tmp_path


def test_processar_grava_eventos_estado_e_e_idempotente_e_retomavel(base):
    r = dg.processar(base, "2026-11-01", _Log(), desde="2026-10-31")
    assert r["fotos"] == 2 and r["eventos"] == 3 and r["ultima_foto"] == "2026-11-01"           # a primeira foto é só a linha de base
    r2 = dg.processar(base, "2026-11-02", _Log())                                              # retoma do estado
    assert r2["fotos"] == 1 and r2["eventos"] == 3
    ev = dg.ler_eventos_mes(base, "2026-11")
    assert len(ev) == 6 and {e["data"] for e in ev} == {"2026-11-01", "2026-11-02"}
    r3 = dg.processar(base, "2026-11-02", _Log())                                              # nada novo
    assert r3["fotos"] == 0 and len(dg.ler_eventos_mes(base, "2026-11")) == 6
    z = dg.processar(base, "2026-11-02", _Log(), desde="2026-10-31", zerar=True)                # reprocessar do zero dá o mesmo
    assert z["eventos"] == 6 and len(dg.ler_eventos_mes(base, "2026-11")) == 6


def test_dia_sem_arquivo_vira_lacuna_e_o_evento_seguinte_diz_entre_que_fotos_foi_visto(base):
    (base / "historico" / "lacnic" / "delegated-extended" / "2026" / "delegated-lacnic-extended-20261101.gz").unlink()
    r = dg.processar(base, "2026-11-02", _Log(), desde="2026-10-31")
    assert r["lacunas"] == ["2026-11-01"] and r["fotos"] == 2
    assert all(e["visto_entre"] == ["2026-10-31", "2026-11-02"] for e in dg.ler_eventos_mes(base, "2026-11"))


def test_raw_do_dia_serve_quando_nao_ha_historico(base, fx):
    (base / "historico" / "lacnic" / "delegated-extended" / "2026" / "delegated-lacnic-extended-20261102.gz").unlink()
    raw = base / "raw" / "2026-11-02" / "summary"
    raw.mkdir(parents=True)
    shutil.copy(fx("ipv4_listas", "delegated-lacnic-extended-20261102.gz"), raw / "delegated-lacnic-extended-2026-11-02.txt.gz")
    assert dg.arquivo_do_dia(base, "2026-11-02").name == "delegated-lacnic-extended-2026-11-02.txt.gz" and dg.processar(base, "2026-11-02", _Log(), desde="2026-10-31")["fotos"] == 3


def test_arquivo_truncado_falha_alto(base, monkeypatch):
    monkeypatch.setattr(dg, "MINIMO_BLOCOS", 100)
    with pytest.raises(RuntimeError, match="esperado ≥"):
        dg.processar(base, "2026-11-02", _Log(), desde="2026-10-31")


def test_run_grava_resumo_com_status_brasil_e_eventos_recentes_e_validacao_cruzada(base, fx):
    from core.common import read_json_gz
    r = dg.run("2026-11-02", base, _Log(), desde="2026-10-31", validar=True)
    doc = read_json_gz(base / "normalized" / "2026-11-02" / "summary" / "ipv4_delegated.json.gz")
    assert doc["ultima_foto"] == "2026-11-02" and doc["eventos_por_tipo"]["titularidade"] == 1 and doc["por_status"]["allocated"]["br_blocos"] >= 3 and r["fotos"] == 3
    assert doc["validacao_cruzada"] is None                                                    # sem ipv4_listas normalizado, não há com o que cruzar
