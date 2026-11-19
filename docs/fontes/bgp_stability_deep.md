<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Estabilidade BGP aprofundada (top ASes ruidosos)

`bgp_stability_deep` · tipo **derivada** · ativa

Relê os updates em cache dos N ASes mais ruidosos para diagnosticar a causa: o ruído é do próprio AS, de um prefixo específico ou de um upstream suspeito.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.bgp_stability_deep.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 8d |
| Chaves | `asn`, `prefixo` |
| Entradas | `bgp_updates_routeviews`, `fulltable_routeviews` |
| Amostra de teste | `tests/fixtures/raw/bgp_updates/` |

## Saídas

- **Normalizado (normalized/):** `summary/bgp_stability_deep.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `suspected_upstreams[].asn` | int | ASN do upstream suspeito de propagar instabilidade. | Hipótese estatística sobre AS-PATH, não afirmação. | bgp_stability → bgp_stability_deep.json |
| `suspected_upstreams[].events_attributed` | int | Eventos atribuídos a esse upstream. | — | bgp_stability → bgp_stability_deep.json |
| `as_diagnosis[].verdict` | str | Veredito da análise para o AS (origem interna, prefixo específico, upstream). | Rótulo inferido. | bgp_stability → bgp_stability_deep.json |
| `as_diagnosis[].prefix_sync_score` | float | Quão sincronizados estão os eventos entre prefixos do AS (0–1). | — | bgp_stability → bgp_stability_deep.json |
| `as_diagnosis[].upstream_concentration_pct` | float | % dos eventos concentrados no upstream mais provável. | — | bgp_stability → bgp_stability_deep.json |

## Limites

Diagnóstico inferido (rotulado como hipótese); depende da janela de 7 dias e de um único coletor.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `bgp_stability`
