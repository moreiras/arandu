<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Consumidor.gov.br — reclamações finalizadas

`consumidor_gov` · tipo **bruta** · ativa

Reclamações finalizadas de consumidores no Consumidor.gov.br (Senacon, Ministério da Justiça e Segurança Pública), um arquivo mensal `finalizadas_AAAA-MM.zip` com todos os segmentos de mercado. O Arandurapé guarda só o segmento de operadoras de telecomunicações e só agregados (empresa × UF × cidade, empresa × assunto e empresa × grupo de problema): a linha original, que traz sexo e faixa etária de quem reclamou, é descartada na leitura.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.consumidor_gov.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | mensal |
| Coleta hoje → alvo | semanal → mensal |
| Frescor máximo | 50d |
| Chaves | `uf` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/consumidor_gov/` |

## Origem e licença

- **URL:** https://consumidor.gov.br/pages/publicacao/externo/publicacoes.json?indicadorTipoPublicacao=3
- **Formato:** JSON com a lista de publicações (nome do arquivo, código, tamanho) e, por `codigo`, o ZIP em `/pages/publicacao/externo/{codigo}/download`: um CSV por mês, UTF-8 com BOM, separador `;`, 19 colunas, CRLF; ~12 MB o zip e ~120 MB o CSV (~360 mil linhas, 27 mil de telecom em 2026-09)
- **Licença:** Dados abertos do Governo Federal (Consumidor.gov.br, Senacon); termos de uso do site
- **Uso comercial:** `permitido`
- **Termos:** https://consumidor.gov.br/pages/dadosabertos/externo/
- **Evidência / ressalvas:** Verificado em 2026-11-07: o `robots.txt` do consumidor.gov.br só proíbe /pages/usuario/, /pages/ticket/, /pages/administrativo/ e /pages/reclamacao/, e a coleta confere o robots antes de cada execução e aborta se ele proibir /pages/publicacao/. A lista só responde com o parâmetro `indicadorTipoPublicacao` (3 = arquivos mensais; 1 = boletins em PDF); o servidor devolve 504 às vezes (3 tentativas) e mistura codificações nos textos da lista (só nome, código e tamanho são usados). Uma requisição por vez, pausa de 1 s, User-Agent identificado. A primeira execução baixa 24 arquivos (~190 MB) e as seguintes só o mês novo (incremental pelo `codigo`). Série pública desde 2014; o Arandurapé usa os últimos 24 meses. O site não declara licença explícita para os dados abertos: a política de dados abertos do Governo Federal (Decreto 8.777/2016) e o crédito à fonte valem.

## Saídas

- **Bruto (raw/):** `summary/consumidor_gov/finalizadas_AAAA-MM.zip`
- **Normalizado (normalized/):** `summary/consumidor_gov.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `meses[AAAA-MM].cidades[]` | lista | Por empresa (nome fantasia) × UF × cidade (nome digitado) no mês (finalizadas, respondidas, avaliadas, resolvidas) e a soma e a contagem do tempo de resposta (dias) e da nota (1 a 5). | Só o segmento de operadoras de telecomunicações. Sexo, faixa etária, região e data da linha não são guardados. | — |
| `meses[AAAA-MM].assuntos[] / grupos[]` | lista | Reclamações do mês por empresa × assunto e por empresa × grupo de problema. | — | — |
| `meses[AAAA-MM].codigo / tamanho / resumo` | dict | Código da publicação (muda se o arquivo é republicado, o que dispara novo download), tamanho do zip e a contagem da leitura (linhas, linhas de telecom, segmentos, empresas, células). | — | — |
| `resumo` | dict | Meses cobertos, mês inicial e final, quantos arquivos foram baixados nesta execução e o total de reclamações de telecom. | — | — |

## Limites

Só reclamações finalizadas, só de empresas que aderiram à plataforma; não é o total de reclamações contra a empresa. A empresa vem pelo nome fantasia, não pelo CNPJ. A cidade é o nome digitado.

## Retenção

- **bruto:** 2 versões
- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `consumidor`
