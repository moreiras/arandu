# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — fragmentos e `compose` do documento de ASN."""
import json

import pytest

from core import compose

D = "2026-10-23"


def _frag(base, produto, itens):
    with compose.gravar_fragmento(base, D, produto) as w:
        for asn, campos in itens:
            w.escrever(asn, campos)


def _doc(base, asn):
    return json.loads((base / "published" / D / "asns" / f"{asn}.json").read_text(encoding="utf-8"))


def test_compose_junta_os_produtos_na_ordem_e_escreve_cada_documento_uma_vez(tmp_path):
    _frag(tmp_path, "base", [(64500, {"asn": 64500, "name": "A", "is_br": True}), (64501, {"asn": 64501, "name": "B"})])
    _frag(tmp_path, "ixp_paths", [(64500, {"ixp_paths": {"sp": [[1, 2]]}})])
    _frag(tmp_path, "sici", [(64500, {"sici": {"acessos": 10}}), (64999, {"sici": {"acessos": 1}})])     # 64999 não tem base
    _frag(tmp_path, "saude", [(64500, {"alerts": [], "name": "A2"})])                                       # substitui a chave
    r = compose.compor_asns(tmp_path, D)
    assert r == {"docs": 2, "produtos": ["base", "ixp_paths", "sici", "saude"]}
    d = _doc(tmp_path, 64500)
    assert list(d) == ["asn", "name", "is_br", "ixp_paths", "sici", "alerts"]      # ordem de inserção = a do fluxo antigo
    assert d["name"] == "A2" and d["sici"] == {"acessos": 10}
    assert set(_doc(tmp_path, 64501)) == {"asn", "name"}
    assert not (tmp_path / "published" / D / "asns" / "64999.json").exists()


def test_fragmento_exige_ordem_crescente_e_so_aparece_se_fechar_sem_erro(tmp_path):
    with pytest.raises(ValueError, match="fora de ordem"):
        _frag(tmp_path, "base", [(2, {}), (1, {})])
    assert not compose.caminho(tmp_path, D, "base").exists()


def test_fragmento_e_deterministico(tmp_path):
    import time
    _frag(tmp_path, "base", [(1, {"a": 1})])
    a = compose.caminho(tmp_path, D, "base").read_bytes()
    time.sleep(1.1)
    _frag(tmp_path, "base", [(1, {"a": 1})])
    assert compose.caminho(tmp_path, D, "base").read_bytes() == a


def test_sem_base_falha_alto(tmp_path):
    _frag(tmp_path, "sici", [(1, {"sici": {}})])
    with pytest.raises(FileNotFoundError, match="base"):
        compose.compor_asns(tmp_path, D)


def test_flag_do_compose(monkeypatch):
    monkeypatch.delenv("ARANDU_COMPOSE", raising=False)
    assert compose.ativo() is True                       # padrão: ligado
    monkeypatch.setenv("ARANDU_COMPOSE", "off")
    assert compose.ativo() is False
    monkeypatch.setenv("ARANDU_COMPOSE", "on")
    assert compose.ativo() is True


def test_snapshot_sem_fragmento_base_segue_o_fluxo_antigo_mesmo_com_a_flag(tmp_path, monkeypatch):
    monkeypatch.setenv("ARANDU_COMPOSE", "on")
    assert compose.fluxo_novo(tmp_path, D) is False                  # data feita sem a flag: não há base
    _frag(tmp_path, "base", [(1, {"asn": 1})])
    assert compose.fluxo_novo(tmp_path, D) is True
    monkeypatch.setenv("ARANDU_COMPOSE", "off")
    assert compose.fluxo_novo(tmp_path, D) is False


def test_regravar_o_base_invalida_os_fragmentos_derivados(tmp_path):
    _frag(tmp_path, "base", [(1, {"asn": 1})])
    _frag(tmp_path, "sici", [(1, {"sici": {}})])
    _frag(tmp_path, "base", [(1, {"asn": 1, "novo": True})])
    assert compose.caminho(tmp_path, D, "base").is_file() and not compose.caminho(tmp_path, D, "sici").exists()


def test_drill_um_bloco_novo_no_asn_e_so_um_produto_novo(tmp_path, monkeypatch):
    """Meta: um bloco novo no documento do ASN exige apenas um produto novo (um fragmento + o nome na ordem)."""
    monkeypatch.setattr(compose, "PRODUTOS_ASN", compose.PRODUTOS_ASN + ("peeringdb_contatos",))
    _frag(tmp_path, "base", [(64500, {"asn": 64500})])
    _frag(tmp_path, "saude", [(64500, {"alerts": []})])
    _frag(tmp_path, "peeringdb_contatos", [(64500, {"contatos_resumo": {"total": 2}})])
    compose.recompor(tmp_path, D)
    d = _doc(tmp_path, 64500)
    assert list(d) == ["asn", "alerts", "contatos_resumo"] and d["contatos_resumo"] == {"total": 2}


def test_retencao_inclui_o_build_com_piso_de_duas_datas(tmp_path):
    from arandu import retencao
    for dd in ("2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"):
        (tmp_path / "build" / dd / "fragments" / "asn").mkdir(parents=True)
    perfil = retencao.carregar(__import__("pathlib").Path(__file__).resolve().parents[2] / "catalog" / "retencao.yaml", "desenvolvimento")
    p = retencao.plano(tmp_path, "2026-10-23", perfil)
    assert {i["item"] for i in p["itens"] if i["camada"] == "build"} == {"2026-10-20", "2026-10-21"}
