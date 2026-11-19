<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Crédito público (BNDES) e sanções (CEIS e CNEP) por operadora

`financiamento_sancoes` · produto

Por operadora (raiz de CNPJ): operações de financiamento do BNDES (total contratado e desembolsado, por ano e UF, últimas operações) e sanções do CEIS e do CNEP (vigentes e encerradas na data do snapshot, com órgão, fundamento legal e período). Registro de fonte oficial, sem julgamento; as duas partes não se ligam.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.financiamento_sancoes.build` |
| Chaves de junção | `cnpj` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [bndes_operacoes](../fontes/bndes_operacoes.md) — uso comercial: `permitido`
- fonte [cgu_ceis_cnep](../fontes/cgu_ceis_cnep.md) — uso comercial: `permitido`

## Saídas

- **Publicado:** `financiamento/operadoras.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `operadoras[raiz].financiamento` | dict | Operações do BNDES da raiz de CNPJ, com total contratado e desembolsado (R$ nominais), primeira e última data, série por ano, por UF e as 50 operações mais recentes. | Só operações diretas e não automáticas; valores nominais da data da contratação, sem correção. | financiamento_sancoes → financiamento/operadoras.json.gz#operadoras |
| `operadoras[raiz].sancoes` | dict | Sanções do CEIS e do CNEP da raiz de CNPJ, separadas em vigentes (inclui as sem prazo e as que começam depois da data) e encerradas na data do snapshot. | Registro do órgão sancionador, sem adjetivo; a vigência é calculada pela data do snapshot; sanção sem prazo vem da data 2099-12-31 da fonte. | financiamento_sancoes → financiamento/operadoras.json.gz#operadoras |
| `resumo / limites / fontes` | dict | Operadoras com financiamento e com sanção, operações e valor contratado totais, datas de referência de cada fonte e os limites. | — | financiamento_sancoes → financiamento/operadoras.json.gz#resumo |

## Limites

Duas fontes independentes (BNDES e CGU), cada uma na sua data; só operações diretas do BNDES; a sanção pode ter sido suspensa ou anulada sem refletir no arquivo do dia; sem ranking nem veredito.
