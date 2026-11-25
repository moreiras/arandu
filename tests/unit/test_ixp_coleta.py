# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — estado da coleta do PTT por família (IXP-E1, IXP-E2, IXPS-E4): o looking glass que responde "0 exist" em IPv6 não é "ok" com 0%."""
import json

from core import ixp_coleta as ic
from core.common import raw_path
from products.ixp_docs.build import publicar_ixp_index

D = "2026-11-22"
VAZIA = "show bgp ipv6 unicast\r\nNo BGP prefixes displayed, 0 exist\r\nlg-fec>"


class _Log:
    def info(self, *a, **k): pass
    debug = info


def _afi(rotas: int, pct: float = 41.2) -> dict:
    return {"total_routes": rotas, "unique_prefixes": rotas, "ixp_space": 0, "asn_direct_count": 3 if rotas else 0, "asn_origin_count": 0,
            "asn_stub_count": 0, "br_asns_origin_count": 0, "br_prefix_coverage_pct": pct if rotas else 0.0,
            "ixp_vs_fulltable_space_pct": pct if rotas else 0.0}


def _ptt(tmp, code, v4, v6, brutos=("v4", "v6")):
    rd = raw_path(tmp, D, code)
    rd.mkdir(parents=True, exist_ok=True)
    for afi in brutos:
        (rd / f"bgp-{afi}-{code}-{D}.txt").write_text(VAZIA if afi == "v6" and v6 and not v6["total_routes"] else "rotas", encoding="utf-8")
    pub = tmp / "published" / D / "ixps"
    pub.mkdir(parents=True, exist_ok=True)
    doc = {"ixp": code, "v4": v4 if v4 is not None else {"status": "missing"}, "v6": v6 if v6 is not None else {"status": "missing"}}
    (pub / f"{code}.json").write_text(json.dumps(doc), encoding="utf-8")


def test_tabela_ipv6_vazia_e_coleta_vazia_e_ptt_parcial(tmp_path):
    """fec desde 2026-10-31: o LG respondeu `No BGP prefixes displayed, 0 exist` em IPv6 e o índice publicava `status: ok` com 0%."""
    _ptt(tmp_path, "fec", _afi(5247), _afi(0))
    _ptt(tmp_path, "ce", _afi(9000), _afi(241338))
    _ptt(tmp_path, "ap", _afi(562), None, brutos=("v4",))
    idx, _ = publicar_ixp_index(tmp_path, D, [{"code": c, "name": c, "uf": "XX"} for c in ("fec", "ce", "ap")], _Log())
    e = {x["code"]: x for x in idx}
    assert e["fec"]["status"] == "partial" and e["fec"]["v6"]["coleta"] == "vazia" and e["fec"]["v4"]["coleta"] == "ok"
    assert e["fec"]["v6"]["total_routes"] == 0 and e["fec"]["v6"]["br_prefix_coverage_pct"] is None      # zero rotas não é 0% de cobertura
    assert e["ce"]["status"] == "ok" and e["ce"]["v6"]["coleta"] == "ok" and e["ce"]["v6"]["br_prefix_coverage_pct"] == 41.2
    assert e["ap"]["status"] == "partial" and e["ap"]["v6"] == {"status": "missing", "coleta": "missing"}


def test_marcacao_vale_para_indice_ja_publicado_e_e_idempotente():
    """A API marca na leitura os índices publicados antes do campo (snapshots de 2026-11-01 a 2026-11-22 com fec, rao e ap `ok`)."""
    entrada = {"code": "rao", "status": "ok", "v4": _afi(5531), "v6": _afi(0)}
    ic.marcar_ptt(entrada)
    assert entrada["status"] == "partial" and entrada["v6"]["coleta"] == "vazia" and entrada["v6"]["ixp_vs_fulltable_space_pct"] is None
    copia = json.loads(json.dumps(entrada))
    assert ic.marcar_ptt(copia) == entrada
    assert ic.marcar_ptt({"code": "x", "status": "missing"}) == {"code": "x", "status": "missing"}       # sem documento: fica o do bruto
    assert ic.status_ptt({"status": "missing"}, {"status": "missing"}) == "missing"
