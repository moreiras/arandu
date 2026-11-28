<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Dicionário de dados

Todos os campos declarados no catálogo, por fonte e por produto. `⚠️` marca dado pessoal ou de contato.

## Fontes

### [abusech](fontes/abusech.md) — Servidores C2 de botnets por ASN (abuse.ch, Feodo Tracker)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `feodo.asns[asn].c2_total` | int | Servidores C2 do Feodo Tracker em prefixos do ASN (instantâneo da lista, que cobre os últimos 30 dias). | Contagem; o ASN que hospeda não é dono do servidor. | — |
| `feodo.asns[asn].c2_online` | int | Quantos deles estavam online na coleta. | — | — |
| `feodo.asns[asn].malware` | dict | Contagem por família (Dridex, Emotet, TrickBot, QakBot, BazarLoader). | — | — |

### [anatel_erbs](fontes/anatel_erbs.md) — Anatel — estações do SMP licenciadas (ERBs)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `estacoes[].fistel / estacao` | str | Número Fistel e número da estação, que juntos identificam a estação licenciada. | Cadastro de licenciamento, não torre física: a mesma torre pode ter mais de um número de estação. | — |
| `estacoes[].marca / entidade / cnpj` | str | Operadora (marca, razão social e CNPJ). | A coluna de CNPJ vem em branco em ~44% das linhas; o CNPJ é o da própria estação quando existe, senão o mais frequente da marca no arquivo. | — |
| `estacoes[].ibge / uf` | str | Código IBGE do município e UF da estação. | O código só vem em uma de cada três cópias de cada registro; a consolidação usa o valor preenchido. Estação sem nenhum valor fica com `ibge: null`. | — |
| `estacoes[].lat / lon / posicao_variavel` | float / bool | Posição da estação (a mais frequente entre as suas linhas). | Fora do Brasil ou ausente vira null (contado em `resumo`); `posicao_variavel` marca as estações cuja posição muda entre linhas. | — |
| `estacoes[].geracoes / tecnologias / tipo_5g / faixas / setores / combinacoes` | lista | Gerações (2G a 5G), tecnologias (GSM, WCDMA, LTE, NR), tipo do 5G (SA, NSA, SA-NSA), faixas em MHz, número de setores e de combinações tecnologia × frequência × setor. | Licenciado, não necessariamente ativo. | — |
| `estacoes[].infra / primeira_licenca / linhas` | str / int | Tipo de infraestrutura física (Rooftop, Greenfield, Indoor...), ano do primeiro licenciamento e linhas do arquivo original que a compõem. | — | — |
| `resumo / data_arquivo / sha256` | dict | Linhas lidas, estações, sem posição, fora do Brasil, posição variável, sem IBGE; data de modificação do arquivo na Anatel e seu hash. | — | — |

### [anatel_fust](fontes/anatel_fust.md) — Anatel — compromissos do FUST

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `compromissos[].id / origem / tipo / programa` | str | Número da linha, edital ou projeto de origem (ex.: Edital nº 166/2024/MCOM, Projetos BNDES), tipo do compromisso (escolas, UBS, favelas, rede, SMP) e programa (ex.: 1.1 Conectividade para Escolas Públicas). | Espaços e tabulações normalizados; os códigos de programa vêm do arquivo. | — |
| `compromissos[].ibge / uf / municipio / nivel / base_ibge` | str | Município (7 primeiros dígitos de `COD_LOCALIDADE`), UF, nome, nível da obrigação (Município ou Localidade) e malha do IBGE usada (IBGE_2010 ou IBGE_2022). | Código de município de malha antiga pode não existir no cadastro atual do IBGE; o produto conta esses casos. | — |
| `compromissos[].status / prazo / investimento` | str / data / float | Situação registrada pela Anatel (Atendido, A vencer, Em apuração), prazo máximo e investimento total previsto em reais. | Investimento é o previsto, não o desembolsado. Valor em branco vira null. | — |
| `resumo / data_arquivo / sha256` | dict | Compromissos lidos, sem município, sem valor, contagem por situação; data de modificação do arquivo na Anatel e seu hash. | — | — |

### [anatel_multas](fontes/anatel_multas.md) — Anatel — multas constituídas

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `empresas[].raiz / grupo / entidade / cnpjs / uf` | str | Raiz do CNPJ (8 dígitos, matriz e filiais), grupo de serviço (SCM, SMP, STFC ou SeAC), nome mais frequente, CNPJs completos e UF mais frequente. | Grupo pelo nome do serviço no arquivo; serviços fora dos quatro (radiodifusão, privados, radioamador) e multas sem serviço (a quem não tem outorga) ficam de fora. | — |
| `empresas[].multas / original / pago / saldo / situacoes / anos` | int / float / dict | Número de multas, valor original, valor pago e saldo devedor atualizado (R$), multas por situação e por ano de aplicação. | Multa constituída não é condenação definitiva: pode estar em recurso, parcelada ou suspensa judicialmente. | — |
| `resumo / data_arquivo / sha256` | dict | Linhas lidas, pessoas físicas descartadas, linhas fora do escopo, empresas e multas consolidadas; data de modificação do arquivo na Anatel e seu hash. | — | — |

### [anatel_pdff](fontes/anatel_pdff.md) — Anatel — quadro de atribuição e destinação de faixas (PDFF)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `faixas[].ini_mhz / fim_mhz` | float | Início e fim da faixa em MHz. | Lidos das colunas `*_MHz` (vírgula decimal). | — |
| `faixas[].destinacao[] / atribuicao[]` | lista | Serviços destinados e atribuídos à faixa no Brasil, cada um com o caráter (Primário ou Secundário). | — | — |
| `resumo / data_arquivo / sha256` | dict | Faixas lidas e quantas têm destinação e atribuição; data de modificação do arquivo na Anatel e seu hash. | — | — |

### [anatel_reclamacoes](fontes/anatel_reclamacoes.md) — Anatel — reclamações de consumidores

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `marcas[]` | lista | Reclamações (tipo Reclamação) por marca × serviço × ano, com os municípios distintos. A marca é maiúscula, como o consumidor a escolheu. | Outros tipos de solicitação (denúncia, pedido de informação, elogio...) entram só em `por_mes`. 'NÃO LOCALIZEI A MINHA EMPRESA' e 'OUTROS' não identificam ninguém. | — |
| `por_mes[] / uf[] / assuntos[] / marca_assuntos[] / marca_mensal[]` | lista | Totais nacionais por mês × serviço × tipo, por UF × serviço × ano, por assunto (só do `contexto`, de 2020 em diante, porque a taxonomia mudou) e por marca × assunto e marca × mês (últimos 3 anos). | — | — |
| `municipios[ibge].itens[]` | lista | Reclamações por ano × serviço × marca nos últimos 3 anos da fonte, por município. | — | — |
| `resumo / data_arquivo / sha256` | dict | Linhas e solicitações de cada arquivo, mês inicial e final, data de extração, marcas e municípios; data de modificação do arquivo na Anatel e seu hash. | — | — |

### [anatel_rqual](fontes/anatel_rqual.md) — Anatel — indicadores de qualidade (RQUAL)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `indicadores[] / prestadoras[]` | lista | Indicadores (serviço, código, descrição, tipo IQS ou informativo, grupo, unidade, valores de referência superior e inferior da Anatel) e prestadoras com o número de municípios medidos. | Os valores de referência são os mais frequentes no arquivo para o indicador; o sentido de 'melhor' depende do indicador e não é interpretado. | — |
| `nacional[]` | lista | Por serviço × prestadora × indicador × mês, municípios medidos, medidas, média simples, média ponderada pelo número de medidas e mediana dos municípios. | Só resultados numéricos; NA, NO e NI são contados em `resumo.sem_valor` (o arquivo não documenta o significado). Não é o desempenho da empresa para um cliente. | — |
| `uf[]` | lista | O mesmo por UF e ano (sem mediana). | — | — |
| `municipios[ibge].itens[]` | lista | O último resultado numérico de cada serviço × prestadora × indicador no município, com mês, medidas, coletores, erro amostral, intervalo e a coluna Estatística da fonte (SIM/NÃO). | Resultado de poucas medidas é incerto; o erro amostral e o intervalo acompanham o valor. | — |
| `resumo / data_arquivo / sha256` | dict | Linhas lidas, resultados numéricos, sem valor, municípios, primeiro e último mês; data de modificação do arquivo na Anatel e seu hash. | — | — |

### [anatel_satelites](fontes/anatel_satelites.md) — Anatel — satélites com direito de exploração

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `direitos[].operadora / satelite / codigo / posicao / banda / tipo / status` | str | Operadora, satélite, código do direito, posição orbital, banda, tipo (Brasileiro ou Estrangeiro) e status do direito. | — | — |
| `direitos[].lancamento / validade / prorrogado` | data / bool | Data de lançamento, validade do direito e se foi prorrogado. | — | — |
| `ngeo[] / operando[]` | lista | Constelações NGEO (prestadora, CNPJ, objeto comercial, órbita, planos e satélites da constelação) e satélites em operação comercial. | CNPJ só nas constelações NGEO (prestadora no Brasil); nos direitos não há CNPJ. | — |
| `resumo / data_arquivo / sha256` | dict | Linhas lidas por tabela; data de modificação do arquivo na Anatel e seu hash. | — | — |

### [anatel_scm](fontes/anatel_scm.md) — Outorgas SCM (Serviço de Comunicação Multimídia)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `cnpj` | str | CNPJ (14 dígitos) da prestadora outorgada. | Chave de junção com SICI, Registro.br e Receita. | outorgas → scm.json.gz |
| `razao_social / nome_fantasia` | str | Razão social e nome fantasia da prestadora. | — | outorgas → scm.json.gz |
| `data_outorga` | str | Data de inclusão da outorga no cadastro da Anatel. | — | outorgas → scm.json.gz |
| `num_servico` | str | Código do serviço da notificação (045 SCM, 010 SMP, 171 STFC, 750 SeAC). | — | outorgas → scm.json.gz |
| `logradouro / numero / complemento / bairro / cep` | str | Endereço da sede da prestadora na notificação. | Endereço de pessoa jurídica; exposto nas rotas públicas listadas (decisão do mantenedor 2026-10-11). | outorgas → scm.json.gz |
| `municipio / uf / codigo_ibge` | str | Município e UF da sede e código IBGE do município. | — | outorgas → scm.json.gz |
| `telefone / email` ⚠️ dado pessoal/contato | str | Contato declarado na notificação. | Removido das rotas públicas; só via /asns/{asn}/contacts com login (teste T4). | outorgas → scm.json.gz |

### [anatel_seac](fontes/anatel_seac.md) — Outorgas SeAC (TV por assinatura)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `cnpj` | str | CNPJ (14 dígitos) da prestadora outorgada. | Chave de junção com SICI, Registro.br e Receita. | outorgas → seac.json.gz |
| `razao_social / nome_fantasia` | str | Razão social e nome fantasia da prestadora. | — | outorgas → seac.json.gz |
| `data_outorga` | str | Data de inclusão da outorga no cadastro da Anatel. | — | outorgas → seac.json.gz |
| `num_servico` | str | Código do serviço da notificação (045 SCM, 010 SMP, 171 STFC, 750 SeAC). | — | outorgas → seac.json.gz |
| `logradouro / numero / complemento / bairro / cep` | str | Endereço da sede da prestadora na notificação. | Endereço de pessoa jurídica; exposto nas rotas públicas listadas (decisão do mantenedor 2026-10-11). | outorgas → seac.json.gz |
| `municipio / uf / codigo_ibge` | str | Município e UF da sede e código IBGE do município. | — | outorgas → seac.json.gz |
| `telefone / email` ⚠️ dado pessoal/contato | str | Contato declarado na notificação. | Removido das rotas públicas; só via /asns/{asn}/contacts com login (teste T4). | outorgas → seac.json.gz |

### [anatel_sici](fontes/anatel_sici.md) — Acessos de banda larga fixa (SICI/Anatel)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `mes_referencia` | str | Último mês de declaração disponível (AAAA-MM). Distinto da data do snapshot. | Citar sempre as duas datas. | sici → sici.json.gz#mes_referencia |
| `cnpjs[cnpj].acessos` | int | Contratos de acesso à Internet em serviço declarados no mês. Não é usuário nem domicílio. | Somar por CNPJ; não somar ASNs do mesmo CNPJ (acessos_compartilhados). | sici → sici.json.gz#cnpjs |
| `cnpjs[cnpj].pf / pj` | int | Acessos de clientes pessoa física e pessoa jurídica. | — | sici → sici.json.gz#cnpjs |
| `cnpjs[cnpj].capacidade_mbps` | float | Soma da velocidade contratada dos acessos (Mbps). | Soma de contratados, não de tráfego. | sici → sici.json.gz#cnpjs |
| `cnpjs[cnpj].por_tecnologia / por_meio / por_faixa / por_produto / por_municipio` | dict | Acessos por tecnologia, meio físico, faixa de velocidade, produto e município. | — | sici → sici.json.gz#cnpjs |
| `cnpjs[cnpj].velocidade_mediana_mbps / velocidade_media_mbps` | float | Mediana e média ponderada da velocidade contratada. | — | sici → sici.json.gz#cnpjs |
| `serie_por_cnpj / serie_total` | list | Série mensal de acessos por CNPJ e total nacional. | — | sici → sici.json.gz#serie_total |
| `distrib_velocidade[uf]` | dict | Distribuição de acessos por faixa de velocidade e UF, PF×PJ. | — | sici → sici.json.gz#distrib_velocidade |

### [anatel_sici_movel](fontes/anatel_sici_movel.md) — Acessos de telefonia móvel (SICI/Anatel)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `mes_referencia` | str | Último mês de declaração disponível (AAAA-MM). | — | sici → sici_movel.json.gz#mes_referencia |
| `cnpjs[cnpj].acessos` | int | Acessos móveis de voz/dados em linha pessoal, declarados no mês. | M2M e PONTO_DE_SERVICO não entram no total (batem com o total oficial da Anatel). | sici → sici_movel.json.gz#cnpjs |
| `cnpjs[cnpj].acessos_m2m / acessos_outros` | int | Acessos M2M (chips embarcados) e demais (infraestrutura da prestadora), contados à parte. | — | sici → sici_movel.json.gz#cnpjs |
| `cnpjs[cnpj].por_geracao / por_modalidade / por_produto / por_municipio` | dict | Acessos por geração (2G–5G), modalidade de cobrança, produto e município. | — | sici → sici_movel.json.gz#cnpjs |
| `cnpjs[cnpj].pf / pj` | int | Acessos de clientes PF e PJ. | — | sici → sici_movel.json.gz#cnpjs |

### [anatel_smp](fontes/anatel_smp.md) — Outorgas SMP (Serviço Móvel Pessoal) e rede virtual

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `cnpj` | str | CNPJ (14 dígitos) da prestadora outorgada. | Chave de junção com SICI, Registro.br e Receita. | outorgas → smp.json.gz |
| `razao_social / nome_fantasia` | str | Razão social e nome fantasia da prestadora. | — | outorgas → smp.json.gz |
| `data_outorga` | str | Data de inclusão da outorga no cadastro da Anatel. | — | outorgas → smp.json.gz |
| `num_servico` | str | Código do serviço da notificação (045 SCM, 010 SMP, 171 STFC, 750 SeAC). | — | outorgas → smp.json.gz |
| `logradouro / numero / complemento / bairro / cep` | str | Endereço da sede da prestadora na notificação. | Endereço de pessoa jurídica; exposto nas rotas públicas listadas (decisão do mantenedor 2026-10-11). | outorgas → smp.json.gz |
| `municipio / uf / codigo_ibge` | str | Município e UF da sede e código IBGE do município. | — | outorgas → smp.json.gz |
| `telefone / email` ⚠️ dado pessoal/contato | str | Contato declarado na notificação. | Removido das rotas públicas; só via /asns/{asn}/contacts com login (teste T4). | outorgas → smp.json.gz |
| `rede_virtual.papel` | str | 'host' (detém a rede) ou 'credenciada' (MVNO credenciada junto a um host). | Vem do dataset de competição (contratos_mvno.csv); MVNO puro sem outorga SMP ganha registro sintético. | outorgas → smp.json.gz |

### [anatel_stfc](fontes/anatel_stfc.md) — Outorgas STFC (telefonia fixa comutada)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `cnpj` | str | CNPJ (14 dígitos) da prestadora outorgada. | Chave de junção com SICI, Registro.br e Receita. | outorgas → stfc.json.gz |
| `razao_social / nome_fantasia` | str | Razão social e nome fantasia da prestadora. | — | outorgas → stfc.json.gz |
| `data_outorga` | str | Data de inclusão da outorga no cadastro da Anatel. | — | outorgas → stfc.json.gz |
| `num_servico` | str | Código do serviço da notificação (045 SCM, 010 SMP, 171 STFC, 750 SeAC). | — | outorgas → stfc.json.gz |
| `logradouro / numero / complemento / bairro / cep` | str | Endereço da sede da prestadora na notificação. | Endereço de pessoa jurídica; exposto nas rotas públicas listadas (decisão do mantenedor 2026-10-11). | outorgas → stfc.json.gz |
| `municipio / uf / codigo_ibge` | str | Município e UF da sede e código IBGE do município. | — | outorgas → stfc.json.gz |
| `telefone / email` ⚠️ dado pessoal/contato | str | Contato declarado na notificação. | Removido das rotas públicas; só via /asns/{asn}/contacts com login (teste T4). | outorgas → stfc.json.gz |

### [aneel_sigel_transmission](fontes/aneel_sigel_transmission.md) — Linhas de transmissão de alta tensão (SIGEL/ANEEL)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `features[].geometry` | GeoJSON | Traçado da linha. | Vértices duplicados em ciclo no serviço de origem são deduplicados. | mapas_infraestrutura → maps/power_transmission_lines.geojson |
| `features[].properties.Name` | str | Descrição da linha em texto livre (ex.: 'Linha LT 230 kV A / B C 1 UF'). | — | mapas_infraestrutura → maps/power_transmission_lines.geojson |
| `features[].properties.tensao_kv / extensao_km` | float | Tensão e extensão extraídas por regex de Name/PopupInfo (best-effort). | Nulos quando o parsing falha. | mapas_infraestrutura → maps/power_transmission_lines.geojson |

### [apnic_dnssec](fontes/apnic_dnssec.md) — Validação de DNSSEC por ASN (APNIC)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].validates_pct` | float | Percentual de clientes que validam DNSSEC ("DNSSEC Validates"); "Partial Validation" vai em parcial_pct. | Medição por amostragem (anúncios em experimentos de usuários); alto = valida. Não é declaração da rede. | — |
| `asns[asn].amostras` | int | Tamanho da amostra da janela; com poucas amostras o percentual é instável. | — | — |
| `as_of` | str | Último dia da série da página (a janela termina nele). | — | — |

### [apnic_irov](fontes/apnic_irov.md) — Validação RPKI por ASN (APNIC I-RoV)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].validates_pct` | float | Percentual de medições em que a rota RPKI-inválida não foi alcançada ("RPKI Validates"; campo filter_rate do JSON). | Medição por amostragem (anúncios em experimentos de usuários); alto = valida. Não é declaração da rede. | — |
| `asns[asn].amostras` | int | Tamanho da amostra da janela; com poucas amostras o percentual é instável. | — | — |
| `as_of` | str | Último dia da série da página (a janela termina nele). | — | — |

### [apnic_pop](fontes/apnic_pop.md) — Estimativas de usuários por AS (APNIC Labs)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `window_days` | int | Janela de medição em dias (60). | — | — |
| `asns[asn].users` | int | Usuários de Internet estimados atrás do AS. | Estimativa por amostragem de anúncios, rotulada 'estimado'. | asn_docs → asns/{asn}.json#apnic_users |
| `asns[asn].users_pct_cc` | float | % da população estimada do país (BR) que o AS representa. | — | asn_docs → asns/{asn}.json#apnic_users_pct_cc |
| `asns[asn].v6_users` | int | Usuários IPv6 estimados. | — | asn_docs → asns/{asn}.json#apnic_v6_users |
| `asns[asn].v6_pct_as` | float | % dos usuários do AS que usam IPv6. | — | asn_docs → asns/{asn}.json#apnic_v6_pct_as |

### [asn_names](fontes/asn_names.md) — Nomes de ASNs (RIPE NCC, bulk global)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `{asn}` | str | Nome do ASN (descrição curta do whois, com código de país ao final). | Chaves string; o publicado traz só os ASNs presentes no snapshot. | asn_docs → asns/names.json#* |

### [bgp_stability_deep](fontes/bgp_stability_deep.md) — Estabilidade BGP aprofundada (top ASes ruidosos)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `suspected_upstreams[].asn` | int | ASN do upstream suspeito de propagar instabilidade. | Hipótese estatística sobre AS-PATH, não afirmação. | bgp_stability → bgp_stability_deep.json |
| `suspected_upstreams[].events_attributed` | int | Eventos atribuídos a esse upstream. | — | bgp_stability → bgp_stability_deep.json |
| `as_diagnosis[].verdict` | str | Veredito da análise para o AS (origem interna, prefixo específico, upstream). | Rótulo inferido. | bgp_stability → bgp_stability_deep.json |
| `as_diagnosis[].prefix_sync_score` | float | Quão sincronizados estão os eventos entre prefixos do AS (0–1). | — | bgp_stability → bgp_stability_deep.json |
| `as_diagnosis[].upstream_concentration_pct` | float | % dos eventos concentrados no upstream mais provável. | — | bgp_stability → bgp_stability_deep.json |

### [bgp_updates_routeviews](fontes/bgp_updates_routeviews.md) — Updates BGP do RouteViews São Paulo (7 dias)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `period` | dict | Janela analisada (início, fim, dias, coletor, arquivos processados e ausentes, eventos vistos e contados). | — | bgp_stability → bgp_stability.json |
| `period.dedup_rate_pct` | float | % de eventos descartados como duplicados entre peers. | — | bgp_stability → bgp_stability.json |
| `as_stability[].asn` | int | ASN analisado. | — | bgp_stability → bgp_stability.json |
| `as_stability[].classification` | str | Classe de estabilidade atribuída ao AS pela taxa de eventos por prefixo por dia. | Faixas definidas em analysis/bgp_stability. | bgp_stability → bgp_stability.json |
| `as_stability[].daily/hourly` | dict | Contagem de eventos por dia e por hora (UTC). | — | bgp_stability → bgp_stability.json |
| `as_stability[].top_prefixes` | list[dict] | Prefixos com mais eventos para o AS. | — | bgp_stability → bgp_stability.json |
| `distribution.{v6,v4}` | dict | Distribuição de eventos por prefixo/dia (percentis p50–p99 e buckets). | — | bgp_stability → bgp_stability.json |
| `hourly_global` | dict | Série horária global de anúncios, retiradas e mudanças de atributo. | — | bgp_stability → bgp_stability.json |

### [bndes_operacoes](fontes/bndes_operacoes.md) — BNDES — operações de financiamento (não automáticas) a empresas de telecom

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `operacoes[cnpj14][]` | lista | Operações do cliente (CNPJ de 14 dígitos, matriz ou filial) com contrato, data, valor contratado e desembolsado (R$), produto, instrumento financeiro, forma de apoio, UF, município IBGE, CNAE, porte, situação e descrição curta do projeto. | Valores nominais da data da contratação, sem correção. Só operações diretas e não automáticas (o recorte da fonte). | — |
| `dump_reference / linhas_lidas / operacoes_guardadas / cnpjs / universo_cnpjs_basicos` | dict | Data de modificação do conjunto no portal, linhas lidas, operações e CNPJs guardados e tamanho do universo. | — | — |

### [bogons](fontes/bogons.md) — Bogons (IANA e Team Cymru)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `iana.v6[] / iana.v4[]` | list[dict] | Blocos de uso especial não alcançáveis globalmente (privados, documentação, loopback etc.) com nome e RFC. | — | — |
| `iana.asns[]` | list[dict] | Faixas de ASN reservadas (documentação, uso privado, AS_TRANS etc.) com o motivo. | — | — |
| `cymru.v6[] / cymru.v4[]` | list[str] | Fullbogons (reservados mais espaço ainda não alocado por nenhum RIR). | A lista de espaço não alocado muda todo dia; vale a data da lista (cymru.as_of). | — |

### [caida_as2org](fontes/caida_as2org.md) — Organização por ASN (CAIDA AS-to-Organization, via AS Rank)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].org_id` | str | Identificador da organização no AS Rank (hash); ASNs com o mesmo valor pertencem à mesma organização. | Inferência do CAIDA a partir do WHOIS. | — |
| `asns[asn].org_nome` | str | Nome da organização como registrado (pode ser o de uma 'Parent'). | Dado do registro, não nome fantasia; rotulado como do CAIDA. | — |
| `asns[asn].org_pais` | str | País da organização (ISO 3166-1 alfa-2). | — | — |
| `asns[asn].membros_total` | int | Número de ASNs da organização no mundo. | — | — |

### [caida_asrank](fontes/caida_asrank.md) — Rank, grau e cone de ASNs (CAIDA AS Rank)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].rank` | int | Posição do ASN pelo tamanho do cone de clientes (1 = maior). | Inferência do CAIDA (relações entre ASNs); estimado. | — |
| `asns[asn].cone` | dict | Tamanho do cone de clientes (ASNs, prefixos e endereços). | Inferência do CAIDA. | — |
| `asns[asn].grau` | dict | Número de vizinhos por tipo (total, clientes, pares, provedores) inferido pelo CAIDA. | Inferência; difere do que o Arandurapé infere em as_relationships. | — |
| `asns[asn].clique` | bool | Campo cliqueMember da API do CAIDA. | NÃO USADO nos produtos. A API devolve true para ASNs de rank baixo (conferido em 2026-10-31, caso do AS28573, posição 7.887), então não é a clique de nível 1. | — |

### [caida_asrel](fontes/caida_asrel.md) — Relações entre ASNs (CAIDA as-rel2)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `p2c[]` | list[int] | Par [provedor, cliente] segundo o CAIDA. | Inferência do CAIDA (AS-Rank), não contrato. | — |
| `p2p[]` | list[int] | Par [menor ASN, maior ASN] em relação de peering segundo o CAIDA. | Inferência do CAIDA; inclui pares vistos em looking glasses de IXPs. | — |
| `as_of` | str | Data do arquivo mensal usado (pode ser até um mês anterior ao snapshot). | — | — |

### [caida_spoofer](fontes/caida_spoofer.md) — CAIDA Spoofer — validação de endereço de origem (SAV)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[].sessoes / sessoes_v4 / sessoes_v6 / pct_nat_v4 / ultima_sessao` | int / float / data | Sessões atribuídas ao ASN na janela de 12 meses (por família), percentual das sessões IPv4 atrás de NAT e data da última. | Sessão que mede IPv6 e IPv4 conta uma vez em `sessoes` e uma vez em cada família. | — |
| `asns[].conclusivas / conclusivas_v4 / conclusivas_v6 / suficiente` | int / bool | Sessões conclusivas (algum teste `blocked` ou `received`) fora de NAT em IPv6 e em IPv4, e se atingem o mínimo (5) para o ASN ter pontuação neste pilar. | `rewritten` (NAT reescreveu a origem) e `unknown` não contam; IPv4 atrás de NAT não conta, porque o resultado não fala da rede do ASN. | — |
| `asns[].pct_bloqueado / pct_recebido_privado / pct_recebido_roteado` | float | % das sessões conclusivas em que nenhum pacote forjado chegou; % dos testes conclusivos com origem privada e com origem roteada em que o pacote chegou. | — | — |
| `resumo / citacao / novas_sessoes` | dict | Sessões na janela, ASNs com dado e suficientes, janela e mínimo; a citação exigida pelo CAIDA; sessões novas baixadas nesta execução. | — | — |

### [cetic_tic_domicilios_microdados](fontes/cetic_tic_domicilios_microdados.md) — TIC Domicílios — microdados (Cetic.br), estimativas por UF

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `grupos[BR | região | UF].indicadores[id].proporcao / erro_padrao / margem / cv` | float | Percentual de domicílios do grupo com a característica, erro-padrão em pontos percentuais, margem de erro de 95% (1,96 × erro-padrão) e coeficiente de variação. | Estimativa do Arandurapé: ponto pelo peso amostral e variância pelas 200 réplicas da base pública. A estimativa pontual coincide com a das tabelas oficiais; a margem oficial é de 1,08 a 1,14 vez a estimada aqui (validação no produto). Precisão "baixa" quando o CV passa de 30%. | — |
| `grupos[...].indicadores[id].total / total_erro_padrao` | int | Domicílios do grupo com a característica, estimados pelos pesos, e erro-padrão do total. | Estimativa expandida; não é contagem. | — |
| `grupos[...].n / domicilios / domicilios_se` | int | Domicílios entrevistados no grupo, domicílios estimados e erro-padrão. | Grupo com menos de 30 entrevistados é suprimido (`suprimido` no lugar dos números). | — |
| `indicadores[id].rotulo / definicao` | str | O que cada indicador mede e quais colunas da base o definem. | — | — |

### [cetic_tic_domicilios_tabelas](fontes/cetic_tic_domicilios_tabelas.md) — TIC Domicílios — tabelas oficiais (Cetic.br)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `edicao / fonte / url / sha256` | int / str | Ano da edição, citação, endereço do ZIP de origem e hash do arquivo guardado. | A edição é a mais recente listada na página do Cetic.br; as anteriores não ficam disponíveis ali. | — |
| `tabelas[aba]` | object | Código, título, universo (a quem a pergunta se aplica) e notas de cada tabela da pesquisa. | O texto vem da planilha; as marcas de nota de rodapé do título são retiradas. | — |
| `linhas[].proporcao / margem_proporcao` | float | Percentual da resposta dentro do recorte e a margem de erro da estimativa, em pontos percentuais. | Estimativa amostral publicada pelo Cetic.br; vazio quando a planilha não traz o valor (nunca zero inventado). | — |
| `linhas[].total / margem_total` | float | Domicílios que dão a resposta no recorte, estimados pela amostra, e a margem de erro dessa estimativa. | Estimativa expandida pelos pesos da pesquisa, não contagem. | — |
| `linhas[].dimensao / recorte / item / resposta` | str | Como a linha se abre: dimensão do recorte (Total, Região, Área, Classe social, Renda familiar), categoria dentro dela, item da pergunta quando a pergunta tem vários itens e a resposta. | — | — |

### [cetic_tic_provedores_tabelas](fontes/cetic_tic_provedores_tabelas.md) — TIC Provedores — tabelas oficiais (Cetic.br)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `edicao / fonte / url / sha256` | int / str | Ano da edição, citação, endereço do ZIP de origem e hash do arquivo guardado. | A edição é a mais recente listada na página do Cetic.br; as anteriores não ficam disponíveis ali. | — |
| `tabelas[aba]` | object | Código, título, universo (a quem a pergunta se aplica) e notas de cada tabela da pesquisa. | O texto vem da planilha; as marcas de nota de rodapé do título são retiradas. | — |
| `linhas[].proporcao / margem_proporcao` | float | Percentual da resposta dentro do recorte e a margem de erro da estimativa, em pontos percentuais. | Estimativa amostral publicada pelo Cetic.br; vazio quando a planilha não traz o valor (nunca zero inventado). | — |
| `linhas[].total / margem_total` | float | Empresas provedoras que dão a resposta no recorte, estimados pela amostra, e a margem de erro dessa estimativa. | Estimativa expandida pelos pesos da pesquisa, não contagem. | — |
| `linhas[].dimensao / recorte / item / resposta` | str | Como a linha se abre: dimensão do recorte (Total, Região, Porte do provedor, Classe de número de clientes), categoria dentro dela, item da pergunta quando a pergunta tem vários itens e a resposta. | — | — |

### [cgu_ceis_cnep](fontes/cgu_ceis_cnep.md) — CGU — sanções a empresas (CEIS e CNEP), recorte de telecom

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `sancoes[cnpj14][]` | lista | Sanções do CNPJ (matriz ou filial) com cadastro (CEIS ou CNEP), código, categoria, início, fim, publicação, abrangência, órgão sancionador, UF e esfera, fundamento legal, processo e valor da multa (CNEP). | Registro do órgão sancionador, sem julgamento. A fonte usa data final 2099-12-31 para sanção sem prazo; o produto trata como "sem prazo". | — |
| `arquivos / linhas_lidas / linhas_pessoa_juridica / sancoes_guardadas / cnpjs / universo_cnpjs_basicos` | dict | Data dos arquivos de origem de cada cadastro, linhas lidas, linhas de pessoa jurídica e o recorte guardado. | — | — |

### [cloudflare_radar](fontes/cloudflare_radar.md) — Cloudflare Radar — IPv6, tráfego, velocidade, BGP e quedas do Brasil (CC BY-NC 4.0)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ipv6[asn]` | dict | Percentual de IPv6 das requisições HTTP de pessoas (`botClass=LIKELY_HUMAN`) do ASN nos últimos 28 dias (`v6`) e a data da leitura (`em`). `v6` nulo = o Radar não devolveu dado para o ASN. | Rodízio de `RADAR_ASNS_POR_EXECUCAO` ASNs por execução (padrão 1.400), os sem leitura primeiro e depois os de leitura mais antiga; cada ASN leva a sua data. Mede quem usa a Cloudflare. | radar → radar/asns.json.gz#asns |
| `trafego.topo / velocidade.topo` | list | Os até 300 ASNs do Brasil com maior participação nas requisições HTTP (`pct`) e os até 300 com testes de velocidade (download, upload, latência ociosa e carregada, jitter, `testes`). | Só existe para os ASNs das listas; fora delas não há número (não é zero). A lista de velocidade veio com 179 ASNs em 2026-11-09. | radar → radar/asns.json.gz#asns |
| `bgp.vazamentos / bgp.sequestros` | dict | Eventos dos últimos 28 dias com ASN do Brasil: vazamentos (vazador, caminho, prefixos) e sequestros (sequestrador, vítimas, nº de prefixos, RPKI inválido). Prefixos só em contagem. | Reduzidos ao necessário para atribuir o papel de cada ASN; o critério do país (`involvedCountry=BR`) pega qualquer evento com ASN do Brasil no caminho, por isso o produto usa o papel. | radar → radar/asns.json.gz#asns; radar → radar/asns.json.gz#bgp |
| `quedas` | dict | Consulta de anomalias de tráfego e de quedas anotadas do Brasil em 52 semanas (contagens) e a data da consulta. | Em 2026-11-09 o Brasil não aparece em nenhum dos dois rankings do Radar (67 e 49 países). Sem série; publica-se o resultado da consulta. | radar → radar/asns.json.gz#quedas |
| `licenca / atribuicao` | str | CC BY-NC 4.0 e o texto de atribuição, que acompanham todo derivado. | — | radar → radar/asns.json.gz#licenca; radar → radar/asns.json.gz#fonte |

### [cnpj_geo](fontes/cnpj_geo.md) — Cadastro e geolocalização das organizações (BrasilAPI + Nominatim)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `orgs[asn].razao_social / nome_fantasia` | str | Razão social e nome fantasia no cadastro do CNPJ. | — | asn_docs → asns/{asn}.json#geo_org |
| `orgs[asn].cnae_fiscal / cnae_fiscal_descricao` | int\|str | Atividade econômica principal (CNAE). | — | asn_docs → asns/{asn}.json#geo_org |
| `orgs[asn].situacao_cadastral` | int\|str | Situação cadastral do CNPJ (ativa, baixada, suspensa…) e motivo. | Cache: pode estar defasado até o próximo refresh. | asn_docs → asns/{asn}.json#geo_org |
| `orgs[asn].natureza_juridica / porte` | str | Natureza jurídica e porte (ME, EPP, demais). | — | asn_docs → asns/{asn}.json#geo_org |
| `orgs[asn].data_inicio_atividade` | str | Data de início de atividade. | — | asn_docs → asns/{asn}.json#geo_org |
| `orgs[asn].logradouro … cep / municipio / uf` | str | Endereço cadastral da organização (pessoa jurídica). | Endereço de PJ exposto nas rotas públicas listadas (decisão 2026-10-11). | asn_docs → asns/{asn}.json#geo_org |
| `orgs[asn].email / ddd_telefone_1 / ddd_telefone_2` ⚠️ dado pessoal/contato | str | Contato cadastral do CNPJ. | Presente no arquivo publicado; removido das rotas públicas (T4). | asn_docs → asns/{asn}.json#geo_org |
| `orgs[asn].lat / lon / geo_confidence / geo_source` | float\|str | Coordenadas do endereço e como foram obtidas. | Mesmos rótulos de confiança das outorgas. | asn_docs → asns/{asn}.json#geo_org |

### [consumidor_gov](fontes/consumidor_gov.md) — Consumidor.gov.br — reclamações finalizadas

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `meses[AAAA-MM].cidades[]` | lista | Por empresa (nome fantasia) × UF × cidade (nome digitado) no mês (finalizadas, respondidas, avaliadas, resolvidas) e a soma e a contagem do tempo de resposta (dias) e da nota (1 a 5). | Só o segmento de operadoras de telecomunicações. Sexo, faixa etária, região e data da linha não são guardados. | — |
| `meses[AAAA-MM].assuntos[] / grupos[]` | lista | Reclamações do mês por empresa × assunto e por empresa × grupo de problema. | — | — |
| `meses[AAAA-MM].codigo / tamanho / resumo` | dict | Código da publicação (muda se o arquivo é republicado, o que dispara novo download), tamanho do zip e a contagem da leitura (linhas, linhas de telecom, segmentos, empresas, células). | — | — |
| `resumo` | dict | Meses cobertos, mês inicial e final, quantos arquivos foram baixados nesta execução e o total de reclamações de telecom. | — | — |

### [curada_bgp_communities](fontes/curada_bgp_communities.md) — Communities BGP de operadores (config/bgp_communities.yaml)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `communities[].asn / operator` | int\|str | ASN e nome do operador que define a community. | — | routing_analysis → routing_analysis.json |
| `communities[].community` | str | Valor (standard AAAA:NNN, extended ou large). | — | routing_analysis → routing_analysis.json |
| `communities[].type / category` | str | Tipo (standard/extended/large) e categoria funcional (local_preference, blackhole…). | — | routing_analysis → routing_analysis.json |
| `communities[].description` | str | Descrição do efeito, em texto livre. | Reproduz documentação de terceiros. | routing_analysis → routing_analysis.json |
| `communities[].source` | str | Origem da linha (ex.: bpf_wiki). | Proveniência por linha. | — |

### [curada_cdns](fontes/curada_cdns.md) — CDNs e grandes provedores de conteúdo (config/cdns.yaml)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `cdns[].name` | str | Nome do provedor/CDN. | — | cdns → cdns.json#cdns |
| `cdns[].asns` | list[int] | ASNs atribuídos ao provedor. | Presença em um IXP = QUALQUER dos ASNs presente. | cdns → cdns.json#cdns |
| `cdns[].aka` | str | Nome do programa de cache (ex.: GGC, OCA). | — | cdns → cdns.json#cdns |

### [curada_ixps](fontes/curada_ixps.md) — Localidades do IX.br (config/ixps.yaml)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ixps[].code` | str | Código curto do IXP (minúsculas; ex.: sp, rj, vix). | Chave de junção em todo o sistema. | ixp_docs → ixps/index.json#code |
| `ixps[].name / uf` | str | Cidade-sede e UF da localidade. | — | ixp_docs → ixps/index.json#name |
| `ixps[].telnet_host / telnet_port / timeout` | str\|int | Host e porta do Looking Glass e tempo máximo de leitura da tabela. | Operacional; não publicado. | — |
| `ixps[].cep` | str | CEP aproximado usado para posicionar a localidade. | Aproximação; PIX têm coordenadas próprias em pix.yaml. | — |

### [curada_marcas_operadoras](fontes/curada_marcas_operadoras.md) — Marca → raiz do CNPJ (config/curada_marcas_operadoras.yaml)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `marcas[].marca / raizes / base` | str / lista / str | Marca como na fonte, raízes de CNPJ (8 dígitos) a que ela se liga e o que sustenta o vínculo. | Uma marca pode ter várias raízes (grupo econômico). Casamento sempre rotulado como curado ou automático; sem casamento a marca fica sem CNPJ. | qualidade → qualidade/rqual.json.gz#prestadoras; qualidade → qualidade/reclamacoes.json.gz#marcas |
| `asns_estrangeiros[].marca / raizes / asns / base / data` | str / lista / lista / str / data | AS de fora do Brasil ligado pela marca a uma operadora brasileira (raízes), com o que sustenta o vínculo e a data da conferência. | Vínculo `estrangeiro` do índice ASN ↔ CNPJ (decisão D5), lido pela API (`api/services/operadoras.py`); a seção `marcas` dá o vínculo `marca`. Selo inferido; o AS estrangeiro não entra nas somas de rede da operadora. | — |

### [curada_peeringdb_ixps](fontes/curada_peeringdb_ixps.md) — IXPs consultados no PeeringDB (config/peeringdb_ixps.yaml)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `external[].code / name / city / country` | str | Identificação do IXP externo exibido. | — | ixp_docs → external-ixps/{ixp}.json |
| `external[].pdb_ix_id` | int | Identificador do IX no PeeringDB. | — | ixp_docs → external-ixps/{ixp}.json#pdb_ix_id |
| `ixbr[]` | list | IXPs do IX.br com ID no PeeringDB, para cruzamento do cadastro. | Operacional. | — |

### [curada_pix](fontes/curada_pix.md) — Pontos de intercâmbio físicos do IX.br (config/pix.yaml)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `pix[code][].name` | str | Nome do ponto (ex.: '[PIX RNP]'). | — | mapas_prefixos → /api/v1/map/pix |
| `pix[code][].address / cep` | str | Endereço e CEP do ponto. | Endereço de instalação, não de pessoa física. | mapas_prefixos → /api/v1/map/pix |
| `pix[code][].lat / lon` | float | Coordenadas do ponto. | Geocodificadas por OSM; podem ter sido corrigidas à mão. | mapas_prefixos → /api/v1/map/pix |

### [decix_alice](fontes/decix_alice.md) — Route servers do DE-CIX Rio de Janeiro e São Paulo (Alice-LG, níveis 0, 1 e 3)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `rs[].estado_rotas` | str | Estado do cache de ROTAS do Alice para o route server (READY, BUSY ou ERROR), do `/status` (ligado pelo nome do RS); não diz nada das sessões. | A leitura de rotas usa o rs1 se o cache estiver READY, senão o rs2. | — |
| `rs[].vizinhos_em` | str | Instante em que o Alice atualizou o cache de vizinhos do route server (`cache_status.cached_at` da resposta do `neighbors`). | — | — |
| `sessoes[]` | list | Uma linha por sessão BGP no route server (ixp = decix-sp ou decix-rj, família, ASN, IP na LAN, estado, último erro, rotas recebidas, aceitas e filtradas, limite de importação) e o `id_vizinho` do Alice. | Sessão up no route server = o ASN faz peering multilateral naquele PTT; não diz nada de peering bilateral. O nome é o rótulo público do LG (organização, não pessoa). | — |
| `vizinhos[].origens` | dict | decix_rs_rotas: {ASN de origem (último do AS_PATH): nº de rotas lidas} do vizinho, nas páginas de `routes/received` lidas. | Um piso, não o conjunto: vizinho com mais de `paginas_max_vizinho` páginas de 250 rotas fica `completo: false`. O produto rotula o conjunto de originadores como parcial. | — |
| `vizinhos[].total` | int | Número de rotas recebidas do vizinho (`pagination.total_results` do Alice); `lidas` é quantas entraram na contagem de origens. | — | — |
| `vizinhos[].herdado` | bool | Verdadeiro se o vizinho não coube no orçamento desta rodada e vem da rodada anterior, com o `coletado_em` original (idade máxima 35 dias). | — | — |
| `cobertura_rodizio` | dict | `total` e `por_ptt`: vizinhos elegíveis, lidos na rodada, herdados, sem leitura e idade máxima da leitura em dias. | — | — |
| `bloqueio` | dict | Presente quando o servidor respondeu 403/429 ou derrubou a conexão: instante, motivo e caminho. A coleta parou na hora e não tenta de novo por 7 dias. | — | — |

### [fulltable_routeviews](fontes/fulltable_routeviews.md) — Tabela BGP global (RouteViews + RIPE RIS)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `origin-prefixes[asn]` | list[str] | Prefixos originados por cada ASN na tabela global. | Chave é o ASN como string. | asn_docs → asns/{asn}.json#global_prefixes_v4; asn_docs → asns/{asn}.json#global_prefixes_v6 |
| `prefix-set` | list[str] | Conjunto ordenado de todos os prefixos únicos vistos na tabela global (v6 ou v4). | — | snapshot → summary.json#ft_space_v4; snapshot → summary.json#ft_space_v6 |
| `aspath-adj[asn].up` | list[int] | ASNs vistos imediatamente à esquerda do AS em qualquer AS-PATH dos coletores. Adjacência (inclui provedores, pares e o ponto de observação); a classificação em relações vem do produto `as_relationships`. | Inferido do AS-PATH; não é relação contratual. | asn_docs → asns/{asn}.json#upstreams_global_v4; asn_docs → asns/{asn}.json#upstreams_global_v6 |
| `aspath-adj[asn].down` | list[int] | ASNs vistos imediatamente à direita do AS em qualquer AS-PATH dos coletores. Adjacência (inclui clientes e pares), não é relação comercial. | Inferido do AS-PATH; não é relação contratual. | asn_docs → asns/{asn}.json#downstreams_global_v4; asn_docs → asns/{asn}.json#downstreams_global_v6 |
| `br-routes[].p` | str | Prefixo de uma rota cuja origem é ASN brasileiro. | — | — |
| `br-routes[].a` | list[int] | AS-PATH (mais representativo entre os coletores) da rota brasileira. | — | — |
| `br-routes[].c` | list[str] | Communities BGP associadas (standard e large). | — | routing_analysis → routing_analysis.json |
| `routes-{afi}.stats` | dict | Totais da tabela (rotas, prefixos únicos, ASNs diretos, de origem e stub). | — | snapshot → summary.json#global_table |
| `origins-multi-{afi}.prefixos[prefixo][asn]` | list[str] | Prefixos com duas ou mais origens (último AS do AS-PATH) entre todas as rotas de todos os coletores (MOAS); para cada origem, os coletores em que algum ponto de observação a viu. Só entram os prefixos com 2+ origens. | Fato observado, sem causa. A origem de um AS_SET final é o último ASN do conjunto (não ordenado). `coletores` lista os coletores que entraram na família; arquivo presente com `prefixos` vazio é nenhum MOAS observado entre eles. Licença e termos os da fonte (RouteViews CC BY 4.0; RIPE RIS não verificado). | routing_analysis → routing_analysis.json#moas; routing_analysis → routing_analysis.json#moas_resumo |
| `fulltable_manifest.{v6,v4}.sources` | list[str] | URLs dos dumps efetivamente usados em cada AFI. | Mostra quais coletores entraram; checado por publish.coleta_checks. | — |

### [global_prefix_geo](fontes/global_prefix_geo.md) — Geolocalização dos prefixos vistos nos IXPs (DB-IP City Lite)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `prefixes[prefix].ixps_seen` | list[str] | IXPs do IX.br onde o prefixo foi visto. | — | mapas_prefixos → maps/global_prefixes.geojson |
| `prefixes[prefix].origin_asn` | int | ASN originador (do primeiro IXP em que o prefixo apareceu). | Se houver conflito de origem entre IXPs, vale o primeiro. | mapas_prefixos → maps/global_prefixes.geojson |
| `prefixes[prefix].lat / lon / city / country / uf` | float\|str | Posição segundo o DB-IP (centroide de cidade). | — | mapas_prefixos → maps/global_prefixes.geojson |
| `geolocated / unknown` | int | Prefixos com e sem geolocalização. | — | — |

### [ibge_bc250_rodovias](fontes/ibge_bc250_rodovias.md) — Malha rodoviária (IBGE BC250)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `features[].geometry` | GeoJSON | Traçado do trecho rodoviário. | — | mapas_infraestrutura → maps/ibge_rodovias.geojson |
| `features[].properties.sigla` | str | Sigla da rodovia (ex.: BR-101). | — | mapas_infraestrutura → maps/ibge_rodovias.geojson |
| `features[].properties.jurisdicao / revestimen` | str | Jurisdição e revestimento do trecho. | 49% 'Desconhecida' em jurisdição (limitação da origem). | mapas_infraestrutura → maps/ibge_rodovias.geojson |

### [ibge_censo_pnad](fontes/ibge_censo_pnad.md) — População, domicílios e uso de internet (IBGE, Censo 2022 e PNAD Contínua)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `municipios[ibge].populacao / area_km2` | int / float | População residente e área da unidade territorial no Censo 2022. | Censo de 2022 (não é estimativa anual); município sem valor fica sem o campo. | — |
| `municipios[ibge].populacao_estimada` | int | População residente estimada pelo IBGE em 1º de julho do ano mais recente (tabela 6579), calculada a partir do Censo 2022. | Estimativa oficial; cobre município criado depois do Censo (que não tem os demais campos). | — |
| `municipios[ibge].domicilios / moradores` | int | Domicílios particulares permanentes OCUPADOS e seus moradores (Censo 2022). | Não inclui domicílios coletivos, de uso ocasional nem vagos. | — |
| `ufs[uf].domicilios_mil / com_internet_mil / taxa` | float | Domicílios (mil) e os em que havia utilização de internet; taxa = com internet ÷ total, por UF (PNAD). | Estimativa amostral. "Utilização de internet" inclui quem usa só o celular; não é banda larga fixa. | — |
| `ufs[uf].domicilios_mil_por_ano` | dict | Domicílios (mil) da UF na PNAD em cada ano da tabela; a razão entre o ano atual e o do Censo projeta os domicílios municipais. | Estimativa amostral; a definição de domicílio da PNAD não é idêntica à do Censo. | — |
| `ufs[uf].cv_domicilios_pct` | float | Coeficiente de variação da estimativa de domicílios da UF. | — | — |

### [ibge_malha_municipal](fontes/ibge_malha_municipal.md) — Malha municipal do IBGE (limites dos municípios e UFs, em tiles)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `municipios.ibge / nome / uf` | str | Código IBGE de 7 dígitos, nome e sigla da UF de cada município. | — | frontend → /malha-municipal.pmtiles |
| `ufs.uf / nome` | str | Sigla e nome de cada UF (união dos municípios simplificados). | — | frontend → /malha-municipal.pmtiles |

### [ipv4_delegated](fontes/ipv4_delegated.md) — Eventos do ciclo de vida do IPv4 (delegated-extended do LACNIC)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ultima_foto / por_status` | str / dict | Data da última foto processada e, por status (allocated, assigned, reserved), blocos e endereços no LACNIC e no Brasil. | — | — |
| `eventos_por_tipo / eventos_ultimos_dias` | dict / int | Eventos dos últimos 30 dias por tipo. | Diferença observada entre fotos diárias, sem causa nem intenção; a data é a da foto em que apareceu (`visto_entre` quando faltou uma foto). | — |
| `validacao_cruzada` | dict | Das transferências diretas BR → BR do Registro.br desde 2020, quantas aparecem como mudança de `opaque-id` no `delegated` (mesmo bloco, de 3 dias antes a 45 dias depois). | — | — |
| `processamento` | dict | Fotos processadas, eventos novos, dias sem arquivo (lacunas) e reorganizações de blocos que não são evento. | — | — |

### [ipv4_listas](fontes/ipv4_listas.md) — Listas de numeração IPv4 normalizadas (transferências, recuperação, recuperados)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `transferencias_registrobr[]` | lista | Transferência direta do Registro.br: data, origem e destino (nome, RIR, país), blocos CIDR, endereços, conjunto original e data do registro original (quando a lista traz), `primeira_vez_visto`. | Nome como vem da fonte (pode ser pessoa física); a publicação mascara. Um lote de blocos na mesma data e partes aparece em várias linhas (agrupado por operação no produto). | — |
| `transferencias_lacnic[]` | lista | Transferência do log do LACNIC (todas as de IPv4 da região, não só as do Brasil), com blocos originais e transferidos. | Registro com endereço nulo é ignorado e contado em `resumo`. | — |
| `recuperacao[] / recuperados[]` | lista | Recurso (bloco IPv6, bloco IPv4 ou ASN) em recuperação com a janela, e recurso já recuperado. | — | — |
| `resumo` | dict | Por lista, registros lidos, linhas ignoradas, primeira data coletada e novos na data. | — | — |

### [ipv4_subasignacao](fontes/ipv4_subasignacao.md) — Bitácora de sub-asignações de IPv4 (política LAC-2025-5, esquema hipotético)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `registros[]` | lista | Sub-asignação no esquema hipotético: bloco, ASN do receptor, início, fim (opcional), ASN do cedente (opcional) e RIR. | ESQUEMA HIPOTÉTICO; nada é publicado como fato enquanto a fonte não estiver ativada e o formato real conferido. | — |

### [ipv4_vigia](fontes/ipv4_vigia.md) — Vigia dos diretórios de numeração (Registro.br e LACNIC)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `alertas[]` | lista | Novidades desde a varredura anterior: `padrao_novo`, `arquivo_novo`, `padrao_removido`, `cabecalho_mudou`, `diretorio_novo`. | Alerta não é falha da coleta; vai para o log (aviso) e para o arquivo da varredura. Arquivo diário com data nova não é novidade. | — |

### [irr_route_objects](fontes/irr_route_objects.md) — IRR (TC e RADB) — objetos route/route6 dos ASNs brasileiros

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `rotas[irr][asn]` | lista | Prefixos (CIDR) de objetos `route`/`route6` com o ASN brasileiro como origem, por IRR (TC e RADB). | Só o par prefixo/origem. O RADB aceita objetos criados por terceiros (o provedor, por exemplo) e o TC não: a existência do objeto não prova que o ASN o criou. | — |
| `aut_num[irr]` | lista | ASNs brasileiros com objeto `aut-num` no IRR. | — | — |
| `politicas[irr][asn]` | lista | Por `aut-num` brasileiro, as linhas `import`/`export` com par ASN explícito, reduzidas a sentido (in ou out), ASN do par e classe do filtro (any, proprio, par, as_set, outro). | Só a classe do filtro; o texto da política, mantenedor e contato não são guardados. Linhas com conjunto no lugar do par, refine/except e fatores múltiplos são ignoradas. Declarado não é praticado: serve de referência e de evidência candidata do 1.5.30, nunca de verdade. | — |
| `fontes[irr]` | dict | URL, serial, tamanho, hash, contagem de objetos do dump (todos, não só brasileiros), ASNs brasileiros com route, prefixos e `aut-num`; `reaproveitado_de` quando o serial não mudou. | — | — |

### [itu_transmission](fontes/itu_transmission.md) — Enlaces terrestres de transmissão (ITU BBmaps)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `features[].geometry` | GeoJSON | Traçado do enlace (LineString/MultiLineString). | — | mapas_infraestrutura → maps/itu_transmission.geojson |
| `features[].properties` | dict | Atributos do enlace conforme a ITU (operador, tipo, situação). | — | mapas_infraestrutura → maps/itu_transmission.geojson |
| `status_counts` | dict | Contagem de enlaces por situação (Operational, Planned, Under Construction…). | Há variações de grafia na origem (ex.: 'Under construction' e 'Under Construction'). | — |

### [ixbr_alice](fontes/ixbr_alice.md) — Sessões BGP dos route servers do IX.br (Alice-LG)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `rs[].estado_rotas` | str | Estado do cache de ROTAS do Alice para o route server (READY, BUSY ou ERROR), do `/status`; `rotas_atualizadas_em` é o fim da última renovação desse cache. | Não diz nada das sessões (o SP rs1 v4 aparece BUSY/ERROR nas rotas e tem sessões com minutos de uptime). O dado de sessão vem do `neighbors`. | — |
| `rs[].vizinhos_em` | str | Instante em que o Alice atualizou o cache de vizinhos do route server (`cache_status.cached_at` da resposta do `neighbors`). | É o frescor das sessões. Vazio se a consulta falhou ou a resposta não traz o dado; o produto trata como incerto. | — |
| `rs[].consultado` | bool | Se a consulta de `neighbors` do RS funcionou nesta rodada. Falso = sem sessões e sem zero inventado (`erro` diz o motivo). | — | — |
| `sessoes[].estado` | str | Estado da sessão BGP no route server (up ou down). | — | — |
| `sessoes[].last_error` | str | Último erro reportado pelo route server para a sessão (por exemplo "Hold timer expired"); vazio quando não há. | — | — |
| `sessoes[].state_changed` | str | Data e hora (horário do route server) da última mudança de estado da sessão. | — | — |
| `sessoes[].rotas` | object | Rotas recebidas, aceitas, filtradas e exportadas pelo route server para o membro. | — | — |
| `sessoes[].import_limit` | int | Limite de prefixos aceitos por sessão (`receive_limit` e `import_limit` do route server). | — | — |
| `sessoes[].descricao` | str | Nome do membro como cadastrado no route server (organização, não pessoa). | — | — |

### [ixbr_alice_rotas](fontes/ixbr_alice_rotas.md) — Rotas rejeitadas e communities dos membros nos route servers do IX.br (Alice-LG, níveis 2 e 3)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `vizinhos[].total` | int | Número de rotas do vizinho no conjunto consultado (`pagination.total_results` do Alice): rejeitadas (rs_filtered) ou recebidas (rs_communities). | O total vem da paginação, não do tamanho da página (250). | — |
| `vizinhos[].motivos` | dict | rs_filtered: {community grande de rejeição: nº de rotas} (`26162:100:0` inválido no Registro.br, `26162:190:0..5` prefixo/ASN inválido, bogon, trânsito, nunca via RS, prefixos do IX.br, `26162:300:0` RPKI inválido, `26162:400:0` inválido nos RIRs, `26162:616:666` blackhole confirmado), decodificadas pelo dicionário `ixbr_communities` do snapshot. | Contagem exata (`contagem` = exata) ou pela amostra (`amostra`, quando o Alice não traz `filters_available`). `sem_motivo` = rotas sem community de motivo decodificada. | — |
| `vizinhos[].amostra` | list | rs_filtered: até 25 rotas rejeitadas do vizinho (prefixo, ASN de origem, motivos): dado público de roteamento. | Amostra, nunca a lista completa; o produto mostra no máximo 5 por ASN e motivo. | — |
| `vizinhos[].comunidades` | dict | rs_communities: {community: nº de rotas recebidas que a carregam}, nas formas padrão (`a:b`), grande (`a:b:c`) e estendida (`ro:a:b`, `rt:a:b`). | A decodificação (não exportar, exportar somente, RIR, PTT, blackhole) é do produto `rs_policy`, pelo dicionário do snapshot. | — |
| `vizinhos[].herdado` | bool | Verdadeiro se o vizinho não coube no orçamento desta rodada e vem da rodada anterior, com o `coletado_em` original (idade máxima 35 dias). | — | — |
| `vizinhos[].consultado_em` | str | Instante (relógio do coletor) em que o vizinho foi consultado; é ele, e não o `coletado_em` (`cached_at` do Alice, que pode ser mais velho), que ordena o rodízio. | — | — |
| `falhas` | list | Vizinhos cuja consulta falhou nesta rodada ou em rodadas anteriores sem leitura posterior (ixp, afi, asn, ip, instante e erro); vão para o fim da fila do rodízio. | — | — |
| `cobertura_rodizio` | dict | `total` e `por_ptt`: vizinhos elegíveis hoje, lidos nesta rodada, herdados (leitura de rodada anterior), sem leitura nenhuma, route servers pulados por lentidão e idade máxima da leitura em dias (pelo `coletado_em`). | Campo aditivo; o produto nunca extrapola para quem não tem leitura. | — |
| `tempo_por_rs` | dict | Por route server: consultas feitas, segundos médios e máximo no relógio da coleta e ms médios de servidor (`request_duration_ms` do Alice). | Base para ajustar orçamento e taxa com o IX.br; route server lento sai da rodada (`rs_pulados`). | — |
| `rs_pulados` | list | Route servers tirados da rodada por lentidão (3 consultas seguidas acima de ARANDU_ALICE_LENTO_S, padrão 20 s); seus vizinhos ficam com a coleta anterior (`herdado`). | — | — |
| `cobertura` | dict | Por PTT, vizinhos elegíveis, coletados nesta rodada e herdados. | A cobertura do nível 3 é parcial por desenho (rodízio dentro do orçamento): o produto nunca extrapola para quem não foi coletado. | — |

### [ixbr_api](fontes/ixbr_api.md) — Cadastro de membros do IX.br (dashboard.ix.br)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ixp` | str | Código do IXP (ex.: sp, rj). | — | — |
| `fetched_at` | datetime | Instante UTC em que a lista foi obtida. | — | — |
| `members_count` | int | Quantidade de membros cadastrados no IXP (>= ASNs vistos no Route Server). | — | ixp_docs → ixps/index.json#ixbr_members_count |
| `members[].asn` | int | ASN do membro cadastrado. | Servido pela API lendo raw/{date}/{ixp}/ixbr_members.json (o raw não pode ser removido antes da retenção do snapshot). | ixp_docs → ixps/index.json#ixbr_members_count |
| `members[].name` | str | Nome do membro como cadastrado no IX.br. | Servido pela API lendo o raw (ver members[].asn). | — |

### [lacnic_delegated](fontes/lacnic_delegated.md) — ASNs delegados ao Brasil (LACNIC delegated-extended)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `br_asns` | list[int] | ASNs com country=BR e status allocated ou assigned no LACNIC. | 'assigned' incluído para capturar transferências. | asn_docs → asns/{asn}.json#is_br |
| `total_br_asns` | int | Quantidade de ASNs brasileiros. | Base do universo de consulta do peeringdb_networks. | — |
| `source_sha256` | str | SHA-256 do arquivo bruto. | — | — |

### [lg_ixbr](fontes/lg_ixbr.md) — Looking Glasses do IX.br (tabelas BGP dos Route Servers)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `collection_manifest.ixps[].v6/v4` | dict | Resultado da coleta de uma família de endereços em um IXP (ok, tamanho, tentativas, erro). | — | snapshot → manifest.json#ixps_collected; snapshot → manifest.json#ixps_failed |
| `bgp-v{4,6}-{ixp}-{as_of}.txt` | texto | Saída literal do comando de tabela BGP do Route Server do IXP, uma linha por rota. | Parseado por products.bgp_routes.build (produto bgp_ixp_normalizado). | — |

### [manrs_participantes](fontes/manrs_participantes.md) — MANRS — participantes do programa de operadores de rede

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `participantes[]` | lista | Uma entrada por organização participante, com `org`, `aprovado`, `areas`, `asns` e as ações (`filtragem`, `anti_spoofing`, `coordenacao`, `roteamento`) como a tabela as mostra (marca de ação atendida ou pontuação em %). | Nunca sai de data/normalized: só `products.manrs.build` lê, e só publica agregados com mínimo de 5 ASNs participantes por recorte. | — |
| `medido_em` | str | Data da última medição do Observatório, informada na legenda da tabela. | — | — |

### [ooni_bloqueios](fontes/ooni_bloqueios.md) — OONI — medições de interferência no Brasil, agregadas por ASN (bucket aberto)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `dias[AAAA-MM-DD].testes[teste][asn]` | dict | Medições válidas (`n`), com anomalia declarada pela sonda (`anom`), por componente (`partes`) e, no tor, alvos totais/acessíveis por tipo (`alvos`). O dia é o da pasta do bucket (lote do dia, UTC). | Veredito da PRÓPRIA sonda segundo o ooni/spec (ts-015, ts-018, ts-019, ts-020, ts-023, ts-029); não é o do backend do OONI. Medição do signal com test_version <= 0.2.3 é descartada (falsos positivos documentados). | — |
| `dias[AAAA-MM-DD].web` | dict | webconnectivity por ASN no dia, só da AMOSTRA de horas: `n`, `anom` (blocking = dns, tcp_ip, http-failure ou http-diff), `partes`, `sem_veredito`, `inacessivel`. Nenhum domínio, URL ou categoria. | Amostra rotulada; veredito da sonda; https nunca recebe veredito de bloqueio pela sonda (ts-017), então a taxa é um piso. | — |
| `dias[AAAA-MM-DD].web_amostra` | dict | Horas UTC amostradas, arquivos lidos e esperados, bytes e se a amostra do dia ficou completa (o teto de GB pode cortá-la). | — | — |
| `ultima_execucao` | dict | Custo da última execução (dias baixados, requisições, bytes baixados, arquivos, medições lidas e descartadas, segundos). | — | — |
| `licenca / atribuicao` | str | CC BY-NC-SA 4.0 e o texto de atribuição, que acompanham todo derivado. | — | — |

### [peeringdb_contacts](fontes/peeringdb_contacts.md) — Contatos de redes BR no PeeringDB (poc)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `contacts[asn][].role` | str | Papel do contato (Abuse, NOC, Policy, Technical, Sales…). | — | asn_docs → /api/v1/asns/{asn}/contacts |
| `contacts[asn][].name` ⚠️ dado pessoal/contato | str | Nome do contato (pode ser pessoa física). | LGPD: não é produto público. | asn_docs → /api/v1/asns/{asn}/contacts |
| `contacts[asn][].email` ⚠️ dado pessoal/contato | str | E-mail do contato. | Só via /contacts com login. | asn_docs → /api/v1/asns/{asn}/contacts |
| `contacts[asn][].phone` ⚠️ dado pessoal/contato | str | Telefone do contato. | Só via /contacts com login. | asn_docs → /api/v1/asns/{asn}/contacts |
| `contacts[asn][].visible` | str | Visibilidade do POC no PeeringDB. Só `Public` é pedido e servido; `Users` (restrito pelo dono da rede a usuários autenticados do PeeringDB) fica de fora, porque o login do site não distingue provedor. | A leitura confere o valor; arquivo de coleta anterior a 2026-11-17, sem o campo, não é servido. | — |

### [peeringdb_fac](fontes/peeringdb_fac.md) — Instalações, carriers, campus e atributos das redes do Brasil (PeeringDB)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `facilities[id]` | dict | Instalação do PeeringDB (nome, organização, cidade, UF, país, coordenadas, site, propriedade, contagens declaradas, datas de criação e atualização, campus). | Autodeclarado; lista branca de campos (sem contatos, notes, redes sociais, endereço de rua nem CEP). | instalacoes → instalacoes/instalacoes.json.gz#instalacoes |
| `netfac / ixfac / carrierfac` | list | Vínculos rede × instalação (só instalações do Brasil), PTT × instalação e carrier × instalação, com as datas de criação e atualização do vínculo de rede. | Declaração no cadastro; não indica tráfego nem contrato. | instalacoes → instalacoes/vinculos.json.gz#por_asn; instalacoes → instalacoes/vinculos.json.gz#por_instalacao |
| `carriers[id] / campus[id]` | dict | Carriers e campus das instalações coletadas (nome, organização, site, datas). | Autodeclarado; sem notes nem redes sociais. | instalacoes → instalacoes/instalacoes.json.gz#carriers; instalacoes → instalacoes/instalacoes.json.gz#campus |
| `redes[asn]` | dict | Escopo geográfico, IPv6, multicast, unicast, "nunca via route server", URLs de looking glass e de route server, datas e contagens declaradas da rede. | Autodeclarado; URL só se for http(s), telnet ou ssh sem credencial embutida; sem notes, contatos nem política. | instalacoes → instalacoes/atributos_rede.json.gz#asns |

### [peeringdb_intl_geo](fontes/peeringdb_intl_geo.md) — Geolocalização de ASNs internacionais (PeeringDB org + Nominatim)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].name / city / country` | str | Nome da organização, cidade e país no PeeringDB. | — | asn_docs → asns/{asn}.json#geo_org |
| `asns[asn].lat / lon` | float | Coordenadas da organização (PeeringDB) ou da cidade (Nominatim); nulas quando desconhecidas. | — | mapas_prefixos → maps/asns.geojson |
| `asns[asn].geo_confidence` | str | org_coords, city_centroid ou unknown. | Rótulo do método. | — |

### [peeringdb_ixps](fontes/peeringdb_ixps.md) — IXPs e membros (PeeringDB netixlan)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `external_ixps[code].name/city/country` | str | Nome, cidade e país do IXP externo (da configuração, não da API). | — | ixp_docs → external-ixps/{ixp}.json |
| `external_ixps[code].pdb_ix_id` | int | Identificador do IX no PeeringDB. | — | ixp_docs → external-ixps/{ixp}.json#pdb_ix_id |
| `external_ixps[code].members[]` | list[dict] | Membros do IXP externo (asn, velocidade da porta). | Marca is_br pelo universo LACNIC-BR. O nome do membro vem de asn_names na publicação (o `name` do netixlan é o nome do PTT; se um snapshot o tiver gravado como nome do membro, a API o corrige na leitura). | ixp_docs → external-ixps/{ixp}.json#members |
| `ixbr_ixps[code].asns` | list[int] | ASNs que declaram presença no IXP do IX.br no PeeringDB. | Comparado ao Route Server e ao cadastro do IX.br; diferença = membro sem cadastro PDB. | asn_docs → asns/{asn}.json#ixp_member_codes |
| `per_asn[asn].external / ixbr` | list[str] | Códigos de IXPs externos e do IX.br em que o ASN declara presença. | — | asn_docs → asns/{asn}.json#external_ixps |

### [peeringdb_networks](fontes/peeringdb_networks.md) — Redes brasileiras no PeeringDB (net)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `networks[asn].name / aka` | str | Nome e nome alternativo da rede cadastrada no PeeringDB. | — | asn_docs → asns/{asn}.json#pdb |
| `networks[asn].info_type` | str | Tipo de rede declarado (NSP, Cable/DSL/ISP, Content, Enterprise, Educational…). | Autodeclarado. | asn_docs → asns/{asn}.json#pdb |
| `networks[asn].info_traffic` | str | Faixa de tráfego declarada. | Autodeclarado. | asn_docs → asns/{asn}.json#pdb |
| `networks[asn].info_ratio` | str | Razão de tráfego declarada (ex.: Balanced, Heavy Inbound). | Autodeclarado. | asn_docs → asns/{asn}.json#pdb |
| `networks[asn].info_prefixes4 / info_prefixes6` | int | Quantidade de prefixos que a rede declara anunciar. | Autodeclarado; comparável aos prefixos observados na tabela global. | asn_docs → asns/{asn}.json#pdb |
| `networks[asn].policy_general / policy_locations / policy_ratio / policy_contracts` | str\|bool | Política de peering declarada (Open/Selective/Restrictive), exigência de localização, de razão de tráfego e de contrato. | Autodeclarado. | asn_docs → asns/{asn}.json#pdb |
| `networks[asn].irr_as_set` | str | as-set de IRR declarado para filtragem de prefixos. | — | asn_docs → asns/{asn}.json#pdb |
| `networks[asn].website` | str | Site da rede. | — | asn_docs → asns/{asn}.json#pdb |
| `pdb_registered / total_br_asns` | int | ASNs BR com registro no PeeringDB e total de ASNs BR consultados. | Checado por publish.coleta_checks (a coleta falha alto em queda anormal). | snapshot → summary.json#br_asns_peeringdb |

### [prefix_geo](fontes/prefix_geo.md) — Geolocalização dos prefixos do Registro.br (DB-IP City Lite)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `prefixes[prefix].lat / lon` | float | Coordenadas do centroide da cidade que o DB-IP associa ao prefixo. | Sempre centroide de cidade. | asn_docs → asns/{asn}.json#geo_prefixes_v4; mapas_prefixos → maps/prefixes.geojson |
| `prefixes[prefix].city / country / uf` | str | Cidade, país e UF segundo o DB-IP (município derivado das coordenadas). | — | asn_docs → asns/{asn}.json#geo_prefixes_v4 |
| `prefixes[prefix].geo_confidence` | str | Sempre 'city_centroid'. | Geolocalização de IP é aproximada. | — |
| `prefixes[prefix].geo_source / mmdb_month` | str | Versão do banco usada (dbip-lite-AAAA-MM). | — | snapshot → manifest.json#geolite2_version |

### [rdap](fontes/rdap.md) — Organizações BR a partir do Registro.br (ASN→nome/CNPJ)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `orgs[asn].name` | str | Nome da organização titular do ASN no whois do NIC.br. | — | asn_docs → asns/{asn}.json#name |
| `orgs[asn].cnpj` | str | CNPJ da organização. | — | asn_docs → asns/{asn}.json#cnpj |
| `total / with_cnpj` | int | ASNs no mapeamento e quantos têm CNPJ. | — | — |

### [rdap_contatos](fontes/rdap_contatos.md) — Contatos dos ASNs do Brasil no RDAP do Registro.br (administrativo e abuso)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `contatos[asn].contatos[].papel` | str | Papel do contato no RDAP (`administrative` ou `abuse`). | — | asn_docs → /api/v1/asns/{asn}/contacts |
| `contatos[asn].contatos[].email` ⚠️ dado pessoal/contato | str | E-mail do contato, em minúsculas. | Só via /asns/{asn}/contacts com login; nunca em log, rota pública nem MCP. | asn_docs → /api/v1/asns/{asn}/contacts |
| `contatos[asn].contatos[].handle` ⚠️ dado pessoal/contato | str | Identificador do contato no Registro.br (pode identificar pessoa física; mantenedor decide se fica). | Só via login. | — |
| `contatos[asn].em / tentou_em / status / incompletas` | dict | Data da última leitura VÁLIDA (`em`; nula se só houve respostas incompletas), data da última tentativa, situação (`completo`, `parcial_confirmado`, `nao_encontrado`, `incompleto`) e quantas respostas incompletas em ritmo saudável o ASN acumulou. | Incompleta não conta como leitura válida: a leitura anterior continua valendo com a data dela. `parcial_confirmado` = faltou e-mail em duas consultas com a fonte respondendo bem (ausência real, não degradação). | asn_docs → /api/v1/asns/{asn}/contacts |
| `cobertura` | dict | ASNs no universo (Registro.br), com leitura válida, completos, parcial confirmado, não encontrados, só incompletos, datas da leitura mais antiga e mais recente. | Declarada ("N de M ASNs com contato lido; leitura mais antiga em AAAA-MM-DD"); ASN sem leitura não é ASN sem contato. | asn_docs → /api/v1/asns/{asn}/contacts |

### [receita_cnpj](fontes/receita_cnpj.md) — Cadastro das empresas de telecom (dados abertos do CNPJ — Receita Federal)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `estabelecimentos[cnpj8][]` | lista | Estabelecimentos do recorte de telecom por CNPJ básico. `c` CNPJ de 14 dígitos, `m` 1 matriz ou 2 filial, `s` situação cadastral (02 ativa, 08 baixada), `d` início da atividade, `ds` data da situação, `u` UF, `mu` código de município da Receita, `p` CNAE principal, `x` CNAEs secundários (até 20), `n` nome fantasia (ausente em empresário individual). | Sem rua, número, complemento, bairro, CEP, telefone nem e-mail. O município é código da Receita (não é IBGE): a tradução é feita no produto, por nome e UF. | — |
| `empresa[cnpj8]` | dict | Natureza jurídica, capital social, porte (00 não informado, 01 micro, 03 pequeno, 05 demais) e razão social. | Empresário individual (natureza 2135) não leva razão social. | — |
| `simples[cnpj8]` | dict | Opção pelo Simples Nacional e pelo MEI, com as datas de opção e de exclusão. | — | — |
| `municipios_rfb / naturezas / cnaes` | dict | Tabelas de apoio da Receita (código → nome), restritas aos CNAEs que aparecem no recorte. | — | — |
| `dump_reference / linhas_lidas / estabelecimentos_guardados / universo_cnpjs_basicos` | dict | Mês (AAAA-MM) do dump, linhas lidas, estabelecimentos guardados e tamanho do universo de CNPJs das outorgas e do SICI. | — | — |

### [receita_socios](fontes/receita_socios.md) — Quadro societário (dados abertos do CNPJ — Receita Federal)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `by_cnpj_basico[cnpj8][].nome_socio` ⚠️ dado pessoal/contato | str | Nome do sócio (PF) ou razão social (PJ). | PF: dado pessoal (LGPD); só entra em produto agregado. | grupos_societarios → grupos_societarios.json.gz#by_cnpj |
| `by_cnpj_basico[cnpj8][].cnpj_cpf_socio` ⚠️ dado pessoal/contato | str | Para PJ: 8 dígitos do CNPJ básico do sócio; para PF: CPF com 3 primeiros e 2 últimos dígitos ocultos. | CPF mascarado pela Receita; colisões possíveis (falso positivo). | — |
| `by_cnpj_basico[cnpj8][].identificador_socio` | str | 1=Pessoa Jurídica, 2=Pessoa Física, 3=Estrangeiro. | — | — |
| `by_cnpj_basico[cnpj8][].qualificacao_socio` | str | Código de qualificação do sócio (administrador, sócio, etc.). | — | — |
| `by_cnpj_basico[cnpj8][].data_entrada_sociedade` | str | Data de entrada do sócio na sociedade. | — | — |
| `by_cnpj_basico[cnpj8][].faixa_etaria` ⚠️ dado pessoal/contato | str | Código da faixa etária do sócio PF (1=0–12 … 9=80+; 0=não se aplica). | — | — |
| `dump_reference` | str | Mês de referência (AAAA-MM) do dump da Receita usado. | — | — |

### [registro_br](fontes/registro_br.md) — Blocos e ASNs do Registro.br (nicbr-asn-blk)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[].asn` | int | Número do sistema autônomo registrado no NIC.br. | — | asn_docs → asns/{asn}.json#asn |
| `asns[].name` | str | Nome da organização titular do ASN no whois do NIC.br. | — | asn_docs → asns/{asn}.json#name |
| `asns[].cnpj` | str | CNPJ (14 dígitos) da organização; chave de junção com Anatel e Receita. | Vazio quando o whois não informa. | asn_docs → asns/{asn}.json#cnpj |
| `asns[].prefixes_v6` | list[str] | Prefixos IPv6 alocados à organização no whois. | — | asn_docs → asns/{asn}.json#rir_prefixes_v6 |
| `asns[].prefixes_v4` | list[str] | Prefixos IPv4 alocados à organização no whois. | — | asn_docs → asns/{asn}.json#rir_prefixes_v4 |
| `total_asns / total_prefixes_v6 / total_prefixes_v4` | int | Totais do arquivo do dia. | Checados por publish.coleta_checks (variação máxima entre coletas). | — |
| `source_sha256` | str | SHA-256 do arquivo bruto baixado; prova de proveniência. | — | — |
| `registro_br_diff.{added,removed,changed}` | list | Diferença entre este arquivo e o do snapshot anterior (ASNs incluídos, removidos e alterados). | Gerado só quando há snapshot anterior (use --no-diff para omitir). | — |

### [rpki_collector](fontes/rpki_collector.md) — VRPs e ASPA validados (Routinator)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `vrps[].asn` | str\|int | ASN autorizado a originar o prefixo pela ROA. | — | rpki_collector → rpki/vrp_list.json.gz#asn |
| `vrps[].prefix` | str | Prefixo coberto pela ROA. | — | rpki_collector → rpki/vrp_list.json.gz#prefix |
| `vrps[].maxLength` | int | Comprimento máximo de prefixo autorizado (mais específicos até este valor são cobertos). | — | rpki_collector → rpki/vrp_list.json.gz#maxLength |
| `vrps[].ta` | str | Trust Anchor (RIR) que emitiu a ROA. | — | rpki_collector → rpki/vrp_list.json.gz#ta |
| `aspa[].customer` | int | ASN que publicou o objeto ASPA (cliente). | — | rpki_collector → rpki/aspa_list.json.gz#customer |
| `aspa[].providers` | list[int] | ASNs provedores autorizados pelo objeto ASPA. | — | rpki_collector → rpki/aspa_list.json.gz#providers |
| `aspa[].tal` | str | Trust Anchor (RIR) que emitiu o objeto ASPA. | — | rpki_collector → rpki/aspa_list.json.gz#tal |

### [scm_geo](fontes/scm_geo.md) — Geolocalização das outorgas SCM (Nominatim)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `lat / lon` | float | Coordenadas geocodificadas do endereço da sede. | Posição do endereço (ou centroide), não da área de cobertura. | outorgas → maps/scms.geojson |
| `geo_confidence` | str | Confiança da geocodificação: exact_address, cep_centroid, city_centroid ou unknown. | Rótulo do método; não é erro em metros. | — |
| `geo_source` | str | Origem da coordenada (nominatim ou cache). | — | outorgas → maps/scms.geojson |
| `geolocated / cached / unknown` | int | Contagens do lote: geocodificados, vindos do cache e sem resultado. | — | — |

### [seac_geo](fontes/seac_geo.md) — Geolocalização das outorgas SEAC (Nominatim)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `lat / lon` | float | Coordenadas geocodificadas do endereço da sede. | Posição do endereço (ou centroide), não da área de cobertura. | outorgas → maps/seacs.geojson |
| `geo_confidence` | str | Confiança da geocodificação: exact_address, cep_centroid, city_centroid ou unknown. | Rótulo do método; não é erro em metros. | — |
| `geo_source` | str | Origem da coordenada (nominatim ou cache). | — | outorgas → maps/seacs.geojson |
| `geolocated / cached / unknown` | int | Contagens do lote: geocodificados, vindos do cache e sem resultado. | — | — |

### [shodan_exposicao](fontes/shodan_exposicao.md) — Shodan — contagens de serviços expostos por ASN do Brasil (API principal, atribuição obrigatória)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn]` | dict | Leitura do ASN: `em` (data), `total` (serviços observados, banners e não IPs únicos), `portas` (as 20 mais vistas, [porta, n]), `risco` (contagem exata de cada porta de risco com serviço), `risco_total` (serviços em qualquer porta de risco) e `vulns` (CVEs mais vistas [cve, n]; nulo se o plano não tem a faceta ou o ASN não foi consultado por ela). | Rodízio de `SHODAN_ASNS_POR_EXECUCAO` ASNs por execução (padrão 1.500), os nunca lidos primeiro e depois os de leitura mais antiga. Três consultas por ASN com serviço (geral, portas de risco, CVEs), uma só se não há serviço. `total` 0 = o Shodan não observou serviço; ASN ausente = não consultado. | exposicao → exposicao/asns.json.gz#asns |
| `plano` | dict | Facetas que a conta aceita (`port`; `vuln` pode ser `indisponivel`, com a data do teste). | A faceta `vuln` recusada é registrada e só reexperimentada depois de 30 dias. | exposicao → exposicao/asns.json.gz#plano |
| `licenca / atribuicao` | str | Licença/termos resumidos e o texto de atribuição ao Shodan, que acompanha todo derivado. | — | exposicao → exposicao/asns.json.gz#licenca; exposicao → exposicao/asns.json.gz#fonte |

### [siasg_contratos](fontes/siasg_contratos.md) — Compras.gov.br (PNCP, Lei 14.133) — resultados de itens por fornecedor de telecom, em rodízio

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `fornecedores[raiz].itens[]` | lista | Resultados de itens do CNPJ de matriz da raiz: chave do item, contratação (número de controle do PNCP), unidade e UF do órgão, CNPJ do órgão, quantidade, valor total homologado (R$), situação e data do resultado. | Mesclados pela chave do item a cada leitura (janela incremental de 45 dias de sobreposição); só fornecedor com CNPJ de 14 dígitos. Filial não é consultada. | contratos → contratos/operadoras.json.gz#operadoras |
| `fornecedores[raiz].lida_em / herdado / incompleto` | dict | Data da leitura da raiz, se esta rodada só herdou a leitura anterior e se o limite de páginas cortou a leitura. | Cada raiz leva a data da sua leitura; o produto publica a idade e a cobertura. Raiz sem leitura não aparece como zero. | contratos → contratos/operadoras.json.gz#cobertura |
| `compras[numero]` | dict | Detalhe da contratação: órgão (razão social e CNPJ), esfera (federal, estadual, municipal, distrital, como informado no PNCP), UF, município do órgão (nome e código IBGE), modalidade e objeto resumido (300 caracteres). | Um GET por contratação, em ordem de valor, dentro do orçamento da rodada; o que ainda não foi enriquecido fica sem esses campos (o produto declara a cobertura). | contratos → contratos/operadoras.json.gz#operadoras |
| `uasg[codigo]` | dict | Unidade de compra ativa (UASG) com nome, UF, município (nome e IBGE) e CNPJ do órgão. | Tabela renovada a cada 30 dias (45 páginas); dá o município do órgão comprador para todo item, sem GET por contratação. | contratos → contratos/municipios.json.gz#municipios |
| `faixas / ultima_execucao` | dict | Faixa (A, B ou C) de cada raiz do universo e a medição da última rodada (fornecedores lidos, requisições, segundos, motivo da parada, raízes sem leitura). | — | contratos → contratos/operadoras.json.gz#cobertura |

### [smp_geo](fontes/smp_geo.md) — Geolocalização das outorgas SMP (Nominatim)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `lat / lon` | float | Coordenadas geocodificadas do endereço da sede. | Posição do endereço (ou centroide), não da área de cobertura. | outorgas → maps/smps.geojson |
| `geo_confidence` | str | Confiança da geocodificação: exact_address, cep_centroid, city_centroid ou unknown. | Rótulo do método; não é erro em metros. | — |
| `geo_source` | str | Origem da coordenada (nominatim ou cache). | — | outorgas → maps/smps.geojson |
| `geolocated / cached / unknown` | int | Contagens do lote: geocodificados, vindos do cache e sem resultado. | — | — |

### [socios_grupos](fontes/socios_grupos.md) — Grupos societários entre operadoras (cruzamento do QSA)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `grupos[].grupo_id` | str | Identificador do grupo (determinístico a partir dos CNPJs básicos ordenados). | — | grupos_societarios → grupos_societarios.json.gz#grupos |
| `grupos[].classificacao` | str | Rótulo do tipo de relação que formou o grupo. | Inferido; transitividade não é aplicada dentro do grupo. | grupos_societarios → grupos_societarios.json.gz#grupos |
| `by_cnpj[cnpj].mesmo_grupo` | list | CNPJs com quadro de sócios idêntico ou controlador exclusivo. | Relação TOTAL, não inferida por transitividade. | grupos_societarios → grupos_societarios.json.gz#by_cnpj |
| `by_cnpj[cnpj].relacionadas_parcial` | list[dict] | CNPJs com sócios em comum, com a contagem e os nomes dos sócios PJ em comum (pessoa física só conta). | PARCIAL: pode haver falso positivo por colisão de nome + CPF mascarado. | grupos_societarios → grupos_societarios.json.gz#by_cnpj |
| `by_cnpj[cnpj].grupo_inferivel / motivo` | bool / str | `false` com `motivo` = `sa_quadro_sem_acionistas` nas sociedades anônimas (natureza jurídica 2046 e 2054 da Receita, `receita_cnpj`): o quadro da Receita de S.A. traz diretoria e conselho, não acionistas, e não gera ligação. Ausente nas demais empresas. | Decisão P8: grupo não inferido pelo quadro de S.A.; a ligação que vem do quadro de outra empresa em que a S.A. é sócia com participação continua. Comandita por ações (2097) fica como pendência, sem caso no universo. Sem nomes. | grupos_societarios → grupos_societarios.json.gz#by_cnpj |
| `efeito_da_regra.sociedades_anonimas_sem_inferencia` | int | Quantas raízes de CNPJ do universo são S.A. e ficam sem inferência pelo quadro (P8). | — | grupos_societarios → grupos_societarios.json.gz#efeito_da_regra |
| `by_cnpj[cnpj].holdings_externas` | list[dict] | Cadastro completo (BrasilAPI) das controladoras fora do universo de outorgas. | — | grupos_societarios → grupos_societarios.json.gz#by_cnpj |
| `by_cnpj[cnpj].socios` ⚠️ dado pessoal/contato | list[dict] | Quadro de sócios do CNPJ; nome e CNPJ básico só de sócio PJ. | LGPD: sócio pessoa física ou estrangeiro sai só com tipo e qualificação, sem nome nem CPF (core.cpf.sem_socios_pessoa_fisica). | grupos_societarios → grupos_societarios.json.gz#by_cnpj |

### [stfc_geo](fontes/stfc_geo.md) — Geolocalização das outorgas STFC (Nominatim)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `lat / lon` | float | Coordenadas geocodificadas do endereço da sede. | Posição do endereço (ou centroide), não da área de cobertura. | outorgas → maps/stfcs.geojson |
| `geo_confidence` | str | Confiança da geocodificação: exact_address, cep_centroid, city_centroid ou unknown. | Rótulo do método; não é erro em metros. | — |
| `geo_source` | str | Origem da coordenada (nominatim ou cache). | — | outorgas → maps/stfcs.geojson |
| `geolocated / cached / unknown` | int | Contagens do lote: geocodificados, vindos do cache e sem resultado. | — | — |

### [telegeography_cables](fontes/telegeography_cables.md) — Cabos submarinos (TeleGeography)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `cables[].name / id` | str | Nome e identificador do cabo. | — | mapas_infraestrutura → maps/submarine_cables.geojson |
| `cables[].length / owners / rfs_year / is_planned` | str\|int\|bool | Extensão, proprietários, ano de entrada em serviço e se é planejado. | — | mapas_infraestrutura → maps/submarine_cables.geojson |
| `cables[].landing_countries` | list[str] | Países de aterragem. | — | mapas_infraestrutura → maps/submarine_cables.geojson |
| `landing_points[]` | dict | Pontos de aterragem (nome, id, geometria). | — | mapas_infraestrutura → maps/submarine_landing_points.geojson |

## Produtos

### [abuso_agregado](produtos/abuso_agregado.md) — Abuso agregado por ASN (Feodo Tracker)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].feodo_c2 / feodo_c2_online / feodo_malware` | dict | Servidores C2 do Feodo Tracker em prefixos do ASN, quantos online e por família. | Contagem de terceiros na data da coleta; o ASN que hospeda não é dono do servidor; sem veredito. | abuso_agregado → abuso_agregado/asns.json.gz#asns |
| `feodo_total_mundo / feodo_online_mundo / feodo_asns_br / feodo_c2_br` | int | Totais da lista no mundo e no Brasil. | — | abuso_agregado → abuso_agregado/asns.json.gz#feodo_total_mundo; abuso_agregado → abuso_agregado/asns.json.gz#feodo_online_mundo; abuso_agregado → abuso_agregado/asns.json.gz#feodo_asns_br; abuso_agregado → abuso_agregado/asns.json.gz#feodo_c2_br |
| `fonte / urlhaus / limites / coletado_em` | dict | Fonte e licença, estado do URLhaus (indisponível), limitações e instante da coleta. | — | abuso_agregado → abuso_agregado/asns.json.gz#fonte; abuso_agregado → abuso_agregado/asns.json.gz#urlhaus; abuso_agregado → abuso_agregado/asns.json.gz#limites; abuso_agregado → abuso_agregado/asns.json.gz#coletado_em |
| `snapshot_date / generated_at` | str | Data do snapshot e instante UTC de geração. | — | abuso_agregado → abuso_agregado/asns.json.gz#snapshot_date; abuso_agregado → abuso_agregado/asns.json.gz#generated_at |

### [area_influencia_ptt](produtos/area_influencia_ptt.md) — Área de influência observada dos PTTs do IX.br

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ptts[code].visoes[diretos|todos]` | dict | Operadoras (CNPJs), municípios e acessos atribuídos ao PTT; P50, P80 e P90 da distância em km (peso por acessos); mediana por operadora (cada operadora conta 1); municípios e acessos por faixa; e, por município, os acessos atribuídos e a faixa (1 até o P50, 2 até o P80, 3 além). `null` quando nenhuma operadora é atribuída ao PTT na visão. | INFERIDO. Os acessos de cada par (município, CNPJ) vão para o PTT mais próximo entre os que o CNPJ enxerga na visão (união dos PTTs dos ASNs ligados ao CNPJ pelo SICI); cada acesso conta uma vez, mesmo num CNPJ com vários ASNs. Linha reta do centroide do município ao PIX mais próximo. Sem exclusão de operadoras. Nenhum nome de operadora é publicado, só contagens. | area_influencia_ptt → territorio/area_influencia_ptt.json.gz#ptts |
| `ptts[code].pix` | dict | Quantos PIX do PTT têm coordenada no cadastro, quantos foram posicionados no centroide do município do endereço e quantos no da sede, se o posicionamento é aproximado, e os pontos usados no cálculo. | PIX sem coordenada em `config/pix.yaml` vai para o centroide do município do endereço; sem endereço reconhecível, para o da sede do PTT. PTT sem PIX no cadastro usa a sede. | area_influencia_ptt → territorio/area_influencia_ptt.json.gz#ptts |
| `municipios[diretos|todos][ibge]` | list | [PTT principal, faixa nesse PTT, acessos atribuídos ao principal, acessos atribuídos no município, nº de PTTs que recebem acessos do município]. Principal é o PTT com mais acessos do município. | INFERIDO. Município sem operadora atribuída a PTT na visão não consta. | area_influencia_ptt → territorio/area_influencia_ptt.json.gz#municipios |
| `municipios_nomes[ibge]` | str | "Nome/UF" dos municípios que aparecem nas listas, para a tabela de alternativa textual ao mapa. | — | area_influencia_ptt → territorio/area_influencia_ptt.json.gz#municipios_nomes |
| `totais[diretos|todos]` | dict | Acessos do SICI no país, atribuídos a algum PTT, sem PTT visível para a operadora e em município sem centroide; CNPJs com mais de um ASN. | — | area_influencia_ptt → territorio/area_influencia_ptt.json.gz#totais |
| `ptts_com_pix_aproximado / faixas / metodo / limites / fontes / natureza / snapshot_date / generated_at` | list / dict / str | PTTs com algum PIX posicionado por centroide, definição das faixas, método em texto, limites, o mês do SICI e o rótulo de natureza. | — | area_influencia_ptt → territorio/area_influencia_ptt.json.gz#ptts_com_pix_aproximado; area_influencia_ptt → territorio/area_influencia_ptt.json.gz#faixas; area_influencia_ptt → territorio/area_influencia_ptt.json.gz#metodo; area_influencia_ptt → territorio/area_influencia_ptt.json.gz#limites; area_influencia_ptt → territorio/area_influencia_ptt.json.gz#fontes; area_influencia_ptt → territorio/area_influencia_ptt.json.gz#natureza; area_influencia_ptt → territorio/area_influencia_ptt.json.gz#snapshot_date; area_influencia_ptt → territorio/area_influencia_ptt.json.gz#generated_at |

### [as2org](produtos/as2org.md) — Organização por ASN (CAIDA) e irmãos do Brasil

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].org_nome / org_id / org_pais / membros_total` | dict | Organização do ASN no CAIDA AS Rank. | Inferência do CAIDA a partir do WHOIS; pode agrupar filiais sob uma 'Parent'; rotulada como do CAIDA. | as2org → as2org/asns.json.gz#asns |
| `asns[asn].irmaos_br` | list[int] | Outros ASNs do Brasil com a mesma organização. | Só ASNs do Brasil; a organização pode ter ASNs em outros países (membros_total). | as2org → as2org/asns.json.gz#asns |
| `cobertura` | dict | ASNs do Brasil do snapshot, quantos têm organização, percentual e número de organizações com mais de um ASN do Brasil. | Medida de cobertura da fonte, não de qualidade do dado. | as2org → as2org/asns.json.gz#cobertura |
| `fonte / limites / coletado_em` | dict | Fonte, citação exigida, limitações e instante da coleta. | — | as2org → as2org/asns.json.gz#fonte; as2org → as2org/asns.json.gz#limites; as2org → as2org/asns.json.gz#coletado_em |
| `snapshot_date / generated_at` | str | Data do snapshot e instante UTC de geração. | — | as2org → as2org/asns.json.gz#snapshot_date; as2org → as2org/asns.json.gz#generated_at |

### [as_relationships](produtos/as_relationships.md) — Relações entre ASNs (ARC v2)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `relacoes[].a / b / tipo` | int / int / str | Elo entre os ASNs a e b. Em p2c, a é provedor de b; em p2p, s2s e complexa, a < b. tipo pode ser sem_classificacao (inclui a abstenção e o elo rebaixado por ciclo). | Inferência rotulada; só entra o elo com ao menos um ASN brasileiro. | as_relationships → as_relationships.json.gz#relacoes |
| `relacoes[].p` | float | Probabilidade posterior da relação indicada (Naive Bayes iterativo da v2, recalibrada por temperatura); `evid.refino.p_v1` guarda a da v1. | Calibração medida na régua (sem ASPA, contra o ASPA, validação cruzada); `calibracao[afi].p_calibrada` diz se o ECE ficou dentro do limite. Abaixo de 0,5 o elo é abstido (sem_classificacao). | as_relationships → as_relationships.json.gz#relacoes |
| `relacoes[].nivel` | str | declarado (ASPA positivo), confirmado (p ≥ 0,95 e 2 fontes independentes), provavel (p ≥ 0,70 e 1 fonte independente) ou possivel. O CAIDA e os irmãos sozinhos nunca passam de possivel. | Fontes independentes são ASPA, rampa dos route servers, coletores e clique. Um p2c `provavel` cujo estrato é `conflito` ou `sem_evidencia` é publicado como `possivel` (`evid.refino.rebaixado_por_estrato`); `declarado` e `confirmado` não são tocados. | as_relationships → as_relationships.json.gz#relacoes |
| `relacoes[].estrato / p_calibrada` | str / float ou null | Só em p2c. `estrato` é a evidência independente do elo vista do provedor inferido: `ambos` (CAIDA concorda e a tripla está confirmada), `so_caida`, `so_tripla`, `conflito` (um confirma e o outro contradiz) ou `sem_evidencia`. `p_calibrada` é a taxa de acerto observada contra o ASPA (régua sem o ASPA como entrada) nesse estrato e família de endereço, só para `ambos` e `so_caida` com `n_vps` > 0; nos demais é null. | Medido: ECE da `p_calibrada` por validação cruzada por ASN de 0,0005 (v6) e 0,010 (v4); `so_tripla` tem 38 eventos e não é calibrável. CAIDA e tripla vêm dos mesmos coletores do ARC: são independentes do prior de distância ao clique, não dos dados de caminho. O ASPA tende a subestimar por ausência de registros. Tabela e data em `estratos` do documento. | as_relationships → as_relationships.json.gz#relacoes |
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

### [asn_docs](produtos/asn_docs.md) — Documentos por ASN, índice e nomes

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `is_br` | bool | ASN delegado ao Brasil pelo LACNIC (country=BR), não apenas visto no BR. | Hierarquia: LACNIC delegated, com fallback às chaves do Registro.br. | asn_docs → asns/{asn}.json#is_br |
| `ixps_direct` | list[str] | Códigos dos IXPs em que o AS tem sessão BGP direta com o Route Server. | — | asn_docs → asns/{asn}.json#ixps_direct |
| `ixps_origin` | list[str] | Códigos dos IXPs em que o AS aparece como origem de rotas (direto ou via terceiros). | — | asn_docs → asns/{asn}.json#ixps_origin |
| `ixp_presence[ixp][afi]` | dict | Por IXP e família: direct, origin e prefixos vistos. | — | asn_docs → asns/{asn}.json#ixp_presence |
| `upstreams / downstreams` | list[int] | Vizinhos nos AS-PATHs dos Route Servers (v6+v4); _v6/_v4 separam a família. | Adjacência observada, não contrato. | asn_docs → asns/{asn}.json#upstreams |
| `upstreams_global_v6/_v4 / downstreams_global_v6/_v4` | list[int] | Adjacências do grafo da tabela global (RouteViews/RIS). | Adjacência observada nos coletores. | asn_docs → asns/{asn}.json#upstreams_global_v4 |
| `is_multihomed_v6/_v4` | bool | Mais de um vizinho a montante distinto na tabela global, na família (adjacência no AS_PATH; não distingue provedor de par). | Inferido: depende de quais coletores enxergam o AS. | asn_docs → asns/{asn}.json#is_multihomed_v4 |
| `single_upstream_v6/_v4` | int\|null | O único vizinho a montante observado na tabela global (quando exatamente um); não prova dependência de um provedor. | Inferido. | asn_docs → asns/{asn}.json#single_upstream_v4 |
| `relacoes` | dict | Relações inferidas do ASN pelo produto as_relationships (ARC v1) — provedores, clientes, pares, irmãos e elos sem classificação, cada um com ASN, probabilidade, nível (declarado, confirmado, provável, possível) e famílias; n_provedores, visibilidade e single_homed/multihomed por família (null = indeterminado). | Inferência rotulada, não contrato. single_homed só é afirmado com visibilidade mínima (VPs dos coletores ou PTTs) e sem provedor apenas possível. Ausente em snapshots anteriores ao ARC. | asn_docs → asns/{asn}.json#relacoes |
| `has_ipv6` | bool | Há prefixo IPv6 alocado, anunciado ou visto em IXP. | — | asn_docs → asns/{asn}.json#has_ipv6 |
| `announced_ipv4_addresses / announced_ipv6_48s` | int | Espaço efetivamente anunciado na tabela global: equivalentes a /48 em IPv6 e endereços em IPv4. | — | asn_docs → asns/{asn}.json#announced_ipv4_addresses |
| `users_per_ip / users_per_v6_48` | float | Usuários estimados (APNIC) por endereço IPv4 anunciado / por /48. | Proxy de CGNAT; derivado de estimativa — rotular 'estimado'. | asn_docs → asns/{asn}.json#users_per_ip |
| `pdb_registered / external_ixps` | bool / list[str] | Se há cadastro no PeeringDB e os IXPs externos em que declara presença. | — | asn_docs → asns/{asn}.json#pdb_registered |
| `ixp_member_codes` | list[str] | IXPs em que o ASN consta no cadastro do IX.br (ixbr_members), mesmo sem sessão no Route Server. | — | asn_docs → asns/{asn}.json#ixp_member_codes |
| `sici` | dict | Bloco do SICI do CNPJ do AS: acessos, PF/PJ, capacidade, tecnologias, série mensal, divergência APNIC×Anatel. | 'nao_comparavel' quando acessos_compartilhados. | asn_docs → asns/{asn}.json#sici |
| `path_node_meta[asn]` | dict | Nome, is_br e espaço v6/v4 dos ASNs que aparecem em caminhos do documento. | — | asn_docs → asns/{asn}.json#path_node_meta |
| `index[].has_rpki / has_aspa` | bool | Se o AS tem ROA / objeto ASPA no snapshot. | — | asn_docs → asns/index.json#has_rpki |
| `index[].space_v6 / space_v4` | int | Espaço anunciado (/48 em IPv6; endereços em IPv4) no índice. | — | asn_docs → asns/index.json#space_v4 |
| `asn` | int | Número do sistema autônomo do documento. | — | asn_docs → asns/{asn}.json#asn |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | asn_docs → asns/{asn}.json#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | asn_docs → asns/{asn}.json#generated_at |
| `name` | str | Nome do AS (Registro.br → PeeringDB → RIPE bulk, nessa ordem de prioridade). | — | asn_docs → asns/{asn}.json#name |
| `cnpj` | str | CNPJ da organização titular, quando conhecido (Registro.br). | — | asn_docs → asns/{asn}.json#cnpj |
| `rir_prefixes_v6` | list[str] | Prefixos IPv6 alocados à organização no Registro.br. | — | asn_docs → asns/{asn}.json#rir_prefixes_v6 |
| `rir_prefixes_v4` | list[str] | Prefixos IPv4 alocados à organização no Registro.br. | — | asn_docs → asns/{asn}.json#rir_prefixes_v4 |
| `rir_prefixes_v4_count` | int | Quantidade de prefixos IPv4 alocados. | — | asn_docs → asns/{asn}.json#rir_prefixes_v4_count |
| `rir_prefixes_v6_count` | int | Quantidade de prefixos IPv6 alocados. | — | asn_docs → asns/{asn}.json#rir_prefixes_v6_count |
| `global_prefixes_v6` | list[str] | Prefixos IPv6 originados pelo AS na tabela global. | — | asn_docs → asns/{asn}.json#global_prefixes_v6 |
| `global_prefixes_v4` | list[str] | Prefixos IPv4 originados pelo AS na tabela global. | — | asn_docs → asns/{asn}.json#global_prefixes_v4 |
| `global_prefixes_v4_count` | int | Quantidade de prefixos IPv4 anunciados. | — | asn_docs → asns/{asn}.json#global_prefixes_v4_count |
| `global_prefixes_v6_count` | int | Quantidade de prefixos IPv6 anunciados. | — | asn_docs → asns/{asn}.json#global_prefixes_v6_count |
| `upstreams_v6` | list[int] | Vizinhos à esquerda no AS-PATH IPv6 dos Route Servers (adjacência; não é relação comercial). | — | asn_docs → asns/{asn}.json#upstreams_v6 |
| `upstreams_v4` | list[int] | Vizinhos à esquerda no AS-PATH IPv4 dos Route Servers (adjacência; não é relação comercial). | — | asn_docs → asns/{asn}.json#upstreams_v4 |
| `downstreams_v6` | list[int] | Vizinhos à direita no AS-PATH IPv6 dos Route Servers (adjacência; não é relação comercial). | — | asn_docs → asns/{asn}.json#downstreams_v6 |
| `downstreams_v4` | list[int] | Vizinhos à direita no AS-PATH IPv4 dos Route Servers (adjacência; não é relação comercial). | — | asn_docs → asns/{asn}.json#downstreams_v4 |
| `downstreams` | list[int] | Vizinhos à direita nos AS-PATHs dos Route Servers (v6 e v4 unidos; adjacência, não relação comercial). | — | asn_docs → asns/{asn}.json#downstreams |
| `is_multihomed_v6` | bool | Mais de um vizinho a montante distinto na tabela global, no IPv6 (adjacência no AS_PATH; não distingue provedor de par). | — | asn_docs → asns/{asn}.json#is_multihomed_v6 |
| `single_upstream_v6` | int\|null | O único vizinho a montante observado no IPv6 (quando exatamente um); não prova dependência de um provedor. | — | asn_docs → asns/{asn}.json#single_upstream_v6 |
| `geo_prefixes_v6` | dict | Geolocalização (DB-IP) dos prefixos IPv6 do AS. | — | asn_docs → asns/{asn}.json#geo_prefixes_v6 |
| `geo_prefixes_v4` | dict | Geolocalização (DB-IP) dos prefixos IPv4 do AS: {prefixo: {lat, lon, city, uf, …}}. | — | asn_docs → asns/{asn}.json#geo_prefixes_v4 |
| `announced_ipv6_48s` | int | Espaço IPv6 anunciado, em equivalentes a /48. | — | asn_docs → asns/{asn}.json#announced_ipv6_48s |
| `users_per_v6_48` | float | Usuários estimados (APNIC) por /48 anunciado. | — | asn_docs → asns/{asn}.json#users_per_v6_48 |
| `geo_org` | dict | Cadastro e geolocalização da organização (cnpj_geo): endereço, CNAE, situação, porte, coordenadas. | — | asn_docs → asns/{asn}.json#geo_org |
| `pdb` | dict | Metadados autodeclarados da rede no PeeringDB (política, tipo, tráfego, IRR). | — | asn_docs → asns/{asn}.json#pdb |
| `apnic_users` | int\|null | Usuários de Internet estimados atrás do AS (APNIC Labs, janela de 60 dias). | — | asn_docs → asns/{asn}.json#apnic_users |
| `apnic_users_pct_cc` | float\|null | % da população estimada do país que o AS representa. | — | asn_docs → asns/{asn}.json#apnic_users_pct_cc |
| `apnic_v6_users` | int\|null | Usuários IPv6 estimados. | — | asn_docs → asns/{asn}.json#apnic_v6_users |
| `apnic_v6_pct_as` | float\|null | % dos usuários do AS que usam IPv6. | — | asn_docs → asns/{asn}.json#apnic_v6_pct_as |
| `asn` | int | ASN. | — | asn_docs → asns/index.json#asn |
| `name` | str | Nome do AS. | — | asn_docs → asns/index.json#name |
| `is_br` | bool | ASN delegado ao Brasil. | — | asn_docs → asns/index.json#is_br |
| `has_ipv6` | bool | Há IPv6 alocado, anunciado ou visto em IXP. | — | asn_docs → asns/index.json#has_ipv6 |
| `rir_prefixes_v4_count` | int | Prefixos IPv4 alocados. | — | asn_docs → asns/index.json#rir_prefixes_v4_count |
| `rir_prefixes_v6_count` | int | Prefixos IPv6 alocados. | — | asn_docs → asns/index.json#rir_prefixes_v6_count |
| `global_prefixes_v4_count` | int | Prefixos IPv4 anunciados. | — | asn_docs → asns/index.json#global_prefixes_v4_count |
| `global_prefixes_v6_count` | int | Prefixos IPv6 anunciados. | — | asn_docs → asns/index.json#global_prefixes_v6_count |
| `ixps_direct_count` | int | IXPs em que o AS é direto. | — | asn_docs → asns/index.json#ixps_direct_count |
| `ixps_origin_count` | int | IXPs em que o AS é originador. | — | asn_docs → asns/index.json#ixps_origin_count |
| `ixps_origin_v4_count` | int | IXPs em que o AS origina rotas IPv4. | — | asn_docs → asns/index.json#ixps_origin_v4_count |
| `ixps_origin_v6_count` | int | IXPs em que o AS origina rotas IPv6. | — | asn_docs → asns/index.json#ixps_origin_v6_count |
| `apnic_users` | int\|null | Usuários estimados (APNIC). | — | asn_docs → asns/index.json#apnic_users |
| `apnic_v6_users` | int\|null | Usuários IPv6 estimados (APNIC). | — | asn_docs → asns/index.json#apnic_v6_users |
| `pct_v6` | float\|null | % de usuários IPv6 do AS (APNIC). | — | asn_docs → asns/index.json#pct_v6 |
| `external_ixps_count` | int | IXPs externos em que declara presença (PeeringDB). | — | asn_docs → asns/index.json#external_ixps_count |
| `pdb_registered` | bool | Há cadastro no PeeringDB. | — | asn_docs → asns/index.json#pdb_registered |
| `has_aspa` | bool | Há objeto ASPA publicado pelo AS. | — | asn_docs → asns/index.json#has_aspa |
| `space_v6` | int | Espaço IPv6 anunciado (em /48 equivalentes) no índice. | — | asn_docs → asns/index.json#space_v6 |
| `*` | str | Mapa ASN (chave string) → nome do AS; só ASNs do snapshot. | — | asn_docs → asns/names.json#* |

### [asn_saude](produtos/asn_saude.md) — Saúde do ASN: RPKI e alertas

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `roa_list` | list[dict] | VRPs que cobrem os prefixos do AS. | — | asn_saude → asns/{asn}.json#roa_list |
| `rpki_validation[prefix]` | str | Estado RPKI do prefixo anunciado: valid, invalid ou not_found. | Calculado no pipeline (etapa saude_asn) contra os VRPs do snapshot. | asn_saude → asns/{asn}.json#rpki_validation |
| `alerts[].id / category / severity / title / detail / refs` | dict | Achados de saúde do AS (presença, roteamento, RPKI, redundância). | Regras de api/asn_health; achado negativo é observação, não prova. | asn_saude → asns/{asn}.json#alerts |
| `aspa_providers` | list[int] | Provedores autorizados pelo objeto ASPA do próprio AS (RPKI). | — | asn_saude → asns/{asn}.json#aspa_providers |
| `aspa_customers` | list[int] | ASNs que declaram este AS como provedor em seus objetos ASPA. | — | asn_saude → asns/{asn}.json#aspa_customers |

### [bgp_ixp_normalizado](produtos/bgp_ixp_normalizado.md) — Tabelas BGP normalizadas por IXP

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `peers-{afi}.json.gz` | dict | Por peer direto (primeiro AS do AS-PATH): prefixos próprios e de terceiros, ASNs originadores distintos e espaço em /48 (v6) ou /24 (v4). Calculado pela etapa bgp_ixp (core/ixp_peers.py) para a API não reler as rotas do PTT inteiro (1.4.2.1). | — | — |
| `routes[].prefix / status / aspath / origin / nexthop` | dict | Rota vista no Route Server: prefixo, status BGP, AS-PATH, origem e next-hop. | — | — |
| `relationships.asn_direct` | list[int] | ASNs com sessão BGP direta com o Route Server (primeiro AS do AS-PATH). | Definição de 'direto' do glossário do MCP. | — |
| `relationships.asn_origin` | list[int] | ASNs que aparecem como origem de rotas no IXP (inclui os alcançados por terceiros). | 'Originador' ≠ presente fisicamente. | — |
| `relationships.asn_stub` | list[int] | ASNs diretos que só originam o próprio espaço (sem trânsito). | Inferido do AS-PATH. | — |

### [bgp_stability](produtos/bgp_stability.md) — Estabilidade BGP (publicação)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `as_stability[].rank / severity / noise_category` | int / str | Posição no ranking de ruído, severidade e categoria de ruído do AS. | Faixas definidas em analysis/bgp_stability. | bgp_stability → bgp_stability.json#as_stability |
| `epppd_stats` | dict | Eventos por prefixo por dia: mediana, média e máximo. | — | bgp_stability → bgp_stability.json#epppd_stats |
| `period` | dict | Janela analisada, coletor e contagem de eventos. | — | bgp_stability → bgp_stability.json#period |
| `distribution` | dict | Distribuição de eventos por prefixo/dia (percentis e buckets) por família. | — | bgp_stability → bgp_stability.json#distribution |
| `hourly_global` | dict | Série horária global de anúncios, retiradas e mudanças de atributo. | — | bgp_stability → bgp_stability.json#hourly_global |
| `published_at` | str | Instante da publicação. | — | bgp_stability → bgp_stability.json#published_at |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | bgp_stability → bgp_stability_deep.json#generated_at |
| `date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | bgp_stability → bgp_stability_deep.json#date |
| `top_n` | int | Quantidade de ASes ruidosos analisados. | — | bgp_stability → bgp_stability_deep.json#top_n |
| `suspected_upstreams` | list[dict] | Upstreams suspeitos com eventos atribuídos e hora de pico (hipótese). | — | bgp_stability → bgp_stability_deep.json#suspected_upstreams |
| `as_diagnosis` | list[dict] | Diagnóstico por AS: veredito, sincronia entre prefixos e concentração em upstream (hipótese). | — | bgp_stability → bgp_stability_deep.json#as_diagnosis |
| `published_at` | str | Instante da publicação. | — | bgp_stability → bgp_stability_deep.json#published_at |

### [bloqueios](produtos/bloqueios.md) — Bloqueios e interferência medidos pelo OONI, por ASN (CC BY-NC-SA 4.0)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].testes[teste]` | dict | Medições (`n`), anomalias declaradas pela sonda (`anomalias`, `pct_anomalia`), componentes (`partes`) e, no Tor, fração de alvos acessíveis por tipo (`alvos_acessiveis_pct`). O `webconnectivity` traz `amostra=true`. | Veredito da própria sonda (ooni/spec), rotulado como tal; mínimo de 10 medições na janela; viés de voluntários e de sondas; CC BY-NC-SA 4.0. | bloqueios → bloqueios/asns.json.gz#asns |
| `janela / minimo_medicoes / testes / web_amostra` | dict | Primeiro e último dia agregados, mínimo por célula, resumo por teste (medições, ASNs publicados, abaixo do mínimo, critério) e o tamanho da amostra do webconnectivity. | Cobertura declarada para não confundir ausência de sonda com ausência de bloqueio. | bloqueios → bloqueios/asns.json.gz#janela; bloqueios → bloqueios/asns.json.gz#minimo_medicoes; bloqueios → bloqueios/asns.json.gz#testes; bloqueios → bloqueios/asns.json.gz#web_amostra |
| `fonte / licenca / aviso / limites / coletado_em` | dict | Fonte, licença CC BY-NC-SA 4.0 e atribuição, aviso de que o veredito é da sonda, limites e instante da coleta. | — | bloqueios → bloqueios/asns.json.gz#fonte; bloqueios → bloqueios/asns.json.gz#licenca; bloqueios → bloqueios/asns.json.gz#aviso; bloqueios → bloqueios/asns.json.gz#limites; bloqueios → bloqueios/asns.json.gz#coletado_em |
| `snapshot_date / generated_at` | str | Data do snapshot e instante UTC de geração. | — | bloqueios → bloqueios/asns.json.gz#snapshot_date; bloqueios → bloqueios/asns.json.gz#generated_at |

### [cadastro_empresas](produtos/cadastro_empresas.md) — Cadastro das empresas de telecom (Receita Federal) cruzado com o SICI

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `operadoras[raiz].matriz / estabelecimentos` | dict | Matriz (CNPJ, UF, município, situação, início da atividade, CNAE) e contagem de estabelecimentos (total, ativos, baixados, filiais ativas) da raiz de CNPJ. | Fato do cadastro da Receita na data do dump mensal; empresário individual sem razão social nem nome fantasia. | cadastro_empresas → empresas/operadoras/{NN}.json.gz#operadoras |
| `operadoras[raiz].presenca[] / resumo_presenca` | lista | Por município, estabelecimentos (total e ativos), se tem a matriz e os acessos fixo e móvel que a empresa declara no SICI; resumo de onde há os dois, só um ou só o outro. | Duas fontes que medem coisas diferentes (sede e filiais × assinantes); a diferença não prova que a empresa atende ou deixou de atender o município. | cadastro_empresas → empresas/operadoras/{NN}.json.gz#operadoras |
| `mercado.entradas_por_ano[] / baixas_por_ano[]` | lista | Empresas de telecom (matriz com CNAE 61 principal) abertas e baixadas por ano, no total e por UF. | Uma contagem por empresa (a matriz); não separa operadora de revenda ou de MEI. | cadastro_empresas → empresas/cadastro.json.gz#mercado |
| `mercado.ativas_por_uf / ativas_por_porte` | dict | Empresas de telecom ativas no dump, por UF e por porte (micro, pequeno, demais, MEI). | — | cadastro_empresas → empresas/cadastro.json.gz#mercado |
| `resumo / limites` | dict | Empresas no recorte, operadoras com e sem cadastro, estabelecimentos sem casamento com o IBGE e os limites do cruzamento. | — | cadastro_empresas → empresas/cadastro.json.gz#resumo |

### [cdns](produtos/cdns.md) — Presença de CDNs nos IXPs

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `cdns[].ixbr / external` | list[str] | IXPs do IX.br e externos em que algum ASN do CDN está presente. | — | cdns → cdns.json#cdns |
| `cdns[].ixbr_count / external_count` | int | Quantidade de IXPs de cada tipo. | — | cdns → cdns.json#cdns |
| `ixbr_columns / external_columns` | list[dict] | Colunas da matriz: IXP e quantos CDNs estão presentes. | — | cdns → cdns.json#ixbr_columns |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | cdns → cdns.json#snapshot_date |
| `external_columns` | list[dict] | Colunas da matriz para IXPs externos: código, nome e CDNs presentes. | — | cdns → cdns.json#external_columns |

### [cetic](produtos/cetic.md) — Pesquisas TIC do Cetic.br, tabelas oficiais

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `snapshot_date` | str | Data do snapshot em que o artefato foi gerado. | — | cetic → cetic/domicilios.json.gz#snapshot_date; cetic → cetic/provedores.json.gz#snapshot_date; cetic → cetic/domicilios_uf.json.gz#snapshot_date |
| `generated_at` | str | Instante UTC em que o artefato foi gerado. | — | cetic → cetic/domicilios.json.gz#generated_at; cetic → cetic/provedores.json.gz#generated_at; cetic → cetic/domicilios_uf.json.gz#generated_at |
| `coletado_em` | str | Instante UTC em que o Arandurapé baixou e leu as tabelas do Cetic.br. | — | cetic → cetic/domicilios.json.gz#coletado_em; cetic → cetic/provedores.json.gz#coletado_em; cetic → cetic/domicilios_uf.json.gz#coletado_em |
| `pesquisa` | str | Nome da pesquisa (TIC Domicílios ou TIC Provedores). | — | cetic → cetic/domicilios.json.gz#pesquisa; cetic → cetic/provedores.json.gz#pesquisa; cetic → cetic/domicilios_uf.json.gz#pesquisa |
| `edicao` | int | Ano da edição publicada pelo Cetic.br. | — | cetic → cetic/domicilios.json.gz#edicao; cetic → cetic/provedores.json.gz#edicao; cetic → cetic/domicilios_uf.json.gz#edicao |
| `fonte` | str | Citação da fonte: Cetic.br\|NIC.br, pesquisa e edição. | — | cetic → cetic/domicilios.json.gz#fonte; cetic → cetic/provedores.json.gz#fonte; cetic → cetic/domicilios_uf.json.gz#fonte |
| `licenca` | str | Licença dos dados (CC BY 4.0, citação obrigatória). | — | cetic → cetic/domicilios.json.gz#licenca; cetic → cetic/provedores.json.gz#licenca; cetic → cetic/domicilios_uf.json.gz#licenca |
| `pagina` | str | Página do Cetic.br de onde os arquivos foram descobertos. | — | cetic → cetic/domicilios.json.gz#pagina; cetic → cetic/provedores.json.gz#pagina; cetic → cetic/domicilios_uf.json.gz#pagina |
| `url` | str | Endereço do ZIP de tabelas usado. | — | cetic → cetic/domicilios.json.gz#url; cetic → cetic/provedores.json.gz#url; cetic → cetic/domicilios_uf.json.gz#url |
| `arquivo` | str | Nome do arquivo ZIP de origem. | — | cetic → cetic/domicilios.json.gz#arquivo; cetic → cetic/provedores.json.gz#arquivo; cetic → cetic/domicilios_uf.json.gz#arquivo |
| `sha256` | str | Hash do ZIP guardado no bruto. | — | cetic → cetic/domicilios.json.gz#sha256; cetic → cetic/provedores.json.gz#sha256; cetic → cetic/domicilios_uf.json.gz#sha256 |
| `total_tabelas` | int | Número de tabelas (abas) da edição. | — | cetic → cetic/domicilios.json.gz#total_tabelas; cetic → cetic/provedores.json.gz#total_tabelas; cetic → cetic/domicilios_uf.json.gz#total_tabelas |
| `total_linhas` | int | Número de linhas do formato longo. | — | cetic → cetic/domicilios.json.gz#total_linhas; cetic → cetic/provedores.json.gz#total_linhas; cetic → cetic/domicilios_uf.json.gz#total_linhas |
| `tabelas` | dict | Por aba: código, título, universo (a quem a pergunta se aplica) e notas. | — | cetic → cetic/domicilios.json.gz#tabelas; cetic → cetic/provedores.json.gz#tabelas; cetic → cetic/domicilios_uf.json.gz#tabelas |
| `linhas` | list | Formato longo: tabela, dimensao, recorte, item, resposta, proporcao, margem_proporcao, total e margem_total. Valor do Cetic.br sem alteração; vazio onde a planilha não traz. | — | cetic → cetic/domicilios.json.gz#linhas; cetic → cetic/provedores.json.gz#linhas; cetic → cetic/domicilios_uf.json.gz#linhas |
| `natureza` | str | Sempre 'estimativa_arandurape': o número não é do Cetic.br, é calculado pelo Arandurapé dos microdados. | — | cetic → cetic/domicilios_uf.json.gz#natureza |
| `domicilios_entrevistados` | int | Domicílios entrevistados na base de microdados. | — | cetic → cetic/domicilios_uf.json.gz#domicilios_entrevistados |
| `metodo` | dict | Réplicas usadas (200), regra da variância, margem de 95% (1,96 × erro-padrão), amostra mínima para não suprimir (30) e limite do CV para precisão baixa (30%). | — | cetic → cetic/domicilios_uf.json.gz#metodo |
| `indicadores` | dict | Por indicador (internet, computador, banda_larga_fixa): rótulo e definição pelas colunas da base. | — | cetic → cetic/domicilios_uf.json.gz#indicadores |
| `grupos` | dict | Brasil, 5 regiões e 27 UFs: domicílios entrevistados e estimados e, por indicador, proporção, erro-padrão, margem, CV, total e precisão; grupo com menos de 30 entrevistados traz 'suprimido'. | — | cetic → cetic/domicilios_uf.json.gz#grupos |
| `validacao` | dict | Comparação com as tabelas oficiais da mesma edição (A1 e A4, Brasil e regiões): maior diferença da proporção em pontos percentuais e faixa da razão margem oficial ÷ margem estimada; nulo se as tabelas não estão disponíveis. | — | cetic → cetic/domicilios_uf.json.gz#validacao |

### [consumidor](produtos/consumidor.md) — Reclamações no Consumidor.gov.br

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `marcas[]` | lista | Por empresa (nome fantasia no Consumidor.gov.br), a janela de 12 meses (finalizadas, respondidas, avaliadas, resolvidas, % respondidas, índice de solução, tempo médio em dias e nota média), a série mensal dos 24 meses e as raízes de CNPJ ligadas (vazio = sem CNPJ). | Índice, tempo e nota só com 30 ou mais casos (nulo = base insuficiente, não zero). A ligação é curada (apelido ou tabela de marcas) ou automática por nome fantasia único validada por UF, nunca um palpite. Reclamação não é prova de falha da empresa. | consumidor → consumidor/consumidor.json.gz#marcas |
| `setor_por_mes[] / janela / meses_disponiveis` | lista | Total do setor de telecomunicações por mês e a janela de 12 meses usada nos indicadores. | — | consumidor → consumidor/consumidor.json.gz#setor_por_mes; consumidor → consumidor/consumidor.json.gz#janela; consumidor → consumidor/consumidor.json.gz#meses_disponiveis |
| `uf[] / assuntos[] / grupos[]` | lista | Empresa × UF com os mesmos indicadores e empresa × assunto e × grupo de problema com a contagem na janela; só células com 5 ou mais reclamações. | Células pequenas não são publicadas (a linha original traz sexo e faixa etária de quem reclamou, que não são guardados). | consumidor → consumidor/consumidor.json.gz#uf; consumidor → consumidor/consumidor.json.gz#assuntos; consumidor → consumidor/consumidor.json.gz#grupos |
| `casamento / cidades / leitura` | dict | Cobertura da ligação empresa → CNPJ (% das reclamações da janela), cobertura do casamento da cidade ao código IBGE (% e as maiores cidades sem código) e a contagem da leitura da fonte. | — | consumidor → consumidor/consumidor.json.gz#casamento; consumidor → consumidor/consumidor.json.gz#cidades; consumidor → consumidor/consumidor.json.gz#leitura |
| `municipios[ibge]` | dict | Por município, o total da janela (com os indicadores) e, por empresa, as células com 5 ou mais reclamações, com a população estimada do IBGE. | A cidade é o nome digitado pelo consumidor, casado ao IBGE por nome e UF; nome repetido na UF não casa. | consumidor → consumidor/consumidor_municipios/{UF}.json.gz#municipios |
| `limites / minimos / natureza / fonte / url_fonte / snapshot_date / generated_at / municipios_uf` | str | O que o dado é e não é, os mínimos de base, fonte, endereço, data do snapshot, instante de geração e o índice código IBGE → UF. | — | consumidor → consumidor/consumidor.json.gz#limites; consumidor → consumidor/consumidor.json.gz#minimos; consumidor → consumidor/consumidor.json.gz#natureza; consumidor → consumidor/consumidor.json.gz#fonte; consumidor → consumidor/consumidor.json.gz#url_fonte; consumidor → consumidor/consumidor.json.gz#snapshot_date; consumidor → consumidor/consumidor.json.gz#generated_at; consumidor → consumidor/consumidor.json.gz#municipios_uf |
| `uf / janela / natureza / fonte / url_fonte / snapshot_date / generated_at` | str | Cabeçalho de cada parte por UF dos municípios. | — | consumidor → consumidor/consumidor_municipios/{UF}.json.gz#uf; consumidor → consumidor/consumidor_municipios/{UF}.json.gz#janela; consumidor → consumidor/consumidor_municipios/{UF}.json.gz#natureza; consumidor → consumidor/consumidor_municipios/{UF}.json.gz#fonte; consumidor → consumidor/consumidor_municipios/{UF}.json.gz#url_fonte; consumidor → consumidor/consumidor_municipios/{UF}.json.gz#snapshot_date; consumidor → consumidor/consumidor_municipios/{UF}.json.gz#generated_at |

### [contratos](produtos/contratos.md) — Contratos públicos de operadoras (PNCP, Lei 14.133)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `operadoras[raiz]` | dict | Leitura da raiz (`lida_em`, `idade_dias`, `faixa`, `cnpj_consultado`) e, havendo resultado, itens, itens cancelados, contratações, órgãos, valor homologado, primeiro e último resultado, séries por ano, UF e esfera, órgãos principais e as 20 contratações mais recentes. | Valor homologado sem os itens cancelados. `resultado = sem_resultado_na_consulta` quando a raiz foi lida e o PNCP não devolveu item (com a data), diferente de raiz sem leitura, que não aparece. Esfera, município e objeto só das contratações detalhadas. | contratos → contratos/operadoras.json.gz#operadoras |
| `municipios[ibge]` | dict | Município do ÓRGÃO COMPRADOR (detalhe da contratação ou unidade de compra da tabela UASG), com contratações, itens, valor e as 20 operadoras de maior valor registrado no município. | Não é o local de entrega do serviço nem prova de que a operadora atende o município. Ordem por valor registrado numa leitura incompleta (rodízio); não é ranking de mercado. | contratos → contratos/municipios.json.gz#municipios |
| `cobertura / por_ano / por_uf / por_esfera` | dict | Cobertura do rodízio (raízes no universo, lidas, com resultado, sem leitura, datas da leitura mais antiga e mais recente, contratações detalhadas e com município) e os totais nacionais por ano, UF e esfera. | Soma só do que foi lido; raiz sem leitura não entra como zero. Sem ranking de fornecedor. | contratos → contratos/resumo.json.gz#cobertura; contratos → contratos/resumo.json.gz#por_ano; contratos → contratos/resumo.json.gz#por_uf; contratos → contratos/resumo.json.gz#por_esfera |
| `fonte / licenca / aviso / limites / coletado_em / natureza` | dict | Fonte (Compras.gov.br, espelho do PNCP), licença (`nao_verificado`), avisos e limites, instante da coleta e a natureza do dado (fato publicado), repetidos nos três arquivos. | — | contratos → contratos/operadoras.json.gz#fonte; contratos → contratos/operadoras.json.gz#licenca; contratos → contratos/operadoras.json.gz#aviso; contratos → contratos/operadoras.json.gz#limites; contratos → contratos/operadoras.json.gz#coletado_em; contratos → contratos/operadoras.json.gz#natureza; contratos → contratos/municipios.json.gz#fonte; contratos → contratos/municipios.json.gz#licenca; contratos → contratos/municipios.json.gz#aviso; contratos → contratos/municipios.json.gz#limites; contratos → contratos/municipios.json.gz#coletado_em; contratos → contratos/municipios.json.gz#natureza; contratos → contratos/resumo.json.gz#fonte; contratos → contratos/resumo.json.gz#licenca; contratos → contratos/resumo.json.gz#aviso; contratos → contratos/resumo.json.gz#limites; contratos → contratos/resumo.json.gz#coletado_em; contratos → contratos/resumo.json.gz#natureza |
| `cobertura / criterio_municipio / valor_homologado` | dict | A cobertura do rodízio repetida em operadoras e municípios, o critério do município (do órgão comprador) e o valor homologado nacional (sem itens cancelados) do resumo. | — | contratos → contratos/operadoras.json.gz#cobertura; contratos → contratos/municipios.json.gz#cobertura; contratos → contratos/municipios.json.gz#criterio_municipio; contratos → contratos/resumo.json.gz#valor_homologado |
| `snapshot_date / generated_at` | str | Data do snapshot e instante da geração. | — | contratos → contratos/operadoras.json.gz#snapshot_date; contratos → contratos/operadoras.json.gz#generated_at; contratos → contratos/municipios.json.gz#snapshot_date; contratos → contratos/municipios.json.gz#generated_at; contratos → contratos/resumo.json.gz#snapshot_date; contratos → contratos/resumo.json.gz#generated_at |

### [decix_rs](produtos/decix_rs.md) — DE-CIX Rio e São Paulo nos route servers (estende os IXPs externos)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ixps[ixp].resumo` | dict | Route servers (total e consultados), sessões up e down, membros (ASNs com sessão), ASNs diretos e originadores (contagens, total e brasileiros). | `asn_direct` = sessão up no route server (não é o primeiro salto do AS_PATH do IX.br); `asn_origin` é um piso (leitura parcial por vizinho). | decix_rs → decix_rs/ixps.json.gz#ixps |
| `ixps[ixp].asn_direct / asn_origin / br_asns_direct / br_asns_origin` | list | ASNs com sessão up, ASNs de origem das rotas lidas e a parte brasileira de cada conjunto. | Sem leitura de rotas não há originador (não é zero); `rotas.parcial` e `rotas.cobertura` dizem quanto foi lido. | decix_rs → decix_rs/ixps.json.gz#ixps |
| `ixps[ixp].membros[]` | list | Por ASN, o nome do LG (organização), sessões up e down por família e rotas recebidas pelo route server. | Rótulo público do LG; nunca contatos. | decix_rs → decix_rs/ixps.json.gz#ixps |
| `ixps[ixp].peeringdb` | dict | Cadastrados no PeeringDB sem sessão up, sessão up sem cadastro e totais. | Cadastro e sessão medem coisas diferentes: cadastrado sem sessão pode ser peering bilateral; sessão sem cadastro, desatualização do PeeringDB. | decix_rs → decix_rs/ixps.json.gz#ixps |
| `ixps[ixp].comparacao_cidade` | dict | Para a cidade do PTT, ASNs diretos do IX.br e do DE-CIX, interseção, só em cada um, ASNs com sessão no DE-CIX e sem direto no IX.br, e o Equinix cadastrado (São Paulo). | Critérios diferentes entre as redes (sessão, primeiro salto, cadastro): compara conjuntos de ASNs, não tráfego nem qualidade. | decix_rs → decix_rs/ixps.json.gz#ixps |
| `bloqueio` | dict | Presente quando a coleta parou por sinal de bloqueio do servidor (403, 429 ou conexão derrubada). | — | decix_rs → decix_rs/ixps.json.gz#bloqueio |
| `snapshot_date / generated_at / coletado_em / rotas_coletadas_em / fonte / versao_alice / aviso` | str | Data do snapshot, instantes UTC de geração e das coletas, fonte, versão do Alice e o aviso sobre o que o dado é. | — | decix_rs → decix_rs/ixps.json.gz#snapshot_date; decix_rs → decix_rs/ixps.json.gz#generated_at; decix_rs → decix_rs/ixps.json.gz#coletado_em; decix_rs → decix_rs/ixps.json.gz#rotas_coletadas_em; decix_rs → decix_rs/ixps.json.gz#fonte; decix_rs → decix_rs/ixps.json.gz#versao_alice; decix_rs → decix_rs/ixps.json.gz#aviso |

### [demanda_oferta](produtos/demanda_oferta.md) — Demanda × oferta de banda larga fixa

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ufs[uf] / regioes[região] / brasil` | dict | Por grupo, domicílios projetados, proporção com banda larga fixa (TIC) e margem, demanda estimada, acessos de pessoa física (SICI), razão com limites, mercado não visto com limites e a classe. | ESTIMATIVA do Arandurapé. Denominador do IBGE tratado como fixo; a margem vem só da amostra da TIC e é menor que a oficial. Grupo suprimido ou de precisão baixa é indeterminado. | demanda_oferta → mercado/demanda_oferta.json.gz#ufs; demanda_oferta → mercado/demanda_oferta.json.gz#regioes; demanda_oferta → mercado/demanda_oferta.json.gz#brasil |
| `tic_edicao / mes_referencia_sici / pnad_ano` | int / str / str | Período de referência de cada fonte (a pesquisa, o SICI e a projeção de domicílios não são do mesmo mês). | — | demanda_oferta → mercado/demanda_oferta.json.gz#tic_edicao; demanda_oferta → mercado/demanda_oferta.json.gz#mes_referencia_sici; demanda_oferta → mercado/demanda_oferta.json.gz#pnad_ano |
| `limites / formulas / intervalo / natureza / fonte` | str / dict | Texto das limitações, as fórmulas, o nível do intervalo e o rótulo de natureza do número. | — | demanda_oferta → mercado/demanda_oferta.json.gz#limites; demanda_oferta → mercado/demanda_oferta.json.gz#formulas; demanda_oferta → mercado/demanda_oferta.json.gz#intervalo; demanda_oferta → mercado/demanda_oferta.json.gz#natureza; demanda_oferta → mercado/demanda_oferta.json.gz#fonte |

### [erbs](produtos/erbs.md) — Estações do SMP licenciadas por município, UF e operadora

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `municipios[ibge]` | dict | Estações licenciadas no município, quantas têm cada geração (2G a 5G), estações por operadora e por 10 mil habitantes. | Cadastro de licenciamento, não cobertura. Município sem estação não aparece (e pode ser atendido por vizinhos). | erbs → erbs/resumo.json.gz#municipios |
| `ufs[uf]` | dict | Estações, municípios, municípios com estação e com 5G, gerações e operadoras da UF. | — | erbs → erbs/resumo.json.gz#ufs |
| `operadoras[]` | lista | Por operadora (CNPJ quando conhecido, senão a marca), estações, municípios, UFs, gerações e tipo do 5G (SA, NSA, SA-NSA). | O CNPJ vem do arquivo da Anatel ou, quando em branco, da razão social nas outorgas do SMP; o que não casa fica só com a marca. | erbs → erbs/resumo.json.gz#operadoras |
| `brasil / casamento` | dict | Totais do país e medidas de casamento (estações com município no IBGE, sem CNPJ, sanidade contra o SICI móvel). | — | erbs → erbs/resumo.json.gz#brasil; erbs → erbs/resumo.json.gz#casamento |
| `limites / natureza / fonte / data_arquivo` | str | O que o dado é e não é, o rótulo de natureza, a fonte e a data de modificação do arquivo na Anatel. | — | erbs → erbs/resumo.json.gz#limites; erbs → erbs/resumo.json.gz#natureza; erbs → erbs/resumo.json.gz#fonte; erbs → erbs/resumo.json.gz#data_arquivo |
| `grade.celulas[]` | lista | Células de ~2 km (0,02 grau) com o centro (lon, lat), o número de estações licenciadas e quantas têm 2G, 3G, 4G e 5G. Alimenta a camada "Antenas" do mapa. | Agregado (não são pontos de estação); estação sem posição válida fica de fora. | erbs → erbs/grade.json.gz#celulas |
| `grade.colunas / passo_graus / natureza / limites` | lista / float / str | Nome das colunas de cada célula, tamanho da célula em graus, rótulo de natureza e limites do dado. | — | erbs → erbs/grade.json.gz#colunas; erbs → erbs/grade.json.gz#passo_graus; erbs → erbs/grade.json.gz#natureza; erbs → erbs/grade.json.gz#limites |

### [exposicao](produtos/exposicao.md) — Exposição de serviços por ASN e UF (contagens do Shodan, atribuição obrigatória)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn]` | dict | `lido_em`, `servicos_observados`, `portas_mais_vistas`, `risco` (serviços de risco, % dos observados e totais por classe com as portas) e `vulnerabilidades` (CVEs mais vistas, ou "não disponível no plano"). | Só ASNs lidos pelo rodízio; sem leitura = ausente (não zero). `sem_servico_observado` = o Shodan não viu serviço. Banners, não hosts únicos. | exposicao → exposicao/asns.json.gz#asns |
| `por_uf` | dict | Por UF, ASNs do cadastro, com leitura e com serviços, serviços observados, serviços de risco (total, % e por classe e serviço). | DERIVADO dos ASNs pelo mapeamento ASN → UF do projeto, só com os ASNs lidos (a cobertura vai junto); sem CVEs. | exposicao → exposicao/asns.json.gz#por_uf |
| `cobertura / plano / classes` | dict | ASNs do Brasil no snapshot, com leitura e com serviços, datas da leitura mais antiga e mais recente; facetas do plano; classes de risco e portas (definição do projeto). | Declarados para não confundir ausência de leitura com ausência de exposição. | exposicao → exposicao/asns.json.gz#cobertura; exposicao → exposicao/asns.json.gz#plano; exposicao → exposicao/asns.json.gz#classes |
| `fonte / licenca / aviso / limites / coletado_em` | dict | Fonte, atribuição ao Shodan, avisos, limites e instante da coleta. | — | exposicao → exposicao/asns.json.gz#fonte; exposicao → exposicao/asns.json.gz#licenca; exposicao → exposicao/asns.json.gz#aviso; exposicao → exposicao/asns.json.gz#limites; exposicao → exposicao/asns.json.gz#coletado_em |
| `snapshot_date / generated_at` | str | Data do snapshot e instante da geração. | — | exposicao → exposicao/asns.json.gz#snapshot_date; exposicao → exposicao/asns.json.gz#generated_at |

### [financiamento_sancoes](produtos/financiamento_sancoes.md) — Crédito público (BNDES) e sanções (CEIS e CNEP) por operadora

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `operadoras[raiz].financiamento` | dict | Operações do BNDES da raiz de CNPJ, com total contratado e desembolsado (R$ nominais), primeira e última data, série por ano, por UF e as 50 operações mais recentes. | Só operações diretas e não automáticas; valores nominais da data da contratação, sem correção. | financiamento_sancoes → financiamento/operadoras.json.gz#operadoras |
| `operadoras[raiz].sancoes` | dict | Sanções do CEIS e do CNEP da raiz de CNPJ, separadas em vigentes (inclui as sem prazo e as que começam depois da data) e encerradas na data do snapshot. | Registro do órgão sancionador, sem adjetivo; a vigência é calculada pela data do snapshot; sanção sem prazo vem da data 2099-12-31 da fonte. | financiamento_sancoes → financiamento/operadoras.json.gz#operadoras |
| `resumo / limites / fontes` | dict | Operadoras com financiamento e com sanção, operações e valor contratado totais, datas de referência de cada fonte e os limites. | — | financiamento_sancoes → financiamento/operadoras.json.gz#resumo |

### [grupos_societarios](produtos/grupos_societarios.md) — Grupos societários publicados

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `total_grupos / total_cnpjs_em_grupo` | int | Quantidade de grupos e de CNPJs que pertencem a algum grupo. | — | grupos_societarios → grupos_societarios.json.gz#total_grupos |
| `by_cnpj[cnpj].tamanho_grupo` | int | Número de CNPJs no grupo do CNPJ. | — | grupos_societarios → grupos_societarios.json.gz#by_cnpj |
| `by_cnpj[cnpj].endereco_sede` | dict | Endereço da sede do CNPJ (pessoa jurídica). | Endereço de PJ exposto (decisão 2026-10-11). | grupos_societarios → grupos_societarios.json.gz#by_cnpj |
| `receita_dump_reference` | str | Mês de referência do dump da Receita usado. | — | grupos_societarios → grupos_societarios.json.gz#receita_dump_reference |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | grupos_societarios → grupos_societarios.json.gz#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | grupos_societarios → grupos_societarios.json.gz#generated_at |
| `receita_socios_generated_at` | str | Instante em que a coleta de sócios usada foi gerada. | — | grupos_societarios → grupos_societarios.json.gz#receita_socios_generated_at |
| `total_cnpjs_em_grupo` | int | CNPJs que pertencem a algum grupo. | — | grupos_societarios → grupos_societarios.json.gz#total_cnpjs_em_grupo |

### [history](produtos/history.md) — Histórico por snapshot

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asn / is_br` | int / bool | Número do AS e se é brasileiro no snapshot. | — | — |
| `users / v6users` | int | Usuários estimados pela APNIC no snapshot (total e IPv6). Estimativa, não contagem; a média móvel de 4 semanas fica nas séries agregadas. | Ausente quando o AS não tem estimativa. | — |
| `p4 / p6` | int | Prefixos IPv6 e IPv4 do AS na tabela global do snapshot. | — | — |
| `n_ixd / n_ixm` | int | PTTs onde o AS tem sessão com o route server observada (ixps_direct) e onde é membro cadastrado (ixp_member_codes). | — | — |
| `n_provedores` | int | Provedores de nível confirmado ou superior (declarado, confirmado) segundo o ARC v1. Inferência rotulada. | Ausente nos snapshots anteriores ao bloco de relações; nunca zero inventado. | — |
| `n_roa / n_aspa / rpki_valid / rpki_invalid / rpki_not_found` | int | ROAs do AS, objetos ASPA publicados por ele e prefixos por estado de validação RPKI (etapa de saúde). | Ausentes quando o documento não traz o campo-fonte nem passou pela etapa de saúde (hoje, os ASNs estrangeiros); ausência de cobertura nunca vira zero. | — |
| `tem_roa_list / tem_rpki_validation / tem_aspa_providers / tem_saude` | bool | Presença do campo-fonte no documento publicado (roa_list, rpki_validation, aspa_providers) e se o documento passou pela etapa de saúde (tem alerts), que grava esses campos sempre que há algo a dizer. Um campo está coberto quando está presente ou tem_saude é verdadeiro. | Linha gravada antes dos marcadores (regra 1) é refeita do documento publicado antes de servir de comparação; sem documento, fica sem cobertura. | — |
| `n_alertas / hash_alertas` | int / str | Quantidade de alertas do AS (só ASN BR) e hash dos ids, para detectar alerta novo ou resolvido sem guardar os conjuntos. | Só se compara entre snapshots de mesmo rules_version. | — |
| `hash_relacoes / hash_ixd / hash_ixm / hash_pfx` | str | Hash curto (sha1, 12 hex) do conjunto de provedores confirmado+, PTTs diretos, PTTs membros e prefixos globais. Mudou o hash, o gerador de eventos lê os dois documentos publicados e calcula a diferença. | — | — |
| `ixp.jsonl.gz (ixp, status, n_direct, n_br_direct, n_origin, n_br_origin, n_membros, v4_rotas, v4_prefixos, v6_rotas, v6_prefixos)` | dict | Uma linha por PTT e snapshot, do índice de PTTs publicado. status é o da coleta (ok, partial, missing, failed); eventos negativos só valem para PTT coletado. | — | — |
| `operadora.jsonl.gz / uf.jsonl.gz` | dict | Soma dos ASNs BR por CNPJ (com grupo_id, só o id) e por UF da sede da organização (não a UF dos usuários), com users_ma4, a média das amostras de usuários APNIC dos últimos 28 dias, e n_ma4, o número de amostras. | A estimativa APNIC é suavizada pela média móvel; só entram datas anteriores ou iguais à do snapshot. | — |
| `events/{date}.jsonl.gz (id, data, tipo, entidade, chave, de, para, janela, estado, confirmado, confirmado_em, revertido_em, destaque, detalhe)` | dict | Diferença observada entre este snapshot e o anterior com histórico. estado é pendente até o novo estado persistir por `janela` snapshots (contando o de origem), depois confirmado; revertido se um snapshot seguinte o desmente. Tipos e janelas (snapshots) — asn_novo/asn_sumido 2; ixp_entrada/ixp_saida (cadastral) 1; ixp_entrada_observada/ixp_saida_observada 2; provedor_novo/provedor_perdido 3; mudanca_origem 2; roa_ganho/roa_perdido 1; aspa_ganho/aspa_perdido 1; rpki_invalido_novo/rpki_invalido_resolvido 2; outorga_nova 1, outorga_baixa 2; alerta_novo/alerta_resolvido 2. | Regra versionada (eventos_regra no índice; 2 desde 2026-11-24). roa_*, aspa_* e rpki_invalido_* só se geram, confirmam ou desmentem com o campo-fonte coberto nos dois snapshots (na regra 1 a ausência contava como zero, e em 2026-07-05 o fim da cobertura de roa_list dos ASNs estrangeiros virou 50.127 roa_perdido). Snapshot de coleta parcial não gera evento negativo e não confirma nem desmente evento. Evento observado de PTT só se o PTT foi coletado por inteiro nos dois snapshots. Alertas só se comparam com o mesmo rules_version. mudanca_origem exige origem única (sem MOAS) e uma ponta brasileira; destaque quando o novo estado é RPKI inválido. provedor_* é inferência (ARC). O evento descreve a diferença, sem causa nem intenção, e leva só a chave (ASN, PTT, CNPJ, prefixo), nunca nome de empresa. | — |
| `index.json` | dict | Snapshots com histórico, estado da coleta (coleta, coleta_ok), PTTs coletados e falhos, rules_version, linhas, sha256 do conteúdo, eventos_regra (versão da regra de eventos), eventos_regenerados_em (quando a camada foi refeita por `python -m products.history.regenerar_eventos`) e built_at. | — | — |

### [instalacoes](produtos/instalacoes.md) — Instalações do PeeringDB, vínculos, atributos das redes e portas externas

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `instalacoes[id]` | dict | Instalação com organização, localização, datas, PTTs (com o código do Arandurapé quando conhecido), carriers, campus, número de redes coletadas e o indicador `cadastro`. | Autodeclarado. `cadastro` (recente até 12 meses, parado de 1 a 3 anos, antigo acima de 3 anos desde a última atualização do registro ou dos vínculos) é INFERÊNCIA; mede a manutenção do cadastro, não a operação da instalação nem da empresa. | instalacoes → instalacoes/instalacoes.json.gz#instalacoes |
| `carriers[id] / campus[id]` | dict | Carriers e campus referenciados pelas instalações. | — | instalacoes → instalacoes/instalacoes.json.gz#carriers; instalacoes → instalacoes/instalacoes.json.gz#campus |
| `cobertura / limiares_cadastro_dias` | dict | Instalações do Brasil, com coordenadas, PTT, carrier e campus; PTTs do IX.br e externos com instalação cadastrada; ASNs do Brasil com instalação; distribuição do indicador de cadastro e seus limiares. | Medidas de cobertura da fonte, não de qualidade. | instalacoes → instalacoes/instalacoes.json.gz#cobertura; instalacoes → instalacoes/instalacoes.json.gz#limiares_cadastro_dias |
| `por_instalacao / por_asn / redes` | dict | Redes por instalação e instalações por ASN (vínculo netfac com as datas de criação e atualização), e o nome e a marca de Brasil de cada rede citada. | Declaração no cadastro; não indica tráfego nem contrato. | instalacoes → instalacoes/vinculos.json.gz#por_instalacao; instalacoes → instalacoes/vinculos.json.gz#por_asn; instalacoes → instalacoes/vinculos.json.gz#redes |
| `asns[asn]` | dict | Atributos de peering declarados pela rede no PeeringDB (escopo, IPv6, multicast, unicast, nunca via route server, looking glass, route server, contagens) e o `cadastro` inferido das datas. | Autodeclarado; URLs não verificadas. | instalacoes → instalacoes/atributos_rede.json.gz#asns |
| `ixps[code] / por_asn` | dict | Por PTT externo, portas, membros, soma, mediana, maior velocidade e histograma por velocidade (Mbps); por ASN do Brasil, as velocidades das portas em cada PTT externo. | Velocidade declarada; a soma é capacidade contratada declarada, não tráfego. | instalacoes → instalacoes/portas_externas.json.gz#ixps; instalacoes → instalacoes/portas_externas.json.gz#por_asn |
| `fonte / limites / coletado_em` | dict | Fonte (PeeringDB, com citação e AUP), limitações e instante da coleta. | — | instalacoes → instalacoes/instalacoes.json.gz#fonte; instalacoes → instalacoes/instalacoes.json.gz#limites; instalacoes → instalacoes/instalacoes.json.gz#coletado_em; instalacoes → instalacoes/vinculos.json.gz#fonte; instalacoes → instalacoes/vinculos.json.gz#limites; instalacoes → instalacoes/vinculos.json.gz#coletado_em; instalacoes → instalacoes/atributos_rede.json.gz#fonte; instalacoes → instalacoes/atributos_rede.json.gz#limites; instalacoes → instalacoes/atributos_rede.json.gz#coletado_em; instalacoes → instalacoes/portas_externas.json.gz#fonte; instalacoes → instalacoes/portas_externas.json.gz#limites; instalacoes → instalacoes/portas_externas.json.gz#coletado_em |
| `snapshot_date / generated_at` | str | Data do snapshot e instante UTC de geração. | — | instalacoes → instalacoes/instalacoes.json.gz#snapshot_date; instalacoes → instalacoes/instalacoes.json.gz#generated_at; instalacoes → instalacoes/vinculos.json.gz#snapshot_date; instalacoes → instalacoes/vinculos.json.gz#generated_at; instalacoes → instalacoes/atributos_rede.json.gz#snapshot_date; instalacoes → instalacoes/atributos_rede.json.gz#generated_at; instalacoes → instalacoes/portas_externas.json.gz#snapshot_date; instalacoes → instalacoes/portas_externas.json.gz#generated_at |

### [ipv4](produtos/ipv4.md) — Mercado de IPv4 (transferências, recuperação e blocos do Brasil)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `transferencias.operacoes[]` | lista | Operação com data, origem e destino (nome, país, RIR, pessoa), blocos, endereços, classe de tamanho, direção (br_br, br_exterior, exterior_br), fontes (registrobr, lacnic), primeira vez visto, defasagem e o ASN atual do destino. | Nome de pessoa física provável é omitido (Pessoa física). Operação é o mesmo dia e as mesmas partes; `anterior_a_coleta` marca o que já estava na primeira lista coletada (a data real de entrada na lista é anterior). | ipv4 → ipv4/transferencias.json.gz#operacoes |
| `mercado.por_ano / por_tamanho / concentracao / maior_operacao / defasagem / casamento` | dict | Operações, blocos e endereços por ano e direção; por classe de tamanho; as 10 maiores partes; a maior operação; a defasagem mediana de publicação; o percentual de destinos casados com ASN. | — | ipv4 → ipv4/mercado.json.gz#por_ano; ipv4 → ipv4/mercado.json.gz#por_tamanho; ipv4 → ipv4/mercado.json.gz#concentracao; ipv4 → ipv4/mercado.json.gz#maior_operacao; ipv4 → ipv4/mercado.json.gz#defasagem; ipv4 → ipv4/mercado.json.gz#casamento |
| `mercado.operacoes / blocos / enderecos / periodo` | int / list | Totais do mercado e o período coberto. | — | ipv4 → ipv4/mercado.json.gz#operacoes; ipv4 → ipv4/mercado.json.gz#blocos; ipv4 → ipv4/mercado.json.gz#enderecos; ipv4 → ipv4/mercado.json.gz#periodo |
| `recuperacao.em_recuperacao / recuperados / eventos_por_mes` | dict | Recursos em recuperação (com a janela e o status atual do bloco no delegated), recuperados por tipo e eventos de recuperação e liberação por mês. | — | ipv4 → ipv4/recuperacao.json.gz#em_recuperacao; ipv4 → ipv4/recuperacao.json.gz#recuperados; ipv4 → ipv4/recuperacao.json.gz#eventos_por_mes |
| `blocos_br.blocos[] / colunas / ultima_foto` | lista | Blocos IPv4 do Brasil na última foto do delegated: início, quantidade de endereços, status, data de registro, `opaque-id`, ASN e organização. | O `opaque-id` é público e não traz nome; a organização vem do casamento com o ASN do snapshot. | ipv4 → ipv4/blocos_br.json.gz#blocos; ipv4 → ipv4/blocos_br.json.gz#colunas; ipv4 → ipv4/blocos_br.json.gz#ultima_foto |
| `snapshot_date / generated_at / natureza / fonte / limites / total` | str | Metadados comuns dos artefatos, o rótulo de natureza (observado) e as limitações. | — | ipv4 → ipv4/transferencias.json.gz#limites; ipv4 → ipv4/transferencias.json.gz#natureza; ipv4 → ipv4/transferencias.json.gz#fonte; ipv4 → ipv4/transferencias.json.gz#total; ipv4 → ipv4/mercado.json.gz#limites; ipv4 → ipv4/mercado.json.gz#natureza; ipv4 → ipv4/mercado.json.gz#fonte; ipv4 → ipv4/recuperacao.json.gz#limites; ipv4 → ipv4/recuperacao.json.gz#natureza; ipv4 → ipv4/recuperacao.json.gz#fonte; ipv4 → ipv4/blocos_br.json.gz#limites; ipv4 → ipv4/blocos_br.json.gz#natureza; ipv4 → ipv4/blocos_br.json.gz#fonte |

### [ipv4_subasig](produtos/ipv4_subasig.md) — Sub-asignações de IPv4 (aluguel regulado)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ativa / aguardando / aviso / politica` | bool / str / dict | Se a fonte oficial está ativa, a mensagem "aguardando a publicação oficial" e o estado da política LAC-2025-5. | — | ipv4_subasig → ipv4/subasignacoes.json.gz#ativa; ipv4_subasig → ipv4/subasignacoes.json.gz#aguardando; ipv4_subasig → ipv4/subasignacoes.json.gz#aviso; ipv4_subasig → ipv4/subasignacoes.json.gz#politica |
| `vigia` | dict | Data da última varredura dos diretórios do Registro.br e do LACNIC e os alertas dos últimos 30 dias (arquivo novo, mudança de formato). | — | ipv4_subasig → ipv4/subasignacoes.json.gz#vigia |
| `subasignacoes[] / eventos[] / ignoradas` | lista | Registros (bloco, receptor, início, fim, verificações feitas pelo OBINT com True, False ou null (não são decisão do Registro.br nem do LACNIC), `em_conformidade` (todas as verificações com True) e pendentes) e eventos subasignacao_inicio e subasignacao_fim vistos entre snapshots. | Vazio até a fonte oficial existir. Esquema hipotético. | ipv4_subasig → ipv4/subasignacoes.json.gz#subasignacoes; ipv4_subasig → ipv4/subasignacoes.json.gz#eventos; ipv4_subasig → ipv4/subasignacoes.json.gz#ignoradas |
| `indicador_terceiros` | dict | Blocos com sinal S1 ou S3 (anúncio de terceiro) cujo anunciante tem sub-asignação registrada e os demais; nulo sem fonte oficial. | Hipótese, não acusação. | ipv4_subasig → ipv4/subasignacoes.json.gz#indicador_terceiros |
| `snapshot_date / generated_at / natureza / validacoes / esquema_hipotetico` | str / dict / bool | Metadados, a lista de validações da política e a marca de que o esquema é hipotético. | — | ipv4_subasig → ipv4/subasignacoes.json.gz#natureza; ipv4_subasig → ipv4/subasignacoes.json.gz#validacoes; ipv4_subasig → ipv4/subasignacoes.json.gz#esquema_hipotetico |

### [ipv4_uso](produtos/ipv4_uso.md) — Espaço IPv4 sem uso e hipóteses de uso por terceiros

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ips_sem_uso.resumo / duracao` | dict | Blocos e endereços por classe e por UF, maiores titulares sem anúncio e as tabelas de origem anteriores consultadas para a duração. | INFERIDO da tabela de origens do snapshot. A duração só conta as tabelas de origem distintas que temos (a tabela é semanal). | ipv4_uso → ipv4/ips_sem_uso.json.gz#resumo; ipv4_uso → ipv4/ips_sem_uso.json.gz#duracao |
| `ips_sem_uso.blocos[] / colunas` | lista | Blocos não anunciados, parciais, com ROA sem anúncio ou em recuperação: início, endereços, classe, % anunciado, titular (ASN e organização), UF, tabelas de origem sem anúncio, desde quando e ano de registro. | — | ipv4_uso → ipv4/ips_sem_uso.json.gz#blocos; ipv4_uso → ipv4/ips_sem_uso.json.gz#colunas |
| `uso_por_terceiros.itens[]` | lista | Blocos com ao menos um sinal (S1 a S4), com titular, origens, ROAs, sinais com confiança e evidência e a confiança do bloco. | HIPÓTESE de uso por terceiros, com os falsos positivos de cada sinal; dois ou mais sinais sobem a confiança um nível. | ipv4_uso → ipv4/uso_por_terceiros.json.gz#itens |
| `uso_por_terceiros.sinais / por_sinal / por_confianca / rotulo / blocos_avaliados / total` | dict | Catálogo dos sinais S1 a S7 (o que é, falsos positivos, ou por que não foi avaliado) e as contagens. | — | ipv4_uso → ipv4/uso_por_terceiros.json.gz#sinais; ipv4_uso → ipv4/uso_por_terceiros.json.gz#por_sinal; ipv4_uso → ipv4/uso_por_terceiros.json.gz#por_confianca; ipv4_uso → ipv4/uso_por_terceiros.json.gz#rotulo; ipv4_uso → ipv4/uso_por_terceiros.json.gz#blocos_avaliados; ipv4_uso → ipv4/uso_por_terceiros.json.gz#total |
| `snapshot_date / generated_at / natureza / fonte / limites / ultima_foto` | str | Metadados, rótulo de natureza (inferido), fonte, limites e a data da última foto do delegated. | — | ipv4_uso → ipv4/ips_sem_uso.json.gz#natureza; ipv4_uso → ipv4/ips_sem_uso.json.gz#fonte; ipv4_uso → ipv4/ips_sem_uso.json.gz#limites; ipv4_uso → ipv4/ips_sem_uso.json.gz#ultima_foto; ipv4_uso → ipv4/uso_por_terceiros.json.gz#natureza; ipv4_uso → ipv4/uso_por_terceiros.json.gz#fonte; ipv4_uso → ipv4/uso_por_terceiros.json.gz#limites; ipv4_uso → ipv4/uso_por_terceiros.json.gz#ultima_foto |

### [ixp_docs](produtos/ixp_docs.md) — Documentos por IXP, agregado e IXPs externos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `v6/v4.asn_direct_count / asn_origin_count / asn_stub_count` | int | Contagem de ASNs diretos, originadores e stubs no IXP. | — | ixp_docs → ixps/{ixp}.json#v4 |
| `v6/v4.br_asns_direct_pct / br_asns_origin_pct` | float | % dos ASNs BR da tabela global que são diretos / originadores no IXP. | — | ixp_docs → ixps/{ixp}.json#v4 |
| `v6/v4.ixp_space` | int | Espaço de endereços anunciado no IXP (/48 em IPv6; endereços em IPv4). | União de prefixos, sem dupla contagem. | ixp_docs → ixps/{ixp}.json#v4 |
| `v6/v4.br_prefix_coverage_pct` | float | % do espaço declarado ao Registro.br coberto por prefixos vistos no IXP. | — | ixp_docs → ixps/{ixp}.json#v4 |
| `v6/v4.ixp_vs_fulltable_space_pct` | float | Espaço do IXP como % do espaço da tabela global. | — | ixp_docs → ixps/{ixp}.json#v4 |
| `ixbr_members_count` | int | Membros cadastrados no IX.br (inclui bilaterais). | — | ixp_docs → ixps/index.json#ixbr_members_count |
| `status` | str | ok, parcial ou ausente conforme a coleta da família no IXP. | — | ixp_docs → ixps/index.json#status |
| `asn_direct_union_count / asn_origin_union_count` | int | Tamanho da união (não a soma) de ASNs entre todos os IXPs. | — | ixp_docs → ixps/_aggregate.json#asn_direct_union_count |
| `members[] (external-ixps)` | list[dict] | Membros do IXP externo com asn, nome, velocidade e is_br. | — | ixp_docs → external-ixps/{ixp}.json#members |
| `br_member_count` | int | Membros brasileiros do IXP externo. | — | ixp_docs → external-ixps/{ixp}.json#br_member_count |
| `ixp` | str | Código do IXP. | — | ixp_docs → ixps/{ixp}.json#ixp |
| `name` | str | Cidade-sede do IXP. | — | ixp_docs → ixps/{ixp}.json#name |
| `uf` | str | UF do IXP. | — | ixp_docs → ixps/{ixp}.json#uf |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | ixp_docs → ixps/{ixp}.json#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | ixp_docs → ixps/{ixp}.json#generated_at |
| `v6` | dict | Métricas IPv6 do IXP (mesma estrutura de v4). | — | ixp_docs → ixps/{ixp}.json#v6 |
| `v4` | dict | Métricas IPv4 do IXP (rotas, prefixos, ASNs diretos/originadores/stubs, cobertura). | — | ixp_docs → ixps/{ixp}.json#v4 |
| `code` | str | Código do IXP externo (configuração). | — | ixp_docs → external-ixps/{ixp}.json#code |
| `name` | str | Nome do IXP externo. | — | ixp_docs → external-ixps/{ixp}.json#name |
| `city` | str | Cidade do IXP externo. | — | ixp_docs → external-ixps/{ixp}.json#city |
| `country` | str | País (ISO 3166-1 alfa-2). | — | ixp_docs → external-ixps/{ixp}.json#country |
| `member_count` | int | Quantidade de membros listados no PeeringDB. | — | ixp_docs → external-ixps/{ixp}.json#member_count |
| `last_updated` | str | Data de referência dos dados do IXP externo (igual à do snapshot). | — | ixp_docs → external-ixps/{ixp}.json#last_updated |
| `asn_direct_union_count` | int | ASNs diretos distintos (união v6+v4) no IXP. | — | ixp_docs → ixps/index.json#asn_direct_union_count |
| `asn_origin_union_count` | int | ASNs originadores distintos (união v6+v4). | — | ixp_docs → ixps/index.json#asn_origin_union_count |
| `br_asns_direct_union_count` | int | ASNs BR diretos distintos. | — | ixp_docs → ixps/index.json#br_asns_direct_union_count |
| `br_asns_origin_union_count` | int | ASNs BR originadores distintos. | — | ixp_docs → ixps/index.json#br_asns_origin_union_count |
| `uf` | str | UF do IXP. | — | ixp_docs → ixps/index.json#uf |
| `v6` | dict | Resumo IPv6 do IXP. | — | ixp_docs → ixps/index.json#v6 |
| `v4` | dict | Resumo IPv4 do IXP. | — | ixp_docs → ixps/index.json#v4 |
| `ixp` | str | Sempre '_aggregate'. | — | ixp_docs → ixps/_aggregate.json#ixp |
| `name` | str | Rótulo do agregado. | — | ixp_docs → ixps/_aggregate.json#name |
| `uf` | str | UF (vazia no agregado). | — | ixp_docs → ixps/_aggregate.json#uf |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | ixp_docs → ixps/_aggregate.json#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | ixp_docs → ixps/_aggregate.json#generated_at |
| `ixp_count` | int | Quantidade de IXPs na união. | — | ixp_docs → ixps/_aggregate.json#ixp_count |
| `asn_origin_union_count` | int | ASNs originadores distintos entre todos os IXPs. | — | ixp_docs → ixps/_aggregate.json#asn_origin_union_count |
| `br_asns_origin_union_count` | int | ASNs BR originadores distintos entre todos os IXPs. | — | ixp_docs → ixps/_aggregate.json#br_asns_origin_union_count |
| `v6` | dict | Métricas IPv6 da união de todos os IXPs. | — | ixp_docs → ixps/_aggregate.json#v6 |
| `v4` | dict | Métricas IPv4 da união de todos os IXPs. | — | ixp_docs → ixps/_aggregate.json#v4 |
| `ixps` | list[dict] | IXPs externos exibidos, com contagens. | — | ixp_docs → external-ixps/index.json#ixps |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | ixp_docs → external-ixps/index.json#snapshot_date |

### [manrs_agregado](produtos/manrs_agregado.md) — Participação no MANRS (agregado)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `brasil / por_faixa_porte / por_uf` | dict | ASNs e usuários do recorte, ASNs participantes, % dos ASNs e % dos usuários estimados do APNIC; `n_asns_com_dado` (ASNs participantes), `peso_top1` (parcela do maior ASN participante nos usuários dos participantes) e `avisos` (`poucos_casos` com menos de 5; `maior_integrante` com 30% ou mais). Nenhum recorte é suprimido (D6); só snapshots anteriores trazem células `suprimido`. | Comparação de prontidão (participantes × não participantes) só no total e por porte, com o n e os avisos de cada lado. | manrs_agregado → manrs/resumo.json.gz#brasil; manrs_agregado → manrs/resumo.json.gz#por_faixa_porte; manrs_agregado → manrs/resumo.json.gz#por_uf |
| `atribuicao / fonte / regras / limites / natureza` | dict | A frase de atribuição exigida pelos termos, a fonte com data da medição, as regras dos avisos e as limitações. | — | manrs_agregado → manrs/resumo.json.gz#atribuicao; manrs_agregado → manrs/resumo.json.gz#fonte; manrs_agregado → manrs/resumo.json.gz#regras; manrs_agregado → manrs/resumo.json.gz#limites; manrs_agregado → manrs/resumo.json.gz#natureza |
| `snapshot_date / generated_at` | str | Data do snapshot e instante em que o arquivo foi gerado. | — | manrs_agregado → manrs/resumo.json.gz#snapshot_date; manrs_agregado → manrs/resumo.json.gz#generated_at |

### [mapas_infraestrutura](produtos/mapas_infraestrutura.md) — Camadas de infraestrutura (cabos, transmissão, rodovias)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `type` | str | Tipo GeoJSON. | — | mapas_infraestrutura → maps/submarine_cables.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | mapas_infraestrutura → maps/submarine_cables.geojson#snapshot_date |
| `source` | str | Origem do dado exibida como atribuição. | — | mapas_infraestrutura → maps/submarine_cables.geojson#source |
| `features` | list | Geometrias da camada com as propriedades de cada elemento. | — | mapas_infraestrutura → maps/submarine_cables.geojson#features |
| `type` | str | Tipo GeoJSON. | — | mapas_infraestrutura → maps/submarine_landing_points.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | mapas_infraestrutura → maps/submarine_landing_points.geojson#snapshot_date |
| `source` | str | Origem do dado exibida como atribuição. | — | mapas_infraestrutura → maps/submarine_landing_points.geojson#source |
| `features` | list | Geometrias da camada com as propriedades de cada elemento. | — | mapas_infraestrutura → maps/submarine_landing_points.geojson#features |
| `type` | str | Tipo GeoJSON. | — | mapas_infraestrutura → maps/itu_transmission.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | mapas_infraestrutura → maps/itu_transmission.geojson#snapshot_date |
| `source` | str | Origem do dado exibida como atribuição. | — | mapas_infraestrutura → maps/itu_transmission.geojson#source |
| `features` | list | Geometrias da camada com as propriedades de cada elemento. | — | mapas_infraestrutura → maps/itu_transmission.geojson#features |
| `type` | str | Tipo GeoJSON. | — | mapas_infraestrutura → maps/power_transmission_lines.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | mapas_infraestrutura → maps/power_transmission_lines.geojson#snapshot_date |
| `source` | str | Origem do dado exibida como atribuição. | — | mapas_infraestrutura → maps/power_transmission_lines.geojson#source |
| `features` | list | Geometrias da camada com as propriedades de cada elemento. | — | mapas_infraestrutura → maps/power_transmission_lines.geojson#features |
| `type` | str | Tipo GeoJSON. | — | mapas_infraestrutura → maps/ibge_rodovias.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | mapas_infraestrutura → maps/ibge_rodovias.geojson#snapshot_date |
| `source` | str | Origem do dado exibida como atribuição. | — | mapas_infraestrutura → maps/ibge_rodovias.geojson#source |
| `features` | list | Geometrias da camada com as propriedades de cada elemento. | — | mapas_infraestrutura → maps/ibge_rodovias.geojson#features |
| `attribution` | str | Atribuição obrigatória à TeleGeography (CC BY-SA). | — | mapas_infraestrutura → maps/submarine_cables.geojson#attribution |
| `attribution` | str | Atribuição obrigatória à TeleGeography (CC BY-SA). | — | mapas_infraestrutura → maps/submarine_landing_points.geojson#attribution |

### [mapas_prefixos](produtos/mapas_prefixos.md) — Mapas de prefixos, ASNs e curvas de Hilbert

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `legacy` | dict | Bloco LEGACY do IPv6: camadas por célula /32 (rir_br, global_br, global_all, ixp_all, rir_br_visible; índices esparsos). | — | mapas_prefixos → hilbert_v6.json#legacy |
| `lacnic` | dict | Bloco LACNIC do IPv6: camadas por célula /32 (rir_br, global_br, global_all, ixp_all, rir_br_visible; índices esparsos). | — | mapas_prefixos → hilbert_v6.json#lacnic |
| `arin` | dict | Bloco ARIN do IPv6: camadas por célula /32 (rir_br, global_br, global_all, ixp_all, rir_br_visible; índices esparsos). | — | mapas_prefixos → hilbert_v6.json#arin |
| `ripe` | dict | Bloco RIPE do IPv6: camadas por célula /32 (rir_br, global_br, global_all, ixp_all, rir_br_visible; índices esparsos). | — | mapas_prefixos → hilbert_v6.json#ripe |
| `apnic` | dict | Bloco APNIC do IPv6: camadas por célula /32 (rir_br, global_br, global_all, ixp_all, rir_br_visible; índices esparsos). | — | mapas_prefixos → hilbert_v6.json#apnic |
| `afrinic` | dict | Bloco AFRINIC do IPv6: camadas por célula /32 (rir_br, global_br, global_all, ixp_all, rir_br_visible; índices esparsos). | — | mapas_prefixos → hilbert_v6.json#afrinic |
| `hilbert_v4.rir_br / global_br / global_all / ixp_all / rir_br_visible` | list[int] | Células de 65.536 posições da curva de Hilbert sobre o IPv4: ocupação alocada ao BR, anunciada, global, vista em IXP e BR visível. | Contagens por célula (/16 agregado). | mapas_prefixos → hilbert_v4.json |
| `rir_br` | list[int] | Por célula /16: espaço alocado ao BR pelo Registro.br. | — | mapas_prefixos → hilbert_v4.json#rir_br |
| `global_br` | list[int] | Por célula /16: espaço BR anunciado na tabela global. | — | mapas_prefixos → hilbert_v4.json#global_br |
| `global_all` | list[int] | Por célula /16: espaço anunciado na tabela global (todos os países). | — | mapas_prefixos → hilbert_v4.json#global_all |
| `ixp_all` | list[int] | Por célula /16: espaço visto nos IXPs. | — | mapas_prefixos → hilbert_v4.json#ixp_all |
| `rir_br_visible` | list[int] | Por célula /16: espaço alocado ao BR que é visível (anunciado) na tabela global. | — | mapas_prefixos → hilbert_v4.json#rir_br_visible |
| `type` | str | Tipo GeoJSON (FeatureCollection). | — | mapas_prefixos → maps/asns.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | mapas_prefixos → maps/asns.geojson#snapshot_date |
| `features` | list | Um ponto por ASN geolocalizado (properties: asn, name, cnpj, razao_social, uf, city, geo_confidence). | — | mapas_prefixos → maps/asns.geojson#features |
| `type` | str | Tipo GeoJSON. | — | mapas_prefixos → maps/prefixes.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | mapas_prefixos → maps/prefixes.geojson#snapshot_date |
| `features` | list | Um ponto por prefixo BR geolocalizado (properties: prefix, ip_version, origin_asn, city, uf, geo_confidence). | — | mapas_prefixos → maps/prefixes.geojson#features |
| `type` | str | Tipo GeoJSON. | — | mapas_prefixos → maps/global_prefixes.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | mapas_prefixos → maps/global_prefixes.geojson#snapshot_date |
| `features` | list | Um ponto por prefixo visto nos IXPs (properties: prefix, origin_asn, ixps_seen, city, uf, geo_confidence). | — | mapas_prefixos → maps/global_prefixes.geojson#features |

### [outorgas](produtos/outorgas.md) — Outorgas Anatel (SCM, SMP, STFC, SeAC) e mapas

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `scms[].asns` | list[int] | ASNs vinculados ao CNPJ pelo Registro.br. | — | outorgas → scm.json.gz#scms |
| `scms[].sici_ativo / sici_mes_referencia / sici_acessos / sici_pf / sici_pj` | bool\|str\|int | Resumo do SICI do CNPJ copiado para a outorga. | Sem soma por ASN; um CNPJ com vários ASNs não deve ser somado duas vezes. | outorgas → scm.json.gz#scms |
| `scms[].sici_municipios / sici_capacidade_mbps / sici_tecnologia / sici_empresa` | int\|float\|str | Municípios atendidos, capacidade contratada, tecnologia predominante e nome no SICI. | — | outorgas → scm.json.gz#scms |
| `matched_asns / cnpj_to_asns` | int / dict | Quantidade de CNPJs ligados a ASN e o mapa CNPJ→ASNs. | — | outorgas → scm.json.gz#cnpj_to_asns |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | outorgas → scm.json.gz#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | outorgas → scm.json.gz#generated_at |
| `total` | int | Quantidade de registros de outorga. | — | outorgas → scm.json.gz#total |
| `unique_cnpjs` | int | CNPJs distintos. | — | outorgas → scm.json.gz#unique_cnpjs |
| `matched_asns` | int | CNPJs com ASN vinculado. | — | outorgas → scm.json.gz#matched_asns |
| `scms` | list[dict] | Registros de outorga SCM (um por CNPJ/endereço). | — | outorgas → scm.json.gz#scms |
| `by_cnpj` | dict | Índice CNPJ → registros de outorga. | — | outorgas → scm.json.gz#by_cnpj |
| `cnpj_to_asns` | dict | CNPJ → ASNs do Registro.br. | — | outorgas → scm.json.gz#cnpj_to_asns |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | outorgas → seac.json.gz#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | outorgas → seac.json.gz#generated_at |
| `total` | int | Quantidade de registros de outorga. | — | outorgas → seac.json.gz#total |
| `unique_cnpjs` | int | CNPJs distintos. | — | outorgas → seac.json.gz#unique_cnpjs |
| `matched_asns` | int | CNPJs com ASN vinculado. | — | outorgas → seac.json.gz#matched_asns |
| `seacs` | list[dict] | Registros de outorga SeAC. | — | outorgas → seac.json.gz#seacs |
| `by_cnpj` | dict | Índice CNPJ → registros de outorga. | — | outorgas → seac.json.gz#by_cnpj |
| `cnpj_to_asns` | dict | CNPJ → ASNs do Registro.br. | — | outorgas → seac.json.gz#cnpj_to_asns |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | outorgas → smp.json.gz#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | outorgas → smp.json.gz#generated_at |
| `total` | int | Quantidade de registros de outorga. | — | outorgas → smp.json.gz#total |
| `unique_cnpjs` | int | CNPJs distintos. | — | outorgas → smp.json.gz#unique_cnpjs |
| `matched_asns` | int | CNPJs com ASN vinculado. | — | outorgas → smp.json.gz#matched_asns |
| `smps` | list[dict] | Registros de outorga SMP. | — | outorgas → smp.json.gz#smps |
| `by_cnpj` | dict | Índice CNPJ → registros de outorga. | — | outorgas → smp.json.gz#by_cnpj |
| `cnpj_to_asns` | dict | CNPJ → ASNs do Registro.br. | — | outorgas → smp.json.gz#cnpj_to_asns |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | outorgas → stfc.json.gz#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | outorgas → stfc.json.gz#generated_at |
| `total` | int | Quantidade de registros de outorga. | — | outorgas → stfc.json.gz#total |
| `unique_cnpjs` | int | CNPJs distintos. | — | outorgas → stfc.json.gz#unique_cnpjs |
| `matched_asns` | int | CNPJs com ASN vinculado. | — | outorgas → stfc.json.gz#matched_asns |
| `stfcs` | list[dict] | Registros de outorga STFC. | — | outorgas → stfc.json.gz#stfcs |
| `by_cnpj` | dict | Índice CNPJ → registros de outorga. | — | outorgas → stfc.json.gz#by_cnpj |
| `cnpj_to_asns` | dict | CNPJ → ASNs do Registro.br. | — | outorgas → stfc.json.gz#cnpj_to_asns |
| `type` | str | Tipo GeoJSON. | — | outorgas → maps/scms.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | outorgas → maps/scms.geojson#snapshot_date |
| `features` | list | Um ponto por CNPJ com outorga SCM geolocalizado (properties: cnpj, razao_social, municipio, uf, asns, has_asn, geo_confidence; SCM acrescenta sici_*). | — | outorgas → maps/scms.geojson#features |
| `type` | str | Tipo GeoJSON. | — | outorgas → maps/seacs.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | outorgas → maps/seacs.geojson#snapshot_date |
| `features` | list | Um ponto por CNPJ com outorga SeAC geolocalizado (properties: cnpj, razao_social, municipio, uf, asns, has_asn, geo_confidence; SCM acrescenta sici_*). | — | outorgas → maps/seacs.geojson#features |
| `type` | str | Tipo GeoJSON. | — | outorgas → maps/smps.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | outorgas → maps/smps.geojson#snapshot_date |
| `features` | list | Um ponto por CNPJ com outorga SMP geolocalizado (properties: cnpj, razao_social, municipio, uf, asns, has_asn, geo_confidence; SCM acrescenta sici_*). | — | outorgas → maps/smps.geojson#features |
| `type` | str | Tipo GeoJSON. | — | outorgas → maps/stfcs.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | outorgas → maps/stfcs.geojson#snapshot_date |
| `features` | list | Um ponto por CNPJ com outorga STFC geolocalizado (properties: cnpj, razao_social, municipio, uf, asns, has_asn, geo_confidence; SCM acrescenta sici_*). | — | outorgas → maps/stfcs.geojson#features |

### [penetracao](produtos/penetracao.md) — Penetração de banda larga fixa e mercado não visto

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `municipios[ibge].domicilios_projetados / fator_projecao_uf` | int / float | Domicílios do Censo 2022 × crescimento de domicílios da UF entre 2022 e o ano mais recente da PNAD. | PROJEÇÃO. Supõe o mesmo crescimento em todos os municípios da UF; sem a série da PNAD fica no nível do Censo e sem o fator. | penetracao → territorio/municipios.json.gz#municipios |
| `municipios[ibge].penetracao / penetracao_pf / penetracao_censo` | float | Acessos fixos declarados (e só os de pessoa física) por domicílio projetado; `penetracao_censo` usa os domicílios do Censo, sem projeção. | Acesso não é domicílio; pode passar de 1. Ausente quando o município não tem domicílios no IBGE. | penetracao → territorio/municipios.json.gz#municipios |
| `municipios[ibge].nao_visto / nao_visto_pct / domicilios_com_internet_est` | int / float | max(0, domicílios projetados × taxa de internet da UF − acessos de pessoa física); a taxa é a da PNAD ("havia utilização de internet"). | ESTIMATIVA. Inclui quem usa só o celular; a taxa é da UF aplicada ao município. Fórmula e limites no próprio artefato. | penetracao → territorio/municipios.json.gz#municipios |
| `ufs[uf] / brasil` | dict | Soma dos municípios e a taxa da PNAD com o coeficiente de variação da UF. | — | penetracao → territorio/municipios.json.gz#ufs |
| `casamento` | dict | Quantos municípios do SICI casaram com o IBGE e quais ficaram sem código no IBGE. | — | penetracao → territorio/municipios.json.gz#casamento |
| `limites / formulas` | str / dict | Texto das limitações e as fórmulas usadas. | — | penetracao → territorio/municipios.json.gz#limites |

### [prontidao](produtos/prontidao.md) — Prontidão em segurança de roteamento por ASN

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].total / classe / pilares_sem_dado` | float / str / lista | Índice (0 a 100) com os pilares que tinham dado, a classe (pronto ≥ 80, em progresso ≥ 50, atrasado, ou sem dados quando há menos de dois pilares) e os pilares que ficaram de fora. | Pesos de componentes e pilares se renormalizam pelo que existe; o índice sempre diz quais pilares entraram. | prontidao → prontidao/asns.json.gz#asns |
| `asns[asn].pilares[pilar].componentes` | dict | Valor (0 a 100), peso e detalhe de cada componente (ROV, bogons, Spoofer, PeeringDB, aut-num, as-set, ROA, IRR, ASPA). | Cada componente cita a fonte nas regras; o objeto IRR documenta política e pode ter sido criado por terceiro; ASPA só conta a favor. | — |
| `brasil / por_uf / por_faixa_porte / por_operadora` | dict | Por grupo (país, UF, porte por usuários estimados do APNIC, operadora), ASNs por classe, média ponderada pelos usuários estimados, mediana e cobertura de cada pilar. | Agregados, nenhum recorte suprimido (D6). Cada um traz `n_asns_com_dado`, `peso_top1` (parcela do ASN com mais usuários entre os que têm índice) e `avisos` (`poucos_casos` com menos de 5; `maior_integrante` com 30% ou mais); `medicoes[componente]` traz os mesmos três campos. `classes_com_rov` e `classes_sem_rov` separam as classes por haver ROV medido (a soma é `classes`). A lista por ASN é outra visão, pública e com ordem padrão por ASN (`prontidao_asn`). Operadora = raiz do CNPJ do ASN. | prontidao → prontidao/asns.json.gz#por_uf; prontidao → prontidao/asns.json.gz#por_faixa_porte; prontidao → prontidao/asns.json.gz#por_operadora; prontidao → prontidao/asns.json.gz#brasil |
| `regras / fontes / limites / natureza` | dict | Versão e hash das regras, pesos e descrição de cada pilar e componente, fonte e data de cada insumo, e as limitações. | — | prontidao → prontidao/asns.json.gz#regras; prontidao → prontidao/asns.json.gz#fontes; prontidao → prontidao/asns.json.gz#limites; prontidao → prontidao/asns.json.gz#natureza |
| `snapshot_date / generated_at` | str | Data do snapshot e instante em que o arquivo foi gerado. | — | prontidao → prontidao/asns.json.gz#snapshot_date; prontidao → prontidao/asns.json.gz#generated_at |

### [qualidade](produtos/qualidade.md) — Qualidade (RQUAL) e reclamações da Anatel

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `rqual.nacional[] / uf[]` | lista | Por serviço × prestadora × indicador, por mês (nacional) ou por ano (UF), municípios medidos, medidas, média simples, média ponderada pelas medidas e (nacional) mediana dos municípios. | Só resultados numéricos; não é o desempenho da empresa para um cliente. Sem ranking. | qualidade → qualidade/rqual.json.gz#nacional; qualidade → qualidade/rqual.json.gz#uf |
| `rqual.indicadores[] / prestadoras[] / casamento` | lista | Indicadores com unidade e valores de referência da Anatel; prestadoras cobertas com as raízes de CNPJ ligadas (casamento curada ou automático) e as que ficaram sem CNPJ. | Cobre só as grandes prestadoras; a ausência de uma empresa não diz nada sobre ela. | qualidade → qualidade/rqual.json.gz#indicadores; qualidade → qualidade/rqual.json.gz#prestadoras; qualidade → qualidade/rqual.json.gz#casamento |
| `rqual.municipios[ibge].itens[]` | lista | O último resultado de cada serviço × prestadora × indicador no município, com mês, medidas, coletores, erro amostral, intervalo e a coluna Estatística da fonte. | Resultado de poucas medidas é incerto; veja o erro amostral. | qualidade → qualidade/rqual_municipios/{UF}.json.gz#municipios |
| `rqual.limites / natureza / fonte / data_arquivo / leitura` | str | O que o dado é e não é, a data do arquivo na Anatel e a contagem da leitura. | — | qualidade → qualidade/rqual.json.gz#limites; qualidade → qualidade/rqual.json.gz#natureza; qualidade → qualidade/rqual.json.gz#fonte; qualidade → qualidade/rqual.json.gz#data_arquivo; qualidade → qualidade/rqual.json.gz#resumo |
| `reclamacoes.marcas[]` | lista | Reclamações por marca × serviço × ano, municípios distintos e as raízes de CNPJ ligadas à marca (vazio = sem CNPJ). | A ligação é curada (config/curada_marcas_operadoras.yaml) ou automática por nome fantasia único, nunca um palpite. Reclamação não é prova de falha da empresa. | qualidade → qualidade/reclamacoes.json.gz#marcas |
| `reclamacoes.taxas` | dict | Reclamações da janela de 12 meses por mil acessos do SICI (SCM e SMP), só com volume suficiente, e a regra e o mês de referência do SICI. | As duas bases têm períodos diferentes e a marca pode agrupar mais de um CNPJ; a regra e o motivo de cada taxa ausente acompanham o dado. | qualidade → qualidade/reclamacoes.json.gz#taxas |
| `reclamacoes.por_mes[] / uf[] / assuntos[] / marca_assuntos[] / casamento` | lista | Totais nacionais por mês, por UF e por assunto, assuntos por marca nos últimos 3 anos e a cobertura da ligação marca → CNPJ (% das reclamações com CNPJ). | — | qualidade → qualidade/reclamacoes.json.gz#por_mes; qualidade → qualidade/reclamacoes.json.gz#uf; qualidade → qualidade/reclamacoes.json.gz#assuntos; qualidade → qualidade/reclamacoes.json.gz#marca_assuntos; qualidade → qualidade/reclamacoes.json.gz#casamento |
| `reclamacoes.municipios[ibge].itens[]` | lista | Reclamações por ano × serviço × marca nos últimos 3 anos da fonte, com a população estimada do IBGE para a taxa por 100 mil habitantes. | — | qualidade → qualidade/reclamacoes_municipios/{UF}.json.gz#municipios |
| `reclamacoes.limites / natureza / fonte / data_arquivo / leitura` | str | O que o dado é e não é, a data do arquivo na Anatel e a contagem da leitura. | — | qualidade → qualidade/reclamacoes.json.gz#limites; qualidade → qualidade/reclamacoes.json.gz#natureza; qualidade → qualidade/reclamacoes.json.gz#fonte; qualidade → qualidade/reclamacoes.json.gz#data_arquivo; qualidade → qualidade/reclamacoes.json.gz#leitura |
| `snapshot_date / generated_at` | str | Data do snapshot e instante em que o arquivo foi gerado. | — | qualidade → qualidade/rqual.json.gz#snapshot_date; qualidade → qualidade/rqual.json.gz#generated_at; qualidade → qualidade/reclamacoes.json.gz#snapshot_date; qualidade → qualidade/reclamacoes.json.gz#generated_at |
| `municipios_uf` | dict | Índice código IBGE do município → UF, para a API achar a parte por UF dos municípios. | — | qualidade → qualidade/rqual.json.gz#municipios_uf; qualidade → qualidade/reclamacoes.json.gz#municipios_uf |
| `anos / url_fonte` | lista / str | Anos com reclamações na fonte e o endereço do arquivo da Anatel. | — | qualidade → qualidade/reclamacoes.json.gz#anos; qualidade → qualidade/reclamacoes.json.gz#url_fonte; qualidade → qualidade/rqual.json.gz#url_fonte |
| `uf / anos_municipio / fonte / natureza / data_arquivo / url_fonte / snapshot_date / generated_at` | str | Cabeçalho de cada parte por UF dos municípios (UF, anos cobertos, fonte, natureza do dado, data do arquivo na Anatel, endereço, data do snapshot e instante de geração). | — | qualidade → qualidade/rqual_municipios/{UF}.json.gz#uf; qualidade → qualidade/rqual_municipios/{UF}.json.gz#fonte; qualidade → qualidade/rqual_municipios/{UF}.json.gz#natureza; qualidade → qualidade/rqual_municipios/{UF}.json.gz#data_arquivo; qualidade → qualidade/rqual_municipios/{UF}.json.gz#url_fonte; qualidade → qualidade/rqual_municipios/{UF}.json.gz#snapshot_date; qualidade → qualidade/rqual_municipios/{UF}.json.gz#generated_at; qualidade → qualidade/reclamacoes_municipios/{UF}.json.gz#uf; qualidade → qualidade/reclamacoes_municipios/{UF}.json.gz#anos_municipio; qualidade → qualidade/reclamacoes_municipios/{UF}.json.gz#fonte; qualidade → qualidade/reclamacoes_municipios/{UF}.json.gz#natureza; qualidade → qualidade/reclamacoes_municipios/{UF}.json.gz#data_arquivo; qualidade → qualidade/reclamacoes_municipios/{UF}.json.gz#url_fonte; qualidade → qualidade/reclamacoes_municipios/{UF}.json.gz#snapshot_date; qualidade → qualidade/reclamacoes_municipios/{UF}.json.gz#generated_at |

### [radar](produtos/radar.md) — Cloudflare Radar por ASN e UF (CC BY-NC 4.0)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn]` | dict | `ipv6` (`pct` e `em`), `trafego_pct_do_brasil`, `velocidade` (download, upload, latências, jitter, testes) e `bgp` (vazou, no_caminho_de_vazamento, sequestrou, vitima_de_sequestro), só do que existe para o ASN. | Ausência não é zero. IPv6 mede quem usa a Cloudflare; velocidade e tráfego só dos ASNs de topo; eventos de BGP não provam intenção nem dano. | radar → radar/asns.json.gz#asns |
| `por_uf` | dict | Por UF, ASNs do cadastro, ASNs com IPv6, mediana de IPv6, IPv6 ponderado pelo tráfego (só ASNs com os dois números, com a contagem) e soma dos papéis de BGP. | DERIVADO dos ASNs pelo mapeamento ASN → UF do projeto; o Radar não tem recorte por UF. | radar → radar/asns.json.gz#por_uf |
| `cobertura / bgp / quedas` | dict | Cobertura (ASNs no snapshot, na lista do Radar, lidos, com dado, datas da leitura mais antiga e mais recente, ASNs de topo), resumo e critério dos eventos de BGP e a consulta de quedas do país. | Declarados para não confundir ausência de leitura com ausência de problema; "sem quedas" é o que a consulta devolveu na data. | radar → radar/asns.json.gz#cobertura; radar → radar/asns.json.gz#bgp; radar → radar/asns.json.gz#quedas |
| `fonte / licenca / aviso / limites / coletado_em / janela_ipv6` | dict | Fonte, licença CC BY-NC 4.0 e atribuição, avisos, limites, instante da coleta e janela do IPv6. | — | radar → radar/asns.json.gz#fonte; radar → radar/asns.json.gz#licenca; radar → radar/asns.json.gz#aviso; radar → radar/asns.json.gz#limites; radar → radar/asns.json.gz#coletado_em; radar → radar/asns.json.gz#janela_ipv6 |
| `snapshot_date / generated_at` | str | Data do snapshot e instante da geração. | — | radar → radar/asns.json.gz#snapshot_date; radar → radar/asns.json.gz#generated_at |

### [rede_territorio](produtos/rede_territorio.md) — Rede no território (IPv6, ROV e trânsito)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ipv6.municipios[ibge] / ufs / brasil` | dict | Acessos fixos declarados, acessos com estimativa, acessos em IPv6 estimados, percentual e a cobertura (parcela dos acessos que entrou). | ESTIMATIVA. Supõe que a adoção de IPv6 do AS (APNIC, ponderada pelos usuários) vale igual em todos os municípios da operadora; operadora sem ASN ou sem medida fica de fora. | rede_territorio → territorio/rede_territorio.json.gz#ipv6 |
| `rov.ufs[uf] / brasil` | dict | Usuários estimados, os com medida de ROV e os atrás de ASNs que validam ROV, por UF da sede do ASN. | ESTIMATIVA. Fração de testes da APNIC em que o AS valida ROV (mínimo de 100 amostras) × usuários estimados; a UF é a da sede do ASN. Nenhuma UF é suprimida (D6) e cada uma traz `n_asns_com_dado` (ASNs com medida), `peso_top1` (parcela do maior ASN nos usuários com medida) e `avisos` (`poucos_casos` com menos de 5; `maior_integrante` com 30% ou mais). | rede_territorio → territorio/rede_territorio.json.gz#rov |
| `transito.municipios[ibge] / ufs` | dict | Parcela dos acessos (das operadoras com relação inferida) cujos ASNs têm um único provedor de trânsito, e o provedor do qual mais acessos dependem. | INFERIDO (relações p2c do ARC em nível provável ou superior); operadora sem relação inferida fica de fora, e um provedor só pode ser falta de observação. | rede_territorio → territorio/rede_territorio.json.gz#transito |
| `snapshot_date / generated_at / natureza / limites / fontes` | str / dict | Cabeçalho do produto: snapshot, natureza (estimado), limites e a suposição, e o período de cada fonte. | — | rede_territorio → territorio/rede_territorio.json.gz#snapshot_date; rede_territorio → territorio/rede_territorio.json.gz#generated_at; rede_territorio → territorio/rede_territorio.json.gz#natureza; rede_territorio → territorio/rede_territorio.json.gz#limites; rede_territorio → territorio/rede_territorio.json.gz#fontes |

### [regiao_municipios](produtos/regiao_municipios.md) — ASNs por município e fatos de rede

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `municipios` | dict | Por código IBGE, os ASNs com vínculo SICI (acessos fixo e móvel), sede ou prefixos geolocalizados (só a contagem). | — | regiao_municipios → territorio/regiao.json.gz#municipios |
| `asns` | dict | Por ASN, nome, PTTs diretos (d) e de origem (o), carregadores observados (c) e provedores de trânsito com probabilidade e nível (p). | — | regiao_municipios → territorio/regiao.json.gz#asns |
| `natureza / limites / fontes / snapshot_date / generated_at` | str | Rótulo de inferência, limites, fontes e data. | — | regiao_municipios → territorio/regiao.json.gz#natureza; regiao_municipios → territorio/regiao.json.gz#limites; regiao_municipios → territorio/regiao.json.gz#fontes; regiao_municipios → territorio/regiao.json.gz#snapshot_date; regiao_municipios → territorio/regiao.json.gz#generated_at |

### [regulatorio](produtos/regulatorio.md) — Regulatório complementar

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `fust.municipios[ibge]` | dict | Compromissos do FUST no município (total, atendidos, a vencer, em apuração), investimento previsto, compromissos por programa e por tipo, por 10 mil habitantes. | Cadastro da Anatel; investimento é o previsto, não o desembolsado. Município sem compromisso não aparece. | regulatorio → regulatorio/fust.json.gz#municipios |
| `fust.ufs[uf] / brasil` | dict | Totais da UF e do país (compromissos, situação, investimento, municípios com compromisso). | — | regulatorio → regulatorio/fust.json.gz#ufs; regulatorio → regulatorio/fust.json.gz#brasil |
| `fust.programas[] / editais[]` | lista | Totais por programa (código e nome) e por edital ou projeto de origem. | — | regulatorio → regulatorio/fust.json.gz#programas; regulatorio → regulatorio/fust.json.gz#editais |
| `fust.casamento / limites / natureza / fonte / data_arquivo` | dict | Compromissos com município no IBGE (e por malha 2010 ou 2022), sem investimento, o que o dado é e não é e a data do arquivo na Anatel. | — | regulatorio → regulatorio/fust.json.gz#casamento; regulatorio → regulatorio/fust.json.gz#limites; regulatorio → regulatorio/fust.json.gz#natureza; regulatorio → regulatorio/fust.json.gz#fonte; regulatorio → regulatorio/fust.json.gz#data_arquivo |
| `multas.empresas[]` | lista | Por empresa (raiz do CNPJ) e grupo de serviço (SCM, SMP, STFC, SeAC), multas constituídas, valor original, pago e saldo devedor atualizado, situações, anos e CNPJ da matriz. | Só pessoa jurídica. Multa constituída não é condenação definitiva (pode estar em recurso, parcelada ou suspensa). | regulatorio → regulatorio/multas.json.gz#empresas |
| `multas.brasil / por_grupo / por_ano` | dict | Totais do país, por grupo de serviço e multas por ano de aplicação e grupo. | — | regulatorio → regulatorio/multas.json.gz#brasil; regulatorio → regulatorio/multas.json.gz#por_grupo; regulatorio → regulatorio/multas.json.gz#por_ano |
| `multas.limites / natureza / fonte / data_arquivo / leitura` | str | O que o dado é e não é, o que ficou de fora (pessoa física, outros serviços) e a data do arquivo na Anatel. | — | regulatorio → regulatorio/multas.json.gz#limites; regulatorio → regulatorio/multas.json.gz#natureza; regulatorio → regulatorio/multas.json.gz#fonte; regulatorio → regulatorio/multas.json.gz#data_arquivo; regulatorio → regulatorio/multas.json.gz#leitura |
| `faixas.faixas[] / referencias[]` | lista | Faixas de frequência em MHz com os serviços destinados e atribuídos no Brasil (caráter primário ou secundário) e as faixas de interesse para a Internet (700 MHz, 3,5 GHz, Wi-Fi 6 GHz...). | É o quadro normativo, não licença. Os nomes das faixas de interesse são referência do Arandurapé. | regulatorio → regulatorio/faixas.json.gz#faixas; regulatorio → regulatorio/faixas.json.gz#referencias |
| `faixas.resumo / limites / natureza / fonte / data_arquivo` | dict | Faixas lidas, com destinação e com atribuição; o que o dado é e não é; a data do arquivo na Anatel. | — | regulatorio → regulatorio/faixas.json.gz#resumo; regulatorio → regulatorio/faixas.json.gz#limites; regulatorio → regulatorio/faixas.json.gz#natureza; regulatorio → regulatorio/faixas.json.gz#fonte; regulatorio → regulatorio/faixas.json.gz#data_arquivo |
| `satelites.direitos[] / ngeo[] / operando[]` | lista | Direitos de exploração de satélite (operadora, satélite, posição, banda, tipo, status, validade), constelações NGEO e satélites em operação comercial. | Direito concedido não é capacidade em uso. Muitas operadoras são estrangeiras e não cruzam com o SICI. | regulatorio → regulatorio/satelites.json.gz#direitos; regulatorio → regulatorio/satelites.json.gz#ngeo; regulatorio → regulatorio/satelites.json.gz#operando |
| `satelites.resumo / limites / natureza / fonte / data_arquivo` | dict | Totais por tipo, status e órbita; direitos vencidos na data do snapshot; o que o dado é e não é; a data do arquivo na Anatel. | — | regulatorio → regulatorio/satelites.json.gz#resumo; regulatorio → regulatorio/satelites.json.gz#limites; regulatorio → regulatorio/satelites.json.gz#natureza; regulatorio → regulatorio/satelites.json.gz#fonte; regulatorio → regulatorio/satelites.json.gz#data_arquivo |
| `snapshot_date / generated_at` | str | Data do snapshot e instante em que o arquivo foi gerado. | — | regulatorio → regulatorio/fust.json.gz#snapshot_date; regulatorio → regulatorio/fust.json.gz#generated_at; regulatorio → regulatorio/multas.json.gz#snapshot_date; regulatorio → regulatorio/multas.json.gz#generated_at; regulatorio → regulatorio/faixas.json.gz#snapshot_date; regulatorio → regulatorio/faixas.json.gz#generated_at; regulatorio → regulatorio/satelites.json.gz#snapshot_date; regulatorio → regulatorio/satelites.json.gz#generated_at |

### [route_servers](produtos/route_servers.md) — Route servers do IX.br, sessões × cadastro

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ixps[ixp].resumo` | dict | Route servers (total, consultados, com cache de rotas pronto e com vizinhos atuais), membros cadastrados com e sem sessão, sessões sem cadastro, sessões up e down, membros down e perto do limite. | Medição no route server na data da coleta; "cadastrado sem sessão" pode ser membro com peering bilateral. | route_servers → route_servers/ixps.json.gz#ixps |
| `ixps[ixp].membros[]` | list | Por ASN do PTT (cadastrado ou com sessão), contagem de sessões up e down, maior tempo de queda e maior uso do limite de importação. | membro down = todas as sessões down há 7 dias ou mais e nenhuma sem frescor confirmado (rs_incerto: cache de vizinhos do Alice com mais de 24 h, sem cached_at ou consulta que falhou); perto do limite = rotas recebidas em 80% ou mais do import_limit. | route_servers → route_servers/ixps.json.gz#ixps |
| `asns[asn].ixps[ixp].lista` | list | Cada sessão do ASN no PTT (route server, família, estado, dias no estado, último erro, rotas e limite). | Dado do route server; o motivo da queda é o que o Alice reporta, sem causa atribuída. | route_servers → route_servers/asns.json.gz#asns |
| `snapshot_date` | str | Data do snapshot em que o artefato foi gerado. | — | route_servers → route_servers/ixps.json.gz#snapshot_date; route_servers → route_servers/asns.json.gz#snapshot_date |
| `generated_at` | str | Instante UTC em que o artefato foi gerado. | — | route_servers → route_servers/ixps.json.gz#generated_at; route_servers → route_servers/asns.json.gz#generated_at |
| `coletado_em` | str | Instante UTC da coleta no Alice-LG: a data do dado (o snapshot só o guarda). | — | route_servers → route_servers/ixps.json.gz#coletado_em; route_servers → route_servers/asns.json.gz#coletado_em |
| `fonte` | str | Fonte das sessões (Alice-LG do IX.br). | — | route_servers → route_servers/ixps.json.gz#fonte; route_servers → route_servers/asns.json.gz#fonte |
| `versao_alice` | str | Versão do Alice-LG que respondeu. | — | route_servers → route_servers/ixps.json.gz#versao_alice; route_servers → route_servers/asns.json.gz#versao_alice |
| `dias_down` | str | Dias de queda a partir dos quais um membro com todas as sessões down conta como membro down (7). | — | route_servers → route_servers/ixps.json.gz#dias_down; route_servers → route_servers/asns.json.gz#dias_down |
| `uso_limite` | str | Fração do limite de importação (rotas recebidas ÷ import_limit) a partir da qual a sessão está perto do limite (0,8). | — | route_servers → route_servers/ixps.json.gz#uso_limite; route_servers → route_servers/asns.json.gz#uso_limite |
| `idade_max_vizinhos_h` | int | Idade máxima, em horas, do cache de vizinhos do Alice (cached_at) para as sessões de um route server valerem como estado atual (24). | — | route_servers → route_servers/ixps.json.gz#idade_max_vizinhos_h; route_servers → route_servers/asns.json.gz#idade_max_vizinhos_h |

### [routing_analysis](produtos/routing_analysis.md) — Análise de roteamento BGP do Brasil

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `pbr_composition.{v6,v4}.strict_br / origin_only_br / prefix_only_br` | dict | Rotas e ASNs em que prefixo e origem são BR (estrito), só a origem é BR ou só o prefixo é BR. | Definição de PBR do projeto. | routing_analysis → routing_analysis.json#pbr_composition |
| `aggregation_by_asn[].savings_origin / savings_path / savings_path_pct` | int / float | Rotas economizáveis se agregadas por origem ou por caminho. | Estimativa teórica; agregação real depende de política. | routing_analysis → routing_analysis.json#aggregation_by_asn |
| `moas[].prefix / afi / origins / br_origins / origens[].asn / origens[].coletores / origens[].coletores_nomes / origens[].asn_br` | list[dict] | Prefixos brasileiros (contidos em bloco do Registro.br) com mais de um AS de origem observado nos coletores da tabela global, com cada origem, se o ASN está na lista do Registro.br e quantos (e quais) coletores a viram. IPv6 antes de IPv4. | Fato observado (de `origins-multi-{afi}`), sem rótulo de causa. Até `moas_resumo.lista_limite` entradas (`lista_truncada`). Nulo, com o motivo em `moas_indisponivel`, quando a coleta do snapshot guardou uma origem por prefixo. | routing_analysis → routing_analysis.json#moas |
| `moas_resumo.prefixos.{v6,v4}.global / br; moas_resumo.coletores.{v6,v4}` | dict | Prefixos com 2+ origens por família, na tabela inteira e só os brasileiros, e os coletores que entraram; família sem `origins-multi` fica nula. Traz também `definicao`, `como_ler` (causas só como hipótese) e `limites`. | Zero com o resumo presente é nenhum MOAS observado entre esses coletores; resumo nulo é não medido. | routing_analysis → routing_analysis.json#moas_resumo |
| `too_specific` | list | Prefixos mais específicos que o limite prático (/48 IPv6, /24 IPv4). | — | routing_analysis → routing_analysis.json#too_specific |
| `registro_br_coverage[].coverage_pct / has_exact_aggregate` | float / bool | Cobertura do bloco alocado por rotas e se o agregado exato é anunciado. | — | routing_analysis → routing_analysis.json#registro_br_coverage |
| `has_path_data` | bool | Se os dados de AS-PATH estavam disponíveis para as análises de caminho. | — | routing_analysis → routing_analysis.json#has_path_data |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | routing_analysis → routing_analysis.json#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | routing_analysis → routing_analysis.json#generated_at |
| `br_asns_visible` | int | ASNs BR vistos na tabela global. | — | routing_analysis → routing_analysis.json#br_asns_visible |
| `br_asns_registered` | int | ASNs BR registrados. | — | routing_analysis → routing_analysis.json#br_asns_registered |
| `summary` | dict | Totais por família (rotas, prefixos, ASNs globais; rotas e ASNs PBR). | — | routing_analysis → routing_analysis.json#summary |
| `prefix_length_dist` | dict | Distribuição de rotas e espaço por comprimento de prefixo (v6, v4). | — | routing_analysis → routing_analysis.json#prefix_length_dist |
| `more_specifics` | dict | Contagem de raízes e mais-específicos (mesma origem × origem diferente) e profundidade. | — | routing_analysis → routing_analysis.json#more_specifics |
| `top_asns_more_specifics` | list[dict] | ASNs BR com mais rotas mais-específicas. | — | routing_analysis → routing_analysis.json#top_asns_more_specifics |
| `global_comparison` | dict | Percentuais de /48 (v6) ou /24 (v4) e de mais-específicos, global × PBR, por família. | — | routing_analysis → routing_analysis.json#global_comparison |
| `as_path_stats` | dict | Estatísticas de AS-PATH por família: comprimento (média, mediana, p95), rotas com prepend, AS privado, loops e AS_TRANS; só com dados de caminho. | — | routing_analysis → routing_analysis.json#as_path_stats |
| `rpki.{v6,v4}.valid / invalid / not_found / espaco` | dict | Rotas brasileiras (P_BR) por estado RPKI de origem (RFC 6811), com a união do espaço de cada estado (/48 ou /24) e os ASNs de origem com rota inválida. | Validação contra os VRPs do snapshot; um bloco pode ter rotas em mais de um estado, então os espaços não somam o total. | routing_analysis → routing_analysis_resumo.json#rpki |
| `saude.{v6,v4}.mais_especificos / filtraveis; saude.moas` | dict | Totais de saúde da tabela para o Panorama técnico (mais-específicos, prefixos filtráveis, MOAS), copiados da análise completa. `saude.moas.{v6,v4}` = {prefixos, prefixos_br, coletores}; nulo, com o motivo em `saude.moas_indisponivel`, quando não medido. | — | routing_analysis → routing_analysis_resumo.json#saude |

### [rs_policy](produtos/rs_policy.md) — Rejeições, communities e política de roteamento nos route servers do IX.br

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

### [seguranca_asn](produtos/seguranca_asn.md) — Segurança de roteamento por ASN, parte A

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].rov / dnssec` | dict | Percentual medido pelo APNIC (validates_pct; DNSSEC também parcial_pct) e o tamanho da amostra. | Medição por amostragem, não declaração da rede; alto = valida; ASN com poucas amostras fica fora dos agregados. | seguranca_asn → seguranca/asns.json.gz#asns |
| `asns[asn].asrank` | dict | Rank, grau e cone de clientes segundo o CAIDA AS Rank. | Inferência do CAIDA; rotulada como estimada. | seguranca_asn → seguranca/asns.json.gz#asns |
| `asns[asn].prefixos_em_bogon / n_prefixos_bogon / asn_reservado` | list / int / str | Prefixos originados pelo ASN dentro de espaço reservado (IANA) ou não alocado (Team Cymru, na data da lista) e ASN em faixa reservada. | Fato verificável contra as listas citadas; bloco recém-alocado pode aparecer como não alocado por horas. | seguranca_asn → seguranca/asns.json.gz#asns |
| `por_uf / por_faixa_porte / brasil` | dict | Contagem de ASNs, mediana e média ponderada de ROV e DNSSEC e distribuição em faixas neutras (até 10, 10 a 90, acima de 90), por UF e por porte (usuários estimados do APNIC; a faixa de acessos declarados ao SICI do CNPJ fica em `faixa_acessos_sici` de cada ASN). | Só ASNs com pelo menos 100 amostras; não é ranking de empresas. Nenhum recorte é suprimido (D6) com `rov` e `dnssec` trazem `n_asns_com_dado`, `peso_top1` (parcela do ASN com mais amostras) e `avisos` (`poucos_casos` com menos de 5; `maior_integrante` com 30% ou mais). | seguranca_asn → seguranca/asns.json.gz#por_uf |
| `fontes / parametros / limites` | dict | Fonte, data e janela de cada sinal, parâmetros do cálculo e as limitações. | — | seguranca_asn → seguranca/asns.json.gz#fontes |

### [sici](produtos/sici.md) — Acessos SICI publicados (fixo e móvel)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `cnpj_to_asns / asn_to_cnpj` | dict | Vínculos CNPJ↔ASN usados para ligar SICI a ASN. | Vêm do Registro.br; vários ASNs por CNPJ ⇒ acessos_compartilhados. | sici → sici.json.gz#cnpj_to_asns |
| `cnpjs[cnpj].acessos_compartilhados / asns` | bool / list[int] | Verdadeiro quando o CNPJ tem mais de um ASN: não somar acessos por ASN. | — | sici → sici.json.gz#cnpjs |
| `divergencia[asn].classificacao / razao` | str / float | Razão acessos SICI × usuários APNIC e classe (normal, acima, abaixo, nao_comparavel). | Hipótese de comparação entre duas estimativas diferentes; rotular. | sici → sici.json.gz#divergencia |
| `municipios[ibge].operadores / hhi / share_maior` | list / int / float | Operadoras do município, índice HHI de concentração e parcela da maior. | HHI sobre acessos declarados, não sobre receita. | sici → sici_municipios.json.gz#municipios |
| `municipios[ibge].acessos / pf / pj / capacidade_mbps` | int / float | Acessos fixos declarados no município. | — | sici → sici_municipios.json.gz#municipios |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | sici → sici.json.gz#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | sici → sici.json.gz#generated_at |
| `fonte` | str | URL do arquivo da Anatel de origem. | — | sici → sici.json.gz#fonte |
| `meses_disponiveis` | list[str] | Meses de declaração disponíveis (SICI fixo). | — | sici → sici.json.gz#meses_disponiveis |
| `total_acessos` | int | Total nacional de acessos no último mês. | — | sici → sici.json.gz#total_acessos |
| `total_cnpjs` | int | CNPJs com acessos no último mês. | — | sici → sici.json.gz#total_cnpjs |
| `matched_cnpjs` | int | CNPJs do SICI com ASN vinculado. | — | sici → sici.json.gz#matched_cnpjs |
| `matched_acessos` | int | Acessos desses CNPJs. | — | sici → sici.json.gz#matched_acessos |
| `serie_por_cnpj` | dict | Série mensal de acessos por CNPJ: lista de [mês, acessos, pf, pj]. | — | sici → sici.json.gz#serie_por_cnpj |
| `serie_total` | list[dict] | Série mensal nacional (mês, acessos, CNPJs). | — | sici → sici.json.gz#serie_total |
| `cnpj_to_asns` | dict | CNPJ → ASNs. | — | sici → sici.json.gz#cnpj_to_asns |
| `asn_to_cnpj` | dict | ASN → CNPJ. | — | sici → sici.json.gz#asn_to_cnpj |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | sici → sici_movel.json.gz#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | sici → sici_movel.json.gz#generated_at |
| `fonte` | str | URL do arquivo da Anatel de origem. | — | sici → sici_movel.json.gz#fonte |
| `meses_disponiveis` | list[str] | Meses de declaração disponíveis (SICI móvel). | — | sici → sici_movel.json.gz#meses_disponiveis |
| `total_acessos` | int | Total nacional de acessos no último mês. | — | sici → sici_movel.json.gz#total_acessos |
| `total_cnpjs` | int | CNPJs com acessos no último mês. | — | sici → sici_movel.json.gz#total_cnpjs |
| `matched_cnpjs` | int | CNPJs do SICI com ASN vinculado. | — | sici → sici_movel.json.gz#matched_cnpjs |
| `matched_acessos` | int | Acessos desses CNPJs. | — | sici → sici_movel.json.gz#matched_acessos |
| `serie_por_cnpj` | dict | Série mensal de acessos por CNPJ: lista de [mês, acessos, pf, pj]. | — | sici → sici_movel.json.gz#serie_por_cnpj |
| `serie_total` | list[dict] | Série mensal nacional (mês, acessos, CNPJs). | — | sici → sici_movel.json.gz#serie_total |
| `cnpj_to_asns` | dict | CNPJ → ASNs. | — | sici → sici_movel.json.gz#cnpj_to_asns |
| `asn_to_cnpj` | dict | ASN → CNPJ. | — | sici → sici_movel.json.gz#asn_to_cnpj |
| `asn_to_cnpj` | dict | ASN → CNPJ (Registro.br). | — | sici → sici.json.gz#asn_to_cnpj |
| `distrib_modalidade` | dict | Acessos por UF, PF×PJ e modalidade de cobrança (Pós-pago/Pré-pago). | — | sici → sici_movel.json.gz#distrib_modalidade |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | sici → sici_municipios.json.gz#snapshot_date |
| `mes_referencia` | str | Mês de referência da declaração. | — | sici → sici_municipios.json.gz#mes_referencia |
| `total` | int | Quantidade de municípios. | — | sici → sici_municipios.json.gz#total |
| `municipios` | dict | Código IBGE do município → acessos, PF/PJ e operadoras. | — | sici → sici_municipios.json.gz#municipios |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | sici → sici_movel_municipios.json.gz#snapshot_date |
| `mes_referencia` | str | Mês de referência da declaração. | — | sici → sici_movel_municipios.json.gz#mes_referencia |
| `total` | int | Quantidade de municípios. | — | sici → sici_movel_municipios.json.gz#total |
| `municipios` | dict | Código IBGE do município → acessos, PF/PJ e operadoras. | — | sici → sici_movel_municipios.json.gz#municipios |

### [sici_indicadores](produtos/sici_indicadores.md) — Indicadores do SICI e outorgas sem declaração

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `municipios[ibge].hhi_cnpj / hhi_grupo / faixa_cnpj / faixa_grupo; ufs[uf]; resumo.mudam_de_faixa` | int / str | HHI do mercado fixo por CNPJ e por grupo econômico (CNPJs do mesmo grupo contam como um) em cada município e UF, a faixa (competitivo, moderado, concentrado) e quantos municípios mudam de faixa. | INFERIDO (o grupo é inferência do quadro societário em comum); sobre acessos declarados, não receita; só `grupos[].cnpjs` e `grupo_id` são lidos, nenhum dado de sócio. | sici_indicadores → mercado_grupos.json.gz#municipios |
| `sobreposicao[cnpj][]` | list[dict] | As 10 operadoras que mais aparecem nos mesmos municípios, com municípios em comum e os acessos de cada lado ali. | Presença nos mesmos municípios, não rivalidade nem disputa de clientes. | sici_indicadores → mercado_grupos.json.gz#sobreposicao |
| `municipios[ibge].acessos / hhi / lideres[].share (série de 13 meses)` | list[int\|null] / list[int\|null] / list[float\|null] | Série mensal de acessos declarados, HHI e participação das 4 maiores operadoras do mês de referência, por município. | Sobre acessos declarados, não sobre receita; mês ausente do cache fica vazio (null), nunca zero; a operadora que ainda não existia no mês conta zero na participação. | sici_indicadores → sici_serie_municipio.json.gz#municipios |
| `operadoras[cnpj].share_br / posicao_br` | float / int | Parcela dos acessos fixos declarados no país e a posição por acessos. | Sobre acessos declarados, não sobre receita; dado declarado. | sici_indicadores → sici_indicadores.json.gz#operadoras |
| `operadoras[cnpj].var_mm / var_aa` | dict | Variação absoluta e percentual de acessos contra o mês anterior e contra o mesmo mês do ano anterior. | — | sici_indicadores → sici_indicadores.json.gz#operadoras |
| `operadoras[cnpj].meses_declinio / em_declinio` | int / bool | Meses seguidos de queda até o mês de referência; verdadeiro quando chega ao limite dos parâmetros. | — | sici_indicadores → sici_indicadores.json.gz#operadoras |
| `parou_de_declarar[cnpj]` | dict | CNPJ que declarou antes e está sem declaração há pelo menos a janela dos parâmetros. | Fato sobre a declaração (último mês declarado), sem causa. | sici_indicadores → sici_indicadores.json.gz#parou_de_declarar |
| `ufs[uf] / municipios[ibge] / brasil` | dict | Acessos, HHI, número de operadoras, líder, variações, ganho e perda do ano. | HHI sobre acessos declarados. Nada é suprimido (D6) e `avisos` traz `poucos_casos` com menos de 5 operadoras; a parcela do líder (`lider.share`) fica à vista e não gera aviso próprio, por ser parte da medida. Nos mercados por grupo, `acessos`, `n_cnpjs`, `n_grupos`, `avisos_cnpj` e `avisos_grupo` (e `lider_grupo_share` na UF) dão a base de cada HHI. | sici_indicadores → sici_indicadores.json.gz#municipios |
| `parametros` | dict | Janelas e limiares usados no cálculo. | — | sici_indicadores → sici_indicadores.json.gz#parametros |
| `itens[cnpj].classe / usuarios_apnic` | str / int | Outorga SCM sem acessos declarados no mês e a classe pelos usuários estimados dos ASNs do CNPJ. | Usuários APNIC são estimativa (medição estatística); a classe nao_comparavel é CNPJ sem ASN. | sici_indicadores → sem_declaracao_sici.json.gz#itens |
| `itens[cnpj].grupo_declara` | bool | Outro CNPJ do mesmo grupo societário declarou acessos no mês. | Evidência para quem lê a linha; grupo parcial não prova controle. | sici_indicadores → sem_declaracao_sici.json.gz#itens |
| `itens[cnpj].rede_virtual_origem` | str | CNPJ da prestadora de origem quando o CNPJ é credenciado de rede virtual (MVNO) no SMP; os acessos do credenciado são declarados pela prestadora de origem (RGST, Resolução Anatel nº 777/2025). | Fato do contrato vigente na Anatel (dataset de competição); ausente quando não há contrato. Só o CNPJ da origem é publicado. | sici_indicadores → sem_declaracao_sici.json.gz#itens |
| `por_uf` | dict | Contagem por UF das outorgas sem declaração, por classe, e soma dos usuários estimados; `grupo_declarou` conta os CNPJs em que outro CNPJ do grupo declarou e `credenciadas_rede_virtual` os credenciados de rede virtual. | — | sici_indicadores → sem_declaracao_sici.json.gz#por_uf |
| `snapshot_date / mes_referencia` | str | Data do snapshot e mês de referência da declaração. | — | sici_indicadores → sici_indicadores.json.gz#mes_referencia; sici_indicadores → sem_declaracao_sici.json.gz#mes_referencia |
| `snapshot_date / generated_at / mes_referencia / natureza / fonte / limites / faixas / resumo / ufs` | str / dict | Cabeçalho do cruzamento de mercado: data do snapshot, mês de referência, natureza (inferido), fonte, limites, as faixas de HHI, o resumo de municípios que mudam de faixa e o HHI por UF. | — | sici_indicadores → mercado_grupos.json.gz#snapshot_date; sici_indicadores → mercado_grupos.json.gz#generated_at; sici_indicadores → mercado_grupos.json.gz#mes_referencia; sici_indicadores → mercado_grupos.json.gz#natureza; sici_indicadores → mercado_grupos.json.gz#fonte; sici_indicadores → mercado_grupos.json.gz#limites; sici_indicadores → mercado_grupos.json.gz#faixas; sici_indicadores → mercado_grupos.json.gz#resumo; sici_indicadores → mercado_grupos.json.gz#ufs |
| `snapshot_date / generated_at / mes_referencia / meses / fonte / parametros` | str / dict | Cabeçalho da série de participação por município: snapshot, mês de referência, os 13 meses da janela, fonte e parâmetros (meses e líderes). | — | sici_indicadores → sici_serie_municipio.json.gz#snapshot_date; sici_indicadores → sici_serie_municipio.json.gz#generated_at; sici_indicadores → sici_serie_municipio.json.gz#mes_referencia; sici_indicadores → sici_serie_municipio.json.gz#meses; sici_indicadores → sici_serie_municipio.json.gz#fonte; sici_indicadores → sici_serie_municipio.json.gz#parametros |

### [snapshot](produtos/snapshot.md) — Manifesto, resumo e detalhe do snapshot

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

### [transito](produtos/transito.md) — Trânsito por UF e cone de clientes (inferido)

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ufs[uf].asns_br / asns_com_provedor / pct_com_provedor` | int / int / float | ASNs do Brasil com sede na UF, quantos têm ao menos um provedor inferido (nível provável ou superior) e a fração. | UF = sede da organização (geo_org do ASN), não onde o trânsito é entregue; provedor = relação p2c inferida pelo ARC v2. | transito → transito/ufs.json.gz#ufs |
| `ufs[uf].hhi_clientes / top1_share / top3_share` | int / float / float | Concentração da participação de cada provedor nos pares (ASN da UF, provedor), com HHI de 0 a 10.000, maior provedor e três maiores. | Mede quem os ASNs têm como provedor inferido, não volume de tráfego nem contratos. | transito → transito/ufs.json.gz#ufs |
| `ufs[uf].provedores[]` | list | Os 20 maiores provedores da UF (ASN, nome, se é brasileiro, clientes e usuários estimados na UF, e a participação). | Usuários são estimativa APNIC e se repetem entre ASNs da mesma operadora, e share_usuarios é rotulado como estimativa. | transito → transito/ufs.json.gz#ufs |
| `asns[asn].cone_asns / cone_br / cone_usuarios / cone_ufs / clientes_diretos` | int | Cone de clientes do ASN pelas relações p2c firmes (busca em largura, segura com ciclos), sem o próprio ASN e os irmãos (mesmo CNPJ raiz ou organização do CAIDA). | Só existem elos com ao menos um ASN brasileiro; o cone de um ASN estrangeiro só conta o que tem ligação com o Brasil. | transito → transito/asns.json.gz#asns |
| `cobertura / limites / fonte` | dict | ASNs do Brasil com provedor, elos p2c usados, algoritmo e data das relações, limites e as coletas dos coletores. | — | transito → transito/ufs.json.gz#cobertura; transito → transito/ufs.json.gz#limites; transito → transito/ufs.json.gz#fonte |
| `snapshot_date / generated_at` | str | Data do snapshot e instante UTC de geração. | — | transito → transito/ufs.json.gz#snapshot_date; transito → transito/ufs.json.gz#generated_at |
