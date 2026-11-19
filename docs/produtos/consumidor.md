<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Reclamações no Consumidor.gov.br

`consumidor` · produto

Reclamações finalizadas de consumidores contra operadoras de telecomunicações no Consumidor.gov.br, por empresa (nome fantasia), UF, município (casado ao código IBGE pelo nome), assunto e grupo de problema, com índice de solução, tempo médio de resposta e nota média só onde há base mínima, e a ligação empresa → CNPJ (tabela curada do 1.5.17, rotulada). Só agregados; sem ranking nem veredito.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.consumidor.build` |
| Chaves de junção | `ibge`, `cnpj` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [consumidor_gov](../fontes/consumidor_gov.md) — uso comercial: `permitido`
- fonte [anatel_scm](../fontes/anatel_scm.md) — uso comercial: `permitido`
- fonte [anatel_smp](../fontes/anatel_smp.md) — uso comercial: `permitido`
- fonte [anatel_stfc](../fontes/anatel_stfc.md) — uso comercial: `permitido`
- fonte [anatel_seac](../fontes/anatel_seac.md) — uso comercial: `permitido`
- fonte [ibge_censo_pnad](../fontes/ibge_censo_pnad.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `consumidor/consumidor.json.gz`, `consumidor/consumidor_municipios/{UF}.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `marcas[]` | lista | Por empresa (nome fantasia no Consumidor.gov.br), a janela de 12 meses (finalizadas, respondidas, avaliadas, resolvidas, % respondidas, índice de solução, tempo médio em dias e nota média), a série mensal dos 24 meses e as raízes de CNPJ ligadas (vazio = sem CNPJ). | Índice, tempo e nota só com 30 ou mais casos (nulo = base insuficiente, não zero). A ligação é curada (apelido ou tabela de marcas) ou automática por nome fantasia único validada por UF, nunca um palpite. Reclamação não é prova de falha da empresa. | consumidor → consumidor/consumidor.json.gz#marcas |
| `setor_por_mes[] / janela / meses_disponiveis` | lista | Total do setor de telecomunicações por mês e a janela de 12 meses usada nos indicadores. | — | consumidor → consumidor/consumidor.json.gz#setor_por_mes; consumidor → consumidor/consumidor.json.gz#janela; consumidor → consumidor/consumidor.json.gz#meses_disponiveis |
| `uf[] / assuntos[] / grupos[]` | lista | Empresa × UF com os mesmos indicadores e empresa × assunto e × grupo de problema com a contagem na janela; só células com 5 ou mais reclamações. | Células pequenas não são publicadas (a linha original traz sexo e faixa etária de quem reclamou, que não são guardados). | consumidor → consumidor/consumidor.json.gz#uf; consumidor → consumidor/consumidor.json.gz#assuntos; consumidor → consumidor/consumidor.json.gz#grupos |
| `casamento / cidades / leitura` | dict | Cobertura da ligação empresa → CNPJ (% das reclamações da janela), cobertura do casamento da cidade ao código IBGE (% e as maiores cidades sem código) e a contagem da leitura da fonte. | — | consumidor → consumidor/consumidor.json.gz#casamento; consumidor → consumidor/consumidor.json.gz#cidades; consumidor → consumidor/consumidor.json.gz#leitura |
| `municipios[ibge]` | dict | Por município, o total da janela (com os indicadores) e, por empresa, as células com 5 ou mais reclamações, com a população estimada do IBGE. | A cidade é o nome digitado pelo consumidor, casado ao IBGE por nome e UF; nome repetido na UF não casa. | consumidor → consumidor/consumidor_municipios/{UF}.json.gz#municipios |
| `limites / minimos / natureza / fonte / url_fonte / snapshot_date / generated_at / municipios_uf` | str | O que o dado é e não é, os mínimos de base, fonte, endereço, data do snapshot, instante de geração e o índice código IBGE → UF. | — | consumidor → consumidor/consumidor.json.gz#limites; consumidor → consumidor/consumidor.json.gz#minimos; consumidor → consumidor/consumidor.json.gz#natureza; consumidor → consumidor/consumidor.json.gz#fonte; consumidor → consumidor/consumidor.json.gz#url_fonte; consumidor → consumidor/consumidor.json.gz#snapshot_date; consumidor → consumidor/consumidor.json.gz#generated_at; consumidor → consumidor/consumidor.json.gz#municipios_uf |
| `uf / janela / natureza / fonte / url_fonte / snapshot_date / generated_at` | str | Cabeçalho de cada parte por UF dos municípios. | — | consumidor → consumidor/consumidor_municipios/{UF}.json.gz#uf; consumidor → consumidor/consumidor_municipios/{UF}.json.gz#janela; consumidor → consumidor/consumidor_municipios/{UF}.json.gz#natureza; consumidor → consumidor/consumidor_municipios/{UF}.json.gz#fonte; consumidor → consumidor/consumidor_municipios/{UF}.json.gz#url_fonte; consumidor → consumidor/consumidor_municipios/{UF}.json.gz#snapshot_date; consumidor → consumidor/consumidor_municipios/{UF}.json.gz#generated_at |
