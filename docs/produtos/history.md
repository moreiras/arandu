<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Histórico por snapshot

`history` · produto

Camada derivada e reconstruível (data/history/) com uma linha por ASN e snapshot, séries agregadas e um log de eventos confirmados por janela. Lê só o publicado (asns/, manifest.json) e nunca o altera; a base de tendências, de "o que mudou" e dos alertas, expostos pela API, pelo MCP e pela interface.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.history.build` |
| Chaves de junção | `asn` |
| Cenários de teste (dataset sintético) | `ptt_coleta_parcial`, `mudanca_de_origem` |

## Entradas

- produto [asn_docs](asn_docs.md)
- produto [asn_saude](asn_saude.md)

## Saídas


## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asn / is_br` | int / bool | Número do AS e se é brasileiro no snapshot. | — | — |
| `users / v6users` | int | Usuários estimados pela APNIC no snapshot (total e IPv6). Estimativa, não contagem; a média móvel de 4 semanas fica nas séries agregadas. | Ausente quando o AS não tem estimativa. | — |
| `p4 / p6` | int | Prefixos IPv6 e IPv4 do AS na tabela global do snapshot. | — | — |
| `n_ixd / n_ixm` | int | PTTs onde o AS é par direto observado (ixps_direct) e onde é membro cadastrado (ixp_member_codes). | — | — |
| `n_provedores` | int | Provedores de nível confirmado ou superior (declarado, confirmado) segundo o ARC v1. Inferência rotulada. | Ausente nos snapshots anteriores ao bloco de relações; nunca zero inventado. | — |
| `n_roa / n_aspa / rpki_valid / rpki_invalid / rpki_not_found` | int | ROAs do AS, objetos ASPA publicados por ele e prefixos por estado de validação RPKI (etapa de saúde). | Ausentes quando o documento não traz o campo-fonte nem passou pela etapa de saúde (hoje, os ASNs estrangeiros); ausência de cobertura nunca vira zero. | — |
| `tem_roa_list / tem_rpki_validation / tem_aspa_providers / tem_saude` | bool | Presença do campo-fonte no documento publicado (roa_list, rpki_validation, aspa_providers) e se o documento passou pela etapa de saúde (tem alerts), que grava esses campos sempre que há algo a dizer. Um campo está coberto quando está presente ou tem_saude é verdadeiro. | Linha gravada antes dos marcadores (regra 1) é refeita do documento publicado antes de servir de comparação; sem documento, fica sem cobertura. | — |
| `n_alertas / hash_alertas` | int / str | Quantidade de alertas do AS (só ASN BR) e hash dos ids, para detectar alerta novo ou resolvido sem guardar os conjuntos. | Só se compara entre snapshots de mesmo rules_version. | — |
| `hash_relacoes / hash_ixd / hash_ixm / hash_pfx` | str | Hash curto (sha1, 12 hex) do conjunto de provedores confirmado+, PTTs diretos, PTTs membros e prefixos globais. Mudou o hash, o gerador de eventos lê os dois documentos publicados e calcula a diferença. | — | — |
| `ixp.jsonl.gz (ixp, status, n_direct, n_br_direct, n_origin, n_br_origin, n_membros, v4_rotas, v4_prefixos, v6_rotas, v6_prefixos)` | dict | Uma linha por PTT e snapshot, do índice de PTTs publicado. status é o da coleta (ok, partial, missing, failed); eventos negativos só valem para PTT coletado. | — | — |
| `operadora.jsonl.gz / uf.jsonl.gz` | dict | Soma dos ASNs BR por CNPJ (com grupo_id, só o id) e por UF da sede da organização (não a UF dos usuários), com users_ma4, a média das amostras de usuários APNIC dos últimos 28 dias, e n_ma4, o número de amostras. | A estimativa APNIC é suavizada pela média móvel; só entram datas anteriores ou iguais à do snapshot. | — |
| `events/{date}.jsonl.gz (id, data, tipo, entidade, chave, de, para, janela, estado, confirmado, confirmado_em, revertido_em, destaque, detalhe)` | dict | Diferença observada entre este snapshot e o anterior com histórico. estado é pendente até o novo estado persistir por `janela` snapshots (contando o de origem), depois confirmado; revertido se um snapshot seguinte o desmente. Tipos e janelas (snapshots) — asn_novo/asn_sumido 2; ixp_entrada/ixp_saida (cadastral) 1; ixp_entrada_observada/ixp_saida_observada 2; provedor_novo/provedor_perdido 3; mudanca_origem 2; roa_ganho/roa_perdido 1; aspa_ganho/aspa_perdido 1; rpki_invalido_novo/rpki_invalido_resolvido 2; outorga_nova 1, outorga_baixa 2; alerta_novo/alerta_resolvido 2. | Regra versionada (eventos_regra no índice; 2 desde 2026-11-24). roa_*, aspa_* e rpki_invalido_* só se geram, confirmam ou desmentem com o campo-fonte coberto nos dois snapshots (na regra 1 a ausência contava como zero, e em 2026-07-05 o fim da cobertura de roa_list dos ASNs estrangeiros virou 50.127 roa_perdido). Snapshot de coleta parcial não gera evento negativo e não confirma nem desmente evento. Evento observado de PTT só se o PTT foi coletado por inteiro nos dois snapshots. Alertas só se comparam com o mesmo rules_version. mudanca_origem exige origem única (sem MOAS) e uma ponta brasileira; destaque quando o novo estado é RPKI inválido. provedor_* é inferência (ARC). O evento descreve a diferença, sem causa nem intenção, e leva só a chave (ASN, PTT, CNPJ, prefixo), nunca nome de empresa. | — |
| `index.json` | dict | Snapshots com histórico, estado da coleta (coleta, coleta_ok), PTTs coletados e falhos, rules_version, linhas, sha256 do conteúdo, eventos_regra (versão da regra de eventos), eventos_regenerados_em (quando a camada foi refeita por `python -m products.history.regenerar_eventos`) e built_at. | — | — |

## Limites

Camada derivada, fora de published/; reconstruível dos snapshots. Cresce com os snapshots (retenção indefinida, como o publicado; o gc não a remove). Eventos negativos só valem com coleta completa e confirmação por janela. Comparar alertas só entre snapshots de mesmo rules_version.

## Pendências

- Backfill dos 3 snapshots mais recentes e medições.
