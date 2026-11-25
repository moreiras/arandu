# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Regenera a camada de eventos do histórico (`history/events/`) com a regra atual (`eventos.REGRA_VERSAO`).

Para cada data do índice, em ordem: completa as linhas de ASN gravadas sem os marcadores de presença (lendo o publicado, que não é
alterado), refaz os eventos contra o snapshot anterior e reavalia os pendentes. Devolve, por data e tipo, a contagem antes e depois,
que é o insumo da nota de revisão. Só escreve em `<base>/history/`; rode primeiro numa cópia (`--base` com `published/` ligado por
symlink e uma cópia de `history/`) e confira o relatório antes de trocar a camada servida.

    python -m products.history.regenerar_eventos --base DIR [--relatorio ARQ.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from core.common import configure_logging, data_dir
from products.history import build
from products.history import eventos as evs


def _contagem(base: Path, d: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for e in build.ler_jsonl_gz(build.dir_eventos(base) / f"{d}.jsonl.gz"):
        out[e["tipo"]] = out.get(e["tipo"], 0) + 1
    return out


def _entrada(base: Path, d: str) -> dict:
    caminho = build.raiz_historico(base) / "index.json"
    indice = json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else {}
    e = next((x for x in indice.get("snapshots", []) if x["date"] == d), {})
    return {k: v for k, v in e.items() if k != "date"}


def regenerar(base: Path, log) -> dict:
    datas = build._datas_indice(base)
    antes = {d: _contagem(base, d) for d in datas}
    completadas = {d: build.completar_presenca(base, d, log) for d in datas}
    for d in datas:
        res = build.gerar_eventos(base, d, log)
        build.atualizar_indice(base, d, {**_entrada(base, d), **res,
                                         "eventos_regenerados_em": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    relatorio: dict = {"regra": evs.REGRA_VERSAO, "datas": {}, "totais": {}, "linhas_completadas": completadas}
    for d in datas:
        depois = _contagem(base, d)
        relatorio["datas"][d] = {t: {"antes": antes[d].get(t, 0), "depois": depois.get(t, 0)} for t in sorted(set(antes[d]) | set(depois))}
        for t, c in relatorio["datas"][d].items():
            tot = relatorio["totais"].setdefault(t, {"antes": 0, "depois": 0})
            tot["antes"] += c["antes"]
            tot["depois"] += c["depois"]
    log.info("history eventos regenerados", datas=len(datas), regra=evs.REGRA_VERSAO,
             antes=sum(c["antes"] for c in relatorio["totais"].values()), depois=sum(c["depois"] for c in relatorio["totais"].values()))
    return relatorio


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Regenera os eventos do histórico com a regra atual")
    p.add_argument("--base", type=Path, default=None, help="diretório de dados (com published/ e history/); padrão: o do ambiente")
    p.add_argument("--relatorio", type=Path, default=None, help="grava o relatório (contagens antes e depois por data e tipo) em JSON")
    a = p.parse_args(argv)
    log = configure_logging()
    base = a.base or data_dir()
    if not (build.raiz_historico(base) / "index.json").exists():
        log.error("history sem índice", base=str(base))
        return 1
    rel = regenerar(base, log)
    if a.relatorio:
        tmp = a.relatorio.with_name(a.relatorio.name + ".tmp")
        tmp.write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, a.relatorio)
    return 0


if __name__ == "__main__":
    sys.exit(main())
