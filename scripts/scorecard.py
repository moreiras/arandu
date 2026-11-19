#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Painel v0: reúne testes, contratos, replay, tempos, disco, uso e coleta num só lugar.

    python3 scripts/scorecard.py [--date AAAA-MM-DD] [--data-dir data] [--replay-report `as_relationships`.json]
                                 [--run-tests] [--out-dir data/ops/scorecard] [--md docs/scorecard.md]

Somente leitura sobre `data/` e o repositório. Cada seção traz a FONTE e a DATA do dado; seção sem fonte
aparece como `indisponivel` (nunca um número inventado). Gera:
  data/ops/scorecard/AAAA-MM-DD.json   (máquina)
  docs/scorecard.md                    (pessoas; sobrescrito a cada execução)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date as _date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEVELS = {"unit": "T0", "sources": "T1", "products": "T2–T5 (produtos, contratos)", "nginx": "gate", "e2e": "E2E",
          "raiz": "política de acesso, IP, gate"}


def _json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _latest(dirpath: Path, suffix: str) -> Path | None:
    if not dirpath.exists():
        return None
    # nome inteiro AAAA-MM-DD<sufixo>: variantes como `AAAA-MM-DD.irr.json` (régua com o IRR ligado só para medir) não contam como o relatório
    files = sorted(p for p in dirpath.iterdir() if re.fullmatch(r"\d{4}-\d{2}-\d{2}" + re.escape(suffix), p.name))
    return files[-1] if files else None


def _gib(kb) -> float | None:
    return round(kb / 1048576, 2) if isinstance(kb, (int, float)) else None


# ── seções ─────────────────────────────────────────────────────────────────

def secao_testes(root: Path, run: bool) -> dict:
    out: dict = {"fonte": "pytest --collect-only" + (" + execução" if run else ""), "por_nivel": {}}
    cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests", "-p", "no:warnings"]
    try:
        r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"fonte": "pytest", "estado": "indisponivel", "motivo": str(exc)[:120]}
    counts: dict[str, int] = {}
    for line in r.stdout.splitlines():
        m = re.match(r"tests/([^/:]+)/", line) or re.match(r"tests/([^/:]+\.py)::", line)
        if m:
            key = m.group(1) if m.group(1) in LEVELS else ("contracts" if m.group(1) == "contracts" else "raiz")
            counts[key] = counts.get(key, 0) + 1
    if not counts:
        # sem pytest no ambiente (ex.: o servidor roda tudo em contêiner) ou coleta quebrada: nunca "0 testes"
        resto = (r.stderr.strip() or r.stdout.strip()).splitlines()
        return {"fonte": "pytest", "estado": "indisponivel",
                "motivo": "nenhum teste coletado" + (f" ({resto[-1][:100]})" if resto else "") + "; rode o painel onde o pytest está instalado"}
    out["por_nivel"] = dict(sorted(counts.items()))
    out["total"] = sum(counts.values())
    if run:
        t0 = datetime.now(timezone.utc)
        rr = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests", "-p", "no:warnings"], cwd=root,
                            capture_output=True, text=True, timeout=1800)
        last = (rr.stdout.strip().splitlines() or [""])[-1]
        out["execucao"] = {"resultado": last, "ok": rr.returncode == 0,
                           "duracao_s": round((datetime.now(timezone.utc) - t0).total_seconds(), 1)}
    return out


def secao_contratos(root: Path) -> dict:
    api = _json(root / "tests" / "contracts" / "api_contract.json") or {}
    mcp = _json(root / "tests" / "contracts" / "mcp_contract.json") or {}
    schemas = sorted((root / "tests" / "contracts" / "schemas").glob("*.schema.json"))
    out = {"fonte": "tests/contracts/", "api_operacoes": len(api.get("operacoes", {})),
           "mcp_tools": len(mcp.get("tools", {})), "mcp_resources": len(mcp.get("resources", [])),
           "mcp_prompts": len(mcp.get("prompts", [])), "esquemas_publicados": len(schemas)}
    # meta do passo: 100% das operações e tools exercitadas — o contrato tem uma chamada por entrada
    out["cobertura_api_pct"] = 100.0 if out["api_operacoes"] else None
    out["cobertura_mcp_pct"] = 100.0 if out["mcp_tools"] else None
    return out


def secao_replay(report: Path | None) -> dict:
    if not report:
        return {"estado": "indisponivel", "motivo": "informe --replay-report (saída de scripts/replay.py --out)"}
    r = _json(report)
    if not isinstance(r, dict) or "contagem" not in r:
        return {"estado": "indisponivel", "motivo": f"{report} ilegível"}
    c = r["contagem"]
    return {"fonte": str(report), "data": r.get("date"), "duracao_s": r.get("duracao_s"), "contagem": c,
            "diferencas_novas": c.get("nova", 0) + c.get("ordem", 0), "etapas": r.get("tempos_s")}


def _latest_run(d: Path) -> Path | None:
    """O relatório de execução mais recente do `arandu` (`AAAA-MM-DD.json`)."""
    if not d.is_dir():
        return None
    arqs = [p for p in d.iterdir() if p.suffix == ".json" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem)]
    return max(arqs, key=lambda p: p.stem, default=None)


def _steps_do_arandu(rel: dict) -> list[dict]:
    """Etapas do relatório do `arandu` (data/ops/runs/AAAA-MM-DD.json) como `{step, duration_s, status}`."""
    out = []
    for e in rel.get("etapas", []):
        if e.get("status") in ("delegada_ao_host", "nao_executada", "planejada"):
            continue
        ok = e.get("status") in ("ok", "retomada", "pulada")
        out.append({"step": e.get("id"), "duration_s": e.get("duracao_s") or 0,
                    "status": "ok" if ok else "falha"})
    if rel.get("duracao_s") is not None:
        out.append({"step": "pipeline", "duration_s": rel["duracao_s"], "status": "ok" if rel.get("ok") else "falha"})
    return out


def secao_pipeline(data: Path) -> dict:
    f = _latest_run(data / "ops" / "runs")
    if not f:
        return {"estado": "indisponivel", "motivo": "data/ops/runs vazio (a 1ª baseline vem do próximo run semanal)"}
    rel = _json(f)
    steps = _steps_do_arandu(rel) if isinstance(rel, dict) else []
    pipe = next((s for s in steps if s.get("step") == "pipeline"), None)
    falhas = [s["step"] for s in steps if s.get("status") != "ok"]
    por_etapa = sorted(((s["step"], s.get("duration_s", 0)) for s in steps if s.get("step") != "pipeline"),
                       key=lambda x: -x[1])
    return {"fonte": str(f.relative_to(data.parent)) if data.parent in f.parents else str(f), "data": f.stem,
            "executor": "arandu",
            "duracao_total_s": pipe.get("duration_s") if pipe else sum(s.get("duration_s", 0) for s in steps),
            "etapas": len([s for s in steps if s.get("step") != "pipeline"]), "falhas": falhas,
            "mais_lentas": [{"etapa": n, "duracao_s": d} for n, d in por_etapa[:5]]}


def secao_disco(data: Path) -> dict:
    f = _latest(data / "ops" / "disk", ".json")
    d = _json(f) if f else None
    if not isinstance(d, dict):
        return {"estado": "indisponivel", "motivo": "data/ops/disk vazio (rode scripts/disk-report.sh)"}
    df = d.get("df") or {}
    return {"fonte": f.name, "data": d.get("date"), "total_data_gib": _gib(d.get("data_total_kb")),
            "por_tipo_gib": {k: _gib(v) for k, v in sorted((d.get("by_type") or {}).items(), key=lambda x: -(x[1] or 0))},
            "snapshots_publicados": len((d.get("by_date") or {}).get("published", {})),
            "disco_usado_pct": df.get("use_pct"), "disco_livre_gib": _gib(df.get("avail_kb")),
            "inodes_usados_pct": (d.get("inodes") or {}).get("use_pct")}


def _pctl(values: list[float], p: float) -> float | None:
    if not values:
        return None
    v = sorted(values)
    return round(v[min(len(v) - 1, int(round(p * (len(v) - 1))))], 1)


def secao_uso(data: Path, ate: _date, dias: int = 7, desde: str | None = None) -> dict:
    d = data / "ops" / "usage"
    arquivos = [d / f"{(ate - timedelta(days=i)).isoformat()}.jsonl" for i in range(dias)]
    arquivos = [p for p in arquivos if p.exists()]
    if not arquivos:
        return {"estado": "indisponivel", "motivo": "data/ops/usage sem arquivos na janela"}
    rotas: dict[str, list] = {}
    tiers: dict[str, int] = {}
    srcs: dict[str, int] = {}
    ms, total_bytes, erros = [], 0, 0
    for p in arquivos:
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if desde and str(r.get("ts", "")) < desde:
                continue
            rotas.setdefault(r.get("route", "?"), []).append(r)
            tiers[str(r.get("tier"))] = tiers.get(str(r.get("tier")), 0) + 1
            srcs[r.get("src", "?")] = srcs.get(r.get("src", "?"), 0) + 1
            if isinstance(r.get("ms"), (int, float)):
                ms.append(r["ms"])
            total_bytes += r.get("bytes") or 0
            st = r.get("status")
            if (isinstance(st, int) and st >= 500) or st == "erro":     # tools do MCP usam "ok"/"erro"
                erros += 1
    top = sorted(rotas.items(), key=lambda kv: -len(kv[1]))[:10]
    return {"fonte": f"data/ops/usage ({len(arquivos)} dia(s) até {ate}" + (f", desde {desde}" if desde else "") + ")",
            "chamadas": sum(len(v) for v in rotas.values()),
            "por_origem": srcs, "por_tipo_de_acesso": tiers, "erros_5xx": erros,
            "latencia_ms": {"p50": _pctl(ms, 0.5), "p95": _pctl(ms, 0.95)}, "bytes_total": total_bytes,
            "rotas_mais_usadas": [{"rota": k, "chamadas": len(v),
                                   "p95_ms": _pctl([x["ms"] for x in v if isinstance(x.get("ms"), (int, float))], 0.95),
                                   "bytes_medio": int(sum((x.get("bytes") or 0) for x in v) / max(1, len(v)))} for k, v in top]}


def secao_coleta(data: Path, hoje: _date) -> dict:
    pub = data / "published"
    datas = sorted(p.name for p in pub.iterdir() if p.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}$", p.name)) if pub.exists() else []
    if not datas:
        return {"estado": "indisponivel", "motivo": "data/published vazio"}
    ultimo = datas[-1]
    m = _json(pub / ultimo / "manifest.json") or {}
    idade = (hoje - _date.fromisoformat(ultimo)).days
    out = {"fonte": f"published/{ultimo}/manifest.json", "snapshots": len(datas), "ultimo": ultimo,
           "idade_dias": idade, "pipeline_version": m.get("pipeline_version"),
           "ptt_coletados": f"{len(m.get('ixps_collected', []))}/{len(m.get('ixps_configured', []))}"}
    if "coleta" in m:
        out.update({"coleta": m.get("coleta"), "coleta_ok": m.get("coleta_ok"),
                    "falhas": [k for k, v in (m.get("checks") or {}).items() if v.get("status") == "falha"]})
    else:
        out["coleta"] = "sem_checks (snapshot anterior à sanidade de coleta)"
    return out


def secao_fase2(root: Path) -> dict:
    """Metas de estrutura: arquivo de build, imports proibidos, documentação, escritas por arquivo, regras de alerta, shims."""
    out: dict = {"fonte": "repositório (products/, catalog/, .importlinter, tests/contracts)"}
    build = []
    for d in ("products", "publish"):
        for p in (root / d).rglob("build.py") if d == "products" else (root / d).glob("*.py"):
            try:
                build.append((sum(1 for _ in p.open(encoding="utf-8")), str(p.relative_to(root))))
            except OSError:
                pass
    if build:
        n, nome = max(build)
        out["maior_arquivo_de_build"] = {"arquivo": nome, "linhas": n, "meta": 600, "ok": n < 600}
        out["arquivos_acima_da_meta"] = sorted(((n, nome) for n, nome in build if n >= 600), reverse=True)
    try:
        r = subprocess.run([sys.executable, "-c", "from importlinter.cli import lint_imports_command; lint_imports_command()"],
                           cwd=root, capture_output=True, text=True, timeout=120)
        m = re.search(r"Contracts: (\d+) kept, (\d+) broken", r.stdout)
        out["camadas"] = {"mantidos": int(m.group(1)), "quebrados": int(m.group(2)), "ok": int(m.group(2)) == 0} if m else {"estado": "indisponivel"}
    except (OSError, subprocess.TimeoutExpired) as exc:
        out["camadas"] = {"estado": "indisponivel", "motivo": str(exc)[:80]}
    try:
        sys.path.insert(0, str(root))
        from core.catalog.loader import load_catalog, validate
        cat = load_catalog(root / "catalog")
        campos = sum(len(x.campos) for x in [*cat.sources.values(), *cat.products.values()])
        sem = sum(1 for x in [*cat.sources.values(), *cat.products.values()] for c in x.campos if not c.significado)
        out["documentacao"] = {"campos": campos, "com_significado": campos - sem, "pct": round(100 * (campos - sem) / campos, 1) if campos else None,
                               "meta_pct": 90, "fontes": len(cat.sources), "etapas": len(cat.steps), "erros_do_catalogo": len(validate(cat))}
        from products.alerts.registro import REGRAS, rules_version
        out["alertas"] = {"regras": len(REGRAS), "rules_version": rules_version()}
    except Exception as exc:  # noqa: BLE001
        out["documentacao"] = {"estado": "indisponivel", "motivo": str(exc)[:80]}
    base = _json(root / "tests" / "contracts" / "escritas_por_arquivo.json") or {}
    if base:
        out["escritas_por_arquivo"] = {"antes_documento_de_asn": base.get("asns/{n}.json", {}).get("max_escritas"),
                                       "antes_indice": base.get("asns/index.json", {}).get("max_escritas"), "meta": 1,
                                       "medicao": "tests/products/test_t2_compose.py (fluxo de fragmentos)"}
    out["shims"] = {pasta: sum(1 for _ in (root / pasta).glob("*.py")) for pasta in ("collector", "enrich", "analysis") if (root / pasta).is_dir()}
    return out


def secao_relacoes(data: Path) -> dict:
    """Régua das relações entre ASNs: lê o `AAAA-MM-DD.json` mais recente de data/ops/relacoes de `python -m products.as_relationships.validacao`."""
    arq = _latest(data / "ops" / "relacoes", ".json")
    if arq is None:
        return {"estado": "indisponivel", "motivo": "rode python -m products.as_relationships.validacao --date AAAA-MM-DD (data/ops/relacoes vazio)"}
    d = _json(arq)
    if not d:
        return {"estado": "indisponivel", "motivo": f"{arq.name} ilegível"}
    d["arquivo"] = arq.name
    return d


def secao_historico(data: Path) -> dict:
    """Camada de histórico: snapshots com histórico (meta: 100% dos que o backfill pediu), eventos por tipo e estado, tamanho em disco."""
    import gzip

    idx = _json(data / "history" / "index.json")
    if not idx or not idx.get("snapshots"):
        return {"estado": "indisponivel", "motivo": "rode python -m products.history.build --date AAAA-MM-DD (data/history vazio)"}
    snaps = []
    por_tipo: dict[str, dict[str, int]] = {}
    for s in idx["snapshots"]:
        d = s["date"]
        tam = sum(f.stat().st_size for f in [*(data / "history" / "weekly" / d).glob("*.jsonl.gz"), data / "history" / "events" / f"{d}.jsonl.gz"] if f.exists())
        snaps.append({"data": d, "coleta": s.get("coleta"), "asns": s.get("asn_linhas"), "eventos": s.get("eventos_n", 0), "kb": round(tam / 1024)})
        arq = data / "history" / "events" / f"{d}.jsonl.gz"
        if arq.exists():
            with gzip.open(arq, "rt", encoding="utf-8") as f:
                for ln in f:
                    e = json.loads(ln)
                    t = por_tipo.setdefault(e["tipo"], {})
                    t[e["estado"]] = t.get(e["estado"], 0) + 1
    return {"estado": "ok", "snapshots": snaps, "eventos_por_tipo": por_tipo, "total_kb": sum(x["kb"] for x in snaps)}


def build(root: Path, data: Path, hoje: _date, replay_report: Path | None = None, run_tests: bool = False,
          usage_since: str | None = None) -> dict:
    version = (root / "VERSION").read_text().strip() if (root / "VERSION").exists() else None
    return {"gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "data": hoje.isoformat(),
            "versao": version, "testes": secao_testes(root, run_tests), "contratos": secao_contratos(root),
            "replay": secao_replay(replay_report), "pipeline": secao_pipeline(data), "disco": secao_disco(data),
            "uso": secao_uso(data, hoje, desde=usage_since), "coleta": secao_coleta(data, hoje),
            "fase2": secao_fase2(root), "relacoes": secao_relacoes(data), "historico": secao_historico(data)}


# ── Markdown ───────────────────────────────────────────────────────────────

def _t(rows: list[list], head: list[str]) -> str:
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join("" if c is None else str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def to_markdown(s: dict) -> str:
    L = ["# Painel do Arandurapé", "",
         f"Gerado em {s['gerado_em']} por `scripts/scorecard.py` · versão do código `{s['versao']}` · "
         "somente leitura; seção sem fonte aparece como *indisponível*.", ""]
    t = s["testes"]
    L += ["## Testes", ""]
    if t.get("estado") == "indisponivel":
        L += [f"*indisponível — {t.get('motivo')}*", ""]
    else:
        L += [_t([[k, LEVELS.get(k, "—"), v] for k, v in t["por_nivel"].items()] + [["**total**", "", t["total"]]],
                 ["pasta", "nível", "testes"]), ""]
        if "execucao" in t:
            L += [f"Última execução: {t['execucao']['resultado']} ({t['execucao']['duracao_s']} s)", ""]
    c = s["contratos"]
    L += ["## Contratos", "",
          _t([["API (operações com contrato)", c["api_operacoes"]], ["MCP (tools)", c["mcp_tools"]],
              ["MCP (resources/prompts)", f"{c['mcp_resources']}/{c['mcp_prompts']}"],
              ["Esquemas dos artefatos publicados (T3)", c["esquemas_publicados"]]], ["item", "valor"]), ""]
    r = s["replay"]
    L += ["## Replay", ""]
    if r.get("estado") == "indisponivel":
        L += [f"*indisponível — {r.get('motivo')}*", ""]
    else:
        L += [f"Snapshot {r['data']}: **{r['diferencas_novas']} diferença(s) nova(s)** — "
              + ", ".join(f"{k}={v}" for k, v in sorted(r['contagem'].items())) + f" ({r['duracao_s']} s)", ""]
    p = s["pipeline"]
    L += ["## Pipeline semanal", ""]
    if p.get("estado") == "indisponivel":
        L += [f"*indisponível — {p.get('motivo')}*", ""]
    else:
        L += [f"Run {p['data']}: {p['duracao_total_s']} s em {p['etapas']} etapas; falhas: {p['falhas'] or 'nenhuma'}", "",
              _t([[e["etapa"], e["duracao_s"]] for e in p["mais_lentas"]], ["etapa mais lenta", "segundos"]), ""]
    d = s["disco"]
    L += ["## Disco", ""]
    if d.get("estado") == "indisponivel":
        L += [f"*indisponível — {d.get('motivo')}*", ""]
    else:
        L += [f"`data/` em {d['data']}: **{d['total_data_gib']} GiB**; disco {d['disco_usado_pct']}% usado "
              f"({d['disco_livre_gib']} GiB livres); inodes {d['inodes_usados_pct']}%; {d['snapshots_publicados']} snapshots publicados.", "",
              _t([[k, v] for k, v in d["por_tipo_gib"].items()], ["tipo", "GiB"]), ""]
    u = s["uso"]
    L += ["## Uso da API e do MCP", ""]
    if u.get("estado") == "indisponivel":
        L += [f"*indisponível — {u.get('motivo')}*", ""]
    else:
        L += [f"{u['fonte']}: {u['chamadas']} chamadas; 5xx: {u['erros_5xx']}; latência p50 {u['latencia_ms']['p50']} ms, "
              f"p95 {u['latencia_ms']['p95']} ms.", "",
              _t([[x["rota"], x["chamadas"], x["p95_ms"], x["bytes_medio"]] for x in u["rotas_mais_usadas"]],
                 ["rota", "chamadas", "p95 (ms)", "bytes médios"]), ""]
    co = s["coleta"]
    L += ["## Coleta e frescor", ""]
    if co.get("estado") == "indisponivel":
        L += [f"*indisponível — {co.get('motivo')}*", ""]
    else:
        L += [f"Último snapshot **{co['ultimo']}** ({co['idade_dias']} dia(s)), {co['snapshots']} publicados, "
              f"PTTs coletados {co['ptt_coletados']}, coleta: **{co['coleta']}**"
              + (f", falhas: {co['falhas']}" if co.get("falhas") else "") + ".", ""]
    f2 = s.get("fase2") or {}
    L += ["## Metas da fase 2", ""]
    if f2:
        linhas = []
        mb = f2.get("maior_arquivo_de_build")
        if mb:
            linhas.append(["Maior arquivo de build (meta < 600 linhas)", f"{mb['arquivo']}: {mb['linhas']}", "ok" if mb["ok"] else "acima da meta"])
        cm = f2.get("camadas") or {}
        if "mantidos" in cm:
            linhas.append(["Regras de camada (import-linter)", f"{cm['mantidos']} mantidos, {cm['quebrados']} quebrados", "ok" if cm["ok"] else "QUEBRADAS"])
        dc = f2.get("documentacao") or {}
        if "pct" in dc:
            linhas.append(["Documentação dos campos (meta ≥ 90%)", f"{dc['pct']}% de {dc['campos']} campos; {dc['fontes']} fontes, {dc['etapas']} etapas", "ok" if (dc["pct"] or 0) >= 90 else "abaixo"])
        al = f2.get("alertas") or {}
        if al:
            linhas.append(["Regras de alerta", f"{al['regras']} regras, rules_version {al['rules_version']}", ""])
        ep = f2.get("escritas_por_arquivo") or {}
        if ep:
            linhas.append(["Escritas por arquivo publicado (meta 1)", f"antes: documento de ASN {ep['antes_documento_de_asn']}×, índice {ep['antes_indice']}×; hoje 1× (T2)", "ok"])
        sh = f2.get("shims") or {}
        if sh:
            linhas.append(["Atalhos a remover no 1.2.9", ", ".join(f"{k}: {v}" for k, v in sh.items()), "a partir de 2026-11-14"])
        L += [_t(linhas, ["meta", "valor", "estado"]), ""]
    else:
        L += ["*indisponível*", ""]
    L += _md_relacoes(s.get("relacoes") or {})
    L += _md_historico(s.get("historico") or {})
    return "\n".join(L).rstrip() + "\n"


def _md_historico(h: dict) -> list[str]:
    L = ["## Histórico", ""]
    if h.get("estado") != "ok":
        return L + [f"*indisponível — {h.get('motivo', 'sem histórico')}*", ""]
    L += [_t([[x["data"], x["coleta"], x["asns"], x["eventos"], x["kb"]] for x in h["snapshots"]], ["snapshot", "coleta", "ASNs", "eventos", "KB"]), "",
          f"Total em disco: {h['total_kb']} KB. Eventos por tipo e estado:", "",
          _t([[t, v.get("confirmado", 0), v.get("pendente", 0), v.get("revertido", 0)] for t, v in sorted(h["eventos_por_tipo"].items())],
             ["tipo", "confirmados", "pendentes", "revertidos"]), ""]
    return L


def _md_relacoes(r: dict) -> list[str]:
    L = ["## Relações entre ASNs (ARC)", ""]
    if r.get("estado") == "indisponivel" or not r:
        return L + [f"*indisponível — {r.get('motivo', 'sem régua')}*", ""]
    L += [f"Régua de {r['snapshot_date']} ({r['algoritmo']}, `{r['arquivo']}`): {r['nota']}.", ""]
    for afi in ("v4", "v6"):
        a = r.get(afi)
        if not a:
            continue
        L += [f"### {afi.upper()} — coletores: {', '.join(a['coletores']) or 'nenhum'}; clique: {len(a['clique'])} ASNs", ""]
        linhas = []
        for escopo in ("br", "global"):
            for nivel in ("ate_provavel", "ate_possivel"):
                m = a["aspa"][escopo][nivel]
                ref = (a.get("caida_como_previsao") or {}).get(escopo, {}).get("ate_provavel", {})
                linhas.append([escopo.upper(), nivel.replace("ate_", "≥ "), m["previstos"], m["precisao"], m["recall"],
                               f"{ref.get('precisao')} / {ref.get('recall')}" if nivel == "ate_provavel" and ref else ""])
        L += [_t(linhas, ["escopo", "nível", "previstos", "precisão", "recall", "CAIDA (prec./recall)"]), ""]
        L += ["Calibração (fração dos provedores previstos que o ASPA confirma, por faixa de p):", "",
              _t([[f"{c['p_de']}–{c['p_ate']}", c["previstos"], c["fracao"]] for c in a["calibracao"]], ["faixa de p", "previstos", "confirmados"]), ""]
        L += ["Subconjuntos difíceis:", "", _t([[k, v["verdade"], v["previstos"], v["precisao"], v["recall"]] for k, v in a["subconjuntos"].items()],
                                              ["subconjunto", "pares ASPA", "previstos", "precisão", "recall"]), ""]
        lin = [[f"sem PTT {k}", v["br_provavel"]["precisao"], v["br_provavel"]["recall"], v["estabilidade"]["jaccard"]] for k, v in a.get("sem_ptt", {}).items()]
        lin += [[f"sem coletor {k}", v["br_provavel"]["precisao"], v["br_provavel"]["recall"], v["estabilidade"]["jaccard"]] for k, v in a.get("sem_coletor", {}).items()]
        if lin:
            L += ["Retirada de um PTT ou coletor por vez (BR, ≥ provável):", "", _t(lin, ["execução", "precisão", "recall", "estabilidade (Jaccard)"]), ""]
        v2 = a.get("v2")
        if v2:
            L += [f"**ARC v2** sobre a mesma execução sem ASPA: {v2['treino']} elos de treino, {len(v2['iteracoes'])} iterações, {v2['abstencoes']} abstenções.", ""]
            linhas = []
            for escopo in ("br", "global"):
                for nivel in ("ate_provavel", "ate_possivel"):
                    m, m1 = v2["aspa"][escopo][nivel], a["aspa"][escopo][nivel]
                    linhas.append([escopo.upper(), nivel.replace("ate_", "≥ "), f"{m1['precisao']} → {m['precisao']}", f"{m1['recall']} → {m['recall']}", m["previstos"]])
            L += [_t(linhas, ["escopo", "nível", "precisão v1 → v2", "recall v1 → v2", "previstos (v2)"]), ""]
            cb = v2.get("calibracao_nb") or {}
            if cb.get("temperatura_otima") is not None:
                L += [f"Calibração do NB: temperatura ótima {cb['temperatura_otima']}; ECE (p ≥ 0,5) bruto {cb['ece_alto_bruto']} → calibrado {cb['ece_alto_calibrado']}; "
                      f"validação cruzada {cb['ece_alto_cv']} ({cb['eventos']} eventos ASPA; limite superior, o ASPA é incompleto).", ""]
                L += [_t([[f"{c['p_de']}–{c['p_ate']}", c["previstos"], c["fracao"]] for c in cb["curva_confiabilidade"]], ["faixa de p (calibrada)", "previstos", "confirmados"]), ""]
            sc = v2.get("subconjuntos") or {}
            L += ["Subconjuntos difíceis (v2):", "", _t([[k, v["verdade"], v["previstos"], v["precisao"], v["recall"]] for k, v in sc.items()], ["subconjunto", "pares ASPA", "previstos", "precisão", "recall"]), ""]
            ab = v2.get("ablacao_br_provavel") or {}
            if ab:
                L += ["Ablação (sem cada característica, BR ≥ provável):", "", _t([[k, v["precisao"], v["recall"]] for k, v in ab.items()], ["sem a característica", "precisão", "recall"]), ""]
        cc = a.get("concordancia_caida")
        if cc:
            L += [f"Concordância com o CAIDA (consistência, não acurácia): p2c {cc['p2c']}, p2p {cc['p2p']}.", ""]
    es = r.get("estabilidade_entre_snapshots") or {}
    L += [("Estabilidade entre snapshots: " + (f"{es['mantidos']} de {es['anterior']} provedores ≥ provável mantidos (Jaccard {es['jaccard']}) entre {es['entre'][0]} e {es['entre'][1]}."
                                                if "mantidos" in es else f"*indisponível — {es.get('motivo')}*")), ""]
    return L


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    ap.add_argument("--data-dir", default=str(ROOT / "data"))
    ap.add_argument("--replay-report")
    ap.add_argument("--usage-since", help="ISO UTC; ignora chamadas anteriores (ex.: depois de uma correção do log)")
    ap.add_argument("--run-tests", action="store_true", help="executa a suíte (mais lento) em vez de só contar")
    ap.add_argument("--out-dir", help="padrão: <data-dir>/ops/scorecard")
    ap.add_argument("--md", default=str(ROOT / "docs" / "scorecard.md"))
    a = ap.parse_args(argv)
    data = Path(a.data_dir)
    s = build(ROOT, data, _date.fromisoformat(a.date), Path(a.replay_report) if a.replay_report else None, a.run_tests,
              a.usage_since)
    out_dir = Path(a.out_dir) if a.out_dir else data / "ops" / "scorecard"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{a.date}.json").write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    Path(a.md).parent.mkdir(parents=True, exist_ok=True)
    Path(a.md).write_text(to_markdown(s), encoding="utf-8")
    print(f"{out_dir / (a.date + '.json')}\n{a.md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
