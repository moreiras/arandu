# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`arandu run --compare`: reexecuta as etapas reprodutíveis num diretório de teste e compara com o publicado.

Critério idêntico ao do `scripts/replay.py`: arquivos iguais, diferenças explicadas em
`scripts/replay_expected.json` e **0 diferenças novas**. A diferença é de origem: aqui as etapas e a ordem vêm
do catálogo (etapas com `replay: true`), não de uma lista própria do replay.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional

from arandu.executor import planejar
from arandu.runner import InProcessRunner
from core.catalog.loader import Catalog

ROOT = Path(__file__).resolve().parents[1]


def carrega_replay():
    spec = importlib.util.spec_from_file_location("arandu_replay", ROOT / "scripts" / "replay.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def etapas_do_compare(cat: Catalog, publicado: Path) -> list:
    return [s for s in planejar(cat) if s.replay and (not s.replay_se_publicado or (publicado / s.replay_se_publicado).exists())]


def restaurar_relacoes(data_dir: Path, work: Path, date: str) -> None:
    """Põe no work dir o fragmento `relacoes` (ARC) do publicado, se faltar.

    O ARC não é reexecutado no compare (lê os caminhos dos coletores, fora do work dir, e leva ~15 min), mas o documento de ASN
    o inclui. Gravar o fragmento `base` apaga os derivados (`core.compose.limpar_derivados`), então a cópia é refeita antes de cada etapa."""
    frag = Path(data_dir) / "build" / date / "fragments" / "asn" / "relacoes.jsonl.gz"
    destino = work / "build" / date / "fragments" / "asn" / frag.name
    if frag.is_file() and not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(frag, destino)


def comparar(cat: Catalog, date: str, data_dir: Path, *, keep: bool = False, work_dir: Optional[Path] = None,
             runner_factory=InProcessRunner, replay_mod=None, log=print) -> dict:
    rp = replay_mod or carrega_replay()
    orig = Path(data_dir) / "published" / date
    if not orig.exists():
        raise SystemExit(f"ERRO: {orig} não existe")
    if not (Path(data_dir) / "normalized" / date).exists():
        raise SystemExit(f"ERRO: {Path(data_dir) / 'normalized' / date} não existe")
    own = work_dir is None
    work = Path(tempfile.mkdtemp(prefix=f"arandu-compare-{date}-")) if own else Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    try:
        t0 = time.time()
        rp.prepare_work_dir(Path(data_dir), work, date)
        try:
            codes = set(json.loads((orig / "manifest.json").read_text(encoding="utf-8")).get("ixps_configured") or [])
        except (OSError, ValueError):
            codes = set()
        etapas = etapas_do_compare(cat, orig)
        runner = runner_factory({"DATA_DIR": str(work)})
        resultados, tempos = [], {}
        from contextlib import nullcontext

        with (rp._restrict_config(codes) if codes else nullcontext()):
            for s in etapas:
                restaurar_relacoes(Path(data_dir), work, date)
                t = time.time()
                log(f"[compare:{s.id}] {s.nome}...")
                r = runner.run(s, date)
                tempos[s.id] = round(time.time() - t, 1)
                resultados.append({"etapa": s.id, "exit": r.rc, "motivo": r.motivo})
                if r.rc != 0:
                    break
        falhou = [x for x in resultados if x["exit"] != 0]
        rep = rp.compare_trees(orig, work / "published" / date, rp.load_expected())
        rep.update({"date": date, "etapas": resultados, "tempos_s": tempos, "duracao_s": round(time.time() - t0, 1),
                    "etapa_falhou": falhou[0]["etapa"] if falhou else None})
        return rep
    finally:
        if own and not keep:
            shutil.rmtree(work, ignore_errors=True)


def diferencas_novas(rep: dict) -> int:
    """Mesmo critério do scripts/replay.py: 'nova' ou 'ordem' são regressão; 'explicada' e 'copiado' não."""
    c = rep.get("contagem", {})
    return c.get("nova", 0) + c.get("ordem", 0)


def resumo(rep: dict) -> str:
    c = rep.get("contagem", {})
    linhas = [f"compare {rep.get('date')} — {len(rep.get('etapas', []))} etapa(s) — {rep.get('duracao_s')} s",
              "  " + "  ".join(f"{k}={v}" for k, v in sorted(c.items()))]
    if rep.get("etapa_falhou"):
        linhas.append(f"  ETAPA FALHOU: {rep['etapa_falhou']}")
    for r in rep.get("arquivos", []):
        if r["classe"] in ("nova", "ordem"):
            linhas.append(f"  {r['classe'].upper():6s} {r['arquivo']}  {r.get('tipo', '')} {r.get('caminhos', '')}")
    linhas.append(f"diferenças novas: {diferencas_novas(rep)}")
    return "\n".join(linhas)
