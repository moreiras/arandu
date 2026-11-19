<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Anatel — estações do SMP licenciadas (ERBs)

`anatel_erbs` · tipo **bruta** · ativa

Estações do Serviço Móvel Pessoal licenciadas na Anatel: uma linha por estação × setor × frequência no arquivo original (3,3 milhões de linhas), consolidadas aqui em uma linha por estação licenciada (~114 mil), com operadora, município, posição, gerações (2G a 5G), faixas, infraestrutura e ano do primeiro licenciamento. É cadastro de licenciamento: não diz que a estação está em operação, nem a cobertura.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.anatel_erbs.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | mensal |
| Coleta hoje → alvo | semanal → mensal |
| Frescor máximo | 45d |
| Chaves | `ibge`, `cnpj` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/anatel_erbs/` |

## Origem e licença

- **URL:** https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/estacoes_smp.zip
- **Formato:** ZIP com um CSV (UTF-8 com BOM, separador `;`, 41 colunas, ~995 MB descomprimido)
- **Licença:** Dados Abertos Anatel
- **Uso comercial:** `permitido`
- **Termos:** https://www.gov.br/anatel/pt-br/dados/dados-abertos
- **Evidência / ressalvas:** Endereço verificado em 2026-11-02 (mesmo padrão do `anatel_smp`; o dataset "Estações licenciadas" do dados.gov.br aponta para a família `paineis_de_dados/outorga_e_licenciamento`). O arquivo `estacoes_licenciadas.zip` (225 MB) é outro: cobre rádio-enlaces e outros serviços, sem as estações do SMP. Uma requisição, com User-Agent identificado.

## Saídas

- **Bruto (raw/):** `summary/estacoes_smp-AAAA-MM-DD.zip`
- **Normalizado (normalized/):** `summary/anatel_erbs.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `estacoes[].fistel / estacao` | str | Número Fistel e número da estação, que juntos identificam a estação licenciada. | Cadastro de licenciamento, não torre física: a mesma torre pode ter mais de um número de estação. | — |
| `estacoes[].marca / entidade / cnpj` | str | Operadora (marca, razão social e CNPJ). | A coluna de CNPJ vem em branco em ~44% das linhas; o CNPJ é o da própria estação quando existe, senão o mais frequente da marca no arquivo. | — |
| `estacoes[].ibge / uf` | str | Código IBGE do município e UF da estação. | O código só vem em uma de cada três cópias de cada registro; a consolidação usa o valor preenchido. Estação sem nenhum valor fica com `ibge: null`. | — |
| `estacoes[].lat / lon / posicao_variavel` | float / bool | Posição da estação (a mais frequente entre as suas linhas). | Fora do Brasil ou ausente vira null (contado em `resumo`); `posicao_variavel` marca as estações cuja posição muda entre linhas. | — |
| `estacoes[].geracoes / tecnologias / tipo_5g / faixas / setores / combinacoes` | lista | Gerações (2G a 5G), tecnologias (GSM, WCDMA, LTE, NR), tipo do 5G (SA, NSA, SA-NSA), faixas em MHz, número de setores e de combinações tecnologia × frequência × setor. | Licenciado, não necessariamente ativo. | — |
| `estacoes[].infra / primeira_licenca / linhas` | str / int | Tipo de infraestrutura física (Rooftop, Greenfield, Indoor...), ano do primeiro licenciamento e linhas do arquivo original que a compõem. | — | — |
| `resumo / data_arquivo / sha256` | dict | Linhas lidas, estações, sem posição, fora do Brasil, posição variável, sem IBGE; data de modificação do arquivo na Anatel e seu hash. | — | — |

## Limites

Não há cobertura (%): só o cadastro de estações licenciadas. Um município sem estação licenciada pode ser atendido por estação de município vizinho. O arquivo não traz estações de rádio-enlace nem de operadoras de banda larga fixa.

## Retenção

- **bruto:** 2 versões
- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `erbs`

## Pendências (nao_verificado)

- Arquivo aberto de cobertura 4G/5G (% por município) não localizado em 2026-11-02; o painel "Estações do SMP" (informacoes.anatel.gov.br) é aplicação, sem download.
