# sources/ — fontes: coleta e fontes derivadas

> Licença: AGPL-3.0-or-later — Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit

Uma pasta por fonte, com o mesmo `<id>` do catálogo (`catalog/sources/<id>.yaml`, que traz licença, termos, cadência, limites de
taxa, entradas, saídas e campos; texto em [docs/fontes/](../docs/fontes/)).

- `collect.py`: fonte bruta, que vai à rede (`python -m sources.<id>.collect --date AAAA-MM-DD [--force]`). Grava em
  `raw/{date}/` e/ou `normalized/{date}/`; o executor `arandu` registra a versão no armazém (`data/sources/<id>/`).
- `enrich.py`: fonte derivada, calculada sobre o que já foi coletado ou com consultas complementares (geocodificação, RDAP)
  (`python -m sources.<id>.enrich --date AAAA-MM-DD`).
- Outros módulos na pasta são partes da própria fonte (parser, cliente, tabela).

Regras de coleta (todas as fontes): `User-Agent` identificado, uma requisição por vez, ≥ 1 s entre requisições, `robots.txt`
respeitado, só fontes abertas; bruto com dado pessoal é agregado em fluxo e não é gravado; campos de terceiros por lista branca.
Cada fonte tem amostra em `tests/fixtures/raw/<fonte>/` (com README de origem) e teste T1 sem rede em `tests/sources/`.

As fontes curadas do catálogo (`curada_*`) e a malha municipal do IBGE não têm pasta aqui: são arquivos em `config/` ou gerados
por `scripts/` (ver `config/descricao-da-pasta.md` e `scripts/descricao-da-pasta.md`).

## Fontes

| Pasta | Fonte | Módulo |
|---|---|---|
| `abusech/` | Servidores C2 de botnets por ASN (abuse.ch, Feodo Tracker) | `collect.py` |
| `anatel_erbs/` | Anatel — estações do SMP licenciadas (ERBs) | `collect.py` |
| `anatel_fust/` | Anatel — compromissos do FUST | `collect.py` |
| `anatel_multas/` | Anatel — multas constituídas | `collect.py` |
| `anatel_outorgas/` | Cadastro de prestadoras da Anatel (CSV nacional de outorgas) | `collect.py`, `download.py`, `geo.py`, `servicos.py` |
| `anatel_pdff/` | Anatel — quadro de atribuição e destinação de faixas (PDFF) | `collect.py` |
| `anatel_reclamacoes/` | Anatel — reclamações de consumidores | `collect.py` |
| `anatel_rqual/` | Anatel — indicadores de qualidade (RQUAL) | `collect.py` |
| `anatel_satelites/` | Anatel — satélites com direito de exploração | `collect.py` |
| `anatel_scm/` | Outorgas SCM (Serviço de Comunicação Multimídia) | `collect.py` |
| `anatel_seac/` | Outorgas SeAC (TV por assinatura) | `collect.py` |
| `anatel_sici/` | Acessos de banda larga fixa (SICI/Anatel) | `collect.py` |
| `anatel_sici_movel/` | Acessos de telefonia móvel (SICI/Anatel) | `collect.py` |
| `anatel_smp/` | Outorgas SMP (Serviço Móvel Pessoal) e rede virtual | `collect.py` |
| `anatel_stfc/` | Outorgas STFC (telefonia fixa comutada) | `collect.py` |
| `aneel_sigel_transmission/` | Linhas de transmissão de alta tensão (SIGEL/ANEEL) | `collect.py` |
| `apnic_dnssec/` | Validação de DNSSEC por ASN (APNIC) | `collect.py` |
| `apnic_irov/` | Validação RPKI por ASN (APNIC I-RoV) | `collect.py` |
| `apnic_labs/` | Leitor comum das páginas de país do APNIC Labs (usado por `apnic_irov` e `apnic_dnssec`; não é fonte) | `tabela.py` |
| `apnic_pop/` | Estimativas de usuários por AS (APNIC Labs) | `collect.py` |
| `asn_names/` | Nomes de ASNs (RIPE NCC, bulk global) | `collect.py` |
| `bgp_stability_deep/` | Estabilidade BGP aprofundada (top ASes ruidosos) | `collect.py` |
| `bgp_updates_routeviews/` | Updates BGP do RouteViews São Paulo (7 dias) | `collect.py` |
| `bndes_operacoes/` | BNDES — operações de financiamento (não automáticas) a empresas de telecom | `collect.py` |
| `bogons/` | Bogons (IANA e Team Cymru) | `collect.py` |
| `caida_as2org/` | Organização por ASN (CAIDA AS-to-Organization, via AS Rank) | `collect.py` |
| `caida_asrank/` | Rank, grau e cone de ASNs (CAIDA AS Rank) | `collect.py` |
| `caida_asrel/` | Relações entre ASNs (CAIDA as-rel2) | `collect.py` |
| `caida_spoofer/` | CAIDA Spoofer — validação de endereço de origem (SAV) | `collect.py` |
| `cetic_tic_domicilios_microdados/` | TIC Domicílios — microdados (Cetic.br), estimativas por UF | `collect.py` |
| `cetic_tic_domicilios_tabelas/` | TIC Domicílios — tabelas oficiais (Cetic.br) | `collect.py` |
| `cetic_tic_provedores_tabelas/` | TIC Provedores — tabelas oficiais (Cetic.br) | `collect.py` |
| `cgu_ceis_cnep/` | CGU — sanções a empresas (CEIS e CNEP), recorte de telecom | `collect.py` |
| `cloudflare_radar/` | Cloudflare Radar — IPv6, tráfego, velocidade, BGP e quedas do Brasil (CC BY-NC 4.0) | `collect.py` |
| `cnpj_geo/` | Cadastro e geolocalização das organizações (BrasilAPI + Nominatim) | `enrich.py` |
| `consumidor_gov/` | Consumidor.gov.br — reclamações finalizadas | `collect.py` |
| `decix_alice/` | Route servers do DE-CIX Rio de Janeiro e São Paulo (Alice-LG, níveis 0, 1 e 3) | `collect.py` |
| `fulltable_routeviews/` | Tabela BGP global (RouteViews + RIPE RIS) | `collect.py`, `caminhos.py` |
| `global_prefix_geo/` | Geolocalização dos prefixos vistos nos IXPs (DB-IP City Lite) | `enrich.py` |
| `ibge_bc250_rodovias/` | Malha rodoviária (IBGE BC250) | `collect.py` |
| `ibge_censo_pnad/` | População, domicílios e uso de internet (IBGE, Censo 2022 e PNAD Contínua) | `collect.py` |
| `ioda_outages/` | Quedas de Internet por país e ASN (IODA) | `collect.py` |
| `ipv4_delegated/` | Eventos do ciclo de vida do IPv4 (delegated-extended do LACNIC) | `enrich.py` |
| `ipv4_listas/` | Listas de numeração IPv4 normalizadas (transferências, recuperação, recuperados) | `enrich.py` |
| `ipv4_subasignacao/` | Bitácora de sub-asignações de IPv4 (política LAC-2025-5, esquema hipotético) | `collect.py` |
| `ipv4_vigia/` | Vigia dos diretórios de numeração (Registro.br e LACNIC) | `collect.py` |
| `irr_route_objects/` | IRR (TC e RADB) — objetos route/route6 dos ASNs brasileiros | `collect.py` |
| `itu_transmission/` | Enlaces terrestres de transmissão (ITU BBmaps) | `collect.py` |
| `ixbr_alice/` | Sessões BGP dos route servers do IX.br (Alice-LG) | `collect.py` |
| `ixbr_alice_rotas/` | Rotas rejeitadas e communities dos membros nos route servers do IX.br (Alice-LG, níveis 2 e 3) | `collect.py` |
| `ixbr_api/` | Cadastro de membros do IX.br (dashboard.ix.br) | `collect.py` |
| `lacnic_delegated/` | ASNs delegados ao Brasil (LACNIC delegated-extended) | `collect.py` |
| `lacnic_historico/` | Histórico do LACNIC (delegated-extended diário e log de transferências) | `collect.py` |
| `lacnic_listas/` | Listas do LACNIC (transferências e infraestrutura crítica) | `collect.py` |
| `lg_ixbr/` | Looking Glasses do IX.br (tabelas BGP dos Route Servers) | `collect.py` |
| `manrs_participantes/` | MANRS — participantes do programa de operadores de rede | `collect.py` |
| `ooni_bloqueios/` | OONI — medições de interferência no Brasil, agregadas por ASN (bucket aberto) | `collect.py` |
| `peeringdb_contacts/` | Contatos de redes BR no PeeringDB (poc) | `collect.py` |
| `peeringdb_fac/` | Instalações, carriers, campus e atributos das redes do Brasil (PeeringDB) | `collect.py` |
| `peeringdb_intl_geo/` | Geolocalização de ASNs internacionais (PeeringDB org + Nominatim) | `enrich.py` |
| `peeringdb_ixps/` | IXPs e membros (PeeringDB netixlan) | `collect.py` |
| `peeringdb_networks/` | Redes brasileiras no PeeringDB (net) | `collect.py` |
| `prefix_geo/` | Geolocalização dos prefixos do Registro.br (DB-IP City Lite) | `enrich.py` |
| `rdap/` | Organizações BR a partir do Registro.br (ASN→nome/CNPJ) | `enrich.py` |
| `rdap_contatos/` | Contatos dos ASNs do Brasil no RDAP do Registro.br (administrativo e abuso) | `collect.py` |
| `receita_cnpj/` | Cadastro das empresas de telecom (dados abertos do CNPJ — Receita Federal) | `collect.py` |
| `receita_socios/` | Quadro societário (dados abertos do CNPJ — Receita Federal) | `collect.py` |
| `registro_br/` | Blocos e ASNs do Registro.br (nicbr-asn-blk) | `collect.py` |
| `registrobr_listas/` | Listas de numeração do Registro.br (transferências e recuperação) | `collect.py` |
| `rpki_collector/` | VRPs e ASPA validados (Routinator) | `collect.py` |
| `scm_geo/` | Geolocalização das outorgas SCM (Nominatim) | `enrich.py` |
| `seac_geo/` | Geolocalização das outorgas SEAC (Nominatim) | `enrich.py` |
| `shodan_exposicao/` | Shodan — contagens de serviços expostos por ASN do Brasil (API principal, atribuição obrigatória) | `collect.py` |
| `siasg_contratos/` | Compras.gov.br (PNCP, Lei 14.133) — resultados de itens por fornecedor de telecom, em rodízio | `collect.py` |
| `smp_geo/` | Geolocalização das outorgas SMP (Nominatim) | `enrich.py` |
| `socios_grupos/` | Grupos societários entre operadoras (cruzamento do QSA) | `enrich.py` |
| `stfc_geo/` | Geolocalização das outorgas STFC (Nominatim) | `enrich.py` |
| `telegeography_cables/` | Cabos submarinos (TeleGeography) | `collect.py` |
