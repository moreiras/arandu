# Notas de versão

## Não lançado (correções OBINT)

Correções e melhorias da análise do OBINT (instância pública), integradas na branch `correcoes-obint`. Os identificadores entre
parênteses remetem à análise.

- **CSV da tabela de participantes do PTT (PT-24 / IXP 5.5).** O botão "Baixar CSV" da tabela baixa o PTT inteiro com o filtro, a UF, a
  busca e a ordem da tela, e todas as colunas (cadastro, direto e originador por família com IPv6 antes de IPv4, sessões e rotas
  filtradas ÷ recebidas do route server, rejeição por motivo com a idade da coleta, acessos fixos do SICI com o mês de referência, CDNs e a
  data do snapshot). Família sem coleta vem em branco, nunca como "não". Como toda exportação, exige conta: o navegador pede o login e a
  rota já trata mais de 100 linhas como `login` (nenhuma rota nova, nenhuma classe nova). Sem contatos.
- **Acessos fixos do SICI por participante do PTT (PT-24 / IXP 5.5).** A tabela de participantes ganha a coluna "Acessos fixos (SICI)",
  ordenável: os acessos de banda larga fixa que o CNPJ do ASN declarou à Anatel no mês de referência (outra data que a do snapshot, dita
  na fonte da tabela). Traço quando não há CNPJ vinculado ao ASN ou o CNPJ não declarou; "compartilhado" quando o CNPJ tem mais de um
  ASN e o mesmo total vale em cada um (não se soma). O registro traz o ASN, então a regra de empresário individual e MEI alcança a
  linha. `GET /ixps/{code}/participantes` ganhou `sici` em cada linha, `fontes.sici` e `ordem=assinantes`; o `esquema` da chamada do
  frontend passou a 2, para o navegador não servir a resposta antiga de um `?date=`. O filtro "No cadastro, sem sessão no RS" (membro
  sem sessão com o route server, com o aviso de que pode haver peering bilateral) já existia desde a integração da PT-24.
- **Variação nos KPIs de segurança do panorama e Linha do tempo com comparabilidade (PT-28 / PANT 5.1).** No Panorama técnico, as rotas
  brasileiras RPKI-válidas (IPv6 e IPv4) ganham a variação em pontos percentuais desde o snapshot anterior, e um cartão novo traz as
  rotas RPKI-inválidas com a mesma variação, sempre pela regra de comparabilidade das séries nacionais (sem variação quando a medida
  falta ou a base, o método ou a cobertura mudou; nunca zero; sem cor de melhora ou de piora). "ASNs com ROA" continua sem variação:
  não há série nacional dessa contagem na mesma base. Os blocos "Linha do tempo" de AS, PTT, operadora e UF passam a usar a mesma regra
  em cada métrica: a linha só liga pontos comparáveis (mínimo de 4 seguidos), o corte aparece com o motivo, a variação só existe entre
  pontos comparáveis, os eventos da data atípica (2026-07-05, D7) são marcados e há "Como ler" e tabela com os mesmos números.
  O bloco `historico` dos perfis ganhou `metricas`, `regra` e `atipico` nos eventos; a regra de acesso não mudou (2 datas recentes
  em `include=historico`; a série inteira só em `include=historico_completo`, com login). Para quem implanta: o `esquema` dos quatro
  perfis passou a ter o sufixo `.h2` (cache imutável de `?date=`).
- **Índice fonte para páginas (PT-20 / FONT 5.5).** `/fontes` ganha "Onde cada fonte aparece": para cada fonte do catálogo, os blocos
  das páginas de AS, PTT, operadora, grupo, UF, município e prefixo que a declaram, montado do registro de blocos (sem lista à mão),
  com a ressalva de que cada bloco combina várias fontes. As fontes que nenhum bloco declara são listadas à parte. Teste garante
  que toda fonte declarada por um bloco está no índice.

- **Estado de erro e de acesso (PT-01).** Quando o tempo de uso sem login acaba, quando é preciso entrar, quando há consultas demais
  ou quando a API ou a rede falha, as páginas passam a dizer a causa e o que fazer ("Entrar", "Tentar de novo", "volte em N"). Antes,
  essas situações apareciam como "não encontrado", "sem dado neste snapshot", zeros ou seções que sumiam, em mais de 20 páginas
  (entidades, listas, comparador, mudanças, panorama, mercado de IPv4, território). "Não encontrado" e "sem dado publicado" ficam
  só para o 404 real. O front aceita o orçamento anônimo esgotado como 403 ou como 429 com `Retry-After`. Componente
  `components/ui/EstadoDados.tsx`; `AccessError` guarda `retryAfter` e o motivo do 401 (TRANSV-E1, ASN-E9, OPERADORA-E1,
  IPV4-E1, MUN-E11, UF-E1, EST-E5, MUNS-E7, LOC-E5, USO-E4, MAPA-E6).
- **Data do snapshot preservada (PT-02).** Com `?date=` na URL, todas as páginas pedem os dados daquela data (municípios, uso da
  Internet, qualidade, regulatório, mercado IPv4, communities, "Quem entrou e quem saiu" do PTT, blocos de IPv4 e FUST), e a data
  acompanha a navegação: links de entidade, abas, lentes, comparador, relatório, menu e busca. Só se sai dela pelo seletor (opção
  atual) ou pelo Voltar. Link copiado do explorar ou de uma entidade reabre o mesmo snapshot. O aviso de data antiga traz "Ir para o
  snapshot atual" e diz que navegar em datas antigas é possível com o login gratuito (TRANSV-E2, MUNS-E1, MUNS-E2, QUALIDADE-E1,
  REL-E6, IXP-E9, IPV4-E2, IXE-E10, USO-E14).
- **Glossário de contagens (V3).** `docs/glossario-contagens.md` descreve cada universo que aparece com o mesmo nome (ASNs
  brasileiros pela LACNIC ou pelo Registro.br, PTTs, participantes por sessão, cadastro ou originação, declarantes do SICI,
  municípios, usuários APNIC por AS, por UF, união ou soma por PTT), com origem no código e valor medido. É a base dos rótulos únicos
  da tela (PT-15).
- **Textos e rótulos que diziam outra coisa (PT-03).** O histórico mostra a data real do primeiro snapshot, lida da lista de
  snapshots, e /mudancas diz a janela de confirmação de cada tipo de evento (sete tipos entram com um snapshot só). O mercado de IPv4
  cita o início real da coleta das listas (2026-11-01, era "junho de 2026"). O panorama de mercado descreve o cruzamento de outorgas
  com ASN como coincidência de CNPJ, e as abas STFC e SeAC deixam de prometer acessos. Presença de CDN descrita como adesão à lista de
  membros do IX.br; grupos societários como ligações diretas e grupo por cadeia, sem "quem controla quem"; localizador como
  originação vista no route server; PTT externo com "Snapshot" no lugar de "Atualizado em"; contagens de /snapshots conforme o campo;
  legenda única dos cartogramas; "Data no cadastro" das outorgas; dica de "Dir. IX.br" como sessão com o route server; telas
  públicas sem instruções de operação (TRANSV-E7, MUD-E1, IPV4-E4, PANORAMA-E3, PANORAMA-E4, CDN-E2, CDNS-E1, GRUPO-E4, LOC-E2,
  IXE-E3, SNAP-E1, SNAP-E2, TRANSV-E15, HOME-E10, EST-E3, OPERADORAS-E6, ASES-E2).
- **Acessibilidade e 404 real (PT-29).** Endereço inexistente passa a responder 404 de verdade, com página e título próprios
  (antes toda URL respondia 200). O nginx do frontend lista as rotas da SPA (`map $rota_spa`); rota nova precisa entrar nele, e
  `components/layout/rotas.test.ts` confere (guia do desenvolvedor, seção Frontend). Quem usa leitor de tela ou só o teclado lê o
  estado de filtros e botões (`aria-pressed`, `aria-expanded`), expande linhas e seleciona grupos, e tem em tabela ("Ver dados") os
  números de mapas e cartogramas que antes só existiam como cor ou dica. Tabelas com `caption` e `scope`; o selo do relatório (fato,
  inferido, estimado) aparece escrito, também impresso; a contagem animada do PTT respeita movimento reduzido; selo SCM do
  localizador e erro do login passam de 4,5:1 de contraste (INST-E2, INST-E3, LOC-E8, INST-E10, IXP-E11, REL-E9, CDNS-E7, SEG-E1,
  EST-E7, OPERADORA-E3, OPERADORA-E4, OPERADORA-E5, GRUPO-E1, GRUPOS-E2, ASES-E8, USO-E13).
- **Cálculos de rede corrigidos (PT-04).** Números publicados que mudam:
  - interconexão do ASN (REST e MCP `asn_interconexao`): o carregador é o AS vizinho ao PTT (último do caminho gravado), e caminhos
    de um AS contam; antes se tomava o primeiro elemento de um caminho invertido e se atribuía entrega a AS sem sessão no PTT;
  - MOAS deixa de ser publicado como número (`moas: null` com `moas_indisponivel`) em `/routing-analysis`, `/brasil/indicadores`,
    MCP e telas, inclusive para snapshots antigos: a coleta da tabela global guarda uma origem por prefixo e não permitia detectar
    MOAS, então o 0 publicado era limite da coleta, não ausência de eventos (MOAS é raro, mas existe); a medição volta quando a coleta
    guardar todas as origens por prefixo e por coletor; a categoria da cobertura passa a "Várias origens, sem agregado";
  - profundidade de mais-específicos pelo pai imediato (era sempre 1); a lista de filtráveis mostra tudo por padrão;
  - originadores por PTT são a união IPv6 ∪ IPv4 (era o maior dos dois) em `ixps/index.json`, `ixp_lista`, `query(ixps)` e na série;
  - PTTs externos contam redes distintas (`redes`, `redes_br`, `portas`; `member_count` e `br_member_count` viram alias): decix-rj
    passa de 16 a 14 membros;
  - communities dos route servers contam ASNs distintos (`asns_total`; a soma por PTT fica em `asns_soma_ptts`): `65000:6939` passa
    de 1.382 a 769;
  - mapeamento PeeringDB dos PTTs: `ria` → 1847 e `rao` → 4862 (estavam trocados), sem `santa-maria`, e `cpv` → 603, `cac` → 2822,
    `cas` → 415 (estavam permutados); com a próxima coleta as instalações vão para os PTTs certos (38 de 40);
  - trânsito do AS pela inferência de relações (regra `sintese-as-2`, sem o próprio AS, irmãos e ASNs do mesmo CNPJ), com campo
    novo `n_provedores_provavel` (`n_provedores` segue contando confirmado ou acima); bloco PeeringDB do ASN e da CDN lê os campos
    que a API envia; presença de CDN nos PTTs em três critérios (membro, sessão, só por terceiros).
  Parâmetro `esquema` de `routing-analysis` e `brasil/indicadores` passa a 3 (ASN-E1, ASN-E2, ASN-E4, CMP-E5, BGP-E2, PFX-E3,
  BGP-E5, BGP-E4, BGP-E8, IXP-E3, IXPS-E1, IXE-E1, IXE-E2, COMM-E1, INST-E2, IXPS-E2, PANT-E1, IXPS-E3, CDN-E1).
- **Cálculos de mercado e território (PT-05).** Serviços da operadora só pelas outorgas: SMP só com outorga SMP; credenciamento
  de rede virtual tem rótulo próprio (acessos do credenciado são declarados pela prestadora de origem, RGST, Res. Anatel 777/2025);
  `has_smp` deixa de valer para credenciada sem outorga própria; relatório sem `b2cPct: 0` fixo nem outorga afirmada sem registro.
  `/operadoras`: aba SMP mostra o universo com o filtro desligado (eram 17 de 256), e `ativo` vale por serviço (aba SCM: 9.917
  declarantes, eram 9.919 por contar acesso móvel). `/omissao-sici`: `grupo_declara` exato (`true`, `false`, `desconhecido`) e filtro
  de UF para quem parou de declarar. UF ganha `operadoras_presentes` (quem tem acesso na UF, com acessos na UF; antes só as sediadas).
  Município: nome de quem não declarou no mês e `None` em vez de 0 na série; penetração sem arredondar a zero. Regulatório: um sistema
  NGEO por linha, sem as cópias por ano de agenda (`ngeo_sistemas`). Panorama móvel: barras de geração e modalidade com a base de
  todas as linhas, série nacional sem área "B2C" igual ao total, sem a razão de declarantes sobre licenciados. Home: destaque de
  divergências com a regra do panorama. Explorar: `float` e listas com tipo, receitas 24 e de macro-região corrigidas. Localizador:
  conta ASNs no raio e `/resolve/place` aceita UF (homônimo sem UF devolve `ambiguo`). MCP: `historico_mudancas(resumo=true)` aplica
  `uf`, `tipo` e `asn`; `uf_detalhe` ganha `operadoras_presentes`; `list_outorgas` muda a semântica de `ativo`. `esquema` de
  `/ufs/{uf}` e `/satelites/resumo` passa a 2 (OPERADORA-E8, OPERADORA-E9, REL-E1 a REL-E5, OPERADORAS-E2, OPERADORAS-E3,
  OPERADORAS-E8, OPERADORAS-E12, RANKINGS-E2, RANKINGS-E4, PANORAMA-E1, PANORAMA-E2, PANORAMA-E5, REGULATORIO-E1, MUN-E1, MUN-E2,
  MUN-E8, UF-E2, UF-E7, HOME-E3, EXP-E1, EXP-E2, EXP-E5, EXP-E7, LOC-E3, LOC-E4).
- **Pipeline, coleta e estado do dado (PT-06).**
  - "ASN brasileiro" é o ASN delegado pela LACNIC/Registro.br com país BR (`is_br`), regra única em todo o site, inclusive na
    análise de rotas e em `/brasil/indicadores`, que usavam a lista de ASNs do Registro.br: 21 ASNs saem do conjunto brasileiro
    (9.150 → 9.129 em 2026-11-22). "Rota brasileira" é a de prefixo contido em bloco alocado pelo Registro.br; a origem do anúncio
    não define. A categoria "apenas origem BR" deixa de compor o total (as categorias somam o total), e rotas de ASN brasileiro em
    espaço de outro RIR ficam numa contagem de apoio, fora do total (D4).
  - PTT com tabela de rotas vazia numa família aparece como coleta parcial ("tabela vazia"), nunca "ok" com 0%: é o caso do IPv6
    de ap, fec e rao desde 2026-10-31, quando o looking glass passou a responder sem rotas com os route servers ativos (a causa do
    lado da coleta é hipótese). Vale também para snapshots já publicados (a marcação é feita na leitura).
  - Eventos de ROA, ASPA e RPKI só são gerados quando o campo de origem estava coberto nos dois snapshots comparados; campo ausente
    não vira zero. A regra é versionada (`eventos_regra = 2`); a camada de eventos publicada será regenerada com nota de revisão
    datada (D7), corrigindo o pico de 2026-07-05.
  - 33 PIX ganham coordenada com fonte registrada (facility do PeeringDB consultada em 2026-11-24, ou a página do PTT no IX.br);
    16 seguem sem, listados com o motivo. CEP de Lajeado corrigido. cxj, igu e laj voltam ao mapa e às distâncias.
  - `/ufs`: contagem de PTTs e distância usam a mesma lista; em snapshot sem SICI, acessos e municípios saem nulos, não zero.
  - Cetic: caixa de frase preserva "Internet", "IX.br" e "IPv6"; margem registrada como zero não vira "±0,0", e precisão baixa
    é avisada. Feed Atom: título conta eventos (não ASes), `updated` na data de confirmação e links por entidade. A API de
    snapshot repassa `manifest.comparado_com`.
  `esquema` de `/ufs`, `/ixps`, `/routing-analysis` e `/brasil/indicadores` sobe (BGP-E3, IXP-E1, IXP-E2, IXPS-E4, TRANSV-E8,
  MAPA-E1, EST-E1, EST-E2, USO-E1, USO-E2, TRANSV-E18, HOME-E1).
- **Nota de revisão: eventos de ROA, ASPA e RPKI (D7), 2026-11-25.** A camada de eventos de todos os snapshots (2026-06-28 a
  2026-11-22) foi regenerada com a regra 2 (`eventos_regra = 2`), que só gera evento de ROA, ASPA ou RPKI quando o campo de origem
  estava coberto nos dois snapshots comparados (campo presente ou documento que passou pela etapa de saúde). Causa: campo ausente era
  contado como zero; o `roa_list` de ASNs estrangeiros foi publicado só em 2026-06-28 e deixou de ser em 2026-07-05, e a perda do
  campo virou perda de ROA. Contagens antes → depois, em 2026-07-05: `roa_perdido` 50.127 → 63 (os 63 de ASN brasileiro),
  `aspa_perdido` 1.827 → 2, `rpki_invalido_resolvido` 1.815 → 14. No total das 20 datas: `roa_perdido` 50.919 → 834, `aspa_perdido`
  1.864 → 38, `rpki_invalido_resolvido` 2.069 → 267, `roa_ganho` 1.140 → 1.135; `aspa_ganho`, `rpki_invalido_novo` e todos os demais
  tipos não mudam. Nas datas recentes saem também eventos de ASNs que deixaram o snapshot (o `asn_sumido` deles continua). Relatório
  por data e tipo gerado por `python -m products.history.regenerar_eventos`; a troca da camada servida é feita na implantação.
  A nota aparece também em /mudancas (quando o filtro inclui eventos de ROA, ASPA ou RPKI) e em /snapshots (PT-06c).
- **Nota de revisão: grupos societários (D5), 2026-11-25.** Só sócio com participação societária, nas duas empresas, liga empresas num
  grupo; administrador, diretor e presidente sem participação deixam de ligar (tabela de qualificações conferida no arquivo oficial de
  Qualificações dos dados abertos de CNPJ da Receita, 2026-11). Medido com dado real (snapshot 2026-11-22, etapa `socios_grupos` rodada
  em diretório de teste): grupos 1.420 → 1.336; CNPJs básicos em grupo 3.667 → 3.385; 460 pares ligados só por cargo sem participação
  deixam de ligar; 151 grupos se desfazem ou encolhem. Exemplos: TIM (raiz 02421421) e a raiz 40166794 deixam de formar grupo (eram
  ligadas só por diretores); BRISANET (04601397) e 44250088 idem. O nome do grupo passa a seguir regra visível (marca curada, senão o
  CNPJ com mais acessos) e o `grupo_id` passa a ser `grp_` + menor raiz do grupo, com tabela de equivalência e redirecionamento dos links
  antigos; séries históricas por grupo de snapshots anteriores usam os ids antigos. "Mercado consolidado" passa a selo inferido.
  Operadora mostra "Grupo no SICI (declarado à Anatel)" e "Grupo societário (inferido do quadro societário da Receita)". Sociedade
  anônima (naturezas 204-6 e 205-4 da Receita) não tem grupo inferido pelo próprio quadro, que traz diretoria e conselho e não os
  acionistas: aparece como "grupo não inferível pelo quadro societário (S.A.)", com o grupo declarado ao SICI ao lado; a ligação que
  vem do quadro de uma Ltda da qual a S.A. é sócia continua (decisão de 2026-11-25). No dado real, 161 S.A. ficam assim marcadas, e os
  totais acima não mudam (o quadro delas só trazia gestão) (GRUPOS-E1, GRUPO-E4, GRUPO-E12, GRUPO-E14, MUN-E4, OPERADORA-E10).
- **Datas por fonte e estado da coleta (PT-16).** /snapshots mostra cada indicador com valor, selo, fonte e data de referência, e um
  cartão de coleta (PTTs coletados de configurados, versão do processamento, verificações). /fontes mostra a licença e o uso comercial
  em rótulos legíveis, o aviso de itens do cadastro ainda não conferidos, o frescor ("atrasada (limite N dias)") e estados distintos
  (desativada, sem versão para o snapshot, curadoria, coleta manual); snapshot sem `manifest.sources` diz isso, sem data inventada.
  Route servers: a cobertura do rodízio chega ao produto e à tela ("N de M vizinhos lidos nesta rodada, K mantidos, S sem leitura,
  leitura mais antiga com D dias"). Instalações: o selo de cadastro mostra as datas do PeeringDB como vêm (registro e último vínculo),
  sem inferir a razão delas (decisão de 2026-11-25). Id `rpki` do bloco de grupo corrigido para `rpki_collector` (SNAP 5.1, SNAP 5.3,
  TRANSV-E9, FONT-E1 a FONT-E5, IXP-E4, COMM-E4, INS-E1, INST-E3).
- **Política editorial (PT-17; D6, D12).** "Omissão" sai do site, da API, do MCP e da documentação: o termo é "sem declaração ao SICI
  em AAAA-MM". A collection `omissao_sici` passa a `sem_declaracao_sici`, a rota `/omissao-sici` a `/sem-declaracao-sici` e
  `?visao=omissao` a `?visao=sem-declaracao`; os nomes antigos seguem como alias, com aviso de depreciação. Rankings não escondem
  linhas: a variação em 12 meses mostra a base (com "base pequena" abaixo de 1.000 acessos), pode ser ordenada pela variação absoluta, e
  quem não tem percentual vai para o fim. /ases e as páginas de PTT e BGP usam paleta neutra, sem verde e vermelho de juízo; %IPv6 com
  menos de 1.000 usuários estimados leva o selo "amostra pequena". Agregados por UF e município (prontidão, ROV, MANRS, HHI) mostram o
  número de casos e o peso do maior, com aviso em vez de supressão. Listas nominais em ordem neutra (route servers por PTT e ASN; multas
  em ordem alfabética, com "Multa constituída não é condenação definitiva"). O alerta de PTT próximo deixa de trazer recomendação de
  negócio, e o diagnóstico de BGP deixa de presumir causa (IXP-E10, ASES-E9, ASES-E10, BGP-E9, RANKINGS-E6, ASN-E6, IPV4-E15, SEG-E5,
  SEG-E11, OPERADORA-E12, OPERADORAS-E18).
- **Imutabilidade (PT-18, D8).** Snapshots e Sobre deixam de prometer imutabilidade absoluta: "Snapshots publicados não mudam,
  salvo correção registrada no CHANGELOG do projeto; quando a correção altera um número publicado, as páginas afetadas trazem uma nota
  datada." O Sobre passa a dizer que os dados são publicados semanalmente e que cada fonte é coletada no seu próprio calendário. Sem
  registro estruturado de correções: elas ficam neste CHANGELOG (TRANSV-E16).
- **Selo, fonte e data visíveis (PT-14).** Os KPIs do panorama (66) e da Home mostram, em texto e não só em dica, a natureza do
  número (fato, estimado ou inferido), a fonte e a data de referência ("Estimado · APNIC Labs · ref. 2026-11-15"), legíveis por leitor
  de tela. O /sobre explica os três selos, com o texto da mesma fonte usada nos KPIs e no relatório (TRANSV-E3, INST 5.4).
- **Motor de consulta (PT-19).** Na consulta genérica (`/query/<coleção>` e a tool `query` do MCP), a agregação passa a respeitar
  `sort` (por campo de `group_by` ou pelo nome do agregado), `limit` e `page`, e a resposta traz `total_grupos`. Mudanças de
  comportamento: `count` com `field` conta os valores não nulos do campo (antes contava linhas; sem `field` continua contando linhas), e
  `sort` por campo que não é grupo nem agregado responde 400 com as opções válidas (antes era ignorado). As coleções `municipios` e
  `acessos_municipio` ganham `mes_referencia` (mês do SICI). O explorador ganha o campo "A partir de" em eventos e séries (TRANSV-E10,
  TRANSV-E11, EXP-E4).
- **Universos de contagem e glossário (PT-15).** Cada total traz o rótulo do seu universo (cadastro do PTT, sessão com route server,
  origem), com a nota "Por que há vários totais" e a seção `/sobre#contagens`. Na consulta genérica, `ixps_membro` (cadastro) e
  `ixps_sessao_rs` (sessão com route server) substituem `ixps_direct`, que continua como alias com o valor do cadastro e devolve
  `aviso_obsoleta`. Usuários alcançáveis por PTT passam a ser apresentados como não aditivos; médias do panorama e da Home trazem
  mediana e faixas; selo, fonte e data chegam às páginas de entidade (TRANSV-E3 a E6, ASES-E2, IXPS-E5, IXP-E6, UF-E3, UF-E4, USO-E5;
  MUNS-E3 e HOME-E4 parciais, só texto).
- **Metadados por collection (PT-20).** `/schema` e `describe_schema` informam, por collection, as fontes (com licença e uso
  comercial), o selo (fato, inferido, estimado) e o uso comercial efetivo (pior caso), lidos do catálogo; o índice ganha
  `fonte_e_selo` e resumos que preservam o aviso do mês de referência do SICI. Saem contagens fixas de PTTs em textos do MCP e do
  schema; `ferramenta_detalhe` de `faixas_espectro` e `satelites_direitos` deixa de apontar para `historico_snapshots` (TRANSV-E12,
  TRANSV-E17).
  Onde a collection mistura naturezas, o selo vale como padrão e os campos de outra natureza trazem `selos_campo` (ex.: em `asns`,
  `apnic_users`, `apnic_v6_users` e `pct_v6` são estimados).
- **Limites publicados (PT-21).** Novo `GET /api/v1/limites` (aberto) publica os tetos em vigor, lidos do código e da configuração:
  orçamento diário e custo por chamada sem conta, janelas da API e do MCP, cota da chave de MCP, tetos de contatos por conta. O quadro
  "Escolha o seu acesso" de `/dados` é gerado dessa rota e, sem a chave de MCP ligada, a página não a promete. O exemplo de consulta
  passa a usar `acessos_municipio` por UF com `mes_referencia`, em vez de `operadoras` por `uf_sede`; o `llms.txt` descreve os limites
  reais (TRANSV-E13, DADOS-E1, DADOS-E2).
- **Acessibilidade.** As fatias dos gráficos de rosca do panorama têm nome acessível (PT-29).
- **Participantes por PTT (PT-24).** Nova tabela única de participantes em cada PTT (`GET /ixps/{code}/participantes`, classe
  `metered`, prévia de 100 linhas): membro do cadastro, sessão com route server por família, originador, sessões no route server,
  rotas filtradas sobre recebidas, idade da coleta e CDNs da lista curada; família sem coleta aparece como "sem coleta". A lista de
  PTTs ganha o grupo "Interligação" (sessões up/down por família e CDNs) e a coluna "dos quais brasileiros". Instalações mostram a
  situação de cada rede do prédio no PTT local (`/facilities/{id}?include=redes_perfil`) e a cobertura de PTT nomeada; a matriz de
  CDNs separa membro com sessão, membro sem sessão e presença só via outro AS; `/ases` separa "membro" de "sessão RS"
  (`ixps_membro_count`). Esquemas do front: `/ixps` 4, `/cdns/presence` 2, `/facilities` 3 (IXP 5.5, IXPS 5.1 e 5.4, CDNS 5.1,
  INSTALACAO 5.1, INSTALACOES 5.1, ASES 5.1).
- **Conformidade com regra de referência (PT-26, D11, D12).** Faixas de HHI aparecem como "método do projeto" (abaixo de 1.500,
  1.500 a 2.499, 2.500 ou mais), sem cor de juízo, citando o Guia H do CADE (2016); HHI por município e UF é cálculo do projeto. A
  coleta de acessos cita o sistema Coleta de Dados da Anatel (Res. 774/2025); o rótulo "SICI" permanece. Município ganha faixa de
  fatos de declaração e a UF um bloco de contagens "sem declaração"; as listas mostram o grupo e a causa "credenciada de rede virtual"
  só onde há contrato (RGST, Res. 777/2025). A página do AS mostra situação cadastral do CNPJ quando não ativa, ASN em recuperação e o
  texto do selo "sem outorga"; multas têm síntese com situação, ano parcial marcado e a regra de atualização (Selic, 0,33% ao dia até
  20%). Mapa e Localizador mostram a declaração das outorgas SCM com o mês. A camada `maps/scms.geojson` traz o mês de referência
  também para outorgas sem declaração (snapshots novos). `esquema`: perfis de município 5, UF 3, ASN 3; instalações 4.
- **Séries e comparabilidade (PT-28).** Regra única (`core/comparabilidade.py`): a variação não é calculada quando muda a base, o
  método ou a cobertura da coleta (25% ou mais, limiar do projeto), nem atravessa a data atípica de 2026-07-05 (D7); a tela mostra o
  corte, o motivo e o "Como ler". Novas séries com tabela, selo e fonte: estado RPKI das rotas brasileiras e prontidão, ROV e
  DNSSEC. Panorama técnico: variação em p.p. dos usuários com IPv6 desde o snapshot anterior. `/snapshots/diff` ganha `razoes` e
  `comparabilidade` (`variacao` pode ser nula); novas `GET /history/brasil/series` e `GET /cdns/mudancas` ("Mudanças entre
  snapshots" em /cdns).
- **Acessibilidade.** Alvo de 24 px nos links de PTT de /instalacoes e links sublinhados no quadro de /dados (PT-29).
- **Onde atua (PT-23).** Operadora: resumo por UF e tabela de todos os municípios com parcela no município, número de declarantes
  e HHI local, sempre com o mês de referência do SICI; `municipios_detalhe` ganha `share`, `municipio_acessos`,
  `municipio_operadores`, `municipio_hhi` e `avisos_hhi`, o que também corrige o mapa de parcela, que recebia `share` nulo. Grupo:
  `GET /grupos/{id}/municipios` e bloco "Onde o conjunto atua", com HHI local por grupo (inferido) e por CNPJ; prévia de 100 linhas.
  Panorama de mercado: municípios por faixa de HHI local (por CNPJ e por grupo) no país e por UF, e o HHI nacional por CNPJ.
  `esquema` de grupos 6 e de `/mercado/grupos` 2.
- **Síntese e portas (PT-22, PT-27).** Home, Panorama técnico e de mercado, UF, Municípios, PTT, IXPs, CDNs, Uso da Internet e
  Localizador ganham um bloco "Em resumo" com 2 a 4 frases geradas dos números da própria página, cada uma com selo, fonte e data
  (no Localizador, anunciado a leitores de tela). A Home passa a ter cinco portas por lente (técnico, regulação, jornalismo, política
  pública, empresa). Nova `GET /territorio/resumo` (agregados por distância ao PTT mais próximo), usada em `/municipios`.
- **Panorama técnico.** A variação do IPv6 pede `/snapshots/diff` com `opcional`: sem histórico, 204 em vez de erro no console.
- **Território (PT-25).** Localizador: bloco "Interconexão no IX.br das redes do raio" com o PTT onde as redes do raio mais participam
  e o mais próximo em linha reta, ambos com distância e "N de M redes" (inferido); o CSV ganha as colunas do PTT de referência. Nova
  `GET /territorio/infra-proximos` (cabos, enlaces da UIT, linhas de transmissão e instalações do PeeringDB num raio), usada no
  Localizador e na ficha do município, que ganha também a tabela de PTT efetivo (onde operadoras com 5% ou mais do fixo local têm
  sessão direta). Municípios: a distância ao PTT mostra o PIX mais próximo e a coluna "Redes com sede" (inferido); `/territorio/ranking`
  ganha `ptt_proximo_nome`, `pix_proximo` e `redes_sede` (`esquema` 2). A tool `infra_proximos` do MCP devolve também `por_status`.
  Parcial: municipio 5.2, estados 5.4 e o filtro de redes sem sessão na lente "Sem PTT a 100 km" ficam para depois.
- **Instalações do AS (P17).** A coluna passa a "PTTs no prédio" e a nota diz que não é o ponto em que a rede se conecta ao PTT (o
  IX.br não divulga em que PIX cada participante se conecta; o cruzamento é rede→prédio e prédio→PTT, ambos do PeeringDB).
- **Replay de paridade.** `scripts/replay.py` recompõe o fragmento `relacoes` dos documentos de ASN (cópia do build ou, se limpo, a
  partir do publicado); replay de 2026-11-22: 0 diferenças novas.
- **Decisões de fechamento do mantenedor (2026-11-25).** A série nacional (`/history/brasil/series`) abre sem login, com a série
  inteira, por conter só totais do Brasil; séries por ASN, PTT, UF e operadora seguem a regra de histórico. O corpo do 429 só sugere a
  chave de MCP quando ela está ligada. `/uso-aceitavel` lê de `/api/v1/limites` o orçamento e o custo por chamada e traz o e-mail de
  contato. Os overlays de produção e sem nginx repassam `MCP_KEY_ATIVA` e `MCP_COTA_DIARIA` à API.
- **Segurança: X-Forwarded-For.** O nginx do frontend só aceita o X-Forwarded-For dos IPs da borda declarados em `NGINX_REAL_IP_FROM`
  (lista de IPv6 e IPv4 separados por espaço ou vírgula; vazio = ninguém); as faixas privadas do Docker deixam de ser confiadas.
  **Quem implanta atrás de borda precisa declarar o IP dela**, senão todos os clientes aparecem com o IP da borda e dividem o
  orçamento; valor mal formado impede a subida do frontend. A imagem do frontend precisa ser reconstruída (BuildKit).
- **Textos.** O total de PTTs na tabela-resumo de `/ixps` e do painel vem do snapshot (ok + parcial + ausente); o número fixo sai do
  Sobre, das descrições de `ixp_lista`, dos recursos do MCP e da descrição da fonte `peeringdb_ixps`. Continuação do PT-15:
  `ixp_proximos` e a rota `nearby` descrevem `direct` como membro do cadastro, e as descrições de presença, `ixp-peers` e peers por PTT
  passam a dizer "sessão com o route server" (só texto; nenhum campo ou valor mudou).
- **Pós-implantação.** `scripts/post_deploy_check.py` confere `/ases`, rota real do SPA, em vez de `/asns`.
- **Rótulos de relação com o PTT.** No frontend, "peering direto", "peer direto" e "par direto" em legendas, mapa, tabelas, histórico e
  textos passam a dizer "sessão com o route server" (dado `asn_direct` do looking glass), distinto de "membro do cadastro"; rótulos em
  `RELACAO_PTT` (`lib/universos.ts`) e termo antigo vetado nos testes. As descrições da API e do MCP (`asn_interconexao`, `asn_rede`,
  histórico, catálogo da consulta, glossário "direto vs. originador") também passam a dizer "sessão com o route server"; só texto.
- **Operação.** `arandu run --force` repassa `--force` às etapas que declaram `aceita_force` no catálogo (55 etapas), em vez de só
  afetar `--retomar`: antes a `saude_asn` relatava "ok" com os alertas antigos. Sem `--only`, isso refaz coletas caras (`receita_cnpj`,
  `cnpj_geo`, `*_geo`, `irr_route_objects`); use `--only`. `anatel_sici` e `anatel_sici_movel` ainda não aceitam (`--force-full` tem
  outro efeito). `restart-safe.sh` marca o ponto de rollback e constrói com o nome de imagem declarado no compose, em vez de
  `arandurape-*` fixo: a instância com outro nome ficava sem rollback.
- **Privacidade da sede (PT-08).** Logradouro, número, complemento, bairro, CEP e coordenada exata da sede deixam de sair para
  qualquer titular no MCP (`asn_detalhe`, `asn_lote`, `outorga_*`, `operadora_detalhe`, `query`, resources de ASN, operadora e UF) e
  nas rotas REST de ASN, outorgas e operadoras; ficam município e UF. No `query`, a posição só serve ao filtro `near` e não volta na
  resposta; selecionar ou filtrar por esses campos dá erro. `geo_localizar` e `/resolve/place` passam ao centroide IBGE do município
  (campo `posicao`). A receita de `asns` deixa de sugerir telefone, e-mail e endereço. A máscara de CPF passa a valer também na lista de
  blocos IPv4 por organização (ASN-E5, ASES-E15, IPV4-E14).
- **Vínculo ASN ↔ CNPJ (PT-09, D5).** Índice único `asn_vinculo` (`cnpj`, `raiz`, `marca`, `estrangeiro`, `nenhum`; só `cnpj` é
  fato, os demais inferidos) usado por operadora, grupo, grupos, /ases, Home e MCP. ASN em filial (mesma raiz) passa a contar para a
  operadora e o grupo, sem duplicar ASN nas somas; marca curada e AS estrangeiro são listados, não somados. O destaque "sem ASN
  próprio" da Home deixa de listar Oi, Hughes e Sky (a raiz da Zaaz no Ne entra na marca SKY pelo grupo "SKY/ZAAZ" declarado ao SICI,
  selo inferido, decisão de 2026-11-25); Starlink aparece como AS estrangeiro (GRUPO-E2, GRUPO-E7, HOME-E2).
- **Página de prefixo (PT-07).** Detentor no Registro.br e origem observada (tabela global ou route servers) vêm separados, cada um
  com fonte; o estado RPKI é o do anúncio observado (`nao_avaliado` sem anúncio), com os ROAs que cobrem o prefixo; o CIDR é
  normalizado e qualquer rota observada abre, mesmo fora das alocações do Registro.br; a ausência é explicada. `origin_asn` fica como
  alias deprecado de `registro_asn`; grafia inválida responde 422 (PFX-E1, PFX-E2, PFX-E4, PFX-E5).
- **MOAS medido (PT-04b).** A coleta da tabela global passa a guardar todas as origens observadas por prefixo e por coletor
  (`origins-multi-{afi}`), e o MOAS volta a ser publicado como fato observado, sem rotular causa: contagem por família, global e de
  prefixos brasileiros, lista com as origens e os coletores que viram cada uma; "nenhum MOAS observado" quando a contagem é zero.
  Snapshots anteriores continuam sem número, com o motivo. Cartão, aba e tabela de /bgp e o bloco do prefixo voltam. A primeira
  execução depois disto coleta a tabela global de novo (BGP-E2, PFX-E3).
- **Registro do aceite (PT-13, D10).** A conta passa a guardar a versão da política aceita e a data do aceite, gravadas no login
  (contas antigas ficam "não registrada" até o próximo login). A tabela de retenção é gerada das constantes do código, com teste;
  a página de privacidade passa a exibi-la (PT-13b). A política (versão 2026-11-25, aprovada pelo mantenedor) declara: o log do servidor
  web, com IP, URL e horário, mantido por tempo indeterminado; os registros de uso sem IP; o registro de páginas visitadas por quem tem
  conta, com IP, por 3 meses; as contagens por dia, conta, origem e classe de rota por até 12 meses, com o identificador da conta
  retirado só na exclusão; os tetos do MCP por minuto, hora e dia; e o armazenamento local do navegador. Nenhuma prática de registro
  mudou. Quem já tinha conta grava a versão vigente no próximo login.
- **Acesso, lista nominal e citação (PT-12; D2, D3, D9).** Lista nominal de prontidão pública com salvaguardas (pilar sem dado é "não
  medido", ordem neutra, aviso de método). "Citar" passa a trazer os valores, a data do snapshot e as fontes, e avisa que o link abre
  sem login enquanto a data estiver entre as recentes; quem abre data antiga sem login vê o aviso de snapshot histórico. `/snapshots`
  passa a exigir login (as páginas abertas usam `/brasil/snapshots`); o detalhe de PTT externo continua sem login (D9 revista pelo
  mantenedor em 2026-11-25); as chamadas das páginas de entrada
  ficam abertas (`/brasil/destaques`, `/cdns/presence`, `/rpki/summary`, `/prontidao/resumo`, `/changes/summary` recente). Orçamento
  anônimo esgotado responde 429 com `Retry-After` até a meia-noite UTC e corpo explicando o limite. Listas mostram ao anônimo uma
  prévia de 100 linhas. As 11 fontes de exposição aberta declaram a decisão e a atribuição no catálogo e em /fontes (SEG-E2, INST-E1,
  REL-E7, TRANSV-E19, IXE-E4, TRANSV-E20, DADOS-E1, EXP-E4, OPERADORAS-E1).
  Atribuições: "Fonte: PeeringDB" nas fontes do PeeringDB e "Fonte: Anatel" nas camadas geo de outorgas, com a geocodificação do
  OpenStreetMap (ODbL) onde ela entra. `/uso-aceitavel` publica os tetos de uso sem login (600 s por dia, 3 s por chamada, 429 com
  `Retry-After` até a meia-noite UTC, rede = IPv4 inteiro ou IPv6 /64).
- **Pessoa natural (PT-11, D1).** Empresário individual e MEI (natureza jurídica da Receita) aparecem pelo nome fantasia ou como
  "Empresário individual" com ASN e CNPJ mascarado, em tela, REST, MCP e CSV, inclusive no nome de ASN e na razão social do
  cadastro; o ponto do mapa vai ao centróide do município e o endereço sai. A regra vale na publicação, na leitura, no motor de
  consulta, na busca e na saída de todas as respostas, inclusive de snapshots já publicados. Buscas por proximidade de sedes exigem
  raio de pelo menos 2 km. Nas transferências IPv4, nome estrangeiro sem marcador de empresa é tratado como pessoa provável e omitido
  (MAPA-E3, INS-E3, GRUPO-E16, TRANSV-E14, OPERADORA-E16, BGP-E18, MUN-E19, IPV4-E14).
- **Correção de manifesto dos snapshots antigos (P10), 2026-11-25.** Nos snapshots cujos documentos de ASN foram compactados em
  `asns.zip` depois do fechamento (2026-06-28 a 2026-08-23), o `manifest.json` listava os `asns/<n>.json` soltos, que já não existiam,
  e não listava o `asns.zip`. O script `scripts/mascarar_pessoa_natural_publicados.py --corrigir-manifesto` reconcilia a lista com o
  disco: tira as entradas absorvidas pelo zip (só as que estão dentro dele), acrescenta o `asns.zip` com o checksum atual e confere
  todos os checksums ao fim; nenhum documento é alterado. A regra de pessoa natural deixa de regravar documento já tratado (antes ele
  era reserializado com outra formatação, mudando bytes e checksum sem mudar o dado).
- **Apresentação e linguagem (PT-30), forma aprovada pelo mantenedor em 2026-11-26.** Home, AS e operadora mostram os cartões
  primeiro e o resumo em texto depois (`ResumoEmTexto`), com fontes e datas recolhidas (`FontesEDatas`, `ApresentacaoRecolhida`). Os
  selos de natureza do dado ficam só com símbolo e cor (círculo, triângulo, losango), com nome acessível e dica de fonte e data que
  abre por mouse, foco de teclado e toque; a legenda fica no rodapé. As caixas de destaque seguem o tom do selo (`lib/paletaSelos.ts`),
  com contraste AA e sem cor de juízo (vermelho, verde de variação). Os textos visíveis deixam de usar travessão como pontuação e
  "(s)": o plural segue o número (`palavra()` em `lib/sintese.ts`); "—" sozinho como valor ausente continua. Um teste
  (`src/test/semTravessao.test.ts`) barra travessão novo em texto; a única exceção é `Privacidade.tsx`, cuja redação é do mantenedor.
  "Sessão no route server" substitui "sessão direta" nos cartões do AS (`RELACAO_PTT`), o denominador de ROA no resumo é o conjunto
  anunciado, o alerta de upstream único diz a classificação do provedor sem a pontuação do método, e a página Sobre deixa de citar
  contagem fixa de CNPJs de STFC e SeAC.
  A mesma forma vale em PTT, UF, panorama técnico e de mercado, `/ixps`, CDNs, municípios, uso da Internet e localizador: resumo
  em texto, fontes e datas recolhidas e, onde há cartões, cartões antes do resumo; em `/ixps` a faixa colorida virou cartões com
  número neutro e selo. `SinteseTopo` fica sem uso (mantido) e um teste reprova uso novo.
- **Aba Numeração no AS (curvas de Hilbert por AS).** A página de AS ganha a aba "Numeração", logo após "Resumo", com a lista de prefixos
  alocados pelo Registro.br (agora aberta, não recolhida) e as curvas de Hilbert IPv6 e IPv4 do AS, que tinham saído da página. Cada curva
  tem três camadas ligáveis (alocado pelo Registro.br, visto só na tabela global, visto num PTT à escolha), quadrantes filtráveis (/8 no
  IPv4, /20 no IPv6) e a lista de prefixos como alternativa em texto. Só mostra onde os prefixos estão, não uso nem tráfego.
  O bloco "Recursos IPv4" (blocos delegados e se aparecem anunciados) também passa para Numeração, depois das curvas.
  As curvas passam a usar os mesmos mapas do panorama técnico (seletor e legenda de camada, dica ao passar o mouse, ampliação do /8 ou
  do /20), com as camadas do AS (alocado pelo Registro.br, visto na tabela global, alocado e visível, visto em PTT do IX.br) e a lista
  de prefixos da camada escolhida embaixo; o desenho próprio em canvas sai. O panorama técnico não muda: os componentes só ganham
  props opcionais, com o padrão de antes.
- **Curvas de Hilbert: decisões do mantenedor, 2026-11-27.** A curva IPv6 do AS passa a mostrar os seis blocos de RIR, como o panorama
  técnico, com os prefixos do AS coloridos (antes só os blocos onde o AS tinha prefixo: no AS22548, só o Legado). A camada "alocado e
  visível" é ciano (`COR_ALOCADO_VISIVEL`) no panorama, IPv4 e IPv6, e na curva do AS; o vermelho que a representava (e o que marca,
  nas outras camadas, o espaço alocado) sai. Três problemas herdados, no panorama e no AS: o zoom concorda o plural ("1 bloco /16",
  "2 blocos /32"); célula com dado tem opacidade mínima de 0,5 (antes 0,18 para 1 /24, quase invisível), crescente até 0,88, sem
  mudar a ordem; e o modal de zoom vira diálogo acessível (`ui/ModalAcessivel`: `role="dialog"`, foco preso, Esc fecha, foco volta).
  Os textos de selo da API não mudam.
- **Decisões de forma do mantenedor (PT-30), 2026-11-26.** Legenda dos selos com nova redação ("Fato: declarado pela fonte ou medido
  diretamente", "Inferido: deduzido de outros dados por uma regra pública; pode não corresponder à realidade", "Estimado: valor
  aproximado, obtido por amostragem ou modelo"). Faixas de distância ao PTT no painel da UF numa escala de um só tom, sem vermelho. Em
  `/privacidade`, seção 4, parênteses no lugar dos travessões, só pontuação; com isso o teste de travessão não tem mais exceção. O
  componente `SinteseTopo`, sem uso desde a replicação, sai. O AGENTS.md ganha o item "Apresentação" com as regras do PT-30.

## v2.1.3

O software ganha logotipo, em `marca/`: globo ortográfico com o sul para cima, centrado no Brasil (Natural Earth 1:110m), com uma rota
simbólica, e o nome em contorno (Lato Semibold). `arandurape-logo.svg` (com o nome) aparece no topo do README;
`arandurape-simbolo.svg` é só o globo; `arandurape-previa-social.png` (1280×640, de `gerar_previa_social.py`) é a imagem para
Settings → Social preview do GitHub, que se envia à mão. O site não muda: segue com o "A" do software ou com a marca da instância
(`instancia/marca/`). Revê a decisão da v2.0.37 de o software não ter logotipo.

## v2.1.2

`/localizador`: o subtítulo acompanha o título novo ("Escolha um ponto no Brasil e veja as redes, os provedores e os acessos de
banda larga ao redor"; era "Encontre Sistemas Autônomos próximos a uma localização no Brasil").

## v2.1.1

Mapas e localizador.
- Cabos submarinos que chegam ao Brasil em verde-mar (`#20B2AA`, era azul); os pontos de chegada passam ao cinza dos demais cabos
  (`submarineCableOther`), como contexto.
- `/localizador`: o título passa a "Localizador de Redes" (era "Localizador de ASes").

## v2.1.0

Desempenho da API: os caminhos quentes que o perfil por amostragem (py-spy, com GIL) apontou no teste de carga da instância de
teste de 2026-11-23 deixam de ser refeitos a cada pedido.
- **Histórico dos perfis** (ASN, PTT, operadora, UF): a lista de todos os eventos, ordenada, e um índice por entidade são montados uma
  vez, sob trava, e refeitos só quando muda a lista de datas ou um arquivo de eventos. Antes, cada perfil juntava e ordenava todos os
  eventos de todas as datas: metade do tempo em que a API segurava o GIL. A saída é a mesma (comparada com o algoritmo antigo).
- **Índice de operadoras** e **outorgas sem contato**: montados uma vez por data e documento carregado (eram refeitos a cada perfil
  de UF, `/meta` e consulta; ~20% do tempo com GIL).
- **Diag leve sem `sys._debugmallocstats`**: ele percorre todas as arenas segurando o GIL e, com carga ao lado, parou a API por 21 s;
  o diag leve é o que o amostrador de memória chama a cada 30 s durante o pipeline. O bloco `pymalloc` fica só no `?deep=1`.
- Resultado na instância de teste (snapshot 2026-11-22, até 200 simultâneos, só navegação web): pior requisição de 31,7 s para 1,9 s,
  pior página de 40,5 s para 1,9 s, p99 no degrau de 200 de 4,5 s para 1,5 s, nenhuma parada do `/health` acima de 3 s (eram 7).

## v2.0.42

Aba de estabilidade de `/bgp`: os ASes com mais updates BGP nas 6 semanas do gráfico de atividade, uma grade AS × semana para IPv6 e
outra para IPv4.
- **Métrica:** volume absoluto (anúncios + retiradas + mudanças de atributo) somado nas semanas, por família. É a carga na tabela, não
  a métrica por prefixo da tabela de estabilidade, e o texto da grade diz isso. Top 10 por família, parcela dos 10 no total de cada
  semana e do período, e a janela real de cada semana (sobreposição ou lacuna em relação à anterior, arquivos do coletor faltando).
- `GET /api/v1/bgp-stability/carga?weeks=&top=` (padrão 6 e 10; até 12 e 20), classe `metered` e aberta a anônimos (decisão do
  mantenedor, 2026-11-23), como o `/history?resumo=1`. Sai de alguns inteiros por AS e semana lidos na mesma passagem que monta as séries
  horárias semanais (medido: ~2,2 MiB por semana para 8.000 ASes), sem reabrir o documento de cada semana.
- MCP: `rota_estabilidade(modo="carga", weeks, limit)`.

## v2.0.41

Coletas em paralelo, uma por destino, no orçamento de memória do worker (desligado por padrão).
- **Cortesia por destino** (decisão do mantenedor, 2026-11-22): uma requisição por vez por host; hosts diferentes podem ser consultados
  ao mesmo tempo. O executor segura um lock por host (`data/ops/destinos/`) enquanto a etapa roda, em série ou em paralelo e também
  entre o pipeline e a trilha contínua. O host vem do `origem.url` das fontes; o que mais a etapa consultar vai em `destinos`
  (`fulltable_routeviews`: RouteViews e RIPE RIS).
- `arandu run --paralelo N` / `arandu continuo --paralelo N` (ou `ARANDU_PARALELO`): só rodam lado a lado as coletas puras (fontes
  `bruta`) com destino e `memoria_mb` que caiba no orçamento (`ARANDU_MEM_ORCAMENTO_MB` ou 80% do teto do contêiner); o resto roda
  sozinho, na ordem do plano, e toda etapa espera as dependências. Em simulação da coleta de 2026-11-22 (durações medidas, sem Alice
  e RDAP), 4 em paralelo com o worker de 3g levam 5,9 h contra 7,5 h em série; o ganho cresce à medida que as coletas curtas
  ganham `memoria_mb` (`arandu memoria`).

## v2.0.40

`GET /api/v1/query/{collection}`: o `corpo` aceita até 5.120 caracteres (era 8.192), e o site passa a usar o GET até 5.000
caracteres codificados (era 6.000); acima disso, o POST, como antes. Com caracteres de 4 bytes, 8.192 caracteres viravam uma URL de
~96 KiB: o fuzz do T4 falhava às vezes porque o cliente HTTP recusava montar a URL (não era 5xx da API).

## v2.0.39

Trilha contínua: as coletas em rodízio diário com orçamento saem do pipeline.
- `continua: true` no catálogo (hoje `ixbr_alice`, `ixbr_alice_rotas` e `rdap_contatos`): a etapa roda em `arandu continuo`, à parte, com
  lock (`data/ops/arandu-continuo.lock`) e relatório (`data/ops/runs/continuo/`) próprios. No pipeline ela não coleta: restaura do
  armazém a última versão registrada (o relatório diz de quando) e quem depende dela roda como antes. Em 2026-11-22 o Alice levou 7 h
  (o orçamento dele) e o RDAP até 3 h dentro do pipeline, que passou de 16 h.
- `scripts/arandu-continuo.sh` roda a trilha no serviço novo `worker_continuo` (herda o worker, teto `WORKER_CONTINUO_MEM_LIMIT`, padrão
  1g) e alerta em caso de falha. O `instalar.sh` agenda às 18:00 UTC, para terminar antes do pipeline das 04:00.
- `gc` e compactação recusam rodar com qualquer das duas trilhas em andamento; `doctor` mostra os dois locks.
- **Implantação em instância existente:** traga o `worker_continuo` do `docker-compose.exemplo.yml` para o `docker-compose.yml` local e
  acrescente ao crontab a linha da trilha contínua (a do `instalar.sh`); sem isso as três coletas param, porque o pipeline já não as roda.

## v2.0.38

Memória medida por etapa do pipeline, base para rodar coletas em paralelo.
- O executor espera o subprocesso de cada etapa com `wait4` e grava no relatório o `pico_mem_mb` (maior RSS entre as tentativas).
- `memoria_mb` no catálogo (etapa ou `etapa:` da fonte): o pico com folga. Declarado para as coletas longas a partir do amostrador
  de memória das execuções de 2026-11-21 e 22 (contêiner do worker, a cada 30 s), com 25% de folga; a medição por `wait4` o refina.
- `arandu memoria`: pico e duração máximos por etapa nos relatórios gravados, contra o declarado.

## v2.0.37

Sai a pasta `logos/`: sobra de antes da decisão de que o software não tem logotipo (o símbolo e os ícones são da instância,
em `instancia/marca/`, fora do git). Nada a usava.

## v2.0.36

Espelho do `data/`: os bancos de `auth/` (contas, chaves de MCP, sessões) chegam ao destino sem permissão para outros
usuários do host (saíam 0664 do diretório de preparo).

## v2.0.35

Espelho do `data/`: o sal do log de uso (`ops/usage/.salt-*`) fica de fora. Só o contêiner da API o lê, então o rsync
falhava nele e o espelho parava antes de `auth/` e dos manifestos; e cada instância usa o seu.

## v2.0.34

Espelho do `data/` em outra instância (um ambiente de teste com os dados da produção, sem coletor).
- `scripts/espelhar-dados.sh`: rsync sobre SSH para `ESPELHO_DESTINO`, só quando há snapshot publicado novo (`--forcar` para a
  primeira carga). Vai tudo menos `raw/`; dele, só os `ixbr_members.json`, que a API ainda lê em tempo de execução, como lê
  `normalized/`. Os SQLite de `auth/` vão por backup consistente e os `-wal`/`-shm` antigos do destino saem antes; os manifestos vão
  por último, então o destino nunca vê um snapshot pela metade. O destino é sobrescrito a cada cópia.

## v2.0.33

Consulta genérica também por GET, cacheável: as perguntas prontas da página inicial deixam de recalcular a cada visita.
- `GET /api/v1/query/{collection}?corpo=<JSON>&date=`: o mesmo motor, os mesmos limites (custo 3 no orçamento, `LIMIT_QUERY`) e a
  mesma prévia anônima do `POST`. Com `date` de snapshot publicado sai `immutable`, e o nginx e o cache de respostas da API a guardam.
  Continua `metered` e fora do cache da Cloudflare, como o POST: a borda não passa pelo gate. O POST continua para corpos grandes.
- O site passa a consultar por GET (`queryColecao`, `frontend/src/services/api.ts`), com recurso ao POST acima de 6.000 caracteres na
  URL. Na página inicial eram quatro POST por visitante novo, de cerca de 0,45 s de CPU cada, e no teste de carga de 2026-11-21 eles
  concentraram os travamentos de 12 a 32 s na chegada de visitantes novos (656 pedidos, 2,7 s em média no servidor).
- **Política de acesso:** a URL guardada não pode depender de quem pede. O `classify` lê o `corpo` do GET: `limit` acima da prévia,
  `page` > 1, `offset` e histórico fora dos snapshots atuais (`COLECOES_HISTORICO`, agora definido em `access_policy`) tornam a URL inteira
  `login` (401 ao anônimo e `private, no-store` a quem tem acesso), como nas demais rotas.

## v2.0.32

Correção da 2.0.31: a razão social lida de `normalized/` volta a sair com o CPF mascarado.
- A API lê `normalized/<data>/summary/geo_orgs.json.gz`, que não passa pela máscara da publicação, e a 2.0.31 tinha tirado a máscara
  dessa leitura também: o nome alternativo do AS (`alt_names`, da razão social da Receita) saía com o CPF de empresário individual ou MEI
  em 9 perfis de AS na produção (varredura de 2026-11-21). A máscara volta nessa leitura (um arquivo por data, guardado em memória);
  as demais leituras de `normalized/` só usam coordenadas, prefixos ou contatos (estes, só com login).

## v2.0.32

Tabelas ordenáveis por coluna em todo o site e rótulos da home conforme o que é contado.
- **Home:** "ASes brasileiros na tabela de roteamento" contava os ASes alocados ao Brasil (delegated do LACNIC, via Registro.br),
  apareçam ou não na tabela global: passa a "ASes brasileiros alocados". "ASes BR que anunciam IPv6" contava também IPv6 só alocado:
  passa a "com IPv6 alocado ou anunciado". O cartão "sem RPKI" filtra prefixo IPv6 na tabela global (o número muda). O destaque de
  municípios com operadora dominante abre `/municipios?ordem=hhi` (o localizador não mostra esse dado) e diz o critério da consulta.
- **Tabelas:** `lib/ordenacao.ts` e `ThOrdenavel` dão às tabelas montadas à mão o comportamento do `TabelaDados` (botão, `aria-sort`,
  seta). A lista inteira é ordenada antes do corte da versão reduzida. Onde a API já ordena, o cabeçalho usa o parâmetro dela.
- `GET /acessos/divergencias/scm` aceita `ordem` e `asc`, aplicados à lista inteira antes do `limit` (tabela "Maiores divergências
  entre APNIC e Anatel").
- Ficam sem ordenação, de propósito: fichas chave/valor, matrizes transpostas, séries curtas, as tabelas marcadas "ordem alfabética, sem
  ranking" (qualidade, multas, Consumidor.gov.br) e as listas que a API ou o pipeline entregam cortadas sem parâmetro de ordem.

## v2.0.31

CPF embutido na razão social de empresário individual e MEI mascarado na publicação, não mais na leitura da API.
- `core.cpf.mascarar_snapshot` mascara os campos de nome de todos os artefatos do snapshot (JSON, GeoJSON, `.json.gz` e as entradas do
  `asns.zip` do formato compactado) no fechamento do snapshot (`publish/coleta_checks.refresh_manifest`, antes dos checksums), regravando
  só o que muda e no mesmo formato. Idempotente.
- A API deixa de percorrer cada documento lido atrás de CPF (`Store`, repositórios, mapas de outorgas, Hilbert, consultas). No perfil da
  produção de 2026-11-21 isso custava cerca de 280 s de CPU em 80 perfis: o `bgp_stability.json` (40 a 47 MB, com nomes de titular)
  passava inteiro pela máscara em cada uma das 6 semanas da série. O sócio pessoa física dos grupos societários continua retirado na
  leitura (`sem_socios_pessoa_fisica`), como antes.
- **Snapshots já publicados:** `scripts/mascarar_cpf_publicados.py DATA_DIR [--aplicar]` aplica a máscara uma vez (simula sem
  `--aplicar`), guarda os originais, atualiza os checksums dos caminhos alterados e registra em `correcoes` no manifesto. **Precisa rodar
  na implantação desta versão**, antes de reiniciar a API: sem ele, os snapshots antigos passam a servir o CPF sem máscara. Na cópia de
  2026-11-15 e 2026-11-08: 47 e 37 arquivos, cerca de 50 s por snapshot.

## v2.0.30

Guarda de memória (`api/memoria.py`) que não disputa a CPU com os pedidos nem derruba a API perto do teto.
- **Varre os caches só quando há motivo.** A cada 5 s ela só lê a memória do cgroup. Percorre as chaves quando uma consulta a data não
  residente termina, quando sai snapshot novo, sob pressão, ou a cada `API_MEMORIA_VARREDURA_S` (600). Antes varria tudo a cada 5 s: no
  perfil da produção foram 763 mil `data_da_chave` em 13 minutos, numa thread que segurava o GIL enquanto os pedidos esperavam.
- **Histerese:** depois de um expurgo por pressão, outro só após `API_MEMORIA_REPETIR_S` (60) ou se o uso subir mais
  `API_MEMORIA_REPETIR_PCT` (5) pontos. O Python nem sempre devolve ao sistema a memória solta, e a guarda repetia o expurgo sem ganho
  ("5827 → 5841 MiB"), jogando fora os caches a cada passada.
- **Crítico menos destrutivo:** a 90% esvazia o cache de respostas prontas (recalculável) e mantém só a data mais recente; o expurgo
  total, inclusive da data mais recente, passa a `API_MEMORIA_TOTAL_PCT` (95) e no máximo uma vez a cada `API_MEMORIA_TOTAL_INTERVALO_S`
  (300). No teste de carga de 2026-11-21 o expurgo total a 91% fez cada pedido recarregar as bases sob carga e a API parou de responder.
- As semanas protegidas da série de estabilidade BGP são calculadas uma vez por conjunto de datas residentes, não a cada passada.
- `LatestResponseCache.esvaziar()` troca o mapeamento inteiro (seguro entre threads); o MCP recebe a mesma guarda.

## v2.0.29

Lista de snapshots guardada em memória (`Store.list_snapshots`).
- Era chamada várias vezes por pedido (política de acesso, middleware, estabilidade BGP, guarda de memória) e cada chamada fazia dois `stat`
  por data publicada. Com 19 datas na produção e a API ocupada, cada `stat` esperava o GIL na volta: a lista custou em média 0,65 s por
  chamada no perfil medido em 2026-11-21, e o mesmo código levava 81 s para aquecer os perfis com 2 datas e 687 s com 19.
- Agora custa um `stat` de `published/`. Data nova, removida ou renomeada muda o diretório; um diretório ainda sem `manifest.json`
  (publicação em andamento) é reconferido a cada chamada até ganhá-lo (`tests/unit/test_store_snapshots.py`).

## v2.0.28

Tabelas que ordenavam só a parte que estava na tela.
- **Estabilidade BGP (`/bgp?aba=estabilidade`):** a tabela recolhida tinha os 10 primeiros por instabilidade combinada; ordenar por v4
  reordenava esses 10 e os mais instáveis em IPv4 não apareciam. `/bgp-stability/overview` passa a trazer, para cada coluna e sentido,
  os 10 primeiros da lista inteira de severidade média ou maior (`ordens`, `as_stability_ordens`), e a tabela mostra essas linhas.
- **AS_PATH (prepending e diversidade de upstreams, `/bgp`):** o pipeline guardava os 20 (50) primeiros por uma coluna só, e a tabela,
  que abre ordenada por excesso médio, ordenava esse corte: no snapshot de 2026-11-15 o AS com maior excesso médio (AS53051, 17,0) estava
  fora. O pipeline passa a guardar os N primeiros e os N últimos de cada coluna ordenável. O snapshot de 2026-11-15 foi **corrigido no
  lugar**, por decisão do mantenedor: só essas duas listas, recalculadas dos mesmos dados (conferido que a regra antiga reproduz o
  publicado), com os originais guardados e o registro em `correcoes` no manifesto. O front pede `/routing-analysis` com `esquema=2`,
  para não servir a versão antiga guardada como `immutable`.
- **Explorar:** com só uma página do resultado (mais de uma página, ou o limite do anônimo), o clique no cabeçalho refaz a consulta com
  `sort` no servidor; com o resultado inteiro, segue ordenando na tabela. `TabelaDados` ganha o modo `ordemServidor`.

## v2.0.27

CI e dependências.
- **Nenhum commit com `Co-Authored-By`** (`tests/unit/test_sem_coautor.py`): percorre o histórico inteiro (o job `python` passa a fazer o
  checkout com `fetch-depth: 0`). A única exceção é o commit da 2.0.1 (`bc4e351`), já publicado com a linha.
- Actions atualizadas (fixadas por SHA, conferido contra a tag): checkout 7.0.1, setup-python 7.1.0, setup-node 7.1.0, upload-artifact
  7.0.2. As anteriores usavam Node.js 20, que o GitHub está descontinuando nos runners.
- `dependabot.yml`: mensal, sem versões maiores (migração é feita à mão) e sem trocar o Python da imagem (só correções e digest); no npm,
  até 5 PRs abertos. Os 21 PRs da primeira execução foram fechados.

## v2.0.26

**A série histórica dos perfis não chega mais a anônimos pelo cache.** O bloco `historico` dos perfis de AS, PTT, operadora e UF mudava
conforme quem pedia (série inteira com login, 2 datas sem), mas o nginx e o cache de bytes da API guardam por URL. O aquecimento da API
monta os perfis com acesso completo, e a partir dali todo anônimo recebia a série inteira; quando o anônimo chegava primeiro, o usuário
logado recebia a série curta e o aviso para entrar.
- `include=historico` traz sempre só os 2 snapshots atuais, para todos; `include=historico_completo` traz a série inteira e é da classe
  `login` (401 ao anônimo, `private, no-store`). A resposta depende só da URL.
- O front pede `historico_completo` quando há usuário (login ou IP na allowlist), com a variante na chave do cache do React Query.
- Testes: mesma URL dá o mesmo bloco para anônimo e logado; `historico_completo` exige login nos quatro perfis.

## v2.0.25

Configuração de memória que não chegava aos contêineres. O `docker-compose.prod.yml` só vale com `PROD_OVERRIDES=true`, e era só ele que
repassava `MALLOC_ARENA_MAX` e os tamanhos de cache: no servidor, a API e o MCP rodavam sem limite de arenas do glibc e a API com os
tamanhos padrão do código, embora o `.env` definisse outros.
- `docker-compose.exemplo.yml`: `MALLOC_ARENA_MAX` (padrão 2) na API e no MCP; `LATEST_CACHE_MAX_BYTES`, `LATEST_CACHE_MAX_ENTRY_BYTES` e
  `STORE_*_LRU` na API, com os padrões do código. Teste em `tests/unit/test_ops_scripts.py`.
- `.env.example` documenta as variáveis.

## v2.0.25

O que o usuário vê fala do site, não do software. O Arandurapé é o software; a instância tem nome, contato e marca próprios.
- **Marca da instância fora do repositório.** O símbolo do cabeçalho e da tela de login e os ícones da aba (`favicon.svg`, `favicon.ico`)
  vêm de `instancia/marca/` (ignorada pelo git, só o README é versionado), copiada sobre `frontend/public/` no `Dockerfile.frontend`.
  Sem ela, o site sai com o símbolo padrão do software, um "A". Saem do git `arandu-mark.svg` (agora `marca.svg`) e `arandu-logo.svg`.
- **Página de fontes:** o `catalogo.json` é gerado com o nome do software e passa por `comIdentidade` (`frontend/src/lib/site.ts`, o mesmo
  marcador de `core/site.py`) antes de ser exibido. A nota da tabela curada de marcas deixa de trazer um e-mail fixo e aponta o contato do
  site.
- **User-Agent:** os coletores do RouteViews/RIPE RIS, da Receita (sócios), dos grupos de sócios, a sondagem do Shodan e a medição de
  RDAP usavam `arandurape/1.0` sem o endereço da instância; passam a usar `core.site.USER_AGENT` (`arandurape/<versão> (+SITE_URL)`).
- Implantação: antes do build, ponha a marca da instância em `instancia/marca/` (`marca.svg`, `favicon.svg`, `favicon.ico`); sem isso o
  site sai com o "A".

## v2.0.24

Contatos no MCP, com a cota do site.
- Tools `asn_contatos` (um AS) e `operadora_contatos` (um CNPJ, `servico=fixa|movel`), só com chave de MCP. A cobrança é da API, numa rota
  interna (`POST /internal/contatos`, com `X-Internal-Token`): mesmo custo (1 por AS revelado; a operadora custa o número de ASNs do CNPJ),
  mesmos tetos por conta, por rede e global, mesma suspensão e o mesmo registro de `api/contatos_cota.py`. A cota da conta é uma só no site
  e no MCP. O MCP não grava em `data/auth/`.
- Sem chave, a tool responde sem contato (`contatos_liberados: false`) e diz como obter a chave.
- As rotas `/asns/{asn}/contacts`, `/acessos/operadora/{cnpj}/contacts` e `/acessos-movel/…` passam a montar a lista pelas mesmas funções
  da rota interna (`montar_contatos_asn`, `montar_contatos_operadora`); a resposta delas não muda.
- Pós-implantação: além das duas tools, nenhuma tool de contato; `asn_contatos` chamada sem chave não pode devolver contato.
- Instruções do MCP (regra 9), descrições, matriz de cobertura e AGENTS.md atualizados.

## v2.0.23

O nome do site no lugar do nome do software nas respostas. Os artefatos do pipeline trazem textos como "n_redes conta os vínculos que o
Arandurapé coletou" (limitações, metodologia, fonte), e o cliente do MCP repetia o nome do software nas respostas e nas citações.
- API: a classe de resposta padrão (`api/respostas.py`) troca o nome nos corpos JSON; o teste é feito em bytes e o corpo sem o nome não é
  tocado. As rotas que montam a resposta à mão (`/asns/{asn}`, `/ixps/{code}`) usam a mesma classe.
- MCP: o resultado de cada tool, resource e template passa por `com_identidade_nos_dados` (`_com_identidade` em `mcp_server/app.py`); só
  valores de texto mudam, nunca chaves. As descrições já passavam por `com_identidade`.
- Os snapshots publicados não mudam: a troca é na saída.

## v2.0.22

Correções da terceira varredura do site, em 20/11/2026, sobre a 2.0.21.
- **A busca não sai mais `immutable`.** Com `?date=` de snapshot publicado, `/busca` era guardada por um ano no navegador, no nginx e na
  borda, mas o índice muda com o código: quem buscou "Núcleo de Informação" antes da 2.0.19 continuava a ver "nada encontrado", embora a
  API já achasse os ASes do NIC.br. A rota passa a `public, max-age=300` (`_SAIDA_DEPENDE_DO_CODIGO` em `api/main.py`). O front acrescenta
  `esquema=2` à URL da busca, o que descarta o que já estava guardado.
- `esquema` passa a ser parâmetro global no middleware de parâmetros desconhecidos, junto com `date`, `v` e `opcional`. Antes, o
  `esquema` de `/brasil/indicadores` era registrado como desconhecido e daria 400 com `API_PARAMETROS_DESCONHECIDOS=rejeitar`.
- Identificadores inválidos não chegam mais à API com erro: `/instalacao/{id}` valida o id e pede `?opcional=1` (204 no lugar de 404).
  `/relatorio/operadora/{cnpj}` e `/relatorio/asn/{asn}` validam o identificador antes da chamada, que dava 400 ou 422.

## v2.0.21

Teto de memória na API e no MCP, pré-carga do MCP e tetos dos contêineres (trabalho medido num ambiente de teste em 18/11/2026 que
ficou fora do recorte público). Os caches do `Store` eram dicionários por data sem expurgo: a API sobe a ~4,2 GiB e chegou a 5,2 GiB
de 6 GiB depois de 4 h em produção; consultar a fundo uma data antiga somava ~1,7 GiB que nunca voltava, e duas levavam ao OOM.
- `api/memoria.py`: ficam em memória a data mais recente e as `*_DATAS_EXTRAS` consultadas por último (API: 1, a anterior, usada nas
  comparações; MCP: 0). A data antiga é **sempre servida**: protegida do expurgo enquanto a consulta roda e expurgada ao fim dela. Os
  caches são achados por introspecção (mapeamentos do `Store`, dos serviços e repositórios dele, e os de nome "cache" nos módulos
  `api.*`) e a data sai da chave; as semanas da série de estabilidade BGP das datas residentes ficam.
- Guarda (a cada 5 s e depois de cada consulta a data não residente): memória anônima do cgroup acima de 80% do teto expurga tudo menos a
  data mais recente; acima de 90%, tudo, relido sob demanda. Nada recebe 503. `API_MEMORIA=0` / `MCP_MEMORIA=0` desligam; estado da API
  em `/api/v1/internal/diag` (`memoria`).
- MCP: a guarda roda numa thread e cada tool executa dentro de `usando(date)`. Pré-carga (`mcp_server/precarga.py`, `MCP_PRECARGA`,
  ligada): percorre as tools da data mais recente ao subir **e a cada snapshot novo**, com as funções originais, fora do log de uso e da
  prévia, com pausa curta entre chamadas para não prender o GIL; `start_period` do healthcheck do MCP passa a 300 s. Teste: os nomes
  chamados existem entre as tools registradas (um nome ausente seria pulado em silêncio).
- Medido com a guarda (ambiente de teste): API com teto de 6 GiB e três datas antigas a fundo terminou em 79% do teto; MCP com teto de
  5 GiB chegou a 91% com uma data antiga, a guarda expurgou tudo e a varredura seguiu em ~1,8 GiB, sem OOM. Data antiga não residente
  relê o disco a cada consulta (1.029 s contra 308 s para a mesma bateria). Restam ~2 GiB que não saem com o expurgo, a investigar.
- Tetos padrão nos três compose (exemplo, `.prod.yml`, `.no-nginx.yml`): API 6g, MCP 5g (era 1g fixo), worker 3g, Routinator 3g (nunca
  junto com o worker), frontend 512m, swap igual ao teto. `.prod.yml` e `.no-nginx.yml` tinham tetos fixos que sobrescreviam o base (API
  9G e 3G, MCP 2G, worker 1G e 2G, frontend 64M). Quem define `WORKER_MEM_LIMIT` ou `ROUTINATOR_MEM_LIMIT` no `.env` segue com o seu valor.

## v2.0.20

Duas correções do RPKI que ficaram fora do recorte público.
- **`scripts/rpki-avulso.sh` recusa saída incompleta.** Em 19/11/2026 o snapshot RRDP do RIPE NCC caiu com "Connection reset by peer"; o
  Routinator saiu 0 com JSON válido e 659 mil ROAs em vez de 1,04 milhão, e o script, que só exigia algum ROA, trocou o arquivo bom.
  Publicado, todo prefixo coberto só pelo RIPE apareceria como "sem ROA". Agora exige ROA de cada TA de `RPKI_TAS` (padrão: as cinco
  RIRs) e ao menos `RPKI_MIN_FRACAO` (0,9) dos ROAs do arquivo anterior; senão preserva o anterior e sai 1 (a etapa RPKI falha e o alerta
  avisa). `--aceitar` pula as conferências numa queda legítima, conferida à mão.
- **Routinator no bridge padrão do Docker**, sem a rede `rpki` própria: uma rede nova pega a próxima /16 livre do pool do Docker, e uma
  delas cobriu a VPN de administração de um host, que ficou inalcançável a cada subida do Docker. Teste: o compose de exemplo só define
  a rede `arandurape`. Quem já tem a rede: `docker network rm <projeto>_rpki` depois de atualizar a cópia local do compose.

## v2.0.19

Correções da varredura anônima e logada de 20/11/2026.

- **Cache na borda das rotas medidas:** a Cloudflare guardava respostas `metered` com `?date=` (`public, immutable`) e as entregava a
  quem já tinha esgotado o orçamento anônimo. Rota `metered` sai agora com `Cloudflare-CDN-Cache-Control: no-store`; navegador e nginx
  (que fica depois do gate) seguem guardando. Exceção declarada em `access_policy._BORDA_PATTERNS`: camadas de mapa e agregados
  globais ou por PTT (`/map/*`, mapas de acessos, território e qualidade, `/ixps/{code}/geo` e `hilbert`, `/bgp-stability`,
  `/bgp-stability/history`, `/bgp-stability/overview`, `/routing-analysis`), pesados (até 23 MB e 60 s medidos) e com poucas URLs;
  aceita-se entregá-los mesmo com o orçamento esgotado. `X-Anon-Limit-Reached: false` deixou de sair (só o `true` tem efeito).
- `/grupo/:id`, `/municipios` e a versão antiga de `/visao-geral` passam pelo `ProtectedRoute`; `/grupo/:id` mostra o painel de login
  em vez de "Grupo não encontrado" quando o motivo é o limite. Teste reprova rota `metered` do SPA sem `<P>`.
- React Query não repete 4xx nem erro de política (cada repetição era outra linha vermelha no console).
- Identificador inválido não chama a API (`/asn/abc`, ASN fora de 1–4294967295, código de PTT fora do formato); perfil de AS, PTT, PTT
  externo e grupo pedem `?opcional=1` (204 em vez de 404). O pré-aquecimento dos perfis acompanha a URL nova.
- `/visao-geral` deixa de ser página de entrada: é alias de `/panorama/tecnico`, que é `metered`.
- O relógio anônimo para no limite (cada `/auth/me` seguia somando tempo de quem só via o painel de login).
- `/ases`: ASN, nome e CNPJ ordenam em ordem crescente no primeiro clique; as páginas que exigem login levam cadeado. Busca: AS também
  pela razão social e nome fantasia da Receita (o nome do Registro.br vem abreviado).

## v2.0.18

- A aba "Grupos econômicos" do Panorama de mercado listava CNPJs com vários ASNs: uma só empresa que separa serviços, regiões ou redes
  incorporadas, não um grupo econômico (esses estão em `/grupos`). Virou a seção "Organizações com vários ASNs" no fim de `/ases`;
  `/panorama/mercado?aba=grupos` redireciona para `/ases?secao=organizacoes`.
- API: `GET /asns/by-organization` substitui `GET /asns/economic-groups`, que segue como alias (`Deprecation` + `Link`). Mesma resposta.
- Em `/ases` a seção é um bloco degradável (rota `metered`): com o orçamento anônimo esgotado não chama a API e avisa.

## v2.0.17

- Zero erros de console na varredura de obint.com.br (≈220 páginas, abas clicadas, visitante anônimo): `/perfil` sem login chamava
  `/auth/perfil` e recebia 401; agora só consulta com sessão de conta.
- Mapa de `/ixps`: `map/asns` e `map/prefixes` (bloco degradável) não são chamados com o orçamento anônimo esgotado, como na home.

## v2.0.16

- CSP libera o beacon do Cloudflare Web Analytics (`static.cloudflareinsights.com` em `script-src`, `cloudflareinsights.com` em
  `connect-src`), que a borda injeta e o navegador bloqueava com erro no console. A política de privacidade (seção 4) cita a medição.

## v2.0.15

- Página inicial: com o tempo de uso anônimo das páginas avançadas esgotado, os blocos opcionais (destaques, cartões de resposta,
  "o que mudou", PTT mais próximo) chamavam assim mesmo `/query/*` e `/map/pix` e recebiam 403, que o navegador registra no console
  mesmo tratado. Agora esperam o `/auth/me` e, com o orçamento esgotado, não chamam a API e mostram o mesmo aviso de login.

## v2.0.14

- Comparação de PTTs: o AS65000 (privado) e o AS270382 (sem registro no snapshot) vinham com link para `/asn/{asn}`, que dava 404.
  O cadastro do IX.br (dashboard.ix.br) traz ASNs privados e ASNs sem documento; `GET /ixp-compare/members` ganhou `has_detail` e a
  tabela só cria o link quando a página existe, indicando a faixa (RFC 6996, 5398, 6793, 7300, 7607) ou "sem registro no snapshot".
- A página explica a fonte dos conjuntos: o cadastro de cada PTT, que inclui quem só troca tráfego bilateral, enquanto a página do AS
  mostra a presença observada no BGP.
- Tabela de participantes com blocos IPv6 antes de IPv4, como o CSV.

## v2.0.13

- Pipeline diário às 04:00 UTC (1h em Brasília) em vez de 12:00 UTC (9h): a coleta e a publicação pesam na API e no disco e
  ficavam no começo do horário de uso. Padrão de `INSTALAR_HORA_PIPELINE` no `instalar.sh` e exemplos do cron; quem já instalou
  ajusta a linha no `crontab -e`.

## v2.0.12

- `/security.txt` redirecionava para `http://<host>:8080/.well-known/security.txt`: atrás do túnel o nginx escuta em 8080 e em HTTP,
  e o `return 301` absoluto levava a porta e o esquema internos. `absolute_redirect off` no `server` do nginx do frontend: vale também
  para os redirecionamentos que o nginx gera sozinho.

## v2.0.11

- Mapa Explorer: as camadas "Prefixos IPv4/IPv6 do PTT" (`prefixos_ix_v4|v6`) e o recorte `near_ix` davam 500 desde a 2.0.0
  (`'Store' object has no attribute '_ixp_geo_prefixes'`): o serviço do mapa pedia ao `Store` dois métodos do serviço de
  geolocalização que não eram delegados. O teste de vazamento do T4 pulava respostas que não eram 200 e não via; teste novo exige 200.
- Mapa Explorer abre com cabos submarinos e enlaces terrestres ligados, como os PIX.
- Cabos submarinos: `#3A5FCD` para os que tocam o Brasil e `#607B8B` para os demais (o marinho e o cinza 70% da 2.0.9 ficaram
  pesados e parecidos).

## v2.0.10

- MCP: toda tool anotada como só leitura (`readOnlyHint: true`, `destructiveHint: false`, `idempotentHint: true`,
  `openWorldHint: false`, anotações de tool da especificação do MCP). Antes nenhuma tinha anotação, e clientes que pedem confirmação
  antes de uma tool sem `readOnlyHint`, ou a tratam como ação de escrita, pediam a cada chamada. Fica no servidor (`add_tool` de
  `mcp_server/contexto.py`): vale para as tools decoradas, os aliases e as geradas das capacidades. Teste em T5.

## v2.0.9

- `config/pix.yaml`: coordenadas aproximadas para os PIX NICNET (Cravinhos) e CLIENT.CO (Ribeirão Preto), que o IX.br e o PeeringDB
  publicam sem coordenadas: a rua do endereço no OpenStreetMap (sem o número; ruas de ~0,3 e ~0,75 km). Sem lat/lon o PIX não
  aparecia no mapa.
- Mapa: cabos submarinos que tocam o Brasil em azul-marinho (blue-950) e os demais em cinza 70% (`#4d4d4d`).

## v2.0.8

- `/.well-known/security.txt` (RFC 9116), gerado pela API: `Contact` com o novo `SITE_CONTATO_SEGURANCA` (padrão `SITE_CONTATO`),
  `Expires` a 180 dias de cada resposta, `Preferred-Languages` e `Canonical`. `/security.txt` redireciona para lá; o resto de
  `/.well-known/` passa a dar 404 (antes o SPA respondia 200 com o HTML). Quem tem `docker-compose.yml` local acrescenta
  `SITE_CONTATO_SEGURANCA` ao ambiente da api, como no exemplo.
- `robots.txt`: busca e uso na resposta de IA liberados, treino não (`Content-Signal: search=yes, ai-input=yes, ai-train=no`, proposta
  da Cloudflare; os robôs de treino conhecidos barrados pelo nome). Os agentes que buscam a pedido de uma pessoa (ChatGPT-User,
  Claude-User, Perplexity-User, MistralAI-User) podem consultar a API e o MCP; os demais robôs seguem fora de `/api/`, exceto o
  OpenAPI e o Swagger.
- `llms.txt` com uma seção para agentes de IA (MCP e API anônimos com prévia, citar a data do snapshot, sem treino) e `<noscript>`
  no `index.html` apontando para eles: sem JavaScript as páginas chegavam vazias.

## v2.0.7

- `products.mapas_prefixos.ixp_prefixos` deixa de tratar `normalized/{data}/summary` como PTT: lá ficam as rotas de todos os PTTs
  juntos (1,2 milhão de prefixos IPv4 em 2026-11-15), o que custava ~46 s por data e gerava `summary-v4|v6.json.gz` que nenhuma
  rota lê.

## v2.0.6

- Camadas de prefixos dos PTTs no mapa (`/ixps/{code}/geo?layer=prefixes_v4|prefixes_v6`) pré-calculadas pelo passo `mapas_geo`
  em `published/{data}/maps/ixp_prefixes/{ptt}-{v4|v6}.json.gz`. Na API o cálculo levava mais de 2 min no IPv4 do SP (85 s no
  IPv6) na primeira chamada depois de cada reinício: a Cloudflare corta em 100 s (524) e o GIL atrasava as demais rotas. A API lê
  o arquivo e só calcula quando ele falta ou quando o Mapa Explorer filtra por AS no caminho. O cálculo saiu de
  `api/services/geolocalizacao.py` para `core/ixp_geo.py`, usado pelos dois lados; no pipeline a geolocalização de cada bloco é
  compartilhada entre os PTTs da data.
- Snapshots já publicados (aditivo, fora do manifesto, como o `.col`):
  `python -m products.mapas_prefixos.ixp_prefixos --date AAAA-MM-DD [--ixp sp] [--force]`.
- `restart-safe.sh` aquece as camadas de prefixos dos PTTs maiores (`WARM_IXP_GEO`, padrão `sp rj ce pr df rs`).

## v2.0.5

- Chave de MCP com o prefixo da instância: `<SITE_MCP_ESQUEMA>_mcp_<id>_<segredo>` (ex.: `obint_mcp_…`), antes fixo em `arandu_mcp_`. A
  verificação aceita qualquer esquema no formato, porque quem autentica é o id com o HMAC do segredo: as chaves já emitidas
  (`arandu_mcp_…`) continuam válidas. Formato e prefixo ficam em `core/site.py`, usados pela API, pelo servidor MCP e pelo perfil.
- Mapa: cabos submarinos um tom mais escuros (sky-400 para os que tocam o Brasil, violet-400 para os demais).

## v2.0.4

`config/pix.yaml` conferido com as páginas de adesão do IX.br e com o PeeringDB (2026-11-20):

- novos: BR.Digital RJO3 e Takoda (Rio de Janeiro), NICNET (Cravinhos) e CLIENT.CO (Ribeirão Preto), BR.Digital (Campo Grande);
- fora: PIX com ativações congeladas no IX.br (FAEPA, CELEPAR, VERO São Paulo, GVT-JD) e SYGO e NEXFIBRA (Porto Alegre), que
  saíram do IX.br;
- nomes atuais: GNS Fibra (antes Giganetsul), IRED TELECOM (antes PERSIS TELECOM), TMKNET (antes ZAP TELECOM);
- endereço do PIX SAMM do Rio (Internexa, Teleporto) e da BR.Digital de Florianópolis (Av. Patrício Caldeira de Andrada).

## v2.0.3

- `restart-safe.sh` reconstrói as imagens pelo compose (`docker compose build --no-cache api|frontend`) em vez de `docker build`.
  Sem o compose, os build args do `.env` não chegavam ao frontend e a cada implantação a interface voltava ao nome, à descrição e
  aos contatos padrão (`SITE_*`). Teste novo em `tests/unit/test_ops_scripts.py`.

## v2.0.2

Contatos e descrição do site configuráveis pelo `.env`, como o nome.

- `SITE_CONTATO_PRIVACIDADE` (novo): e-mail do controlador mostrado na Privacidade (3 lugares) e no Uso aceitável, antes fixo no
  código; padrão `lgpd@internetbitabit.com.br`. Repassado no `docker-compose.exemplo.yml` (api, mcp, worker e build do frontend) e no
  `Dockerfile.frontend`. **Quem já tem um `docker-compose.yml` local precisa acrescentar as mesmas linhas.**
- A descrição do `index.html` (`description` e `og:description`) e o `llms.txt` usam `SITE_NOME_EXTENSO` em vez do texto fixo.
- Teste: nenhum e-mail fixo no frontend fora dos padrões de `lib/site.ts`.

## v2.0.1

Implantação com **Docker rootless**. Os scripts detectam o modo do daemon e funcionam nos dois casos; com Docker com root o
comportamento não muda.

- `scripts/lib-docker.sh` (novo): `docker_rootless` e `docker_host_atual`.
- `scripts/preparar-dados-api-sem-root.sh`: no rootless, roda sem sudo e faz o `chown 1001:0` de dentro de um contêiner da imagem da
  API (o UID 1001 do contêiner é outro UID no host; um `chown` no host entregaria `data/auth` a outra conta). `--uid` só numérico.
- `scripts/instalar.sh`: no rootless, nada pede sudo; as permissões de `data/` são acertadas depois do build e antes de subir; as linhas
  do cron levam o `DOCKER_HOST`; o vigia vai para o systemd do usuário; confere linger e delegação dos controladores do cgroup (o aviso
  de `userland-proxy` só vale com root).
- `restart-safe.sh`: no rootless, roda como o usuário do serviço e recusa sudo; com root, exige root como antes.
- `docker/systemd/user/arandurape-vigia.{service,timer}` (novos): vigia no systemd do usuário, com o socket do rootless.
- Documentação: seção 9 do `recomendacoes-deployment.md`, README, guia, `AGENTS.md` e `.env.example`.

## v2.0.0

Primeira versão pública do projeto.
