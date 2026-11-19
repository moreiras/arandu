<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Pesquisas TIC do Cetic.br, tabelas oficiais

`cetic` · produto

As tabelas oficiais das pesquisas TIC Domicílios e TIC Provedores do Cetic.br|NIC.br (edição vigente), em formato longo: proporção, total e margem de erro por recorte (região, área, classe social, renda, porte do provedor). Valores do Cetic.br sem alteração, com a margem de erro; estimativas amostrais, não contagens.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.cetic.build` |
| Chaves de junção | `uf` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [cetic_tic_domicilios_tabelas](../fontes/cetic_tic_domicilios_tabelas.md) — uso comercial: `permitido`
- fonte [cetic_tic_provedores_tabelas](../fontes/cetic_tic_provedores_tabelas.md) — uso comercial: `permitido`
- fonte [cetic_tic_domicilios_microdados](../fontes/cetic_tic_domicilios_microdados.md) — uso comercial: `permitido`

## Saídas

- **Publicado:** `cetic/domicilios.json.gz`, `cetic/provedores.json.gz`, `cetic/domicilios_uf.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `snapshot_date` | str | Data do snapshot em que o artefato foi gerado. | — | cetic → cetic/domicilios.json.gz#snapshot_date; cetic → cetic/provedores.json.gz#snapshot_date; cetic → cetic/domicilios_uf.json.gz#snapshot_date |
| `generated_at` | str | Instante UTC em que o artefato foi gerado. | — | cetic → cetic/domicilios.json.gz#generated_at; cetic → cetic/provedores.json.gz#generated_at; cetic → cetic/domicilios_uf.json.gz#generated_at |
| `coletado_em` | str | Instante UTC em que o Arandurapé baixou e leu as tabelas do Cetic.br. | — | cetic → cetic/domicilios.json.gz#coletado_em; cetic → cetic/provedores.json.gz#coletado_em; cetic → cetic/domicilios_uf.json.gz#coletado_em |
| `pesquisa` | str | Nome da pesquisa (TIC Domicílios ou TIC Provedores). | — | cetic → cetic/domicilios.json.gz#pesquisa; cetic → cetic/provedores.json.gz#pesquisa; cetic → cetic/domicilios_uf.json.gz#pesquisa |
| `edicao` | int | Ano da edição publicada pelo Cetic.br. | — | cetic → cetic/domicilios.json.gz#edicao; cetic → cetic/provedores.json.gz#edicao; cetic → cetic/domicilios_uf.json.gz#edicao |
| `fonte` | str | Citação da fonte: Cetic.br\|NIC.br, pesquisa e edição. | — | cetic → cetic/domicilios.json.gz#fonte; cetic → cetic/provedores.json.gz#fonte; cetic → cetic/domicilios_uf.json.gz#fonte |
| `licenca` | str | Licença dos dados (CC BY 4.0, citação obrigatória). | — | cetic → cetic/domicilios.json.gz#licenca; cetic → cetic/provedores.json.gz#licenca; cetic → cetic/domicilios_uf.json.gz#licenca |
| `pagina` | str | Página do Cetic.br de onde os arquivos foram descobertos. | — | cetic → cetic/domicilios.json.gz#pagina; cetic → cetic/provedores.json.gz#pagina; cetic → cetic/domicilios_uf.json.gz#pagina |
| `url` | str | Endereço do ZIP de tabelas usado. | — | cetic → cetic/domicilios.json.gz#url; cetic → cetic/provedores.json.gz#url; cetic → cetic/domicilios_uf.json.gz#url |
| `arquivo` | str | Nome do arquivo ZIP de origem. | — | cetic → cetic/domicilios.json.gz#arquivo; cetic → cetic/provedores.json.gz#arquivo; cetic → cetic/domicilios_uf.json.gz#arquivo |
| `sha256` | str | Hash do ZIP guardado no bruto. | — | cetic → cetic/domicilios.json.gz#sha256; cetic → cetic/provedores.json.gz#sha256; cetic → cetic/domicilios_uf.json.gz#sha256 |
| `total_tabelas` | int | Número de tabelas (abas) da edição. | — | cetic → cetic/domicilios.json.gz#total_tabelas; cetic → cetic/provedores.json.gz#total_tabelas; cetic → cetic/domicilios_uf.json.gz#total_tabelas |
| `total_linhas` | int | Número de linhas do formato longo. | — | cetic → cetic/domicilios.json.gz#total_linhas; cetic → cetic/provedores.json.gz#total_linhas; cetic → cetic/domicilios_uf.json.gz#total_linhas |
| `tabelas` | dict | Por aba: código, título, universo (a quem a pergunta se aplica) e notas. | — | cetic → cetic/domicilios.json.gz#tabelas; cetic → cetic/provedores.json.gz#tabelas; cetic → cetic/domicilios_uf.json.gz#tabelas |
| `linhas` | list | Formato longo: tabela, dimensao, recorte, item, resposta, proporcao, margem_proporcao, total e margem_total. Valor do Cetic.br sem alteração; vazio onde a planilha não traz. | — | cetic → cetic/domicilios.json.gz#linhas; cetic → cetic/provedores.json.gz#linhas; cetic → cetic/domicilios_uf.json.gz#linhas |
| `natureza` | str | Sempre 'estimativa_arandurape': o número não é do Cetic.br, é calculado pelo Arandurapé dos microdados. | — | cetic → cetic/domicilios_uf.json.gz#natureza |
| `domicilios_entrevistados` | int | Domicílios entrevistados na base de microdados. | — | cetic → cetic/domicilios_uf.json.gz#domicilios_entrevistados |
| `metodo` | dict | Réplicas usadas (200), regra da variância, margem de 95% (1,96 × erro-padrão), amostra mínima para não suprimir (30) e limite do CV para precisão baixa (30%). | — | cetic → cetic/domicilios_uf.json.gz#metodo |
| `indicadores` | dict | Por indicador (internet, computador, banda_larga_fixa): rótulo e definição pelas colunas da base. | — | cetic → cetic/domicilios_uf.json.gz#indicadores |
| `grupos` | dict | Brasil, 5 regiões e 27 UFs: domicílios entrevistados e estimados e, por indicador, proporção, erro-padrão, margem, CV, total e precisão; grupo com menos de 30 entrevistados traz 'suprimido'. | — | cetic → cetic/domicilios_uf.json.gz#grupos |
| `validacao` | dict | Comparação com as tabelas oficiais da mesma edição (A1 e A4, Brasil e regiões): maior diferença da proporção em pontos percentuais e faixa da razão margem oficial ÷ margem estimada; nulo se as tabelas não estão disponíveis. | — | cetic → cetic/domicilios_uf.json.gz#validacao |

## Limites

Estimativas amostrais do Cetic.br, não contagens: cada proporção vem com a margem de erro oficial, e recortes pequenos têm erro grande. As definições diferem das do SICI (domicílio com acesso à Internet ou com banda larga × acesso contratado declarado pela prestadora) e o período de referência é o da edição da pesquisa: comparar com o SICI só com a definição e as duas datas explícitas. Microdados sob termo de acesso ficam fora; só o que é público para download.
