<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Cabos submarinos (TeleGeography)

`telegeography_cables` · tipo **bruta** · ativa

Cabos submarinos e pontos de aterragem do Submarine Cable Map (API v3).

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.telegeography_cables.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | usar_ultima_valida |
| Cadência (origem atualiza) | irregular |
| Coleta hoje → alvo | semanal → mensal |
| Frescor máximo | 45d |
| Chaves | `cabo`, `pais`, `ponto` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/telegeography/` |

## Origem e licença

- **URL:** https://www.submarinecablemap.com/api/v3/
- **Formato:** JSON/GeoJSON
- **Licença:** CC BY-SA 4.0 (conforme declarado no código do coletor)
- **Uso comercial:** `restrito`
- **Evidência / ressalvas:** O código do coletor declara CC BY-SA 4.0 com atribuição obrigatória e mantida na UI (mapTheme.ts). Share-alike: obras derivadas da base herdam a licença. Não verificado na origem (site é uma SPA sem texto estático em 2026-10-13).

## Saídas

- **Normalizado (normalized/):** `summary/telegeography_cables.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `cables[].name / id` | str | Nome e identificador do cabo. | — | mapas_infraestrutura → maps/submarine_cables.geojson |
| `cables[].length / owners / rfs_year / is_planned` | str\|int\|bool | Extensão, proprietários, ano de entrada em serviço e se é planejado. | — | mapas_infraestrutura → maps/submarine_cables.geojson |
| `cables[].landing_countries` | list[str] | Países de aterragem. | — | mapas_infraestrutura → maps/submarine_cables.geojson |
| `landing_points[]` | dict | Pontos de aterragem (nome, id, geometria). | — | mapas_infraestrutura → maps/submarine_landing_points.geojson |

## Limites

Mapa de referência, não registro oficial; traçado esquemático. Atribuição à TeleGeography obrigatória.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `mapas_infraestrutura`

## Pendências (nao_verificado)

- Confirmar a licença (CC BY-SA 4.0?) diretamente na TeleGeography e as implicações de share-alike para a camada publicada.
