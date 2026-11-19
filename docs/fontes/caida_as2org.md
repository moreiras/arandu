<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Organização por ASN (CAIDA AS-to-Organization, via AS Rank)

`caida_as2org` · tipo **bruta** · ativa

Organização (nome, país e número de ASNs membros) de cada ASN do Brasil, pela API GraphQL pública do CAIDA AS Rank, que usa o mapeamento as2org do CAIDA. Consulta em lotes de 150 ASNs (≈ 62 requisições para ~9,2 mil ASNs). O arquivo trimestral `publicdata.caida.org/datasets/as-organizations/` NÃO é usado porque o robots.txt do host tem `Disallow=/`.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.caida_as2org.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | trimestral |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 120d |
| Chaves | `asn` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/caida_as2org/` |

## Origem e licença

- **URL:** https://api.asrank.caida.org/v2/graphql
- **Formato:** JSON (GraphQL, asns(asns) com edges.node.organization: orgId, orgName, country, members)
- **Licença:** dados públicos do CAIDA (Acceptable Use Agreement for Publicly Accessible Datasets), atribuição obrigatória
- **Uso comercial:** `nao_verificado`
- **Termos:** https://www.caida.org/about/legal/aua/public_aua/
- **Evidência / ressalvas:** Public AUA lido em 2026-11-06: licença limitada de copiar, modificar e usar; sem cláusula de uso não comercial; exige citar "The CAIDA UCSD AS Rank" e "The CAIDA AS Organizations Dataset" e comunicar a publicação ao CAIDA (data-info@caida.org). A API do AS Rank não tem robots.txt (500). Coletor com User-Agent identificado, uma requisição por vez e pausa de 1 s. A organização do AS Rank usa orgId próprio e pode agrupar filiais sob uma "Parent".

## Saídas

- **Normalizado (normalized/):** `summary/caida_as2org.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].org_id` | str | Identificador da organização no AS Rank (hash); ASNs com o mesmo valor pertencem à mesma organização. | Inferência do CAIDA a partir do WHOIS. | — |
| `asns[asn].org_nome` | str | Nome da organização como registrado (pode ser o de uma 'Parent'). | Dado do registro, não nome fantasia; rotulado como do CAIDA. | — |
| `asns[asn].org_pais` | str | País da organização (ISO 3166-1 alfa-2). | — | — |
| `asns[asn].membros_total` | int | Número de ASNs da organização no mundo. | — | — |

## Limites

A lista de ASNs vem do caida_asrank (ASNs do Brasil vistos na tabela de rotas); ASN fora do AS Rank não tem organização. Leva ≈ 3 minutos.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `as2org`, `as_relationships`, `transito`

## Pendências (nao_verificado)

- Comunicar ao CAIDA (data-info@caida.org) o uso, como pede o Public AUA.
- Uso comercial não verificado.
