<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Rank, grau e cone de ASNs (CAIDA AS Rank)

`caida_asrank` · tipo **bruta** · ativa

Rank, grau (clientes, pares e provedores) e cone de cada ASN do Brasil, pela API REST pública do CAIDA AS Rank (listagem paginada de todos os ~123 mil ASNs, filtrada pelo país). Inferência do CAIDA sobre a tabela de rotas pública.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.caida_asrank.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | mensal |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 45d |
| Chaves | `asn` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/caida_asrank/` |

## Origem e licença

- **URL:** https://api.asrank.caida.org/v2/restful/asns/
- **Formato:** JSON (data.asns.edges[].node), paginado por first/offset
- **Licença:** dados públicos do CAIDA (Acceptable Use Agreement for Publicly Accessible Datasets), atribuição obrigatória
- **Uso comercial:** `nao_verificado`
- **Termos:** https://www.caida.org/about/legal/aua/
- **Evidência / ressalvas:** Citação: "The CAIDA UCSD AS Rank, https://asrank.caida.org". O AS Rank é inferência do CAIDA e nunca vai como verdade: rotulado como estimado.

## Saídas

- **Normalizado (normalized/):** `summary/caida_asrank.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].rank` | int | Posição do ASN pelo tamanho do cone de clientes (1 = maior). | Inferência do CAIDA (relações entre ASNs); estimado. | — |
| `asns[asn].cone` | dict | Tamanho do cone de clientes (ASNs, prefixos e endereços). | Inferência do CAIDA. | — |
| `asns[asn].grau` | dict | Número de vizinhos por tipo (total, clientes, pares, provedores) inferido pelo CAIDA. | Inferência; difere do que o Arandurapé infere em as_relationships. | — |
| `asns[asn].clique` | bool | Campo cliqueMember da API do CAIDA. | NÃO USADO nos produtos. A API devolve true para ASNs de rank baixo (conferido em 2026-10-31, caso do AS28573, posição 7.887), então não é a clique de nível 1. | — |

## Limites

Mensal, defasado até ~1 mês; "país" é o do registro do ASN (pode diferir de is_br do Arandurapé). Listagem completa leva 4 a 5 minutos (13 páginas de ~3,6 MB, ~20 s cada).

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `seguranca_asn`

## Pendências (nao_verificado)

- Uso comercial do dataset (AUA); servir só o derivado rotulado, com a atribuição.
