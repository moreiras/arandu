# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`arandu gc --compactar`: passa um snapshot antigo ao `layout_version` 2 (ver `core/layout.py`) e desfaz.

O original só sai depois de três verificações: (1) cada membro do ZIP e cada camada compartilhada tem o SHA-256 do manifesto;
(2) com o original posto em quarentena (`.compactacao/` dentro do snapshot), o leitor da API (`Store`) devolve, byte a byte, os mesmos
documentos; (3) o manifesto novo foi gravado por inteiro. Qualquer falha devolve tudo ao lugar (o snapshot volta a ser o de antes).
`descompactar` faz o caminho inverso e confere os checksums do manifesto.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import zipfile
from pathlib import Path
from typing import Optional

from core import layout
from core.integridade import sha256_arquivo

QUARENTENA = ".compactacao"
_DATA_FIXA = (1980, 1, 1, 0, 0, 0)       # ZIP reprodutível: o mesmo conteúdo gera o mesmo arquivo
_AMOSTRA_API = 300


class CompactacaoErro(RuntimeError):
    pass


def _manifesto(pub: Path) -> dict:
    return json.loads((pub / "manifest.json").read_text(encoding="utf-8"))


def _gravar_manifesto(pub: Path, man: dict) -> None:
    tmp = pub / "manifest.json.tmp"
    tmp.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, pub / "manifest.json")


def _hex(sha: str) -> str:
    return sha.split(":", 1)[-1]


def plano(base: Path, data: str) -> dict:
    """O que a compactação faria com `data`, sem tocar em nada."""
    pub = base / "published" / data
    if not (pub / "manifest.json").is_file():
        raise CompactacaoErro(f"{data}: sem manifest.json")
    man = _manifesto(pub)
    if man.get("layout_version", 1) >= 2:
        return {"data": data, "estado": "ja-compactado"}
    asns = pub / "asns"
    arquivos = [p for p in asns.iterdir() if p.is_file()] if asns.is_dir() else []
    comp = [(rel, pub / rel) for rel in layout.COMPARTILHAVEIS if (pub / rel).is_file()]
    return {
        "data": data, "estado": "compactavel", "asns_arquivos": len(arquivos), "asns_bytes": sum(p.stat().st_size for p in arquivos),
        "compartilhaveis": [{"rel": r, "bytes": p.stat().st_size} for r, p in comp],
    }


def _montar_zip(asns: Path, destino: Path) -> int:
    n = 0
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(asns.iterdir()):
            if not p.is_file():
                continue
            zi = zipfile.ZipInfo(p.name, _DATA_FIXA)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, p.read_bytes(), compresslevel=6)
            n += 1
    return n


def _verificar_zip(zip_path: Path, asns: Path, checksums: dict[str, str]) -> int:
    """O ZIP tem de ser idêntico ao diretório, byte a byte. Devolve quantos arquivos **já divergiam do manifesto no disco**.

    Um snapshot alterado depois de o manifesto fechar tem documentos com checksum diferente do manifesto antes de qualquer
    compactação. Isso não impede a compactação — o que ela não pode é mudar o conteúdo —, mas fica registrado em `compactado.divergentes_previos`."""
    import hashlib
    divergentes = 0
    with zipfile.ZipFile(zip_path) as z:
        nomes = set(z.namelist())
        em_disco = {p.name for p in asns.iterdir() if p.is_file()}
        if nomes != em_disco:
            raise CompactacaoErro(f"o ZIP tem {len(nomes)} membros e o diretório {len(em_disco)}")
        for nome in sorted(nomes):
            dados = z.read(nome)
            if dados != (asns / nome).read_bytes():
                raise CompactacaoErro(f"asns/{nome} difere entre o ZIP e o diretório")
            esperado = checksums.get(f"asns/{nome}")
            if esperado is not None and "sha256:" + hashlib.sha256(dados).hexdigest() != esperado:
                divergentes += 1
    return divergentes


def _verificar_leitura_pela_api(base: Path, data: str, original: Path, asns: list[int]) -> None:
    """Com o original em quarentena, o `Store` (o leitor da API) tem de devolver os mesmos documentos e as camadas compartilhadas."""
    from api.store import Store

    st = Store(base)
    for asn in asns:
        doc = st.asn_detail(data, asn)
        if doc is None or doc != json.loads((original / f"{asn}.json").read_bytes()):
            raise CompactacaoErro(f"o Store não leu asns/{asn}.json do ZIP igual ao original")
    for nome in ("index.json", "names.json"):
        if (original / nome).is_file() and layout.ler_bytes(base / "published" / data, f"asns/{nome}") != (original / nome).read_bytes():
            raise CompactacaoErro(f"asns/{nome} não lido do ZIP")


def compactar(base: Path, data: str) -> dict:
    pub = base / "published" / data
    p = plano(base, data)
    if p["estado"] != "compactavel":
        return p
    man = _manifesto(pub)
    checksums = man.get("checksums") or {}
    asns = pub / "asns"
    quarentena = pub / QUARENTENA
    if quarentena.exists():
        raise CompactacaoErro(f"{quarentena} já existe: uma compactação anterior não terminou; confira antes de repetir")
    zip_tmp = pub / "asns.zip.tmp"
    movidos: list[tuple[Path, Path]] = []        # (onde estava, onde está agora) para poder devolver
    novos_shared: list[Path] = []
    try:
        membros = _montar_zip(asns, zip_tmp)
        divergentes = _verificar_zip(zip_tmp, asns, checksums)
        compartilhados: dict[str, str] = {}
        for item in p["compartilhaveis"]:
            rel = item["rel"]
            sha = checksums.get(rel) or sha256_arquivo(pub / rel)
            if sha256_arquivo(pub / rel) != sha:
                raise CompactacaoErro(f"{rel} não bate com o checksum do manifesto; não compartilhado")
            alvo = base / "published" / "_shared" / _hex(sha) / Path(rel).name
            if not alvo.exists():
                alvo.parent.mkdir(parents=True, exist_ok=True)
                tmp = alvo.with_name(alvo.name + ".tmp")
                shutil.copy2(pub / rel, tmp)
                os.replace(tmp, alvo)
                novos_shared.append(alvo)
            if sha256_arquivo(alvo) != sha:
                raise CompactacaoErro(f"cópia compartilhada de {rel} não bate com o checksum")
            compartilhados[rel] = _hex(sha)
        # coloca o original em quarentena e o ZIP no lugar
        nomes = [p_.name for p_ in asns.iterdir() if p_.is_file()]
        quarentena.mkdir()
        os.replace(asns, quarentena / "asns"); movidos.append((asns, quarentena / "asns"))
        for rel in compartilhados:
            (quarentena / Path(rel).parent).mkdir(parents=True, exist_ok=True)
            os.replace(pub / rel, quarentena / rel); movidos.append((pub / rel, quarentena / rel))
        os.replace(zip_tmp, pub / "asns.zip")
        manifesto_antigo = (pub / "manifest.json").read_bytes()
        man["layout_version"] = 2
        man["compactado"] = {
            "em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "asns": {"arquivo": "asns.zip", "membros": membros, "divergentes_previos": divergentes},
            "compartilhados": compartilhados, "layout_anterior": 1,
        }
        _gravar_manifesto(pub, man)
        layout.esquecer(pub)
        try:
            ids = sorted(int(n[:-5]) for n in nomes if n[:-5].isdigit())
            passo = max(1, len(ids) // _AMOSTRA_API)
            _verificar_leitura_pela_api(base, data, quarentena / "asns", ids[::passo])
            for rel in compartilhados:
                if layout.ler_bytes(pub, rel) != (quarentena / rel).read_bytes():
                    raise CompactacaoErro(f"{rel} não lido de _shared/ igual ao original")
        except Exception:
            (pub / "manifest.json").write_bytes(manifesto_antigo)
            layout.esquecer(pub)
            raise
    except Exception:
        for onde, agora in reversed(movidos):
            if agora.exists():
                onde.parent.mkdir(parents=True, exist_ok=True)
                os.replace(agora, onde)
        for f in (pub / "asns.zip", zip_tmp):
            f.unlink(missing_ok=True)
        for a in novos_shared:
            a.unlink(missing_ok=True)
        shutil.rmtree(quarentena, ignore_errors=True)
        layout.esquecer(pub)
        raise
    liberado = sum(f.stat().st_size for f in quarentena.rglob("*") if f.is_file())
    arquivos_antes = sum(1 for f in quarentena.rglob("*") if f.is_file())
    shutil.rmtree(quarentena)
    layout.esquecer(pub)
    return {**p, "estado": "compactado", "zip_bytes": (pub / "asns.zip").stat().st_size, "membros": membros,
            "arquivos_removidos": arquivos_antes, "liberado_bytes": liberado, "compartilhados": compartilhados,
            "divergentes_previos": divergentes}


def descompactar(base: Path, data: str) -> dict:
    """Devolve o snapshot ao formato 1: extrai `asns.zip`, copia as camadas de `_shared/` e confere os checksums do manifesto."""
    pub = base / "published" / data
    man = _manifesto(pub)
    comp = man.get("compactado")
    if man.get("layout_version", 1) < 2 or not comp:
        return {"data": data, "estado": "nao-compactado"}
    checksums = man.get("checksums") or {}
    tmp = pub / "asns.extraindo"
    shutil.rmtree(tmp, ignore_errors=True)
    copiados: list[Path] = []
    try:
        with zipfile.ZipFile(pub / "asns.zip") as z:
            tmp.mkdir()
            z.extractall(tmp)
        # a compactação registrou quantos já divergiam do manifesto; a extração não pode ter mais nem menos
        previos = (comp.get("asns") or {}).get("divergentes_previos", 0)
        diverge = sum(1 for nome in os.listdir(tmp) if checksums.get(f"asns/{nome}") and sha256_arquivo(tmp / nome) != checksums[f"asns/{nome}"])
        if diverge != previos:
            raise CompactacaoErro(f"{diverge} arquivos extraídos divergem do manifesto; eram {previos} quando foi compactado")
        for rel, h in (comp.get("compartilhados") or {}).items():
            origem = base / "published" / "_shared" / h / Path(rel).name
            destino = pub / rel
            t = destino.with_name(destino.name + ".tmp")
            shutil.copy2(origem, t)
            if sha256_arquivo(t) != checksums.get(rel, f"sha256:{h}"):
                t.unlink()
                raise CompactacaoErro(f"{rel} de _shared/ não bate com o manifesto")
            os.replace(t, destino); copiados.append(destino)
        os.replace(tmp, pub / "asns")
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        for c in copiados:
            c.unlink(missing_ok=True)
        raise
    man["layout_version"] = comp.get("layout_anterior", 1)
    man.pop("compactado", None)
    _gravar_manifesto(pub, man)
    (pub / "asns.zip").unlink()
    layout.esquecer(pub)
    return {"data": data, "estado": "descompactado", "membros": len(os.listdir(pub / "asns"))}


def orfaos_shared(base: Path) -> list[Path]:
    """Diretórios de `_shared/<hash>` que nenhum manifesto cita (sobram quando todos os que os usavam foram descompactados ou removidos)."""
    shared = base / "published" / "_shared"
    if not shared.is_dir():
        return []
    usados: set[str] = set()
    for d in (base / "published").iterdir():
        m = d / "manifest.json"
        if d.is_dir() and m.is_file():
            try:
                usados |= set(((json.loads(m.read_text(encoding="utf-8")).get("compactado") or {}).get("compartilhados") or {}).values())
            except ValueError:
                continue
    return [d for d in sorted(shared.iterdir()) if d.is_dir() and d.name not in usados]
