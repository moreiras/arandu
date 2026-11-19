<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Linhas de transmissão de alta tensão (SIGEL/ANEEL)

`aneel_sigel_transmission` · tipo **bruta** · ativa

Linhas da rede básica nacional (ONS) do SIGEL/ANEEL via ArcGIS REST, com tensão e extensão extraídas por regex de campos de texto livre. Não informa presença de OPGW.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.aneel_sigel_transmission.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | usar_ultima_valida |
| Cadência (origem atualiza) | irregular |
| Coleta hoje → alvo | semanal → mensal |
| Frescor máximo | 45d |
| Chaves | `ponto` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/aneel_sigel/` |

## Origem e licença

- **URL:** https://sigel.aneel.gov.br/arcgis/rest/services/PORTAL/Transmiss%C3%A3o/MapServer/1
- **Formato:** ArcGIS REST (Esri JSON → GeoJSON)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Termos:** https://dadosabertos.aneel.gov.br/
- **Evidência / ressalvas:** Portal de Dados Abertos da ANEEL declara dados sob 'licença aberta' em geral (2026-10-13); a camada SIGEL específica não foi verificada.

## Saídas

- **Normalizado (normalized/):** `summary/aneel_transmission.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `features[].geometry` | GeoJSON | Traçado da linha. | Vértices duplicados em ciclo no serviço de origem são deduplicados. | mapas_infraestrutura → maps/power_transmission_lines.geojson |
| `features[].properties.Name` | str | Descrição da linha em texto livre (ex.: 'Linha LT 230 kV A / B C 1 UF'). | — | mapas_infraestrutura → maps/power_transmission_lines.geojson |
| `features[].properties.tensao_kv / extensao_km` | float | Tensão e extensão extraídas por regex de Name/PopupInfo (best-effort). | Nulos quando o parsing falha. | mapas_infraestrutura → maps/power_transmission_lines.geojson |

## Limites

Não indica OPGW (fibra no cabo para-raios); só geometria e atributos. Não cobre subtransmissão/distribuição.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `mapas_infraestrutura`

## Pendências (nao_verificado)

- Licença/termos da camada SIGEL PORTAL/Transmissão.
