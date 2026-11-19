<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Updates BGP do RouteViews São Paulo (7 dias)

`bgp_updates_routeviews` · tipo **bruta** · ativa

Baixa os arquivos de update MRT do coletor route-views.saopaulo dos 7 dias anteriores ao snapshot e conta eventos (anúncios, retiradas, mudanças de atributo) por (AS, prefixo), com deduplicação.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.bgp_updates_routeviews.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | semanal → diaria |
| Frescor máximo | 8d |
| Chaves | `asn`, `prefixo` |
| Entradas | `fulltable_routeviews`, `registro_br` |
| Amostra de teste | `tests/fixtures/raw/bgp_updates/` |

## Origem e licença

- **URL:** http://archive.routeviews.org/route-views.saopaulo/bgpdata
- **Formato:** MRT updates (bz2)
- **Licença:** CC BY 4.0 (RouteViews)
- **Uso comercial:** `permitido`
- **Termos:** https://www.routeviews.org/routeviews/faq/
- **Evidência / ressalvas:** RouteViews: FAQ → Creative Commons v4 com Atribuição (verificado em 2026-10-13).

## Saídas

- **Bruto (raw/):** `route-views.saopaulo/updates.{AAAAMMDD}.{HHMM}.bz2`
- **Normalizado (normalized/):** `summary/bgp_stability.json.gz`, `summary/bgp_stability_manifest.json`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `period` | dict | Janela analisada (início, fim, dias, coletor, arquivos processados e ausentes, eventos vistos e contados). | — | bgp_stability → bgp_stability.json |
| `period.dedup_rate_pct` | float | % de eventos descartados como duplicados entre peers. | — | bgp_stability → bgp_stability.json |
| `as_stability[].asn` | int | ASN analisado. | — | bgp_stability → bgp_stability.json |
| `as_stability[].classification` | str | Classe de estabilidade atribuída ao AS pela taxa de eventos por prefixo por dia. | Faixas definidas em analysis/bgp_stability. | bgp_stability → bgp_stability.json |
| `as_stability[].daily/hourly` | dict | Contagem de eventos por dia e por hora (UTC). | — | bgp_stability → bgp_stability.json |
| `as_stability[].top_prefixes` | list[dict] | Prefixos com mais eventos para o AS. | — | bgp_stability → bgp_stability.json |
| `distribution.{v6,v4}` | dict | Distribuição de eventos por prefixo/dia (percentis p50–p99 e buckets). | — | bgp_stability → bgp_stability.json |
| `hourly_global` | dict | Série horária global de anúncios, retiradas e mudanças de atributo. | — | bgp_stability → bgp_stability.json |

## Limites

Um único coletor (peers latino-americanos): é a visão do route-views.saopaulo, não da Internet. Evento é variação observada, não necessariamente instabilidade de causa interna ao AS.

## Retenção

- **bruto:** 14 dias
- **normalizado:** 52 semanas

## Quem usa

- **Fontes derivadas:** `bgp_stability_deep`
- **Produtos:** `bgp_stability`
