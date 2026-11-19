<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Rejeições, communities e política de roteamento nos route servers do IX.br

`rs_policy` · produto

Por PTT e por ASN: rotas que o route server rejeitou, por motivo decodificado (RPKI inválido, bogon, inválido no Registro.br, nunca via route server, blackhole…) com amostra de prefixos; uso das communities de ação nas rotas recebidas (não exportar para AS, exportar somente para, por RIR, por PTT, blackhole); perfil de política (aberto, seletivo, restritivo) INFERIDO por heurística documentada; explorador de communities (quem usa cada uma) e grafo declarado "não exporto para". Cobertura de cada coleta em todo bloco: ASN não coletado não tem perfil.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.rs_policy.build` |
| Chaves de junção | `ixp`, `asn` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [ixbr_alice_rotas](../fontes/ixbr_alice_rotas.md) — uso comercial: `nao_verificado`
- fonte [ixbr_alice](../fontes/ixbr_alice.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `rs_policy/ixps.json.gz`, `rs_policy/asns.json.gz`, `rs_policy/communities.json.gz`, `rs_policy/grafo.json.gz`, `rs_policy/linhas.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ixps[ixp].rejeicoes` | dict | Cobertura da coleta de nível 2, ASNs com rota rejeitada, rotas rejeitadas, rotas com motivo decodificado (e a soma dos motivos, que passa do total quando uma rota tem mais de um), motivos (código, rótulo, rotas, ASNs) e a lista de ASNs por rotas rejeitadas. | Contagem exata sobre as rotas do vizinho (filters_available do Alice); só entram os vizinhos coletados (cobertura no bloco). | rs_policy → rs_policy/ixps.json.gz#ixps |
| `ixps[ixp].politica` | dict | Cobertura do nível 3, ASNs com dado, contagem de perfis, ASNs por classe de ação, blackhole e estados RPKI das rotas recebidas. | Só dos vizinhos coletados (rodízio dentro do orçamento); perfil é inferido. | rs_policy → rs_policy/ixps.json.gz#ixps |
| `asns[asn].ixps[ixp].rejeicoes` | dict | Rotas rejeitadas do ASN no PTT, por motivo, com até 5 prefixos de amostra por motivo. | A amostra de prefixos é parcial (as primeiras 250 rotas da página); o total e as contagens são exatos. | rs_policy → rs_policy/asns.json.gz#asns |
| `asns[asn].ixps[ixp].politica` | dict | Perfil (aberto, seletivo, restritivo), critério, ações por classe e alvo (fração das rotas), blackhole e RPKI das rotas recebidas. | Perfil INFERIDO: restritivo = 'exportar somente para' em 50% ou mais das rotas (ou 'não exportar para' 50 ASNs ou mais em 50% ou mais); seletivo = alguma ação em 10% ou mais; aberto = o resto; sem perfil com menos de 10 rotas. É a declaração do membro, não tráfego nem relação comercial. | rs_policy → rs_policy/asns.json.gz#asns |
| `asns[asn].evidencia_rs` | dict | Rotas rejeitadas pelo route server por tipo (RPKI inválido, bogon, inválido no Registro.br, nos RIRs, comprimento, nunca via route server…), somadas nos PTTs coletados. | Evidência DO route server (insumo possível para a prontidão), não o veredito sobre o ASN; ainda não entra nas regras da prontidão. | rs_policy → rs_policy/asns.json.gz#asns |
| `communities[]` | list | Por community (padrão, grande ou estendida), classe, rótulo, forma da decodificação e, por PTT, ASNs que a usam, rotas e os 10 que mais usam. | `forma` = equivalente_padrao quando a community padrão (65000:N) ou estendida (rt:65000:N) foi lida como a grande 65000:0:N do dicionário (equivalência assumida pela forma). | rs_policy → rs_policy/communities.json.gz#communities |
| `arestas[]` | list | Relações declaradas por communities (de → para, por PTT): não exporta para AS, exporta somente para AS, com as rotas e a fração das rotas do ASN. | Declaração por rota recebida, só de quem foi coletado; complementa o peering inferido do AS_PATH, não o substitui. | rs_policy → rs_policy/grafo.json.gz#arestas |
| `rs_communities / rs_filtradas` | list | Linhas por (PTT, ASN, community, sem a classe informativa) e por (PTT, ASN, motivo) para o /query. | — | rs_policy → rs_policy/linhas.json.gz#rs_communities; rs_policy → rs_policy/linhas.json.gz#rs_filtradas |
| `snapshot_date` | str | Data do snapshot em que o artefato foi gerado. | — | rs_policy → rs_policy/ixps.json.gz#snapshot_date; rs_policy → rs_policy/asns.json.gz#snapshot_date; rs_policy → rs_policy/communities.json.gz#snapshot_date; rs_policy → rs_policy/grafo.json.gz#snapshot_date; rs_policy → rs_policy/linhas.json.gz#snapshot_date |
| `generated_at` | str | Instante UTC em que o artefato foi gerado. | — | rs_policy → rs_policy/ixps.json.gz#generated_at; rs_policy → rs_policy/asns.json.gz#generated_at; rs_policy → rs_policy/communities.json.gz#generated_at; rs_policy → rs_policy/grafo.json.gz#generated_at; rs_policy → rs_policy/linhas.json.gz#generated_at |
| `fonte` | str | Fonte das rotas (Alice-LG do IX.br). | — | rs_policy → rs_policy/ixps.json.gz#fonte; rs_policy → rs_policy/asns.json.gz#fonte; rs_policy → rs_policy/communities.json.gz#fonte; rs_policy → rs_policy/grafo.json.gz#fonte; rs_policy → rs_policy/linhas.json.gz#fonte |
| `versao_alice` | str | Versão do Alice-LG que respondeu. | — | rs_policy → rs_policy/ixps.json.gz#versao_alice; rs_policy → rs_policy/asns.json.gz#versao_alice; rs_policy → rs_policy/communities.json.gz#versao_alice; rs_policy → rs_policy/grafo.json.gz#versao_alice; rs_policy → rs_policy/linhas.json.gz#versao_alice |
| `coletado_nivel2` | str | Instante UTC em que a coleta de nível 2 (rotas rejeitadas) foi gerada; o dado de cada vizinho tem a data própria em coletado_de e coletado_ate. | — | rs_policy → rs_policy/ixps.json.gz#coletado_nivel2; rs_policy → rs_policy/asns.json.gz#coletado_nivel2; rs_policy → rs_policy/communities.json.gz#coletado_nivel2; rs_policy → rs_policy/grafo.json.gz#coletado_nivel2; rs_policy → rs_policy/linhas.json.gz#coletado_nivel2 |
| `coletado_nivel3` | str | Instante UTC em que a coleta de nível 3 (rotas recebidas, communities) foi gerada; vizinhos herdados de rodada anterior têm data própria. | — | rs_policy → rs_policy/ixps.json.gz#coletado_nivel3; rs_policy → rs_policy/asns.json.gz#coletado_nivel3; rs_policy → rs_policy/communities.json.gz#coletado_nivel3; rs_policy → rs_policy/grafo.json.gz#coletado_nivel3; rs_policy → rs_policy/linhas.json.gz#coletado_nivel3 |
| `requisicoes_nivel2` | int | Requisições feitas ao Alice na rodada de nível 2 (inclui as do nível 3 quando a rodada é conjunta). | — | rs_policy → rs_policy/ixps.json.gz#requisicoes_nivel2; rs_policy → rs_policy/asns.json.gz#requisicoes_nivel2; rs_policy → rs_policy/communities.json.gz#requisicoes_nivel2; rs_policy → rs_policy/grafo.json.gz#requisicoes_nivel2; rs_policy → rs_policy/linhas.json.gz#requisicoes_nivel2 |
| `requisicoes_nivel3` | int | Requisições feitas ao Alice na rodada de nível 3 (a rodada é a mesma do nível 2 quando coletados juntos). | — | rs_policy → rs_policy/ixps.json.gz#requisicoes_nivel3; rs_policy → rs_policy/asns.json.gz#requisicoes_nivel3; rs_policy → rs_policy/communities.json.gz#requisicoes_nivel3; rs_policy → rs_policy/grafo.json.gz#requisicoes_nivel3; rs_policy → rs_policy/linhas.json.gz#requisicoes_nivel3 |
| `rs_pulados` | list | Route servers tirados da rodada de coleta por lentidão (3 consultas seguidas acima do limite): os vizinhos deles não foram coletados nesta rodada (ficam com a coleta anterior, se houver). | A cobertura de cada PTT traz pulados_lentos; ausência de dado de um PTT pode ser isso, não ausência de política. | rs_policy → rs_policy/ixps.json.gz#rs_pulados; rs_policy → rs_policy/asns.json.gz#rs_pulados; rs_policy → rs_policy/communities.json.gz#rs_pulados; rs_policy → rs_policy/grafo.json.gz#rs_pulados; rs_policy → rs_policy/linhas.json.gz#rs_pulados |
| `parametros` | dict | Limites da heurística do perfil e da amostra (amostra de prefixos, mínimo de rotas, frações, alvos). | — | rs_policy → rs_policy/ixps.json.gz#parametros; rs_policy → rs_policy/asns.json.gz#parametros; rs_policy → rs_policy/communities.json.gz#parametros; rs_policy → rs_policy/grafo.json.gz#parametros; rs_policy → rs_policy/linhas.json.gz#parametros |
| `total` | int | Quantidade de itens da lista do artefato. | — | rs_policy → rs_policy/communities.json.gz#total; rs_policy → rs_policy/grafo.json.gz#total |
