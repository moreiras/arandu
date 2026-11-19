<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Cadastro das empresas de telecom (Receita Federal) cruzado com o SICI

`cadastro_empresas` · produto

Por operadora (raiz de CNPJ): matriz, estabelecimentos ativos e baixados, porte, Simples e MEI e a presença física por município (onde há estabelecimento ativo × onde a empresa declara acessos no SICI). Do mercado: entradas e baixas de empresas de telecom por ano e UF, empresas ativas por UF e porte. Fato cadastral da Receita na data do dump mensal; o cruzamento com o SICI não prova atendimento.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.cadastro_empresas.build` |
| Chaves de junção | `cnpj`, `ibge` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [receita_cnpj](../fontes/receita_cnpj.md) — uso comercial: `nao_verificado`
- fonte [anatel_scm](../fontes/anatel_scm.md) — uso comercial: `permitido`
- fonte [anatel_smp](../fontes/anatel_smp.md) — uso comercial: `permitido`
- fonte [anatel_stfc](../fontes/anatel_stfc.md) — uso comercial: `permitido`
- fonte [anatel_seac](../fontes/anatel_seac.md) — uso comercial: `permitido`
- produto [sici](sici.md)

## Saídas

- **Publicado:** `empresas/cadastro.json.gz`, `empresas/operadoras/{NN}.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `operadoras[raiz].matriz / estabelecimentos` | dict | Matriz (CNPJ, UF, município, situação, início da atividade, CNAE) e contagem de estabelecimentos (total, ativos, baixados, filiais ativas) da raiz de CNPJ. | Fato do cadastro da Receita na data do dump mensal; empresário individual sem razão social nem nome fantasia. | cadastro_empresas → empresas/operadoras/{NN}.json.gz#operadoras |
| `operadoras[raiz].presenca[] / resumo_presenca` | lista | Por município, estabelecimentos (total e ativos), se tem a matriz e os acessos fixo e móvel que a empresa declara no SICI; resumo de onde há os dois, só um ou só o outro. | Duas fontes que medem coisas diferentes (sede e filiais × assinantes); a diferença não prova que a empresa atende ou deixou de atender o município. | cadastro_empresas → empresas/operadoras/{NN}.json.gz#operadoras |
| `mercado.entradas_por_ano[] / baixas_por_ano[]` | lista | Empresas de telecom (matriz com CNAE 61 principal) abertas e baixadas por ano, no total e por UF. | Uma contagem por empresa (a matriz); não separa operadora de revenda ou de MEI. | cadastro_empresas → empresas/cadastro.json.gz#mercado |
| `mercado.ativas_por_uf / ativas_por_porte` | dict | Empresas de telecom ativas no dump, por UF e por porte (micro, pequeno, demais, MEI). | — | cadastro_empresas → empresas/cadastro.json.gz#mercado |
| `resumo / limites` | dict | Empresas no recorte, operadoras com e sem cadastro, estabelecimentos sem casamento com o IBGE e os limites do cruzamento. | — | cadastro_empresas → empresas/cadastro.json.gz#resumo |

## Limites

Cadastro na data do dump mensal; recorte de telecom (outorgas, SICI e CNAE 61); município por nome e UF; sem e-mail, telefone, rua nem CEP.
