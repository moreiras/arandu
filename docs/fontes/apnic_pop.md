<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Estimativas de usuários por AS (APNIC Labs)

`apnic_pop` · tipo **bruta** · ativa

Tabela do APNIC Labs (v6pop, país BR, janela de 60 dias) com usuários estimados por AS, % da população do país e % de usuários IPv6. Medição por anúncio, não censo.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.apnic_pop.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 8d |
| Chaves | `asn` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/apnic_pop/` |

## Origem e licença

- **URL:** https://stats.labs.apnic.net/v6pop?c=BR&w=60
- **Formato:** HTML com tabela embutida em JavaScript (google.visualization)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** Página não declara licença legível (verificado em 2026-10-13: HTML de 2 MB sem termos). Termos da APNIC Labs a confirmar.

## Saídas

- **Bruto (raw/):** `apnic_v6pop-{as_of}.html`
- **Normalizado (normalized/):** `summary/apnic_pop.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `window_days` | int | Janela de medição em dias (60). | — | — |
| `asns[asn].users` | int | Usuários de Internet estimados atrás do AS. | Estimativa por amostragem de anúncios, rotulada 'estimado'. | asn_docs → asns/{asn}.json#apnic_users |
| `asns[asn].users_pct_cc` | float | % da população estimada do país (BR) que o AS representa. | — | asn_docs → asns/{asn}.json#apnic_users_pct_cc |
| `asns[asn].v6_users` | int | Usuários IPv6 estimados. | — | asn_docs → asns/{asn}.json#apnic_v6_users |
| `asns[asn].v6_pct_as` | float | % dos usuários do AS que usam IPv6. | — | asn_docs → asns/{asn}.json#apnic_v6_pct_as |

## Limites

Estimativa estatística; não é número de clientes nem de domicílios. ASNs com poucos usuários podem faltar. Mudança de leiaute do HTML quebra o parser (falha opcional: campos viram nulos).

## Retenção

- **bruto:** 4 versões
- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `asn_docs`, `rede_territorio`, `sici`, `sici_indicadores`

## Pendências (nao_verificado)

- Licença/termos da série APNIC Labs a confirmar.
