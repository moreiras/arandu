<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Contatos de redes BR no PeeringDB (poc)

`peeringdb_contacts` · tipo **bruta** · ativa

Coleta /api/poc (pontos de contato) de visibilidade Public das redes BR já presentes em peeringdb_networks. Os de visibilidade Users (restritos pelo dono da rede a usuários do PeeringDB) não são pedidos nem servidos. Dado de pessoa: nunca sai em rota pública nem no MCP; é servido apenas ao usuário logado, com cota, e NÃO é copiado para published/ (AUP). O bruto não é gravado: só o manifesto das requisições.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.peeringdb_contacts.collect` |
| Publicável | sim (exposição: login) |
| Política de falha | opcional |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 8d |
| Chaves | `asn` |
| Entradas | `peeringdb_networks` |
| Amostra de teste | `tests/fixtures/raw/peeringdb/` |

## Origem e licença

- **URL:** https://www.peeringdb.com/api/poc
- **Formato:** JSON (API REST, depth=1)
- **Licença:** PeeringDB AUP
- **Uso comercial:** `restrito`
- **Termos:** https://www.peeringdb.com/aup
- **Evidência / ressalvas:** PeeringDB AUP (https://www.peeringdb.com/aup, verificado em 2026-10-13): fora de 'finalidades operacionais de Internet' aprovadas, nenhuma parte dos dados pode ser reproduzida ou repassada em massa sem autorização; o uso excluído inclui 'listas de marketing, mapeamento demográfico ou qualquer outra aplicação comercial'.

## Saídas

- **Bruto (raw/):** `summary/peeringdb-contacts-requisicoes-{as_of}.json`
- **Normalizado (normalized/):** `summary/peeringdb_contacts.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `contacts[asn][].role` | str | Papel do contato (Abuse, NOC, Policy, Technical, Sales…). | — | asn_docs → /api/v1/asns/{asn}/contacts |
| `contacts[asn][].name` ⚠️ dado pessoal/contato | str | Nome do contato (pode ser pessoa física). | LGPD: não é produto público. | asn_docs → /api/v1/asns/{asn}/contacts |
| `contacts[asn][].email` ⚠️ dado pessoal/contato | str | E-mail do contato. | Só via /contacts com login. | asn_docs → /api/v1/asns/{asn}/contacts |
| `contacts[asn][].phone` ⚠️ dado pessoal/contato | str | Telefone do contato. | Só via /contacts com login. | asn_docs → /api/v1/asns/{asn}/contacts |
| `contacts[asn][].visible` | str | Visibilidade do POC no PeeringDB. Só `Public` é pedido e servido; `Users` (restrito pelo dono da rede a usuários autenticados do PeeringDB) fica de fora, porque o login do site não distingue provedor. | A leitura confere o valor; arquivo de coleta anterior a 2026-11-17, sem o campo, não é servido. | — |

## Limites

Contatos autodeclarados; só os POCs de visibilidade Public. Servidos com cota por conta, por rede e global (api/contatos_cota.py). Teste T4 garante que nenhuma rota pública expõe e-mail/telefone.

## Retenção

- **bruto:** 2 versões (dado pessoal)
- **normalizado:** 4 semanas (dado pessoal)

## Pendências (nao_verificado)

- Uso comercial e redistribuição de dados do PeeringDB dependem de autorização do PeeringDB (AUP); confirmar com o PeeringDB e o jurídico.
- Definir retenção mínima para dado pessoal (LGPD) com o jurídico; valores acima são proposta.
