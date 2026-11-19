# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T2/T4 — relações ARC v2, `transito` e as rotas novas sobre uma CÓPIA do dataset sintético em que o produto é publicado.

O pipeline compartilhado (`pipeline`) não publica `as_relationships` nem `transito` (etapas fora do run semanal, sem replay no sintético),
então aqui o produto roda numa cópia e a API serve essa cópia."""
import dataclasses
import shutil

import pytest

from core.common import configure_logging, read_json_gz
from products.as_relationships import build as relacoes, config as cf
from products.transito import build as transito
from tests.products.api_contract import ALLOWED
from tests.products.conftest import fake_pix
from tests.synth.world import T1

CFG = dataclasses.replace(cf.carregar(), descartar_asn=((0, 0), (23456, 23456)))


@pytest.fixture(scope="module")
def base(pipeline, tmp_path_factory):
    base0, _ = pipeline
    b = tmp_path_factory.mktemp("transito") / "data"
    shutil.copytree(base0, b)
    assert relacoes.run(T1, b, configure_logging(), cfg=CFG)
    assert transito.publicar(b, T1, configure_logging(), cfg=CFG)
    return b


@pytest.fixture(scope="module")
def cliente(base):
    from fastapi.testclient import TestClient

    with pytest.MonkeyPatch.context() as mp:
        for k, v in {"DATA_DIR": str(base), "JWT_SECRET": "x" * 32, "GOOGLE_CLIENT_ID": "a", "GOOGLE_CLIENT_SECRET": "b", "ALLOWED_IPS": "203.0.113.128/25",
                     "APP_BASE_URL": "http://localhost", "ANON_SESSION_LIMIT_MINUTES": "10", "ACCESS_POLICY_MODE": "enforce", "USAGE_LOG": "off"}.items():
            mp.setenv(k, v)
        from api.main import app
        from api.ratelimit import limiter
        from api.store import Store

        mp.setattr(Store, "_load_pix_config", lambda self: fake_pix())
        mp.setattr(limiter, "enabled", False)
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
        for attr in ("store", "latest_cache"):
            if hasattr(app.state, attr):
                delattr(app.state, attr)


def test_documento_v2_traz_estado_refino_calibracao_e_limites(base):
    doc = read_json_gz(base / "published" / T1 / "as_relationships.json.gz")
    assert doc["algoritmo"] == "ARC v2" and set(doc) >= {"refino", "restricoes", "calibracao", "estabilidade", "mudancas", "politica_rs"}
    assert doc["estabilidade"]["persistencia"] == 2 and doc["estabilidade"]["novos"] + doc["estabilidade"]["estaveis"] + doc["estabilidade"]["pendentes"] >= 1
    assert doc["calibracao"]["v4"]["p_calibrada"] is False and doc["calibracao"]["v4"]["ece"] > 0.10   # ECE medido na régua acima do limite: p não calibrada
    assert doc["refino"]["v4"]["iteracoes"] and doc["refino"]["v4"]["treino"] > 0
    assert doc["restricoes"]["irmaos"] >= 0 and "ciclos_rompidos" in doc["restricoes"]
    for r in doc["relacoes"]:
        assert r["tipo"] in ("p2c", "p2p", "s2s", "complexa", "sem_classificacao")
        if r["tipo"] in ("p2c", "p2p"):                                 # toda linha refinada guarda a probabilidade da v1 (ou, v4≠v6 sem refino por família, a evidência)
            evs = [r["evid"]] if "refino" in r["evid"] or "fontes" in r["evid"] else [r["evid"].get("v4") or {}, r["evid"].get("v6") or {}]
            assert any("refino" in e or "fontes" in e for e in evs), r


def test_p2c_publicado_e_aciclico(base):
    doc = read_json_gz(base / "published" / T1 / "as_relationships.json.gz")
    arestas = {}
    for r in doc["relacoes"]:
        if r["tipo"] == "p2c":
            arestas.setdefault(r["a"], set()).add(r["b"])
    visto, em_pilha = set(), set()

    def tem_ciclo(x):
        visto.add(x)
        em_pilha.add(x)
        for y in arestas.get(x, ()):
            if y in em_pilha or (y not in visto and tem_ciclo(y)):
                return True
        em_pilha.discard(x)
        return False

    assert not any(tem_ciclo(a) for a in list(arestas) if a not in visto)


def test_transito_artefatos_e_rotas(cliente, base):
    asns = read_json_gz(base / "published" / T1 / "transito" / "asns.json.gz")
    ufs = read_json_gz(base / "published" / T1 / "transito" / "ufs.json.gz")
    assert asns["limites"] and ufs["cobertura"]["algoritmo"] == "ARC v2" and ufs["ufs"]
    r = cliente.get("/api/v1/transito/ufs", headers=ALLOWED).json()
    assert r["total"] == len(ufs["ufs"]) and all("provedores" not in u for u in r["ufs"]) and r["limites"]
    uf = next(iter(ufs["ufs"]))
    d = cliente.get(f"/api/v1/transito/ufs/{uf.lower()}", headers=ALLOWED).json()
    assert d["uf"] == uf and d["snapshot_date"] == T1 and "provedores" in d
    assert cliente.get("/api/v1/transito/ufs/XX", headers=ALLOWED).status_code == 404
    if asns["asns"]:
        asn = int(next(iter(asns["asns"])))
        a = cliente.get(f"/api/v1/asns/{asn}/transito", headers=ALLOWED).json()
        assert a["com_cliente"] is True and a["cone_asns"] >= 1 and a["limites"]
        assert cliente.get(f"/api/v1/asns/{asn}", params={"include": "transito"}, headers=ALLOWED).json()["transito"]["cone_asns"] == a["cone_asns"]
    sem = cliente.get("/api/v1/asns/99999999/transito", headers=ALLOWED).json()
    assert sem["com_cliente"] is False and sem["cone_asns"] == 0
    assert "transito" not in cliente.get("/api/v1/asns/64496", headers=ALLOWED).json()
    assert cliente.get(f"/api/v1/ufs/{uf}", params={"include": "transito"}, headers=ALLOWED).json()["transito"]["uf"] == uf


def test_colecoes_do_query(cliente):
    q = cliente.post("/api/v1/query/transito_uf", json={"limit": 50}, headers=ALLOWED).json()["items"]
    assert q and all({"uf", "hhi_clientes", "asns_br"} <= set(x) for x in q)
    q = cliente.post("/api/v1/query/transito_asn", json={"limit": 50, "sort": [{"field": "cone_br", "dir": "desc"}]}, headers=ALLOWED).json()["items"]
    assert all({"asn", "cone_br", "cone_asns"} <= set(x) for x in q)


def test_nao_ha_contato_nem_ip_nas_respostas(cliente):
    txt = cliente.get("/api/v1/transito/ufs", headers=ALLOWED).text + cliente.post("/api/v1/query/transito_asn", json={"limit": 50}, headers=ALLOWED).text
    assert not any(k in txt.lower() for k in ("email", "phone", "telefone", "@"))
