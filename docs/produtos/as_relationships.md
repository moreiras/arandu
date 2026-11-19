<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Relações entre ASNs (ARC v2)

`as_relationships` · produto

Relações provedor-cliente, par e irmãos entre ASNs com ao menos um brasileiro, inferidas com evidência explícita, probabilidade e nível (declarado, confirmado, provável, possível). Usa a rampa dos route servers do IX.br, os caminhos dos coletores (com ponto de observação e propagação valley-free), o ASPA e o CAIDA como prior. Substitui a leitura de "vizinho à esquerda" como provedor. Na v2 um Naive Bayes iterativo refina o veredito (com abstenção e calibração), os irmãos (CNPJ raiz e organização do CAIDA) viram s2s, o grafo p2c é acíclico, v6 e v4 divergentes com força viram `complexa` e a relação publicada só muda depois de persistir (histerese).

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.as_relationships.build` |
| Chaves de junção | `asn` |
| Cenários de teste (dataset sintético) | `cnpj_dois_asns` |

## Entradas

- fonte [fulltable_routeviews](../fontes/fulltable_routeviews.md) — uso comercial: `nao_verificado`
- fonte [lg_ixbr](../fontes/lg_ixbr.md) — uso comercial: `nao_verificado`
- fonte [rpki_collector](../fontes/rpki_collector.md) — uso comercial: `nao_verificado`
- fonte [caida_asrel](../fontes/caida_asrel.md) — uso comercial: `nao_verificado`
- fonte [caida_as2org](../fontes/caida_as2org.md) — uso comercial: `nao_verificado`
- fonte [registro_br](../fontes/registro_br.md) — uso comercial: `nao_verificado`
- produto [rs_policy](rs_policy.md)

## Saídas

- **Publicado:** `as_relationships.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `relacoes[].a / b / tipo` | int / int / str | Elo entre os ASNs a e b. Em p2c, a é provedor de b; em p2p, s2s e complexa, a < b. tipo pode ser sem_classificacao (inclui a abstenção e o elo rebaixado por ciclo). | Inferência rotulada; só entra o elo com ao menos um ASN brasileiro. | as_relationships → as_relationships.json.gz#relacoes |
| `relacoes[].p` | float | Probabilidade posterior da relação indicada (Naive Bayes iterativo da v2, recalibrada por temperatura); `evid.refino.p_v1` guarda a da v1. | Calibração medida na régua (sem ASPA, contra o ASPA, validação cruzada); `calibracao[afi].p_calibrada` diz se o ECE ficou dentro do limite. Abaixo de 0,5 o elo é abstido (sem_classificacao). | as_relationships → as_relationships.json.gz#relacoes |
| `relacoes[].nivel` | str | declarado (ASPA positivo), confirmado (p ≥ 0,95 e 2 fontes independentes), provavel (p ≥ 0,70 e 1 fonte independente) ou possivel. O CAIDA e os irmãos sozinhos nunca passam de possivel. | Fontes independentes são ASPA, rampa dos route servers, coletores e clique. Um p2c `provavel` cujo estrato é `conflito` ou `sem_evidencia` é publicado como `possivel` (`evid.refino.rebaixado_por_estrato`); `declarado` e `confirmado` não são tocados. | as_relationships → as_relationships.json.gz#relacoes |
| `relacoes[].estrato / p_calibrada` | str / float ou null | Só em p2c. `estrato` é a evidência independente do elo vista do provedor inferido: `ambos` (CAIDA concorda e a tripla está confirmada), `so_caida`, `so_tripla`, `conflito` (um confirma e o outro contradiz) ou `sem_evidencia`. `p_calibrada` é a taxa de acerto observada contra o ASPA (régua sem o ASPA como entrada) nesse estrato e família de endereço, só para `ambos` e `so_caida` com `n_vps` > 0; nos demais é null. | Medido: ECE da `p_calibrada` por validação cruzada por ASN de 0,0005 (v6) e 0,010 (v4); `so_tripla` tem 38 eventos e não é calibrável. CAIDA e tripla vêm dos mesmos coletores do ARC: são independentes do prior de distância ao clique, não dos dados de caminho. O ASPA tende a subestimar por omissão. Tabela e data em `estratos` do documento. | as_relationships → as_relationships.json.gz#relacoes |
| `relacoes[].afi` | list[str] | Famílias de endereço em que a relação foi inferida; v6 e v4 divergentes viram duas linhas com afi_divergente. | — | as_relationships → as_relationships.json.gz#relacoes |
| `relacoes[].evid` | dict | Evidência por fonte (rs, colecao, aspa, caida, clique, irmaos), as fontes que sustentam a relação e a hipótese contrária quando alguma fonte independente a apoia (contra). | ASPA é evidência de alto peso, não veto; a divergência com o BGP aparece em contra. | as_relationships → as_relationships.json.gz#relacoes |
| `relacoes[].n_vps / n_ptt` | int | Maior número de pontos de observação dos coletores e de PTTs com a rampa que viram o elo. | — | as_relationships → as_relationships.json.gz#relacoes |
| `relacoes[].visto_em` | str | Data do snapshot em que a relação foi inferida. | — | as_relationships → as_relationships.json.gz#relacoes |
| `relacoes[].pendente / mudou_em` | dict / str | Histerese (E6). `tipo`, `a`, `b`, `p` e `nivel` são o ESTADO publicado; `pendente` é uma mudança vista mas ainda não confirmada (proposta, desde quando, nº de gerações de evidência). `mudou_em` marca o snapshot em que o estado mudou. | A mudança só vira estado depois de `persistencia` coletas semanais distintas com a mesma proposta (dois snapshots diários sobre a mesma coleta não contam). ASPA positivo muda na hora. | as_relationships → as_relationships.json.gz#relacoes |
| `relacoes[] com tipo complexa` | dict | v6 e v4 divergem com força (p ≥ 0,8 e nível ≥ provável nas duas). `evid.complexa` traz o subtipo (hibrida = p2c numa família e p2p na outra; inversa = p2c nos dois sentidos) e a visão de cada família. | Inferência; o elo complexo não conta como provedor nem como cliente em `n_provedores`, nos eventos do histórico nem no cone do `transito`. | as_relationships → as_relationships.json.gz#relacoes |
| `mudancas / estabilidade / refino / restricoes / calibracao / politica_rs / estratos` | dict | Mudanças de estado confirmadas no snapshot (de → para), contagens da histerese, iterações do Naive Bayes por família, irmãos/ciclos/complexas aplicados, temperatura e ECE da calibração e cobertura do rs_policy como característica; `estratos` traz a configuração do rebaixo e das `p_calibrada` (data da medição) e a contagem de elos por estrato e de rebaixados. | — | as_relationships → as_relationships.json.gz#mudancas; as_relationships → as_relationships.json.gz#estabilidade; as_relationships → as_relationships.json.gz#refino; as_relationships → as_relationships.json.gz#restricoes; as_relationships → as_relationships.json.gz#calibracao; as_relationships → as_relationships.json.gz#estratos |
| `clique` | dict | ASNs do topo (clique sem provedor) por família, detectados nos caminhos dos coletores; vazio sem coletores. | — | as_relationships → as_relationships.json.gz#clique |
| `resumo` | dict | Contagem de elos por tipo/nível. | — | as_relationships → as_relationships.json.gz#resumo |
| `entradas / diagnostico` | dict | O que foi usado (coletores, objetos ASPA, data do CAIDA) e contadores de sanitização por família. | — | as_relationships → as_relationships.json.gz#entradas |

## Limites

A v2 melhora a estabilidade e a abstenção, mas a verdade de referência (ASPA) é pequena e enviesada, então precisão e calibração medidas são limites. Sem os caminhos dos coletores não há clique nem propagação, e nenhum elo passa de provável. Elos sem ASN brasileiro não são publicados. O CAIDA (rótulo usado como característica, com o erro aprendido) e os coletores compartilham os mesmos VPs (circularidade). O rs_policy cobre poucos PTTs e ASNs, então quase não discrimina. O IRR não entra como evidência de relação (o coletor guarda só route e a existência do aut-num, não import/export). Feedback de operadores e elos ocultos (TopoScope) não foram entregues.

## Pendências

- Revisão pelo mantenedor da linguagem pública de "provedor" (níveis e ressalvas).
- Feedback de operadores e detecção de elos ocultos (E7), fora desta entrega.
