# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Recomputação dos alertas de um snapshot já publicado com as regras ATUAIS, sem tocar no publicado.

O publicado é imutável: o resultado vai para `alerts/<rules_version>/<data>/` — `alertas.jsonl.gz` (uma linha por ASN BR com os alertas)
e `meta.json` (regras, contagens por severidade/categoria/id e o hash do conteúdo). O histórico compara essas séries; só é válido
comparar datas de mesmo `rules_version` (`registro.comparavel`). Reproduzível: o mesmo snapshot e as mesmas regras dão o mesmo
`conteudo_sha256` (o `.jsonl.gz` é determinístico).

Os dados auxiliares (full table, RPKI, análise BGP, índices) vêm do próprio snapshot; a única entrada fora dele é a configuração de PTTs
(`config/pix.yaml`), usada pela regra `ptt_proximo_sem_participar`.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from products.alerts.registro import calcular_alertas, regras_publicadas, rules_version


def diretorio(base: Path, date_str: str, versao: str | None = None) -> Path:
    return base / "alerts" / (versao or rules_version()) / date_str


def recomputar(base: Path, date_str: str, log, criar_store: Callable) -> dict:
    """Recalcula os alertas de `date_str` com as regras em vigor; devolve o `meta.json` gravado."""
    pub = base / "published" / date_str / "asns"
    if not pub.is_dir():
        raise FileNotFoundError(f"snapshot sem documentos de ASN: {pub}")
    store = criar_store(base)
    destino = diretorio(base, date_str)
    destino.mkdir(parents=True, exist_ok=True)
    alvo = destino / "alertas.jsonl.gz"
    tmp = alvo.with_name(alvo.name + ".tmp")
    por_sev: Counter = Counter()
    por_cat: Counter = Counter()
    por_id: Counter = Counter()
    n_asns = n_alertas = 0
    sha = hashlib.sha256()
    arquivos = sorted((p for p in pub.glob("*.json") if p.stem.isdigit()), key=lambda p: int(p.stem))
    with tmp.open("wb") as bruto, gzip.GzipFile(filename="", mode="wb", fileobj=bruto, compresslevel=6, mtime=0) as gz:
        for i, p in enumerate(arquivos, 1):
            if i % 5000 == 0:
                log.info("alerts recompute progress", done=i, total=len(arquivos))
            doc = json.loads(p.read_text(encoding="utf-8"))
            if not doc.get("is_br"):
                continue                                   # a saúde (e os alertas) só existe para ASes BR, como no publicado
            doc.pop("alerts", None)
            alertas = calcular_alertas(store, date_str, int(doc["asn"]), doc)
            linha = (json.dumps({"asn": int(doc["asn"]), "alerts": alertas}, ensure_ascii=False) + "\n").encode("utf-8")
            gz.write(linha)
            sha.update(linha)
            n_asns += 1
            n_alertas += len(alertas)
            for a in alertas:
                por_sev[a["severity"]] += 1
                por_cat[a["category"]] += 1
                por_id[a["id"]] += 1
    tmp.replace(alvo)
    manifesto = {}
    try:
        manifesto = json.loads((base / "published" / date_str / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    meta = {
        "data": date_str,
        "rules_version": rules_version(),
        "rules": regras_publicadas(),
        "rules_version_do_snapshot": manifesto.get("rules_version"),       # None = manifesto sem rules_version
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "asns": n_asns,
        "alertas": n_alertas,
        "por_severidade": dict(sorted(por_sev.items())),
        "por_categoria": dict(sorted(por_cat.items())),
        "por_id": dict(sorted(por_id.items())),
        "conteudo_sha256": sha.hexdigest(),
    }
    (destino / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info("alerts recomputed", date=date_str, rules_version=meta["rules_version"], asns=n_asns, alertas=n_alertas)
    return meta


def ler_alertas(base: Path, date_str: str, versao: str | None = None):
    """(asn, alertas) do recomputo de `date_str` para a versão de regras (padrão: a atual)."""
    with gzip.open(diretorio(base, date_str, versao) / "alertas.jsonl.gz", "rt", encoding="utf-8") as f:
        for linha in f:
            r = json.loads(linha)
            yield r["asn"], r["alerts"]
