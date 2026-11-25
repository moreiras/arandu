# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T2 — MOAS medido (PT-04b): `routing_analysis` sobre uma cópia do publicado sintético, e o que a API e o MCP servem.

T1 tem `origins-multi-{afi}` (dois coletores, cenário 1 e mais dois prefixos); em T0 o arquivo é apagado antes da análise, como num
snapshot cuja coleta guardava uma origem por prefixo. `routing_analysis` fica fora do T2 principal (o `pipeline` não o roda), então
roda aqui numa cópia, sem mexer no publicado que os outros módulos leem."""
import asyncio
import json
import shutil

import pytest

from core.common import configure_logging
from tests.products.conftest import fake_pix
from tests.synth.world import T0, T1

PALAVRAS_DE_CAUSA = ("sequestro", "hijack", "sequestrad")


@pytest.fixture(scope="module")
def base_moas(pipeline, tmp_path_factory):
    base, _ = pipeline
    copia = tmp_path_factory.mktemp("moas") / "data"
    shutil.copytree(base, copia)
    from products.routing_analysis import build

    for afi in ("v6", "v4"):
        (copia / "normalized" / T0 / "summary" / f"origins-multi-{afi}.json.gz").unlink()
    log = configure_logging()
    assert build.run(T1, copia, log) and build.run(T0, copia, log)
    return copia


def _pub(base, date, nome):
    return json.loads((base / "published" / date / nome).read_text(encoding="utf-8"))


def test_analise_mede_moas_com_origens_e_coletores(base_moas):
    ra = _pub(base_moas, T1, "routing_analysis.json")
    r = ra["moas_resumo"]
    assert "moas_indisponivel" not in ra
    assert r["prefixos"] == {"v6": {"global": 1, "br": 1}, "v4": {"global": 2, "br": 1}}   # o prefixo estrangeiro só conta no global
    assert r["coletores"] == {"v6": ["rvT", "rvU"], "v4": ["rvT", "rvU"]} and r["lista_truncada"] is False
    assert [m["afi"] for m in ra["moas"]] == ["v6", "v4"]                                    # IPv6 antes de IPv4
    v4 = next(m for m in ra["moas"] if m["prefix"] == "198.18.0.0/24")
    assert v4["origins"] == [64496, 64497] and v4["br_origins"] == [64496, 64497]
    assert [(o["asn"], o["coletores"], o["coletores_nomes"]) for o in v4["origens"]] == [(64496, 2, ["rvT", "rvU"]), (64497, 1, ["rvU"])]
    v6 = ra["moas"][0]
    assert v6["prefix"] == "2001:db8::/48" and v6["br_origins"] == [64496] and len(v6["origins"]) == 2


def test_moas_e_fato_sem_rotulo_de_causa(base_moas):
    ra = _pub(base_moas, T1, "routing_analysis.json")
    texto = json.dumps({"moas": ra["moas"], "moas_resumo": ra["moas_resumo"]}, ensure_ascii=False).lower()
    assert not any(p in texto for p in PALAVRAS_DE_CAUSA)
    assert "hipótese" in ra["moas_resumo"]["como_ler"].lower()                     # causas só no "como ler", como hipótese
    assert all(set(m) == {"prefix", "afi", "origins", "br_origins", "is_prefix_br", "origens"} for m in ra["moas"])


def test_resumo_traz_contagem_por_familia(base_moas):
    s = _pub(base_moas, T1, "routing_analysis_resumo.json")["saude"]
    assert s["moas"] == {"v6": {"prefixos": 1, "prefixos_br": 1, "coletores": 2}, "v4": {"prefixos": 2, "prefixos_br": 1, "coletores": 2}}
    assert "moas_indisponivel" not in s


def test_snapshot_sem_artefato_fica_nulo_com_o_motivo(base_moas):
    ra = _pub(base_moas, T0, "routing_analysis.json")
    assert ra["moas"] is None and ra["moas_resumo"] is None and "limite da coleta" in ra["moas_indisponivel"]
    s = _pub(base_moas, T0, "routing_analysis_resumo.json")["saude"]
    assert s["moas"] is None and "não medida" in s["moas_indisponivel"]


# ── API e MCP ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_moas(base_moas):
    from fastapi.testclient import TestClient

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATA_DIR", str(base_moas))
        mp.setenv("JWT_SECRET", "x" * 32)
        mp.setenv("GOOGLE_CLIENT_ID", "a")
        mp.setenv("GOOGLE_CLIENT_SECRET", "b")
        mp.setenv("ALLOWED_IPS", "203.0.113.128/25")
        mp.setenv("APP_BASE_URL", "http://localhost")
        mp.setenv("ACCESS_POLICY_MODE", "off")
        mp.setenv("USAGE_LOG", "off")
        from api.main import app
        from api.ratelimit import limiter
        from api.store import Store

        mp.setattr(Store, "_load_pix_config", lambda self: fake_pix())
        mp.setattr(limiter, "enabled", False)
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def test_api_routing_analysis_serve_moas_medido_e_nulo(api_moas):
    r = api_moas.get("/api/v1/routing-analysis", params={"date": T1})
    assert r.status_code == 200
    d = r.json()
    assert len(d["moas"]) == 2 and d["moas_resumo"]["prefixos"]["v4"] == {"global": 2, "br": 1} and "moas_indisponivel" not in d
    d0 = api_moas.get("/api/v1/routing-analysis", params={"date": T0}).json()
    assert d0["moas"] is None and d0["moas_resumo"] is None and "limite da coleta" in d0["moas_indisponivel"]


def test_api_brasil_indicadores_saude_moas(api_moas):
    s1 = api_moas.get("/api/v1/brasil/indicadores", params={"date": T1}).json()["rpki"]["rotas"]["saude"]
    assert s1["moas"]["v4"] == {"prefixos": 2, "prefixos_br": 1, "coletores": 2}
    s0 = api_moas.get("/api/v1/brasil/indicadores", params={"date": T0}).json()["rpki"]["rotas"]["saude"]
    assert s0["moas"] is None and s0["moas_indisponivel"]


def _mcp(base, nome, args):
    from api.store import Store
    from mcp_server import app as m

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(m, "_store", Store(base))
        mp.setattr(Store, "_load_pix_config", lambda self: fake_pix())
        out = asyncio.run(m.mcp.call_tool(nome, args))
    blocos = out[0] if isinstance(out, tuple) else out
    return json.loads("".join(getattr(b, "text", "") for b in blocos))


def test_mcp_rota_analise_moas(base_moas):
    sec = _mcp(base_moas, "rota_analise", {"secao": "moas", "date": T1})
    assert [m["prefix"] for m in sec["conteudo"]] == ["2001:db8::/48", "198.18.0.0/24"]
    idx = _mcp(base_moas, "rota_analise", {"date": T1})
    assert idx["moas_resumo"]["prefixos"]["v6"] == {"global": 1, "br": 1}
    sec0 = _mcp(base_moas, "rota_analise", {"secao": "moas", "date": T0})
    assert sec0["conteudo"] is None
    idx0 = _mcp(base_moas, "rota_analise", {"date": T0})
    assert idx0["moas"] is None and "limite da coleta" in idx0["moas_indisponivel"]
