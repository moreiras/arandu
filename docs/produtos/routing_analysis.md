<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Análise de roteamento BGP do Brasil

`routing_analysis` · produto

Composição do espaço BR na tabela global (estrito, só origem, só prefixo), distribuição de tamanhos, mais-específicos, agregação possível, cobertura do Registro.br, prefixos específicos demais e origem múltipla (MOAS) dos prefixos brasileiros.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.routing_analysis.build` |
| Chaves de junção | `asn`, `prefixo` |
| Cenários de teste (dataset sintético) | `rpki_invalido_moas` |

## Entradas

- fonte [fulltable_routeviews](../fontes/fulltable_routeviews.md) — uso comercial: `nao_verificado`
- fonte [registro_br](../fontes/registro_br.md) — uso comercial: `nao_verificado`
- fonte [rpki_collector](../fontes/rpki_collector.md) — uso comercial: `nao_verificado`
- fonte [asn_names](../fontes/asn_names.md) — uso comercial: `nao_verificado`
- fonte [curada_bgp_communities](../fontes/curada_bgp_communities.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `routing_analysis.json`, `routing_analysis_resumo.json`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `pbr_composition.{v6,v4}.strict_br / origin_only_br / prefix_only_br` | dict | Rotas e ASNs em que prefixo e origem são BR (estrito), só a origem é BR ou só o prefixo é BR. | Definição de PBR do projeto. | routing_analysis → routing_analysis.json#pbr_composition |
| `aggregation_by_asn[].savings_origin / savings_path / savings_path_pct` | int / float | Rotas economizáveis se agregadas por origem ou por caminho. | Estimativa teórica; agregação real depende de política. | routing_analysis → routing_analysis.json#aggregation_by_asn |
| `moas[].prefix / afi / origins / br_origins / origens[].asn / origens[].coletores / origens[].coletores_nomes / origens[].asn_br` | list[dict] | Prefixos brasileiros (contidos em bloco do Registro.br) com mais de um AS de origem observado nos coletores da tabela global, com cada origem, se o ASN está na lista do Registro.br e quantos (e quais) coletores a viram. IPv6 antes de IPv4. | Fato observado (de `origins-multi-{afi}`), sem rótulo de causa. Até `moas_resumo.lista_limite` entradas (`lista_truncada`). Nulo, com o motivo em `moas_indisponivel`, quando a coleta do snapshot guardou uma origem por prefixo. | routing_analysis → routing_analysis.json#moas |
| `moas_resumo.prefixos.{v6,v4}.global / br; moas_resumo.coletores.{v6,v4}` | dict | Prefixos com 2+ origens por família, na tabela inteira e só os brasileiros, e os coletores que entraram; família sem `origins-multi` fica nula. Traz também `definicao`, `como_ler` (causas só como hipótese) e `limites`. | Zero com o resumo presente é nenhum MOAS observado entre esses coletores; resumo nulo é não medido. | routing_analysis → routing_analysis.json#moas_resumo |
| `too_specific` | list | Prefixos mais específicos que o limite prático (/48 IPv6, /24 IPv4). | — | routing_analysis → routing_analysis.json#too_specific |
| `registro_br_coverage[].coverage_pct / has_exact_aggregate` | float / bool | Cobertura do bloco alocado por rotas e se o agregado exato é anunciado. | — | routing_analysis → routing_analysis.json#registro_br_coverage |
| `has_path_data` | bool | Se os dados de AS-PATH estavam disponíveis para as análises de caminho. | — | routing_analysis → routing_analysis.json#has_path_data |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | routing_analysis → routing_analysis.json#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | routing_analysis → routing_analysis.json#generated_at |
| `br_asns_visible` | int | ASNs BR vistos na tabela global. | — | routing_analysis → routing_analysis.json#br_asns_visible |
| `br_asns_registered` | int | ASNs BR registrados. | — | routing_analysis → routing_analysis.json#br_asns_registered |
| `summary` | dict | Totais por família (rotas, prefixos, ASNs globais; rotas e ASNs PBR). | — | routing_analysis → routing_analysis.json#summary |
| `prefix_length_dist` | dict | Distribuição de rotas e espaço por comprimento de prefixo (v6, v4). | — | routing_analysis → routing_analysis.json#prefix_length_dist |
| `more_specifics` | dict | Contagem de raízes e mais-específicos (mesma origem × origem diferente) e profundidade. | — | routing_analysis → routing_analysis.json#more_specifics |
| `top_asns_more_specifics` | list[dict] | ASNs BR com mais rotas mais-específicas. | — | routing_analysis → routing_analysis.json#top_asns_more_specifics |
| `global_comparison` | dict | Percentuais de /48 (v6) ou /24 (v4) e de mais-específicos, global × PBR, por família. | — | routing_analysis → routing_analysis.json#global_comparison |
| `as_path_stats` | dict | Estatísticas de AS-PATH por família: comprimento (média, mediana, p95), rotas com prepend, AS privado, loops e AS_TRANS; só com dados de caminho. | — | routing_analysis → routing_analysis.json#as_path_stats |
| `rpki.{v6,v4}.valid / invalid / not_found / espaco` | dict | Rotas brasileiras (P_BR) por estado RPKI de origem (RFC 6811), com a união do espaço de cada estado (/48 ou /24) e os ASNs de origem com rota inválida. | Validação contra os VRPs do snapshot; um bloco pode ter rotas em mais de um estado, então os espaços não somam o total. | routing_analysis → routing_analysis_resumo.json#rpki |
| `saude.{v6,v4}.mais_especificos / filtraveis; saude.moas` | dict | Totais de saúde da tabela para o Panorama técnico (mais-específicos, prefixos filtráveis, MOAS), copiados da análise completa. `saude.moas.{v6,v4}` = {prefixos, prefixos_br, coletores}; nulo, com o motivo em `saude.moas_indisponivel`, quando não medido. | — | routing_analysis → routing_analysis_resumo.json#saude |

## Limites

Depende do RPKI estar coletado antes.
