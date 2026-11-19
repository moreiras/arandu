# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Ponte entre o catálogo e o armazém: quais arquivos formam a versão de uma fonte, qual é a sua `as_of`,
como registrá-la e como restaurá-la nos caminhos de sempre (`raw/`, `normalized/`, `published/`)."""
from __future__ import annotations

import gzip
import json
import re
import shutil
from pathlib import Path
from typing import Optional

from core.catalog.loader import Catalog
from core.store.versions import Versao, registrar

TIPOS = ("raw", "normalized", "published")


def _glob(padrao: str, date: str) -> str:
    return re.sub(r"\{[^}]+\}", "*", padrao.replace("{as_of}", date))


def padroes_da_fonte(cat: Catalog, fonte_id: str) -> list[tuple[str, str]]:
    """[(tipo, padrão relativo a <tipo>/<data>/)] que formam a versão. Caches (`../`) nunca entram."""
    s = cat.sources[fonte_id]
    if s.armazem and s.armazem.incluir:
        out = []
        for item in s.armazem.incluir:
            tipo, _, pad = item.partition(":")
            if tipo not in TIPOS or not pad:
                raise ValueError(f"armazem.incluir inválido em {fonte_id}: {item!r}")
            out.append((tipo, pad))
        return out
    out = [("normalized", p) for p in s.saidas.normalizado if not p.startswith("../")]
    out += [("published", p) for p in s.saidas.publicado]
    return out


def arquivos_da_fonte(cat: Catalog, data_dir: Path, fonte_id: str, date: str) -> dict[str, Path]:
    """{'normalized/summary/x.json.gz': caminho} dos arquivos que existem para a fonte naquela data."""
    achados: dict[str, Path] = {}
    for tipo, pad in padroes_da_fonte(cat, fonte_id):
        base = Path(data_dir) / tipo / date
        if not base.is_dir():
            continue
        for p in sorted(base.glob(_glob(pad, date))):
            if p.is_file():
                achados[f"{tipo}/{p.relative_to(base).as_posix()}"] = p
    return achados


def _ler_json(p: Path):
    try:
        if p.name.endswith(".gz"):
            with gzip.open(p, "rt", encoding="utf-8") as f:
                return json.load(f)
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def as_of_do_dado(fonte_id: str, arquivos: dict[str, Path], date: str) -> str:
    """Referência do dado: a data da coleta, salvo nas fontes mensais (SICI: mês de referência; sócios: mês do dump)."""
    campo = {"anatel_sici": "mes_referencia", "anatel_sici_movel": "mes_referencia", "receita_socios": "dump_reference"}.get(fonte_id)
    if campo:
        for rel, p in arquivos.items():
            d = _ler_json(p) if rel.endswith((".json", ".json.gz")) else None
            v = d.get(campo) if isinstance(d, dict) else None
            if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", v):
                return v
    return date


def registrar_da_fonte(cat: Catalog, data_dir: Path, fonte_id: str, date: str, *, pipeline_version: str = "",
                       coletado_em: Optional[str] = None) -> Optional[tuple[Versao, str]]:
    """Registra no armazém a versão que a coleta de `date` produziu. None se a fonte não gerou arquivos."""
    s = cat.sources.get(fonte_id)
    if s is None or s.tipo == "curada":
        return None
    arqs = arquivos_da_fonte(cat, data_dir, fonte_id, date)
    if not arqs:
        return None
    as_of = as_of_do_dado(fonte_id, arqs, date)
    return registrar(data_dir, fonte_id, as_of, arqs, origem=(s.origem.url or "") if s.origem else "",
                     coletado_em=coletado_em, disponivel_desde=date, pipeline_version=pipeline_version)


def materializar(data_dir: Path, versao: Versao, date: str, *, sobrescrever: bool = False) -> list[str]:
    """Restaura os arquivos da versão em `<tipo>/<date>/...` (cópia). Não sobrescreve o que já existe, salvo pedido."""
    feitos = []
    for rel in versao.arquivos:
        tipo, _, resto = rel.partition("/")
        if tipo not in TIPOS:
            continue
        destino = Path(data_dir) / tipo / date / resto
        if destino.exists() and not sobrescrever:
            continue
        destino.parent.mkdir(parents=True, exist_ok=True)
        tmp = destino.with_name(destino.name + ".tmp")
        shutil.copy2(versao.data_dir / rel, tmp)
        tmp.replace(destino)
        feitos.append(rel)
    return feitos
