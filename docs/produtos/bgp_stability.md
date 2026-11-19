<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Estabilidade BGP (publicação)

`bgp_stability` · produto

Publica a análise de estabilidade dos ASNs BR (7 dias, route-views.saopaulo) e o diagnóstico aprofundado dos mais ruidosos.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.bgp_stability.build; products.bgp_stability.deep` |
| Chaves de junção | `asn` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [bgp_updates_routeviews](../fontes/bgp_updates_routeviews.md) — uso comercial: `permitido`
- fonte [bgp_stability_deep](../fontes/bgp_stability_deep.md)
- fonte [asn_names](../fontes/asn_names.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `bgp_stability.json`, `bgp_stability_deep.json`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `as_stability[].rank / severity / noise_category` | int / str | Posição no ranking de ruído, severidade e categoria de ruído do AS. | Faixas definidas em analysis/bgp_stability. | bgp_stability → bgp_stability.json#as_stability |
| `epppd_stats` | dict | Eventos por prefixo por dia: mediana, média e máximo. | — | bgp_stability → bgp_stability.json#epppd_stats |
| `period` | dict | Janela analisada, coletor e contagem de eventos. | — | bgp_stability → bgp_stability.json#period |
| `distribution` | dict | Distribuição de eventos por prefixo/dia (percentis e buckets) por família. | — | bgp_stability → bgp_stability.json#distribution |
| `hourly_global` | dict | Série horária global de anúncios, retiradas e mudanças de atributo. | — | bgp_stability → bgp_stability.json#hourly_global |
| `published_at` | str | Instante da publicação. | — | bgp_stability → bgp_stability.json#published_at |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | bgp_stability → bgp_stability_deep.json#generated_at |
| `date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | bgp_stability → bgp_stability_deep.json#date |
| `top_n` | int | Quantidade de ASes ruidosos analisados. | — | bgp_stability → bgp_stability_deep.json#top_n |
| `suspected_upstreams` | list[dict] | Upstreams suspeitos com eventos atribuídos e hora de pico (hipótese). | — | bgp_stability → bgp_stability_deep.json#suspected_upstreams |
| `as_diagnosis` | list[dict] | Diagnóstico por AS: veredito, sincronia entre prefixos e concentração em upstream (hipótese). | — | bgp_stability → bgp_stability_deep.json#as_diagnosis |
| `published_at` | str | Instante da publicação. | — | bgp_stability → bgp_stability_deep.json#published_at |

## Limites

/bgp-stability completo pesa ~40 MB: listas usam /bgp-stability/summary.
