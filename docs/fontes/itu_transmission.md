<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Enlaces terrestres de transmissão (ITU BBmaps)

`itu_transmission` · tipo **bruta** · ativa

Geometrias de fibra/micro-ondas do Transmission Networks Geocatalogue da ITU (BBmaps), via WFS, camada global.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.itu_transmission.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | usar_ultima_valida |
| Cadência (origem atualiza) | irregular |
| Coleta hoje → alvo | semanal → mensal |
| Frescor máximo | 45d |
| Chaves | `ponto` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/itu/` |

## Origem e licença

- **URL:** https://bbmaps.itu.int/geoserver/itu-geocatalogue/wfs
- **Formato:** WFS/GeoJSON
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** Sem autenticação; termos de uso do ITU BBmaps não localizados (bbmaps.itu.int/bbmaps/ não retorna texto estático em 2026-10-13).

## Saídas

- **Normalizado (normalized/):** `summary/itu_transmission.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `features[].geometry` | GeoJSON | Traçado do enlace (LineString/MultiLineString). | — | mapas_infraestrutura → maps/itu_transmission.geojson |
| `features[].properties` | dict | Atributos do enlace conforme a ITU (operador, tipo, situação). | — | mapas_infraestrutura → maps/itu_transmission.geojson |
| `status_counts` | dict | Contagem de enlaces por situação (Operational, Planned, Under Construction…). | Há variações de grafia na origem (ex.: 'Under construction' e 'Under Construction'). | — |

## Limites

Cobertura heterogênea e declarada por administrações; não indica propriedade nem capacidade. Dado muda pouco.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `mapas_infraestrutura`

## Pendências (nao_verificado)

- Termos de uso do ITU BBmaps não localizados.
