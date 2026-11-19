<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Documentos por IXP, agregado e IXPs externos

`ixp_docs` · produto

Métricas por IXP do IX.br (ASNs diretos, originadores, stubs, cobertura de espaço × tabela global), a união entre IXPs e os documentos dos IXPs externos do PeeringDB.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.ixp_metrics.build; publish.snapshot_builder` |
| Chaves de junção | `ixp`, `asn`, `uf` |
| Cenários de teste (dataset sintético) | `ptt_coleta_parcial`, `municipio_sem_ptt` |

## Entradas

- produto [bgp_ixp_normalizado](bgp_ixp_normalizado.md)
- fonte [fulltable_routeviews](../fontes/fulltable_routeviews.md) — uso comercial: `nao_verificado`
- fonte [registro_br](../fontes/registro_br.md) — uso comercial: `nao_verificado`
- fonte [ixbr_api](../fontes/ixbr_api.md) — uso comercial: `nao_verificado`
- fonte [peeringdb_ixps](../fontes/peeringdb_ixps.md) — uso comercial: `restrito`
- fonte [curada_ixps](../fontes/curada_ixps.md) — uso comercial: `nao_verificado`
- fonte [curada_peeringdb_ixps](../fontes/curada_peeringdb_ixps.md) — uso comercial: `nao_verificado`
- fonte [lacnic_delegated](../fontes/lacnic_delegated.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `ixps/{ixp}.json`, `ixps/index.json`, `ixps/_aggregate.json`, `external-ixps/{ixp}.json`, `external-ixps/index.json`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `v6/v4.asn_direct_count / asn_origin_count / asn_stub_count` | int | Contagem de ASNs diretos, originadores e stubs no IXP. | — | ixp_docs → ixps/{ixp}.json#v4 |
| `v6/v4.br_asns_direct_pct / br_asns_origin_pct` | float | % dos ASNs BR da tabela global que são diretos / originadores no IXP. | — | ixp_docs → ixps/{ixp}.json#v4 |
| `v6/v4.ixp_space` | int | Espaço de endereços anunciado no IXP (/48 em IPv6; endereços em IPv4). | União de prefixos, sem dupla contagem. | ixp_docs → ixps/{ixp}.json#v4 |
| `v6/v4.br_prefix_coverage_pct` | float | % do espaço declarado ao Registro.br coberto por prefixos vistos no IXP. | — | ixp_docs → ixps/{ixp}.json#v4 |
| `v6/v4.ixp_vs_fulltable_space_pct` | float | Espaço do IXP como % do espaço da tabela global. | — | ixp_docs → ixps/{ixp}.json#v4 |
| `ixbr_members_count` | int | Membros cadastrados no IX.br (inclui bilaterais). | — | ixp_docs → ixps/index.json#ixbr_members_count |
| `status` | str | ok, parcial ou ausente conforme a coleta da família no IXP. | — | ixp_docs → ixps/index.json#status |
| `asn_direct_union_count / asn_origin_union_count` | int | Tamanho da união (não a soma) de ASNs entre todos os IXPs. | — | ixp_docs → ixps/_aggregate.json#asn_direct_union_count |
| `members[] (external-ixps)` | list[dict] | Membros do IXP externo com asn, nome, velocidade e is_br. | — | ixp_docs → external-ixps/{ixp}.json#members |
| `br_member_count` | int | Membros brasileiros do IXP externo. | — | ixp_docs → external-ixps/{ixp}.json#br_member_count |
| `ixp` | str | Código do IXP. | — | ixp_docs → ixps/{ixp}.json#ixp |
| `name` | str | Cidade-sede do IXP. | — | ixp_docs → ixps/{ixp}.json#name |
| `uf` | str | UF do IXP. | — | ixp_docs → ixps/{ixp}.json#uf |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | ixp_docs → ixps/{ixp}.json#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | ixp_docs → ixps/{ixp}.json#generated_at |
| `v6` | dict | Métricas IPv6 do IXP (mesma estrutura de v4). | — | ixp_docs → ixps/{ixp}.json#v6 |
| `v4` | dict | Métricas IPv4 do IXP (rotas, prefixos, ASNs diretos/originadores/stubs, cobertura). | — | ixp_docs → ixps/{ixp}.json#v4 |
| `code` | str | Código do IXP externo (configuração). | — | ixp_docs → external-ixps/{ixp}.json#code |
| `name` | str | Nome do IXP externo. | — | ixp_docs → external-ixps/{ixp}.json#name |
| `city` | str | Cidade do IXP externo. | — | ixp_docs → external-ixps/{ixp}.json#city |
| `country` | str | País (ISO 3166-1 alfa-2). | — | ixp_docs → external-ixps/{ixp}.json#country |
| `member_count` | int | Quantidade de membros listados no PeeringDB. | — | ixp_docs → external-ixps/{ixp}.json#member_count |
| `last_updated` | str | Data de referência dos dados do IXP externo (igual à do snapshot). | — | ixp_docs → external-ixps/{ixp}.json#last_updated |
| `asn_direct_union_count` | int | ASNs diretos distintos (união v6+v4) no IXP. | — | ixp_docs → ixps/index.json#asn_direct_union_count |
| `asn_origin_union_count` | int | ASNs originadores distintos (união v6+v4). | — | ixp_docs → ixps/index.json#asn_origin_union_count |
| `br_asns_direct_union_count` | int | ASNs BR diretos distintos. | — | ixp_docs → ixps/index.json#br_asns_direct_union_count |
| `br_asns_origin_union_count` | int | ASNs BR originadores distintos. | — | ixp_docs → ixps/index.json#br_asns_origin_union_count |
| `uf` | str | UF do IXP. | — | ixp_docs → ixps/index.json#uf |
| `v6` | dict | Resumo IPv6 do IXP. | — | ixp_docs → ixps/index.json#v6 |
| `v4` | dict | Resumo IPv4 do IXP. | — | ixp_docs → ixps/index.json#v4 |
| `ixp` | str | Sempre '_aggregate'. | — | ixp_docs → ixps/_aggregate.json#ixp |
| `name` | str | Rótulo do agregado. | — | ixp_docs → ixps/_aggregate.json#name |
| `uf` | str | UF (vazia no agregado). | — | ixp_docs → ixps/_aggregate.json#uf |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | ixp_docs → ixps/_aggregate.json#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | ixp_docs → ixps/_aggregate.json#generated_at |
| `ixp_count` | int | Quantidade de IXPs na união. | — | ixp_docs → ixps/_aggregate.json#ixp_count |
| `asn_origin_union_count` | int | ASNs originadores distintos entre todos os IXPs. | — | ixp_docs → ixps/_aggregate.json#asn_origin_union_count |
| `br_asns_origin_union_count` | int | ASNs BR originadores distintos entre todos os IXPs. | — | ixp_docs → ixps/_aggregate.json#br_asns_origin_union_count |
| `v6` | dict | Métricas IPv6 da união de todos os IXPs. | — | ixp_docs → ixps/_aggregate.json#v6 |
| `v4` | dict | Métricas IPv4 da união de todos os IXPs. | — | ixp_docs → ixps/_aggregate.json#v4 |
| `ixps` | list[dict] | IXPs externos exibidos, com contagens. | — | ixp_docs → external-ixps/index.json#ixps |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | ixp_docs → external-ixps/index.json#snapshot_date |

## Limites

Visão do Route Server: membro bilateral só aparece pelo cadastro. AP não coletou em 2026-10-11.
