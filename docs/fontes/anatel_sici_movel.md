<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Acessos de telefonia móvel (SICI/Anatel)

`anatel_sici_movel` · tipo **bruta** · ativa

Acessos móveis declarados por prestadora, município, modalidade (pré/pós), geração (2G–5G) e tipo de cliente. Mesma mecânica incremental do SICI fixo, com membros semestrais (~100–250 MB) e histórico a partir de 2019.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.anatel_sici_movel.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | mensal |
| Coleta hoje → alvo | semanal → diaria_se_novo_mes |
| Frescor máximo | 45d |
| Chaves | `cnpj`, `ibge`, `uf`, `mes_referencia` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/anatel_sici_movel/` |

## Origem e licença

- **URL:** https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/acessos_telefonia_movel.zip
- **Formato:** zip/csv (~3 GB; leitura por HTTP Range)
- **Licença:** Dados Abertos Anatel (licença aberta, crédito à fonte)
- **Uso comercial:** `permitido`
- **Termos:** https://www.gov.br/anatel/pt-br/dados/dados-abertos
- **Evidência / ressalvas:** Plano de Dados Abertos da Anatel (verificado em 2026-10-13): dados 'disponibilizados sob licença aberta que permita sua livre utilização, consumo ou cruzamento, limitando-se a creditar a autoria ou a fonte' (Decreto 8.777/2016). A licença específica do conjunto em dados.gov.br não pôde ser lida (exige JavaScript/token).

## Saídas

- **Normalizado (normalized/):** `summary/sici_movel_acessos.json.gz`, `../sici_movel_cache/state.json`, `../sici_movel_cache/months/{AAAA-MM}.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `mes_referencia` | str | Último mês de declaração disponível (AAAA-MM). | — | sici → sici_movel.json.gz#mes_referencia |
| `cnpjs[cnpj].acessos` | int | Acessos móveis de voz/dados em linha pessoal, declarados no mês. | M2M e PONTO_DE_SERVICO não entram no total (batem com o total oficial da Anatel). | sici → sici_movel.json.gz#cnpjs |
| `cnpjs[cnpj].acessos_m2m / acessos_outros` | int | Acessos M2M (chips embarcados) e demais (infraestrutura da prestadora), contados à parte. | — | sici → sici_movel.json.gz#cnpjs |
| `cnpjs[cnpj].por_geracao / por_modalidade / por_produto / por_municipio` | dict | Acessos por geração (2G–5G), modalidade de cobrança, produto e município. | — | sici → sici_movel.json.gz#cnpjs |
| `cnpjs[cnpj].pf / pj` | int | Acessos de clientes PF e PJ. | — | sici → sici_movel.json.gz#cnpjs |

## Limites

Só formato unificado (2019 em diante). Autodeclarado. Linhas ≠ pessoas (uma pessoa pode ter várias).

## Retenção

- **bruto:** cache incremental
- **normalizado:** 52 semanas

## Quem usa

- **Fontes derivadas:** `siasg_contratos`
- **Produtos:** `erbs`, `regiao_municipios`, `sici`

## Pendências (nao_verificado)

- Confirmar a licença no registro do conjunto em dados.gov.br (página exige JavaScript; API pública responde 401).
