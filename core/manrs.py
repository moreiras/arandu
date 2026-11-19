# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tabela pública de participantes do MANRS (programa de operadores de rede).

Lê o HTML de https://manrs.org/netops/participants/ (`<table id="participant-table">`). O mesmo conteúdo sai no botão "CSV" da página, que é gerado no navegador a partir da tabela.
Os termos (manrs.org/terms-of-service/) só permitem divulgar dados de outras redes de forma agregada e sem identificá-las: por isso o resultado daqui é insumo interno e nunca é publicado.
"""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Optional

_TABELA = re.compile(r'<table id="participant-table".*?</table>', re.S)
_LINHA = re.compile(r"<tr>(.*?)</tr>", re.S)
_ASN = re.compile(r"\d+")


def _celula(linha: str, classe: str) -> Optional[str]:
    m = re.search(r'<td class="%s"([^>]*)>(.*?)</td>' % classe, linha, re.S)
    return m.group(2) if m else None


def _texto(h: Optional[str]) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h or ""))).strip()


def _acao(h: Optional[str]) -> dict:
    """Uma célula de ação: `marca` (a tabela mostra o visto de ação atendida), `pct` (pontuação medida pelo Observatório) ou nenhum dos dois (sem dado)."""
    t = _texto(h)
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", t)
    if m:
        return {"marca": None, "pct": float(m.group(1).replace(",", "."))}
    oculto = re.search(r'<span class="hidden">\s*([01])\s*</span>', h or "")
    return {"marca": (oculto.group(1) == "1") if oculto else None, "pct": None}


def _roteamento(h: Optional[str]) -> dict:
    out = {}
    for nome in ("irr", "rpki"):
        m = re.search(r'<span class="%s[^"]*">(.*?)</span>' % nome, h or "", re.S)
        p = re.search(r"(\d+(?:[.,]\d+)?)\s*%", _texto(m.group(1))) if m else None
        out[nome] = float(p.group(1).replace(",", ".")) if p else None
    out["marca"] = _acao(h)["marca"]
    return out


def medido_em(pagina: str) -> Optional[str]:
    """`Data last measured:` da legenda da tabela, como AAAA-MM-DD."""
    m = re.search(r"<caption>\s*Data last measured:\s*(.*?)</caption>", pagina, re.S)
    if not m:
        return None
    t = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", _texto(m.group(1)))
    try:
        return datetime.strptime(t, "%d %B %Y").date().isoformat()
    except ValueError:
        return None


def participantes(pagina: str) -> list[dict]:
    """Uma entrada por organização: `org`, `aprovado` (AAAA-MM-DD), `areas` (países), `asns` e as ações (1 filtragem, 2 anti-spoofing, 3 coordenação, 4 roteamento IRR/RPKI)."""
    m = _TABELA.search(pagina)
    if not m:
        raise ValueError("tabela de participantes ausente: o HTML do MANRS mudou?")
    out = []
    for linha in _LINHA.findall(m.group(0)):
        if '<td class="org-name"' not in linha:
            continue
        data = re.search(r'data-sort="(\d+)"', linha)
        out.append({
            "org": _texto(_celula(linha, "org-name")),
            "aprovado": datetime.fromtimestamp(int(data.group(1)), timezone.utc).date().isoformat() if data else None,
            "areas": [a.strip() for a in _texto(_celula(linha, "areas")).split(",") if a.strip()],
            "asns": sorted({int(a) for a in _ASN.findall(_texto(_celula(linha, "asns")))}),
            "acoes": {"filtragem": _acao(_celula(linha, "action-1")), "anti_spoofing": _acao(_celula(linha, "action-2")), "coordenacao": _acao(_celula(linha, "action-3")),
                      "roteamento": _roteamento(_celula(linha, "action-4"))},
        })
    return out
