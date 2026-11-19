# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Universo de CNPJs de telecom (8 dígitos): outorgas, SICI e o recorte da Receita. Usado pelas fontes que só guardam o que é de operadora."""
from __future__ import annotations

from pathlib import Path

from core.common import normalized_path, read_json_gz

OUTORGAS = ("anatel_scm.json.gz", "anatel_smp.json.gz", "anatel_stfc.json.gz", "anatel_seac.json.gz")


def basicos(base: Path, date_str: str, log=None, com_receita: bool = True) -> set[str]:
    """CNPJs básicos das outorgas, do SICI e, se já coletado, dos estabelecimentos de telecom da Receita (CNAE 61, principal ou secundário: ~585 mil raízes em 2026-11-06).

    `com_receita=False` devolve só outorgas e SICI (~20,9 mil raízes), o universo de quem consulta um serviço por CNPJ (SIASG)."""
    out: set[str] = set()
    for nome in OUTORGAS:
        p = normalized_path(base, date_str, "summary", nome)
        if p.exists():
            out.update(c[:8] for c in ((read_json_gz(p) or {}).get("by_cnpj") or {}) if len(c) == 14)
        elif log:
            log.info("fonte de outorga ausente", fonte=nome)
    p = normalized_path(base, date_str, "summary", "sici_acessos.json.gz")
    if p.exists():
        cn = (read_json_gz(p) or {}).get("cnpjs") or {}
        out.update(c[:8] for c in (cn.keys() if isinstance(cn, dict) else cn) if isinstance(c, str) and len(c) == 14)
    p = normalized_path(base, date_str, "summary", "receita_cnpj.json.gz")
    if com_receita and p.exists():
        out.update((read_json_gz(p) or {}).get("estabelecimentos", {}).keys())
    return out


def cnae_principal_ativa(base: Path, date_str: str) -> set[str]:
    """Raízes com algum estabelecimento ATIVO cuja atividade PRINCIPAL é CNAE 61 (telecomunicações). ~61 mil em 2026-11-06 (com CNAE 61 em qualquer posição seriam ~585 mil)."""
    p = normalized_path(base, date_str, "summary", "receita_cnpj.json.gz")
    if not p.exists():
        return set()
    out: set[str] = set()
    for raiz, estabs in ((read_json_gz(p) or {}).get("estabelecimentos") or {}).items():
        for e in (estabs if isinstance(estabs, list) else [estabs]):
            if isinstance(e, dict) and str(e.get("p", "")).startswith("61") and str(e.get("s", "")) == "02":
                out.add(raiz)
                break
    return out
