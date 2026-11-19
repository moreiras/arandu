# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Versões imutáveis de fonte: registro, listagem e resolução.

Layout (aditivo; `raw/`, `normalized/` e `published/` não mudam):

    data/sources/<id>/<as_of>/meta.json
    data/sources/<id>/<as_of>/data/<caminho relativo>...
    data/sources/<id>/<as_of>.r2/...     revisão: mesma as_of com conteúdo diferente (ex.: `--force`)
    data/sources/<id>/_log.jsonl         trilha só de acréscimo (nova | confirmada | revisao)

`as_of` é a referência do dado (a data da coleta, ou o mês de referência no SICI); `coletado_em` é quando a versão
passou a existir e decide se ela está disponível para um snapshot (`coletado_em <= data do snapshot`).
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional

LAYOUT = 1
_REV = re.compile(r"^(?P<as_of>[0-9]{4}-[0-9]{2}(?:-[0-9]{2})?)(?:\.r(?P<rev>[0-9]+))?$")


@dataclass(frozen=True)
class Versao:
    fonte: str
    as_of: str
    revisao: int
    nome: str                      # nome da pasta: '2026-10-18' ou '2026-10-18.r2'
    coletado_em: str               # ISO UTC (relógio da coleta)
    disponivel_desde: str          # AAAA-MM-DD: a partir de qual snapshot a versão pode ser usada
    hash: str
    ok: bool
    tamanho: int
    arquivos: tuple[str, ...]
    origem: str
    caminho: Path = field(compare=False, default=Path("."))

    @property
    def data_dir(self) -> Path:
        return self.caminho / "data"

    @property
    def coletado_dia(self) -> str:
        return self.coletado_em[:10]


def _agora() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


# Campos que mudam a cada execução sem mudar o dado (mesma lista do replay): ficam de fora do hash de conteúdo.
VOLATEIS = {"generated_at", "published_at", "pipeline_version", "checksums", "source_file",
            "receita_socios_generated_at", "snapshot_date", "date"}


def _sem_volateis(x):
    if isinstance(x, dict):
        return {k: _sem_volateis(v) for k, v in x.items() if k not in VOLATEIS}
    if isinstance(x, list):
        return [_sem_volateis(v) for v in x]
    return x


def _sha256_conteudo(path: Path) -> str:
    """Hash do conteúdo: JSON (.json/.json.gz) sem os campos voláteis; qualquer outro arquivo, os bytes.

    Sem isso, cada coleta teria hash novo só por causa de `generated_at` e toda reexecução viraria uma revisão."""
    if path.name.endswith((".json", ".json.gz")):
        try:
            if path.name.endswith(".gz"):
                with gzip.open(path, "rt", encoding="utf-8") as f:
                    dado = json.load(f)
            else:
                dado = json.loads(path.read_text(encoding="utf-8"))
            return hashlib.sha256(json.dumps(_sem_volateis(dado), sort_keys=True, ensure_ascii=False,
                                             separators=(",", ":")).encode()).hexdigest()
        except (OSError, ValueError):
            pass
    return _sha256(path)


def hash_do_conjunto(arquivos: Mapping[str, Path]) -> tuple[str, list[dict]]:
    """Hash determinístico do conjunto (ordem dos caminhos relativos) e a lista de arquivos com hashes e tamanho."""
    itens, h = [], hashlib.sha256()
    for rel in sorted(arquivos):
        p = arquivos[rel]
        conteudo = _sha256_conteudo(p)
        itens.append({"caminho": rel, "sha256": _sha256(p), "conteudo_sha256": conteudo, "bytes": p.stat().st_size})
        h.update(f"{rel}\0{conteudo}\n".encode())
    return h.hexdigest(), itens


def raiz(data_dir: Path, fonte: str) -> Path:
    return Path(data_dir) / "sources" / fonte


def _ler_meta(pasta: Path) -> Optional[Versao]:
    try:
        m = json.loads((pasta / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    mt = _REV.match(pasta.name)
    if not mt:
        return None
    return Versao(fonte=m["fonte"], as_of=m["as_of"], revisao=int(mt.group("rev") or 1), nome=pasta.name,
                  coletado_em=m["coletado_em"], disponivel_desde=m.get("disponivel_desde") or m["coletado_em"][:10], hash=m["hash"], ok=bool(m.get("ok", True)), tamanho=int(m.get("tamanho", 0)),
                  arquivos=tuple(a["caminho"] for a in m.get("arquivos", [])), origem=m.get("origem", ""), caminho=pasta)


def listar(data_dir: Path, fonte: str) -> list[Versao]:
    """Versões da fonte, da mais antiga para a mais nova (por as_of e revisão)."""
    r = raiz(data_dir, fonte)
    if not r.is_dir():
        return []
    vs = [v for p in r.iterdir() if p.is_dir() and not p.name.startswith((".", "_")) for v in [_ler_meta(p)] if v]
    return sorted(vs, key=lambda v: (v.as_of, v.revisao))


def _log(data_dir: Path, fonte: str, evento: str, v: Versao, quando: str, extra: Optional[dict] = None) -> None:
    """`ts` é o relógio; `quando` é a data lógica do snapshot a que a coleta pertence (decide a cadência)."""
    r = raiz(data_dir, fonte)
    r.mkdir(parents=True, exist_ok=True)
    reg = {"ts": _agora(), "quando": quando, "evento": evento, "versao": v.nome, "as_of": v.as_of, "hash": v.hash, **(extra or {})}
    with (r / "_log.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(reg, ensure_ascii=False) + "\n")


def ultima_verificacao(data_dir: Path, fonte: str) -> Optional[str]:
    """Data lógica (AAAA-MM-DD) da última coleta bem-sucedida da fonte, mesmo quando só confirmou uma versão existente."""
    try:
        linhas = (raiz(data_dir, fonte) / "_log.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    melhor = None
    for l in linhas:
        try:
            r = json.loads(l)
            q = r.get("quando") or r["ts"][:10]
        except (ValueError, KeyError):
            continue
        melhor = q if melhor is None or q > melhor else melhor
    return melhor


def registrar(data_dir: Path, fonte: str, as_of: str, arquivos: Mapping[str, Path], *, origem: str = "",
              coletado_em: Optional[str] = None, disponivel_desde: Optional[str] = None, ok: bool = True,
              pipeline_version: str = "") -> tuple[Versao, str]:
    """Registra uma versão. Devolve (versão, evento) com evento 'nova', 'confirmada' (mesmo conteúdo) ou 'revisao'.

    Idempotente: o mesmo conteúdo para a mesma `as_of` não cria pasta nova. Conteúdo diferente cria `<as_of>.rN`
    (a versão antiga nunca é alterada). Escrita atômica: monta numa pasta temporária e renomeia.
    """
    if not _REV.match(as_of):
        raise ValueError(f"as_of inválida: {as_of!r} (use AAAA-MM-DD ou AAAA-MM)")
    arquivos = {k: Path(v) for k, v in arquivos.items()}
    faltam = [k for k, v in arquivos.items() if not v.is_file()]
    if faltam:
        raise FileNotFoundError(f"arquivos ausentes para {fonte}: {faltam[:3]}")
    h, itens = hash_do_conjunto(arquivos)
    existentes = [v for v in listar(data_dir, fonte) if v.as_of == as_of]
    quando = disponivel_desde or (coletado_em or _agora())[:10]
    for v in existentes:
        if v.hash == h:
            _log(data_dir, fonte, "confirmada", v, quando)
            return v, "confirmada"
    n = len(existentes) + 1
    nome = as_of if n == 1 else f"{as_of}.r{n}"
    r = raiz(data_dir, fonte)
    r.mkdir(parents=True, exist_ok=True)
    final = r / nome
    tmp = r / f".tmp-{nome}-{os.getpid()}"
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        for rel, p in arquivos.items():
            destino = tmp / "data" / rel
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, destino)           # cópia, não link: coletores que regravam no lugar não podem alterar a versão
        coletado = coletado_em or _agora()
        meta = {"fonte": fonte, "as_of": as_of, "revisao": n, "coletado_em": coletado,
                "disponivel_desde": disponivel_desde or coletado[:10], "hash": h, "ok": ok,
                "tamanho": sum(i["bytes"] for i in itens), "arquivos": itens, "origem": origem,
                "pipeline_version": pipeline_version, "layout": LAYOUT}
        (tmp / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        os.rename(tmp, final)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    v = _ler_meta(final)
    assert v is not None
    evento = "nova" if n == 1 else "revisao"
    _log(data_dir, fonte, evento, v, quando)
    return v, evento


def resolver(data_dir: Path, fonte: str, snapshot_date: str) -> Optional[Versao]:
    """Última versão válida disponível em `snapshot_date`: `ok` e `disponivel_desde <= snapshot_date` (a mais nova por as_of/revisão).

    `disponivel_desde` é a data do snapshot em cujo pipeline a versão foi coletada (uma execução tardia da data D continua
    valendo para D), ou o dia da coleta quando registrada à mão."""
    cand = [v for v in listar(data_dir, fonte) if v.ok and v.disponivel_desde <= snapshot_date]
    return cand[-1] if cand else None
