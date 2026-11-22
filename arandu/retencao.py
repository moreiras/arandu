# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Retenção: perfis em `catalog/retencao.yaml`, plano do `arandu gc` e remoção.

A política diz o que pode sair; os **pisos em código** dizem o que nunca sai, seja qual for o perfil:
as `PISO_DATAS` mais recentes de cada camada, a data do dia, as datas protegidas do perfil, a última versão de cada fonte no
armazém e toda versão ainda referenciada por um `published`. Erro de configuração só pode resultar em "não apagou".
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

CAMADAS = ("published", "normalized", "raw", "build")
PISO_DATAS = {"published": 4, "normalized": 2, "raw": 2, "build": 2}      # build: fragmentos do compose
PISO_VERSOES = 2
_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class Camada:
    tudo: bool = False
    datas: Optional[int] = None
    semanas: Optional[int] = None
    um_por_mes: bool = False


@dataclass(frozen=True)
class Perfil:
    nome: str
    descricao: str
    camadas: dict[str, Camada]
    armazem_versoes: int
    protegidas: frozenset[str] = field(default_factory=frozenset)


def carregar(caminho: Path, nome: Optional[str] = None) -> Perfil:
    raw = yaml.safe_load(Path(caminho).read_text(encoding="utf-8")) or {}
    nome = nome or os.environ.get("ARANDU_RETENCAO") or raw.get("perfil_padrao")
    perfis = raw.get("perfis") or {}
    if nome not in perfis:
        raise ValueError(f"perfil de retenção '{nome}' não existe em {caminho} (há: {', '.join(sorted(perfis))})")
    p = perfis[nome]
    camadas = {}
    for c in CAMADAS:
        spec = p.get(c) or ({"datas": 2} if c == "build" else {})     # `build` é opcional nos perfis: padrão 2 datas
        extra = set(spec) - {"tudo", "datas", "semanas", "um_por_mes"}
        if extra:
            raise ValueError(f"perfil {nome}.{c}: chave(s) desconhecida(s) {sorted(extra)}")
        if not spec:
            raise ValueError(f"perfil {nome}: falta a camada '{c}'")
        camadas[c] = Camada(tudo=bool(spec.get("tudo")), datas=spec.get("datas"), semanas=spec.get("semanas"),
                            um_por_mes=bool(spec.get("um_por_mes")))
    prot = frozenset(str(d) for d in p.get("protegidas") or [])
    for d in prot:
        if not _DATA.match(d):
            raise ValueError(f"perfil {nome}: data protegida inválida '{d}'")
    return Perfil(nome, p.get("descricao", ""), camadas, int((p.get("armazem") or {}).get("versoes", PISO_VERSOES)), prot)


def _tamanho(p: Path) -> int:
    total = 0
    for raiz, _, arqs in os.walk(p):
        for a in arqs:
            try:
                total += os.lstat(os.path.join(raiz, a)).st_size
            except OSError:
                pass
    return total


def _datas(data_dir: Path, camada: str) -> list[str]:
    d = data_dir / camada
    if not d.is_dir():
        return []
    return sorted((x.name for x in d.iterdir() if x.is_dir() and not x.is_symlink() and _DATA.match(x.name)), reverse=True)


def _manter_da_camada(c: Camada, datas: list[str], em: str) -> set[str]:
    """Datas que a política manda guardar (antes dos pisos); `datas` em ordem decrescente."""
    if c.tudo:
        return set(datas)
    manter: set[str] = set()
    if c.datas is not None:
        manter |= set(datas[: max(c.datas, 0)])
    if c.semanas is not None:
        limite = (dt.date.fromisoformat(em) - dt.timedelta(weeks=c.semanas)).isoformat()
        manter |= {d for d in datas if d >= limite}
    if c.um_por_mes:
        por_mes: dict[str, str] = {}
        for d in datas:
            por_mes.setdefault(d[:7], d)
        manter |= set(por_mes.values())
    return manter


def referenciadas(data_dir: Path) -> set[tuple[str, str]]:
    """(fonte, versão) citadas no `sources[]` de qualquer `published/*/manifest.json` que ainda exista."""
    refs: set[tuple[str, str]] = set()
    base = data_dir / "published"
    if not base.is_dir():
        return refs
    for d in base.iterdir():
        try:
            m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for s in m.get("sources") or []:
            if s.get("id") and s.get("versao"):
                refs.add((s["id"], s["versao"]))
    return refs


def plano(data_dir: Path, em: str, perfil: Perfil, manter_por_fonte: Optional[dict[str, int]] = None) -> dict:
    """O que o perfil removeria e o que os pisos seguraram. Não remove nada.

    `manter_por_fonte` (do catálogo, `armazem.manter_versoes`) sobe o número de versões de fontes de histórico fino."""
    from core.store import listar

    itens: list[dict] = []
    seguradas: list[dict] = []
    resumo: dict = {}
    for camada in CAMADAS:
        datas = _datas(data_dir, camada)
        politica = _manter_da_camada(perfil.camadas[camada], datas, em)
        pisos = {d: "recente" for d in datas[: PISO_DATAS[camada]]}
        pisos.update({d: "protegida" for d in perfil.protegidas if d in datas})
        if em in datas:
            pisos[em] = "data do dia"
        for d in datas:
            if d in politica:
                continue
            if d in pisos:
                seguradas.append({"camada": camada, "item": d, "motivo": pisos[d]})
                continue
            p = data_dir / camada / d
            itens.append({"camada": camada, "item": d, "bytes": _tamanho(p), "caminho": str(p)})
        resumo[camada] = {"datas": len(datas), "removeriam": sum(1 for i in itens if i["camada"] == camada)}
    # Basemap (tiles): a versão servida (current.json) e a anterior; reconstruir exige ~2× o espaço de uma versão.
    tiles = data_dir / "tiles"
    if tiles.is_dir():
        vers = sorted((x.name for x in tiles.iterdir() if x.is_dir() and not x.is_symlink() and _DATA.match(x.name)), reverse=True)
        try:
            atual = json.loads((tiles / "current.json").read_text(encoding="utf-8")).get("date")
        except (OSError, ValueError):
            atual = None
        manter = {atual} if atual else set()
        manter |= set([v for v in vers if v != atual][:1])
        for v in vers:
            if v in manter:
                seguradas.append({"camada": "tiles", "item": v, "motivo": "versão atual" if v == atual else "versão anterior"})
            else:
                itens.append({"camada": "tiles", "item": v, "bytes": _tamanho(tiles / v), "caminho": str(tiles / v)})
    refs = referenciadas(data_dir)
    fontes = data_dir / "sources"
    if fontes.is_dir():
        for f in sorted(x.name for x in fontes.iterdir() if x.is_dir() and not x.name.startswith((".", "_"))):
            vs = listar(data_dir, f)                      # da mais antiga para a mais nova
            n = max(perfil.armazem_versoes, PISO_VERSOES, (manter_por_fonte or {}).get(f, 0))
            manter = {v.nome for v in vs[-n:]}
            for v in vs:
                if v.nome in manter:
                    continue
                if (f, v.nome) in refs:
                    seguradas.append({"camada": "armazem", "item": f"{f}/{v.nome}", "motivo": "referenciada por um published"})
                    continue
                itens.append({"camada": "armazem", "item": f"{f}/{v.nome}", "bytes": _tamanho(v.caminho), "caminho": str(v.caminho)})
    return {"perfil": perfil.nome, "descricao": perfil.descricao, "em": em, "itens": itens, "seguradas_pelos_pisos": seguradas,
            "resumo": resumo, "liberaria_bytes": sum(i["bytes"] for i in itens)}


def _marcador(data_dir: Path) -> Path:
    return data_dir / "ops" / "gc" / "dry-run-feito.json"


def registrar_dry_run(data_dir: Path, p: dict) -> None:
    m = _marcador(data_dir)
    m.parent.mkdir(parents=True, exist_ok=True)
    m.write_text(json.dumps({"em": p["em"], "perfil": p["perfil"], "itens": len(p["itens"]),
                             "quando": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}), encoding="utf-8")


def _seguro(data_dir: Path, item: dict) -> bool:
    """O caminho a remover tem de ser exatamente <data>/<camada>/<data> ou <data>/sources/<fonte>/<versão>, sem symlink."""
    p = Path(item["caminho"])
    if p.is_symlink() or not p.is_dir():
        return False
    esperado = (data_dir / "sources" / item["item"]) if item["camada"] == "armazem" else (data_dir / item["camada"] / item["item"])
    return p.resolve() == esperado.resolve() and data_dir.resolve() in p.resolve().parents


def aplicar(data_dir: Path, p: dict, *, lock_ativo: bool = False) -> dict:
    """Remove os itens do plano. Recusa sem um `--dry-run` anterior e com execução do pipeline em andamento."""
    if lock_ativo:
        raise RuntimeError("há uma execução do arandu em andamento (pipeline ou trilha contínua: data/ops/arandu.lock, arandu-continuo.lock): o gc não roda em paralelo")
    if not _marcador(data_dir).is_file():
        raise RuntimeError("rode `arandu gc --dry-run` e revise a lista antes do primeiro `--apply`")
    removidos, falhas, bytes_ = [], [], 0
    for i in p["itens"]:
        if not _seguro(data_dir, i):
            falhas.append({"item": f"{i['camada']}/{i['item']}", "erro": "caminho fora do esperado; não removido"})
            continue
        try:
            shutil.rmtree(i["caminho"])
            removidos.append(f"{i['camada']}/{i['item']}")
            bytes_ += i["bytes"]
        except OSError as exc:
            falhas.append({"item": f"{i['camada']}/{i['item']}", "erro": str(exc)})
    rel = {"em": p["em"], "perfil": p["perfil"], "removidos": removidos, "falhas": falhas, "liberados_bytes": bytes_}
    d = data_dir / "ops" / "gc"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{p['em']}.json").write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding="utf-8")
    return rel
