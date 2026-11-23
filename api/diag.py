# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Diagnóstico de memória da API: o que ocupa a RAM do processo, por cache e por data.

Somente leitura e sem efeito no comportamento. Objetivo: medir antes de decidir a arquitetura de cache
(100% em memória, mais de um `uvicorn`). Dois níveis:

  leve (padrão)  tamanho de cada cache em nº de entradas e as datas residentes; custa microssegundos;
  profundo       estimativa do tamanho em bytes por AMOSTRAGEM (as primeiras N entradas de cada cache,
                 extrapoladas); segura o GIL por alguns segundos — use fora do horário de pico.

O tamanho estimado é de objetos Python (o que importa para a RAM); a extrapolação supõe entradas de
tamanho parecido, por isso cada medida traz `estimado: true` quando houve amostragem.
"""
from __future__ import annotations

import gc
import os
import re
import sys
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CGROUP_DIRS = (Path("/sys/fs/cgroup"), Path("/sys/fs/cgroup/memory"))


# ── processo e cgroup ──────────────────────────────────────────────────────

def _int_file(path: Path) -> int | None:
    try:
        raw = path.read_text().strip()
        return int(raw) if raw.isdigit() else None        # "max" (sem limite) vira None
    except OSError:
        return None


def process_info(deep: bool = False) -> dict:
    out: dict[str, Any] = {"pid": os.getpid(), "threads": threading.active_count(),
                           "malloc_arena_max": os.environ.get("MALLOC_ARENA_MAX"),
                           "gc_contagem": list(gc.get_count())}
    if deep:   # gc.get_objects() cria uma lista com TODOS os objetos rastreados: só no modo profundo
        out["objetos_rastreados_gc"] = len(gc.get_objects())
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith(("VmRSS:", "VmHWM:", "VmSize:")):
                k, v = line.split(":", 1)
                out[{"VmRSS": "rss_bytes", "VmHWM": "rss_pico_bytes", "VmSize": "virtual_bytes"}[k]] = int(v.split()[0]) * 1024
    except OSError:
        import resource

        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        out["rss_pico_bytes"] = peak if sys.platform == "darwin" else peak * 1024
    cg: dict[str, int | None] = {}
    for d in _CGROUP_DIRS:
        for key, names in (("atual", ("memory.current", "memory.usage_in_bytes")),
                           ("pico", ("memory.peak", "memory.max_usage_in_bytes")),
                           ("limite", ("memory.max", "memory.limit_in_bytes"))):
            for n in names:
                v = _int_file(d / n)
                if v is not None and key not in cg:
                    cg[key] = v
    if cg:
        out["cgroup_bytes"] = cg
    return out


# ── tamanho de objetos ─────────────────────────────────────────────────────

def deep_size(obj: Any, budget: int = 400_000) -> tuple[int, bool]:
    """Bytes alcançáveis a partir de `obj` (sem contar duas vezes o mesmo objeto) e se a conta foi
    completa (`False` = parou no orçamento de nós)."""
    seen: set[int] = set()
    stack = [obj]
    total = 0
    while stack:
        o = stack.pop()
        i = id(o)
        if i in seen:
            continue
        seen.add(i)
        total += sys.getsizeof(o, 0)
        if len(seen) >= budget:
            return total, False
        if isinstance(o, dict):
            stack.extend(o.keys())
            stack.extend(o.values())
        elif isinstance(o, Mapping):
            try:
                for k, v in o.items():
                    stack.append(k)
                    stack.append(v)
            except Exception:  # noqa: BLE001
                pass
        elif isinstance(o, (list, tuple, set, frozenset)):
            stack.extend(o)
    return total, True


def estimate_size(obj: Any, sample: int = 64, budget: int = 400_000) -> tuple[int, bool]:
    """Estima o tamanho profundo de uma coleção grande medindo `sample` entradas e extrapolando.
    Devolve (bytes, estimado)."""
    try:
        n = len(obj)
    except TypeError:
        return deep_size(obj, budget)[0], False
    if n <= sample or not isinstance(obj, (dict, list, tuple, set, frozenset, Mapping)):
        size, complete = deep_size(obj, budget)
        return size, not complete
    if isinstance(obj, (set, frozenset)):
        items = list(_take(iter(obj), sample))
    elif isinstance(obj, (list, tuple)):
        items = list(obj[:sample])
    else:
        items = []
        for k, v in _take(iter(obj.items()), sample):
            items.extend((k, v))
    per, _ = deep_size(items, budget)
    entries = max(1, len(items) // (2 if isinstance(obj, Mapping) else 1))
    return int(sys.getsizeof(obj, 0) + per / entries * n), True


def _take(it, n):
    for _ in range(n):
        try:
            yield next(it)
        except StopIteration:
            return


def _date_of(key: Any) -> str | None:
    if isinstance(key, str) and _DATE.match(key):
        return key
    if isinstance(key, tuple) and key and isinstance(key[0], str) and _DATE.match(key[0]):
        return key[0]
    return None


# ── Store e byte-cache ─────────────────────────────────────────────────────

def _is_container(v: Any) -> bool:
    return isinstance(v, (dict, list, set, frozenset, Mapping)) and not isinstance(v, (str, bytes))


def store_report(store: Any, deep: bool = False, sample: int = 64) -> dict:
    attrs = []
    dates: set[str] = set()
    total = 0
    for name, value in sorted(vars(store).items()):
        if not name.startswith("_") or not _is_container(value):
            continue
        try:
            n = len(value)
        except TypeError:
            continue
        entry: dict[str, Any] = {"nome": name, "tipo": type(value).__name__, "entradas": n}
        keys = []
        if isinstance(value, Mapping):
            try:
                keys = list(value.keys())
            except Exception:  # noqa: BLE001
                keys = []
        by_date = sorted({d for d in (_date_of(k) for k in keys) if d})
        if by_date:
            entry["datas"] = by_date
            dates.update(by_date)
        if deep and n:
            size, est = estimate_size(value, sample)
            entry["bytes_estimados"] = size
            entry["estimado"] = est
            total += size
            # dict por data: detalha cada data (a troca de snapshot mantém duas ao mesmo tempo)
            if by_date and all(_date_of(k) == k for k in keys):
                entry["por_data"] = {d: {"entradas": _safe_len(value[d]),
                                         "bytes_estimados": estimate_size(value[d], sample)[0]} for d in by_date}
        attrs.append(entry)
    attrs.sort(key=lambda e: (-(e.get("bytes_estimados") or 0), -e["entradas"]))
    out = {"datas_residentes": sorted(dates), "caches": attrs}
    if deep:
        out["total_bytes_estimados"] = total
    return out


def _safe_len(x: Any) -> int | None:
    try:
        return len(x)
    except TypeError:
        return None


_MODULE_PREFIXES = ("api", "mcp_server", "analysis", "publish", "collector", "enrich", "scripts")


def module_caches_report(deep: bool = False, sample: int = 64, limit: int = 25) -> list[dict]:
    """Coleções e `lru_cache` em escopo de MÓDULO (fora do `Store`): caches de rota, memoizações, tabelas
    carregadas na importação. É onde costuma estar a memória que o relatório do Store não explica."""
    import functools

    rows: list[dict] = []
    for mod_name, mod in list(sys.modules.items()):
        if not mod or not mod_name.split(".")[0] in _MODULE_PREFIXES:
            continue
        for attr, value in list(vars(mod).items()):
            if attr.startswith("__"):
                continue
            row: dict[str, Any] | None = None
            if isinstance(value, functools._lru_cache_wrapper):          # noqa: SLF001
                info = value.cache_info()
                row = {"nome": f"{mod_name}.{attr}", "tipo": "lru_cache", "entradas": info.currsize,
                       "maximo": info.maxsize}
            elif _is_container(value):
                n = _safe_len(value)
                if not n:
                    continue
                row = {"nome": f"{mod_name}.{attr}", "tipo": type(value).__name__, "entradas": n}
                if deep:
                    size, est = estimate_size(value, sample)
                    row.update(bytes_estimados=size, estimado=est)
            if row:
                rows.append(row)
    rows.sort(key=lambda r: (-(r.get("bytes_estimados") or 0), -r["entradas"]))
    return rows[:limit]


def type_histogram(limit: int = 15) -> list[dict]:
    """Histograma dos objetos rastreados pelo gc, por tipo (contagem e bytes rasos). Cria uma lista com todos
    os objetos: só no modo profundo."""
    from collections import Counter

    count: Counter = Counter()
    size: Counter = Counter()
    for o in gc.get_objects():
        t = type(o).__name__
        count[t] += 1
        size[t] += sys.getsizeof(o, 0)
    return [{"tipo": t, "objetos": count[t], "bytes_rasos": size[t]} for t, _ in size.most_common(limit)]


def pymalloc_stats() -> dict | None:
    """Estatísticas do alocador de objetos pequenos do CPython (`sys._debugmallocstats`, que escreve em stderr):
    bytes em blocos vivos × bytes de arenas reservadas. A diferença é fragmentação: RSS que NÃO é dado vivo e
    que `gc.collect()` e `malloc_trim` não devolvem (uma arena só volta ao SO quando todas as suas páginas
    ficam livres). Devolve None se o interpretador não tiver a função ou stderr não for um arquivo."""
    import tempfile

    if not hasattr(sys, "_debugmallocstats"):
        return None
    try:
        fd = sys.stderr.fileno()
    except (OSError, ValueError, AttributeError):
        return None
    saved = os.dup(fd)
    try:
        with tempfile.TemporaryFile() as tf:
            os.dup2(tf.fileno(), fd)
            try:
                sys._debugmallocstats()
                sys.stderr.flush()
            finally:
                os.dup2(saved, fd)
            tf.seek(0)
            text = tf.read().decode("utf-8", "replace")
    finally:
        os.close(saved)
    vals: dict[str, int] = {}
    pick: dict[str, int | float] = {}
    for line in text.splitlines():
        m = re.match(r"^\s*(\d[\d,]*) arenas \* (\d[\d,]*) bytes/arena\s*=\s*(\d[\d,]*)\s*$", line)
        if m:                                           # "2362 arenas * 1048576 bytes/arena = 2,476,..."
            pick["arenas_atuais"] = int(m.group(1).replace(",", ""))
            pick["bytes_arenas_reservadas"] = int(m.group(3).replace(",", ""))
            continue
        m = re.match(r"^\s*(.*?)\s*=\s*([0-9,]+)\s*$", line)
        if m:
            vals[re.sub(r"\s+", " ", m.group(1)).strip()] = int(m.group(2).replace(",", ""))
    for key, name in (("# bytes in allocated blocks", "bytes_em_blocos_vivos"),
                      ("# bytes in available blocks", "bytes_em_blocos_livres_em_paginas_usadas"),
                      ("# bytes lost to pool headers", "bytes_perdidos_cabecalhos"),
                      ("# bytes lost to quantization", "bytes_perdidos_quantizacao"),
                      ("# bytes lost to arena alignment", "bytes_perdidos_alinhamento"),
                      ("# arenas allocated total", "arenas_alocadas_total"), ("# arenas reclaimed", "arenas_devolvidas")):
        if key in vals:
            pick[name] = vals[key]
    for k, v in vals.items():                       # "N unused pools * 16384 bytes"
        if "unused pools" in k:
            pick["bytes_em_paginas_livres"] = v
    res, vivos = pick.get("bytes_arenas_reservadas"), pick.get("bytes_em_blocos_vivos")
    if res and vivos is not None:
        pick["fragmentacao_pct"] = round(100 * (1 - vivos / res), 1)
    return pick or None


def latest_cache_report(cache: Any) -> dict | None:
    if cache is None:
        return None
    out: dict[str, Any] = {"entradas": _safe_len(cache)}
    for attr in ("size_bytes", "max_bytes", "max_entry_bytes"):
        v = getattr(cache, attr, None)
        try:
            out[attr] = v() if callable(v) else v
        except Exception:  # noqa: BLE001
            pass
    return out


def collect(store: Any, latest_cache: Any = None, deep: bool = False, sample: int = 64) -> dict:
    t0 = time.perf_counter()
    sample = max(8, min(int(sample), 512))
    # pymalloc só no profundo: `sys._debugmallocstats` percorre todas as arenas segurando o GIL e, com carga ao lado, chegou a parar a API
    # por 21 s (teste de 2026-11-23); o diag leve é o que o amostrador de memória chama a cada 30 s durante o pipeline.
    rep = {"processo": process_info(deep), "pymalloc": pymalloc_stats() if deep else None, "store": store_report(store, deep, sample),
           "byte_cache_latest": latest_cache_report(latest_cache), "profundo": bool(deep), "amostra": sample if deep else None,
           "caches_de_modulo": module_caches_report(deep, sample)}
    if deep:
        rep["histograma_de_tipos"] = type_histogram()
    rep["duracao_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return rep
