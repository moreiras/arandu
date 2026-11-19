<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Participação no MANRS (agregado)

`manrs_agregado` · produto

Quantos ASNs e quantos usuários estimados do Brasil estão em organizações participantes do programa de operadores do MANRS, no total, por faixa de porte e por UF, e a prontidão média de participantes e não participantes (total e porte). Só agregados com a atribuição exigida; não há registro por ASN nem por organização.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.manrs.build` |
| Chaves de junção | `asn`, `uf` |
| Cenários de teste (dataset sintético) | — |

## Entradas


## Saídas

- **Publicado:** `manrs/resumo.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `brasil / por_faixa_porte / por_uf` | dict | ASNs e usuários do recorte, ASNs participantes, % dos ASNs e % dos usuários estimados do APNIC; recorte com menos de 5 participantes vem `suprimido`. | Comparação de prontidão (participantes × não participantes) só no total e por porte, com pelo menos 5 ASNs com índice em cada lado. | manrs_agregado → manrs/resumo.json.gz#brasil; manrs_agregado → manrs/resumo.json.gz#por_faixa_porte; manrs_agregado → manrs/resumo.json.gz#por_uf |
| `atribuicao / fonte / regras / limites / natureza` | dict | A frase de atribuição exigida pelos termos, a fonte com data da medição, a regra de supressão e as limitações. | — | manrs_agregado → manrs/resumo.json.gz#atribuicao; manrs_agregado → manrs/resumo.json.gz#fonte; manrs_agregado → manrs/resumo.json.gz#regras; manrs_agregado → manrs/resumo.json.gz#limites; manrs_agregado → manrs/resumo.json.gz#natureza |
| `snapshot_date / generated_at` | str | Data do snapshot e instante em que o arquivo foi gerado. | — | manrs_agregado → manrs/resumo.json.gz#snapshot_date; manrs_agregado → manrs/resumo.json.gz#generated_at |
