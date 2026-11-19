# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Decodificação das communities do IX.br pelo dicionário do Alice-LG.

O dicionário é o `ixbr_communities.json.gz` de cada snapshot (a semântica pode mudar): `reject_reasons` (motivos de rejeição, em communities grandes `a:b:c`),
`noexport_reasons` (ações de não exportar e exportar somente), `rpki`, `bgp_communities` (informativas) e `bgp_blackhole_communities`. Uma folha do dicionário
é um texto; `*` casa qualquer valor do nível e `$N` no texto é o N-ésimo número da community (começa em 0: `65000:0:$2` é o terceiro).

A community é uma cadeia estável: `a:b` (padrão, RFC 1997), `a:b:c` (grande, RFC 8092) ou `ro:a:b`/`rt:a:b` (estendida, RFC 4360).

Classes devolvidas por `classificar` (campo `classe`):
  rejeicao, rpki, blackhole, nao_exportar_para, exportar_somente_para, nao_exportar_rir, exportar_somente_rir, nao_exportar_ptt, nao_exportar_rtt,
  nao_exportar_perda, informativa, outra.
`forma` diz como se chegou lá: `dicionario` (folha do dicionário), `equivalente_padrao` (a community padrão `65000:N` ou a estendida `rt:65000:N` lida como a grande
`65000:0:N` do dicionário: equivalência ASSUMIDA pela forma, que o Alice não declara) ou `nao_decodificada`.
"""
from __future__ import annotations

import re
from typing import Optional

ACOES = ("nao_exportar_para", "exportar_somente_para", "nao_exportar_rir", "exportar_somente_rir", "nao_exportar_ptt", "nao_exportar_rtt", "nao_exportar_perda")
_CLASSE_POR_PREFIXO_ACAO = {"65000": "nao_exportar_para", "65001": "exportar_somente_para", "65002": "nao_exportar_rir", "65003": "exportar_somente_rir",
                            "65004": "nao_exportar_ptt", "65010": "nao_exportar_rtt", "65011": "nao_exportar_perda"}
BLACKHOLE_PADRAO = ("65535:666",)
_ASN = re.compile(r"^\d{1,10}$")


def _folha(no, partes: list[str]) -> Optional[str]:
    """Texto da folha do dicionário para `partes` (exato antes de `*`), ou None se o caminho não termina numa folha de texto."""
    if isinstance(no, str):
        return no if not partes else None
    if not isinstance(no, dict) or not partes:
        return None
    for chave in (partes[0], "*"):
        if chave in no:
            r = _folha(no[chave], partes[1:])
            if r is not None:
                return r
    return None


def _rotulo(texto: str, partes: list[str]) -> str:
    return re.sub(r"\$(\d+)", lambda m: partes[int(m.group(1))] if int(m.group(1)) < len(partes) else m.group(0), texto)


def partes_da_community(c: str) -> tuple[str, list[str]]:
    """('padrao'|'grande'|'estendida', números) de `a:b`, `a:b:c` ou `ro:a:b`."""
    p = c.split(":")
    if p[0] in ("ro", "rt") and len(p) == 3:
        return "estendida", p
    return ("padrao" if len(p) == 2 else "grande"), p


def chaves_da_rota(bgp: dict) -> list[str]:
    """Communities de uma rota do Alice (`bgp.communities`, `large_communities`, `ext_communities`) como cadeias estáveis."""
    out = [":".join(str(x) for x in c) for c in (bgp.get("communities") or [])]
    out += [":".join(str(x) for x in c) for c in (bgp.get("large_communities") or [])]
    out += [":".join(str(x) for x in c) for c in (bgp.get("ext_communities") or [])]
    return out


class Dicionario:
    """Classificador de communities a partir do dicionário de um snapshot."""

    def __init__(self, doc: Optional[dict]):
        doc = doc or {}
        self.reject = doc.get("reject_reasons") or {}
        self.noexport = doc.get("noexport_reasons") or {}
        self.informativas = doc.get("bgp_communities") or {}
        rp = doc.get("rpki") or {}
        self.rpki = {":".join(map(str, c)): k for k in ("valid", "unknown", "not_checked", "invalid") for c in (rp.get(k) or [])}
        bh = doc.get("bgp_blackhole_communities") or {}
        self.blackhole = {":".join(str(x[0]) if x[0] == x[1] else f"{x[0]}-{x[1]}" for x in c) for c in (bh.get("standard") or [])} | set(BLACKHOLE_PADRAO)
        self.vazio = not (self.reject or self.noexport or self.informativas)

    def motivo_de_rejeicao(self, community: str) -> Optional[str]:
        """Rótulo do motivo de rejeição (community grande), ou None."""
        tipo, p = partes_da_community(community)
        return _rotulo(r, p) if tipo == "grande" and (r := _folha(self.reject, p)) else None

    def e_blackhole(self, community: str) -> bool:
        tipo, p = partes_da_community(community)
        if community in self.blackhole:
            return True
        return tipo == "grande" and p[1:] == ["616", "666"] and p[0] in ("65535", "26162")

    def classificar(self, community: str) -> dict:
        """`{community, classe, rotulo, forma, alvo?}`; `alvo` é o número do AS, do RIR ou do PTT que a ação cita."""
        tipo, p = partes_da_community(community)
        base = {"community": community}
        if self.e_blackhole(community):
            r = self.motivo_de_rejeicao(community)
            return {**base, "classe": "blackhole", "rotulo": r or "Blackhole", "forma": "dicionario" if r else "equivalente_padrao"}
        if tipo == "grande":
            if (r := self.motivo_de_rejeicao(community)):
                return {**base, "classe": "rejeicao", "rotulo": r, "forma": "dicionario"}
            if community in self.rpki:
                return {**base, "classe": "rpki", "rotulo": {"valid": "RPKI válido", "unknown": "RPKI desconhecido (not found)", "not_checked": "RPKI não verificado",
                                                             "invalid": "RPKI inválido"}[self.rpki[community]], "forma": "dicionario", "estado_rpki": self.rpki[community]}
            acao = self._acao(p, "dicionario")
            if acao:
                return {**base, **acao}
        elif tipo == "padrao" and p[0] in _CLASSE_POR_PREFIXO_ACAO and p[0] in ("65000", "65001") and _ASN.match(p[1]):
            acao = self._acao([p[0], "0", p[1]], "equivalente_padrao")
            if acao:
                return {**base, **acao}
        elif tipo == "estendida" and p[0] == "rt" and p[1] in ("65000", "65001") and _ASN.match(p[2]):
            acao = self._acao([p[1], "0", p[2]], "equivalente_padrao")
            if acao:
                return {**base, **acao}
        r = _folha(self.informativas, p if tipo != "estendida" else [])
        if r:
            return {**base, "classe": "informativa", "rotulo": _rotulo(r, p), "forma": "dicionario"}
        return {**base, "classe": "outra", "rotulo": None, "forma": "nao_decodificada"}

    def _acao(self, p: list[str], forma: str) -> Optional[dict]:
        classe = _CLASSE_POR_PREFIXO_ACAO.get(p[0])
        if not classe:
            return None
        r = _folha(self.noexport, p)
        if not r:
            return None
        return {"classe": classe, "rotulo": _rotulo(r, p), "forma": forma, "alvo": int(p[2]) if _ASN.match(p[2]) else None}
