# SPDX-License-Identifier: AGPL-3.0-or-later
"""T1 — coleta Telnet dos Looking Glasses do IX.br contra um LG falso."""
import asyncio
import json

import pytest

from products.bgp_routes.build import parse_bgp_output, parse_ixp as parse_ixp_
from core import telnet as _telnet
from core.common import ler_texto_bruto
from sources.lg_ixbr import collect as lg_ixbr
from tests.fakes.telnet_lg import FakeLG, LGBehavior

TO = dict(connect_timeout=2.0, idle_timeout=0.6, total_timeout=8.0)


@pytest.fixture()
def texts(fx):
    return (fx("lg_ixbr", "bgp-v4.sample.txt").read_text(encoding="utf-8"),
            fx("lg_ixbr", "bgp-v6.sample.txt").read_text(encoding="utf-8"))


def run(coro):
    return asyncio.run(coro)


def test_v4_coleta_e_parser_entende_o_texto(texts):
    async def go():
        b = LGBehavior(v4_text=texts[0], v6_text=texts[1])
        async with FakeLG(b) as lg:
            r = await _telnet.collect_afi("127.0.0.1", lg.port, "v4", **TO)
            return r, b
    r, b = run(go())
    assert r["status"] == "ok" and r["command"] == "show ip bgp"
    assert b.received[:2] == ["terminal length 0", "show ip bgp"]
    routes = parse_bgp_output(r["text"])
    assert len(routes) >= 10 and all(x["aspath"] for x in routes) and routes[0]["prefix"].count(".") == 3


def test_v6_formato_de_duas_linhas(texts):
    async def go():
        async with FakeLG(LGBehavior(v4_text=texts[0], v6_text=texts[1])) as lg:
            return await _telnet.collect_afi("127.0.0.1", lg.port, "v6", **TO)
    r = run(go())
    assert r["status"] == "ok" and r["command"] == "show bgp ipv6 unicast"
    routes = parse_bgp_output(r["text"])
    assert routes and all(":" in x["prefix"] for x in routes)


def test_firmware_antigo_cai_para_show_ipv6_bgp(texts):
    async def go():
        b = LGBehavior(v4_text=texts[0], v6_text=texts[1], v6_commands=("show ipv6 bgp",))
        async with FakeLG(b) as lg:
            r = await _telnet.collect_afi("127.0.0.1", lg.port, "v6", **TO)
            return r, b
    r, b = run(go())
    assert r["status"] == "ok" and r["command"] == "show ipv6 bgp"


def test_nenhum_comando_valido_devolve_erro(texts):
    async def go():
        b = LGBehavior(v4_text=texts[0], v6_text=texts[1], v6_commands=())
        async with FakeLG(b) as lg:
            return await _telnet.collect_afi("127.0.0.1", lg.port, "v6", **TO)
    r = run(go())
    assert r["status"] == "error" and "no BGP header" in r["error"]


def test_negociacao_iac_e_recusada_e_nao_polui_o_texto(texts):
    async def go():
        b = LGBehavior(v4_text=texts[0], negotiate=True)
        async with FakeLG(b) as lg:
            r = await _telnet.collect_afi("127.0.0.1", lg.port, "v4", **TO)
            return r, b
    r, b = run(go())
    assert bytes([_telnet._IAC, _telnet._WONT, 24]) in b.iac_replies      # DO → WONT
    assert bytes([_telnet._IAC, _telnet._DONT, 1]) in b.iac_replies       # WILL → DONT
    assert "\xff" not in r["text"] and "�" not in r["text"]


def test_sem_marcador_final_encerra_por_inatividade(texts):
    async def go():
        b = LGBehavior(v4_text=texts[0], no_end_marker=True)
        async with FakeLG(b) as lg:
            return await _telnet.collect_afi("127.0.0.1", lg.port, "v4", connect_timeout=2, idle_timeout=0.4, total_timeout=8)
    r = run(go())
    assert r["status"] == "ok" and "Displayed" not in r["text"]


def test_conexao_recusada(texts):
    async def go():
        async with FakeLG(LGBehavior()) as lg:
            port = lg.port
        return await _telnet.collect_afi("127.0.0.1", port, "v4", **TO)
    r = run(go())
    assert r["status"] == "error" and r["error"] == "connection refused"


def test_lg_mudo_responde_vazio_e_vira_erro():
    async def go():
        async with FakeLG(LGBehavior(silent=True)) as lg:
            return await _telnet.collect_afi("127.0.0.1", lg.port, "v4", connect_timeout=2, idle_timeout=0.3, total_timeout=1.0)
    r = run(go())
    assert r["status"] == "error"


@pytest.mark.parametrize("buf, clean, resp, rest", [
    (b"abc", b"abc", b"", b""),
    (bytes([255, 253, 1]) + b"x", b"x", bytes([255, 252, 1]), b""),            # DO → WONT
    (bytes([255, 251, 3]) + b"x", b"x", bytes([255, 254, 3]), b""),            # WILL → DONT
    (bytes([255, 255]) + b"a", bytes([255]) + b"a", b"", b""),                 # IAC IAC literal
    (b"ab" + bytes([255]), b"ab", b"", bytes([255])),                           # sequência truncada
    (bytes([255, 250, 24, 1, 255, 240]) + b"z", b"z", b"", b""),               # sub-negociação
])
def test_process_iac(buf, clean, resp, rest):
    assert _telnet._process_iac(buf) == (clean, resp, rest)


@pytest.mark.parametrize("text, esperado", [
    ("BGP table version is 1\n...", True),
    ("   Network          Next Hop   Metric", True),
    ("% Unknown command: show ipv6 bgp", False),
    ("% No match\nBGP table version", False),
    ("", False),
])
def test_is_valid_bgp_response(text, esperado):
    assert _telnet._is_valid_bgp_response(text) is esperado


def test_run_grava_raw_por_ixp_e_manifesto(base, log, texts, date_str, monkeypatch):
    async def go():
        ok = LGBehavior(v4_text=texts[0], v6_text=texts[1])
        v4only = LGBehavior(v4_text=texts[0], v6_commands=())
        async with FakeLG(ok) as a, FakeLG(v4only) as b:
            monkeypatch.setattr(lg_ixbr, "load_ixps", lambda: [
                {"code": "aa", "telnet_host": "127.0.0.1", "telnet_port": a.port, "timeout": 8},
                {"code": "bb", "telnet_host": "127.0.0.1", "telnet_port": b.port, "timeout": 8},
                {"code": "cc", "telnet_host": "127.0.0.1", "telnet_port": 1, "timeout": 8},      # porta fechada
            ])
            monkeypatch.setattr(lg_ixbr, "load_settings", lambda: {"collection": {"parallel_workers": 3, "connect_timeout": 2}})
            real = lg_ixbr.collect_afi

            async def fast(host, port, afi, connect_timeout, idle_timeout, total_timeout):
                return await real(host, port, afi, connect_timeout, 0.4, total_timeout)   # inatividade curta nos testes

            monkeypatch.setattr(lg_ixbr, "collect_afi", fast)
            return await lg_ixbr.run(date_str, base, None, log)
    res = {r["ixp"]: r for r in run(go())}
    assert res["aa"]["v4"]["status"] == "ok" and res["aa"]["v6"]["status"] == "ok"
    assert res["bb"]["v4"]["status"] == "ok" and res["bb"]["v6"]["status"] == "error"
    assert res["cc"]["v4"]["status"] == "error"
    raw = base / "raw" / date_str
    assert ler_texto_bruto(raw / "aa" / f"bgp-v4-aa-{date_str}.txt.gz").count("Displayed") == 1
    assert not (raw / "bb" / f"bgp-v6-bb-{date_str}.txt.gz").exists()
    man = json.loads((raw / "collection_manifest.json").read_text())
    assert man["total"] == 3 and man["ok"] == 2 and man["failed"] == 1


def test_run_sem_ixps_devolve_lista_vazia(base, log, date_str, monkeypatch):
    monkeypatch.setattr(lg_ixbr, "load_ixps", lambda: [{"code": "aa", "telnet_host": "x"}])
    assert run(lg_ixbr.run(date_str, base, ["zz"], log)) == []


def test_tabela_vazia_e_coleta_valida_com_zero_rotas(fx):
    # IX.br Macapá (2026-10-11): route servers sem prefixos; o FRR responde só "No BGP prefixes displayed"
    empty = fx("lg_ixbr", "bgp-empty.sample.txt").read_text(encoding="utf-8")

    async def go():
        async with FakeLG(LGBehavior(v4_text=empty, v6_text=empty)) as lg:
            return [await _telnet.collect_afi("127.0.0.1", lg.port, afi, **TO) for afi in ("v4", "v6")]
    for r in run(go()):
        assert r["status"] == "ok"
        assert parse_bgp_output(r["text"]) == []


def test_bruto_gz_e_deterministico_e_legivel_com_ou_sem_gz(tmp_path):
    """O bruto novo é .txt.gz com bytes estáveis (hash do armazém); o .txt antigo segue legível."""
    from core.common import gravar_texto_gz, raw_existente
    a, b = tmp_path / "a.txt.gz", tmp_path / "b.txt.gz"
    gravar_texto_gz(a, "linha\n" * 1000)
    import time; time.sleep(1.1)
    gravar_texto_gz(b, "linha\n" * 1000)
    assert a.read_bytes() == b.read_bytes() and a.stat().st_size < 200
    assert ler_texto_bruto(tmp_path / "a.txt") == "linha\n" * 1000          # pede o .txt, acha o .gz
    antigo = tmp_path / "c.txt"
    antigo.write_text("velho")
    assert raw_existente(antigo) == antigo and ler_texto_bruto(antigo) == "velho"


def test_p1_le_o_bruto_comprimido_igual_ao_texto(tmp_path, fx, log):
    """Mesma tabela BGP em .txt (snapshots antigos) e em .txt.gz: o `bgp_ixp` produz o mesmo resultado."""
    from core.common import gravar_texto_gz, normalized_path, raw_path, read_json_gz
    texto = {afi: fx("lg_ixbr", f"bgp-{afi}.sample.txt").read_text(encoding="utf-8") for afi in ("v4", "v6")}
    saidas = {}
    for nome, gz in (("2026-10-01", False), ("2026-10-02", True)):
        rd = raw_path(tmp_path, nome, "sp")
        rd.mkdir(parents=True)
        for afi, t in texto.items():
            alvo = rd / f"bgp-{afi}-sp-{nome}.txt"
            if gz:
                gravar_texto_gz(alvo.with_name(alvo.name + ".gz"), t)
            else:
                alvo.write_text(t, encoding="utf-8")
        parse_ixp_("sp", nome, tmp_path, log)
        saidas[nome] = [read_json_gz(normalized_path(tmp_path, nome, "sp") / f"routes-{afi}.json.gz") for afi in ("v4", "v6")]

    def sem_volateis(x):
        return {k: v for k, v in x.items() if k not in ("date", "snapshot_date", "generated_at", "source_file")} if isinstance(x, dict) else x
    assert [sem_volateis(x) for x in saidas["2026-10-01"]] == [sem_volateis(x) for x in saidas["2026-10-02"]]
    assert saidas["2026-10-02"][0]
