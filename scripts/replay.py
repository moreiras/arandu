#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Replay de snapshot: portão de paridade para mudanças em sources/, products/ e publish/.

Reconstrói o `published/{data}/` a partir do `raw/` e do `normalized/` em um diretório
temporário (nunca escreve em `data/`) e compara arquivo a arquivo com o publicado.

    python3 scripts/replay.py --date 2026-09-20 [--data-dir data] [--stages bgp_ixp,metricas_ixp_asn,snapshot_completo,saude_asn]
                              [--out relatorio.json] [--keep] [--work-dir DIR]

Estágios reexecutados (na ordem do pipeline), com o nome da etapa do catálogo: `bgp_ixp` (parser BGP, raw → normalized),
`metricas_ixp_asn` (métricas por IXP e documentos de ASN), `snapshot_completo` (publicação: índices, mapas, mercado, manifesto),
`analise_bgp` (`routing_analysis`, `bgp_stability` e `bgp_stability_deep`, a partir do `normalized/`; só os que
existem no publicado), `saude_asn` (pré-cálculo de alertas e RPKI por ASN). Os nomes antigos (`p1`, `p2p3`, `p6`, `bgp`, `p6b`)
seguem aceitos. Não são reexecutadas por dependerem de rede/serviços externos: coletas, geocodificação e RPKI (Routinator) — o RPKI é copiado do publicado
e fica fora da comparação (aparece como `copiado` no relatório).

Classificação de cada arquivo:
  igual       bytes idênticos ou JSON idêntico após remover campos voláteis;
  ordem       mesmo conteúdo, só muda a ordem de listas (candidato a não determinismo);
  explicada   difere, mas casa com uma entrada de `scripts/replay_expected.json`;
  nova        difere sem explicação — o replay sai com código 1;
  so_original / so_replay   arquivo existe só de um lado (mesma regra de explicação);
  copiado     artefato não reexecutado (informativo).
"""
from __future__ import annotations

import argparse
import fnmatch
import gzip
import json
import os
import re
import shutil
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Campos que mudam a cada execução sem mudar o conteúdo publicado.
VOLATILE = {"generated_at", "published_at", "pipeline_version", "checksums", "source_file", "receita_socios_generated_at"}

# Artefatos que o replay não reconstrói (rede ou serviço externo): o RPKI vem do Routinator (avulso). A análise de
# roteamento e as de estabilidade BGP SÃO reexecutadas (estágio `bgp`): leem só `normalized/` e o publicado.
# `as_relationships.json.gz` também: o ARC lê os caminhos dos coletores (`aspaths`, fora do armazém e do work dir) e demora
# ~15 min; o publicado entra como entrada e o fragmento `asn.relacoes` dos documentos de ASN é recomposto por `restaurar_relacoes`
# (copia `build/{data}/fragments/asn/relacoes.jsonl.gz` do `data/` ou, sem ele, o refaz a partir de `asns/*.json` do publicado).
NOT_REPLAYED = ("rpki/*", "as_relationships.json.gz")

CACHE_DIRS = ("geo_cache", "holdings_cache", "sici_cache", "sici_movel_cache")
STAGES_ALL = ("bgp_ixp", "metricas_ixp_asn", "snapshot_completo", "analise_bgp", "saude_asn")
ALIASES_STAGES = {"p1": "bgp_ixp", "p2p3": "metricas_ixp_asn", "p6": "snapshot_completo", "bgp": "analise_bgp", "p6b": "saude_asn"}
EXPECTED_FILE = Path(__file__).resolve().parent / "replay_expected.json"
MAX_DIFFS_PER_FILE = 5


# ── comparação ─────────────────────────────────────────────────────────────

def strip_volatile(x):
    if isinstance(x, dict):
        return {k: strip_volatile(v) for k, v in x.items() if k not in VOLATILE}
    if isinstance(x, list):
        return [strip_volatile(v) for v in x]
    return x


def _canon(x) -> str:
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _sort_lists(x):
    """Forma canônica independente da ordem das listas (para detectar só-ordem)."""
    if isinstance(x, dict):
        return {k: _sort_lists(v) for k, v in x.items()}
    if isinstance(x, list):
        return sorted((_sort_lists(v) for v in x), key=_canon)
    return x


def diff_paths(a, b, path: str = "", out: list | None = None, limit: int = MAX_DIFFS_PER_FILE) -> list[str]:
    """Primeiros caminhos (JSON pointer) em que `a` e `b` divergem."""
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if type(a) is not type(b):
        out.append(path or "/")
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{path}/{k}")
            else:
                diff_paths(a[k], b[k], f"{path}/{k}", out, limit)
            if len(out) >= limit:
                break
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f"{path} (len {len(a)} ≠ {len(b)})")
        for i, (x, y) in enumerate(zip(a, b)):
            diff_paths(x, y, f"{path}/{i}", out, limit)
            if len(out) >= limit:
                break
    elif a != b:
        out.append(path or "/")
    return out


def _load(path: Path):
    if path.name.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(path.read_text(encoding="utf-8"))


def _is_json(rel: str) -> bool:
    return rel.endswith((".json", ".json.gz", ".geojson", ".geojson.gz"))


def load_expected(path: Path = EXPECTED_FILE) -> list[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("diferencas", [])
    except (OSError, ValueError):
        return []


def explanation(rel: str, kind: str, expected: list[dict], a=None, b=None) -> str | None:
    """Motivo da primeira entrada que casa. `caminhos_regex` (opcional) exige que TODOS os
    caminhos divergentes casem com a expressão — evita que uma entrada por arquivo esconda
    diferenças novas no mesmo arquivo."""
    for e in expected:
        if not (fnmatch.fnmatch(rel, e.get("arquivo", "")) and e.get("tipo", kind) == kind):
            continue
        rx = e.get("caminhos_regex")
        if rx and a is not None:
            paths = diff_paths(a, b, limit=100000)
            if not paths or not all(re.search(rx, p) for p in paths):
                continue
        return e.get("motivo", "(sem motivo)")
    return None


def compare_file(rel: str, orig: Path | None, rep: Path | None, expected: list[dict]) -> dict:
    """Classifica um arquivo do publicado contra o reconstruído."""
    if orig is None or rep is None:
        kind = "so_replay" if orig is None else "so_original"
        why = explanation(rel, kind, expected)
        return {"arquivo": rel, "classe": "explicada" if why else "nova", "tipo": kind, "motivo": why}
    if orig.read_bytes() == rep.read_bytes():
        return {"arquivo": rel, "classe": "igual"}
    if not _is_json(rel):
        why = explanation(rel, "conteudo", expected)
        return {"arquivo": rel, "classe": "explicada" if why else "nova", "tipo": "conteudo", "motivo": why}
    a, b = strip_volatile(_load(orig)), strip_volatile(_load(rep))
    if a == b:
        return {"arquivo": rel, "classe": "igual", "detalhe": "só campos voláteis/formatação"}
    if _sort_lists(a) == _sort_lists(b):
        why = explanation(rel, "ordem", expected, a, b)
        return {"arquivo": rel, "classe": "explicada" if why else "ordem", "tipo": "ordem", "motivo": why,
                "caminhos": diff_paths(a, b)}
    why = explanation(rel, "conteudo", expected, a, b)
    return {"arquivo": rel, "classe": "explicada" if why else "nova", "tipo": "conteudo", "motivo": why,
            "caminhos": diff_paths(a, b)}


def _files(root: Path) -> dict[str, Path]:
    return {str(p.relative_to(root)): p for p in sorted(root.rglob("*")) if p.is_file()}


def compare_trees(orig_root: Path, rep_root: Path, expected: list[dict] | None = None) -> dict:
    expected = load_expected() if expected is None else expected
    fo, fr = _files(orig_root), _files(rep_root)
    results = []
    for rel in sorted(set(fo) | set(fr)):
        if any(fnmatch.fnmatch(rel, pat) for pat in NOT_REPLAYED):
            results.append({"arquivo": rel, "classe": "copiado"})
            continue
        results.append(compare_file(rel, fo.get(rel), fr.get(rel), expected))
    counts = Counter(r["classe"] for r in results)
    return {"contagem": dict(counts), "arquivos": results}


# ── reconstrução ───────────────────────────────────────────────────────────

def prepare_work_dir(src: Path, work: Path, date: str) -> None:
    """Monta `work/` com entradas do `src` sem tocar nele: raw por link (só leitura pelos
    estágios), normalized da data e caches por cópia (os estágios gravam em normalized/)."""
    (work / "raw").mkdir(parents=True, exist_ok=True)
    raw_d = src / "raw" / date
    if raw_d.exists():
        os.symlink(raw_d.resolve(), work / "raw" / date)
    norm_src = src / "normalized"
    (work / "normalized").mkdir(parents=True, exist_ok=True)
    if (norm_src / date).exists():
        shutil.copytree(norm_src / date, work / "normalized" / date)
    for name in CACHE_DIRS:
        if (norm_src / name).exists():
            shutil.copytree(norm_src / name, work / "normalized" / name)
    if (src / "ipv4").exists():      # estado e eventos do delegated: derivados fora de normalized/, que o produto de IPv4 lê
        shutil.copytree(src / "ipv4", work / "ipv4")
    # snapshot anterior: o manifesto compara com ele (sanidade de coleta): só manifesto e VRPs
    from publish.coleta_checks import previous_snapshot

    prev = previous_snapshot(src, date)
    for rel in (("manifest.json", "rpki/vrp_list.json.gz") if prev else ()):
        f = src / "published" / prev / rel
        if f.exists():
            dst = work / "published" / prev / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
    if prev:                  # o check asn_names (1.2.2.3) compara com os nomes da coleta anterior
        nomes = src / "normalized" / prev / "summary" / "asn_names.json.gz"
        if nomes.exists():
            dst = work / "normalized" / prev / "summary" / "asn_names.json.gz"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(nomes, dst)
    anteriores = sorted((d.name for d in norm_src.iterdir() if d.is_dir() and d.name < date and (d / "summary" / "origin-prefixes-v4.json.gz").exists()), reverse=True)[:8]
    for d in anteriores:                  # a duração sem anúncio do IPv4 olha as tabelas de origem dos snapshots anteriores
        dst = work / "normalized" / d / "summary" / "origin-prefixes-v4.json.gz"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(norm_src / d / "summary" / "origin-prefixes-v4.json.gz", dst)
    pub_src = src / "published" / date
    for pat in NOT_REPLAYED:
        for p in pub_src.glob(pat):
            dst = work / "published" / date / p.relative_to(pub_src)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if p.is_file():
                shutil.copy2(p, dst)


def _numeros_de_asn(pub: Path) -> list[int]:
    """ASNs com documento em `published/{data}/asns/` (diretório ou `asns.zip`), sem o `index.json`."""
    nomes: list[str] = []
    zpath = pub / "asns.zip"
    if (pub / "asns").is_dir():
        nomes = [p.name for p in (pub / "asns").iterdir()]
    elif zpath.is_file():
        import zipfile

        with zipfile.ZipFile(zpath) as z:
            nomes = [n for n in z.namelist() if "/" not in n]
    return sorted(int(n[:-5]) for n in nomes if n.endswith(".json") and n[:-5].isdigit())


def restaurar_relacoes(src: Path, work: Path, date: str) -> str | None:
    """Põe em `work/build/{data}/fragments/asn/relacoes.jsonl.gz` o fragmento `relacoes` (ARC) dos documentos de ASN.

    O estágio `as_relationships` não é reexecutado, mas `documentos de ASN`, alertas `single_homed` e o trânsito do território leem o
    fragmento. Origem, em ordem: (1) o fragmento do `data/` (`build/{data}/fragments/asn/`), copiado; (2) sem ele, refeito a partir do campo
    `relacoes` dos `asns/{asn}.json` publicados (diretório ou `asns.zip`), no formato do estágio (`{"asn": N, "d": {"relacoes": ...}}`, ASN
    crescente). Só lê `src`. Gravar o fragmento `base` apaga os derivados (`core.compose.limpar_derivados`): chame antes de cada estágio.
    Devolve "copiado", "recomposto", "presente" (já no work dir) ou None (publicado sem `relacoes`)."""
    from core import compose, layout

    destino = compose.caminho(work, date, "relacoes")
    if destino.exists():
        return "presente"
    origem = compose.caminho(src, date, "relacoes")
    if origem.is_file():
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)
        return "copiado"
    pub = src / "published" / date
    docs = 0
    with compose.gravar_fragmento(work, date, "relacoes") as w:
        for asn in _numeros_de_asn(pub):
            raw = layout.ler_bytes(pub, f"asns/{asn}.json")
            rel = json.loads(raw).get("relacoes") if raw else None
            if rel is not None:
                w.escrever(asn, {"relacoes": rel})
                docs += 1
    if not docs:
        destino.unlink(missing_ok=True)
        return None
    return "recomposto"


def _restrict_config(codes: set[str]):
    """Restringe a configuração de PTTs aos IXPs do snapshot original (`ixps_configured` do
    manifesto). O replay usa o `config/` atual; sem isso, um PTT adicionado depois da data
    (ex.: `ap`, em 2026-09-28) apareceria só no replay e contaminaria os índices e os alertas."""
    from contextlib import ExitStack
    from unittest import mock

    from products.bgp_routes import build as bgp_parser
    from products.ixp_metrics import build as metrics
    from api.store import Store
    from publish import snapshot_builder

    def keep(items):
        return [i for i in items if i.get("code") in codes]

    stack = ExitStack()
    for mod in (bgp_parser, metrics, snapshot_builder):
        orig = mod.load_ixps
        stack.enter_context(mock.patch.object(mod, "load_ixps", lambda o=orig: keep(o())))
    orig_pdb = snapshot_builder.load_peeringdb_ixps_config

    def pdb():
        cfg = dict(orig_pdb())
        cfg["ixbr"] = keep(cfg.get("ixbr", []))
        return cfg

    stack.enter_context(mock.patch.object(snapshot_builder, "load_peeringdb_ixps_config", pdb))
    from products import passos              # os passos do build leem a configuração por estes dois ganchos

    orig_ix = passos._ixps_atual
    stack.enter_context(mock.patch.object(passos, "_ixps_atual", lambda o=orig_ix: keep(o())))
    orig_cfg = passos._config_atual

    def cfg():
        c = dict(orig_cfg())
        c["ixbr"] = keep(c.get("ixbr", []))
        return c

    stack.enter_context(mock.patch.object(passos, "_config_atual", cfg))
    orig_pix = Store._load_pix_config
    stack.enter_context(mock.patch.object(
        Store, "_load_pix_config",
        lambda self: {k: v for k, v in orig_pix(self).items() if k in codes}))
    return stack


def run_stages(work: Path, date: str, stages: tuple[str, ...], log=None, ixp_codes: set[str] | None = None,
               original: Path | None = None, data_dir: Path | None = None) -> dict:
    """Executa os estágios sobre `work` (cada um é o mesmo código do pipeline). Aceita os nomes antigos (`ALIASES_STAGES`)."""
    from contextlib import nullcontext

    from core.common import configure_logging

    log = log or configure_logging()
    with (_restrict_config(ixp_codes) if ixp_codes else nullcontext()):
        return _run_stages(work, date, tuple(ALIASES_STAGES.get(s, s) for s in stages), log, original, data_dir)


def _run_stages(work: Path, date: str, stages: tuple[str, ...], log, original: Path | None = None,
                data_dir: Path | None = None) -> dict:
    timings: dict[str, float] = {}
    if data_dir is None and original is not None:
        data_dir = original.parent.parent

    def relacoes() -> None:      # o `base` regravado por metricas_ixp_asn apaga o fragmento: restaura antes de cada estágio que o lê
        if data_dir is not None:
            restaurar_relacoes(data_dir, work, date)

    if "bgp_ixp" in stages:
        t = time.time()
        from products.bgp_routes import build as bgp_parser

        for ixp in bgp_parser.load_ixps():
            if (work / "raw" / date / ixp["code"]).exists():
                bgp_parser.parse_ixp(ixp["code"], date, work, log)
        timings["bgp_ixp"] = round(time.time() - t, 1)
    if "metricas_ixp_asn" in stages:
        t = time.time()
        from products.ixp_metrics import build as metrics

        metrics.run(date, work, log=log)
        timings["metricas_ixp_asn"] = round(time.time() - t, 1)
    if "snapshot_completo" in stages:
        relacoes()
        t = time.time()
        from publish import snapshot_builder

        snapshot_builder.run(date, work, log)
        timings["snapshot_completo"] = round(time.time() - t, 1)
    if "analise_bgp" in stages:
        relacoes()
        from products.bgp_stability import build as bgp_stability
        from products.bgp_stability import deep as bgp_stability_deep
        from products.routing_analysis import build as routing_analysis

        t = time.time()
        for artefato, modulo in (("routing_analysis.json", routing_analysis), ("bgp_stability.json", bgp_stability),
                                 ("bgp_stability_deep.json", bgp_stability_deep)):
            if original is not None and not (original / artefato).exists():
                continue                  # o snapshot publicado não tem este artefato: não há o que comparar
            modulo.run(date, work, log)
        timings["analise_bgp"] = round(time.time() - t, 1)
    if "saude_asn" in stages:
        relacoes()
        from publish import snapshot_builder

        t = time.time()
        snapshot_builder.run_asn_health_only(work, date, log)
        timings["saude_asn"] = round(time.time() - t, 1)
        if original is None or (original / "prontidao").exists():           # o índice vem depois de saude_asn (precisa da validação RPKI) e só se o publicado o tem
            from products.prontidao import build as prontidao
            from publish import coleta_checks

            prontidao.publicar_prontidao(work, date, log)
            if original is None or (original / "manrs").exists():           # agregado do MANRS depois da prontidão
                from products.manrs import build as manrs

                manrs.publicar_manrs(work, date, log)
            if original is None or (original / "territorio" / "regiao.json.gz").exists():      # ASNs por município
                from products.regiao import build as regiao

                regiao.publicar_regiao(work, date, log)
            if original is None or (original / "territorio" / "rede_territorio.json.gz").exists():      # IPv6, ROV e trânsito no território (depois da região)
                from products.rede_territorio import build as rede_territorio

                rede_territorio.publicar_rede_territorio(work, date, log)
            coleta_checks.refresh_manifest(work, date, log, checksums=True)
    return timings


def replay(date: str, data_dir: Path, stages: tuple[str, ...] = STAGES_ALL, work_dir: Path | None = None,
           keep: bool = False, expected: list[dict] | None = None, restrict_ixps: bool = True) -> dict:
    data_dir = Path(data_dir)
    orig = data_dir / "published" / date
    if not orig.exists():
        raise SystemExit(f"ERRO: {orig} não existe")
    if not (data_dir / "normalized" / date).exists():
        raise SystemExit(f"ERRO: {data_dir / 'normalized' / date} não existe")
    own = work_dir is None
    work = Path(tempfile.mkdtemp(prefix=f"replay-{date}-")) if own else Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    try:
        t0 = time.time()
        prepare_work_dir(data_dir, work, date)
        codes = None
        if restrict_ixps:
            try:
                codes = set(json.loads((orig / "manifest.json").read_text(encoding="utf-8")).get("ixps_configured") or [])
            except (OSError, ValueError):
                codes = None
        timings = run_stages(work, date, stages, ixp_codes=codes or None, original=orig, data_dir=data_dir)
        report = compare_trees(orig, work / "published" / date, expected)
        report.update({"date": date, "stages": list(stages), "tempos_s": timings,
                       "duracao_s": round(time.time() - t0, 1), "work_dir": str(work) if keep or not own else None})
        return report
    finally:
        if own and not keep:
            shutil.rmtree(work, ignore_errors=True)


def summary_text(report: dict) -> str:
    c = report["contagem"]
    lines = [f"replay {report['date']} — etapas {','.join(report['stages'])} — {report['duracao_s']} s",
             "  " + "  ".join(f"{k}={v}" for k, v in sorted(c.items()))]
    for r in report["arquivos"]:
        if r["classe"] in ("nova", "ordem"):
            lines.append(f"  {r['classe'].upper():6s} {r['arquivo']}  {r.get('tipo', '')} {r.get('caminhos', '')}")
    n_new = c.get("nova", 0) + c.get("ordem", 0)
    lines.append(f"diferenças novas: {n_new}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", required=True, help="AAAA-MM-DD do snapshot publicado")
    ap.add_argument("--data-dir", default=str(ROOT / "data"))
    ap.add_argument("--stages", default=",".join(STAGES_ALL), help=f"subconjunto de {','.join(STAGES_ALL)}")
    ap.add_argument("--out", help="grava o relatório completo em JSON")
    ap.add_argument("--work-dir", help="diretório de trabalho (padrão: temporário, apagado ao fim)")
    ap.add_argument("--keep", action="store_true", help="mantém o diretório reconstruído")
    ap.add_argument("--no-restrict-ixps", action="store_true",
                    help="usa todos os PTTs do config/ atual (padrão: só os `ixps_configured` do manifesto)")
    args = ap.parse_args(argv)
    stages = tuple(ALIASES_STAGES.get(s, s) for s in args.stages.split(",") if s)
    bad = [s for s in stages if s not in STAGES_ALL]
    if bad:
        ap.error(f"etapas desconhecidas: {bad}")
    report = replay(args.date, Path(args.data_dir), stages,
                    Path(args.work_dir) if args.work_dir else None, args.keep,
                    restrict_ixps=not args.no_restrict_ixps)
    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(summary_text(report))
    c = report["contagem"]
    return 1 if c.get("nova", 0) or c.get("ordem", 0) else 0


if __name__ == "__main__":
    sys.exit(main())
