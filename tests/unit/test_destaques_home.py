# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — as consultas fixas de `GET /brasil/destaques` são as dos cartões da home (`cartoes.json`): o número do destaque é o da lista de destino."""
import json
from pathlib import Path

from api.routes.brasil import _DESTAQUES_QUERY, _DIVERGENCIAS, _O_QUE_MUDOU

ROOT = Path(__file__).resolve().parents[2]
CARTOES = {c["id"]: c for c in json.loads((ROOT / "frontend" / "src" / "features" / "home" / "cartoes.json").read_text(encoding="utf-8"))["cartoes"]}


def _sem_limite(corpo: dict) -> dict:
    return {k: v for k, v in corpo.items() if k not in ("limit", "select", "sort")}


def test_consultas_dos_destaques_sao_as_dos_cartoes():
    for id_, (colecao, corpo) in _DESTAQUES_QUERY.items():
        c = CARTOES[id_]["consulta"]
        assert c["tipo"] == "query" and c["colecao"] == colecao, id_
        assert _sem_limite(c["corpo"]) == _sem_limite(corpo), id_


def test_o_que_mudou_e_o_cartao_com_limite_1():
    c = CARTOES["o-que-mudou"]["consulta"]
    assert c["colecao"] == "eventos" and c["corpo"]["filter"] == _O_QUE_MUDOU["filter"] and c["corpo"]["select"] == _O_QUE_MUDOU["select"]
    assert _O_QUE_MUDOU["limit"] == 1


def test_divergencias_usam_os_parametros_padrao_da_rota_de_destino():
    import inspect

    from api.routes.acessos import acessos_divergencias_scm
    padrao = {k: v.default.default for k, v in inspect.signature(acessos_divergencias_scm).parameters.items() if hasattr(v.default, "default")}
    for k, v in _DIVERGENCIAS.items():
        assert padrao[k] == v, k
    assert CARTOES["divergencias-apnic-anatel"]["consulta"]["caminho"] == "/api/v1/acessos/divergencias/scm"


def test_front_destaques_leem_os_totais_da_rota_aberta():
    ids = {d["id"] for d in json.loads(json.dumps([{"id": i} for i in ("grandes-sem-asn", "sem-rpki", "monopolio-local", "divergencias")]))}
    fonte = (ROOT / "frontend" / "src" / "features" / "home" / "regrasDestaques.ts").read_text(encoding="utf-8")
    assert all(f"id: '{i}'" in fonte for i in ids)
    comp = (ROOT / "frontend" / "src" / "features" / "home" / "Destaques.tsx").read_text(encoding="utf-8")
    assert "fetchDestaquesHome" in comp and "queryColecao" not in comp          # nada de `/query` genérico na entrada
