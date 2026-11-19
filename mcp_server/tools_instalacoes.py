# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tools de instalações do PeeringDB do MCP: `facility_lista`, `facility_detalhe`, `asn_peering` e `ixp_portas`.

Mesma fonte das rotas `/facilities`, `/asns/{asn}/peering` e `/ixps/{code}/portas` (`api.services.instalacoes` sobre `instalacoes/*.json.gz`). Cadastro AUTODECLARADO no PeeringDB; o campo
`cadastro` é inferência pelas datas de atualização e não diz nada da operação. Contatos do PeeringDB não são coletados nem servidos.
"""
from __future__ import annotations

from typing import Optional

from api.services import instalacoes as inst
from mcp_server.contexto import _resolve, _store, mcp


@mcp.tool()
def facility_lista(
    uf: Optional[str] = None, q: Optional[str] = None, ptt: Optional[str] = None, asn: Optional[int] = None, cadastro: Optional[str] = None,
    pais: Optional[str] = None, ordem: str = "redes", limit: int = 25, date: Optional[str] = None,
) -> dict:
    """Instalações (datacenters, pontos de interconexão) cadastradas no PeeringDB: do Brasil por padrão, filtráveis por UF, nome, PTT, rede e estado do cadastro.

    Cada item traz cidade, UF, coordenadas, organização, redes vinculadas, PTTs, carriers e `cadastro` (recente, parado ou antigo: INFERÊNCIA pela data da última atualização do registro;
    mede a manutenção do cadastro, não a operação da instalação nem da empresa). É cadastro autodeclarado: pode faltar, sobrar ou estar desatualizado. Com `asn`, lista as instalações do Brasil em que
    a rede declara estar (com a data do vínculo). Para o detalhe de uma instalação (redes, carriers, campus) use `facility_detalhe`; para filtros e agregações livres, `query(collection="facilities")`.

    Args:
        uf: Sigla da UF (ex.: "SP").
        q: Trecho do nome, da organização ou da cidade.
        ptt: Código do PTT (minúsculo; IX.br ou externo cadastrado) para listar só as instalações dele.
        asn: Número do AS: lista as instalações do Brasil em que a rede declara estar (ignora os demais filtros).
        cadastro: recente | parado | antigo.
        pais: ISO do país (padrão BR); "todos" inclui as instalações de PTTs externos.
        ordem: redes | ptts | nome | atualizado.
        limit: Quantas listar (1..200).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    doc = _store.instalacoes_doc(d)
    if not doc:
        raise ValueError(f"Instalações do PeeringDB não publicadas no snapshot {d}.")
    if asn is not None:
        b = inst.bloco_asn(doc, _store.vinculos_instalacoes_doc(d), int(asn))
        if b is None:
            raise ValueError(f"AS{asn} sem instalação do Brasil vinculada no PeeringDB no snapshot {d}.")
        return {**b, "items": b["items"][:max(1, min(limit, 200))]}
    try:
        return inst.lista(doc, pais, uf, q, ptt, cadastro, False, False, ordem, max(1, min(limit, 200)), 0)
    except inst.InstalacoesErro as e:
        raise ValueError(e.mensagem)


@mcp.tool()
def facility_detalhe(id: int, date: Optional[str] = None) -> dict:
    """Uma instalação do PeeringDB: organização, localização, datas, PTTs, carriers, campus e as redes vinculadas (só nas do Brasil).

    `ixps` traz o código do Arandurapé quando o PTT é conhecido. `redes` lista ASN, nome e a data do vínculo: é declaração no cadastro, não indica tráfego nem contrato. `cadastro` é
    inferência pelas datas de atualização (mede a manutenção do registro, não a operação). Autodeclarado.

    Args:
        id: Identificador da instalação no PeeringDB (campo `id` de `facility_lista`).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    doc = _store.instalacoes_doc(d)
    if not doc:
        raise ValueError(f"Instalações do PeeringDB não publicadas no snapshot {d}.")
    r = inst.detalhe(doc, _store.vinculos_instalacoes_doc(d), int(id))
    if r is None:
        raise ValueError(f"Instalação {id} não encontrada no snapshot {d}.")
    return r


@mcp.tool()
def asn_peering(asn: int, date: Optional[str] = None) -> dict:
    """Atributos de peering que a rede declara no PeeringDB: escopo, IPv6, multicast, unicast, "nunca via route server", looking glass, route server, datas do registro e portas em PTTs externos.

    As URLs de looking glass e de route server são as informadas pela rede, sem verificação de que respondem. `cadastro` é inferência pelas datas (mede a manutenção do registro). Autodeclarado:
    pode estar desatualizado. As instalações da rede estão em `facility_lista(asn=…)`.

    Args:
        asn: Número do AS.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    b = inst.bloco_peering(_store.atributos_rede_doc(d), _store.portas_externas_doc(d), _store.vinculos_instalacoes_doc(d), int(asn))
    if b is None:
        raise ValueError(f"AS{asn} sem registro de rede no PeeringDB no snapshot {d}.")
    return b


@mcp.tool()
def ixp_portas(code: str, date: Optional[str] = None) -> dict:
    """Portas de um PTT externo no PeeringDB: quantas, quantos membros, distribuição por velocidade (Mbps), mediana, maior e soma.

    A soma é capacidade contratada declarada, não tráfego nem utilização. Só PTTs externos cadastrados no Arandurapé (veja `ixp_externo()`); o IX.br não entra. Autodeclarado no PeeringDB.

    Args:
        code: Código do PTT externo (minúsculo; ex.: "decix-sp", "equinix-sp").
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    b = inst.bloco_portas(_store.portas_externas_doc(d), code.lower())
    if b is None:
        raise ValueError(f"PTT externo '{code}' sem portas publicadas no snapshot {d}.")
    return b
