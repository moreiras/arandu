<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Demanda × oferta de banda larga fixa

`demanda_oferta` · produto

Cruza a proporção de domicílios com banda larga fixa (TIC Domicílios, estimativa do Arandurapé) com os domicílios projetados do IBGE e os acessos fixos de pessoa física do SICI, por UF, grande região e Brasil, com razão, mercado não visto e intervalo de 95%.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.demanda_oferta.build` |
| Chaves de junção | `uf` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [cetic_tic_domicilios_microdados](../fontes/cetic_tic_domicilios_microdados.md) — uso comercial: `permitido`
- fonte [ibge_censo_pnad](../fontes/ibge_censo_pnad.md) — uso comercial: `nao_verificado`
- fonte [anatel_sici](../fontes/anatel_sici.md) — uso comercial: `permitido`

## Saídas

- **Publicado:** `mercado/demanda_oferta.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ufs[uf] / regioes[região] / brasil` | dict | Por grupo, domicílios projetados, proporção com banda larga fixa (TIC) e margem, demanda estimada, acessos de pessoa física (SICI), razão com limites, mercado não visto com limites e a classe. | ESTIMATIVA do Arandurapé. Denominador do IBGE tratado como fixo; a margem vem só da amostra da TIC e é menor que a oficial. Grupo suprimido ou de precisão baixa é indeterminado. | demanda_oferta → mercado/demanda_oferta.json.gz#ufs; demanda_oferta → mercado/demanda_oferta.json.gz#regioes; demanda_oferta → mercado/demanda_oferta.json.gz#brasil |
| `tic_edicao / mes_referencia_sici / pnad_ano` | int / str / str | Período de referência de cada fonte (a pesquisa, o SICI e a projeção de domicílios não são do mesmo mês). | — | demanda_oferta → mercado/demanda_oferta.json.gz#tic_edicao; demanda_oferta → mercado/demanda_oferta.json.gz#mes_referencia_sici; demanda_oferta → mercado/demanda_oferta.json.gz#pnad_ano |
| `limites / formulas / intervalo / natureza / fonte` | str / dict | Texto das limitações, as fórmulas, o nível do intervalo e o rótulo de natureza do número. | — | demanda_oferta → mercado/demanda_oferta.json.gz#limites; demanda_oferta → mercado/demanda_oferta.json.gz#formulas; demanda_oferta → mercado/demanda_oferta.json.gz#intervalo; demanda_oferta → mercado/demanda_oferta.json.gz#natureza; demanda_oferta → mercado/demanda_oferta.json.gz#fonte |

## Limites

Cruza declaração (SICI, sem erro amostral) com estimativa amostral (TIC Domicílios): a classe sai do intervalo de 95% da razão e fica `indeterminado` com CV acima de 30%. Diferença entre demanda e oferta é divergência entre fontes com definições e períodos diferentes, não erro nem omissão das prestadoras.
