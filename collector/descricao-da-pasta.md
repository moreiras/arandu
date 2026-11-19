# collector/ — atalhos de compatibilidade

> Licença: AGPL-3.0-or-later — Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit

Nomes antigos dos coletores, mantidos para quem ainda os chama (`python -m collector.<nome>` ou `import collector.<nome>`). Cada arquivo
só importa o módulo novo e emite `DeprecationWarning`; o código Python do projeto não os importa (`tests/unit/test_sem_uso_dos_atalhos.py`).
Os coletores vivem em `sources/<id>/collect.py`; `_common` e `_telnet` viraram `core/common.py` e `core/telnet.py`. Detalhes em `sources/descricao-da-pasta.md`.

| Nome antigo | Módulo atual |
|---|---|
| `collector._common` | `core.common` |
| `collector._telnet` | `core.telnet` |
| `collector.anatel_scm` | `sources.anatel_scm.collect` |
| `collector.anatel_seac` | `sources.anatel_seac.collect` |
| `collector.anatel_sici` | `sources.anatel_sici.collect` |
| `collector.anatel_sici_movel` | `sources.anatel_sici_movel.collect` |
| `collector.anatel_smp` | `sources.anatel_smp.collect` |
| `collector.anatel_stfc` | `sources.anatel_stfc.collect` |
| `collector.aneel_sigel_transmission` | `sources.aneel_sigel_transmission.collect` |
| `collector.apnic_pop` | `sources.apnic_pop.collect` |
| `collector.asn_names` | `sources.asn_names.collect` |
| `collector.bgp_stability_deep` | `sources.bgp_stability_deep.collect` |
| `collector.bgp_updates_routeviews` | `sources.bgp_updates_routeviews.collect` |
| `collector.fulltable_routeviews` | `sources.fulltable_routeviews.collect` |
| `collector.ibge_bc250_rodovias` | `sources.ibge_bc250_rodovias.collect` |
| `collector.itu_transmission` | `sources.itu_transmission.collect` |
| `collector.ixbr_api` | `sources.ixbr_api.collect` |
| `collector.lacnic_delegated` | `sources.lacnic_delegated.collect` |
| `collector.lg_ixbr` | `sources.lg_ixbr.collect` |
| `collector.peeringdb_contacts` | `sources.peeringdb_contacts.collect` |
| `collector.peeringdb_ixps` | `sources.peeringdb_ixps.collect` |
| `collector.peeringdb_networks` | `sources.peeringdb_networks.collect` |
| `collector.receita_socios` | `sources.receita_socios.collect` |
| `collector.registro_br` | `sources.registro_br.collect` |
| `collector.rpki_collector` | `sources.rpki_collector.collect` |
| `collector.telegeography_cables` | `sources.telegeography_cables.collect` |
