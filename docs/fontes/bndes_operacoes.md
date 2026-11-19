<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# BNDES — operações de financiamento (não automáticas) a empresas de telecom

`bndes_operacoes` · tipo **bruta** · ativa

Operações de financiamento direto do BNDES (conjunto "operacoes-financiamento", recurso "Operações não automáticas", CSV com CNPJ completo e município IBGE). Guarda só as operações de clientes cujo CNPJ básico está no universo de telecom (outorgas SCM, SMP, STFC e SeAC, SICI e estabelecimentos de CNAE 61 da Receita). Por operação: contrato, data, valor contratado e desembolsado, produto, instrumento, forma de apoio, UF, município (IBGE), CNAE, porte, situação e a descrição curta do projeto.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.bndes_operacoes.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | mensal |
| Coleta hoje → alvo | mensal → mensal |
| Frescor máximo | 60d |
| Chaves | `cnpj`, `ibge` |
| Entradas | `anatel_scm`, `anatel_smp`, `anatel_stfc`, `anatel_seac`, `anatel_sici` |
| Amostra de teste | `tests/fixtures/raw/bndes_operacoes/` |

## Origem e licença

- **URL:** https://dadosabertos.bndes.gov.br/dataset/operacoes-financiamento
- **Formato:** CSV latin-1 (`;`, aspas, cabeçalho, 35 colunas, ~20 MB) via CKAN (`package_show`); decimal com vírgula
- **Licença:** ODbL (Open Data Commons Open Database License), com atribuição ao BNDES
- **Uso comercial:** `permitido`
- **Termos:** https://dadosabertos.bndes.gov.br/
- **Evidência / ressalvas:** Licença lida no próprio metadado do conjunto (CKAN, `license_title`) em 2026-11-08; o texto integral da ODbL e a cláusula de compartilhamento pela mesma licença (share-alike) valem para base derivada: avaliar na publicação aberta. Conferido em 2026-11-08 contra o arquivo real (23.896 linhas; 59 CNPJs de telecom, 375 operações no recorte local). O recurso "Operações indiretas automáticas" (1,2 GB) NÃO é coletado: o CNPJ do cliente vem mascarado e não se liga a uma operadora.

## Saídas

- **Normalizado (normalized/):** `summary/bndes_operacoes.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `operacoes[cnpj14][]` | lista | Operações do cliente (CNPJ de 14 dígitos, matriz ou filial) com contrato, data, valor contratado e desembolsado (R$), produto, instrumento financeiro, forma de apoio, UF, município IBGE, CNAE, porte, situação e descrição curta do projeto. | Valores nominais da data da contratação, sem correção. Só operações diretas e não automáticas (o recorte da fonte). | — |
| `dump_reference / linhas_lidas / operacoes_guardadas / cnpjs / universo_cnpjs_basicos` | dict | Data de modificação do conjunto no portal, linhas lidas, operações e CNPJs guardados e tamanho do universo. | — | — |

## Limites

Só as operações não automáticas (diretas); as indiretas automáticas (via banco credenciado), em volume maior, têm o CNPJ mascarado e ficam de fora. A operadora aparece só se o CNPJ básico estiver no universo de telecom.

## Retenção

- **normalizado:** 3 versões

## Quem usa

- **Produtos:** `financiamento_sancoes`

## Pendências (nao_verificado)

- Texto integral da ODbL (base derivada, share-alike) a avaliar na publicação aberta e na consulta jurídica.
