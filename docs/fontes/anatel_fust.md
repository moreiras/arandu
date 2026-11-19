<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Anatel — compromissos do FUST

`anatel_fust` · tipo **bruta** · ativa

Compromissos de aplicação dos recursos do Fundo de Universalização dos Serviços de Telecomunicações (FUST) registrados pela Anatel: conectividade de escolas públicas e de unidades básicas de saúde, redes de transporte em fibra, SMP 4G e atendimento de favelas, por município, com programa, edital, investimento previsto, prazo e situação (Atendido, A vencer, Em apuração). Não identifica a empresa executora.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.anatel_fust.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | diaria |
| Coleta hoje → alvo | semanal → mensal |
| Frescor máximo | 45d |
| Chaves | `ibge` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/anatel_fust/` |

## Origem e licença

- **URL:** https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acompanhamento_e_controle/fust.zip
- **Formato:** ZIP com 3 CSVs (UTF-8 com BOM, separador `;`); só `Base_FUST.csv` (41 colunas, ~21,6 mil linhas, ~9,5 MB) é lido
- **Licença:** Dados Abertos Anatel
- **Uso comercial:** `permitido`
- **Termos:** https://www.gov.br/anatel/pt-br/dados/dados-abertos
- **Evidência / ressalvas:** Endereço achado por padrão de nome e verificado em 2026-11-02 (HTTP 200, 971.969 bytes). O catálogo do dados.gov.br não responde a consulta automática. O mesmo zip traz `Base_SEI.csv` e `Base_SIGEC.csv` (ônus contratual do STFC), que não são lidos. Uma requisição, com User-Agent identificado.

## Saídas

- **Bruto (raw/):** `summary/fust-AAAA-MM-DD.zip`
- **Normalizado (normalized/):** `summary/anatel_fust.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `compromissos[].id / origem / tipo / programa` | str | Número da linha, edital ou projeto de origem (ex.: Edital nº 166/2024/MCOM, Projetos BNDES), tipo do compromisso (escolas, UBS, favelas, rede, SMP) e programa (ex.: 1.1 Conectividade para Escolas Públicas). | Espaços e tabulações normalizados; os códigos de programa vêm do arquivo. | — |
| `compromissos[].ibge / uf / municipio / nivel / base_ibge` | str | Município (7 primeiros dígitos de `COD_LOCALIDADE`), UF, nome, nível da obrigação (Município ou Localidade) e malha do IBGE usada (IBGE_2010 ou IBGE_2022). | Código de município de malha antiga pode não existir no cadastro atual do IBGE; o produto conta esses casos. | — |
| `compromissos[].status / prazo / investimento` | str / data / float | Situação registrada pela Anatel (Atendido, A vencer, Em apuração), prazo máximo e investimento total previsto em reais. | Investimento é o previsto, não o desembolsado. Valor em branco vira null. | — |
| `resumo / data_arquivo / sha256` | dict | Compromissos lidos, sem município, sem valor, contagem por situação; data de modificação do arquivo na Anatel e seu hash. | — | — |

## Limites

Não identifica a empresa executora nem o valor desembolsado. 'Em apuração' é a situação registrada pela Anatel, não inadimplência.

## Retenção

- **bruto:** 2 versões
- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `regulatorio`
