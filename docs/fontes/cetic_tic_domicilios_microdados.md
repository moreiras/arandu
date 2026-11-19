<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# TIC Domicílios — microdados (Cetic.br), estimativas por UF

`cetic_tic_domicilios_microdados` · tipo **bruta** · ativa

Base de microdados de domicílios da pesquisa TIC Domicílios (edição vigente; ~27 mil domicílios, desidentificada, com a UF e 200 pesos de réplica). Só agregados saem dela: proporção, total e erro-padrão por UF, região e Brasil de três indicadores (acesso à Internet, computador e banda larga fixa). É estimativa do Arandurapé, não número do Cetic.br.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.cetic_tic_domicilios_microdados.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | anual |
| Coleta hoje → alvo | semanal → mensal |
| Frescor máximo | 400d |
| Chaves | `uf` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/cetic/` |

## Origem e licença

- **URL:** https://cetic.br/pt/pesquisa/domicilios/microdados/
- **Formato:** CSV (Latin-1, separador `;`, vírgula decimal), uma linha por domicílio, com PESO e REP1 a REP200
- **Licença:** CC BY 4.0
- **Uso comercial:** `permitido`
- **Termos:** https://creativecommons.org/licenses/by/4.0/deed.pt_BR
- **Evidência / ressalvas:** Citar "Cetic.br|NIC.br, TIC Domicílios AAAA (microdados)" (CC BY 4.0). Base desidentificada e de acesso público (sem Termo de Acesso); microdados restritos estão fora do escopo. A base de domicílios fica só no bruto e nunca é publicada. Sem API nem URL estável: o coletor descobre o link na página de microdados. Uma requisição para a página e uma para o CSV (36 MB), com pausa e User-Agent identificado.

## Saídas

- **Bruto (raw/):** `summary/tic_domicilios_AAAA_domicilios_base_de_microdados_v1.0.csv.gz`
- **Normalizado (normalized/):** `summary/cetic_tic_domicilios_uf.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `grupos[BR | região | UF].indicadores[id].proporcao / erro_padrao / margem / cv` | float | Percentual de domicílios do grupo com a característica, erro-padrão em pontos percentuais, margem de erro de 95% (1,96 × erro-padrão) e coeficiente de variação. | Estimativa do Arandurapé: ponto pelo peso amostral e variância pelas 200 réplicas da base pública. A estimativa pontual coincide com a das tabelas oficiais; a margem oficial é de 1,08 a 1,14 vez a estimada aqui (validação no produto). Precisão "baixa" quando o CV passa de 30%. | — |
| `grupos[...].indicadores[id].total / total_erro_padrao` | int | Domicílios do grupo com a característica, estimados pelos pesos, e erro-padrão do total. | Estimativa expandida; não é contagem. | — |
| `grupos[...].n / domicilios / domicilios_se` | int | Domicílios entrevistados no grupo, domicílios estimados e erro-padrão. | Grupo com menos de 30 entrevistados é suprimido (`suprimido` no lugar dos números). | — |
| `indicadores[id].rotulo / definicao` | str | O que cada indicador mede e quais colunas da base o definem. | — | — |

## Limites

Estimativa amostral com 700 a 1.500 domicílios por UF: a margem de erro por UF é bem maior que a do Brasil e deve acompanhar o número. Não há município nem pessoa. As colunas usadas são A4 (acesso à Internet), A1_AGREG (computador) e A7_AGREG (banda larga fixa); a definição de domicílio e o ano de referência são os da pesquisa.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `cetic`, `demanda_oferta`

## Pendências (nao_verificado)

- Margem de erro própria 8% a 14% menor que a das tabelas oficiais; investigar com o Cetic.br se há uma regra de variância que a reproduza.
