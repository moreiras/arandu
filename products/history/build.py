# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Produto `history`: histórico por snapshot a partir do publicado (`published/{date}/`), sem tocá-lo.

Saídas em `data/history/` (camada derivada e reconstruível; o publicado segue imutável):
  weekly/{date}/asn.jsonl.gz        uma linha por ASN (products/history/esquema.py); determinístico (mesmo snapshot, mesmos bytes)
  weekly/{date}/{ixp,operadora,uf}.jsonl.gz   séries agregadas (products/history/agregados.py), operadora e UF com média móvel de 28 dias
  events/{date}.jsonl.gz       eventos detectados nesta data em relação ao snapshot anterior com histórico (products/history/eventos.py);
                               o estado (pendente, confirmado, revertido) é reavaliado a cada snapshot novo, com regravação atômica
  index.json                   snapshots com histórico, estado da coleta, PTTs coletados, `rules_version` e `built_at`
A pasta se chama `weekly`, mas há uma por snapshot, semanal ou diário.
Idempotente: sem `--force`, snapshot já construído é pulado."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from core.common import configure_logging, data_dir, published_path, read_json_gz, today_str
from products.history import agregados as ag
from products.history import eventos as evs
from products.history.snapshot import Snap
from products.history.esquema import HISTORY_SCHEMA_VERSION
from products.history.linhas import linha_asn


def raiz_historico(base: Path) -> Path:
    return base / "history"


def dir_semanal(base: Path, date_str: str) -> Path:
    return raiz_historico(base) / "weekly" / date_str


def _gravar_atomico(destino: Path, conteudo: bytes) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".tmp")
    tmp.write_bytes(conteudo)
    os.replace(tmp, destino)


def gravar_jsonl_gz(destino: Path, linhas, log=None) -> tuple[int, str]:
    """Grava as linhas (dicts) em JSONL gzip determinístico (mtime 0) e de forma atômica. Devolve (n, sha256 do conteúdo sem compressão)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".tmp")
    sha = hashlib.sha256()
    n = 0
    with tmp.open("wb") as bruto, gzip.GzipFile(filename="", mode="wb", fileobj=bruto, compresslevel=6, mtime=0) as gz:
        for linha in linhas:
            b = (json.dumps(linha, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
            gz.write(b)
            sha.update(b)
            n += 1
            if log and n % 20000 == 0:
                log.info("history progress", linhas=n)
    os.replace(tmp, destino)
    return n, sha.hexdigest()


def linhas_asn(pub: Path, log=None):
    """Linhas de todos os ASNs do snapshot, em ordem numérica."""
    arquivos = sorted((p for p in (pub / "asns").glob("*.json") if p.stem.isdigit()), key=lambda p: int(p.stem))
    for i, p in enumerate(arquivos, 1):
        if log and i % 10000 == 0:
            log.info("history leitura", lidos=i, total=len(arquivos))
        yield linha_asn(json.loads(p.read_text(encoding="utf-8")))


def meta_do_snapshot(pub: Path) -> dict:
    """O que do manifesto importa ao histórico: se a coleta foi completa e com quais regras de alerta."""
    m = json.loads((pub / "manifest.json").read_text(encoding="utf-8")) if (pub / "manifest.json").exists() else {}
    coletados = m.get("ixps_collected")
    return {
        "coleta": m.get("coleta"),                       # completa | parcial | pendente; ausente em snapshot sem o campo
        "coleta_ok": m.get("coleta_ok"),
        "ptts_coletados": sorted(coletados) if coletados is not None else None,
        "ptts_falhos": sorted(m.get("ixps_failed") or []),
        "rules_version": m.get("rules_version"),
        "pipeline_version": m.get("pipeline_version"),
    }


def atualizar_indice(base: Path, date_str: str, entrada: dict) -> dict:
    caminho = raiz_historico(base) / "index.json"
    indice = json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else {}
    snaps = {s["date"]: s for s in indice.get("snapshots", [])}
    snaps[date_str] = {"date": date_str, **entrada}
    novo = {"schema_version": HISTORY_SCHEMA_VERSION, "snapshots": [snaps[d] for d in sorted(snaps)]}
    linhas = ",\n".join(json.dumps(s, ensure_ascii=False, separators=(",", ":")) for s in novo["snapshots"])    # um snapshot por linha (diff legível)
    texto = f'{{"schema_version":{HISTORY_SCHEMA_VERSION},"snapshots":[\n{linhas}\n]}}\n'
    _gravar_atomico(caminho, texto.encode("utf-8"))
    return novo


def ler_jsonl_gz(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    with gzip.open(caminho, "rt", encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def _anteriores(base: Path, date_str: str, arquivo: str, chave: str) -> list[dict[str, dict]]:
    """Agregados {chave: linha} das datas com histórico dentro da janela da média móvel (anteriores a `date_str`)."""
    indice = json.loads((raiz_historico(base) / "index.json").read_text(encoding="utf-8")) if (raiz_historico(base) / "index.json").exists() else {}
    out = []
    for s in indice.get("snapshots", []):
        if ag.dentro_da_janela(date_str, s["date"]):
            out.append({ln[chave]: ln for ln in ler_jsonl_gz(dir_semanal(base, s["date"]) / arquivo)})
    return out


def _grupos(pub: Path) -> dict[str, str]:
    """{cnpj: grupo_id}. Só o id do grupo: nomes e documentos de sócios (pessoa física) nunca entram no histórico."""
    caminho = pub / "grupos_societarios.json.gz"
    if not caminho.exists():
        return {}
    by_cnpj = (read_json_gz(caminho) or {}).get("by_cnpj") or {}
    return {c: v["grupo_id"] for c, v in by_cnpj.items() if isinstance(v, dict) and v.get("grupo_id")}


def dir_eventos(base: Path) -> Path:
    return raiz_historico(base) / "events"


def _datas_indice(base: Path) -> list[str]:
    caminho = raiz_historico(base) / "index.json"
    indice = json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else {}
    return sorted(s["date"] for s in indice.get("snapshots", []))


def gerar_eventos(base: Path, date_str: str, log) -> dict:
    """Eventos de `date_str` contra o snapshot anterior com histórico e reavaliação dos eventos pendentes de datas anteriores."""
    datas = sorted(set(_datas_indice(base)) | {date_str})
    anteriores = [d for d in datas if d < date_str]
    eventos = evs.detectar(Snap(base, date_str), Snap(base, anteriores[-1])) if anteriores else []
    gravar_jsonl_gz(dir_eventos(base) / f"{date_str}.jsonl.gz", eventos)
    reavaliados = 0
    for antes in anteriores:                                   # pendentes de datas anteriores: o snapshot novo pode decidi-los
        caminho = dir_eventos(base) / f"{antes}.jsonl.gz"
        velhos = ler_jsonl_gz(caminho)
        if not any(e["estado"] == "pendente" for e in velhos):
            continue
        seguintes = [Snap(base, d) for d in datas if antes < d <= date_str]
        novos = [evs.avaliar(dict(e), seguintes) for e in velhos]
        if novos != velhos:
            gravar_jsonl_gz(caminho, novos)
            reavaliados += sum(1 for a, b in zip(velhos, novos) if a != b)
    por_tipo: dict[str, int] = {}
    for e in eventos:
        por_tipo[e["tipo"]] = por_tipo.get(e["tipo"], 0) + 1
    log.info("history eventos", date=date_str, eventos=len(eventos), anterior=anteriores[-1] if anteriores else None, reavaliados=reavaliados)
    return {"eventos_n": len(eventos), "eventos": por_tipo, "anterior": anteriores[-1] if anteriores else None, "reavaliados": reavaliados}


def construir(base: Path, date_str: str, log, force: bool = False) -> dict:
    pub = published_path(base, date_str)
    if not (pub / "asns").is_dir():
        raise FileNotFoundError(f"snapshot sem documentos de ASN: {pub}")
    destino = dir_semanal(base, date_str)
    if not force and (destino / "asn.jsonl.gz").exists():
        log.info("history já construído; use --force", date=date_str)
        return {"pulado": True}
    br: list[dict] = []

    def _linhas():
        for ln in linhas_asn(pub, log):
            if ln["is_br"]:
                br.append(ln)
            yield ln

    entrada = {**meta_do_snapshot(pub)}
    n, sha = gravar_jsonl_gz(destino / "asn.jsonl.gz", _linhas(), log)
    entrada.update(asn_linhas=n, asn_sha256=sha)
    idx_ixp = pub / "ixps" / "index.json"
    series = {
        "ixp": ag.linhas_ixp(json.loads(idx_ixp.read_text(encoding="utf-8"))) if idx_ixp.exists() else [],
        "operadora": ag.linhas_operadora(ag.com_media_movel(ag.agregar_operadoras(br, _grupos(pub)),
                                                            _anteriores(base, date_str, "operadora.jsonl.gz", "cnpj"))),
        "uf": ag.linhas_uf(ag.com_media_movel(ag.agregar_ufs(br), _anteriores(base, date_str, "uf.jsonl.gz", "uf"))),
    }
    for nome, linhas in series.items():
        n_s, sha_s = gravar_jsonl_gz(destino / f"{nome}.jsonl.gz", linhas)
        entrada[f"{nome}_linhas"] = n_s
        entrada[f"{nome}_sha256"] = sha_s
    atualizar_indice(base, date_str, {**entrada, "built_at": None})     # os Snap leem o índice: a data nova já precisa constar nele
    entrada.update(gerar_eventos(base, date_str, log))
    entrada["built_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    atualizar_indice(base, date_str, entrada)
    log.info("history construído", date=date_str, asns=n, **{f"{k}": len(v) for k, v in series.items()})
    return entrada


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Histórico por snapshot")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        construir(data_dir(), a.date, log, a.force)
    except FileNotFoundError as exc:
        log.error("history falhou", erro=str(exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
