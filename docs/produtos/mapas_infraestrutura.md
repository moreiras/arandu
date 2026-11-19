<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Camadas de infraestrutura (cabos, transmissão, rodovias)

`mapas_infraestrutura` · produto

GeoJSON das camadas de fundo de infraestrutura: cabos submarinos e aterragens, enlaces ITU, linhas de transmissão e rodovias.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `publish.snapshot_builder` |
| Chaves de junção | `ponto`, `cabo` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [telegeography_cables](../fontes/telegeography_cables.md) — uso comercial: `restrito`
- fonte [itu_transmission](../fontes/itu_transmission.md) — uso comercial: `nao_verificado`
- fonte [aneel_sigel_transmission](../fontes/aneel_sigel_transmission.md) — uso comercial: `nao_verificado`
- fonte [ibge_bc250_rodovias](../fontes/ibge_bc250_rodovias.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `maps/submarine_cables.geojson`, `maps/submarine_landing_points.geojson`, `maps/itu_transmission.geojson`, `maps/power_transmission_lines.geojson`, `maps/ibge_rodovias.geojson`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `type` | str | Tipo GeoJSON. | — | mapas_infraestrutura → maps/submarine_cables.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | mapas_infraestrutura → maps/submarine_cables.geojson#snapshot_date |
| `source` | str | Origem do dado exibida como atribuição. | — | mapas_infraestrutura → maps/submarine_cables.geojson#source |
| `features` | list | Geometrias da camada com as propriedades de cada elemento. | — | mapas_infraestrutura → maps/submarine_cables.geojson#features |
| `type` | str | Tipo GeoJSON. | — | mapas_infraestrutura → maps/submarine_landing_points.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | mapas_infraestrutura → maps/submarine_landing_points.geojson#snapshot_date |
| `source` | str | Origem do dado exibida como atribuição. | — | mapas_infraestrutura → maps/submarine_landing_points.geojson#source |
| `features` | list | Geometrias da camada com as propriedades de cada elemento. | — | mapas_infraestrutura → maps/submarine_landing_points.geojson#features |
| `type` | str | Tipo GeoJSON. | — | mapas_infraestrutura → maps/itu_transmission.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | mapas_infraestrutura → maps/itu_transmission.geojson#snapshot_date |
| `source` | str | Origem do dado exibida como atribuição. | — | mapas_infraestrutura → maps/itu_transmission.geojson#source |
| `features` | list | Geometrias da camada com as propriedades de cada elemento. | — | mapas_infraestrutura → maps/itu_transmission.geojson#features |
| `type` | str | Tipo GeoJSON. | — | mapas_infraestrutura → maps/power_transmission_lines.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | mapas_infraestrutura → maps/power_transmission_lines.geojson#snapshot_date |
| `source` | str | Origem do dado exibida como atribuição. | — | mapas_infraestrutura → maps/power_transmission_lines.geojson#source |
| `features` | list | Geometrias da camada com as propriedades de cada elemento. | — | mapas_infraestrutura → maps/power_transmission_lines.geojson#features |
| `type` | str | Tipo GeoJSON. | — | mapas_infraestrutura → maps/ibge_rodovias.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | mapas_infraestrutura → maps/ibge_rodovias.geojson#snapshot_date |
| `source` | str | Origem do dado exibida como atribuição. | — | mapas_infraestrutura → maps/ibge_rodovias.geojson#source |
| `features` | list | Geometrias da camada com as propriedades de cada elemento. | — | mapas_infraestrutura → maps/ibge_rodovias.geojson#features |
| `attribution` | str | Atribuição obrigatória à TeleGeography (CC BY-SA). | — | mapas_infraestrutura → maps/submarine_cables.geojson#attribution |
| `attribution` | str | Atribuição obrigatória à TeleGeography (CC BY-SA). | — | mapas_infraestrutura → maps/submarine_landing_points.geojson#attribution |

## Limites

Atribuição obrigatória (TeleGeography CC BY-SA); camadas não indicam fibra em linhas elétricas nem rodovias.
