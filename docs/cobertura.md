# Cobertura API × MCP × interface

Gerado por `python3 scripts/gen_cobertura.py` a partir do OpenAPI, do MCP, do frontend e de `serve/capabilities/`.
Não edite à mão. Rota nova precisa de uma entrada em `serve/capabilities/_manuais.yaml` (ou de uma capacidade declarada); lacuna
sem justificativa falha o CI. Alias `deprecated` ficam de fora: valem pelas rotas que os substituem.

- Rotas de dados (GET, não deprecated): **177**; com tool no MCP: **141**; consumidas pela interface: **145**.
- Pendências marcadas (`pendente:`): **0**; lacunas sem justificativa: **0**.
- Tools do MCP geradas de capacidade declarada: **2** de 58.

| Rota | MCP | UI | Observação |
|---|---|---|---|
| `GET /acessos/divergencias` | `operadora_divergencia` | — | UI: sem tela própria hoje; atende o MCP e clientes externos |
| `GET /acessos/divergencias/scm` | — | ✔ | MCP: variante com parâmetros próprios (k_pf, k_pj, min_razao) de uma análise de hipótese; operadora_divergencia cobre a razão usuários APNIC ÷ acessos por AS |
| `GET /acessos/municipio/{ibge}` | `municipio_banda_larga` | ✔ |  |
| `GET /acessos/municipios` | `query:acessos_municipio` | ✔ |  |
| `GET /acessos/municipios/mapa` | — | ✔ | MCP: blob de visualização (GeoJSON); fora do MCP |
| `GET /acessos/operadora/{cnpj}` | `operadora_acessos` | ✔ |  |
| `GET /acessos/operadora/{cnpj}/contacts` | `operadora_contatos` | ✔ |  |
| `GET /acessos/operadoras` | `operadora_ranking` | ✔ |  |
| `GET /acessos/stats` | `historico_acessos` | ✔ |  |
| `GET /analytics/operators/reach` | `operadora_alcance` | — | UI: sem tela própria hoje; atende o MCP e clientes externos |
| `GET /asns` | `asn_lista` | ✔ |  |
| `GET /asns/by-organization` | — | ✔ | MCP: ASNs do mesmo CNPJ: asn_detalhe traz same_cnpj_asns e same_raiz_asns por AS; o ranking de CNPJs ou raízes com vários ASNs sai de query(collection=asns, group_by=cnpj ou cnpj_root) |
| `GET /asns/ix-presence` | `asn_ix_presence` | ✔ |  |
| `GET /asns/names` | `asn_names` | ✔ |  |
| `GET /asns/{asn}` | `asn_detalhe` | ✔ |  |
| `GET /asns/{asn}/abuso` | `query:organizacoes_asn` | — | UI: a página usa o mesmo bloco pelo ?include=abuso do perfil |
| `GET /asns/{asn}/acessos` | `operadora_acessos` | ✔ |  |
| `GET /asns/{asn}/acessos/municipios` | — | ✔ | MCP: operadora_acessos(asn=) traz os 25 maiores municípios (top_municipios); a lista completa sai de query(collection=acessos_municipio) filtrando asns contains <asn> |
| `GET /asns/{asn}/bloqueios` | `asn_bloqueios` | — | UI: a página usa o mesmo bloco pelo ?include=bloqueios do perfil |
| `GET /asns/{asn}/contacts` | `asn_contatos` | ✔ |  |
| `GET /asns/{asn}/exposicao` | `asn_exposicao` | — | UI: a página usa o mesmo bloco pelo ?include=exposicao do perfil |
| `GET /asns/{asn}/facilities` | `facility_lista` | — | UI: a página usa o mesmo bloco pelo ?include=facilities do perfil |
| `GET /asns/{asn}/geo` | `viz` | ✔ |  |
| `GET /asns/{asn}/interconexao` | `asn_interconexao` | ✔ |  |
| `GET /asns/{asn}/ixp-peers` | `asn_rede` | ✔ |  |
| `GET /asns/{asn}/organizacao` | `query:organizacoes_asn` | — | UI: a página usa o mesmo bloco pelo ?include=organizacao do perfil |
| `GET /asns/{asn}/paths` | `asn_rede` | ✔ |  |
| `GET /asns/{asn}/peering` | `asn_peering` | — | UI: a página usa o mesmo bloco pelo ?include=peering do perfil |
| `GET /asns/{asn}/politica` | `asn_politica` | — | UI: a página usa o mesmo bloco pelo ?include=politica_rs do perfil |
| `GET /asns/{asn}/radar` | `asn_radar` | — | UI: a página usa o mesmo bloco pelo ?include=radar do perfil |
| `GET /asns/{asn}/route-servers` | `query:rs_sessoes` | — | UI: a página usa o mesmo bloco pelo ?include=route_servers do perfil |
| `GET /asns/{asn}/transito` | `query:transito_asn` | — | UI: a página usa o mesmo bloco pelo ?include=transito do perfil |
| `GET /bgp-stability` | — | ✔ | MCP: documento completo de dezenas de MB; o MCP serve recortes por rota_estabilidade (asn=, modo=visao_geral|resumo|historico) |
| `GET /bgp-stability-deep` | — | ✔ | MCP: documento completo de dezenas de MB; o MCP serve recortes por rota_estabilidade (asn=, modo=visao_geral|resumo|historico) |
| `GET /bgp-stability/asn/{asn}` | `rota_estabilidade` | ✔ |  |
| `GET /bgp-stability/carga` | `rota_estabilidade` | ✔ |  |
| `GET /bgp-stability/history` | `rota_estabilidade` | ✔ |  |
| `GET /bgp-stability/overview` | `rota_estabilidade` | ✔ |  |
| `GET /bgp-stability/summary` | `rota_estabilidade` | — | UI: a interface usa /bgp-stability/overview e /bgp-stability/history; o resumo atende clientes externos |
| `GET /brasil/destaques` | — | ✔ | MCP: números fixos de apresentação dos destaques e do "O que mudou" da home, cada um o total de uma pergunta pronta; o MCP tem query com as mesmas coleções (operadoras, asns, acessos_municipio, eventos) e acessos_divergencias |
| `GET /brasil/indicadores` | — | ✔ | MCP: resumo de apresentação da home e do Panorama técnico (agregados do país); o MCP tem query(collection=asns) com os usuários do APNIC por ASN, query(collection=seguranca_asn) e prontidao_agregado com os mesmos agregados, rota_rpki com a publicação de ROA/ASPA e rota_analise com a análise da tabela |
| `GET /brasil/snapshots` | `historico_snapshots` | ✔ |  |
| `GET /brasil/snapshots/{date_str}` | `historico_snapshots` | ✔ |  |
| `GET /busca` | — | ✔ | MCP: busca da barra do site, agrupada por tipo. O MCP já resolve por nome com asn_lista(q), operadora_resolver e municipio_resolver, e está em 54 de 56 tools; uma tool de busca geral entra na revisão do MCP (nome de domínio a definir) |
| `GET /cdns/alcance` | — | ✔ | MCP: estimativa de apresentação por CDN e UF; o MCP já tem cdn_presence e operator_reach, e o alcance por UF é uma conta sobre usuários estimados da APNIC que a interface rotula |
| `GET /cdns/mudancas` | — | ✔ | MCP: diferença de cadastro de membros entre duas datas para a aba Mudanças de CDNs; o MCP tem cdn_presenca por data e historico_mudancas para os eventos de PTT |
| `GET /cdns/presence` | `cdn_presenca` | ✔ |  |
| `GET /cetic/estimativas` | `query:cetic_estimativas_uf` | ✔ |  |
| `GET /cetic/estimativas/uf/{uf}` | `query:cetic_estimativas_uf` | — | UI: a página de UF usa o mesmo bloco pelo ?include=cetic do perfil |
| `GET /cetic/indicadores` | `query:cetic_indicadores` | ✔ |  |
| `GET /cetic/tabelas` | `query:cetic_indicadores` | ✔ |  |
| `GET /changes` | `historico_mudancas` | ✔ |  |
| `GET /changes/summary` | `historico_mudancas` | ✔ |  |
| `GET /communities` | `ixp_communities` | ✔ |  |
| `GET /consumidor/marcas` | `query:consumidor_marca` | ✔ |  |
| `GET /consumidor/municipios/{ibge}` | — | — | MCP: reclamações por município e empresa ficam fora do /query; o MCP cobre as reclamações por empresa e mês em query(collection=consumidor_marca), e o detalhe municipal fica na API e na interface; UI: a página do município usa o mesmo dado pelo ?include=consumidor do perfil |
| `GET /consumidor/resumo` | `query:consumidor_marca` | ✔ |  |
| `GET /contratos/municipios/{ibge}` | — | ✔ | MCP: o teto de tools do MCP e a leitura parcial do rodízio (município sem contratação nas leituras não é município sem contratação) deixam o detalhe municipal na API e na interface; o MCP cobre o contrato por operadora |
| `GET /contratos/operadoras/{cnpj}` | `operadora_contratos` | ✔ |  |
| `GET /contratos/resumo` | — | — | MCP: cobertura do rodízio e totais por ano, UF e esfera, sem ranking de fornecedor; a tool operadora_contratos já traz a cobertura em cada resposta; UI: a página própria de Contratos públicos fica para depois da primeira rodada completa do rodízio: com o rodízio ainda cobrindo parte do universo, os totais nacionais enganam mais do que informam; os blocos da operadora e do município já mostram a cobertura |
| `GET /empresas/mercado` | — | ✔ | MCP: séries pequenas de entradas e baixas por ano e UF, já na interface; o MCP não ganha nada novo antes de uma coleção de empresas por CNPJ (pendente), e a pergunta mais comum (quem tem filial onde) é por operadora |
| `GET /empresas/operadoras/{cnpj}` | — | ✔ | MCP: o cadastro por CNPJ cabe melhor numa coleção do /query (empresas_operadora), que fica como evolução do passo; por ora a API e a interface cobrem a presença física da operadora |
| `GET /erbs/municipios` | `query:erbs_municipio` | ✔ |  |
| `GET /erbs/resumo` | `query:erbs_municipio` | — | UI: o bloco de cada UF e de cada operadora usa o mesmo dado pelo ?include=erbs dos perfis |
| `GET /espectro/faixas` | `query:faixas_espectro` | ✔ |  |
| `GET /espectro/resumo` | `query:faixas_espectro` | ✔ |  |
| `GET /exposicao/ufs/{uf}` | `asn_exposicao` | — | UI: a página da UF usa o mesmo bloco pelo ?include=exposicao do perfil |
| `GET /external-ixps` | `ixp_externo` | ✔ |  |
| `GET /external-ixps/{code}` | `ixp_externo` | ✔ |  |
| `GET /facilities` | `facility_lista` | ✔ |  |
| `GET /facilities/{fac_id}` | `facility_detalhe` | ✔ |  |
| `GET /feed/mudancas.atom` | — | ✔ | MCP: feed de assinatura (Atom) para leitores; o MCP tem historico_mudancas |
| `GET /financiamento/operadoras/{cnpj}` | `operadora_financiamento` | ✔ |  |
| `GET /fust/municipios` | `query:fust_municipio` | ✔ |  |
| `GET /fust/resumo` | `query:fust_municipio` | ✔ |  |
| `GET /grupos` | `query:socios` | ✔ |  |
| `GET /grupos/empresa/{cnpj}` | `operadora_grupo` | ✔ |  |
| `GET /grupos/{grupo_id}` | `grupo_perfil` | ✔ |  |
| `GET /grupos/{grupo_id}/municipios` | — | ✔ | MCP: tabela de apresentação da página de grupo (parcela, declarantes e HHI local por município, paginada); o MCP tem grupo_perfil e query(collection=acessos_municipio), com parcela, declarantes e HHI por CNPJ |
| `GET /grupos/{grupo_id}/prefixos-geo` | — | ✔ | MCP: blob de visualização (GeoJSON); fora do MCP |
| `GET /hilbert/v4` | `viz` | ✔ |  |
| `GET /hilbert/v4/detail` | `viz` | ✔ |  |
| `GET /hilbert/v6` | `viz` | ✔ |  |
| `GET /history/asns/{asn}` | `historico_serie` | — | UI: a linha do tempo da página lê o bloco historico do perfil (include=historico), não esta rota |
| `GET /history/brasil/series` | — | ✔ | MCP: séries nacionais de roteamento e segurança com a regra de comparabilidade, para o gráfico das páginas; o MCP já tem rota_analise e query:prontidao_agregado por data, e historico_serie para a entidade |
| `GET /history/ixps/{code}` | `historico_serie` | — | UI: a linha do tempo da página lê o bloco historico do perfil (include=historico), não esta rota |
| `GET /history/operadoras/{cnpj}` | `historico_serie` | — | UI: a linha do tempo da página lê o bloco historico do perfil (include=historico), não esta rota |
| `GET /history/uf/{uf}` | `historico_serie` | — | UI: a linha do tempo da página lê o bloco historico do perfil (include=historico), não esta rota |
| `GET /ipv4/asns/{asn}` | `query:uso_por_terceiros_ipv4` | ✔ |  |
| `GET /ipv4/blocos/{prefix}/ciclo-de-vida` | `query:eventos_bloco` | ✔ |  |
| `GET /ipv4/espaco` | `query:espaco_ipv4` | ✔ |  |
| `GET /ipv4/recuperacao` | `query:recuperacao_ipv4` | ✔ |  |
| `GET /ipv4/subasignacoes` | `query:subasignacoes_ipv4` | ✔ |  |
| `GET /ipv4/transferencias` | `query:transferencias_ipv4` | ✔ |  |
| `GET /ipv4/transferencias/resumo` | `query:transferencias_ipv4` | ✔ |  |
| `GET /ipv4/uso-por-terceiros` | `query:uso_por_terceiros_ipv4` | ✔ |  |
| `GET /ixp-compare/members` | — | ✔ | MCP: a comparação sai de query(collection=asns) com ixps_sessao_rs contains X e ncontains Y (álgebra de conjuntos, ver as instruções) ou de ixp_participantes de cada PTT |
| `GET /ixps` | `ixp_lista` | ✔ |  |
| `GET /ixps/estimated-users` | `ixp_usuarios` | ✔ |  |
| `GET /ixps/{code}` | `ixp_detalhe` | ✔ |  |
| `GET /ixps/{code}/assinantes` | `ixp_assinantes` | ✔ |  |
| `GET /ixps/{code}/estimated-users` | `ixp_usuarios` | ✔ |  |
| `GET /ixps/{code}/facilities` | `facility_lista` | ✔ |  |
| `GET /ixps/{code}/geo` | `viz` | ✔ |  |
| `GET /ixps/{code}/hilbert/v4` | `viz` | ✔ |  |
| `GET /ixps/{code}/hilbert/v4/detail` | `viz` | ✔ |  |
| `GET /ixps/{code}/hilbert/v6` | `viz` | ✔ |  |
| `GET /ixps/{code}/members` | `ixp_participantes` | ✔ |  |
| `GET /ixps/{code}/nearby` | `ixp_proximos` | — | UI: a interface usa /ixps/{code}/potential; a rota atende o MCP e clientes externos |
| `GET /ixps/{code}/participantes` | — | ✔ | MCP: tabela de apresentação da página de PTT que junta cadastro, sessão com o route server, rejeição e CDNs; o MCP tem ixp_participantes (membros e peers), ixp_rejeicoes e query(collection=rs_sessoes) com os mesmos dados por consulta |
| `GET /ixps/{code}/peers` | `ixp_participantes` | ✔ |  |
| `GET /ixps/{code}/portas` | `ixp_portas` | ✔ |  |
| `GET /ixps/{code}/potential` | `ixp_potencial` | ✔ |  |
| `GET /ixps/{code}/rejeicoes` | `ixp_rejeicoes` | — | UI: a página usa o mesmo bloco pelo ?include=rejeicoes do perfil |
| `GET /ixps/{code}/route-servers` | `query:rs_sessoes` | — | UI: a página usa o mesmo bloco pelo ?include=route_servers do perfil |
| `GET /limites` | — | ✔ | MCP: tetos de uso do site e do próprio MCP, para quem escreve o cliente; não é dado do mapa e as instruções do MCP já estão no teto de tamanho |
| `GET /map/asns` | `viz` | ✔ |  |
| `GET /map/asns-overview` | `viz` | ✔ |  |
| `GET /map/erbs` | `query:erbs_municipio` | ✔ |  |
| `GET /map/layers` | — | ✔ | MCP: lista de camadas do mapa da interface; fora do MCP |
| `GET /map/pix` | `viz` | ✔ |  |
| `GET /map/power-transmission-lines` | `infra_proximos` | ✔ |  |
| `GET /map/prefixes` | `viz` | ✔ |  |
| `GET /map/rodovias` | `infra_proximos` | ✔ |  |
| `GET /map/submarine-cables` | `infra_proximos` | ✔ |  |
| `GET /map/submarine-landing-points` | `infra_proximos` | ✔ |  |
| `GET /map/terrestrial-links` | `infra_proximos` | ✔ |  |
| `GET /mercado/demanda-oferta` | `query:demanda_oferta` | ✔ |  |
| `GET /mercado/grupos` | — | ✔ | MCP: resumo de apresentação do Panorama de mercado; o MCP já tem query(collection=municipios) e operadoras, e o HHI por grupo é uma inferência que a interface rotula |
| `GET /mercado/maiores` | — | ✔ | MCP: resumo de apresentação (posição mês a mês e treemap); o MCP já tem top_operators e access_history, que dão os mesmos números por operadora, e o agrupamento por grupo é uma inferência que a interface rotula |
| `GET /multas/empresas` | `query:multas_empresa` | ✔ |  |
| `GET /multas/resumo` | `query:multas_empresa` | ✔ |  |
| `GET /municipios/{ibge}` | `municipio_detalhe` | ✔ |  |
| `GET /operadoras/{cnpj}` | `operadora_detalhe` | ✔ |  |
| `GET /outorgas` | `outorga_lista` | ✔ |  |
| `GET /outorgas/map` | — | ✔ | MCP: blob de visualização (GeoJSON); fora do MCP |
| `GET /outorgas/stats` | — | ✔ | MCP: totais por serviço saem de outorga_lista (campo total, com servico=) e a quebra por UF, de query(collection=scms|smps|stfcs|seacs, group_by=uf) |
| `GET /outorgas/{cnpj}` | `outorga_detalhe` | ✔ |  |
| `GET /prefixes` | `rota_prefixos` | ✔ |  |
| `GET /prefixes/lookup` | `rota_prefixo` | ✔ |  |
| `GET /prefixes/{prefix}` | `rota_prefixo` | ✔ |  |
| `GET /prontidao/asns` | `query:prontidao_asn` | — | UI: a lista de ASes usa a coluna de /asns?include=prontidao; a rota é a mesma lista nominal pública (PRONTIDAO_LISTA_NOMINAL), com ordem padrão por ASN |
| `GET /prontidao/resumo` | `query:prontidao_agregado` | ✔ |  |
| `GET /qualidade/mapa` | — | ✔ | MCP: blob de visualização ({ibge: valor} de todos os municípios para o mapa); o MCP já tem query(collection=qualidade_uf) e o resumo do RQUAL, e a média entre prestadoras não é uma medida da Anatel |
| `GET /qualidade/municipios/{ibge}` | — | — | MCP: o RQUAL por município (322 mil itens) não cabe numa coleção do /query; o MCP cobre o RQUAL por UF e prestadora em query(collection=qualidade_uf), e o detalhe municipal fica na API e na interface; UI: a página do município usa o mesmo dado pelo ?include=qualidade do perfil |
| `GET /qualidade/prestadoras` | `query:qualidade_uf` | ✔ |  |
| `GET /qualidade/resumo` | `query:qualidade_uf` | ✔ |  |
| `GET /qualidade/serie` | `query:qualidade_uf` | ✔ |  |
| `GET /query/{collection}` | `query` | ✔ |  |
| `GET /radar/ufs/{uf}` | `uf_radar` | — | UI: a página da UF usa o mesmo bloco pelo ?include=radar do perfil |
| `GET /ranking/municipios` | — | ✔ | MCP: o ranking por município atendido sai de query:acessos_municipio; o HHI e a variação por município vêm de municipio_banda_larga (bloco indicadores) |
| `GET /ranking/operadoras` | `query:indicadores_operadora` | ✔ |  |
| `GET /ranking/route-servers` | `query:rs_sessoes` | ✔ |  |
| `GET /reclamacoes/marcas` | `query:reclamacoes_marca` | ✔ |  |
| `GET /reclamacoes/municipios/{ibge}` | — | — | MCP: reclamações por município e marca (milhões de linhas) ficam fora do /query; o MCP cobre as reclamações por marca, serviço e ano em query(collection=reclamacoes_marca), e o detalhe municipal fica na API e na interface; UI: a página do município usa o mesmo dado pelo ?include=reclamacoes do perfil |
| `GET /reclamacoes/resumo` | `query:reclamacoes_marca` | ✔ |  |
| `GET /regiao` | — | ✔ | MCP: agregado de um conjunto de municípios para a página de município (raio); o MCP tem asn_ix_presence, ixp_nearby e get_asn para o mesmo tipo de pergunta por ASN ou PTT |
| `GET /resolve/operator` | `operadora_resolver` | — | UI: sem tela própria hoje; atende o MCP |
| `GET /resolve/place` | `municipio_resolver` | ✔ |  |
| `GET /routing-analysis` | `rota_analise` | ✔ |  |
| `GET /rpki/summary` | `rota_rpki` | ✔ |  |
| `GET /satelites/direitos` | `query:satelites_direitos` | ✔ |  |
| `GET /satelites/resumo` | `query:satelites_direitos` | ✔ |  |
| `GET /schema` | `describe_schema` | ✔ |  |
| `GET /seguranca/resumo` | `query:seguranca_asn` | ✔ |  |
| `GET /sem-declaracao-sici` | `query:sem_declaracao_sici` | ✔ |  |
| `GET /snapshots` | `historico_snapshots` | ✔ |  |
| `GET /snapshots/diff` | `historico_mudancas` | ✔ |  |
| `GET /snapshots/{date_str}` | `historico_snapshots` | ✔ |  |
| `GET /territorio/mapa` | — | ✔ | MCP: blob de visualização ({ibge: valor} de todos os municípios para o mapa coroplético); o MCP já tem query(collection=municipios) e municipio_detalhe, que trazem os mesmos indicadores com filtro |
| `GET /territorio/municipio/{ibge}/semelhantes` | — | ✔ | MCP: comparação de apresentação (municípios do mesmo porte); o MCP já tem query(collection=municipios), que filtra e ordena por domicílios, penetração e fibra |
| `GET /territorio/ranking` | `query:municipios` | ✔ |  |
| `GET /territorio/rede` | — | ✔ | MCP: resumo de apresentação por UF (estimativas e inferências com cobertura); o MCP já tem query(collection=municipios) e as tools de segurança de roteamento e de trânsito |
| `GET /territorio/resumo` | — | ✔ | MCP: agregado de apresentação da síntese de /municipios (país ou UF, por distância ao PTT); o MCP já tem query(collection=municipios) com group_by sem_ptt_proximo e aggregate, que devolve os mesmos agregados com filtro |
| `GET /transito/ufs` | `query:transito_uf` | — | UI: a página da UF usa o bloco pelo ?include=transito do perfil; a lista das 27 UFs só existe na API e no MCP |
| `GET /transito/ufs/{uf}` | `query:transito_uf` | — | UI: a página da UF usa o detalhe pelo mesmo endpoint dentro do bloco de trânsito; o MCP traz as linhas pela coleção |
| `GET /ufs` | `uf_detalhe` | ✔ |  |
| `GET /ufs/{uf}` | `uf_detalhe` | ✔ |  |
