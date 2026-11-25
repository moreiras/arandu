<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Redes brasileiras no PeeringDB (net)

`peeringdb_networks` · tipo **bruta** · ativa

Para os ASNs brasileiros do LACNIC, consulta /api/net?asn__in= em lotes e extrai política de peering, tipo de rede, tráfego declarado, IRR as-set e site.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.peeringdb_networks.collect` |
| Publicável | sim (exposição: aberta) |
| Decisão sobre a exposição | Aberta por decisão do projeto (D9, 2026-11-24; PTT externo revisto em 2026-11-25): o que a fonte alimenta é servido sem login na interface, na API e no MCP, e a abertura é intencional, não um padrão esquecido. Dado do PeeringDB: o projeto publica atributos por rede (política de peering, tipo, as-set), sem contatos. |
| Atribuição exigida | PeeringDB (https://www.peeringdb.com). Uso sujeito à AUP (https://www.peeringdb.com/aup); a forma de atribuição que o PeeringDB exige não foi verificada. |
| Política de falha | critica |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 8d |
| Chaves | `asn` |
| Entradas | `lacnic_delegated` |
| Amostra de teste | `tests/fixtures/raw/peeringdb/` |

## Origem e licença

- **URL:** https://www.peeringdb.com/api/net
- **Formato:** JSON (API REST)
- **Licença:** PeeringDB AUP
- **Uso comercial:** `restrito`
- **Termos:** https://www.peeringdb.com/aup
- **Evidência / ressalvas:** PeeringDB AUP (https://www.peeringdb.com/aup, verificado em 2026-10-13): fora de 'finalidades operacionais de Internet' aprovadas, nenhuma parte dos dados pode ser reproduzida ou repassada em massa sem autorização; o uso excluído inclui 'listas de marketing, mapeamento demográfico ou qualquer outra aplicação comercial'.

## Saídas

- **Bruto (raw/):** `summary/peeringdb-networks-{as_of}.json`
- **Normalizado (normalized/):** `summary/peeringdb_networks.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `networks[asn].name / aka` | str | Nome e nome alternativo da rede cadastrada no PeeringDB. | — | asn_docs → asns/{asn}.json#pdb |
| `networks[asn].info_type` | str | Tipo de rede declarado (NSP, Cable/DSL/ISP, Content, Enterprise, Educational…). | Autodeclarado. | asn_docs → asns/{asn}.json#pdb |
| `networks[asn].info_traffic` | str | Faixa de tráfego declarada. | Autodeclarado. | asn_docs → asns/{asn}.json#pdb |
| `networks[asn].info_ratio` | str | Razão de tráfego declarada (ex.: Balanced, Heavy Inbound). | Autodeclarado. | asn_docs → asns/{asn}.json#pdb |
| `networks[asn].info_prefixes4 / info_prefixes6` | int | Quantidade de prefixos que a rede declara anunciar. | Autodeclarado; comparável aos prefixos observados na tabela global. | asn_docs → asns/{asn}.json#pdb |
| `networks[asn].policy_general / policy_locations / policy_ratio / policy_contracts` | str\|bool | Política de peering declarada (Open/Selective/Restrictive), exigência de localização, de razão de tráfego e de contrato. | Autodeclarado. | asn_docs → asns/{asn}.json#pdb |
| `networks[asn].irr_as_set` | str | as-set de IRR declarado para filtragem de prefixos. | — | asn_docs → asns/{asn}.json#pdb |
| `networks[asn].website` | str | Site da rede. | — | asn_docs → asns/{asn}.json#pdb |
| `pdb_registered / total_br_asns` | int | ASNs BR com registro no PeeringDB e total de ASNs BR consultados. | Checado por publish.coleta_checks (a coleta falha alto em queda anormal). | snapshot → summary.json#br_asns_peeringdb |

## Limites

Só ASNs que têm cadastro no PeeringDB (5.429 de 9.119 ASNs BR em 2026-10-11); campos autodeclarados e podem estar desatualizados.

## Retenção

- **bruto:** 4 versões
- **normalizado:** 52 semanas

## Quem usa

- **Fontes derivadas:** `peeringdb_contacts`, `peeringdb_fac`, `peeringdb_intl_geo`
- **Produtos:** `asn_docs`

## Pendências (nao_verificado)

- Uso comercial e redistribuição de dados do PeeringDB dependem de autorização do PeeringDB (AUP); confirmar com o PeeringDB e o jurídico.
