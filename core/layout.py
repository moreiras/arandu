# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Leitura de `published/<data>/` nos dois formatos (`layout_version` 1 e 2).

Formato 1 (o que o pipeline grava): um arquivo por artefato. Formato 2 (só o que `arandu gc --compactar` produz, em snapshots antigos):

  * **`asns.zip`** no lugar do diretório `asns/` (87 mil arquivos pequenos): ZIP com os mesmos nomes (`1.json`, `index.json`…), de
    acesso aleatório pelo diretório central;
  * **camadas estáticas em `published/_shared/<sha256>/<arquivo>`**: o mesmo conteúdo de rodovias, cabos etc. deixa de se repetir em
    cada semana; o manifesto diz qual hash (`compactado.compartilhados`).

O manifesto continua com os checksums dos caminhos originais (`asns/1.json`), então o conteúdo é verificável nos dois formatos.
Quem lê um artefato de snapshot usa `ler_bytes`/`caminho`, nunca monta o caminho à mão.
"""
from __future__ import annotations

import json
import threading
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Optional

#: diretórios que o formato 2 guarda como `<dir>.zip`
DIRETORIOS_ZIP = ("asns",)
#: camadas que não mudam de semana para semana e passam a viver em `_shared/`
COMPARTILHAVEIS = (
    "maps/ibge_rodovias.geojson", "maps/itu_transmission.geojson", "maps/power_transmission_lines.geojson",
    "maps/submarine_cables.geojson", "maps/submarine_landing_points.geojson",
)

_ZIPS_ABERTOS = 8
_zips: "OrderedDict[str, zipfile.ZipFile]" = OrderedDict()
_trava = threading.Lock()
_compartilhados: dict[str, dict[str, str]] = {}


def _zip_de(caminho: Path) -> Optional[zipfile.ZipFile]:
    chave = str(caminho)
    with _trava:
        z = _zips.get(chave)
        if z is not None:
            _zips.move_to_end(chave)
            return z
        if not caminho.is_file():
            return None
        try:
            z = zipfile.ZipFile(caminho)
        except (OSError, zipfile.BadZipFile):
            return None
        _zips[chave] = z
        while len(_zips) > _ZIPS_ABERTOS:
            _zips.popitem(last=False)[1].close()
        return z


def esquecer(pub: Path) -> None:
    """Fecha o que está aberto sobre `pub` e esquece o manifesto lido (a compactação acabou de mudar o snapshot)."""
    with _trava:
        for chave in [k for k in _zips if k.startswith(str(pub) + "/")]:
            _zips.pop(chave).close()
        _compartilhados.pop(str(pub), None)


def compartilhados(pub: Path) -> dict[str, str]:
    """`{caminho relativo: sha256 hex}` das camadas deste snapshot que estão em `_shared/` (vazio no formato 1)."""
    chave = str(pub)
    if chave not in _compartilhados:
        mapa: dict[str, str] = {}
        try:
            man = json.loads((pub / "manifest.json").read_bytes())
            mapa = dict((man.get("compactado") or {}).get("compartilhados") or {})
        except (OSError, ValueError):
            pass
        _compartilhados[chave] = mapa
    return _compartilhados[chave]


def rel_seguro(rel: str) -> bool:
    """`rel` fica dentro do snapshot: sem NUL, barra invertida, caminho absoluto nem componente `..` (o `code` de uma tool do MCP pode chegar aqui com `../`)."""
    return isinstance(rel, str) and "\0" not in rel and "\\" not in rel and not rel.startswith("/") and ".." not in rel.split("/")


def caminho(pub: Path, rel: str) -> Optional[Path]:
    """Arquivo em disco de `rel` neste snapshot (no próprio diretório ou em `_shared/`); `None` se não está como arquivo ou se `rel` sai do snapshot."""
    if not rel_seguro(rel):
        return None
    p = pub / rel
    if p.exists():
        return p
    h = compartilhados(pub).get(rel)
    if h:
        c = pub.parent / "_shared" / h / Path(rel).name
        if c.exists():
            return c
    return None


def _membro_zip(pub: Path, rel: str) -> Optional[bytes]:
    if not rel_seguro(rel):
        return None
    topo, _, resto = rel.partition("/")
    if topo not in DIRETORIOS_ZIP or not resto:
        return None
    z = _zip_de(pub / f"{topo}.zip")
    if z is None:
        return None
    try:
        return z.read(resto)
    except KeyError:
        return None


def existe(pub: Path, rel: str) -> bool:
    if not rel_seguro(rel):
        return False
    if caminho(pub, rel) is not None:
        return True
    topo, _, resto = rel.partition("/")
    if topo in DIRETORIOS_ZIP and resto:
        z = _zip_de(pub / f"{topo}.zip")
        return z is not None and resto in z.NameToInfo
    return False


def ler_bytes(pub: Path, rel: str) -> Optional[bytes]:
    """Conteúdo bruto de `rel` em qualquer dos dois formatos; `None` se não existe (ou é ilegível)."""
    p = caminho(pub, rel)
    if p is not None:
        try:
            return p.read_bytes()
        except OSError:
            return None
    return _membro_zip(pub, rel)


def ler_bytes_de_caminho(path: Path) -> Optional[bytes]:
    """Como `ler_bytes` para quem tem o caminho completo (`<base>/published/<data>/<rel>`): descobre o snapshot pela pasta `published`."""
    partes = path.parts
    if "published" in partes:
        i = len(partes) - 1 - partes[::-1].index("published")
        if len(partes) > i + 2:
            pub = Path(*partes[: i + 2])
            rel = "/".join(partes[i + 2:])
            return ler_bytes(pub, rel) if rel_seguro(rel) else None
    try:
        return path.read_bytes()
    except OSError:
        return None
