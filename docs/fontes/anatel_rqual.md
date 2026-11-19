<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Anatel — indicadores de qualidade (RQUAL)

`anatel_rqual` · tipo **bruta** · ativa

Indicadores de qualidade do Regulamento de Qualidade (RQUAL) apurados pela Anatel desde 2022, um resultado por mês × município × prestadora × serviço × indicador: banda larga fixa, telefonia fixa e telefonia móvel, com 31 indicadores (conexão e queda de chamadas, velocidade, latência, variação de latência, perda de pacotes, disponibilidade, prazos, medições da EAQ em 3G/4G/5G e Wi-Fi 2,4/5 GHz), número de coletores e medidas, erro amostral, intervalo de confiança e os valores de referência da Anatel. Cobre só as grandes prestadoras de cada serviço.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.anatel_rqual.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | mensal |
| Coleta hoje → alvo | semanal → mensal |
| Frescor máximo | 45d |
| Chaves | `ibge`, `uf` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/anatel_rqual/` |

## Origem e licença

- **URL:** https://www.anatel.gov.br/dadosabertos/paineis_de_dados/qualidade/indicadores_rqual.zip
- **Formato:** ZIP com `Tabela_CSV_Indicadores_RQUAL.csv` (UTF-8 com BOM, separador `;`, 21 colunas, ~18 milhões de linhas, ~2,7 GB descompactado; 264.754.163 bytes o zip)
- **Licença:** Dados Abertos Anatel
- **Uso comercial:** `permitido`
- **Termos:** https://www.gov.br/anatel/pt-br/dados/dados-abertos
- **Evidência / ressalvas:** Endereço verificado em 2026-11-06 (HTTP 200, last-modified 2026-11-06). Termos lidos em 2026-11-02 (Plano de Dados Abertos da Anatel, Decreto 8.777/2016: licença aberta, crédito à fonte). O `robots.txt` do anatel.gov.br respondeu 423 (Locked) em 2026-11-06, sem regra de exclusão legível; o arquivo é o publicado nos painéis de dados abertos, e a coleta é uma requisição por execução, com User-Agent identificado. Leitura em fluxo (2 min, ~1,9 GB de memória de pico medidos).

## Saídas

- **Bruto (raw/):** `summary/rqual-AAAA-MM-DD.zip`
- **Normalizado (normalized/):** `summary/anatel_rqual.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `indicadores[] / prestadoras[]` | lista | Indicadores (serviço, código, descrição, tipo IQS ou informativo, grupo, unidade, valores de referência superior e inferior da Anatel) e prestadoras com o número de municípios medidos. | Os valores de referência são os mais frequentes no arquivo para o indicador; o sentido de 'melhor' depende do indicador e não é interpretado. | — |
| `nacional[]` | lista | Por serviço × prestadora × indicador × mês, municípios medidos, medidas, média simples, média ponderada pelo número de medidas e mediana dos municípios. | Só resultados numéricos; NA, NO e NI são contados em `resumo.sem_valor` (o arquivo não documenta o significado). Não é o desempenho da empresa para um cliente. | — |
| `uf[]` | lista | O mesmo por UF e ano (sem mediana). | — | — |
| `municipios[ibge].itens[]` | lista | O último resultado numérico de cada serviço × prestadora × indicador no município, com mês, medidas, coletores, erro amostral, intervalo e a coluna Estatística da fonte (SIM/NÃO). | Resultado de poucas medidas é incerto; o erro amostral e o intervalo acompanham o valor. | — |
| `resumo / data_arquivo / sha256` | dict | Linhas lidas, resultados numéricos, sem valor, municípios, primeiro e último mês; data de modificação do arquivo na Anatel e seu hash. | — | — |

## Limites

Só as grandes prestadoras (13 na banda larga fixa, 7 na telefonia fixa e 4 na móvel em 2026-11). A fonte identifica a empresa pelo nome, não pelo CNPJ. Sem ranking nem veredito.

## Retenção

- **bruto:** 2 versões
- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `qualidade`
