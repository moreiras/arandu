# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Pré-carga do MCP (mcp_server/precarga.py): cobre as tools, os PTTs e as UFs da data mais recente e sobrevive a erro de tool."""
from mcp_server import precarga


class _Store:
    def resolve_date(self, d):
        return d or "2026-11-13"

    def ixp_index(self, d):
        return [{"code": "sp"}, {"code": "rj"}, {"sem": "code"}]


def test_chamadas_cobrem_ptts_ufs_e_so_a_data_pedida():
    cs = precarga.chamadas("2026-11-13", ["sp"])
    nomes = {n for n, _ in cs}
    assert {"ixp_detalhe", "ixp_potencial", "ixp_assinantes", "viz", "uf_detalhe", "asn_lista"} <= nomes
    assert ("viz", {"kind": "ixp_geo", "layer": "prefixes_v4", "code": "sp", "date": "2026-11-13"}) in cs
    assert all(a.get("date") in (None, "2026-11-13") for _, a in cs)
    assert not any(n.startswith("historico") for n in nomes)             # leem várias datas: ficam de fora


def test_precarregar_usa_as_funcoes_dadas_e_ignora_falhas():
    vistos = []

    def ok(**kw):
        vistos.append(kw)

    def falha(**kw):
        raise ValueError("PTT sem portas")
    funcoes = {n: ok for n, _ in precarga.chamadas("x", ["sp"])}
    funcoes["ixp_potencial"] = falha
    r = precarga.precarregar(funcoes, _Store())
    assert r["ptts"] == 2 and r["falhas"] == 2 and r["chamadas"] == len(vistos) > 0
    assert any(v.get("code") == "rj" for v in vistos)


def test_desligada_nao_inicia(monkeypatch):
    monkeypatch.setenv("MCP_PRECARGA", "0")
    assert precarga.iniciar({}, _Store()) is None


def test_app_guarda_as_funcoes_originais_antes_da_previa():
    from mcp_server import app
    assert set(app._funcoes_originais) >= {"ixp_detalhe", "viz", "asn_detalhe"}
    assert not getattr(app._funcoes_originais["viz"], "_previa", False)


def test_nomes_chamados_existem_entre_as_tools_registradas():
    """A pré-carga pula em silêncio um nome que não existe: tool renomeada sem atualizar a lista voltaria a ficar fria sem aviso."""
    from mcp_server import app
    nomes = {n for n, _ in precarga.chamadas("2026-11-13", ["sp"])}
    assert nomes - set(app._funcoes_originais) == set()


def test_acompanhar_repete_a_cada_snapshot_novo(monkeypatch):
    import threading
    monkeypatch.setenv("MCP_PRECARGA", "1")
    monkeypatch.setenv("MCP_PRECARGA_PAUSA_S", "0")
    datas = iter(["2026-11-13", "2026-11-13", "2026-11-14", "2026-11-14"])
    parar = threading.Event()
    feitas = []

    class _S(_Store):
        def resolve_date(self, d):
            try:
                return next(datas)
            except StopIteration:
                parar.set()
                return "2026-11-14"

    monkeypatch.setattr(precarga, "precarregar", lambda funcoes, store, data=None: feitas.append(data))
    precarga.acompanhar({}, _S(), intervalo=0, parar=parar)
    assert feitas == ["2026-11-13", "2026-11-14"]                         # uma vez por data, não a cada volta
