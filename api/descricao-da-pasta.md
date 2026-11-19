# api/ — API REST (FastAPI)

> Licença: AGPL-3.0-or-later — Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit

Servidor REST do Arandurapé (FastAPI/uvicorn). Serve os artefatos de `data/published/{date}/` sem banco de dados: o `Store` lê os
arquivos e os serviços guardam em memória, por data, o que cada assunto precisa. A lista completa de rotas está no OpenAPI
(`/api/v1/docs`) e, com a tool do MCP que atende cada uma, em [docs/cobertura.md](../docs/cobertura.md).

## Arquivos

| Arquivo | Papel |
|---|---|
| `main.py` | Aplicação FastAPI: middlewares (controle de acesso, limites, cache HTTP, compressão), ciclo de vida (aquecimento dos índices), `/health` e inclusão dos routers. |
| `store.py` | Fachada de acesso aos dados de `published/{date}/`: escolhe o snapshot e delega aos repositórios (`repos/`) e serviços (`services/`). |
| `cache.py` | Cache de respostas em memória, escopado ao snapshot mais recente. |
| `query.py` | Camada de consulta genérica (`POST /query`): filtro, seleção, ordenação e agregação sobre as tabelas em memória do snapshot. Usada pela API e pelo MCP. |
| `query_catalogo.py` | Catálogo da camada de consulta: collections, schema de cada uma, operadores e receitas. |
| `query_colunar.py` | Motor da mesma linguagem de consulta sobre tabelas colunares (`core/colunar.py`), para as collections grandes. |
| `capacidades.py` | Rotas REST geradas das capacidades declaradas em `serve/capabilities/*.yaml`. |
| `busca.py` | Busca universal: índice em memória por snapshot e a consulta sobre ele (rota em `routes/busca.py`). |
| `snapshot_detail.py` | Detalhe de um snapshot (`GET /api/v1/snapshots/{date}`): resumo e metadados do manifesto. |
| `outorgas_store.py` | Leitura das outorgas da Anatel publicadas (SCM, SMP, STFC e SeAC), uma implementação para os quatro serviços. |
| `privacidade.py` | Garante que contatos não saiam em resposta pública nem no MCP: só contagens, e a rota de contatos exige login. |
| `limites.py` | Orçamento de requisições por cliente (conta ou rede; IPv6 pelo /64), por minuto, hora e dia, com custo por rota. Comum à API e ao MCP. |
| `contatos_cota.py` | Cota de consultas de contato por conta. |
| `concurrency.py` | Limite de pedidos calculando ao mesmo tempo; os demais esperam na fila e, passado o tempo, recebem 503. |
| `ratelimit.py` | Limitador anti-abuso (slowapi), chave pelo IP do cliente lido dos cabeçalhos do proxy. |
| `parametros.py` | Trata parâmetros de consulta não declarados nas rotas GET (registra ou rejeita, conforme `API_PARAMETROS_DESCONHECIDOS`). |
| `deprecation.py` | Rotas substituídas por contratos unificados: continuam respondendo, com os cabeçalhos `Deprecation` e `Link`. |
| `gate_app.py` | Processo do gate de acesso (`auth_request` do nginx, porta 8001): mesma regra do middleware, fail-open em 2 s. |
| `usage_log.py` | Log de uso da API e do MCP, sem IP, cookie, e-mail nem querystring (ver `/privacidade`, seção 2.2). |
| `uso_conta.py` | Registro de uso por conta (`conta_id`), para controle de acesso e prevenção de abuso, e o perfil de uso mostrado ao titular. |
| `precompressao.py` | Pré-compressão brotli-11 das camadas estáticas endereçadas por conteúdo. |
| `heap.py` | Coleta de lixo do Python fora do caminho das requisições. |
| `diag.py` | Diagnóstico de memória da API: o que ocupa a RAM do processo, por cache e por data. |
| `asn_health.py` | Implementação anterior dos alertas por ASN; as regras vivem em `products/alerts/`. Fica como referência do teste de paridade (`tests/products/test_t2_alertas_paridade.py`). |
| `geo.py` | Atalho para `core.geo.haversine_km`, mantido para quem importava daqui. |

## Subpastas

| Pasta | Papel |
|---|---|
| `routes/` | Os routers, um por assunto (ASNs, IXPs, prefixos, outorgas, SICI, BGP, mapas, histórico, produtos de cada fonte). A docstring de cada arquivo diz as rotas que ele atende. |
| `services/` | Um serviço por assunto sobre o `Store`: guarda os caches e a lógica (funções puras sobre os artefatos publicados) e é usado pela API, pelo `/query` e pelo MCP. |
| `repos/` | Repositórios de artefatos publicados: cada um lê e guarda em cache, por data, um tipo de arquivo de `published/{data}/` (`base.py` define o `ArtifactRepo`). |
| `auth/` | Autenticação e controle de acesso (ver abaixo). |
| `schemas/` | Modelos Pydantic de resposta para o OpenAPI. |

### `auth/`

| Arquivo | Papel |
|---|---|
| `access_policy.py` | Fonte única da política de acesso: classifica cada rota em `open`, `metered` ou `login`. |
| `access.py` | Decisão de acesso: allowlist, usuário com conta ou sessão anônima, aplicando a política da rota. |
| `anon_session.py` | Sessão anônima (navegação sem login, com limite de tempo de uso ativo). |
| `previa.py` | Prévia anônima de listas e histórico, a mesma no site, no `/query` e no MCP. |
| `router.py` | Login OAuth (Google, LinkedIn, PeeringDB), `GET /auth/me`, heartbeat e logout. |
| `contas.py` | Cadastro de contas com `conta_id` estável, sessão revogável e exclusão com prazo. |
| `sessao.py` | Valida o JWT contra o cadastro de contas (conta ativa, "sair de todos os dispositivos"). |
| `perfil.py` | Perfil da conta: dados mínimos, uso, chave de MCP, "sair de todos os dispositivos" e pedido de exclusão (30 dias). |
| `chaves_mcp.py` | Chave de MCP (`arandu_mcp_<id>_<segredo>`, 256 bits), guardada só como HMAC-SHA-256 com pepper do ambiente. |
| `tentativas.py` | Limite de tentativas inválidas de chave de MCP, em memória. |
| `internas.py` | Rotas internas, só para o contêiner do MCP: verificar a chave e enviar eventos de uso por conta. |
| `manutencao.py` | Manutenção diária (`python -m api.auth.manutencao`): apaga contas com exclusão pedida há 30 dias ou mais e aplica a retenção do uso por conta. |
| `deps.py` | Dependências FastAPI que protegem rotas sensíveis (ex.: contatos). |
| `jwt_utils.py` | Geração e validação de tokens JWT. |
| `storage.py` | Armazenamento dos tokens de autenticação pendentes. |
| `config.py` | Configuração do módulo de autenticação (segredos e prazos lidos do ambiente). |

## Cache

1. **Por data, em memória:** repositórios e serviços guardam os artefatos já lidos de cada snapshot.
2. **Respostas do snapshot mais recente** (`cache.py`).
3. **HTTP:** `?date=` de snapshot publicado sai `immutable`; o nginx do frontend (`nginx_cache`) guarda as respostas e o
   `restart-safe.sh` o limpa a cada implantação.
