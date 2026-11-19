<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Anatel — satélites com direito de exploração

`anatel_satelites` · tipo **bruta** · ativa

Direitos de exploração de satélite no Brasil (operadora, satélite, posição orbital, banda, tipo nacional ou estrangeiro, status e validade), constelações de órbita não geoestacionária (NGEO, como as de órbita baixa) e satélites em operação comercial.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.anatel_satelites.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | diaria |
| Coleta hoje → alvo | semanal → mensal |
| Frescor máximo | 45d |
| Chaves | `cnpj` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/anatel_satelites/` |

## Origem e licença

- **URL:** https://www.anatel.gov.br/dadosabertos/paineis_de_dados/espectro_e_orbita/satelites.zip
- **Formato:** ZIP com 7 CSVs (UTF-8 com BOM, separador `;`); lidos os de direitos (123 linhas), de constelações NGEO (73) e de satélites em operação comercial (55)
- **Licença:** Dados Abertos Anatel
- **Uso comercial:** `permitido`
- **Termos:** https://www.gov.br/anatel/pt-br/dados/dados-abertos
- **Evidência / ressalvas:** Endereço achado por padrão de nome e verificado em 2026-11-02 (HTTP 200, 49.431 bytes). Uma requisição, com User-Agent identificado.

## Saídas

- **Bruto (raw/):** `summary/satelites-AAAA-MM-DD.zip`
- **Normalizado (normalized/):** `summary/anatel_satelites.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `direitos[].operadora / satelite / codigo / posicao / banda / tipo / status` | str | Operadora, satélite, código do direito, posição orbital, banda, tipo (Brasileiro ou Estrangeiro) e status do direito. | — | — |
| `direitos[].lancamento / validade / prorrogado` | data / bool | Data de lançamento, validade do direito e se foi prorrogado. | — | — |
| `ngeo[] / operando[]` | lista | Constelações NGEO (prestadora, CNPJ, objeto comercial, órbita, planos e satélites da constelação) e satélites em operação comercial. | CNPJ só nas constelações NGEO (prestadora no Brasil); nos direitos não há CNPJ. | — |
| `resumo / data_arquivo / sha256` | dict | Linhas lidas por tabela; data de modificação do arquivo na Anatel e seu hash. | — | — |

## Limites

Direito concedido não é capacidade em uso nem número de assinantes. Muitas operadoras são estrangeiras e não se ligam aos grupos do SICI.

## Retenção

- **bruto:** 2 versões
- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `regulatorio`
