# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Saúde do ASN no documento publicado: alertas, ROAs, validação RPKI e ASPA, como fragmento `saude`.

`criar_store` entrega o `Store` da API sobre o snapshot (injetado por quem orquestra: esta camada não importa `api`)."""
from __future__ import annotations

import json
from pathlib import Path

from core import compose
from core.common import published_path
from products.asn_saude.enrich import enrich_asn_document


def publicar_asn_saude(base: Path, date_str: str, log, criar_store, force: bool = False) -> int:
    """Pré-computa alerts + RPKI (rpki_validation/roa_list) + path_node_meta para
    todos os ASNs e grava de volta em cada asns/{asn}.json, para a API só ler e servir.

    Reusa exatamente a função do request-path (products.asn_saude.enrich.enrich_asn_document),
    garantindo saída idêntica à que a rota produziria. Roda no fim do publish, com a
    Store apontando para o snapshot já montado (full table, RPKI, geo já disponíveis).

    `enrich_asn_document` é idempotente: se o doc já tem `alerts`, não faz nada. Com
    `force=True`, removemos `alerts`/`roa_list`/`rpki_validation` antes de chamar —
    necessário para reaplicar uma correção de lógica de enriquecimento a um snapshot
    já publicado (backfill normal não precisa disso, só roda uma vez por snapshot).

    Retorna o número de arquivos ASN enriquecidos.
    """

    pub_dir = published_path(base, date_str, "asns")
    # ARANDU_COMPOSE=on: lê os fragmentos (base, ixp_paths, sici), grava o pedaço `saude` e o compose monta TODOS os documentos, uma só vez.
    por_fragmento = compose.fluxo_novo(base, date_str)
    if not por_fragmento and not pub_dir.exists():
        log.warning("asns dir missing, skipping asn health build")
        return 0

    if por_fragmento:
        existente = compose.caminho(base, date_str, "saude")
        if existente.exists() and not force:
            log.info("asn health fragment already present, skipping", path=str(existente))
            if not any(pub_dir.glob("[0-9]*.json")):       # fragmento feito, mas o compose não chegou a rodar
                compose.recompor(base, date_str, log)
            return 0
        existente.unlink(missing_ok=True)                   # force: recalcula a saúde a partir dos pedaços sem ela

    store = criar_store(base)
    if por_fragmento:
        documentos = compose.iterar_documentos(base, date_str, ("base", "ixp_paths", "sici", "relacoes"))
        total = None
    else:
        paths = sorted(
            (p for p in pub_dir.glob("*.json") if p.stem.isdigit()),
            key=lambda p: int(p.stem),
        )
        total = len(paths)
        documentos = ((None, p) for p in paths)
    log.info("building asn health (alerts + rpki)", total=total, force=force)

    def _docs():
        if por_fragmento:
            for _a, d in documentos:
                yield None, d
            return
        for _n, p in documentos:
            try:
                yield p, json.loads(p.read_bytes())
            except Exception:
                continue

    enriched = 0
    frag_ctx = compose.gravar_fragmento(base, date_str, "saude") if por_fragmento else None
    fragmento = frag_ctx.__enter__() if frag_ctx else None
    try:
        for i, (path, doc) in enumerate(_docs(), 1):
            if i % 2000 == 0:
                log.info("asn health progress", done=i, total=total)
            asn = doc.get("asn")
            if asn is None:
                continue
            if not doc.get("is_br"):
                continue
            if force:
                for key in ("alerts", "roa_list", "rpki_validation", "aspa_providers", "aspa_customers"):
                    doc.pop(key, None)
            try:
                full = enrich_asn_document(store, date_str, int(asn), doc)
            except Exception as exc:
                log.warning("asn health enrich failed", asn=asn, error=str(exc))
                continue
            # Só reescreve quando a augmentação adicionou algo (evita I/O à toa).
            if full is not doc and ("alerts" in full or "rpki_validation" in full
                                    or "aspa_providers" in full or "aspa_customers" in full):
                if fragmento is not None:
                    fragmento.escrever(int(asn), {k: v for k, v in full.items() if k not in doc or doc[k] != v})
                else:
                    path.write_text(json.dumps(full, ensure_ascii=False), encoding="utf-8")
                enriched += 1
    except BaseException:
        if frag_ctx is not None:
            frag_ctx.__exit__(*__import__("sys").exc_info())        # fragmento incompleto não fica
            compose.recompor(base, date_str, log)               # a falha da saúde (etapa opcional) não pode deixar o snapshot sem documentos
        raise
    if frag_ctx is not None:
        frag_ctx.__exit__(None, None, None)
        compose.recompor(base, date_str, log)                   # a única escrita dos documentos de ASN
    log.info("asn health enrichment done", enriched=enriched)
    return enriched
