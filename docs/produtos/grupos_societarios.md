<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Grupos societários publicados

`grupos_societarios` · produto

Publica o cruzamento do quadro societário das operadoras (grupos, relações total/parcial, holdings externas e sede).

## Resumo

| | |
|---|---|
| Módulo (hoje) | `publish.snapshot_builder` |
| Chaves de junção | `cnpj`, `grupo` |
| Cenários de teste (dataset sintético) | `grupos_societarios` |

## Entradas

- fonte [socios_grupos](../fontes/socios_grupos.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `grupos_societarios.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `total_grupos / total_cnpjs_em_grupo` | int | Quantidade de grupos e de CNPJs que pertencem a algum grupo. | — | grupos_societarios → grupos_societarios.json.gz#total_grupos |
| `by_cnpj[cnpj].tamanho_grupo` | int | Número de CNPJs no grupo do CNPJ. | — | grupos_societarios → grupos_societarios.json.gz#by_cnpj |
| `by_cnpj[cnpj].endereco_sede` | dict | Endereço da sede do CNPJ (pessoa jurídica). | Endereço de PJ exposto (decisão 2026-10-11). | grupos_societarios → grupos_societarios.json.gz#by_cnpj |
| `receita_dump_reference` | str | Mês de referência do dump da Receita usado. | — | grupos_societarios → grupos_societarios.json.gz#receita_dump_reference |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | grupos_societarios → grupos_societarios.json.gz#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | grupos_societarios → grupos_societarios.json.gz#generated_at |
| `receita_socios_generated_at` | str | Instante em que a coleta de sócios usada foi gerada. | — | grupos_societarios → grupos_societarios.json.gz#receita_socios_generated_at |
| `total_cnpjs_em_grupo` | int | CNPJs que pertencem a algum grupo. | — | grupos_societarios → grupos_societarios.json.gz#total_cnpjs_em_grupo |

## Limites

Hipótese baseada em quadro societário; ver socios_grupos.
