# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Resumo de mudanças do histórico com os filtros (UF-E7)."""
from api.services import historico as h

# ── UF-E7: o resumo do histórico respeita uf, tipo e asn ──

class _Repo:
    def __init__(self, eventos):
        self._ev = eventos

    def datas(self):
        return ["2026-11-15", "2026-11-22"]

    def eventos(self, d):
        return [e for e in self._ev if e["data"] == d]


def test_resumo_de_mudancas_aplica_os_filtros():
    ev = [{"data": "2026-11-22", "tipo": "asn_novo", "estado": "confirmado", "uf": "AM", "asn": 1, "entidade": "asn", "chave": "1"},
          {"data": "2026-11-22", "tipo": "asn_novo", "estado": "pendente", "uf": "SP", "asn": 2, "entidade": "asn", "chave": "2"},
          {"data": "2026-11-22", "tipo": "ixp_entrada", "estado": "confirmado", "uf": "AM", "asn": 3, "entidade": "asn", "chave": "3"}]
    repo = _Repo(ev)
    assert h.mudancas_resumo(repo, "2026-11-15")["total"] == 3
    r = h.mudancas_resumo(repo, "2026-11-15", uf="am")
    assert r["total"] == 2 and r["filtros"] == {"uf": "AM"}
    assert r["total"] == h.mudancas(repo, "2026-11-15", uf="AM", estado="todos")["total"]
    assert h.mudancas_resumo(repo, "2026-11-15", tipo="asn_novo", uf="AM")["total"] == 1
    assert h.mudancas_resumo(repo, "2026-11-15", asn=2)["por_tipo"] == {"asn_novo": {"confirmado": 0, "pendente": 1, "revertido": 0}}


def test_tool_mcp_repassa_os_filtros_ao_resumo(monkeypatch):
    from mcp_server import tools_historico as t
    visto = {}
    monkeypatch.setattr(t, "_chama", lambda fn, *a: visto.setdefault("args", (fn.__name__, a)))
    fn = getattr(t.historico_mudancas, "fn", t.historico_mudancas)          # o decorador do MCP pode embrulhar a função
    fn(de="2026-11-15", uf="AM", tipo="asn_novo", asn=5, resumo=True)
    assert visto["args"] == ("mudancas_resumo", ("2026-11-15", None, "asn_novo", "AM", 5))
