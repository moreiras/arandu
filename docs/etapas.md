<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Etapas do pipeline (ordem calculada)

Ordem topológica a partir das `entradas` das fontes/produtos e de `depois_de`; desempate pelo campo `ordem` de cada etapa. Etapas `host` rodam no shell (`scripts/host-steps.sh`) enquanto o `arandu` roda no container worker.

| # | Etapa | Executa | Política | Tentativas | Produz | Depende de |
|---|---|---|---|---|---|---|
| 1 | `ooni_bloqueios` | `python -m sources.ooni_bloqueios.collect --date {date}` | opcional | 2 | fonte ooni_bloqueios | — |
| 2 | `manrs_participantes` | `python -m sources.manrs_participantes.collect --date {date}` | opcional | 3 | fonte manrs_participantes | — |
| 3 | `ixbr_alice` | `python -m sources.ixbr_alice.collect --date {date}` | opcional | 2 | fonte ixbr_alice | — |
| 4 | `ixbr_alice_rotas` | `python -m sources.ixbr_alice_rotas.collect --date {date}` | opcional | 1 | fonte ixbr_alice_rotas | ixbr_alice |
| 5 | `ipv4_vigia` | `python -m sources.ipv4_vigia.collect --date {date}` | opcional | 2 | fonte ipv4_vigia | — |
| 6 | `ipv4_subasignacao` | `python -m sources.ipv4_subasignacao.collect --date {date}` | opcional | 2 | fonte ipv4_subasignacao | — |
| 7 | `ioda_outages` | `python -m sources.ioda_outages.collect --date {date}` | opcional | 1 | fonte ioda_outages | — |
| 8 | `ibge_censo_pnad` | `python -m sources.ibge_censo_pnad.collect --date {date}` | opcional | 3 | fonte ibge_censo_pnad | — |
| 9 | `decix_alice` | `python -m sources.decix_alice.collect --date {date}` | opcional | 1 | fonte decix_alice | — |
| 10 | `consumidor_gov` | `python -m sources.consumidor_gov.collect --date {date}` | opcional | 3 | fonte consumidor_gov | — |
| 11 | `cetic_tic_provedores_tabelas` | `python -m sources.cetic_tic_provedores_tabelas.collect --date {date}` | opcional | 3 | fonte cetic_tic_provedores_tabelas | — |
| 12 | `cetic_tic_domicilios_tabelas` | `python -m sources.cetic_tic_domicilios_tabelas.collect --date {date}` | opcional | 3 | fonte cetic_tic_domicilios_tabelas | — |
| 13 | `cetic_tic_domicilios_microdados` | `python -m sources.cetic_tic_domicilios_microdados.collect --date {date}` | opcional | 3 | fonte cetic_tic_domicilios_microdados | — |
| 14 | `caida_spoofer` | `python -m sources.caida_spoofer.collect --date {date}` | opcional | 3 | fonte caida_spoofer | — |
| 15 | `caida_asrel` | `python -m sources.caida_asrel.collect --date {date}` | opcional | 3 | fonte caida_asrel | — |
| 16 | `caida_asrank` | `python -m sources.caida_asrank.collect --date {date}` | opcional | 3 | fonte caida_asrank | — |
| 17 | `caida_as2org` | `python -m sources.caida_as2org.collect --date {date}` | opcional | 3 | fonte caida_as2org | — |
| 18 | `bogons` | `python -m sources.bogons.collect --date {date}` | opcional | 3 | fonte bogons | — |
| 19 | `apnic_irov` | `python -m sources.apnic_irov.collect --date {date}` | opcional | 3 | fonte apnic_irov | — |
| 20 | `apnic_dnssec` | `python -m sources.apnic_dnssec.collect --date {date}` | opcional | 3 | fonte apnic_dnssec | — |
| 21 | `anatel_satelites` | `python -m sources.anatel_satelites.collect --date {date}` | opcional | 3 | fonte anatel_satelites | — |
| 22 | `anatel_rqual` | `python -m sources.anatel_rqual.collect --date {date}` | opcional | 3 | fonte anatel_rqual | — |
| 23 | `anatel_reclamacoes` | `python -m sources.anatel_reclamacoes.collect --date {date}` | opcional | 3 | fonte anatel_reclamacoes | — |
| 24 | `anatel_pdff` | `python -m sources.anatel_pdff.collect --date {date}` | opcional | 3 | fonte anatel_pdff | — |
| 25 | `anatel_multas` | `python -m sources.anatel_multas.collect --date {date}` | opcional | 3 | fonte anatel_multas | — |
| 26 | `anatel_fust` | `python -m sources.anatel_fust.collect --date {date}` | opcional | 3 | fonte anatel_fust | — |
| 27 | `anatel_erbs` | `python -m sources.anatel_erbs.collect --date {date}` | opcional | 3 | fonte anatel_erbs | — |
| 28 | `abusech` | `python -m sources.abusech.collect --date {date}` | opcional | 3 | fonte abusech | — |
| 29 | `rs_policy` | `python -m products.passos --passo rs_policy --date {date}` | opcional | 1 | parcial rs_policy | ixbr_alice_rotas |
| 30 | `regulatorio` | `python -m products.passos --passo regulatorio --date {date}` | opcional | 1 | parcial regulatorio | anatel_fust, anatel_multas, anatel_pdff, anatel_satelites, ibge_censo_pnad |
| 31 | `cetic` | `python -m products.passos --passo cetic --date {date}` | opcional | 1 | parcial cetic | cetic_tic_domicilios_microdados, cetic_tic_domicilios_tabelas, cetic_tic_provedores_tabelas |
| 32 | `anatel_outorgas` | `python -m sources.anatel_outorgas.collect --date {date}` | opcional | 3 | fonte anatel_outorgas | — |
| 33 | `lacnic_listas` | `python -m sources.lacnic_listas.collect --date {date}` | opcional | 3 | fonte lacnic_listas | — |
| 34 | `registrobr_listas` | `python -m sources.registrobr_listas.collect --date {date}` | opcional | 3 | fonte registrobr_listas | — |
| 35 | `ipv4_listas` | `python -m sources.ipv4_listas.enrich --date {date}` | opcional | 2 | fonte ipv4_listas | lacnic_listas, registrobr_listas |
| 36 | `lg_ixbr` | `python -m sources.lg_ixbr.collect --date {date}` | critica | 2 | fonte lg_ixbr | — |
| 37 | `ixbr_api` | `python -m sources.ixbr_api.collect --date {date}` | critica | 3 | fonte ixbr_api | — |
| 38 | `route_servers` | `python -m products.passos --passo route_servers --date {date}` | opcional | 1 | parcial route_servers | ixbr_alice, ixbr_api |
| 39 | `registro_br` | `python -m sources.registro_br.collect --date {date}` | critica | 3 | fonte registro_br | — |
| 40 | `irr_route_objects` | `python -m sources.irr_route_objects.collect --date {date}` | opcional | 3 | fonte irr_route_objects | registro_br |
| 41 | `lacnic_delegated` | `python -m sources.lacnic_delegated.collect --date {date}` | critica | 3 | fonte lacnic_delegated | — |
| 42 | `fulltable_routeviews` | `python -m sources.fulltable_routeviews.collect --date {date}` | critica | 3 | fonte fulltable_routeviews | registro_br |
| 43 | `peeringdb_ixps` | `python -m sources.peeringdb_ixps.collect --date {date}` | critica | 3 | fonte peeringdb_ixps | — |
| 44 | `peeringdb_networks` | `python -m sources.peeringdb_networks.collect --date {date}` | critica | 3 | fonte peeringdb_networks | lacnic_delegated |
| 45 | `peeringdb_fac` | `python -m sources.peeringdb_fac.collect --date {date}` | opcional | 3 | fonte peeringdb_fac | peeringdb_ixps, peeringdb_networks |
| 46 | `peeringdb_contacts` | `python -m sources.peeringdb_contacts.collect --date {date}` | opcional | 2 | fonte peeringdb_contacts | peeringdb_networks |
| 47 | `anatel_scm` | `python -m sources.anatel_scm.collect --date {date}` | opcional | 1 | fonte anatel_scm | anatel_outorgas |
| 48 | `anatel_sici` | `python -m sources.anatel_sici.collect --date {date}` | opcional | 1 | fonte anatel_sici | — |
| 49 | `anatel_smp` | `python -m sources.anatel_smp.collect --date {date}` | opcional | 1 | fonte anatel_smp | anatel_outorgas |
| 50 | `anatel_sici_movel` | `python -m sources.anatel_sici_movel.collect --date {date}` | opcional | 1 | fonte anatel_sici_movel | — |
| 51 | `itu_transmission` | `python -m sources.itu_transmission.collect --date {date}` | usar_ultima_valida | 1 | fonte itu_transmission | — |
| 52 | `telegeography_cables` | `python -m sources.telegeography_cables.collect --date {date}` | usar_ultima_valida | 1 | fonte telegeography_cables | — |
| 53 | `aneel_sigel_transmission` | `python -m sources.aneel_sigel_transmission.collect --date {date}` | usar_ultima_valida | 1 | fonte aneel_sigel_transmission | — |
| 54 | `anatel_stfc` | `python -m sources.anatel_stfc.collect --date {date}` | opcional | 1 | fonte anatel_stfc | anatel_outorgas |
| 55 | `anatel_seac` | `python -m sources.anatel_seac.collect --date {date}` | opcional | 1 | fonte anatel_seac | anatel_outorgas |
| 56 | `receita_cnpj` | `python -m sources.receita_cnpj.collect --date {date}` | opcional | 2 | fonte receita_cnpj | anatel_scm, anatel_seac, anatel_sici, anatel_smp, anatel_stfc |
| 57 | `siasg_contratos` | `python -m sources.siasg_contratos.collect --date {date}` | opcional | 1 | fonte siasg_contratos | anatel_scm, anatel_seac, anatel_sici, anatel_sici_movel, anatel_smp, anatel_stfc, receita_cnpj |
| 58 | `cgu_ceis_cnep` | `python -m sources.cgu_ceis_cnep.collect --date {date}` | opcional | 3 | fonte cgu_ceis_cnep | anatel_scm, anatel_seac, anatel_sici, anatel_smp, anatel_stfc |
| 59 | `bndes_operacoes` | `python -m sources.bndes_operacoes.collect --date {date}` | opcional | 2 | fonte bndes_operacoes | anatel_scm, anatel_seac, anatel_sici, anatel_smp, anatel_stfc |
| 60 | `consumidor` | `python -m products.passos --passo consumidor --date {date}` | opcional | 1 | parcial consumidor | anatel_scm, anatel_seac, anatel_smp, anatel_stfc, consumidor_gov, ibge_censo_pnad |
| 61 | `ibge_bc250_rodovias` | `python -m sources.ibge_bc250_rodovias.collect --date {date}` | opcional | 1 | fonte ibge_bc250_rodovias | — |
| 62 | `mapas_infraestrutura` | `python -m products.passos --passo mapas_infraestrutura --date {date}` | opcional | 1 | parcial mapas_infraestrutura | aneel_sigel_transmission, ibge_bc250_rodovias, itu_transmission, telegeography_cables |
| 63 | `asn_names` | `python -m sources.asn_names.collect --date {date}` | critica | 3 | fonte asn_names | — |
| 64 | `apnic_pop` | `python -m sources.apnic_pop.collect --date {date}` | opcional | 1 | fonte apnic_pop | — |
| 65 | `rdap` | `python -m sources.rdap.enrich --date {date}` | opcional | 1 | fonte rdap | registro_br |
| 66 | `shodan_exposicao` | `python -m sources.shodan_exposicao.collect --date {date}` | usar_ultima_valida | 1 | fonte shodan_exposicao | rdap |
| 67 | `rdap_contatos` | `python -m sources.rdap_contatos.collect --date {date}` | opcional | 1 | fonte rdap_contatos | rdap |
| 68 | `cnpj_geo` | `python -m sources.cnpj_geo.enrich --date {date}` | opcional | 1 | fonte cnpj_geo | rdap |
| 69 | `peeringdb_intl_geo` | `python -m sources.peeringdb_intl_geo.enrich --date {date}` | opcional | 1 | fonte peeringdb_intl_geo | ixbr_api, peeringdb_networks |
| 70 | `prefix_geo` | `python -m sources.prefix_geo.enrich --date {date}` | opcional | 1 | fonte prefix_geo | registro_br |
| 71 | `scm_geo` | `python -m sources.scm_geo.enrich --date {date}` | opcional | 1 | fonte scm_geo | anatel_scm |
| 72 | `smp_geo` | `python -m sources.smp_geo.enrich --date {date}` | opcional | 1 | fonte smp_geo | anatel_smp |
| 73 | `stfc_geo` | `python -m sources.stfc_geo.enrich --date {date}` | opcional | 1 | fonte stfc_geo | anatel_stfc |
| 74 | `seac_geo` | `python -m sources.seac_geo.enrich --date {date}` | opcional | 1 | fonte seac_geo | anatel_seac |
| 75 | `bgp_ixp` | `python -m products.bgp_routes.build --date {date}` | critica | 1 | produto bgp_ixp_normalizado | lg_ixbr |
| 76 | `metricas_ixp_asn` | `python -m products.ixp_metrics.build --date {date}` | critica | 1 | produto asn_docs, produto ixp_docs | anatel_sici, apnic_pop, asn_names, bgp_ixp, cnpj_geo, fulltable_routeviews, ixbr_api, lacnic_delegated, peeringdb_intl_geo, peeringdb_ixps, peeringdb_networks, prefix_geo, rdap, registro_br |
| 77 | `asn_nomes` | `python -m products.passos --passo asn_nomes --date {date}` | critica | 1 | parcial asn_docs | anatel_sici, apnic_pop, asn_names, bgp_ixp, cnpj_geo, fulltable_routeviews, lacnic_delegated, metricas_ixp_asn, peeringdb_intl_geo, peeringdb_ixps, peeringdb_networks, prefix_geo, rdap, registro_br |
| 78 | `asn_ixp_paths` | `python -m products.passos --passo asn_ixp_paths --date {date}` | critica | 1 | parcial asn_docs | anatel_sici, apnic_pop, asn_names, bgp_ixp, cnpj_geo, fulltable_routeviews, lacnic_delegated, metricas_ixp_asn, peeringdb_intl_geo, peeringdb_ixps, peeringdb_networks, prefix_geo, rdap, registro_br |
| 79 | `sici` | `python -m products.passos --passo sici --date {date}` | opcional | 1 | parcial sici | anatel_sici, anatel_sici_movel, apnic_pop, asn_ixp_paths, registro_br |
| 80 | `financiamento_sancoes` | `python -m products.passos --passo financiamento_sancoes --date {date}` | opcional | 1 | parcial financiamento_sancoes | anatel_scm, anatel_seac, anatel_smp, anatel_stfc, bndes_operacoes, cgu_ceis_cnep, sici |
| 81 | `penetracao` | `python -m products.passos --passo penetracao --date {date}` | opcional | 1 | parcial penetracao | ibge_censo_pnad, sici |
| 82 | `demanda_oferta` | `python -m products.passos --passo demanda_oferta --date {date}` | opcional | 1 | parcial demanda_oferta | cetic, penetracao |
| 83 | `sici_movel` | `python -m products.passos --passo sici_movel --date {date}` | opcional | 1 | parcial sici | anatel_sici, anatel_sici_movel, apnic_pop, registro_br, sici |
| 84 | `cadastro_empresas` | `python -m products.passos --passo cadastro_empresas --date {date}` | opcional | 1 | parcial cadastro_empresas | anatel_scm, anatel_seac, anatel_smp, anatel_stfc, receita_cnpj, sici, sici_movel |
| 85 | `outorgas_scm` | `python -m products.passos --passo outorgas_scm --date {date}` | opcional | 1 | parcial outorgas | anatel_scm, anatel_seac, anatel_sici, anatel_smp, anatel_stfc, registro_br, scm_geo, seac_geo, sici, smp_geo, stfc_geo |
| 86 | `outorgas_demais` | `python -m products.passos --passo outorgas_demais --date {date}` | opcional | 1 | parcial outorgas | anatel_scm, anatel_seac, anatel_sici, anatel_smp, anatel_stfc, outorgas_scm, registro_br, scm_geo, seac_geo, smp_geo, stfc_geo |
| 87 | `qualidade` | `python -m products.passos --passo qualidade --date {date}` | opcional | 1 | parcial qualidade | anatel_reclamacoes, anatel_rqual, ibge_censo_pnad, outorgas_demais, outorgas_scm, sici, sici_movel |
| 88 | `erbs` | `python -m products.passos --passo erbs --date {date}` | opcional | 1 | parcial erbs | anatel_erbs, ibge_censo_pnad, outorgas_demais, sici_movel |
| 89 | `ixp_indice` | `python -m products.passos --passo ixp_indice --date {date}` | critica | 1 | parcial ixp_docs | bgp_ixp, fulltable_routeviews, ixbr_api, lacnic_delegated, metricas_ixp_asn, peeringdb_ixps, registro_br |
| 90 | `global_prefix_geo` | `python -m sources.global_prefix_geo.enrich --date {date}` | opcional | 1 | fonte global_prefix_geo | bgp_ixp, prefix_geo |
| 91 | `receita_socios` | `python -m sources.receita_socios.collect --date {date}` | usar_ultima_valida | 1 | fonte receita_socios | — |
| 92 | `socios_grupos` | `python -m sources.socios_grupos.enrich --date {date}` | opcional | 1 | fonte socios_grupos | anatel_scm, anatel_seac, anatel_smp, anatel_stfc, receita_cnpj, receita_socios |
| 93 | `grupos_societarios` | `python -m products.passos --passo grupos_societarios --date {date}` | opcional | 1 | parcial grupos_societarios | socios_grupos |
| 94 | `rpki_collector` | `python -m sources.rpki_collector.collect --date {date}` | opcional | 1 | fonte rpki_collector, produto rpki | — |
| 95 | `asn_indice` | `python -m products.passos --passo asn_indice --date {date}` | critica | 1 | parcial asn_docs | anatel_sici, apnic_pop, asn_names, bgp_ixp, cnpj_geo, fulltable_routeviews, lacnic_delegated, metricas_ixp_asn, peeringdb_intl_geo, peeringdb_ixps, peeringdb_networks, prefix_geo, rdap, registro_br, rpki_collector |
| 96 | `exposicao` | `python -m products.passos --passo exposicao --date {date}` | opcional | 1 | parcial exposicao | asn_indice, shodan_exposicao |
| 97 | `instalacoes` | `python -m products.passos --passo instalacoes --date {date}` | opcional | 1 | parcial instalacoes | asn_indice, peeringdb_fac |
| 98 | `abuso_agregado` | `python -m products.passos --passo abuso_agregado --date {date}` | opcional | 1 | parcial abuso_agregado | abusech, asn_indice |
| 99 | `as2org` | `python -m products.passos --passo as2org --date {date}` | opcional | 1 | parcial as2org | asn_indice, caida_as2org |
| 100 | `bloqueios` | `python -m products.passos --passo bloqueios --date {date}` | opcional | 1 | parcial bloqueios | asn_indice, ooni_bloqueios |
| 101 | `contratos` | `python -m products.passos --passo contratos --date {date}` | opcional | 1 | parcial contratos | asn_indice, siasg_contratos |
| 102 | `seguranca_asn` | `python -m products.passos --passo seguranca_asn --date {date}` | opcional | 1 | parcial seguranca_asn | apnic_dnssec, apnic_irov, asn_indice, bogons, caida_asrank, sici |
| 103 | `sici_indicadores` | `python -m products.passos --passo sici_indicadores --date {date}` | opcional | 1 | parcial sici_indicadores | asn_indice, grupos_societarios, outorgas_scm, sici |
| 104 | `mapas_geo` | `python -m products.passos --passo mapas_geo --date {date}` | critica | 1 | parcial mapas_prefixos | asn_indice, bgp_ixp, cnpj_geo, fulltable_routeviews, global_prefix_geo, peeringdb_intl_geo, prefix_geo, registro_br |
| 105 | `ixp_externos` | `python -m products.passos --passo ixp_externos --date {date}` | opcional | 1 | parcial ixp_docs | asn_indice, bgp_ixp, fulltable_routeviews, ixbr_api, lacnic_delegated, peeringdb_ixps, registro_br |
| 106 | `cdns` | `python -m products.passos --passo cdns --date {date}` | opcional | 1 | parcial cdns | ixp_externos, ixp_indice, metricas_ixp_asn |
| 107 | `mapas_hilbert` | `python -m products.passos --passo mapas_hilbert --date {date}` | critica | 1 | parcial mapas_prefixos | asn_indice, bgp_ixp, cnpj_geo, fulltable_routeviews, global_prefix_geo, peeringdb_intl_geo, prefix_geo, registro_br |
| 108 | `snapshot_resumo` | `python -m products.passos --passo snapshot_resumo --date {date}` | critica | 1 | parcial snapshot | asn_indice, fulltable_routeviews, ixp_indice, mapas_hilbert, metricas_ixp_asn, registro_br |
| 109 | `decix_rs` | `python -m products.passos --passo decix_rs --date {date}` | opcional | 1 | parcial decix_rs | decix_alice, ixp_externos, ixp_indice, metricas_ixp_asn |
| 110 | `snapshot_completo` | `python -m publish.snapshot_builder --date {date}` | critica | 1 | parcial snapshot, parcial outorgas, parcial sici, parcial grupos_societarios, parcial mapas_infraestrutura, parcial mapas_prefixos, parcial cdns, parcial ixp_docs | lacnic_listas, metricas_ixp_asn, registrobr_listas, rpki_collector |
| 111 | `routing_analysis` | `python -m products.routing_analysis.build --date {date}` | opcional | 1 | produto routing_analysis | asn_indice, asn_names, fulltable_routeviews, registro_br, rpki_collector, snapshot_completo |
| 112 | `bgp_updates_routeviews` | `python -m sources.bgp_updates_routeviews.collect --date {date}` | opcional | 1 | fonte bgp_updates_routeviews | fulltable_routeviews, registro_br |
| 113 | `bgp_stability` | `python -m products.bgp_stability.build --date {date}` | opcional | 1 | parcial bgp_stability | asn_indice, bgp_updates_routeviews, snapshot_completo |
| 114 | `bgp_stability_deep_coleta` | `python -m sources.bgp_stability_deep.collect --date {date}` | opcional | 1 | fonte bgp_stability_deep | bgp_stability, bgp_updates_routeviews, fulltable_routeviews |
| 115 | `bgp_stability_deep_publicacao` | `python -m products.bgp_stability.deep --date {date}` | opcional | 1 | produto bgp_stability | asn_names, bgp_stability_deep_coleta, bgp_updates_routeviews |
| 116 | `cloudflare_radar` | `python -m sources.cloudflare_radar.collect --date {date}` | usar_ultima_valida | 2 | fonte cloudflare_radar | — |
| 117 | `radar` | `python -m products.passos --passo radar --date {date}` | opcional | 1 | parcial radar | asn_indice, cloudflare_radar |
| 118 | `lacnic_historico` | `python -m sources.lacnic_historico.collect --tipo delegated` | opcional | 1 | fonte lacnic_historico | — |
| 119 | `ipv4_delegated` | `python -m sources.ipv4_delegated.enrich --date {date}` | opcional | 2 | fonte ipv4_delegated | lacnic_delegated, lacnic_historico |
| 120 | `ipv4` | `python -m products.passos --passo ipv4 --date {date}` | opcional | 1 | parcial ipv4 | asn_indice, ipv4_delegated, ipv4_listas |
| 121 | `ipv4_uso` | `python -m products.passos --passo ipv4_uso --date {date}` | opcional | 1 | parcial ipv4_uso | ipv4 |
| 122 | `ipv4_subasig` | `python -m products.passos --passo ipv4_subasig --date {date}` | opcional | 1 | parcial ipv4_subasig | ipv4_uso |
| 123 | `as_relationships` | `python -m products.as_relationships.build --date {date}` | opcional | 1 | produto as_relationships, parcial asn_docs | asn_ixp_paths, bgp_ixp, caida_as2org, caida_asrel, fulltable_routeviews, lg_ixbr, metricas_ixp_asn, registro_br, rpki_collector, rs_policy, sici |
| 124 | `regiao` | `python -m products.regiao.build --date {date}` | opcional | 1 | produto regiao_municipios | anatel_sici, anatel_sici_movel, as_relationships, cnpj_geo, metricas_ixp_asn, prefix_geo, registro_br, sici, sici_movel |
| 125 | `rede_territorio` | `python -m products.rede_territorio.build --date {date}` | opcional | 1 | produto rede_territorio | anatel_sici, apnic_irov, apnic_pop, asn_indice, caida_asrel, regiao, seguranca_asn, sici |
| 126 | `saude_asn` | `python -m publish.snapshot_builder --date {date} --asn-health-only` | opcional | 1 | produto asn_saude, refresca asn_docs, refresca snapshot | anatel_sici, as_relationships, asn_indice, asn_ixp_paths, asn_nomes, cdns, grupos_societarios, ixp_externos, ixp_indice, mapas_geo, mapas_hilbert, mapas_infraestrutura, metricas_ixp_asn, outorgas_demais, outorgas_scm, rpki_collector, sici, sici_movel, snapshot_completo, snapshot_resumo |
| 127 | `prontidao` | `python -m products.prontidao.build --date {date}` | opcional | 1 | produto prontidao | apnic_irov, bogons, caida_spoofer, irr_route_objects, saude_asn, seguranca_asn |
| 128 | `manrs` | `python -m products.manrs.build --date {date}` | opcional | 1 | produto manrs_agregado | manrs_participantes, prontidao |
| 129 | `manifesto` | `python -m publish.manifesto --date {date}` | critica | 1 | produto snapshot | abuso_agregado, as2org, asn_indice, asn_ixp_paths, asn_nomes, bgp_stability, bgp_stability_deep_publicacao, bloqueios, cadastro_empresas, cdns, cetic, consumidor, contratos, demanda_oferta, erbs, exposicao, financiamento_sancoes, fulltable_routeviews, grupos_societarios, instalacoes, ipv4, ipv4_subasig, ipv4_uso, ixp_externos, ixp_indice, lacnic_listas, manrs, mapas_geo, mapas_hilbert, mapas_infraestrutura, metricas_ixp_asn, outorgas_demais, outorgas_scm, penetracao, prontidao, qualidade, radar, rede_territorio, regiao, registro_br, registrobr_listas, regulatorio, route_servers, routing_analysis, rs_policy, saude_asn, seguranca_asn, sici, sici_indicadores, sici_movel, snapshot_resumo |
| 130 | `host_warmup` | `docker compose exec -T api python -c <POST /api/v1/warmup>` (host) | opcional | 1 | — | saude_asn |
| 131 | `host_basemap_build` | `bash scripts/build-basemap-tiles.sh --date {date}` (host) | opcional | 1 | — | host_warmup |
| 132 | `host_basemap_validate` | `bash scripts/validate-basemap-tiles.sh --date {date}` (host) | opcional | 1 | — | host_basemap_build |
| 133 | `host_disk_report` | `bash scripts/disk-report.sh --date {date}` (host) | opcional | 1 | — | host_basemap_validate |
| 134 | `history` | `python -m products.history.build --date {date}` | opcional | 1 | produto history | as_relationships, metricas_ixp_asn, saude_asn |
| 135 | `transito` | `python -m products.transito.build --date {date}` | opcional | 1 | produto transito | as_relationships, caida_as2org, metricas_ixp_asn, registro_br |
