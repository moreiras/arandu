<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Pontos de intercâmbio físicos do IX.br (config/pix.yaml)

`curada_pix` · tipo **curada** · ativa

Localização física (nome, endereço, CEP, lat/lon) de cada PIX por localidade do IX.br; gerada por raspagem de old.ix.br/adesao e geocodificada, com correções manuais.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `config/pix.yaml` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | irregular |
| Coleta hoje → alvo | semanal → sob_demanda |
| Frescor máximo | 400d |
| Chaves | `ixp`, `ponto` |
| Entradas | `curada_ixps` |

## Origem e licença

- **URL:** —
- **Formato:** YAML mantido à mão em config/
- **Licença:** Curadoria do projeto (dados factuais; fontes citadas)
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** Fonte: https://old.ix.br/adesao/{code} (raspado por scripts/scrape_pix_locations.py); coordenadas via OSM/PeeringDB (ex.: AP, corrigido em 2026-09-28).

## Saídas


## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `pix[code][].name` | str | Nome do ponto (ex.: '[PIX RNP]'). | — | mapas_prefixos → /api/v1/map/pix |
| `pix[code][].address / cep` | str | Endereço e CEP do ponto. | Endereço de instalação, não de pessoa física. | mapas_prefixos → /api/v1/map/pix |
| `pix[code][].lat / lon` | float | Coordenadas do ponto. | Geocodificadas por OSM; podem ter sido corrigidas à mão. | mapas_prefixos → /api/v1/map/pix |

## Limites

Raspagem de página que pode mudar; já houve endereço repetido por engano (Macapá/Boa Vista).

## Retenção

- **normalizado:** git

## Quem usa

- **Produtos:** `area_influencia_ptt`, `mapas_prefixos`

## Pendências (nao_verificado)

- Licença/termos dos dados do IX.br e da raspagem de old.ix.br.
