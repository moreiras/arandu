<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Tabela BGP global (RouteViews + RIPE RIS)

`fulltable_routeviews` · tipo **bruta** · ativa

Baixa RIBs MRT TABLE_DUMP_V2 (RFC 6396) de vários coletores RouteViews e RIPE RIS, processa em streaming e grava prefixos únicos, origem por prefixo e grafo de adjacências de AS-PATH, com o recorte das rotas brasileiras, e os prefixos com mais de uma origem observada (MOAS) com as origens por coletor. Não guarda os dumps (raw vazio).

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.fulltable_routeviews.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | critica |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 8d |
| Chaves | `asn`, `prefixo` |
| Entradas | `registro_br` |
| Amostra de teste | `tests/fixtures/raw/fulltable/` |

## Origem e licença

- **URL:** http://archive.routeviews.org/{coletor}/bgpdata/{AAAA.MM}/RIBS/rib.{data}.{hora}.bz2; https://data.ris.ripe.net/{rrc}/{AAAA.MM}/bview.{data}.{hora}.gz
- **Formato:** MRT TABLE_DUMP_V2 (bz2/gz)
- **Licença:** CC BY 4.0 (RouteViews); RIPE RIS: nao_verificado
- **Uso comercial:** `nao_verificado`
- **Termos:** https://www.routeviews.org/routeviews/faq/
- **Evidência / ressalvas:** RouteViews: FAQ 'Is RouteViews data licensed?' → Creative Commons v4 com Atribuição (verificado em 2026-10-13). RIPE RIS: termos não verificados; enquanto isso, a fonte inteira fica nao_verificado.

## Saídas

- **Normalizado (normalized/):** `summary/routes-{afi}.json.gz`, `summary/origin-prefixes-{afi}.json.gz`, `summary/prefix-set-{afi}.json.gz`, `summary/aspath-adj-{afi}.json.gz`, `summary/aspaths-{afi}/{coletor}.tsv.gz`, `summary/br-routes-{afi}.json.gz`, `summary/origins-multi-{afi}.json.gz`, `summary/fulltable_manifest.json`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `origin-prefixes[asn]` | list[str] | Prefixos originados por cada ASN na tabela global. | Chave é o ASN como string. | asn_docs → asns/{asn}.json#global_prefixes_v4; asn_docs → asns/{asn}.json#global_prefixes_v6 |
| `prefix-set` | list[str] | Conjunto ordenado de todos os prefixos únicos vistos na tabela global (v6 ou v4). | — | snapshot → summary.json#ft_space_v4; snapshot → summary.json#ft_space_v6 |
| `aspath-adj[asn].up` | list[int] | ASNs vistos imediatamente à esquerda do AS em qualquer AS-PATH dos coletores. Adjacência (inclui provedores, pares e o ponto de observação); a classificação em relações vem do produto `as_relationships`. | Inferido do AS-PATH; não é relação contratual. | asn_docs → asns/{asn}.json#upstreams_global_v4; asn_docs → asns/{asn}.json#upstreams_global_v6 |
| `aspath-adj[asn].down` | list[int] | ASNs vistos imediatamente à direita do AS em qualquer AS-PATH dos coletores. Adjacência (inclui clientes e pares), não é relação comercial. | Inferido do AS-PATH; não é relação contratual. | asn_docs → asns/{asn}.json#downstreams_global_v4; asn_docs → asns/{asn}.json#downstreams_global_v6 |
| `br-routes[].p` | str | Prefixo de uma rota cuja origem é ASN brasileiro. | — | — |
| `br-routes[].a` | list[int] | AS-PATH (mais representativo entre os coletores) da rota brasileira. | — | — |
| `br-routes[].c` | list[str] | Communities BGP associadas (standard e large). | — | routing_analysis → routing_analysis.json |
| `routes-{afi}.stats` | dict | Totais da tabela (rotas, prefixos únicos, ASNs diretos, de origem e stub). | — | snapshot → summary.json#global_table |
| `origins-multi-{afi}.prefixos[prefixo][asn]` | list[str] | Prefixos com duas ou mais origens (último AS do AS-PATH) entre todas as rotas de todos os coletores (MOAS); para cada origem, os coletores em que algum ponto de observação a viu. Só entram os prefixos com 2+ origens. | Fato observado, sem causa. A origem de um AS_SET final é o último ASN do conjunto (não ordenado). `coletores` lista os coletores que entraram na família; arquivo presente com `prefixos` vazio é nenhum MOAS observado entre eles. Licença e termos os da fonte (RouteViews CC BY 4.0; RIPE RIS não verificado). | routing_analysis → routing_analysis.json#moas; routing_analysis → routing_analysis.json#moas_resumo |
| `fulltable_manifest.{v6,v4}.sources` | list[str] | URLs dos dumps efetivamente usados em cada AFI. | Mostra quais coletores entraram; checado por publish.coleta_checks. | — |

## Limites

Visão agregada de poucos coletores (7 v6/8 v4, ver COLLECTORS); não vê tudo da Internet e a escolha de AS-PATH por prefixo é determinística, não 'o' caminho real. Dump de horário diferente por coletor (00h/02h), então uma troca de origem entre os horários dos dumps aparece como MOAS.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Fontes derivadas:** `bgp_stability_deep`, `bgp_updates_routeviews`
- **Produtos:** `as_relationships`, `asn_docs`, `ixp_docs`, `mapas_prefixos`, `routing_analysis`, `snapshot`

## Pendências (nao_verificado)

- Termos de uso do RIPE RIS (dados brutos MRT) não verificados.
