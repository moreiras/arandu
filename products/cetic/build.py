# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Publica as tabelas oficiais das pesquisas TIC do Cetic.br em `published/{date}/cetic/`.

Cópia do normalizado (`cetic_tic_domicilios.json.gz`, `cetic_tic_provedores.json.gz`) sem alterar nenhum número: o valor é do Cetic.br e a margem de erro
vem junto. O que o Arandurapé calcula (estimativas por UF a partir dos microdados, demanda × oferta) fica em outros produtos e é rotulado como derivado.
Sem o normalizado de uma pesquisa, o artefato dela não é gerado (a fonte é anual e opcional).

`domicilios_uf.json.gz` traz as estimativas por UF calculadas dos microdados da TIC Domicílios (`natureza: estimativa_arandurape`), com a
`validacao` contra as tabelas oficiais da mesma edição (proporção do Brasil e das regiões; razão das margens de erro).
"""
from __future__ import annotations

from pathlib import Path

from core.cetic_microdados import validar
from core.common import normalized_path, now_iso, published_path
from core.jsonio import carregar_json_gz, gravar_json_gz

PESQUISAS = {"domicilios": "cetic_tic_domicilios", "provedores": "cetic_tic_provedores"}


def publicar_cetic(base: Path, date_str: str, log) -> dict:
    destino = published_path(base, date_str) / "cetic"
    gerados = {}
    for chave, arquivo in PESQUISAS.items():
        doc = carregar_json_gz(normalized_path(base, date_str, "summary") / f"{arquivo}.json.gz")
        if not doc:
            log.info("cetic: normalizado ausente", pesquisa=chave)
            continue
        destino.mkdir(parents=True, exist_ok=True)
        gravar_json_gz(destino / f"{chave}.json.gz", {**doc, "snapshot_date": date_str, "generated_at": now_iso(), "coletado_em": doc.get("generated_at")})
        gerados[chave] = {"edicao": doc.get("edicao"), "tabelas": doc.get("total_tabelas"), "linhas": doc.get("total_linhas")}
    uf = carregar_json_gz(normalized_path(base, date_str, "summary") / "cetic_tic_domicilios_uf.json.gz")
    if uf:
        oficial = carregar_json_gz(normalized_path(base, date_str, "summary") / "cetic_tic_domicilios.json.gz")
        destino.mkdir(parents=True, exist_ok=True)
        gravar_json_gz(destino / "domicilios_uf.json.gz", {**uf, "snapshot_date": date_str, "generated_at": now_iso(), "coletado_em": uf.get("generated_at"),
                                                           "validacao": validar(uf["grupos"], oficial) if oficial and oficial.get("edicao") == uf.get("edicao") else None})
        gerados["domicilios_uf"] = {"edicao": uf.get("edicao"), "grupos": len(uf["grupos"])}
    log.info("cetic published", **{k: v["edicao"] for k, v in gerados.items()})
    return gerados
