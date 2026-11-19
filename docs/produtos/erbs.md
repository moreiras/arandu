<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Estações do SMP licenciadas por município, UF e operadora

`erbs` · produto

Contagem das estações do SMP licenciadas (cadastro da Anatel, 2G a 5G) por município, UF, operadora e geração, com o casamento com o IBGE e o CNPJ. É cadastro de licenciamento, não cobertura.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.erbs.build` |
| Chaves de junção | `ibge`, `cnpj` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [anatel_erbs](../fontes/anatel_erbs.md) — uso comercial: `permitido`
- fonte [ibge_censo_pnad](../fontes/ibge_censo_pnad.md) — uso comercial: `nao_verificado`
- fonte [anatel_smp](../fontes/anatel_smp.md) — uso comercial: `permitido`
- fonte [anatel_sici_movel](../fontes/anatel_sici_movel.md) — uso comercial: `permitido`

## Saídas

- **Publicado:** `erbs/resumo.json.gz`, `erbs/grade.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `municipios[ibge]` | dict | Estações licenciadas no município, quantas têm cada geração (2G a 5G), estações por operadora e por 10 mil habitantes. | Cadastro de licenciamento, não cobertura. Município sem estação não aparece (e pode ser atendido por vizinhos). | erbs → erbs/resumo.json.gz#municipios |
| `ufs[uf]` | dict | Estações, municípios, municípios com estação e com 5G, gerações e operadoras da UF. | — | erbs → erbs/resumo.json.gz#ufs |
| `operadoras[]` | lista | Por operadora (CNPJ quando conhecido, senão a marca), estações, municípios, UFs, gerações e tipo do 5G (SA, NSA, SA-NSA). | O CNPJ vem do arquivo da Anatel ou, quando em branco, da razão social nas outorgas do SMP; o que não casa fica só com a marca. | erbs → erbs/resumo.json.gz#operadoras |
| `brasil / casamento` | dict | Totais do país e medidas de casamento (estações com município no IBGE, sem CNPJ, sanidade contra o SICI móvel). | — | erbs → erbs/resumo.json.gz#brasil; erbs → erbs/resumo.json.gz#casamento |
| `limites / natureza / fonte / data_arquivo` | str | O que o dado é e não é, o rótulo de natureza, a fonte e a data de modificação do arquivo na Anatel. | — | erbs → erbs/resumo.json.gz#limites; erbs → erbs/resumo.json.gz#natureza; erbs → erbs/resumo.json.gz#fonte; erbs → erbs/resumo.json.gz#data_arquivo |
| `grade.celulas[]` | lista | Células de ~2 km (0,02 grau) com o centro (lon, lat), o número de estações licenciadas e quantas têm 2G, 3G, 4G e 5G. Alimenta a camada "Antenas" do mapa. | Agregado (não são pontos de estação); estação sem posição válida fica de fora. | erbs → erbs/grade.json.gz#celulas |
| `grade.colunas / passo_graus / natureza / limites` | lista / float / str | Nome das colunas de cada célula, tamanho da célula em graus, rótulo de natureza e limites do dado. | — | erbs → erbs/grade.json.gz#colunas; erbs → erbs/grade.json.gz#passo_graus; erbs → erbs/grade.json.gz#natureza; erbs → erbs/grade.json.gz#limites |
