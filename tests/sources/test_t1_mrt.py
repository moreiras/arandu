# SPDX-License-Identifier: AGPL-3.0-or-later
"""T1 — MRT: RIB da tabela global (TABLE_DUMP_V2) e updates BGP4MP do RouteViews."""
import bz2
import datetime
import io
import json
import shutil
import urllib.error

import mrtparse
import pytest

from sources.bgp_updates_routeviews import collect as upd
from sources.fulltable_routeviews import collect as ft
from tests.sources.conftest import read_gz, volatile, write_gz


# ── RIB (TABLE_DUMP_V2) ────────────────────────────────────────────────────

def test_parse_mrt_v4_extrai_melhor_rota_e_ignora_default(fx, log):
    routes, adj = ft._parse_mrt(fx("fulltable", "rib-v4.sample.mrt.bz2"), "v4", log)
    por = {r["prefix"]: r for r in routes}
    assert set(por) == {"198.51.100.0/24", "203.0.113.0/24", "192.0.2.0/25", "10.0.0.0/8"}   # 0.0.0.0/0 ignorada
    assert por["198.51.100.0/24"]["aspath"] == [64496, 64510] and por["198.51.100.0/24"]["status"] == ">"
    assert por["203.0.113.0/24"]["aspath"] == [64497, 64511, 64511, 64511]       # o prepend fica na rota


def test_parse_mrt_grafo_ignora_prepend_e_junta_todos_os_caminhos(fx, log):
    _, adj = ft._parse_mrt(fx("fulltable", "rib-v4.sample.mrt.bz2"), "v4", log)
    # 64496 aparece à esquerda de 64510 (rota 1) e 64497 → 64496 (2º caminho)
    assert adj["64510"]["up"] == [64496]
    assert 64496 in adj["64497"]["down"]
    assert adj["64511"] == {"up": [64497], "down": []}        # 64511 ×3 conta uma vez só


def test_parse_mrt_communities_so_para_origem_br(fx, log):
    routes, _ = ft._parse_mrt(fx("fulltable", "rib-v4.sample.mrt.bz2"), "v4", log, br_asns={64511})
    por = {r["prefix"]: r for r in routes}
    assert por["203.0.113.0/24"]["communities"]
    assert "communities" not in por["198.51.100.0/24"]     # origem 64510 não é "BR" nesta chamada


def test_parse_mrt_v6(fx, log):
    routes, adj = ft._parse_mrt(fx("fulltable", "rib-v6.sample.mrt.bz2"), "v6", log)
    assert [r["prefix"] for r in routes] == ["2001:db8::/32", "2001:db8:1::/48"]
    assert adj["64510"]["up"] == [64496]


def test_parse_mrt_afi_errado_nao_devolve_nada(fx, log):
    assert ft._parse_mrt(fx("fulltable", "rib-v6.sample.mrt.bz2"), "v4", log)[0] == []


def test_parse_mrt_arquivo_truncado_nao_levanta(fx, log, tmp_path):
    raw = bz2.decompress(fx("fulltable", "rib-v4.sample.mrt.bz2").read_bytes())
    p = tmp_path / "trunc.bz2"
    p.write_bytes(bz2.compress(raw[: len(raw) - 7]))
    routes, _ = ft._parse_mrt(p, "v4", log)
    assert len(routes) >= 1


def test_write_normalized_grava_todos_os_artefatos(fx, log, base, date_str):
    routes, adj = ft._parse_mrt(fx("fulltable", "rib-v4.sample.mrt.bz2"), "v4", log, br_asns={64510, 64511})
    ft._write_normalized(routes, adj, "v4", date_str, ["rv-sample"], base, log, br_asns={64510, 64511})
    s = base / "normalized" / date_str / "summary"
    assert read_gz(s / "prefix-set-v4.json.gz") == sorted(r["prefix"] for r in routes)
    origin = read_gz(s / "origin-prefixes-v4.json.gz")
    assert origin["64510"] == ["198.51.100.0/24"] and origin["64520"] == ["192.0.2.0/25"]
    stats = read_gz(s / "routes-v4.json.gz")["stats"]
    assert stats["total_routes"] == 4 and stats["asn_origin_count"] == 4 and stats["unique_prefixes"] == 4
    br = read_gz(s / "br-routes-v4.json.gz")
    assert {x["p"] for x in br} == {"198.51.100.0/24", "203.0.113.0/24"} and any("c" in x for x in br)
    assert read_gz(s / "aspath-adj-v4.json.gz")["64510"]["up"] == [64496]


def test_merge_into_primeiro_coletor_prevalece():
    seen, up, dn = {}, {}, {}
    from collections import defaultdict
    up, dn = defaultdict(set), defaultdict(set)
    ft._merge_into(seen, up, dn, [{"prefix": "p", "aspath": [1, 2]}], {"2": {"up": [1], "down": []}})
    ft._merge_into(seen, up, dn, [{"prefix": "p", "aspath": [9, 9]}, {"prefix": "q", "aspath": [3]}], {"2": {"up": [7], "down": []}})
    assert seen["p"]["aspath"] == [1, 2] and "q" in seen
    assert up["2"] == {1, 7}


def _fake_collectors(monkeypatch, fx, log):
    monkeypatch.setattr(ft, "COLLECTORS", {"v4": [("rvA", "rv"), ("rvB", "rv")], "v6": [("rvA", "rv")]})
    monkeypatch.setattr(ft, "_find_rib_url_rv", lambda name, target, clog: f"http://x/{name}.v4.bz2" if name != "rvB" else None)

    def download(url, dest, clog):
        which = "v6" if "v6" in dest.name else "v4"
        shutil.copy(fx("fulltable", f"rib-{which}.sample.mrt.bz2"), dest)
        return True

    monkeypatch.setattr(ft, "_download", download)


def test_run_fulltable_pula_coletor_sem_dump_e_grava_manifesto(base, log, fx, date_str, monkeypatch):
    _fake_collectors(monkeypatch, fx, log)
    write_gz(base / "normalized" / date_str / "summary" / "registro_br.json.gz", {"asns": [{"asn": 64511}]})
    r = ft.run(date_str, base, ["v4", "v6"], False, log)
    assert r["v4"]["status"] == "ok" and r["v4"]["unique_prefixes"] == 4 and len(r["v4"]["sources"]) == 1
    assert r["v6"]["unique_prefixes"] == 2
    s = base / "normalized" / date_str / "summary"
    assert (s / "fulltable_manifest.json").exists() and not (s / "_ckpt_v4").exists()
    assert read_gz(s / "br-routes-v4.json.gz")[0]["a"][-1] == 64511


def test_run_fulltable_segunda_execucao_e_skip(base, log, fx, date_str, monkeypatch):
    _fake_collectors(monkeypatch, fx, log)
    ft.run(date_str, base, ["v4"], False, log)
    r = ft.run(date_str, base, ["v4"], False, log)
    assert r["v4"] == {"status": "skipped"}


def test_run_fulltable_familia_pronta_nao_e_refeita_quando_a_outra_falha(base, log, fx, date_str, monkeypatch):
    """v4 e v6 são independentes: se o v6 falha, a retentativa pula o v4 já gravado e refaz só o v6."""
    _fake_collectors(monkeypatch, fx, log)
    ok_download = ft._download
    monkeypatch.setattr(ft, "_download", lambda url, dest, clog: False if "v6" in dest.name else ok_download(url, dest, clog))
    r1 = ft.run(date_str, base, ["v4", "v6"], False, log)
    assert r1["v4"]["status"] == "ok" and r1["v6"]["status"] == "error"
    manifesto = json.loads((base / "normalized" / date_str / "summary" / "fulltable_manifest.json").read_text())
    assert manifesto["v4"]["status"] == "ok" and "v6" not in manifesto
    monkeypatch.setattr(ft, "_download", ok_download)
    r2 = ft.run(date_str, base, ["v4", "v6"], False, log)
    assert r2["v4"] == {"status": "skipped"} and r2["v6"]["status"] == "ok"
    manifesto = json.loads((base / "normalized" / date_str / "summary" / "fulltable_manifest.json").read_text())
    assert manifesto["v4"]["status"] == "ok" and manifesto["v6"]["status"] == "ok"


def test_coletores_mrt_nao_deixam_sigpipe_no_padrao():
    """O mrtparse restaura SIGPIPE ao importar; sem ignorar_sigpipe(), um socket fechado pelo servidor mata o processo (-13)."""
    import importlib
    import signal
    from sources.bgp_stability_deep import collect as deep
    from sources.bgp_updates_routeviews import collect as upd
    for mod in (ft, upd, deep):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # como o mrtparse deixa
        importlib.reload(mod)
        assert signal.getsignal(signal.SIGPIPE) == signal.SIG_IGN, mod.__name__


def test_run_fulltable_todos_os_coletores_falham(base, log, date_str, monkeypatch):
    monkeypatch.setattr(ft, "COLLECTORS", {"v4": [("rvA", "rv")], "v6": []})
    monkeypatch.setattr(ft, "_find_rib_url_rv", lambda *a: "http://x/a.bz2")
    monkeypatch.setattr(ft, "_download", lambda url, dest, clog: False)
    r = ft.run(date_str, base, ["v4"], False, log)
    assert r["v4"]["status"] == "error"
    assert not (base / "normalized" / date_str / "summary" / "prefix-set-v4.json.gz").exists()


# ── updates BGP4MP ─────────────────────────────────────────────────────────

SAMPLE = "updates.20260913.0000.sample.bz2"


def _origins(sample_bytes: bytes) -> set[int]:
    out = set()
    for m in mrtparse.Reader(io.BytesIO(bz2.decompress(sample_bytes))):
        for a in m.data.get("bgp_message", {}).get("path_attributes", []):
            if 2 in a.get("type", {}):
                segs = [int(x) for s in a["value"] for x in s["value"]]
                if segs:
                    out.add(segs[-1])
    return out


@pytest.fixture()
def upd_env(base, fx, date_str, monkeypatch):
    sample = fx("bgp_updates", SAMPLE).read_bytes()
    write_gz(base / "normalized" / date_str / "summary" / "registro_br.json.gz",
             {"asns": [{"asn": a} for a in _origins(sample)]})
    target = "updates.20260913.0000.bz2"

    def urlopen(req, timeout=0):
        if req.full_url.endswith(target):
            return io.BytesIO(sample)
        raise urllib.error.HTTPError(req.full_url, 404, "nao existe", {}, None)

    monkeypatch.setattr(upd.urllib.request, "urlopen", urlopen)
    return sample


def test_parse_updates_conta_eventos_de_origem_br(upd_env, log):
    acc = upd.UpdateAccumulator(int(datetime.datetime(2026, 9, 13, tzinfo=datetime.timezone.utc).timestamp()))
    v4, v6 = upd._parse_updates(upd_env, _origins(upd_env), {}, acc, log)
    assert v4 + v6 > 0 and acc.raw_seen == v4 + v6
    assert acc.counted <= acc.raw_seen
    assert all(asn in _origins(upd_env) for asn, _ in acc.data)


def test_parse_updates_ignora_origem_nao_br(upd_env, log):
    acc = upd.UpdateAccumulator(0)
    assert upd._parse_updates(upd_env, {1}, {}, acc, log) == (0, 0)


def test_parse_updates_bz2_corrompido(log):
    acc = upd.UpdateAccumulator(0)
    assert upd._parse_updates(b"isto nao e bz2", {1}, {}, acc, log) == (0, 0)


def test_run_updates_normaliza_estabilidade(upd_env, base, log, date_str):
    assert upd.run(date_str, base, log) is True
    out = read_gz(base / "normalized" / date_str / "summary" / "bgp_stability.json.gz")
    p = out["period"]
    assert p["days"] == 7 and p["files_processed"] == 1 and p["files_missing"] == 671
    assert p["raw_events_seen"] >= p["events_counted"] > 0
    assert out["as_stability"] and {"asn"} <= set(out["as_stability"][0])
    man = json.loads((base / "normalized" / date_str / "summary" / "bgp_stability_manifest.json").read_text())
    assert man["asns_analyzed"] == len(out["as_stability"])


def test_run_updates_segunda_execucao_e_skip_e_force_reprocessa(upd_env, base, log, date_str):
    upd.run(date_str, base, log)
    gz = base / "normalized" / date_str / "summary" / "bgp_stability.json.gz"
    gz.unlink()
    assert upd.run(date_str, base, log) is True and not gz.exists()          # manifesto presente → pula
    assert upd.run(date_str, base, log, force=True) is True and gz.exists()


def test_run_updates_sem_br_asns_aborta(base, log, date_str):
    assert upd.run(date_str, base, log) is False


def test_update_urls_cobrem_7_dias_de_15_em_15_minutos():
    urls = upd._update_urls("2026-09-20")
    assert len(urls) == 7 * 96
    assert urls[0][1].endswith("/2026.09/UPDATES/updates.20260913.0000.bz2")
    assert urls[-1][0] == datetime.datetime(2026, 9, 19, 23, 45)


# ── análise aprofundada (etapa 2) sobre o cache da etapa 1 ─────────────────

from sources.bgp_stability_deep import collect as deep


def _prefix_origin_pairs(sample_bytes: bytes) -> dict[str, int]:
    out = {}
    for m in mrtparse.Reader(io.BytesIO(bz2.decompress(sample_bytes))):
        body = m.data.get("bgp_message", {})
        asp = None
        for a in body.get("path_attributes", []):
            if 2 in a.get("type", {}):
                segs = [int(x) for s in a["value"] for x in s["value"]]
                asp = segs[-1] if segs else None
        if asp:
            for n in body.get("nlri", []):
                out[f"{n['prefix']}/{n['length']}"] = asp
            for a in body.get("path_attributes", []):
                if 14 in a.get("type", {}):                      # MP_REACH_NLRI (IPv6)
                    for n in a.get("value", {}).get("nlri", []):
                        out[f"{n['prefix']}/{n['length']}"] = asp
    return out


def _origin_files(base, date_str, pairs):
    by_v4, by_v6 = {}, {}
    for p, a in pairs.items():
        (by_v6 if ":" in p else by_v4).setdefault(str(a), []).append(p)
    s = base / "normalized" / date_str / "summary"
    write_gz(s / "origin-prefixes-v4.json.gz", by_v4)
    write_gz(s / "origin-prefixes-v6.json.gz", by_v6)


def test_deep_diagnostica_top_ases(upd_env, base, log, date_str):
    assert upd.run(date_str, base, log) is True                       # etapa 1 deixa o cache bz2 em raw/
    pairs = _prefix_origin_pairs(upd_env)
    assert pairs, "a amostra precisa ter anúncios IPv4 de origem BR"
    _origin_files(base, date_str, pairs)
    assert deep.run(date_str, base, 5, False, log) is True
    out = read_gz(base / "normalized" / date_str / "summary" / "bgp_stability_deep.json.gz")
    assert out["date"] == date_str and out["top_n"] == 5
    d = out["as_diagnosis"][0]
    assert d["verdict"] in {"upstream_instability", "prefix_specific", "origin_instability"}
    assert 0.0 <= d["prefix_sync_score"] <= 1.0 and isinstance(d["hot_prefixes"], list)


def test_deep_sem_etapa_1_retorna_false(base, log, date_str):
    assert deep.run(date_str, base, 5, False, log) is False


def test_deep_sem_cache_mrt_retorna_false(upd_env, base, log, date_str, tmp_path):
    upd.run(date_str, base, log)
    for f in (base / "raw" / date_str / "route-views.saopaulo").glob("*.bz2"):
        f.unlink()
    _origin_files(base, date_str, _prefix_origin_pairs(upd_env))
    assert deep.run(date_str, base, 5, False, log) is False


def test_deep_skip_sem_force(upd_env, base, log, date_str):
    upd.run(date_str, base, log)
    _origin_files(base, date_str, _prefix_origin_pairs(upd_env))
    deep.run(date_str, base, 5, False, log)
    out = base / "normalized" / date_str / "summary" / "bgp_stability_deep.json.gz"
    out.write_bytes(b"")
    assert deep.run(date_str, base, 5, False, log) is True and out.read_bytes() == b""
    assert deep.run(date_str, base, 5, True, log) is True and out.stat().st_size > 0


@pytest.mark.parametrize("sync, conc, esperado", [
    (0.9, 90.0, "upstream_instability"),
    (0.9, 50.0, "origin_instability"),          # sincronizado, mas sem upstream concentrado
    (0.05, 10.0, "prefix_specific"),
    (0.5, 10.0, "origin_instability"),
])
def test_deep_verdict(sync, conc, esperado):
    assert deep._verdict(sync, conc) == esperado


def test_todo_coletor_routeviews_configurado_tem_diretorio_e_url_do_arquivo():
    """`route-views.napafrica` aponta para o diretório certo (`napafrica/` dá 404)."""
    from sources.fulltable_routeviews import collect as ft

    rv = {n for afi in ft.COLLECTORS.values() for n, kind in afi if kind == "rv"}
    assert rv and rv <= set(ft._RV_PATHS)
    assert ft._rv_base_url("route-views.napafrica") == "http://archive.routeviews.org/route-views.napafrica/bgpdata"
    assert ft._rv_base_url("route-views2") == "http://archive.routeviews.org/bgpdata"
    for n in rv - {"route-views2"}:
        # no arquivo da RouteViews o diretório de cada coletor tem o nome do coletor
        assert ft._rv_base_url(n) == f"http://archive.routeviews.org/{n}/bgpdata", n


# ── Caminhos únicos com VP ─────────────────────────────────────

def test_parse_mrt_agrega_caminhos_unicos_com_vp(fx, log):
    from sources.fulltable_routeviews.caminhos import AgregadorCaminhos

    ag = AgregadorCaminhos()
    routes, adj = ft._parse_mrt(fx("fulltable", "rib-v4.sample.mrt.bz2"), "v4", log, caminhos=ag)
    sem, _ = ft._parse_mrt(fx("fulltable", "rib-v4.sample.mrt.bz2"), "v4", log)
    assert routes == sem                                              # o novo parâmetro não muda rotas nem grafo
    caminhos = {tuple(__import__("array").array("I", k)): v for k, v in ag.dados.items()}
    assert (64496, 64510) in caminhos and (64497, 64511) in caminhos   # prepend comprimido
    assert all(mask > 0 and n >= 1 for mask, n in caminhos.values())
    assert sum(n for _, n in caminhos.values()) >= len(routes)


def test_run_grava_aspaths_por_coletor_e_o_formato_le_de_volta(base, log, fx, date_str, monkeypatch):
    from sources.fulltable_routeviews import caminhos as cm

    _fake_collectors(monkeypatch, fx, log)
    ft.run(date_str, base, ["v4"], False, log)
    arq = base / "normalized" / date_str / "summary" / "aspaths-v4" / "rvA.tsv.gz"
    assert arq.exists()
    cab = cm.cabecalho(arq)
    assert cab["n_vps"] >= 1 and all(isinstance(a, int) for a in cab["vps"])
    lidos = list(cm.ler(arq))
    assert lidos and all(c.n_vps >= 1 and c.n_rotas >= 1 and len(c.asns) >= 1 for c in lidos)
    assert any(c.asns == (64496, 64510) for c in lidos)


def test_aspaths_desligavel_por_variavel(base, log, fx, date_str, monkeypatch):
    _fake_collectors(monkeypatch, fx, log)
    monkeypatch.setattr(ft, "CAMINHOS_VP", False)
    ft.run(date_str, base, ["v4"], False, log)
    assert not (base / "normalized" / date_str / "summary" / "aspaths-v4").exists()


def test_force_apaga_aspaths_antigos(base, log, fx, date_str, monkeypatch):
    _fake_collectors(monkeypatch, fx, log)
    ft.run(date_str, base, ["v4"], False, log)
    velho = base / "normalized" / date_str / "summary" / "aspaths-v4" / "rvZ.tsv.gz"
    velho.write_bytes(b"x")
    ft.run(date_str, base, ["v4"], True, log)
    assert not velho.exists()
