# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Manifesto do snapshot — a ÚLTIMA etapa do build.

Monta `manifest.json` (metadados do pipeline, `checks` de coleta, `sources[]`, `rules_version`) e os checksums de TODOS os arquivos publicados,
depois que tudo foi publicado (índices, mapas, mercado, BGP, estabilidade, saúde do ASN já composta). Como a API só lista datas com
`manifest.json` (`Store.dates`), o snapshot **só aparece quando termina**: publicação atômica, em vez de aparecer incompleto por horas.

    python -m publish.manifesto --date 2026-10-24

O caminho legado (`snapshot_builder.run`) chama `fechar` no fim do `snapshot_completo`; o `saude_asn` o refaz com os checksums finais.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.common import configure_logging, data_dir, normalized_path, published_path, today_str
from core.jsonio import carregar_json, carregar_json_gz
from products.snapshot.build import montar_manifesto
from publish import coleta_checks


def fechar(base: Path, date_str: str, log, all_ixps: list[dict]) -> dict:
    """Escreve o manifesto e fecha os checks, `sources[]`, `rules_version`, o detalhe do snapshot e os checksums de tudo."""
    pub = published_path(base, date_str)
    summary = carregar_json(pub / "summary.json") or {}
    ixp_index = carregar_json(pub / "ixps" / "index.json") or []
    geo_meta = carregar_json_gz(normalized_path(base, date_str, "summary") / "geo_prefixes.json.gz")
    geolite2 = geo_meta.get("mmdb_month") if geo_meta else None
    log.info("writing manifest")
    manifesto = montar_manifesto(date_str, all_ixps, ixp_index, summary, {}, geolite2_version=geolite2)
    (pub / "manifest.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    coleta_checks.refresh_manifest(base, date_str, log)                    # checks de coleta, sources[] e rules
    # Detalhe de `GET /snapshots/{date}`: calculado uma vez, aqui, e FORA dos checksums (carrega uma cópia do manifesto)
    try:
        from api import snapshot_detail

        snapshot_detail.build_sidecar(base, date_str, log)
    except Exception as exc:  # noqa: BLE001 — a API recalcula se o arquivo faltar
        log.warning("snapshot detail failed", error=str(exc))
    final = coleta_checks.refresh_manifest(base, date_str, log, checksums=True)     # checksums de tudo + metadados do detalhe
    log.info("manifest closed", files_checksummed=len((final or {}).get("checksums", {})))
    return final or manifesto


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Fecha o snapshot: manifesto, checks e checksums")
    p.add_argument("--date", default=today_str())
    a = p.parse_args(argv)
    from products import passos

    log = configure_logging()
    try:
        fechar(data_dir(), a.date, log, passos._ixps_atual())
    except Exception:
        log.exception("falha ao fechar o manifesto")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
