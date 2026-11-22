# Notas de versão

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
