<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Malha rodoviária (IBGE BC250)

`ibge_bc250_rodovias` · tipo **bruta** · ativa

Trechos rodoviários (camada rod_trecho_rodoviario_l) da Base Cartográfica Contínua 1:250.000 do IBGE, lidos do ZIP por HTTP Range (47 MB de 761 MB).

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.ibge_bc250_rodovias.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | irregular |
| Coleta hoje → alvo | semanal → mensal |
| Frescor máximo | 400d |
| Chaves | `ponto` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/ibge_bc250/` |

## Origem e licença

- **URL:** https://geoftp.ibge.gov.br/cartas_e_mapas/bases_cartograficas_continuas/bc250/versao2025/shapefiles/bc_250_shapefiles_2026_03_03.zip
- **Formato:** zip/shapefile (SIRGAS 2000)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** Política de dados abertos do IBGE não pôde ser lida (HTTP 403 em 2026-10-13).

## Saídas

- **Normalizado (normalized/):** `summary/ibge_rodovias.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `features[].geometry` | GeoJSON | Traçado do trecho rodoviário. | — | mapas_infraestrutura → maps/ibge_rodovias.geojson |
| `features[].properties.sigla` | str | Sigla da rodovia (ex.: BR-101). | — | mapas_infraestrutura → maps/ibge_rodovias.geojson |
| `features[].properties.jurisdicao / revestimen` | str | Jurisdição e revestimento do trecho. | 49% 'Desconhecida' em jurisdição (limitação da origem). | mapas_infraestrutura → maps/ibge_rodovias.geojson |

## Limites

Muda a cada ~2 anos; não indica fibra nem dutos, só a malha. URL traz a versão (bc_250_shapefiles_2026_03_03.zip): nova versão exige atualização do código.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `mapas_infraestrutura`

## Pendências (nao_verificado)

- Licença/termos de uso do IBGE (política de dados abertos).
