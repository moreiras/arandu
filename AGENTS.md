# AGENTS.md — regras de trabalho no código (pessoas e agentes de programação)

Este arquivo orienta quem trabalha no código do Arandurapé. Regras que **não podem** quebrar estão em testes automatizados; aqui
ficam as que os testes não cobrem. Mantenha curto: só o que não se deduz lendo o código. A arquitetura e as diretrizes de projeto,
com o porquê de cada uma, estão no [guia do desenvolvedor](guia-do-desenvolvedor.md).

## 1. O projeto em 30 segundos

- O Arandurapé mapeia a Internet brasileira (BGP do IX.br, tabela global, Registro.br/LACNIC, PeeringDB, RPKI, Anatel/SICI e outras
  fontes públicas) em **snapshots datados e imutáveis**, servidos por API REST (FastAPI), servidor MCP e interface web
  (React/Vite/TypeScript). Sem banco de dados em tempo de execução: a fonte são arquivos em `data/`.
- Idioma: **português** em documentação, interface, mensagens e commits.
- Licença AGPL-3.0-or-later: todo arquivo novo de código leva o cabeçalho SPDX e o copyright (copie de um módulo vizinho). Arquivos
  vindos de terceiros mantêm a licença de origem (ex.: `tests/ipv6/v6bench/`, MIT).
- Mapa: `sources/<id>/` (coleta e fontes derivadas) → `products/<id>/` (análises) → `publish/` (snapshot); `arandu/` (executor) e
  `catalog/` (catálogo declarativo); `core/` (utilitários); `api/` (rotas em `api/routes/`, acesso em `api/auth/`); `mcp_server/`;
  `frontend/`; `docker/` e `docker-compose*.yml`; `tests/`; `config/`. `collector/`, `enrich/` e `analysis/` são só atalhos de
  compatibilidade para os nomes antigos dos módulos. Cada pasta de código tem um `descricao-da-pasta.md`.

## 2. Regras gerais de trabalho

1. **Commit ao fim de cada mudança coerente**, sem acumular, stageando só o que é da tarefa. Mensagem em português no estilo
   `escopo: resumo` ou `tipo(escopo): resumo`, explicando o porquê.
2. **Versão por integração:** ao integrar uma mudança em `main`, bump de `VERSION` + nota em `CHANGELOG.md` e tag `vX.Y.Z` no commit
   do merge.
3. **Agente não faz push nem implantação** sem pedido explícito de quem mantém o serviço. Nunca `docker compose up` de um serviço
   isolado num ambiente com nginx: ele resolve o host `api` na subida e derruba o serviço. Implantação é `sudo bash restart-safe.sh` (com Docker rootless, `bash restart-safe.sh` como o usuário do serviço).
4. **Node/npm não são necessários na máquina**: tudo do frontend via Docker (seção 5).
5. **Não cite números de memória**; meça. Relate com fidelidade o que foi testado, o que falhou e o que ficou pendente.
6. Antes de apagar ou sobrescrever, olhe o alvo. Nada de copiar `data/` (dezenas de GB). Em logs grandes use `tail -c`, nunca `cat`.
7. As diretrizes de projeto do guia do desenvolvedor só mudam com aprovação do mantenedor.
8. Nada removido sem alias ou aviso; `published/{date}/` e `raw/` são imutáveis.

## 3. Como codificar

Resumo do que mais quebra (o completo está nas diretrizes do guia):

- **Estilo:** siga o módulo vizinho (nomes, densidade de comentário, idioma). Comentários explicam o porquê, não o quê, e não citam
  documentos que não estão no repositório. Logs com `structlog`; sem `print` em serviço/pipeline.
- **Configuração** em `config/`; segredos só no `.env`, nunca no repositório.
- **Honestidade semântica:** inferido, estimado e hipótese são rotulados; todo número exibido tem fonte e data.
- **Política editorial:** só dados e comparações, sem juízo de valor, causa ou intenção ("sem declaração", não "omitiu"); ranking
  nominal só com dado medido ou declarado e regra visível; a revisão humana é da metodologia, não de cada resultado.
- **Privacidade:** contatos (PeeringDB, RDAP) e dados de pessoa física **não** vão para rota pública nem para o MCP. O log de uso
  (`api/usage_log.py`, `data/ops/usage/`) **nunca** grava IP, cookie, e-mail nem querystring; se mudar o que ele registra, atualize a
  seção 2.2 de `/privacidade`. O registro por conta (`api/uso_conta.py`, `data/ops/uso_conta/`) usa `conta_id` (nunca e-mail nem IP)
  e segue a seção 2.3 de `/privacidade`: detalhe 90 dias, agregados 12 meses; a exclusão de conta é sempre em 30 dias
  (`python -m api.auth.manutencao`, diário). A chave de MCP nunca aparece em log, resposta pública, contrato nem fixture
  (`tests/unit/test_chave_mcp_nao_vaza.py`).
- **Versão:** a fonte única é o arquivo `VERSION` (lido por `core.common.app_version()`); não escreva número de versão em outro lugar.
- **API:** rota pesada precisa de cache/memoização e, se devolve MBs, de uma rota-resumo para listas. O GIL faz uma rota pesada
  atrasar as triviais: pense em payload e CPU. Mantenha aliases ao renomear. Contratos golden (`tests/contracts/*.json`) mudam
  **conscientemente**.
- **Frontend:** hover não deve disparar estado do React (use CSS); mapas e gráficos não re-renderizam por hover. Qualquer 401 abre o
  modal de login; não mostre erro cru. IPv6 antes de IPv4 em toda ordem visual e texto (`lib/familias.ts`); acessibilidade
  ABNT NBR 17225 / WCAG 2.2 AA (`tests/e2e/acessibilidade.js`).
- **Coleta:** `User-Agent` identificado, uma requisição por vez, ≥ 1 s entre requisições, `robots.txt` respeitado, só fontes abertas;
  bruto com dado pessoal é agregado em fluxo e não gravado; campos de terceiros por lista branca.
- **Limites:** identidade por conta ou rede (IPv6 pelo /64), janelas de minuto, hora e dia, custo por rota (`api/limites.py`); contatos
  só com conta e com cota (`api/contatos_cota.py`). Rota nova cara: some o custo em `custo_api`. Os testes desligam os tetos em
  `tests/conftest.py`; quem testa um limite liga o dele.
- **Pipeline/coletor:** idempotente (`--date`, `--force`), escrita atômica, falha alto com código ≠ 0, limite de taxa.
- **Nome do site:** vem do `.env` (`SITE_NOME`, `SITE_URL`, `SITE_MCP_ESQUEMA`… em `core/site.py` e `frontend/src/lib/site.ts`; o
  frontend lê na compilação). Não escreva o nome público nem o domínio em código: use `SITE`. Em docstring e descrição de rota/tool,
  "Arandurapé" e `arandurape://` servem de marcador que `core.site.com_identidade` troca na saída (OpenAPI, catálogo, MCP). Nos
  artefatos do pipeline "Arandurapé" é o software e fica. `tests/unit/test_identidade_site.py` confere.

## 4. Política de acesso (a parte que mais quebra por descuido)

Níveis: **allowed** (IP em `ALLOWED_IPS`, nunca vê login), **user** (cookie `auth_token`), **anon**. Classes de rota em
[api/auth/access_policy.py](api/auth/access_policy.py), fonte única:

- `open`: páginas de entrada, sempre liberadas;
- `metered`: páginas avançadas, liberadas enquanto o orçamento (`ANON_SESSION_LIMIT_MINUTES`, só conta uso ativo em área `metered`)
  não esgota; rota não listada cai aqui;
- `login`: expandir/paginar lista (> 100 ou `page > 1`), histórico (datas fora das 2 mais recentes), contatos, CSV.

Ao **criar ou alterar uma rota de API**:

1. classifique-a: `open`/`login` em `access_policy.py`; avançada (`metered`) pode ser declarada em `tests/access_metered_routes.json`
   (rota sem classe explícita falha `tests/test_access_policy.py`);
2. se uma página de entrada passa a chamá-la, registre em `tests/access_entry_calls.json`: em `paginas` (tem de ser `open`) ou em
   `degradaveis` (mapa/popup opcional, `metered`, e a página deve avisar quando o bloco for bloqueado);
3. atualize o espelho do frontend em [frontend/src/auth/accessPolicy.ts](frontend/src/auth/accessPolicy.ts) (`routeAccess()`);
4. registre a rota na matriz de cobertura: declare a capacidade em `serve/capabilities/<entidade>.yaml` (as rotas e a tool do MCP
   nascem dela) ou acrescente a rota a `serve/capabilities/_manuais.yaml` com `mcp:` (a tool que a atende) ou `sem_mcp:`
   (justificativa), e rode `python3 scripts/gen_cobertura.py` (regrava `docs/cobertura.md`; rota sem decisão falha o CI);
5. o gate (nginx `auth_request` → `api/gate_app.py`, porta 8001, fail-open em 2 s) e o middleware usam a mesma regra; não crie uma
   terceira.

`ACCESS_POLICY_MODE` = `off | shadow | enforce` (em produção: `enforce`). Textos de consentimento e privacidade têm redação definida
pelo mantenedor: não reescreva sem pedir.

## 5. Como testar

Sempre antes de commitar o que for tocado (`$PY` é o Python do seu ambiente, instalado por `pip install --require-hashes -r requirements-dev.lock`):

| O quê | Comando |
|---|---|
| Python (sempre) | `$PY -m pytest -q tests` |
| Coletor/enriquecedor (mexeu em `sources/`) | `$PY -m pytest -q tests/sources` — T1 sem rede; amostras em `tests/fixtures/raw/<fonte>/` (o README diz se é real, reconstruída ou sintética) |
| Pipeline/produtos (mexeu em `products/`, `publish/`, `api/store.py`) | `$PY -m pytest -q tests/products` — T2 sobre o dataset sintético (`tests/synth/README.md`); mudança de saída intencional: `--update-golden` e REVISAR o diff |
| Formato dos artefatos publicados | `$PY -m pytest -q tests/products/test_t3_schemas.py` — T3: esquemas em `tests/contracts/schemas/`; mudança intencional de formato: ajuste o esquema (`python -m tests.contracts.infer --published data/published/DATA --out DIR` ajuda) e registre no CHANGELOG |
| API (rota em `api/routes/`, `api/main.py` ou `api/auth/`) | `$PY -m pytest -q tests/products/test_t4_api.py tests/products/test_t4_fuzz.py` — T4: contrato por operação (`tests/contracts/api_contract.json`, `--update-golden` e REVISAR), privacidade, cache, paginação e fuzz do OpenAPI sem 5xx. Rota nova precisa de uma requisição válida em `tests/products/api_contract.py` |
| MCP (tool, resource ou prompt em `mcp_server/`) | `$PY -m pytest -q tests/products/test_t5_mcp.py` — T5: inventário e uma chamada por tool (`tests/contracts/mcp_contract.json`, `--update-golden` e REVISAR), sem e-mail/telefone, instruções só citam tools que existem. Tool nova: nome de domínio (`asn_`, `ixp_`, `rota_`, `operadora_`…; `mcp_server/nomes.py`), linha em `mcp_server/guia.py` e argumentos em `tests/products/mcp_contract.py` se tiver obrigatório novo. Nome antigo nunca some: vira alias oculto |
| Catálogo/executor (`catalog/`, `core/catalog/`, `arandu/`) | `$PY -m pytest -q tests/unit/test_arandu.py tests/unit/test_catalog_schema.py tests/products/test_t3_catalogo.py tests/products/test_t2_arandu_compare.py` e `python3 scripts/gen_docs.py` (regenera `docs/`; `--check` no CI). Fonte/etapa nova: `catalog/sources/` + `catalog/steps/`; ordem em `python -m arandu plan`, fixada em `tests/contracts/ordem_etapas.json` (mudança intencional: regrave e REVISAR). Etapa é citada pelo `id`; id renomeado ganha alias em `ALIASES_ETAPA` |
| Capacidades e cobertura (`serve/capabilities/`, `core/capacidades.py`, `api/capacidades.py`, `mcp_server/` ou rota nova) | `$PY -m pytest -q tests/unit/test_capacidades.py tests/unit/test_cobertura.py` e `python3 scripts/gen_cobertura.py`; a geração não deve alterar o OpenAPI (`python3 scripts/gen_openapi.py --check`) nem o inventário do MCP |
| Tudo (antes de integrar) | `PYTHON=$PY bash scripts/ci.sh` — o mesmo que a integração contínua roda (regras de camada, sintaxe dos scripts, pytest T0–T5); `bash scripts/ci.sh --docker` repete na imagem-base de produção. API sintética fora do pytest: `python -m tests.synth.publish --out DIR --extra-asns 1100` |
| Frontend (mexeu em `frontend/`) | `bash scripts/front-test.sh` — tsc + vitest (msw com respostas do dataset sintético, `frontend/src/test/fixtures/`, regerar com `python -m tests.synth.export_front_fixtures`) + build, via Docker; `--quick` só vitest. O espelho da política de acesso é conferido em `tests/unit/test_front_access_mirror.py` |
| Dependências (mexeu em `requirements*.txt`, `frontend/package*.json`, Dockerfile ou imagem) | `bash scripts/travar-dependencias.sh` depois de mudar um `requirements*.txt` (regrava os locks com hashes; `tests/unit/test_lock_dependencias.py` reprova lock atrasado). `bash scripts/sbom.sh` — SBOM CycloneDX e Grype: reprova vulnerabilidade alta ou crítica com correção no que vai para produção; `--imagens` inclui as imagens construídas. Exceção só em `config/vex.openvex.json`, com justificativa |
| Gate no nginx (nginx, gate ou política) | `bash tests/nginx/test_gate.sh` |
| E2E Playwright (acesso, login, listas) | `bash tests/e2e/run.sh` (pré-requisitos no cabeçalho do script), sobre a API sintética. Fumaça e orçamento de chamadas/bytes: `bash tests/e2e/run.sh smoke.js` (baseline em `tests/contracts/page_budget.json`; `--update` regrava, REVISAR). Erros de console: `bash tests/e2e/run.sh console.js`; contra um ambiente real, `BASE_URL=<endereço>` (ver o cabeçalho de `console.js` e `segunda_visita.js`) |
| IPv6, T7 (nginx, `api/auth/`, IP do cliente, allowlist, log de uso ou `tests/ipv6/`) | `KATHARA="<venv>/bin/python -m kathara" bash tests/ipv6/run.sh` — laboratório Kathará + TAYGA (sem root) com clientes dual, só IPv4, só IPv6, NAT64/DNS64 e SIIT; confere o que `/auth/diag` vê em cada cenário (`tests/ipv6/esperado.json`), cabeçalho forjado ignorado e log de uso sem IP. Kathará: `pip install -r tests/ipv6/requirements.txt` num venv próprio |
| Paridade (mexeu em `sources/`, `products/` ou `publish/`, com dados reais) | `$PY scripts/replay.py --date AAAA-MM-DD` — reconstrói o publicado de uma data e compara; **0 diferenças novas** (as explicadas ficam em `scripts/replay_expected.json`) |
| Pós-implantação | `bash scripts/post-deploy-check.sh [--expect-version X]` — só leitura contra o endereço público: `/health` e versão, rotas-chave, contatos exigem login, MCP, páginas; o `restart-safe.sh` já roda isto |

Se um teste falhar, corrija a causa; não desative teste sem registro. Se não puder rodar um nível aplicável, diga isso
explicitamente em vez de omitir.

## 6. Armadilhas já vividas

- Nginx de borda (fora do repositório): use `proxy_pass` com variável e `resolver 127.0.0.11` para re-resolver o DNS do contêiner;
  upstream fixo quebra quando a API é recriada.
- `/bgp-stability` completo pesa ~40 MB; listas usam `/bgp-stability/summary`.
- `sed` do macOS não aceita `\n`; use Python para edições multilinha.
- Inserir imports por script quebra imports multilinha de TS: confira o build.
- E2E local (`tests/e2e/run.sh`): suba a API com `APP_BASE_URL=http://localhost`; com `https://…` o cookie `anon_sid` sai `Secure` e o
  teste "API avançada = 403" falha sem ser bug.
- Teste de coletor novo: cada fonte precisa de amostra em `tests/fixtures/raw/<fonte>/` + README (origem, data, recorte, o que foi
  anonimizado). Nunca dado pessoal real nem registros de bases com EULA restritiva: use amostra sintética no formato original. HTTP
  com `respx`; urllib com `monkeypatch`; Telnet com `tests/fakes/telnet_lg.py`.
- Um venv local pode divergir da produção (FastAPI, Starlette): rode `bash scripts/ci.sh --docker` quando mexer em rota, middleware
  ou schema.
- `GET /api/v1/snapshots/{date}` lê `published/{data}/snapshot_detail.json`; para snapshots antigos sem o arquivo:
  `python -m publish.snapshot_builder --date AAAA-MM-DD --detail-only` (aditivo). Sem ele, a API recalcula e a memória cresce
  centenas de MiB por data.
- Logs de produção chegam a GB; leia com `tail -c` ou por stdin.
- Todo 4xx vira erro no console do navegador, mesmo tratado. Página que consulta um serviço que a entidade pode não ter pede
  `?opcional=1` e recebe **204** em vez de 404 (`api/main.py`); sem o parâmetro a API continua respondendo 404.
- `?date=` de snapshot publicado sai `immutable` por um ano (navegador e `nginx_cache`): campo novo numa rota existente, ou arquivo
  aditivo gravado num snapshot já servido, só aparece se o front mudar a URL (parâmetro `esquema`, ver `fetchBrasilIndicadores`).
  Recriar contêiner à mão não limpa o `nginx_cache`; o `restart-safe.sh` limpa.
- Os glifos do mapa de fundo (`data/tiles/_assets/fonts/…`) não são gerados por `build-basemap-tiles.sh` nem estão no git:
  `bash scripts/fetch-basemap-fonts.sh [data]` os provisiona (idempotente). Sem eles cada mapa dá 404 e perde os rótulos.
- Arquivos de `data/auth/` criados por outro usuário ficam só-leitura para o contêiner da API (`cap_drop: ALL`): o SQLite responde
  "readonly database" e `/auth/me` dá 500. Não use `chmod a+rw`: `sudo bash scripts/preparar-dados-api-sem-root.sh` entrega `auth/`,
  `ops/usage`, `ops/uso_conta` e `cache/br11` ao UID 1001 com 0770/0660; com `API_USER=1001:0` e `API_DATA_MODE=ro` a API roda sem
  root e com `data/` só leitura. Com Docker rootless o UID 1001 do contêiner é outro no host (subuid): `chown 1001` no host entrega os
  dados a outra conta; rode o script sem sudo, que ele faz o `chown` de dentro de um contêiner.
- `GET /query/global_prefixes` lê `maps/global_prefixes.col` (tabela colunar por `mmap`, `core/colunar.py`); snapshot sem o arquivo
  cai no GeoJSON (~8 s). Para os já publicados: `python -m products.mapas_prefixos.colunar --date AAAA-MM-DD`.
- `GET /ixps/{code}/geo?layer=prefixes_v4|v6` lê `maps/ixp_prefixes/{ptt}-{afi}.json.gz` (passo `mapas_geo`); sem o arquivo calcula
  na hora, e no SP isso passa dos 100 s da Cloudflare (524). Para os já publicados, no worker com `scripts/arandu-exclusivo.sh`:
  `python -m products.mapas_prefixos.ixp_prefixos --date AAAA-MM-DD` (precisa do `normalized/` da data e da base em `raw/dbip/`).
- Coleta diária (`ARANDU_MODO=due`): fonte dentro da cadência é restaurada do armazém **com a data de origem no nome**. Quem lê o
  bruto do LG usa `core.common.raw_bgp_ixp`, não monta o nome com a data do snapshot; sem isso o snapshot sai com todos os PTTs
  `missing` e a execução consta como `ok`.
- Coleta ou produto pesado feito à mão passa por `scripts/arandu-exclusivo.sh` (mesmo lock do cron: nunca ao lado do pipeline) e roda
  no worker com teto (`WORKER_MEM_LIMIT`). A API chega a ~4,3 GiB com o conjunto completo de dados: dimensione `API_MEM_LIMIT` e
  `API_MEMSWAP_LIMIT` com folga, ou ela cai por OOM em laço.
- RPKI: o Routinator roda avulso antes do worker (`scripts/rpki-avulso.sh`, perfil `rpki`, cache no volume `rpki_cache`) e a etapa
  `rpki_collector` lê `data/cache/rpki/vrps.json`. Não volte a um serviço 24/7: ele revalida o repositório o tempo todo e satura o
  disco. Coleta RPKI à mão: `scripts/rpki-avulso.sh` antes da etapa.

## 7. Ao terminar qualquer tarefa

Testes do nível aplicável verdes, commit feito, o que ficou pendente dito com clareza e, se houver implantação envolvida, a
verificação pós-implantação listada para quem implanta.
