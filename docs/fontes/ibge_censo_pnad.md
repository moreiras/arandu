<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# População, domicílios e uso de internet (IBGE, Censo 2022 e PNAD Contínua)

`ibge_censo_pnad` · tipo **bruta** · ativa

População, área e domicílios particulares permanentes ocupados por município (Censo 2022, tabelas SIDRA 4714 e 4712), população estimada por município (Estimativas de População, tabela 6579) e domicílios com e sem utilização de internet por UF (PNAD Contínua anual, tabela 7307, com a série de domicílios de todos os anos). Denominador da penetração de banda larga e do mercado não visto.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.ibge_censo_pnad.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | anual |
| Coleta hoje → alvo | semanal → mensal |
| Frescor máximo | 400d |
| Chaves | `ibge`, `uf` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/ibge_sidra/` |

## Origem e licença

- **URL:** https://apisidra.ibge.gov.br/values
- **Formato:** JSON da API SIDRA (cabeçalho como primeiro elemento; valores em texto)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Termos:** https://www.ibge.gov.br/acesso-informacao/institucional/termo-de-uso.html
- **Evidência / ressalvas:** Dados abertos do IBGE; a página de termos respondeu HTTP 403 em 2026-10-31, então a licença não foi lida. Citar "IBGE" como fonte.

## Saídas

- **Bruto (raw/):** `summary/ibge-sidra-{tabela}-{ano}.json.gz`
- **Normalizado (normalized/):** `summary/ibge_municipios.json.gz`, `summary/ibge_taxa_internet.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `municipios[ibge].populacao / area_km2` | int / float | População residente e área da unidade territorial no Censo 2022. | Censo de 2022 (não é estimativa anual); município sem valor fica sem o campo. | — |
| `municipios[ibge].populacao_estimada` | int | População residente estimada pelo IBGE em 1º de julho do ano mais recente (tabela 6579), calculada a partir do Censo 2022. | Estimativa oficial; cobre município criado depois do Censo (que não tem os demais campos). | — |
| `municipios[ibge].domicilios / moradores` | int | Domicílios particulares permanentes OCUPADOS e seus moradores (Censo 2022). | Não inclui domicílios coletivos, de uso ocasional nem vagos. | — |
| `ufs[uf].domicilios_mil / com_internet_mil / taxa` | float | Domicílios (mil) e os em que havia utilização de internet; taxa = com internet ÷ total, por UF (PNAD). | Estimativa amostral. "Utilização de internet" inclui quem usa só o celular; não é banda larga fixa. | — |
| `ufs[uf].domicilios_mil_por_ano` | dict | Domicílios (mil) da UF na PNAD em cada ano da tabela; a razão entre o ano atual e o do Censo projeta os domicílios municipais. | Estimativa amostral; a definição de domicílio da PNAD não é idêntica à do Censo. | — |
| `ufs[uf].cv_domicilios_pct` | float | Coeficiente de variação da estimativa de domicílios da UF. | — | — |

## Limites

O Censo é de 2022, a PNAD do ano mais recente (2025 na coleta de 2026-10) e a população estimada de 2026: idades diferentes. A taxa de internet é por UF, não por município. Domicílio e acesso não são a mesma unidade (um domicílio pode ter vários acessos).

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `consumidor`, `demanda_oferta`, `erbs`, `penetracao`, `qualidade`, `regulatorio`

## Pendências (nao_verificado)

- Licença e termos de uso do IBGE (página de termos inacessível por HTTP 403); consulta jurídica em aberto.
