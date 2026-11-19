<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Qualidade (RQUAL) e reclamações da Anatel

`qualidade` · produto

Indicadores de qualidade do RQUAL (série nacional por prestadora, por UF e o último resultado de cada município) e reclamações de consumidores na Anatel (por marca, serviço, UF, município e assunto), com a ligação prestadora e marca → CNPJ (tabela curada mais nome fantasia único, rotulada) e a taxa de reclamações por mil acessos do SICI onde há volume. Medido ou declarado, com fonte e período; sem ranking nem veredito.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.qualidade.build` |
| Chaves de junção | `ibge`, `cnpj` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [anatel_rqual](../fontes/anatel_rqual.md) — uso comercial: `permitido`
- fonte [anatel_reclamacoes](../fontes/anatel_reclamacoes.md) — uso comercial: `permitido`
- fonte [anatel_scm](../fontes/anatel_scm.md) — uso comercial: `permitido`
- fonte [anatel_smp](../fontes/anatel_smp.md) — uso comercial: `permitido`
- fonte [anatel_stfc](../fontes/anatel_stfc.md) — uso comercial: `permitido`
- fonte [anatel_seac](../fontes/anatel_seac.md) — uso comercial: `permitido`
- fonte [ibge_censo_pnad](../fontes/ibge_censo_pnad.md) — uso comercial: `nao_verificado`
- produto [sici](sici.md)

## Saídas

- **Publicado:** `qualidade/rqual.json.gz`, `qualidade/rqual_municipios/{UF}.json.gz`, `qualidade/reclamacoes.json.gz`, `qualidade/reclamacoes_municipios/{UF}.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `rqual.nacional[] / uf[]` | lista | Por serviço × prestadora × indicador, por mês (nacional) ou por ano (UF), municípios medidos, medidas, média simples, média ponderada pelas medidas e (nacional) mediana dos municípios. | Só resultados numéricos; não é o desempenho da empresa para um cliente. Sem ranking. | qualidade → qualidade/rqual.json.gz#nacional; qualidade → qualidade/rqual.json.gz#uf |
| `rqual.indicadores[] / prestadoras[] / casamento` | lista | Indicadores com unidade e valores de referência da Anatel; prestadoras cobertas com as raízes de CNPJ ligadas (casamento curada ou automático) e as que ficaram sem CNPJ. | Cobre só as grandes prestadoras; a ausência de uma empresa não diz nada sobre ela. | qualidade → qualidade/rqual.json.gz#indicadores; qualidade → qualidade/rqual.json.gz#prestadoras; qualidade → qualidade/rqual.json.gz#casamento |
| `rqual.municipios[ibge].itens[]` | lista | O último resultado de cada serviço × prestadora × indicador no município, com mês, medidas, coletores, erro amostral, intervalo e a coluna Estatística da fonte. | Resultado de poucas medidas é incerto; veja o erro amostral. | qualidade → qualidade/rqual_municipios/{UF}.json.gz#municipios |
| `rqual.limites / natureza / fonte / data_arquivo / leitura` | str | O que o dado é e não é, a data do arquivo na Anatel e a contagem da leitura. | — | qualidade → qualidade/rqual.json.gz#limites; qualidade → qualidade/rqual.json.gz#natureza; qualidade → qualidade/rqual.json.gz#fonte; qualidade → qualidade/rqual.json.gz#data_arquivo; qualidade → qualidade/rqual.json.gz#resumo |
| `reclamacoes.marcas[]` | lista | Reclamações por marca × serviço × ano, municípios distintos e as raízes de CNPJ ligadas à marca (vazio = sem CNPJ). | A ligação é curada (config/curada_marcas_operadoras.yaml) ou automática por nome fantasia único, nunca um palpite. Reclamação não é prova de falha da empresa. | qualidade → qualidade/reclamacoes.json.gz#marcas |
| `reclamacoes.taxas` | dict | Reclamações da janela de 12 meses por mil acessos do SICI (SCM e SMP), só com volume suficiente, e a regra e o mês de referência do SICI. | As duas bases têm períodos diferentes e a marca pode agrupar mais de um CNPJ; a regra e o motivo de cada taxa ausente acompanham o dado. | qualidade → qualidade/reclamacoes.json.gz#taxas |
| `reclamacoes.por_mes[] / uf[] / assuntos[] / marca_assuntos[] / casamento` | lista | Totais nacionais por mês, por UF e por assunto, assuntos por marca nos últimos 3 anos e a cobertura da ligação marca → CNPJ (% das reclamações com CNPJ). | — | qualidade → qualidade/reclamacoes.json.gz#por_mes; qualidade → qualidade/reclamacoes.json.gz#uf; qualidade → qualidade/reclamacoes.json.gz#assuntos; qualidade → qualidade/reclamacoes.json.gz#marca_assuntos; qualidade → qualidade/reclamacoes.json.gz#casamento |
| `reclamacoes.municipios[ibge].itens[]` | lista | Reclamações por ano × serviço × marca nos últimos 3 anos da fonte, com a população estimada do IBGE para a taxa por 100 mil habitantes. | — | qualidade → qualidade/reclamacoes_municipios/{UF}.json.gz#municipios |
| `reclamacoes.limites / natureza / fonte / data_arquivo / leitura` | str | O que o dado é e não é, a data do arquivo na Anatel e a contagem da leitura. | — | qualidade → qualidade/reclamacoes.json.gz#limites; qualidade → qualidade/reclamacoes.json.gz#natureza; qualidade → qualidade/reclamacoes.json.gz#fonte; qualidade → qualidade/reclamacoes.json.gz#data_arquivo; qualidade → qualidade/reclamacoes.json.gz#leitura |
| `snapshot_date / generated_at` | str | Data do snapshot e instante em que o arquivo foi gerado. | — | qualidade → qualidade/rqual.json.gz#snapshot_date; qualidade → qualidade/rqual.json.gz#generated_at; qualidade → qualidade/reclamacoes.json.gz#snapshot_date; qualidade → qualidade/reclamacoes.json.gz#generated_at |
| `municipios_uf` | dict | Índice código IBGE do município → UF, para a API achar a parte por UF dos municípios. | — | qualidade → qualidade/rqual.json.gz#municipios_uf; qualidade → qualidade/reclamacoes.json.gz#municipios_uf |
| `anos / url_fonte` | lista / str | Anos com reclamações na fonte e o endereço do arquivo da Anatel. | — | qualidade → qualidade/reclamacoes.json.gz#anos; qualidade → qualidade/reclamacoes.json.gz#url_fonte; qualidade → qualidade/rqual.json.gz#url_fonte |
| `uf / anos_municipio / fonte / natureza / data_arquivo / url_fonte / snapshot_date / generated_at` | str | Cabeçalho de cada parte por UF dos municípios (UF, anos cobertos, fonte, natureza do dado, data do arquivo na Anatel, endereço, data do snapshot e instante de geração). | — | qualidade → qualidade/rqual_municipios/{UF}.json.gz#uf; qualidade → qualidade/rqual_municipios/{UF}.json.gz#fonte; qualidade → qualidade/rqual_municipios/{UF}.json.gz#natureza; qualidade → qualidade/rqual_municipios/{UF}.json.gz#data_arquivo; qualidade → qualidade/rqual_municipios/{UF}.json.gz#url_fonte; qualidade → qualidade/rqual_municipios/{UF}.json.gz#snapshot_date; qualidade → qualidade/rqual_municipios/{UF}.json.gz#generated_at; qualidade → qualidade/reclamacoes_municipios/{UF}.json.gz#uf; qualidade → qualidade/reclamacoes_municipios/{UF}.json.gz#anos_municipio; qualidade → qualidade/reclamacoes_municipios/{UF}.json.gz#fonte; qualidade → qualidade/reclamacoes_municipios/{UF}.json.gz#natureza; qualidade → qualidade/reclamacoes_municipios/{UF}.json.gz#data_arquivo; qualidade → qualidade/reclamacoes_municipios/{UF}.json.gz#url_fonte; qualidade → qualidade/reclamacoes_municipios/{UF}.json.gz#snapshot_date; qualidade → qualidade/reclamacoes_municipios/{UF}.json.gz#generated_at |
