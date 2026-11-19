<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Anatel — reclamações de consumidores

`anatel_reclamacoes` · tipo **bruta** · ativa

Solicitações de consumidores registradas na Anatel (reclamações, denúncias, pedidos de informação...), agregadas pela própria Anatel por mês × município (IBGE) × canal × serviço × marca × assunto × problema, de 2015 em diante: `reclamacoes.csv` (2015 a 2020, legado) e `reclamacoes_contexto.csv` (2020 em diante). Não há texto livre nem dado de quem reclamou.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.anatel_reclamacoes.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | mensal |
| Coleta hoje → alvo | semanal → mensal |
| Frescor máximo | 45d |
| Chaves | `ibge`, `uf` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/anatel_reclamacoes/` |

## Origem e licença

- **URL:** https://www.anatel.gov.br/dadosabertos/paineis_de_dados/consumidor/consumidor_reclamacoes.zip
- **Formato:** ZIP com 2 CSVs (UTF-8 com BOM, separador `;`): `reclamacoes_contexto.csv` (8,3 milhões de linhas, 1,5 GB) e `reclamacoes.csv` (16 milhões, 2,7 GB); 355.770.452 bytes o zip
- **Licença:** Dados Abertos Anatel
- **Uso comercial:** `permitido`
- **Termos:** https://www.gov.br/anatel/pt-br/dados/dados-abertos
- **Evidência / ressalvas:** Endereço verificado em 2026-11-06 (HTTP 200, last-modified 2026-10-13). Termos lidos em 2026-11-02 (licença aberta, crédito à fonte). O `robots.txt` do anatel.gov.br respondeu 423 (Locked) em 2026-11-06, sem regra legível; uma requisição por execução, com User-Agent identificado. Leitura em fluxo (~3 min, ~310 MB de memória medidos). Os dois arquivos se sobrepõem em 2020: vale o `contexto` e o legado só antes do primeiro mês dele (2020-01).

## Saídas

- **Bruto (raw/):** `summary/reclamacoes-AAAA-MM-DD.zip`
- **Normalizado (normalized/):** `summary/anatel_reclamacoes.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `marcas[]` | lista | Reclamações (tipo Reclamação) por marca × serviço × ano, com os municípios distintos. A marca é maiúscula, como o consumidor a escolheu. | Outros tipos de solicitação (denúncia, pedido de informação, elogio...) entram só em `por_mes`. 'NÃO LOCALIZEI A MINHA EMPRESA' e 'OUTROS' não identificam ninguém. | — |
| `por_mes[] / uf[] / assuntos[] / marca_assuntos[] / marca_mensal[]` | lista | Totais nacionais por mês × serviço × tipo, por UF × serviço × ano, por assunto (só do `contexto`, de 2020 em diante, porque a taxonomia mudou) e por marca × assunto e marca × mês (últimos 3 anos). | — | — |
| `municipios[ibge].itens[]` | lista | Reclamações por ano × serviço × marca nos últimos 3 anos da fonte, por município. | — | — |
| `resumo / data_arquivo / sha256` | dict | Linhas e solicitações de cada arquivo, mês inicial e final, data de extração, marcas e municípios; data de modificação do arquivo na Anatel e seu hash. | — | — |

## Limites

A fonte identifica a empresa pelo nome da marca, não pelo CNPJ. Reclamação não é prova de falha da empresa. Assuntos antes de 2020 não são comparáveis com os de depois.

## Retenção

- **bruto:** 2 versões
- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `qualidade`
