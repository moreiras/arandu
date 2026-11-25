# Arandurápolis — dataset sintético (T2)

Mini-Brasil fictício que exercita os cruzamentos do pipeline **sem nenhum dado real**:
60 ASNs (32 provedores + 4 trânsitos BR e 24 estrangeiros), 3 PTTs (`za`, `zb`, `zc`), 12 municípios, ~150 prefixos
de documentação (198.18.0.0/15, 100.64.0.0/10, 2001:db8::/32), CNPJs fictícios com DV válido. Dois instantes
(T0 = 2026-09-13, T1 = 2026-09-20) com diferenças plantadas.

    python -m tests.synth.generate --seed 1 --out tests/data/arandurapolis      # gera a árvore (não é versionada)
    pytest tests/products                                                       # T2 (pipeline `bgp_ixp` → `snapshot_completo` sobre o dataset)
    pytest tests/products --update-golden                                       # regrava os ouros; REVISE o diff

O repositório guarda o **gerador** (`world.py`, `market.py`, `infra.py`, `generate.py`) e o **`expected/`**.

## Cenários plantados (todos asseridos em `tests/products/test_t2_pipeline.py`)

| # | Cenário | Onde |
|---|---|---|
| 1 | AS multihomed com MOAS e ROA inválido (64496/64497, 198.18.0.0/24) → `rpki_invalido`; MOAS por coletor em `origins-multi-{afi}` (rvT, rvU; mais um prefixo estrangeiro e um IPv6 de 64496) | alerts do ASN 64497; `routing_analysis.json#moas` em `tests/products/test_t2_moas.py` |
| 2 | Operadora com outorga SCM sem SICI e com usuários APNIC (64510) | `scm.json.gz` × `sici.json.gz` |
| 3 | Um CNPJ com dois ASNs (64500/64501): `acessos_compartilhados`, soma não duplica | `sici` nos docs de ASN |
| 4 | Grupos: `quadro_identico`, holding externa em comum, controle exclusivo | `grupos_societarios.json.gz` |
| 5 | PTT com coleta v6 falha (`zc`): status `partial`, sem eventos negativos | `ixps/index.json`, summary |
| 6 | Prefixo que muda de origem (198.18.24.0/21: 64502 → 64503) e vira RPKI inválido | `asns/64502`, `asns/64503` T0×T1 |
| 7 | Contatos PeeringDB nunca em `published/` (o telefone de outorga é checado na API, no T4) | varredura de `published/` |
| 8 | Município sem PTT a < 100 km (Tabajara do Norte) fica fora do raio de todos os PTTs | `Store.ixp_nearby_breakdown` |
| 9 | Membro estrangeiro só com IPv6 no `za`: originadores = união IPv6 ∪ IPv4 > max (IXP-E3) | `ixps/index.json`, `tests/products/test_t2_originadores_uniao.py` |

Também há divergência APNIC × Anatel plantada (64504 `apnic_alto`, 64505 `apnic_baixo`) e um novo membro em T1 (zb).

## O que o pipeline T2 percorre

`raw/…/bgp-*.txt` (LG sintético) → `products.bgp_routes.build` (`bgp_ixp`) → `products.ixp_metrics.build` (`metricas_ixp_asn`) → `publish.snapshot_builder`
(`snapshot_completo`, inclui outorgas, SICI, grupos e mapas) → pré-cálculo de alertas/RPKI (`saude_asn`) → `sources.socios_grupos.enrich` (`socios_grupos`).
As fontes **coletadas** entram já normalizadas (`normalized/…/summary/*.json.gz`), no formato dos coletores
(verificado pelos T1). **Fora do T2:** `products.routing_analysis.build`, `bgp_stability*` e `fulltable`
real (MRT), conferidos pelo replay sobre dados reais (`scripts/replay.py`). A exceção é o MOAS: `tests/products/test_t2_moas.py`
roda `routing_analysis` numa cópia do publicado sintético e confere a API e o MCP.

## Determinismo

`PYTHONHASHSEED` não afeta o resultado (o `grupo_id` de `sources/socios_grupos/enrich.py` usa ordem fixa).
