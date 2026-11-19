# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tools de roteamento e RPKI do MCP: `routing_analysis`, `bgp_stability`, `rpki_summary` e `rpki_prefix`.

Mesma fonte das rotas `/routing-analysis`, `/bgp-stability/*` e `/rpki/summary` (o `Store` e `api.routes.rpki.montar_resumo`). Os documentos
completos (`/bgp-stability` ~46 MB, `/bgp-stability-deep`) não vão ao MCP: as tools devolvem recortes que cabem numa resposta.
"""
from __future__ import annotations

import ipaddress
import json
from typing import Optional

from mcp_server.contexto import _resolve, _store, mcp

_LIMITE_SECAO_BYTES = 4000        # seção maior que isto só é descrita no índice; `secao=` a devolve inteira


@mcp.tool()
def routing_analysis(secao: Optional[str] = None, limit: int = 50, offset: int = 0, date: Optional[str] = None) -> dict:
    """Análise BGP global focada nos prefixos brasileiros (P_BR): composição, tamanhos de prefixo, more specifics, agregação, MOAS.

    Sem `secao` devolve o índice: os campos pequenos inteiros e, das seções grandes, só o nome e o tamanho em `secoes_grandes`.
    Com `secao` devolve aquela seção; lista ou mapa com mais de `limit` entradas vem fatiado (`total`, `offset`, `truncado`) — algumas
    seções têm dezenas de MB (cobertura do Registro.br). Inclui prefixos potencialmente filtráveis e, quando `has_path_data` é
    verdadeiro, estatísticas de AS_PATH, prepending, upstream aparente, higiene e communities (`as_path_stats`).

    Args:
        secao: Nome de uma seção do documento (veja `secoes_grandes` na chamada sem argumento).
        limit: Entradas por chamada de uma seção grande (1..500).
        offset: A partir de qual entrada (para paginar uma seção grande).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    from api.routes.routing_analysis import _enrich_top_communities
    d = _resolve(date)
    doc = _store.routing_analysis(d)
    if doc is None:
        raise ValueError(f"routing_analysis indisponível no snapshot {d}.")
    doc = dict(doc)
    _enrich_top_communities(doc)
    if secao is not None:
        if secao not in doc:
            raise ValueError(f"seção inválida: {secao!r}; válidas: {', '.join(sorted(doc))}")
        conteudo = doc[secao]
        limit, offset = max(1, min(limit, 500)), max(0, offset)
        if isinstance(conteudo, (list, dict)) and len(conteudo) > limit:
            total = len(conteudo)
            fatia = conteudo[offset: offset + limit] if isinstance(conteudo, list) else dict(list(conteudo.items())[offset: offset + limit])
            return {"snapshot_date": d, "secao": secao, "total": total, "offset": offset, "truncado": offset + limit < total, "conteudo": fatia}
        return {"snapshot_date": d, "secao": secao, "conteudo": conteudo}
    pequenos, grandes = {}, {}
    for k, v in doc.items():
        tamanho = len(json.dumps(v, ensure_ascii=False, default=str))
        if tamanho <= _LIMITE_SECAO_BYTES:
            pequenos[k] = v
        else:
            grandes[k] = {"tipo": type(v).__name__, "bytes": tamanho,
                          **({"itens": len(v)} if isinstance(v, (list, dict)) else {})}
    return {"snapshot_date": d, **pequenos, "secoes_grandes": grandes}


@mcp.tool()
def bgp_stability(
    asn: Optional[int] = None,
    modo: str = "visao_geral",
    weeks: int = 6,
    limit: int = 50,
    date: Optional[str] = None,
) -> dict:
    """Estabilidade BGP (eventos de atualização por prefixo por dia) — a visão geral, o ranking por AS ou um AS específico.

    Com `asn`: o AS no snapshot ativo (`stability`, null se não está na análise), diagnóstico aprofundado, estatísticas da semana e
    as séries horárias das últimas `weeks` semanas. Sem `asn`, `modo`:
      - `visao_geral`: período, distribuição, estatísticas, atividade global por hora, contagem de ASes por categoria de ruído e
        severidade e os 10 mais ruidosos;
      - `resumo`: uma linha por AS com `epppd` (eventos/prefixo/dia; total, v6 e v4), do mais ruidoso ao mais calmo, até `limit`;
      - `historico`: a atividade global por hora das últimas `weeks` semanas.
    O documento completo (~46 MB) não é servido por esta tool.

    Args:
        asn: Número do AS. Omita para as visões globais.
        modo: visao_geral | resumo | historico (ignorado com `asn`).
        weeks: Semanas de série (1..12).
        limit: Quantos ASes em `modo="resumo"` (1..500).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    weeks = max(1, min(weeks, 12))
    indisponivel = f"bgp_stability indisponível no snapshot {d}."
    if asn is not None:
        out = _store.bgp_stability_asn(d, int(asn), weeks)
        if out is None:
            raise ValueError(indisponivel)
        return out
    if modo == "visao_geral":
        out = _store.bgp_stability_visao_geral(d)
        if out is None:
            raise ValueError(indisponivel)
        return out
    if modo == "resumo":
        itens = _store.bgp_stability_resumo(d)
        if itens is None:
            raise ValueError(indisponivel)
        ordenados = sorted(itens, key=lambda r: r.get("epppd") or 0, reverse=True)
        return {"snapshot_date": d, "total": len(itens), "items": ordenados[:max(1, min(limit, 500))]}
    if modo == "historico":
        return {"snapshot_date": d, "weeks": _store.bgp_stability_historico_resumo(d, weeks)}
    raise ValueError(f"modo inválido: {modo!r}; válidos: visao_geral, resumo, historico")


@mcp.tool()
def rpki_summary(date: Optional[str] = None) -> dict:
    """Adoção de RPKI nos ASNs brasileiros: quantos publicaram ROA e ASPA e quanto do espaço anunciado tem ROA.

    Os campos `br_space_v4_*` e `br_space_v6_*` são o espaço ANUNCIADO (equivalentes a /24 e /48) pelos ASNs BR, agrupado por o AS
    ter publicado ao menos uma ROA — não é o espaço alocado pelo Registro.br e não garante que cada prefixo tenha ROA válida
    (para um prefixo específico use `rpki_prefix`).

    Args:
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    from api.routes.rpki import montar_resumo
    return montar_resumo(_store, _resolve(date))


@mcp.tool()
def rpki_prefix(prefix: str, asn: Optional[int] = None, date: Optional[str] = None) -> dict:
    """Validade RPKI (RFC 6483) de um prefixo anunciado por um AS: `valid`, `invalid` ou `not_found`, com as ROAs do AS que o cobrem.

    `valid` = há ROA do AS cobrindo o prefixo e o tamanho cabe no `maxLength`; `invalid` = há ROA do AS que cobre o prefixo, mas o
    tamanho excede o `maxLength`, ou só há ROA de OUTRO AS; `not_found` = nenhuma ROA cobre o prefixo. Sem `asn`, usa o AS originador do prefixo
    geolocalizado do Registro.br (`get_prefix`); se o prefixo não está lá, informe o `asn`.

    Args:
        prefix: Prefixo CIDR (ex.: "200.160.0.0/20" ou "2001:12ff::/32").
        asn: AS que anuncia o prefixo. Opcional para prefixos do Registro.br.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    try:
        rede = ipaddress.ip_network(prefix.strip(), strict=False)
    except ValueError:
        raise ValueError(f"prefixo inválido: {prefix!r}")
    texto = str(rede)
    origem = "informado"
    if asn is None:
        gj = _store.geo_map(d, "prefixes") or {}
        feat = next((f for f in gj.get("features", []) if (f.get("properties") or {}).get("prefix") == texto), None)
        asn = (feat or {}).get("properties", {}).get("origin_asn") if feat else None
        if asn is None:
            raise ValueError(f"informe o `asn`: o prefixo {texto} não está entre os geolocalizados do Registro.br em {d}.")
        origem = "prefixo geolocalizado do Registro.br"
    asn = int(asn)
    estado = _store.rpki_validate_prefixes(d, asn, [texto]).get(texto)
    if estado is None:
        raise ValueError(f"sem VRPs (RPKI) no snapshot {d}.")
    cobrem = []
    for v in _store.rpki_vrps_for_asn(d, asn):
        try:
            if rede.version == ipaddress.ip_network(v["prefix"], strict=False).version and rede.subnet_of(ipaddress.ip_network(v["prefix"], strict=False)):
                cobrem.append(v)
        except (ValueError, TypeError, KeyError):
            continue
    return {"snapshot_date": d, "prefix": texto, "asn": asn, "origem_do_asn": origem, "estado": estado,
            "roas_do_as_que_cobrem": cobrem, "tamanho": rede.prefixlen}
