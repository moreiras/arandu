# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Registro das regras de alerta e cálculo dos alertas de um ASN.

A ORDEM de `REGRAS` é a ordem de emissão do fluxo antigo (`api/asn_health.py`): o desempate da ordenação final por (severidade, categoria)
depende dela, e a API, o MCP e o frontend mostram os alertas nessa ordem.
"""
from __future__ import annotations

from products.alerts.base import Contexto, Regra
from products.alerts.regras import (
    agregacao_elevada, anuncio_por_outro_as, as_loop_detectado, desagregacao, import_limit_proximo, membro_sem_peering, pdb_prefixos_divergente,
    politica_v4v6_divergente, prefixo_fora_alocacao, prefixo_inalcancavel, prefixos_filtraveis, prepend_excessivo,
    ptt_proximo_sem_participar, roa_maxlength_folgado, rpki_cobertura_parcial, rpki_invalido, sem_aspa, sem_ipv6, sem_irr_as_set,
    sem_peeringdb, sem_rpki, sessao_rs_down, single_homed,
)

MODULOS = (
    sem_ipv6, prefixo_inalcancavel, anuncio_por_outro_as, desagregacao, prefixo_fora_alocacao,
    sem_rpki, rpki_invalido, rpki_cobertura_parcial, roa_maxlength_folgado, sem_aspa,
    politica_v4v6_divergente,
    sem_peeringdb, sem_irr_as_set, membro_sem_peering, single_homed, pdb_prefixos_divergente,
    ptt_proximo_sem_participar,
    agregacao_elevada, prefixos_filtraveis, prepend_excessivo, as_loop_detectado,
    sessao_rs_down, import_limit_proximo,
)
REGRAS: tuple[Regra, ...] = tuple(m.REGRA for m in MODULOS)

_SEVERITY_RANK = {"critico": 0, "aviso": 1, "info": 2}


def regras_publicadas() -> dict[str, int]:
    """{id da regra: versão} das regras em vigor, em ordem alfabética (vai para o manifesto)."""
    return {r.id: r.versao for r in sorted(REGRAS, key=lambda r: r.id)}


def rules_version() -> str:
    """Identificador do CONJUNTO de regras em vigor: muda quando uma regra é acrescentada, removida ou muda de versão.

    Séries de alertas (contagens por categoria, por severidade, por id) só são comparáveis entre snapshots de mesmo `rules_version`;
    use `comparavel(a, b)` antes de calcular uma variação entre datas."""
    import hashlib

    corpo = "\n".join(f"{i}@{v}" for i, v in regras_publicadas().items())
    return "r" + hashlib.sha256(corpo.encode("utf-8")).hexdigest()[:8]


def comparavel(rules_version_a: str | None, rules_version_b: str | None) -> bool:
    """Duas séries de alertas são comparáveis se vêm da mesma versão do conjunto de regras (snapshot sem versão nunca é comparável)."""
    return bool(rules_version_a) and rules_version_a == rules_version_b


def calcular_alertas(store, date_str: str, asn: int, doc: dict) -> list[dict]:
    """Pontos de atenção do AS. Nunca levanta exceção: cada regra é isolada para não derrubar a página."""
    ctx = Contexto(store=store, date_str=date_str, asn=asn, doc=doc)
    alerts: list[dict] = []
    for m in MODULOS:
        regra = m.REGRA
        try:
            achados = m.avaliar(ctx)
        except Exception:
            continue
        for a in achados:
            alerts.append({
                "id": a["id"] or regra.id,
                "category": regra.categoria,
                "severity": regra.severidade,
                "title": a["title"],
                "detail": a["detail"],
                "refs": a["refs"],
                "desde_versao": regra.versao,        # versão da regra que gerou o alerta: compara-se só o que tem a mesma
            })
    alerts.sort(key=lambda a: (_SEVERITY_RANK.get(a["severity"], 9), a["category"]))
    return alerts
