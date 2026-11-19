<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Anatel — multas constituídas

`anatel_multas` · tipo **bruta** · ativa

Multas constituídas pela Anatel (arrecadação), uma linha por multa, de 2002 em diante: entidade, CNPJ, serviço, valor original, valor pago, saldo devedor atualizado e situação (Quitado, Devedor, Parcial). Aqui só as pessoas jurídicas de SCM, SMP, STFC e SeAC são consolidadas, por raiz do CNPJ e grupo de serviço.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.anatel_multas.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | diaria |
| Coleta hoje → alvo | semanal → mensal |
| Frescor máximo | 45d |
| Chaves | `cnpj` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/anatel_multas/` |

## Origem e licença

- **URL:** https://www.anatel.gov.br/dadosabertos/paineis_de_dados/arrecadacao/arrecadacao.zip
- **Formato:** ZIP com `multas_constituidas.csv` (UTF-8 com BOM, separador `;`, ~68,6 mil linhas, ~35 MB)
- **Licença:** Dados Abertos Anatel
- **Uso comercial:** `permitido`
- **Termos:** https://www.gov.br/anatel/pt-br/dados/dados-abertos
- **Evidência / ressalvas:** Endereço achado por padrão de nome e verificado em 2026-11-02 (HTTP 200, 5.267.946 bytes). O CPF já vem mascarado na fonte (`***.999.999-**`); essas linhas são descartadas e contadas. Uma requisição, com User-Agent identificado.

## Saídas

- **Bruto (raw/):** `summary/multas-AAAA-MM-DD.zip`
- **Normalizado (normalized/):** `summary/anatel_multas.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `empresas[].raiz / grupo / entidade / cnpjs / uf` | str | Raiz do CNPJ (8 dígitos, matriz e filiais), grupo de serviço (SCM, SMP, STFC ou SeAC), nome mais frequente, CNPJs completos e UF mais frequente. | Grupo pelo nome do serviço no arquivo; serviços fora dos quatro (radiodifusão, privados, radioamador) e multas sem serviço (a quem não tem outorga) ficam de fora. | — |
| `empresas[].multas / original / pago / saldo / situacoes / anos` | int / float / dict | Número de multas, valor original, valor pago e saldo devedor atualizado (R$), multas por situação e por ano de aplicação. | Multa constituída não é condenação definitiva: pode estar em recurso, parcelada ou suspensa judicialmente. | — |
| `resumo / data_arquivo / sha256` | dict | Linhas lidas, pessoas físicas descartadas, linhas fora do escopo, empresas e multas consolidadas; data de modificação do arquivo na Anatel e seu hash. | — | — |

## Limites

Não traz a decisão final do processo nem o motivo da infração. Pessoa física não é publicada.

## Retenção

- **bruto:** 2 versões
- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `regulatorio`
