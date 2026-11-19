<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Manifesto, resumo e detalhe do snapshot

`snapshot` · produto

Metadados do snapshot: versão do pipeline, estado da coleta, checksums, totais nacionais e o detalhe pré-calculado usado pela API.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `publish.snapshot_builder` |
| Chaves de junção | `mes` |
| Cenários de teste (dataset sintético) | `ptt_coleta_parcial` |

## Entradas

- produto [asn_docs](asn_docs.md)
- produto [ixp_docs](ixp_docs.md)
- produto [outorgas](outorgas.md)
- produto [sici](sici.md)
- fonte [fulltable_routeviews](../fontes/fulltable_routeviews.md) — uso comercial: `nao_verificado`
- fonte [registro_br](../fontes/registro_br.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `manifest.json`, `summary.json`, `snapshot_detail.json`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `pipeline_version` | str | Versão do pipeline que gerou o snapshot (arquivo VERSION). | — | snapshot → manifest.json#pipeline_version |
| `ixps_configured / ixps_collected / ixps_failed` | list[str] | IXPs configurados, coletados e que falharam na coleta. | — | snapshot → manifest.json#ixps_failed |
| `fulltable_v4_status / fulltable_v6_status / registro_br_status` | str | Estado das fontes críticas (ok, parcial, ausente). | — | snapshot → manifest.json#fulltable_v4_status |
| `geolite2_version` | str | Versão da base de geolocalização usada (AAAA-MM; GeoLite2 até 2026-10, DB-IP Lite depois). O nome do campo é histórico. | — | snapshot → manifest.json#geolite2_version |
| `checksums` | dict | SHA-256 de cada arquivo publicado; prova de imutabilidade. | — | snapshot → manifest.json#checksums |
| `total_asns_br / total_asns_global` | int | ASNs brasileiros e ASNs globais no snapshot. | — | snapshot → summary.json#total_asns_br |
| `br_asns_with_ipv6 / br_ipv6_pct` | int / float | ASNs BR com IPv6 e o percentual. | — | snapshot → summary.json#br_asns_with_ipv6 |
| `global_table` | dict | Totais da tabela global (prefixos, espaço, cobertura BR, ASNs). | — | snapshot → summary.json#global_table |
| `ixp_aggregate` | dict | Resumo da união entre IXPs. | — | snapshot → summary.json#ixp_aggregate |
| `versao` | int | Versão do formato do snapshot_detail.json. | — | snapshot → snapshot_detail.json#versao |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | snapshot → summary.json#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | snapshot → summary.json#generated_at |
| `pipeline_version` | str | Versão do pipeline que gerou o snapshot. | — | snapshot → summary.json#pipeline_version |
| `ixps_configured` | int | Quantidade de IXPs configurados. | — | snapshot → summary.json#ixps_configured |
| `ixps_ok` | int | IXPs com v6 e v4 coletados. | — | snapshot → summary.json#ixps_ok |
| `ixps_partial` | int | IXPs com só uma das famílias coletada. | — | snapshot → summary.json#ixps_partial |
| `ixps_missing` | int | IXPs sem coleta. | — | snapshot → summary.json#ixps_missing |
| `ixps_failed` | list[str] | Códigos dos IXPs que falharam. | — | snapshot → summary.json#ixps_failed |
| `fulltable_v4_status` | str | Estado da tabela global IPv4 (ok/missing). | — | snapshot → summary.json#fulltable_v4_status |
| `fulltable_v6_status` | str | Estado da tabela global IPv6 (ok/missing). | — | snapshot → summary.json#fulltable_v6_status |
| `registro_br_status` | str | Estado do arquivo do Registro.br (ok/missing). | — | snapshot → summary.json#registro_br_status |
| `total_asns_global` | int | ASNs no índice (BR ∪ vistos em IXP ∪ vistos na tabela global). | — | snapshot → summary.json#total_asns_global |
| `br_ipv6_pct` | float | % dos ASNs BR com IPv6. | — | snapshot → summary.json#br_ipv6_pct |
| `registro_br_asns` | int | ASNs no arquivo do Registro.br. | — | snapshot → summary.json#registro_br_asns |
| `m3_asns` | int | O mesmo que registro_br_asns (nome mantido por compatibilidade). | — | snapshot → summary.json#m3_asns |
| `registro_br_prefixes_v6` | int | Prefixos IPv6 alocados no Registro.br. | — | snapshot → summary.json#registro_br_prefixes_v6 |
| `m3_prefixes_v6` | int | O mesmo que registro_br_prefixes_v6 (nome mantido por compatibilidade). | — | snapshot → summary.json#m3_prefixes_v6 |
| `registro_br_prefixes_v4` | int | Prefixos IPv4 alocados no Registro.br. | — | snapshot → summary.json#registro_br_prefixes_v4 |
| `m3_prefixes_v4` | int | O mesmo que registro_br_prefixes_v4 (nome mantido por compatibilidade). | — | snapshot → summary.json#m3_prefixes_v4 |
| `registro_br_declared_space_v6` | int | Espaço IPv6 alocado segundo o Registro.br (endereços). | — | snapshot → summary.json#registro_br_declared_space_v6 |
| `m3_declared_space_v6` | int | O mesmo que registro_br_declared_space_v6 (nome mantido por compatibilidade). | — | snapshot → summary.json#m3_declared_space_v6 |
| `registro_br_declared_space_v4` | int | Espaço IPv4 alocado (endereços) segundo o Registro.br. | — | snapshot → summary.json#registro_br_declared_space_v4 |
| `m3_declared_space_v4` | int | O mesmo que registro_br_declared_space_v4 (nome mantido por compatibilidade). | — | snapshot → summary.json#m3_declared_space_v4 |
| `ft_space_v6` | int | Espaço IPv6 da tabela global (endereços). | — | snapshot → summary.json#ft_space_v6 |
| `ft_space_v4` | int | Espaço IPv4 da tabela global (endereços). | — | snapshot → summary.json#ft_space_v4 |
| `br_asns_peeringdb` | int | ASNs BR com cadastro no PeeringDB. | — | snapshot → summary.json#br_asns_peeringdb |
| `br_asns_geolocalized` | int | ASNs BR com organização geolocalizada. | — | snapshot → summary.json#br_asns_geolocalized |
| `br_asns_with_ipv6` | int | ASNs BR com IPv6. | — | snapshot → summary.json#br_asns_with_ipv6 |
| `ixp_aggregate` | dict | Resumo da união entre IXPs. | — | snapshot → summary.json#ixp_aggregate |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | snapshot → manifest.json#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | snapshot → manifest.json#generated_at |
| `ixps_configured` | list[str] | Códigos dos IXPs configurados. | — | snapshot → manifest.json#ixps_configured |
| `ixps_collected` | list[str] | Códigos dos IXPs com coleta. | — | snapshot → manifest.json#ixps_collected |
| `ixps_failed` | list[str] | Códigos dos IXPs que falharam. | — | snapshot → manifest.json#ixps_failed |
| `fulltable_v4_status` | str | Estado da tabela global IPv4. | — | snapshot → manifest.json#fulltable_v4_status |
| `fulltable_v6_status` | str | Estado da tabela global IPv6. | — | snapshot → manifest.json#fulltable_v6_status |
| `registro_br_status` | str | Estado do arquivo do Registro.br. | — | snapshot → manifest.json#registro_br_status |
| `total_asns_br` | int | ASNs brasileiros no snapshot. | — | snapshot → manifest.json#total_asns_br |
| `total_asns_global` | int | ASNs no índice global. | — | snapshot → manifest.json#total_asns_global |
| `registro_br_prefixes_v6` | int | Prefixos IPv6 do Registro.br. | — | snapshot → manifest.json#registro_br_prefixes_v6 |
| `m3_prefixes_v6` | int | O mesmo que registro_br_prefixes_v6 (nome mantido por compatibilidade). | — | snapshot → manifest.json#m3_prefixes_v6 |
| `registro_br_prefixes_v4` | int | Prefixos IPv4 do Registro.br. | — | snapshot → manifest.json#registro_br_prefixes_v4 |
| `m3_prefixes_v4` | int | O mesmo que registro_br_prefixes_v4 (nome mantido por compatibilidade). | — | snapshot → manifest.json#m3_prefixes_v4 |
| `ft_space_v6` | int | Espaço IPv6 da tabela global. | — | snapshot → manifest.json#ft_space_v6 |
| `ft_space_v4` | int | Espaço IPv4 da tabela global. | — | snapshot → manifest.json#ft_space_v4 |
| `pipeline_version` | str | Versão do pipeline. | — | snapshot → manifest.json#pipeline_version |
| `geolite2_version` | str | Versão da base de geolocalização usada (GeoLite2 até 2026-10, DB-IP Lite depois; nome histórico). | — | snapshot → manifest.json#geolite2_version |
| `checksums` | dict | SHA-256 de cada arquivo publicado. | — | snapshot → manifest.json#checksums |
| `versao` | int | Versão do formato do detalhe. | — | snapshot → snapshot_detail.json#versao |
| `date` | str | Data do snapshot. | — | snapshot → snapshot_detail.json#date |
| `summary` | dict | Conteúdo de summary.json acrescido de contagens usadas pela API (usuários estimados por IXP, provedores SICI…). | — | snapshot → snapshot_detail.json#summary |
| `manifest` | dict | Manifesto reduzido: versão do pipeline, geração, IXPs configurados/coletados/falhos e estados das fontes críticas. | — | snapshot → snapshot_detail.json#manifest |
| `checks` | dict | Resultado de cada verificação de sanidade da coleta (ptt_coletados, asns_br, prefixos, vrps, pdb_registrados): status ok/falha/sem_base/pendente. | — | snapshot → manifest.json#checks |
| `coleta_ok` | bool | Falso quando alguma verificação de sanidade falhou; não bloqueia a publicação. | — | snapshot → manifest.json#coleta_ok |
| `coleta` | str | completa, parcial ou pendente, conforme as verificações. | — | snapshot → manifest.json#coleta |
| `comparado_com` | str | Data do snapshot anterior usado como base das comparações. | — | snapshot → manifest.json#comparado_com |

## Limites

manifest.json é aditivo (layout_version e sources[] podem faltar). Snapshot sem snapshot_detail.json: backfill opcional.
