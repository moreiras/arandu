<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Geolocalização dos prefixos vistos nos IXPs (DB-IP City Lite)

`global_prefix_geo` · tipo **derivada** · ativa

Para cada prefixo único visto em qualquer IXP do IX.br registra os IXPs onde apareceu, o ASN originador e a geolocalização DB-IP.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.global_prefix_geo.enrich` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | mensal |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 8d |
| Chaves | `prefixo`, `asn`, `ixp`, `ponto` |
| Entradas | `prefix_geo` |
| Amostra de teste | `tests/fixtures/raw/dbip/` |

## Origem e licença

- **URL:** https://download.db-ip.com/free/dbip-city-lite-{AAAA-MM}.mmdb.gz
- **Formato:** MMDB (DB-IP City Lite, mensal)
- **Licença:** CC BY 4.0 (DB-IP); dados do GeoNames sob CC BY
- **Uso comercial:** `permitido`
- **Termos:** https://db-ip.com/db/lite.php
- **Evidência / ressalvas:** Lido em 2026-10-31: "licensed under a Creative Commons Attribution 4.0 International License"; atribuição obrigatória, com link para db-ip.com nas páginas que exibem resultados da base ("IP Geolocation by DB-IP") e atribuição ao GeoNames. A cláusula que proíbe oferecer API de geolocalização vale só para a licença paga, mas o Arandurapé não expõe consulta por IP ou bloco. Sem chave de licença. Snapshot gerado com o GeoLite2 (MaxMind) guarda valores derivados dele.

## Saídas

- **Normalizado (normalized/):** `summary/geo_global_prefixes.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `prefixes[prefix].ixps_seen` | list[str] | IXPs do IX.br onde o prefixo foi visto. | — | mapas_prefixos → maps/global_prefixes.geojson |
| `prefixes[prefix].origin_asn` | int | ASN originador (do primeiro IXP em que o prefixo apareceu). | Se houver conflito de origem entre IXPs, vale o primeiro. | mapas_prefixos → maps/global_prefixes.geojson |
| `prefixes[prefix].lat / lon / city / country / uf` | float\|str | Posição segundo o DB-IP (centroide de cidade). | — | mapas_prefixos → maps/global_prefixes.geojson |
| `geolocated / unknown` | int | Prefixos com e sem geolocalização. | — | — |

## Limites

Mesmas limitações de prefix_geo. Depende dos normalizados por IXP (etapa bgp_ixp), por isso roda depois de products.bgp_routes.build.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `mapas_prefixos`

## Pendências (nao_verificado)

- Ver prefix_geo.
