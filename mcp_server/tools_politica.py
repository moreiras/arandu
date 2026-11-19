# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tools de política de roteamento nos route servers do IX.br do MCP: `asn_politica`, `ixp_rejeicoes` e `ixp_communities`.

Mesma fonte das rotas `/asns/{asn}/politica`, `/ixps/{code}/rejeicoes` e `/communities` (`api.services.rs_policy` sobre `rs_policy/*.json.gz`). É a declaração do membro por communities
e a decisão do route server, vistas pelo Alice-LG; não é tráfego nem relação comercial. O perfil é inferido e só existe para quem teve as rotas recebidas coletadas.
"""
from __future__ import annotations

from typing import Optional

from api.services import rs_policy as pol
from mcp_server.contexto import _resolve, _store, mcp


@mcp.tool()
def asn_politica(asn: int, ixp: Optional[str] = None, date: Optional[str] = None) -> dict:
    """Política de roteamento de um ASN nos route servers do IX.br: rotas rejeitadas e communities de exportação, por PTT coletado.

    Por PTT: `rejeicoes` (rotas rejeitadas por motivo decodificado: RPKI inválido, bogon, inválido no Registro.br…, com até 5 prefixos de amostra) e `politica` (perfil aberto, seletivo ou
    restritivo INFERIDO por heurística, com o critério; ações como "não exportar para AS" e "exportar somente para AS" com a fração das rotas; blackhole; RPKI das rotas recebidas).
    `evidencia_rs` soma as rejeições por tipo. Só tem dado quem foi coletado (rodízio dentro de um orçamento de requisições): sem coleta não há perfil, e isso não prova que o ASN é aberto.
    É declaração do membro e decisão do route server naquele instante, não tráfego nem relação comercial.

    Args:
        asn: Número do AS.
        ixp: Código do PTT (minúsculo) para restringir a um PTT.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    b = pol.bloco_asn(_store.rs_policy_asns_doc(d), int(asn), ixp.lower() if ixp else None)
    if b is None:
        raise ValueError(f"AS{asn} sem rejeição nem política coletadas nos route servers do IX.br no snapshot {d} (não foi coletado, ou não há dado).")
    return b


@mcp.tool()
def ixp_rejeicoes(code: str, limit: int = 25, motivo: Optional[str] = None, date: Optional[str] = None) -> dict:
    """Rotas rejeitadas pelo route server em um PTT do IX.br, por motivo e por ASN, e o resumo da política dos membros coletados.

    `rejeicoes.por_motivo` traz o motivo (código da community grande e rótulo do dicionário do Alice), as rotas e os ASNs; `rejeicoes.asns` os ASNs com mais rotas rejeitadas. `politica` resume
    perfis inferidos, ações usadas, blackhole e RPKI das rotas recebidas. A `cobertura` diz quantos vizinhos foram coletados: a medida é só de quem foi coletado, não do PTT inteiro.

    Args:
        code: Código do PTT (minúsculo; ex.: "sp", "rj", "df").
        limit: Quantos ASNs listar (1..200).
        motivo: Mantém só os ASNs com esse motivo (ex.: "26162:300:0" = RPKI inválido).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    b = pol.bloco_ixp(_store.rs_policy_ixps_doc(d), code.lower(), max(1, min(limit, 200)), 0, motivo)
    if b is None:
        raise ValueError(f"Rejeições e política do PTT '{code}' não publicadas no snapshot {d}.")
    return b


@mcp.tool()
def ixp_communities(community: Optional[str] = None, q: Optional[str] = None, ixp: Optional[str] = None, classe: Optional[str] = None, limit: int = 25, date: Optional[str] = None) -> dict:
    """Communities dos route servers do IX.br: o que significam e quem as usa (só das rotas recebidas coletadas).

    Com `community` exata (ex.: "65000:0:13335", "26162:300:1", "65535:666"): classe, rótulo do dicionário e, por PTT, ASNs que a usam, rotas e os 10 que mais usam. Sem ela, lista as que casam
    `q` (trecho da community ou do rótulo; número = ASN-alvo de "não exportar para"/"exportar somente para"), filtrando por `ixp` e `classe` (nao_exportar_para, exportar_somente_para,
    nao_exportar_rir, nao_exportar_ptt, blackhole, rpki, informativa, outra…). `forma: equivalente_padrao` = community padrão ou estendida lida como a grande equivalente (assumido pela forma).
    Ausência na lista não prova que ninguém a usa: só há dado de quem foi coletado.

    Args:
        community: Community exata (a:b, a:b:c ou ro|rt:a:b).
        q: Busca por trecho/rótulo/ASN-alvo (quando `community` é omitida).
        ixp: Código do PTT (minúsculo).
        classe: Classe da community.
        limit: Quantas listar (1..200).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    doc = _store.rs_policy_communities_doc(d)
    if doc is None:
        raise ValueError(f"Communities dos route servers não publicadas no snapshot {d}.")
    if community:
        r = pol.uso_da_community(doc, community.strip(), ixp.lower() if ixp else None)
        if r is None:
            raise ValueError(f"Community '{community}' não aparece nas rotas coletadas no snapshot {d}.")
        return r
    return pol.communities(doc, q, ixp.lower() if ixp else None, classe, max(1, min(limit, 200)), 0)
