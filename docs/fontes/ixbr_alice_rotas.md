<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Rotas rejeitadas e communities dos membros nos route servers do IX.br (Alice-LG, níveis 2 e 3)

`ixbr_alice_rotas` · tipo **bruta** · ativa

Por vizinho (sessão BGP up no route server do IX.br), uma requisição ao Alice-LG: no nível 2, `routes/filtered` (rotas que o route server rejeitou, com o motivo decodificado pelo dicionário de communities do snapshot e uma amostra de prefixos); no nível 3, `routes/received` (uso de cada community nas rotas recebidas do membro: não exportar para AS, exportar somente para, por RIR e por PTT, blackhole, validação RPKI). Contagens exatas sobre todas as rotas do vizinho (o Alice conta cada community sobre o conjunto inteiro); só a amostra de prefixos é parcial.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.ixbr_alice_rotas.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | diaria → diaria |
| Frescor máximo | 10d |
| Chaves | `ixp`, `asn` |
| Entradas | `ixbr_alice` |
| Amostra de teste | `tests/fixtures/raw/ixbr_alice_rotas/` |

## Origem e licença

- **URL:** https://lg.ix.br/api/v1/routeservers/{rs}/neighbors/{id}/routes/{filtered\|received}?page=0&page_size=250
- **Formato:** JSON (Alice-LG 6.1.0; os route servers são BIRD)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** Mesma API pública do `ixbr_alice` (robots.txt do lg.ix.br pede Crawl-delay de 1 s e não bloqueia caminhos; termos de uso não localizados em 2026-11-06). User-Agent identificado, uma requisição por vez, no mínimo 1 s entre requisições (definido pelo mantenedor: 1 s e granularidade por vizinho), repetição com recuo só em erro transitório, orçamento de requisições por rodada (`ARANDU_ALICE_ORCAMENTO`, padrão 10000; a rodada para se o Alice falhar 10 vezes seguidas; um route server com 3 consultas seguidas acima de 20 s sai da rodada; relógio máximo de 25200 s por rodada). Um vizinho é consultado em um só route server (rs1 se o cache de rotas estiver READY, senão rs2). Prefixos de rotas são dado público de roteamento; guarda-se uma amostra limitada, nunca contatos.

## Saídas

- **Normalizado (normalized/):** `summary/rs_filtered.json.gz`, `summary/rs_communities.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `vizinhos[].total` | int | Número de rotas do vizinho no conjunto consultado (`pagination.total_results` do Alice): rejeitadas (rs_filtered) ou recebidas (rs_communities). | O total vem da paginação, não do tamanho da página (250). | — |
| `vizinhos[].motivos` | dict | rs_filtered: {community grande de rejeição: nº de rotas} (`26162:100:0` inválido no Registro.br, `26162:190:0..5` prefixo/ASN inválido, bogon, trânsito, nunca via RS, prefixos do IX.br, `26162:300:0` RPKI inválido, `26162:400:0` inválido nos RIRs, `26162:616:666` blackhole confirmado), decodificadas pelo dicionário `ixbr_communities` do snapshot. | Contagem exata (`contagem` = exata) ou pela amostra (`amostra`, quando o Alice não traz `filters_available`). `sem_motivo` = rotas sem community de motivo decodificada. | — |
| `vizinhos[].amostra` | list | rs_filtered: até 25 rotas rejeitadas do vizinho (prefixo, ASN de origem, motivos): dado público de roteamento. | Amostra, nunca a lista completa; o produto mostra no máximo 5 por ASN e motivo. | — |
| `vizinhos[].comunidades` | dict | rs_communities: {community: nº de rotas recebidas que a carregam}, nas formas padrão (`a:b`), grande (`a:b:c`) e estendida (`ro:a:b`, `rt:a:b`). | A decodificação (não exportar, exportar somente, RIR, PTT, blackhole) é do produto `rs_policy`, pelo dicionário do snapshot. | — |
| `vizinhos[].herdado` | bool | Verdadeiro se o vizinho não coube no orçamento desta rodada e vem da rodada anterior, com o `coletado_em` original (idade máxima 35 dias). | — | — |
| `vizinhos[].consultado_em` | str | Instante (relógio do coletor) em que o vizinho foi consultado; é ele, e não o `coletado_em` (`cached_at` do Alice, que pode ser mais velho), que ordena o rodízio. | — | — |
| `falhas` | list | Vizinhos cuja consulta falhou nesta rodada ou em rodadas anteriores sem leitura posterior (ixp, afi, asn, ip, instante e erro); vão para o fim da fila do rodízio. | — | — |
| `cobertura_rodizio` | dict | `total` e `por_ptt`: vizinhos elegíveis hoje, lidos nesta rodada, herdados (leitura de rodada anterior), sem leitura nenhuma, route servers pulados por lentidão e idade máxima da leitura em dias (pelo `coletado_em`). | Campo aditivo; o produto nunca extrapola para quem não tem leitura. | — |
| `tempo_por_rs` | dict | Por route server: consultas feitas, segundos médios e máximo no relógio da coleta e ms médios de servidor (`request_duration_ms` do Alice). | Base para ajustar orçamento e taxa com o IX.br; route server lento sai da rodada (`rs_pulados`). | — |
| `rs_pulados` | list | Route servers tirados da rodada por lentidão (3 consultas seguidas acima de ARANDU_ALICE_LENTO_S, padrão 20 s); seus vizinhos ficam com a coleta anterior (`herdado`). | — | — |
| `cobertura` | dict | Por PTT, vizinhos elegíveis, coletados nesta rodada e herdados. | A cobertura do nível 3 é parcial por desenho (rodízio dentro do orçamento): o produto nunca extrapola para quem não foi coletado. | — |

## Limites

O custo de uma consulta varia muito por route server (medido em 2026-11-06: ~1 s de servidor no SP, ~66 s por vizinho no CE rs2 IPv4): o Alice repete a consulta no route server para cada vizinho novo. Política declarada por communities, não tráfego nem relação comercial. Os dois níveis cobrem todos os PTTs em rodízio por vizinho (os sem leitura primeiro, depois a leitura mais antiga), dentro do orçamento da rodada; quem ainda não foi lido fica sem dado (não é zero) e a idade de cada leitura é publicada. O Alice guarda cache de rotas: o dado é o do `coletado_em` de cada vizinho, que pode ter minutos ou horas de atraso; o cache de rotas em ERROR (SP, RJ e CE rs1 IPv4 em 2026-11-06) obriga a consultar o rs2. Dois route servers do mesmo PTT recebem as mesmas rotas do membro: consulta-se um só (premissa verificada em amostra, não em todos). Ponto de vista diferente do `lg_ixbr` (Telnet: o que o route server exporta para a sessão do coletor): aqui é o que o route server recebeu, aceitou ou filtrou de cada vizinho; as duas visões não se somam.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `rs_policy`

## Pendências (nao_verificado)

- Termos de uso do lg.ix.br não localizados (uso comercial).
- Medir quantos dias o rodízio leva para cobrir todos os vizinhos (orçamento padrão de 10000 requisições por rodada, 1 s de intervalo mínimo; ver `cobertura_rodizio`).
