<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Sessões BGP dos route servers do IX.br (Alice-LG)

`ixbr_alice` · tipo **bruta** · ativa

Estado de cada route server do IX.br (164 em 41 PTTs: rs1 e rs2, IPv6 e IPv4) e de cada sessão BGP dos membros, vistos pela API do Alice-LG do `lg.ix.br`. Por sessão, o estado, o motivo do último erro, a data da última mudança de estado, as rotas recebidas, aceitas e filtradas, o limite de importação e os contadores de atualização. Guarda também o dicionário de communities (rejeição, não exportar, RPKI, blackhole), um por snapshot.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.ixbr_alice.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | diaria → diaria |
| Frescor máximo | 10d |
| Chaves | `ixp`, `asn` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/ixbr_alice/` |

## Origem e licença

- **URL:** https://lg.ix.br/api/v1/ (config, status, routeservers, routeservers/{id}/neighbors)
- **Formato:** JSON (Alice-LG 6.1.0; os route servers são BIRD)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** API pública do Looking Glass do IX.br, sem autenticação. O robots.txt do lg.ix.br pede Crawl-delay de 1 s e não bloqueia caminhos; termos de uso não localizados em 2026-10-31. Coletor com User-Agent identificado (`arandurape/<versão> (+SITE_URL)`, `core/site.py`), uma requisição por vez e pausa de 1 s. Uma rodada tem 167 requisições (164 `neighbors` mais `config`, `status` e `routeservers`); medido em 2026-11-10 (164 de 164 route servers, 36.080 sessões, 174 s). Diária desde 2026-11-10 (decisão do mantenedor), para o `ixbr_alice_rotas` diário partir das sessões do dia.

## Saídas

- **Normalizado (normalized/):** `summary/rs_sessions.json.gz`, `summary/ixbr_communities.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `rs[].estado_rotas` | str | Estado do cache de ROTAS do Alice para o route server (READY, BUSY ou ERROR), do `/status`; `rotas_atualizadas_em` é o fim da última renovação desse cache. | Não diz nada das sessões (o SP rs1 v4 aparece BUSY/ERROR nas rotas e tem sessões com minutos de uptime). O dado de sessão vem do `neighbors`. | — |
| `rs[].vizinhos_em` | str | Instante em que o Alice atualizou o cache de vizinhos do route server (`cache_status.cached_at` da resposta do `neighbors`). | É o frescor das sessões. Vazio se a consulta falhou ou a resposta não traz o dado; o produto trata como incerto. | — |
| `rs[].consultado` | bool | Se a consulta de `neighbors` do RS funcionou nesta rodada. Falso = sem sessões e sem zero inventado (`erro` diz o motivo). | — | — |
| `sessoes[].estado` | str | Estado da sessão BGP no route server (up ou down). | — | — |
| `sessoes[].last_error` | str | Último erro reportado pelo route server para a sessão (por exemplo "Hold timer expired"); vazio quando não há. | — | — |
| `sessoes[].state_changed` | str | Data e hora (horário do route server) da última mudança de estado da sessão. | — | — |
| `sessoes[].rotas` | object | Rotas recebidas, aceitas, filtradas e exportadas pelo route server para o membro. | — | — |
| `sessoes[].import_limit` | int | Limite de prefixos aceitos por sessão (`receive_limit` e `import_limit` do route server). | — | — |
| `sessoes[].descricao` | str | Nome do membro como cadastrado no route server (organização, não pessoa). | — | — |

## Limites

Sessão BGP no route server não é tráfego nem relação comercial: mostra o que o IX.br enxerga naquele instante. O bruto não é guardado (derivados apenas); RS cujo `neighbors` falhou fica sem sessões e marcado; o READY/BUSY/ERROR do Alice é do cache de rotas, não das sessões. O Alice ainda não foi coletado em série diária.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Fontes derivadas:** `ixbr_alice_rotas`
- **Produtos:** `route_servers`, `rs_policy`

## Pendências (nao_verificado)

- Termos de uso do lg.ix.br não localizados (uso comercial).
- Taxa: no mínimo 1 s entre requisições, uma por vez (definido pelo mantenedor).
