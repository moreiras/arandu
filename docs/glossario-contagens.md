# Glossário de contagens

Este texto lista os universos que hoje aparecem no site, na API e no MCP com o mesmo nome ("ASNs brasileiros", "PTTs",
"participantes", "declarantes", "municípios", "usuários"), mas que contam coisas diferentes. Para cada um: o nome proposto para a
tela, a definição, onde o número nasce (arquivo publicado e código que o calcula), o valor medido no snapshot 2026-11-22 e onde ele
aparece hoje. É a referência para unificar rótulos (PT-15) e para a regra única de "brasileiro" da decisão D4.

Valores medidos em 2026-11-24 sobre o snapshot publicado de 2026-11-22 (arquivos de `data/published/2026-11-22/` e
`data/normalized/2026-11-22/summary/`, e a API servindo essa data); código no commit `037b1e7`. "Não medido" quer dizer que o
número não foi conferido nesta verificação, não que é zero. Caminhos de dado são relativos a `data/`; de código, à raiz do
repositório.

## Por que há vários totais

Um total depende de três escolhas, e cada página fez as suas.

1. **A regra de "brasileiro".** Há duas listas de ASNs em produção. A da delegação LACNIC com país BR (`is_br`, 9.129) é usada pelo
   índice de ASNs, pelos PTTs, pela home e pelo resumo do snapshot. A do Registro.br (`nicbr-asn-blk`, 9.150) é usada pela análise
   de rotas (`/bgp`, `/brasil/indicadores`) até a unificação; ela contém os 9.129 e mais 21 ASNs (AS174, AS2914, AS8075 e
   outros). A decisão D4 fixa `is_br` como regra única de "ASN brasileiro" em todo o site, inclusive na análise de rotas (os 21 saem
   do conjunto brasileiro), e o bloco do Registro.br para "rota brasileira".
2. **O que conta como presença.** Num PTT do IX.br um ASN pode ter sessão com o route server, constar do cadastro de participantes
   ou originar prefixo visto no looking glass, inclusive sem estar no PTT (pelo trânsito de outro). São três conjuntos de tamanho
   muito diferente (3.134, 3.792 e 40.375 ASNs).
3. **União ou soma, e qual denominador.** Somar por PTT conta o mesmo ASN, ou os mesmos usuários, uma vez por PTT: a soma dos
   usuários estimados nos 40 PTTs é 3,9 vezes os usuários do país. Restringir a quem tem UF, medição ou estimativa muda a base sem
   mudar o nome.

Regra para quem escreve tela, rota ou tool: o rótulo diz o universo ("ASNs brasileiros (LACNIC)", "com sessão em route server",
"com UF da sede conhecida"), se é união ou soma, a fonte e o mês ou snapshot. Dois números do mesmo nome com valores diferentes na
mesma página são defeito.

## ASNs

### Delegados ao Brasil (LACNIC)
- **Nome na tela:** "ASNs brasileiros (delegados pela LACNIC ao Brasil)".
- **Definição:** ASNs na lista `br_asns` do arquivo delegated-extended da LACNIC com país BR. É o `is_br` e a regra única de "ASN
  brasileiro" (D4).
- **Origem:** `normalized/{data}/summary/lacnic_delegated.json.gz`; `products/ixp_metrics/entradas.py:68-79`
  (`_load_lacnic_br_asns`), `products/ixp_metrics/documentos_asn.py:54-55,194` (`is_br`); total em
  `products/snapshot/build.py:111-112` (`summary.total_asns_br`).
- **Valor:** 9.129.
- **Onde aparece:** home, `/ases` ("9.129 ASNs"), `/snapshots`, `/ixps` (bloco `totais`), `/brasil/indicadores` (`asns`),
  `summary.json`; MCP `query(collection=asns)` com `is_br`. A descrição do campo em `api/schemas/__init__.py:107` diz "segundo o
  Registro.br", o que está errado.

### Alocados pelo Registro.br
- **Nome na tela:** "ASNs na lista do Registro.br (21 a mais que a delegação LACNIC ao Brasil)".
- **Definição:** ASNs do arquivo `nicbr-asn-blk` do Registro.br, com os blocos IPv6 e IPv4 de cada um. Contém os 9.129 `is_br`; os
  21 a mais estão listados em `analise-obint/consolidacao/v1-reproducao.md`, seção 1 (fora do repositório).
- **Origem:** `normalized/{data}/summary/registro_br.json.gz`; `products/snapshot/build.py:55-66` (`summary.registro_br_asns`, com
  o alias `m3_asns`); `products/routing_analysis/build.py:66,103` (`br_asns_registered`).
- **Valor:** 9.150.
- **Onde aparece:** `/bgp` (cartão "ASNs BR visíveis na tabela", denominador), `/brasil/indicadores` e `/seguranca-de-roteamento`
  pela classificação de rotas, painel de estatísticas (`features/dashboard/Estatisticas.tsx`); MCP `rota_analise`.

### No índice de ASNs
- **Nome na tela:** "ASNs observados no snapshot (Brasil e exterior)".
- **Definição:** todo ASN com documento no snapshot: os `is_br` mais os vistos como origem na tabela global ou nas relações e
  origens dos PTTs.
- **Origem:** `published/{data}/asns/index.json`; `products/ixp_metrics/indice_asn.py` (`_build_asn_index`),
  `products/asn_docs/build.py` (índice compacto); `summary.total_asns_global` e `summary.global_table.total_asns`.
- **Valor:** 88.866.
- **Onde aparece:** `summary.json`, `/ixps` (bloco `totais`), `/query` collection `asns` (sem filtro de `is_br`).

### Com UF da sede
- **Nome na tela:** "ASNs brasileiros com UF da sede conhecida".
- **Definição:** ASNs `is_br` cuja organização tem UF no cadastro de CNPJ geolocalizado. A UF é a da sede, não a de operação.
- **Origem:** `normalized/{data}/summary/geo_orgs.json.gz`; junção em `api/services/consultas.py:131-149`; contagem por UF em
  `api/services/perfis.py:248-259` e nas linhas por UF do histórico (`products/history/agregados.py:40-42`, soma em
  `api/services/historico.py:153,183`).
- **Valor:** 9.052. Variante: `summary.br_asns_geolocalized` = 8.984 (com coordenada), outra base.
- **Onde aparece:** `/ufs`, `/uf/:uf`, cartograma da home, série nacional e `/snapshots/diff` (`n_asns`).

### Visíveis na tabela global
- **Nome na tela:** "ASNs brasileiros (LACNIC) com prefixo visível na tabela global".
- **Definição:** `is_br` com pelo menos um prefixo IPv6 ou IPv4 originado na tabela global dos coletores.
- **Origem:** `normalized/{data}/summary/origin-prefixes-v6.json.gz` e `-v4`; `products/snapshot/build.py:116-120`
  (`summary.global_table.br_asns_in_ft`); por família em `api/snapshot_detail.py:37-42` (`br_asns_ft_v6`, `br_asns_ft_v4`).
- **Valor:** 8.732 (IPv6 7.573; IPv4 7.955). Sem nenhum prefixo visível: 397, o mesmo conjunto nas duas listas. Na base do
  Registro.br (`routing_analysis.json`, `br_asns_visible`, `products/routing_analysis/build.py:99-102`): 8.753 de 9.150, porque
  os 21 extras são todos visíveis. Em P_BR (`routing_analysis_resumo.json`, `br_origin_asns`, base Registro.br): 7.589 em IPv6 e
  7.976 em IPv4. Esses valores são de antes da regra de rota brasileira de D4 (PT-06): P_BR passou a ser só a rota com prefixo em
  bloco do Registro.br, e `br_origin_asns` conta os ASNs da lista com alguma rota nesses blocos; as rotas de ASN da lista em espaço
  de outro RIR ficam em `pbr_composition.{afi}.asn_br_fora_de_bloco`, fora do total. `br_asns_visible` mantém a base de antes
  (ASN da lista visível como origem de qualquer rota).
- **Onde aparece:** `/ases` (proposta de síntese), panorama técnico (86,7% de IPv6 sobre 8.732), `/bgp` (8.753 / 9.150),
  `/snapshots`, `SummaryTable`.

### Com IPv6 anunciado
- **Nome na tela:** "ASNs brasileiros que anunciam IPv6 na tabela global".
- **Definição:** `is_br` com `global_prefixes_v6_count > 0`.
- **Origem:** `published/{data}/asns/index.json`; `api/snapshot_detail.py:40-42` (`br_asns_ft_v6`).
- **Valor:** 7.573 (83,0% de 9.129; 86,7% de 8.732: o mesmo numerador com dois denominadores, ver acima).
- **Onde aparece:** KPI da home (`features/home/kpisBrasilEmNumeros.ts`), panorama técnico (`ResumoTecnico.tsx`,
  `AbaFamilia.tsx`), `/snapshots`.

### Com IPv6 alocado ou observado
- **Nome na tela:** "ASNs brasileiros com algum IPv6 (alocado, anunciado ou visto num PTT)"; não chamar de "com IPv6".
- **Definição:** `has_ipv6`: bloco IPv6 alocado pelo Registro.br, ou prefixo IPv6 na tabela global, ou prefixo IPv6 visto num PTT.
- **Origem:** `products/ixp_metrics/documentos_asn.py:122-125`; `products/snapshot/build.py:113-114` (`br_asns_with_ipv6`,
  `br_ipv6_pct`).
- **Valor:** 8.862 (97,08%). Só alocação (`rir_prefixes_v6_count > 0`): 8.852, sem campo de resumo próprio.
- **Onde aparece:** `components/stats/StatsOverview.tsx`, `summary.json`, outras páginas que usam `br_ipv6_pct`.

## PTTs

### PTTs do IX.br
- **Nome na tela:** "PTTs do IX.br".
- **Definição:** PTTs configurados em `config/ixps.yaml`, com coleta de looking glass e route server.
- **Origem:** `published/{data}/ixps/index.json`; `summary.ixps_configured`.
- **Valor:** 40 (40 `ok` em 2026-11-22; ap, fec e rao com tabela IPv6 vazia no looking glass, ver V1).
- **Onde aparece:** `/ixps`, home, mapa; MCP `ixp_lista`.

### IXPs fora do IX.br
- **Nome na tela:** "IXPs fora do IX.br (PeeringDB)".
- **Definição:** IXPs do PeeringDB fora do IX.br listados no snapshot.
- **Origem:** `published/{data}/external-ixps/`; rota `/external-ixps`.
- **Valor:** 56.
- **Onde aparece:** `/ixps` (seção de externos), `/ixp-externo/:code`; MCP `ixp_externo`.

### KPI misto
- **Nome na tela:** não usar sem quebra: "40 PTTs do IX.br e 56 IXPs de fora (PeeringDB)".
- **Definição:** soma das duas listas acima (`frontend/src/pages/IXPs.tsx:101,113`, "IXPs no snapshot").
- **Valor:** 96.
- **Onde aparece:** KPI de `/ixps`.

## Participantes de PTT

### Sessão com route server
- **Nome na tela:** "ASNs com sessão em route server do IX.br" (todos os países) e "ASNs brasileiros com sessão em route server do
  IX.br" (`is_br`). Não chamar de "peering direto".
- **Definição:** ASN com sessão BGP com algum route server, pelas relações do looking glass (`asn_direct`).
- **Origem:** `published/{data}/ixps/_aggregate.json` e `summary.ixp_aggregate.asn_direct_union_count`
  (`products/ixp_metrics/metricas_ixp.py:131-151`, união IPv6 ∪ IPv4); por ASN, `ixps_direct_count` em `asns/index.json`
  (`products/asn_docs/build.py:102`); por PTT, `asn_direct_union_count` em `ixps/index.json` (`products/ixp_docs/build.py:158`).
- **Valor:** união 3.134 (2.966 `is_br`, 168 estrangeiros); IPv6 2.895 (2.750 `is_br`), IPv4 3.024 (2.864 `is_br`); soma por PTT
  5.875. Por região da sede, `is_br`: SE 1.285, NE 788, S 494, CO 210, N 162, sem UF 27.
- **Onde aparece:** KPI de `/ixps` ("ASNs em peering direto", `IXPs.tsx:131-136`), `IXPTable`, `SummaryTable`, `/ixp/:code`, coluna
  "PTTs" de `/ases`; MCP `ixp_lista`, `asn_detalhe`.
- **Cuidado:** `br_asns_direct_pct` de `_aggregate.json` usa como denominador os `is_br` visíveis na família (2.750 de 7.573 em
  IPv6 = 36,31%), não os 9.129.

### Membro do cadastro do IX.br
- **Nome na tela:** "ASNs no cadastro de participantes do IX.br".
- **Definição:** ASN na lista oficial de participantes de cada PTT (`ixbr_members.json` da coleta), com ou sem sessão com route
  server.
- **Origem:** `raw/{data}/{ptt}/ixbr_members.json`; `ixbr_members_count` em `products/ixp_docs/build.py:193`; índice reverso
  `api/store.py:478-515` (`asn_ix_presence`, chave `m`).
- **Valor:** união 3.792 (3.509 `is_br`); soma por PTT 7.395. Os 3.134 com sessão estão todos entre os membros; 658 membros sem
  sessão.
- **Onde aparece:** `IXPTable` (coluna de membros), `/ixp/:code`, mapa da home, bloco de PTTs de `/uf/:uf`, `/asns/ix-presence`
  (localizador). **Defeito de nome:** na collection `asns` do `/query`, o campo `ixps_direct` vem de `m`, isto é, do cadastro
  (`api/services/consultas.py:147`), e não da sessão com route server.

### Originador
- **Nome na tela:** "ASNs cujos prefixos aparecem no IX.br" (com ou sem presença no PTT).
- **Definição:** ASN de origem de pelo menos uma rota no looking glass de algum PTT, inclusive por trânsito de outro participante.
- **Origem:** `summary.ixp_aggregate.asn_origin_union_count` e `br_asns_origin_union_count`
  (`products/ixp_metrics/metricas_ixp.py:131-153`; `br_` usa `is_br`); por família, `summary.br_ixp_origin_v6`/`_v4`.
- **Valor:** 40.375 (todos); 8.550 `is_br` (IPv6 7.437; IPv4 7.746; só IPv6 804; só IPv4 1.113; ambos 6.633).
- **Onde aparece:** KPI de `/ixps` ("ASNs originando prefixos"), `/snapshots` (8.550, lido como "ASes BR no IX.br"), `/ixp/:code`,
  panorama (`AbaInterconexao.tsx`).

### ASN brasileiro em IXP de fora
- **Nome na tela:** "ASNs brasileiros que declaram presença em IXPs fora do IX.br (PeeringDB)".
- **Definição:** união por ASN dos `is_br` listados como rede em algum dos 56 IXPs externos. A contagem por IXP hoje conta portas,
  não redes (IXE-E1).
- **Origem:** `api/snapshot_detail.py:68-70` (`external_ixps_br_asn_union_count`); `products/ixp_docs/build.py:52-56,70-71`.
- **Valor:** 179.
- **Onde aparece:** KPI de `/ixps`, panorama (`AbaInterconexao.tsx`).

## Declarantes do SICI

### Declarantes de acesso fixo
- **Nome na tela:** "CNPJs que declararam acessos fixos ao SICI (2026-09)".
- **Definição:** CNPJs no SICI de banda larga fixa do mês de referência, com ou sem outorga SCM no cadastro.
- **Origem:** `published/{data}/sici.json.gz` (`cnpjs`); `api/services/operadoras.py:149-185` (`operadora_index`, `ativo`);
  `api/routes/acessos.py:75-76,148`.
- **Valor:** 9.928 (11 sem outorga SCM no cadastro).
- **Onde aparece:** `/acessos/stats` (`total_cnpjs`, `operadoras_ativas`), `/acessos/operadoras`, `/ranking/operadoras`
  (`/rankings`), home; MCP `operadora_ranking`.

### Outorgados SCM que declararam acesso fixo
- **Nome na tela:** "CNPJs com outorga SCM que declararam acessos fixos (2026-09)".
- **Definição:** interseção dos CNPJs com outorga SCM (20.634) com os declarantes de acesso fixo.
- **Origem:** `api/routes/acessos.py:80-87` (`cobertura_declaracao.informaram_sici`); `products/outorgas/build.py:27-32,141-144`
  (`sici_ativo` nos registros SCM).
- **Valor:** 9.917 de 20.634 (48,1%); com ASN pelo mesmo CNPJ: 4.703 de 7.228 (65,1%).
- **Onde aparece:** home (cobertura de declaração), `/scms?ativo=true`, mapa de outorgas.

### Outorgados SCM com acesso fixo ou móvel
- **Nome na tela:** "CNPJs com outorga SCM que declararam acesso fixo ou móvel"; na aba SCM, usar o universo anterior.
- **Definição:** CNPJs com outorga SCM cuja soma de acesso fixo e móvel declarado é maior que zero.
- **Origem:** `api/services/perfis.py:68-82` (`ativo = acessos_fixo + acessos_movel > 0`).
- **Valor:** 9.919 (os 9.917 mais 2 que só declaram móvel).
- **Onde aparece:** `/operadoras` (filtro "apenas em operação" na aba SCM, `/outorgas?servico=SCM&ativo=true`); MCP `outorga_lista`
  com `ativo`.

### Outros universos do mesmo tema
- Declarantes de acesso móvel (SICI móvel 2026-08): 17 de 256 CNPJs com SMP (`api/routes/acessos_movel.py:76-80`).
- "Provedores fixos ativos" (`summary.provedores_fixos_ativos`, `api/snapshot_detail.py:88-90`): CNPJ com ASN **ou** com
  declaração; 12.453. "Provedores móveis ativos": 99. Nenhum dos dois é contagem de declarantes.

## CNPJs e registros de outorga

- **Nome na tela:** "CNPJs com outorga" e, separado, "registros de outorga". Nunca "outorgas" para contar empresas.
- **Definição:** o arquivo da Anatel tem uma linha por registro; um CNPJ pode ter vários (filiais, áreas, datas ou cópias que a
  normalização não distingue).
- **Origem:** `published/{data}/scm.json.gz`, `smp.json.gz`, `stfc.json.gz`, `seac.json.gz` (`total` e `unique_cnpjs`);
  `core/consulta_outorgas.py:125-139` (`estatisticas`, também `cnpjs_with_asn`); contagem por UF em
  `core/consulta_outorgas.py:113-122`, que soma registros.
- **Valor (registros / CNPJs):** SCM 21.103 / 20.634; SMP 333 / 256; STFC 5.784 / 1.685; SeAC 1.542 / 1.455. CNPJs SCM com ASN pelo
  mesmo CNPJ: 7.228; ASNs `is_br` com outorga SCM: 7.412 de 9.129.
- **Onde aparece:** cartões de `/operadoras` ("Outorgas", "CNPJs únicos", "CNPJs com ASN"), barras por UF, `/outorgas/stats`; MCP
  `outorga_lista`, `outorga_detalhe`.

## Municípios

### Tabela do IBGE (referência)
- **Nome na tela:** "municípios do Brasil (tabela do IBGE)", com nota sobre Boa Esperança do Norte/MT (5101837), criado depois do
  Censo 2022 e sem população nem domicílios do Censo.
- **Origem:** `normalized/{data}/summary/ibge_municipios.json.gz`.
- **Valor:** 5.571.
- **Onde aparece:** como cobertura do SICI fixo 2026-09 (`sici_municipios.json.gz`; `municipios_atendidos` em
  `api/routes/acessos.py:149`; KPI "Municípios com banda larga fixa declarada" da home, que hoje é igual ao universo),
  `territorio/municipios.json.gz`, `/ranking/municipios`, collection `municipios`.

### Lista do Censo 2022
- **Nome na tela:** quando for este o universo, "municípios do Censo 2022".
- **Valor:** 5.570 (sem 5101837).
- **Onde aparece:** sitemap (`config/paginas_publicas.json`, lista estática, `api/routes/sitemap.py:35,80-82`); RQUAL
  (`core/rqual.py:147`); cobertura do SICI móvel 2026-08 (`api/routes/acessos_movel.py:107`), que atende 5.570 dos 5.571.

### Reclamações (Anatel)
- **Nome na tela:** "municípios com reclamação registrada (Anatel, desde 2020)", só com códigos da tabela do IBGE.
- **Origem:** `normalized/{data}/summary/anatel_reclamacoes.json.gz` (`resumo.municipios`), exibido como `leitura.municipios` em
  `published/{data}/qualidade/reclamacoes.json.gz`; `core/reclamacoes.py:88,118`, `products/qualidade/build.py:173`.
- **Valor:** 5.573 códigos distintos em todo o período; 5.546 com reclamação nos 3 últimos anos, dos quais 2 não são municípios
  (4300001 Lagoa Mirim e 4300002 Lagoa dos Patos, RS). Que 5.573 seja 5.571 mais esses 2 é inferência pela soma; o conjunto
  completo não é gravado.
- **Onde aparece:** cabeçalho da aba de reclamações de `/qualidade`.

### Consumidor.gov.br
- **Valor:** 4.321 municípios com reclamação na janela publicada (`published/{data}/consumidor/consumidor_municipios/`).
- **Onde aparece:** `/qualidade` (aba consumidor.gov.br).

## Usuários estimados (APNIC)

Todas as linhas abaixo partem da mesma estimativa do APNIC Labs por ASN (`apnic_users`); mudam o recorte e a forma de agregar.
Não é o número que o APNIC publica para o país.

### Por AS
- **Nome na tela:** "usuários estimados (APNIC) do AS".
- **Origem:** `normalized/{data}/summary/apnic_pop.json.gz` → `apnic_users` em `published/{data}/asns/index.json`.
- **Valor:** 6.707 ASNs `is_br` com estimativa (de 9.129).
- **Onde aparece:** `/ases`, `/asn/:asn`; MCP `asn_detalhe`, `query(collection=asns)`.

### Total do país
- **Nome na tela:** "usuários estimados em ASNs brasileiros (soma APNIC por ASN)".
- **Definição:** soma de `apnic_users` dos ASNs `is_br`.
- **Origem:** `api/snapshot_detail.py:43-46` (`summary.br_apnic_users_total`); `/brasil/indicadores` (`ipv6.usuarios`,
  `prontidao.agregado.usuarios`); `territorio/rede_territorio.json.gz` (`rov.brasil.usuarios`).
- **Valor:** 161.288.456.
- **Onde aparece:** home, panorama técnico, `/ixps` (síntese e bloco `totais`), `/snapshots`, `/seguranca-de-roteamento`.

### Por UF da sede
- **Nome na tela:** "usuários estimados em ASNs com sede na UF"; no total, "… com UF da sede conhecida".
- **Definição:** a mesma soma, agrupada pela UF da sede da organização do ASN; ASNs sem UF ficam fora.
- **Origem:** `api/services/perfis.py:248-259` (`asns_por_uf`); linhas por UF do histórico (`products/history/agregados.py:40-42`).
- **Valor:** 160.714.887 no total das UFs; diferença para o total do país, 573.569, é a soma dos ASNs sem UF.
- **Onde aparece:** `/ufs`, `/uf/:uf`, cartograma, série nacional e `/snapshots/diff` (`users`); MCP `uf_detalhe`,
  `historico_mudancas`.

### Com medição de ROV
- **Nome na tela:** "usuários estimados em ASNs com medição de ROV (APNIC, ≥ 100 amostras)".
- **Origem:** `products/rede_territorio/build.py:78-96` (`calcular_rov`), campo `rov.brasil.usuarios_com_medida`.
- **Valor:** 154.943.072 (cobertura 96,1% do total); destes, 11.060.163 atrás de ROV (7,1%).
- **Onde aparece:** panorama de rede (`features/rede/PanoramaRede.tsx:83`), `/seguranca-de-roteamento`.

### Em ASNs com sessão em route server
- **Definição:** soma de `apnic_users` dos `is_br` com `ixps_direct_count ≥ 1`.
- **Valor:** 83.923.846 (52,0% do total do país). Hoje sem campo publicado; calculado nesta verificação.
- **Onde aparece:** panorama técnico (proposta de quadro por região, 52,0%).

### União por PTT (alcançáveis pelo IX.br)
- **Nome na tela:** "usuários estimados alcançáveis pelo IX.br (IPv4, sem dupla contagem)".
- **Definição:** para cada ASN `is_br` que origina prefixos IPv4 em algum PTT, usuários × fração do espaço IPv4 anunciado visível
  no IX.br, com os prefixos de todos os PTTs unidos antes do cálculo. Inclui o que chega por trânsito.
- **Origem:** `api/services/ixp_potencial.py:251` (`ixp_estimated_users_aggregate`); `api/snapshot_detail.py:61`
  (`summary.ixp_estimated_users_v4`).
- **Valor:** 61.912.578. IPv6: não medido.
- **Onde aparece:** KPI de `/ixps` ("usuários estimados"), panorama (`AbaInterconexao.tsx`, `AbaFamilia.tsx`).

### Por PTT e soma por PTT
- **Nome na tela:** por PTT, "usuários estimados alcançáveis por este PTT (IPv4)". A soma entre PTTs não deve ser exibida.
- **Definição:** a mesma conta, PTT a PTT (`api/services/ixp_potencial.py:181`, rota `/ixps/{code}/estimated-users` e
  `/ixps/estimated-users`).
- **Valor:** de 237.233 (rr) a 57.933.013 (sp); a soma dos 40 é 630.174.581, 3,9 vezes o total do país, porque o mesmo usuário
  conta em cada PTT onde o seu AS aparece.
- **Onde aparece:** `/ixps` (coluna), `/ixp/:code`; MCP `ixp_usuarios`.

## Lacunas desta versão

Não medidos aqui: número de PTTs do IX.br e externos "com AS BR presente" (KPI de `/ixps`); presença por porta contra rede nos
56 IXPs externos (medida em V1 só para alguns); contagens de sessão com route server do Alice-LG (`route_servers/`); usuários com
IPv6 por PTT. O conjunto exato dos 5.573 códigos de reclamações não é gravado no snapshot.
