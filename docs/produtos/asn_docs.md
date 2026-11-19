<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Documentos por ASN, índice e nomes

`asn_docs` · produto

Um documento por ASN (BR ∪ visto nos IXPs ∪ visto na tabela global) com identidade, prefixos, presença em IXPs, conectividade, PeeringDB, geolocalização, SICI, RPKI e alertas; mais o índice resumido e o dicionário de nomes.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.ixp_metrics.build; publish.snapshot_builder` |
| Chaves de junção | `asn`, `cnpj`, `prefixo`, `ixp` |
| Cenários de teste (dataset sintético) | `rpki_invalido_moas`, `cnpj_dois_asns`, `mudanca_de_origem`, `scm_sem_sici` |

## Entradas

- fonte [registro_br](../fontes/registro_br.md) — uso comercial: `nao_verificado`
- fonte [lacnic_delegated](../fontes/lacnic_delegated.md) — uso comercial: `nao_verificado`
- fonte [fulltable_routeviews](../fontes/fulltable_routeviews.md) — uso comercial: `nao_verificado`
- produto [bgp_ixp_normalizado](bgp_ixp_normalizado.md)
- fonte [asn_names](../fontes/asn_names.md) — uso comercial: `nao_verificado`
- fonte [apnic_pop](../fontes/apnic_pop.md) — uso comercial: `nao_verificado`
- fonte [peeringdb_networks](../fontes/peeringdb_networks.md) — uso comercial: `restrito`
- fonte [peeringdb_ixps](../fontes/peeringdb_ixps.md) — uso comercial: `restrito`
- fonte [rdap](../fontes/rdap.md)
- fonte [cnpj_geo](../fontes/cnpj_geo.md) — uso comercial: `nao_verificado`
- fonte [prefix_geo](../fontes/prefix_geo.md) — uso comercial: `permitido`
- fonte [peeringdb_intl_geo](../fontes/peeringdb_intl_geo.md) — uso comercial: `restrito`
- fonte [anatel_sici](../fontes/anatel_sici.md) — uso comercial: `permitido`

## Saídas

- **Publicado:** `asns/{asn}.json`, `asns/index.json`, `asns/names.json`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `is_br` | bool | ASN delegado ao Brasil pelo LACNIC (country=BR), não apenas visto no BR. | Hierarquia: LACNIC delegated, com fallback às chaves do Registro.br. | asn_docs → asns/{asn}.json#is_br |
| `ixps_direct` | list[str] | Códigos dos IXPs em que o AS tem sessão BGP direta com o Route Server. | — | asn_docs → asns/{asn}.json#ixps_direct |
| `ixps_origin` | list[str] | Códigos dos IXPs em que o AS aparece como origem de rotas (direto ou via terceiros). | — | asn_docs → asns/{asn}.json#ixps_origin |
| `ixp_presence[ixp][afi]` | dict | Por IXP e família: direct, origin e prefixos vistos. | — | asn_docs → asns/{asn}.json#ixp_presence |
| `upstreams / downstreams` | list[int] | Vizinhos nos AS-PATHs dos Route Servers (v6+v4); _v6/_v4 separam a família. | Adjacência observada, não contrato. | asn_docs → asns/{asn}.json#upstreams |
| `upstreams_global_v6/_v4 / downstreams_global_v6/_v4` | list[int] | Adjacências do grafo da tabela global (RouteViews/RIS). | Adjacência observada nos coletores. | asn_docs → asns/{asn}.json#upstreams_global_v4 |
| `is_multihomed_v6/_v4` | bool | Mais de um vizinho a montante distinto na tabela global, na família (adjacência no AS_PATH; não distingue provedor de par). | Inferido: depende de quais coletores enxergam o AS. | asn_docs → asns/{asn}.json#is_multihomed_v4 |
| `single_upstream_v6/_v4` | int\|null | O único vizinho a montante observado na tabela global (quando exatamente um); não prova dependência de um provedor. | Inferido. | asn_docs → asns/{asn}.json#single_upstream_v4 |
| `relacoes` | dict | Relações inferidas do ASN pelo produto as_relationships (ARC v1) — provedores, clientes, pares, irmãos e elos sem classificação, cada um com ASN, probabilidade, nível (declarado, confirmado, provável, possível) e famílias; n_provedores, visibilidade e single_homed/multihomed por família (null = indeterminado). | Inferência rotulada, não contrato. single_homed só é afirmado com visibilidade mínima (VPs dos coletores ou PTTs) e sem provedor apenas possível. Ausente em snapshots anteriores ao ARC. | asn_docs → asns/{asn}.json#relacoes |
| `has_ipv6` | bool | Há prefixo IPv6 alocado, anunciado ou visto em IXP. | — | asn_docs → asns/{asn}.json#has_ipv6 |
| `announced_ipv4_addresses / announced_ipv6_48s` | int | Espaço efetivamente anunciado na tabela global: equivalentes a /48 em IPv6 e endereços em IPv4. | — | asn_docs → asns/{asn}.json#announced_ipv4_addresses |
| `users_per_ip / users_per_v6_48` | float | Usuários estimados (APNIC) por endereço IPv4 anunciado / por /48. | Proxy de CGNAT; derivado de estimativa — rotular 'estimado'. | asn_docs → asns/{asn}.json#users_per_ip |
| `pdb_registered / external_ixps` | bool / list[str] | Se há cadastro no PeeringDB e os IXPs externos em que declara presença. | — | asn_docs → asns/{asn}.json#pdb_registered |
| `ixp_member_codes` | list[str] | IXPs em que o ASN consta no cadastro do IX.br (ixbr_members), mesmo sem sessão no Route Server. | — | asn_docs → asns/{asn}.json#ixp_member_codes |
| `sici` | dict | Bloco do SICI do CNPJ do AS: acessos, PF/PJ, capacidade, tecnologias, série mensal, divergência APNIC×Anatel. | 'nao_comparavel' quando acessos_compartilhados. | asn_docs → asns/{asn}.json#sici |
| `path_node_meta[asn]` | dict | Nome, is_br e espaço v6/v4 dos ASNs que aparecem em caminhos do documento. | — | asn_docs → asns/{asn}.json#path_node_meta |
| `index[].has_rpki / has_aspa` | bool | Se o AS tem ROA / objeto ASPA no snapshot. | — | asn_docs → asns/index.json#has_rpki |
| `index[].space_v6 / space_v4` | int | Espaço anunciado (/48 em IPv6; endereços em IPv4) no índice. | — | asn_docs → asns/index.json#space_v4 |
| `asn` | int | Número do sistema autônomo do documento. | — | asn_docs → asns/{asn}.json#asn |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | asn_docs → asns/{asn}.json#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | asn_docs → asns/{asn}.json#generated_at |
| `name` | str | Nome do AS (Registro.br → PeeringDB → RIPE bulk, nessa ordem de prioridade). | — | asn_docs → asns/{asn}.json#name |
| `cnpj` | str | CNPJ da organização titular, quando conhecido (Registro.br). | — | asn_docs → asns/{asn}.json#cnpj |
| `rir_prefixes_v6` | list[str] | Prefixos IPv6 alocados à organização no Registro.br. | — | asn_docs → asns/{asn}.json#rir_prefixes_v6 |
| `rir_prefixes_v4` | list[str] | Prefixos IPv4 alocados à organização no Registro.br. | — | asn_docs → asns/{asn}.json#rir_prefixes_v4 |
| `rir_prefixes_v4_count` | int | Quantidade de prefixos IPv4 alocados. | — | asn_docs → asns/{asn}.json#rir_prefixes_v4_count |
| `rir_prefixes_v6_count` | int | Quantidade de prefixos IPv6 alocados. | — | asn_docs → asns/{asn}.json#rir_prefixes_v6_count |
| `global_prefixes_v6` | list[str] | Prefixos IPv6 originados pelo AS na tabela global. | — | asn_docs → asns/{asn}.json#global_prefixes_v6 |
| `global_prefixes_v4` | list[str] | Prefixos IPv4 originados pelo AS na tabela global. | — | asn_docs → asns/{asn}.json#global_prefixes_v4 |
| `global_prefixes_v4_count` | int | Quantidade de prefixos IPv4 anunciados. | — | asn_docs → asns/{asn}.json#global_prefixes_v4_count |
| `global_prefixes_v6_count` | int | Quantidade de prefixos IPv6 anunciados. | — | asn_docs → asns/{asn}.json#global_prefixes_v6_count |
| `upstreams_v6` | list[int] | Vizinhos à esquerda no AS-PATH IPv6 dos Route Servers (adjacência; não é relação comercial). | — | asn_docs → asns/{asn}.json#upstreams_v6 |
| `upstreams_v4` | list[int] | Vizinhos à esquerda no AS-PATH IPv4 dos Route Servers (adjacência; não é relação comercial). | — | asn_docs → asns/{asn}.json#upstreams_v4 |
| `downstreams_v6` | list[int] | Vizinhos à direita no AS-PATH IPv6 dos Route Servers (adjacência; não é relação comercial). | — | asn_docs → asns/{asn}.json#downstreams_v6 |
| `downstreams_v4` | list[int] | Vizinhos à direita no AS-PATH IPv4 dos Route Servers (adjacência; não é relação comercial). | — | asn_docs → asns/{asn}.json#downstreams_v4 |
| `downstreams` | list[int] | Vizinhos à direita nos AS-PATHs dos Route Servers (v6 e v4 unidos; adjacência, não relação comercial). | — | asn_docs → asns/{asn}.json#downstreams |
| `is_multihomed_v6` | bool | Mais de um vizinho a montante distinto na tabela global, no IPv6 (adjacência no AS_PATH; não distingue provedor de par). | — | asn_docs → asns/{asn}.json#is_multihomed_v6 |
| `single_upstream_v6` | int\|null | O único vizinho a montante observado no IPv6 (quando exatamente um); não prova dependência de um provedor. | — | asn_docs → asns/{asn}.json#single_upstream_v6 |
| `geo_prefixes_v6` | dict | Geolocalização (DB-IP) dos prefixos IPv6 do AS. | — | asn_docs → asns/{asn}.json#geo_prefixes_v6 |
| `geo_prefixes_v4` | dict | Geolocalização (DB-IP) dos prefixos IPv4 do AS: {prefixo: {lat, lon, city, uf, …}}. | — | asn_docs → asns/{asn}.json#geo_prefixes_v4 |
| `announced_ipv6_48s` | int | Espaço IPv6 anunciado, em equivalentes a /48. | — | asn_docs → asns/{asn}.json#announced_ipv6_48s |
| `users_per_v6_48` | float | Usuários estimados (APNIC) por /48 anunciado. | — | asn_docs → asns/{asn}.json#users_per_v6_48 |
| `geo_org` | dict | Cadastro e geolocalização da organização (cnpj_geo): endereço, CNAE, situação, porte, coordenadas. | — | asn_docs → asns/{asn}.json#geo_org |
| `pdb` | dict | Metadados autodeclarados da rede no PeeringDB (política, tipo, tráfego, IRR). | — | asn_docs → asns/{asn}.json#pdb |
| `apnic_users` | int\|null | Usuários de Internet estimados atrás do AS (APNIC Labs, janela de 60 dias). | — | asn_docs → asns/{asn}.json#apnic_users |
| `apnic_users_pct_cc` | float\|null | % da população estimada do país que o AS representa. | — | asn_docs → asns/{asn}.json#apnic_users_pct_cc |
| `apnic_v6_users` | int\|null | Usuários IPv6 estimados. | — | asn_docs → asns/{asn}.json#apnic_v6_users |
| `apnic_v6_pct_as` | float\|null | % dos usuários do AS que usam IPv6. | — | asn_docs → asns/{asn}.json#apnic_v6_pct_as |
| `asn` | int | ASN. | — | asn_docs → asns/index.json#asn |
| `name` | str | Nome do AS. | — | asn_docs → asns/index.json#name |
| `is_br` | bool | ASN delegado ao Brasil. | — | asn_docs → asns/index.json#is_br |
| `has_ipv6` | bool | Há IPv6 alocado, anunciado ou visto em IXP. | — | asn_docs → asns/index.json#has_ipv6 |
| `rir_prefixes_v4_count` | int | Prefixos IPv4 alocados. | — | asn_docs → asns/index.json#rir_prefixes_v4_count |
| `rir_prefixes_v6_count` | int | Prefixos IPv6 alocados. | — | asn_docs → asns/index.json#rir_prefixes_v6_count |
| `global_prefixes_v4_count` | int | Prefixos IPv4 anunciados. | — | asn_docs → asns/index.json#global_prefixes_v4_count |
| `global_prefixes_v6_count` | int | Prefixos IPv6 anunciados. | — | asn_docs → asns/index.json#global_prefixes_v6_count |
| `ixps_direct_count` | int | IXPs em que o AS é direto. | — | asn_docs → asns/index.json#ixps_direct_count |
| `ixps_origin_count` | int | IXPs em que o AS é originador. | — | asn_docs → asns/index.json#ixps_origin_count |
| `ixps_origin_v4_count` | int | IXPs em que o AS origina rotas IPv4. | — | asn_docs → asns/index.json#ixps_origin_v4_count |
| `ixps_origin_v6_count` | int | IXPs em que o AS origina rotas IPv6. | — | asn_docs → asns/index.json#ixps_origin_v6_count |
| `apnic_users` | int\|null | Usuários estimados (APNIC). | — | asn_docs → asns/index.json#apnic_users |
| `apnic_v6_users` | int\|null | Usuários IPv6 estimados (APNIC). | — | asn_docs → asns/index.json#apnic_v6_users |
| `pct_v6` | float\|null | % de usuários IPv6 do AS (APNIC). | — | asn_docs → asns/index.json#pct_v6 |
| `external_ixps_count` | int | IXPs externos em que declara presença (PeeringDB). | — | asn_docs → asns/index.json#external_ixps_count |
| `pdb_registered` | bool | Há cadastro no PeeringDB. | — | asn_docs → asns/index.json#pdb_registered |
| `has_aspa` | bool | Há objeto ASPA publicado pelo AS. | — | asn_docs → asns/index.json#has_aspa |
| `space_v6` | int | Espaço IPv6 anunciado (em /48 equivalentes) no índice. | — | asn_docs → asns/index.json#space_v6 |
| `*` | str | Mapa ASN (chave string) → nome do AS; só ASNs do snapshot. | — | asn_docs → asns/names.json#* |

## Limites

Arquivo grande (≈ 87 mil ASNs; index.json ≈ 43 MB): listas paginam via /asns/summary. Contém e-mail/telefone de CNPJ em geo_org e nas outorgas; só as rotas públicas os removem.
