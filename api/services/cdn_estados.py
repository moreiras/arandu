# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Três estados por célula da matriz de CDNs (PT-24 / CDNS-E5.1): membro com sessão no route server, membro sem sessão e prefixos vistos por outro participante.

`cdns.json` só diz se um ASN da CDN consta no cadastro de participantes do PTT (`ixbr`). A página chamava isso de "presença" e o bloco do PTT de "peering direto observado", o que
mistura cadastro e sessão. Aqui o estado de cada CDN em cada PTT do IX.br é separado, na leitura, com dado já publicado (documento do PTT e documento de cada ASN da CDN), de modo que
vale também para snapshots antigos:

  * `ixbr_rs`: PTTs onde um ASN da CDN é membro **e** tem sessão com o route server (`asn_direct` do looking glass);
  * `ixbr_sem_rs`: PTTs onde é membro e não tem sessão com o route server observada. A troca pode ocorrer por sessão bilateral, que o route server não vê: nada aqui diz que não há tráfego;
  * `ixbr_origem`: PTTs onde não é membro, mas prefixos de um ASN da CDN aparecem nas rotas (`ixps_origin` do documento do ASN). INFERIDO: mostra que o conteúdo é alcançável pelo PTT,
    não onde está o servidor nem quanto tráfego passa;
  * `asns_sem_documento`: ASNs da lista curada sem documento no snapshot; ficam fora da conta (nunca contam como "sem sessão").

PTT sem coleta válida em nenhuma família não afirma ausência de sessão: o PTT sai de `ixbr_sem_rs` e vai para `ixbr_sem_coleta`.
"""
from __future__ import annotations

from typing import Callable, Optional

ESTADOS = {
    "ixbr_rs": "membro com sessão no route server",
    "ixbr_sem_rs": "membro, sem sessão no route server observada (pode haver peering bilateral)",
    "ixbr_origem": "não membro; prefixos da CDN vistos no PTT por outro participante (inferido)",
}
LIMITES = ("Membro é o ASN listado como participante do PTT pelo IX.br. Sessão no route server é observada no looking glass do IX.br; muitas redes grandes trocam tráfego por sessões bilaterais, "
           "que não aparecem aqui, então a ausência dessa sessão não indica ausência de troca de tráfego. Prefixos vistos por outro participante mostram que o conteúdo é alcançável pelo PTT, "
           "sem dizer onde está o servidor nem quanto tráfego passa. A lista de CDNs é uma curadoria e é incompleta.")


def estados(cdns: list[dict], direto_por_ptt: dict[str, set[int]], coleta_ok: dict[str, bool], origem_de: Callable[[int], Optional[set[str]]]) -> dict[str, dict]:
    """`{nome da CDN: {ixbr_rs, ixbr_sem_rs, ixbr_sem_coleta, ixbr_origem, asns_sem_documento, sem_rs_em_nenhum_ptt}}`.
    `direto_por_ptt` é o `asn_direct` (v6 ∪ v4) de cada PTT, `coleta_ok` diz se o PTT teve alguma família com coleta válida e `origem_de(asn)` devolve os PTTs onde o ASN origina
    prefixos (`None` = ASN sem documento no snapshot)."""
    out: dict[str, dict] = {}
    for c in cdns:
        membros = set(c.get("ixbr") or [])
        asns = [int(a) for a in c.get("asns") or []]
        rs = {code for code in membros if any(a in direto_por_ptt.get(code, ()) for a in asns)}
        sem_coleta = sorted(code for code in membros - rs if not coleta_ok.get(code))
        origem: set[str] = set()
        faltando: list[int] = []
        for a in asns:
            o = origem_de(a)
            if o is None:
                faltando.append(a)
            else:
                origem |= set(o)
        out[c["name"]] = {
            "ixbr_rs": sorted(rs),
            "ixbr_sem_rs": sorted(membros - rs - set(sem_coleta)),
            "ixbr_sem_coleta": sem_coleta,
            "ixbr_origem": sorted(origem - membros),
            "asns_sem_documento": faltando,
            "sem_rs_em_nenhum_ptt": bool(membros) and not rs and not sem_coleta,
        }
    return out
