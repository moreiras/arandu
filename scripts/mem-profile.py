#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Perfil de memória da API sobre um `data/` local. Uso offline: não toca em produção.

    python3 scripts/mem-profile.py [--data-dir data] [--date AAAA-MM-DD] [--sample 64] [--json out.json]
    python3 scripts/mem-profile.py --workers 1,2,4 [--data-dir data]      # custo de N processos uvicorn

Modo padrão: sobe a API real (FastAPI + lifespan) em processo, mede o RSS depois de cada etapa — importação,
aquecimento do lifespan, prewarm em segundo plano, cada rota típica — e fecha com o relatório por cache do
`/api/v1/internal/diag?deep=1`. Modo `--workers`: sobe N processos `uvicorn` e soma a memória de todos
(PSS em Linux, que divide páginas compartilhadas; RSS em macOS, que as conta N vezes).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
MiB = 1048576


def rss_mib(pid: int | None = None) -> float:
    pid = pid or os.getpid()
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024
    except OSError:
        pass
    out = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    return int(out) / 1024 if out else 0.0


def pss_mib(pid: int) -> float | None:
    try:
        for line in Path(f"/proc/{pid}/smaps_rollup").read_text().splitlines():
            if line.startswith("Pss:"):
                return int(line.split()[1]) / 1024
    except OSError:
        return None
    return None


def trim_malloc() -> bool:
    """glibc: devolve ao SO as páginas livres retidas pelo alocador. Só em Linux (macOS não tem)."""
    try:
        import ctypes

        libc = ctypes.CDLL("libc.so.6")
        libc.malloc_trim(0)
        return True
    except (OSError, AttributeError):
        return False


def children(pid: int) -> list[int]:
    """Filhos diretos de `pid`: /proc em Linux (a imagem slim não tem `pgrep`), `pgrep` no macOS."""
    proc = Path("/proc")
    if proc.exists():
        out = []
        for d in proc.iterdir():
            if d.name.isdigit():
                try:
                    stat = (d / "stat").read_text()
                    ppid = int(stat.rsplit(")", 1)[1].split()[1])
                except (OSError, ValueError, IndexError):
                    continue
                if ppid == pid:
                    out.append(int(d.name))
        return sorted(out)
    out = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True).stdout.split()
    return [int(x) for x in out]


def env_for(data_dir: Path) -> dict:
    e = dict(os.environ)
    e.update({"DATA_DIR": str(data_dir), "JWT_SECRET": "perfil-de-memoria-perfil-de-memoria-12", "GOOGLE_CLIENT_ID": "a",
              "GOOGLE_CLIENT_SECRET": "b", "APP_BASE_URL": "http://localhost", "ACCESS_POLICY_MODE": "off",
              "USAGE_LOG": "off", "ALLOWED_IPS": "127.0.0.1/32", "INTERNAL_API_TOKEN": "perfil"})
    return e


ROUTES = ["/api/v1/brasil/snapshots", "/api/v1/ixps", "/api/v1/asns?limit=50", "/api/v1/asns/names", "/api/v1/asns/ix-presence",
          "/api/v1/cdns/presence", "/api/v1/hilbert/v4", "/api/v1/hilbert/v6", "/api/v1/map/asns", "/api/v1/map/prefixes",
          "/api/v1/map/scms", "/api/v1/map/rodovias", "/api/v1/scms?limit=20", "/api/v1/acessos/stats",
          "/api/v1/acessos/operadoras?limit=20", "/api/v1/acessos/municipios", "/api/v1/rpki/summary",
          "/api/v1/bgp-stability/summary", "/api/v1/routing-analysis", "/api/v1/asns/by-organization"]


def top_allocations(n: int = 15) -> list[dict]:
    import tracemalloc

    snap = tracemalloc.take_snapshot().filter_traces((tracemalloc.Filter(False, "<frozen importlib._bootstrap*"),
                                                      tracemalloc.Filter(False, "<unknown>")))
    out = []
    for st in snap.statistics("lineno")[:n]:
        f = st.traceback[0]
        out.append({"onde": f"{Path(f.filename).name}:{f.lineno}", "arquivo": f.filename, "mib": round(st.size / MiB, 1),
                    "blocos": st.count})
    return out


def top_by_file(n: int = 12) -> list[dict]:
    import tracemalloc

    snap = tracemalloc.take_snapshot().filter_traces((tracemalloc.Filter(False, "<frozen importlib._bootstrap*"),
                                                      tracemalloc.Filter(False, "<unknown>")))
    return [{"arquivo": str(st.traceback[0].filename).split("site-packages/")[-1].replace(str(ROOT) + "/", ""),
             "mib": round(st.size / MiB, 1)} for st in snap.statistics("filename")[:n]]


def single_process(args) -> dict:
    data = Path(args.data_dir).resolve()
    os.environ.update(env_for(data))
    if args.tracemalloc:
        import tracemalloc

        tracemalloc.start(1)      # 1 frame: com mais, o overhead estoura a RAM do Docker (visto: Killed)
    steps: list[tuple[str, float]] = [("processo vazio (Python)", rss_mib())]
    from fastapi.testclient import TestClient

    import api.main as main

    steps.append(("após importar a aplicação", rss_mib()))
    date = args.date or ""
    with TestClient(main.app, raise_server_exceptions=False) as c:
        steps.append(("após o lifespan (Store + warm-up)", rss_mib()))
        for _ in range(args.settle):                      # prewarm roda em tarefas de segundo plano
            time.sleep(1)
        steps.append((f"após {args.settle} s (prewarm do latest e dos ASNs mais acessados)", rss_mib()))
        alloc_warm = {"linhas": top_allocations(), "arquivos": top_by_file()} if args.tracemalloc else None
        extras = [x for x in args.extra.split(",") if x]
        hdr_int = {"X-Internal-Token": "perfil"}
        hdr = {"X-Real-IP": "127.0.0.1", "Accept-Encoding": "gzip"}
        dq = f"?date={date}" if date else ""
        if "warmup" in extras:                  # o `POST /warmup` do restart-safe: dispara prewarm DE NOVO
            r = c.post(f"/api/v1/warmup{dq}", headers=hdr_int)
            for _ in range(args.settle):
                time.sleep(1)
            steps.append((f"após POST /warmup (reforço do restart-safe) → {r.status_code}", rss_mib()))
        if "nginxwarm" in extras:               # os 9 caminhos que o restart-safe aquece pelo nginx
            for pth in ("ixps", "external-ixps", "cdns/presence", "asns", "asns/names", "hilbert/v4", "hilbert/v6",
                        "map/asns", "map/prefixes"):
                c.get(f"/api/v1/{pth}{dq}", headers=hdr)
            steps.append(("após os 9 endpoints do aquecimento do nginx", rss_mib()))
        if "potential" in extras:               # /ixps/{code}/potential de cada PTT (40 em produção)
            codes = [i["code"] for i in c.get(f"/api/v1/ixps{dq}", headers=hdr).json().get("ixps", [])]
            for code in codes:
                c.get(f"/api/v1/ixps/{code}/potential{dq}", headers=hdr)
            steps.append((f"após /potential de {len(codes)} PTTs", rss_mib()))
        if args.only_warmup:
            rep = c.get("/api/v1/internal/diag?deep=1&sample=%d" % args.sample, headers={"X-Internal-Token": "perfil"}).json()
            return {"data_dir": str(data), "etapas": [{"etapa": n, "rss_mib": round(v)} for n, v in steps], "diag": rep,
                    "tracemalloc": alloc_warm}
        h = {"X-Real-IP": "127.0.0.1"}
        q = f"&date={date}" if date else ""
        for r in ROUTES:
            sep = "&" if "?" in r else "?"
            resp = c.get(r + (f"{sep}date={date}" if date and "date=" not in r else ""), headers=h)
            steps.append((f"GET {r} → {resp.status_code}, {len(resp.content) / MiB:.1f} MiB", rss_mib()))
        resp = c.post("/api/v1/map/query", json={}, headers=h)
        steps.append((f"POST /map/query {{}} → {resp.status_code}", rss_mib()))
        rep = c.get(f"/api/v1/internal/diag?deep=1&sample={args.sample}", headers={"X-Internal-Token": "perfil"}).json()
        steps.append(("após o diagnóstico profundo", rss_mib()))
        alloc = {"linhas": top_allocations(), "arquivos": top_by_file()} if args.tracemalloc else None
        import gc

        gc.collect()
        steps.append(("após gc.collect()", rss_mib()))
        trimmed = trim_malloc()
        if trimmed:
            steps.append(("após malloc_trim(0) — memória livre que o alocador (glibc) devolve ao SO", rss_mib()))
    return {"data_dir": str(data), "etapas": [{"etapa": n, "rss_mib": round(v)} for n, v in steps], "diag": rep,
            "tracemalloc": alloc}


def workers(args) -> dict:
    data = Path(args.data_dir).resolve()
    results = []
    for n in [int(x) for x in args.workers.split(",")]:
        port = 8700 + n
        p = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", str(port),
                              "--workers", str(n), "--log-level", "warning"], cwd=ROOT, env=env_for(data),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(180):
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2).read()
                    break
                except Exception:  # noqa: BLE001
                    time.sleep(1)
            # cada worker aquece sozinho; manda tráfego suficiente para que todos toquem os mesmos caches
            for _ in range(n * 6):
                for r in ROUTES[:8]:
                    try:
                        urllib.request.urlopen(f"http://127.0.0.1:{port}{r}", timeout=60).read()
                    except Exception:  # noqa: BLE001
                        pass
            time.sleep(args.settle)
            pids = children(p.pid) or [p.pid]
            rss = [rss_mib(x) for x in pids]
            pss = [pss_mib(x) for x in pids]
            results.append({"workers": n, "pids": pids, "rss_mib_por_processo": [round(x) for x in rss],
                            "rss_mib_total": round(sum(rss)),
                            "pss_mib_total": round(sum(x for x in pss if x)) if all(x is not None for x in pss) else None})
        finally:
            p.terminate()
            p.wait(timeout=30)
    return {"data_dir": str(data), "workers": results}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-dir", default=str(ROOT / "data"))
    ap.add_argument("--date", default="")
    ap.add_argument("--sample", type=int, default=64)
    ap.add_argument("--settle", type=int, default=45, help="segundos esperando o prewarm em segundo plano")
    ap.add_argument("--workers", help="lista, ex.: 1,2,4 (mede N processos uvicorn)")
    ap.add_argument("--tracemalloc", action="store_true",
                    help="liga o tracemalloc (5 a 10x mais lento, mais RAM): mostra QUAIS linhas alocam a memória viva")
    ap.add_argument("--extra", default="", help="reproduz a sequência do restart-safe: warmup,nginxwarm,potential")
    ap.add_argument("--only-warmup", action="store_true", help="para depois do prewarm (poupa memória no --tracemalloc)")
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    out = workers(args) if args.workers else single_process(args)
    if args.json:
        Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    if args.workers:
        print(f"{'workers':>8} {'RSS total (MiB)':>16} {'PSS total (MiB)':>16}  RSS por processo")
        for r in out["workers"]:
            print(f"{r['workers']:>8} {r['rss_mib_total']:>16} {str(r['pss_mib_total'] or '-'):>16}  {r['rss_mib_por_processo']}")
        return 0
    print(f"dados: {out['data_dir']}")
    for e in out["etapas"]:
        print(f"  {e['rss_mib']:>6} MiB  {e['etapa']}")
    st = out["diag"]["store"]
    print(f"\ndatas residentes: {st['datas_residentes']} | total estimado dos caches do Store: "
          f"{st.get('total_bytes_estimados', 0) / MiB:.0f} MiB")
    print(f"{'MiB':>8} {'entradas':>9}  cache")
    for c in st["caches"][:15]:
        print(f"{c.get('bytes_estimados', 0) / MiB:>8.0f} {c['entradas']:>9}  {c['nome']} {c.get('datas', '')}")
    if out.get("tracemalloc"):
        print("\nmemória viva por linha de código (tracemalloc):")
        for a in out["tracemalloc"]["linhas"]:
            print(f"{a['mib']:>8.1f} MiB {a['blocos']:>9} blocos  {a['onde']}  ({a['arquivo'].replace(str(ROOT) + '/', '')})")
        print("\npor arquivo:")
        for a in out["tracemalloc"]["arquivos"]:
            print(f"{a['mib']:>8.1f} MiB  {a['arquivo']}")
    print("\ncaches em escopo de MÓDULO (fora do Store):")
    print(f"{'MiB':>8} {'entradas':>9}  nome")
    for c in out["diag"].get("caches_de_modulo", [])[:12]:
        print(f"{c.get('bytes_estimados', 0) / MiB:>8.0f} {c['entradas']:>9}  {c['nome']} ({c['tipo']})")
    if out["diag"].get("histograma_de_tipos"):
        print("\nobjetos vivos por tipo (gc; bytes rasos):")
        for h in out["diag"]["histograma_de_tipos"][:10]:
            print(f"{h['bytes_rasos'] / MiB:>8.0f} MiB {h['objetos']:>10} objetos  {h['tipo']}")
    pm = out["diag"].get("pymalloc")
    if pm:
        vivos, total = pm.get("bytes_em_blocos_vivos", 0), pm.get("bytes_arenas_reservadas", 0)
        print(f"\nalocador de objetos do Python (pymalloc): {vivos / MiB:.0f} MiB em blocos vivos de {total / MiB:.0f} MiB "
              f"reservados em {pm.get('arenas_atuais', '?')} arenas → fragmentação {pm.get('fragmentacao_pct', '?')}%")
    bc = out["diag"].get("byte_cache_latest") or {}
    print(f"\nbyte-cache do latest: {bc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
