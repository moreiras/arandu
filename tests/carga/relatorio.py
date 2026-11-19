# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Relatório de um teste de carga (tests/carga/rodar.sh): por degrau de usuários, o lado do cliente (Locust), o tempo no servidor (log do
nginx: tempo do upstream, sem a rede), memória e CPU dos contêineres (amostrador) e o canário (navegador real); aplica os critérios
de `cenarios.yaml` (`slo`) e diz qual foi o maior degrau que os cumpriu e se o gerador ou a rede viraram o gargalo.

    python tests/carga/relatorio.py tests/carga/saida/<execução>
"""
from __future__ import annotations

import csv
import glob
import ipaddress
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

AQUI = Path(__file__).resolve().parent
CANARIO = ipaddress.ip_network("198.19.240.0/20")
ABUSIVO = ipaddress.ip_address("198.19.255.254")
NGINX = re.compile(r'^(\S+) - \S+ \[([^\]]+)\] "(\S+) (\S+) [^"]*" (\d{3}) (\d+) .* rt=(\S+) urt=(\S+) cs=(\S*)')


def pct(xs, p):
    if not xs:
        return None
    s = sorted(xs)
    return s[min(len(s) - 1, max(0, int(round(p / 100 * len(s) + 0.5)) - 1))]


def grupo(tipo: str, nome: str) -> str:
    if tipo == "PAGINA":
        return "pagina_carga" if nome.startswith("carga") else "pagina_nav"
    if nome.startswith("mcp tool:"):
        return "mcp_tool"
    if nome.startswith("mcp"):
        return "mcp_sessao"
    if nome.startswith("abuso"):
        return "abuso"
    if nome.startswith("api "):
        return "api_cliente"
    if nome in ("web estatico", "web tiles"):
        return "estaticos"
    return "web_api"


def _seg(v: str) -> float | None:
    """`urt` pode vir com vários upstreams ("0.010, 0.002") ou "-" (cache)."""
    vals = [float(x) for x in re.split(r"[,:\s]+", v) if x and x != "-"]
    return sum(vals) if vals else None


def main(d: Path) -> int:
    ini = json.loads((d / "inicio.json").read_text())
    cfg, t0 = ini["config"], ini["t0"]
    slo = yaml.safe_load((AQUI / "cenarios.yaml").read_text(encoding="utf-8"))["slo"]
    D, degraus = cfg["degrau_s"], cfg["degraus"]
    janelas = [(t0 + k * D + D / 3, t0 + (k + 1) * D) for k in range(len(degraus))]

    def degrau(ts: float):
        for k, (a, b) in enumerate(janelas):
            if a <= ts < b:
                return k
        return None

    # ── cliente ──
    cli = [dict() for _ in degraus]
    bytes_ = [0] * len(degraus)
    for f in glob.glob(str(d / "requisicoes-*.csv")):
        for r in csv.DictReader(open(f)):
            k = degrau(float(r["ts"]))
            if k is None:
                continue
            g = grupo(r["tipo"], r["nome"])
            e = cli[k].setdefault(g, {"ms": [], "n": 0, "falhas": {}})
            e["n"] += 1
            e["ms"].append(float(r["ms"]))
            if r["falha"]:
                cat = r["falha"].split(":")[0] if r["tipo"] != "PAGINA" else "pagina"
                e["falhas"][cat] = e["falhas"].get(cat, 0) + 1
            if r["tipo"] != "PAGINA":
                bytes_[k] += int(r["tamanho"] or 0)
            if r["nome"] == "reconexao":
                e["n"] -= 1                     # tentativa repetida (conexão velha), não conta como requisição

    # ── gerador parado (sleep, travamento): intervalos sem nenhum pedido enquanto havia usuários ──
    ts_todos = sorted(float(r["ts"]) for f in glob.glob(str(d / "requisicoes-*.csv")) for r in csv.DictReader(open(f)))
    paradas = [(a, b) for a, b in zip(ts_todos, ts_todos[1:]) if b - a > 30]
    degraus_com_parada = sorted({k for a, b in paradas for k in range(len(degraus)) if a < janelas[k][1] and b > janelas[k][0]})

    # ── servidor: nginx ──
    srv = [{"api": [], "mcp": [], "cache_hit": 0, "api_n": 0, "status": {}} for _ in degraus]
    if (d / "nginx.log").exists():
        for linha in open(d / "nginx.log", errors="replace"):
            m = NGINX.match(linha)
            if not m:
                continue
            ip, quando, _met, url, st, _b, _rt, urt, cs = m.groups()
            try:
                a = ipaddress.ip_address(ip)
            except ValueError:
                continue
            if a in CANARIO or a == ABUSIVO:
                continue
            k = degrau(datetime.strptime(quando, "%d/%b/%Y:%H:%M:%S %z").timestamp())
            if k is None:
                continue
            s = srv[k]
            s["status"][st] = s["status"].get(st, 0) + 1
            u = _seg(urt)
            if url.startswith("/mcp"):
                if u is not None:
                    s["mcp"].append(u * 1000)
            elif url.startswith(("/api/", "/auth/")):
                s["api_n"] += 1
                if cs in ("HIT", "STALE", "UPDATING"):
                    s["cache_hit"] += 1
                elif u is not None:
                    s["api"].append(u * 1000)

    # ── servidor: amostrador ──
    amo = [{} for _ in degraus]
    if (d / "servidor.jsonl").exists():
        for linha in open(d / "servidor.jsonl"):
            try:
                j = json.loads(linha)
            except ValueError:
                continue
            k = degrau(datetime.fromisoformat(j["ts"].replace("Z", "+00:00")).timestamp())
            if k is None:
                continue
            a = amo[k]
            for c in j.get("containers") or []:
                nome = re.sub(r"^.*?-(api|mcp|frontend|routinator|worker)(-run)?-.*$", r"\1", c["nome"])
                a.setdefault(nome + "_cpu", []).append(c.get("cpu_pct") or 0)
                a.setdefault(nome + "_mem", []).append((c.get("bytes") or 0) / 2 ** 30)
            h = j.get("host") or {}
            if h.get("disponivel_bytes"):
                a.setdefault("host_disp", []).append(h["disponivel_bytes"] / 2 ** 30)

    # ── canário ──
    can = [{"ms": [], "falhas": 0, "erros": 0} for _ in degraus]
    if (d / "canario.jsonl").exists():
        for linha in open(d / "canario.jsonl"):
            j = json.loads(linha)
            k = degrau(j["ts"])
            if k is None:
                continue
            can[k]["ms"].append(j["ms"])
            can[k]["falhas"] += 0 if j["ok"] else 1
            can[k]["erros"] += j.get("erros_console", 0)

    rede = json.loads((d / "rede.json").read_text()) if (d / "rede.json").exists() else {}
    log = (d / "locust.log").read_text(errors="replace") if (d / "locust.log").exists() else ""
    cpu_gerador = "CPU usage above" in log or "CPU usage was too high" in log

    linhas, resumo = [], []
    for k, n in enumerate(degraus):
        dur = janelas[k][1] - janelas[k][0]
        c, s, a, cn = cli[k], srv[k], amo[k], can[k]
        normais = [g for g in c if g not in ("abuso", "pagina_carga", "pagina_nav")]
        tot = sum(c[g]["n"] for g in normais)
        falhas = {}
        for g in normais:
            for cat, q in c[g]["falhas"].items():
                falhas[cat] = falhas.get(cat, 0) + q
        falha_pct = 100 * sum(falhas.values()) / tot if tot else None
        r = {
            "usuarios": n, "req_s": round(tot / dur, 1) if dur else None, "falhas_pct": None if falha_pct is None else round(falha_pct, 2),
            "falhas": falhas,
            "cli_web_api_p95": pct(c.get("web_api", {}).get("ms", []), 95), "cli_mcp_p95": pct(c.get("mcp_tool", {}).get("ms", []), 95),
            "cli_pagina_nav_p95": pct(c.get("pagina_nav", {}).get("ms", []), 95), "cli_pagina_carga_p95": pct(c.get("pagina_carga", {}).get("ms", []), 95),
            "srv_api_p50": pct(s["api"], 50), "srv_api_p95": pct(s["api"], 95), "srv_api_p99": pct(s["api"], 99),
            "srv_mcp_p95": pct(s["mcp"], 95), "srv_cache_hit_pct": round(100 * s["cache_hit"] / s["api_n"], 1) if s["api_n"] else None,
            "api_cpu_med": round(sum(a["api_cpu"]) / len(a["api_cpu"]), 0) if a.get("api_cpu") else None,
            "api_cpu_max": max(a["api_cpu"]) if a.get("api_cpu") else None,
            "api_mem_max": round(max(a["api_mem"]), 2) if a.get("api_mem") else None,
            "mcp_mem_max": round(max(a["mcp_mem"]), 2) if a.get("mcp_mem") else None,
            "mcp_cpu_max": max(a["mcp_cpu"]) if a.get("mcp_cpu") else None,
            "host_disp_min": round(min(a["host_disp"]), 2) if a.get("host_disp") else None,
            "canario_p95": pct(cn["ms"], 95), "canario_falhas": cn["falhas"], "canario_erros_console": cn["erros"],
            "abuso_429_pct": round(100 * c["abuso"]["falhas"].get("429_limite", 0) / c["abuso"]["n"], 1) if c.get("abuso", {}).get("n") else None,
            "MBps_recebidos": round(bytes_[k] / dur / 1e6, 2) if dur else None,
        }
        if c.get("abuso", {}).get("n"):
            r["abuso_req_s"] = round(c["abuso"]["n"] / dur, 1)
        crit = {
            "servidor_api_p95": r["srv_api_p95"] is None or r["srv_api_p95"] <= slo["servidor_api_p95_ms"],
            "servidor_mcp_p95": r["srv_mcp_p95"] is None or r["srv_mcp_p95"] <= slo["servidor_mcp_p95_ms"],
            "falhas": r["falhas_pct"] is None or r["falhas_pct"] <= slo["falhas_pct"],
            "canario_p95": r["canario_p95"] is None or r["canario_p95"] <= slo["canario_p95_ms"],
        }
        r["gerador_parado"] = k in degraus_com_parada
        if r["gerador_parado"]:
            crit["gerador"] = False                 # degrau contaminado: não vale como medida do alvo
        r["criterios_ok"] = all(crit.values())
        r["criterios_falhos"] = [x for x, ok in crit.items() if not ok]
        # gerador ou rede no limite: o cliente espera muito mais que o servidor e a ida e volta somados (os bytes do Locust são os
        # descomprimidos, não servem para comparar com a banda medida)
        rtt = rede.get("health_ms_mediana") or 0
        cli50, srv50 = pct(c.get("web_api", {}).get("ms", []), 50), r["srv_api_p50"]
        r["cli_web_api_p50"] = cli50
        r["gerador_no_limite_da_rede"] = bool(cli50 and srv50 is not None and cli50 > 3 * (rtt + srv50) and cli50 > 1000)
        resumo.append(r)

    capacidade = None
    for r in resumo:
        if not r["criterios_ok"]:
            break
        capacidade = r["usuarios"]

    f = lambda v, suf="": "—" if v is None else f"{v:.0f}{suf}" if isinstance(v, float) else f"{v}{suf}"   # noqa: E731
    md = [f"# Teste de carga: {ini['cenario']}", "",
          f"- {cfg.get('descricao', '')}",
          f"- Alvo: versão {rede.get('versao')}, snapshot {rede.get('snapshot')}; pipeline rodando: "
          f"{(d / 'pipeline_rodando.txt').read_text().strip() if (d / 'pipeline_rodando.txt').exists() else '?'}",
          f"- Rede do gerador ao alvo: /health em {rede.get('health_ms_mediana')} ms (mediana), banda {rede.get('banda_MBps')} MB/s. "
          "Tempos do **cliente** incluem essa rede; os do **servidor** (nginx, tempo do upstream) não.",
          f"- Degraus de {D} s; medido o trecho depois do primeiro terço de cada um (a subida fica de fora).",
          f"- Critérios: servidor API p95 ≤ {slo['servidor_api_p95_ms']} ms, MCP p95 ≤ {slo['servidor_mcp_p95_ms']} ms, falhas ≤ "
          f"{slo['falhas_pct']}%, canário p95 ≤ {slo['canario_p95_ms']} ms.",
          f"- **Maior degrau dentro dos critérios: {capacidade if capacidade is not None else 'nenhum'} usuários simultâneos.**", ""]
    if paradas:
        md.append(f"- ⚠ O gerador ficou parado (nenhum pedido por mais de 30 s) {len(paradas)} vez(es), somando "
                  f"{sum(b - a for a, b in paradas) / 60:.1f} min, nos degraus de {', '.join(str(degraus[k]) for k in degraus_com_parada)} "
                  "usuários: esses degraus não valem (sleep do Mac, travamento do gerador ou da rede).")
    if cpu_gerador:
        md.append("- ⚠ O Locust avisou CPU alta no gerador: os degraus finais medem o gerador, não o alvo (use `--processos N`).")
    if any(r["gerador_no_limite_da_rede"] for r in resumo):
        md.append("- ⚠ Em algum degrau o cliente esperou bem mais que o servidor e a rede somados: o gerador ou a rede dele é o gargalo.")
    md += ["", "| usuários | req/s | falhas % | srv API p50/p95/p99 ms | srv MCP p95 ms | cache nginx % | cli página nav p95 ms | "
           "canário p95 ms | API CPU méd/máx % | API mem GiB | MCP mem GiB | host livre GiB | MB/s (descomprimido) | ok |",
           "|---" * 14 + "|"]
    for r in resumo:
        md.append(f"| {r['usuarios']} | {f(r['req_s'])} | {r['falhas_pct'] if r['falhas_pct'] is not None else '—'} | "
                  f"{f(r['srv_api_p50'])}/{f(r['srv_api_p95'])}/{f(r['srv_api_p99'])} | {f(r['srv_mcp_p95'])} | {f(r['srv_cache_hit_pct'])} | "
                  f"{f(r['cli_pagina_nav_p95'])} | {f(r['canario_p95'])} | {f(r['api_cpu_med'])}/{f(r['api_cpu_max'])} | "
                  f"{r['api_mem_max'] if r['api_mem_max'] is not None else '—'} | {r['mcp_mem_max'] if r['mcp_mem_max'] is not None else '—'} | "
                  f"{r['host_disp_min'] if r['host_disp_min'] is not None else '—'} | {r['MBps_recebidos']} | "
                  f"{'sim' if r['criterios_ok'] else 'não: ' + ', '.join(r['criterios_falhos'])} |")
    falhas = {}
    for r in resumo:
        for k, v in r["falhas"].items():
            falhas[k] = falhas.get(k, 0) + v
    if falhas:
        md += ["", "Falhas por tipo (todos os degraus): " + ", ".join(f"{k} {v}" for k, v in sorted(falhas.items()))]
    if any(r.get("abuso_req_s") for r in resumo):
        md += ["", "Abusivo (um IP): " + "; ".join(f"{r['usuarios']} usuários: {r['abuso_req_s']} req/s, {r['abuso_429_pct']}% recusadas"
                                                  for r in resumo if r.get("abuso_req_s"))]
    (d / "relatorio.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (d / "resumo.json").write_text(json.dumps({"cenario": ini["cenario"], "capacidade": capacidade, "rede": rede, "degraus": resumo},
                                              ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
