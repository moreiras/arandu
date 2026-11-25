<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Instalações, carriers, campus e atributos das redes do Brasil (PeeringDB)

`peeringdb_fac` · tipo **bruta** · ativa

Instalações (`fac`) do Brasil e as dos PTTs externos já cadastrados, com os vínculos de redes (`netfac`, só instalações do Brasil), de PTTs (`ixfac`) e de carriers (`carrierfac`), os carriers, os campus e os atributos de peering de cada rede do Brasil que está no PeeringDB (`net`, em lotes de 500 ASNs). Cerca de 30 requisições por coleta, uma por vez, com pausa de 1,5 s. Escopo restrito ao Brasil e às instalações dos PTTs cadastrados (sem dump mundial). Os campos de contato (`*_email`, `*_phone`) e `notes` NÃO são mantidos, porque o normalizador usa lista branca e o bruto não é gravado (só o manifesto das requisições).

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.peeringdb_fac.collect` |
| Publicável | sim (exposição: aberta) |
| Decisão sobre a exposição | Aberta por decisão do projeto (D9, 2026-11-24): o que a fonte alimenta é servido sem login na interface, na API e no MCP, salvo o que está dito a seguir, e a abertura é intencional, não um padrão esquecido. Dado do PeeringDB (AUP): o projeto publica atributos e agregados por rede e por instalação, sem contatos; a lista completa de membros de um PTT externo (`/external-ixps/{code}`) exige login, porque é a redistribuição em massa que a AUP restringe e que a rota já declarava "Requer autenticação". A diferença é uma escolha de risco do projeto, não uma conclusão jurídica; a consulta jurídica segue aberta. |
| Atribuição exigida | PeeringDB (https://www.peeringdb.com). Uso sujeito à AUP (https://www.peeringdb.com/aup); a forma de atribuição que o PeeringDB exige não foi verificada. |
| Política de falha | opcional |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 8d |
| Chaves | `asn`, `facilidade` |
| Entradas | `peeringdb_networks`, `peeringdb_ixps` |
| Amostra de teste | `tests/fixtures/raw/peeringdb_fac/` |

## Origem e licença

- **URL:** https://www.peeringdb.com/api/fac
- **Formato:** JSON (API REST; fac, netfac, ixfac, carrierfac, carrier, campus, ix e net, com filtros country, id__in, asn__in e fields)
- **Licença:** PeeringDB AUP
- **Uso comercial:** `nao_verificado`
- **Termos:** https://www.peeringdb.com/aup
- **Evidência / ressalvas:** PeeringDB AUP (https://www.peeringdb.com/aup, verificado em 2026-10-13): fora de 'finalidades operacionais de Internet' aprovadas, nenhuma parte dos dados pode ser reproduzida ou repassada em massa sem autorização. Em 2026-11-06 o mantenedor autorizou o uso sem confirmação escrita do PeeringDB, com as condições: chave de API (PEERINGDB_API_KEY), coleta só do Brasil e das instalações dos PTTs externos cadastrados, e nunca expor contatos (POC). Não substitui a consulta jurídica; o uso comercial segue não verificado. robots.txt do host só bloqueia /register, /account/login, /username-retrieve e /reset-password (2026-11-06). Limite da API com chave: 1000 requisições por hora.

## Saídas

- **Bruto (raw/):** `summary/peeringdb-fac-requisicoes-{as_of}.json`
- **Normalizado (normalized/):** `summary/peeringdb_fac.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `facilities[id]` | dict | Instalação do PeeringDB (nome, organização, cidade, UF, país, coordenadas, site, propriedade, contagens declaradas, datas de criação e atualização, campus). | Autodeclarado; lista branca de campos (sem contatos, notes, redes sociais, endereço de rua nem CEP). | instalacoes → instalacoes/instalacoes.json.gz#instalacoes |
| `netfac / ixfac / carrierfac` | list | Vínculos rede × instalação (só instalações do Brasil), PTT × instalação e carrier × instalação, com as datas de criação e atualização do vínculo de rede. | Declaração no cadastro; não indica tráfego nem contrato. | instalacoes → instalacoes/vinculos.json.gz#por_asn; instalacoes → instalacoes/vinculos.json.gz#por_instalacao |
| `carriers[id] / campus[id]` | dict | Carriers e campus das instalações coletadas (nome, organização, site, datas). | Autodeclarado; sem notes nem redes sociais. | instalacoes → instalacoes/instalacoes.json.gz#carriers; instalacoes → instalacoes/instalacoes.json.gz#campus |
| `redes[asn]` | dict | Escopo geográfico, IPv6, multicast, unicast, "nunca via route server", URLs de looking glass e de route server, datas e contagens declaradas da rede. | Autodeclarado; URL só se for http(s), telnet ou ssh sem credencial embutida; sem notes, contatos nem política. | instalacoes → instalacoes/atributos_rede.json.gz#asns |

## Limites

Só instalações do Brasil e as dos PTTs externos cadastrados; só as redes do Brasil que o peeringdb_networks achou no PeeringDB (5.431 em 2026-11-05). O PeeringDB só dá o estado de agora, então o snapshot recebe a foto do dia da coleta (`fetched_at`), não a da data do snapshot. Cadastro autodeclarado, sem verificação independente.

## Retenção

- **bruto:** 4 versões
- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `instalacoes`

## Pendências (nao_verificado)

- Uso comercial e redistribuição de dados do PeeringDB dependem de autorização do PeeringDB (AUP); o mantenedor autorizou o desenvolvimento sem confirmação escrita (2026-11-06); a consulta jurídica segue aberta.
