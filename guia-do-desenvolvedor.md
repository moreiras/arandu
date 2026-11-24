# Guia do desenvolvedor — Arandurapé

> **Licença:** GNU Affero General Public License v3 ou posterior (AGPL-3.0-or-later)
> Texto completo: <https://www.gnu.org/licenses/agpl-3.0.html>

## O que é o Arandurapé

O Arandurapé mapeia a Internet brasileira em snapshots datados e imutáveis, publicados a cada semana. Combina dezenas de fontes públicas (looking glasses do IX.br, tabela BGP global do RouteViews e do RIPE RIS, Registro.br, LACNIC, PeeringDB, RPKI, estimativas de usuários do APNIC, dados abertos da Anatel e outras; lista em [docs/fontes/](docs/fontes/)) para produzir métricas de presença em PTTs, roteamento, segurança, mercado e território dos ASNs e das operadoras brasileiras.

Os dados são servidos via API REST (FastAPI), servidor MCP (Model Context Protocol) e interface web (React).

---

## Diretrizes de projeto

Regras que guiam qualquer mudança. As que não podem quebrar estão em testes; as demais estão aqui, com o porquê. O
[AGENTS.md](AGENTS.md) resume as mesmas regras para agentes.

### Arquitetura

1. **Cada fonte é um pacote declarado** (`catalog/sources/<id>.yaml` + `sources/<id>/`): metadados, licença, cadência, esquema,
   coletor, normalizador, amostra de teste e documentação.
2. **A documentação de fontes e produtos é gerada do catálogo** (`scripts/gen_docs.py`), não escrita à mão; o CI confere.
3. **O pipeline é um grafo declarado** (fontes → produtos → publicação); a ordem é calculada (`python -m arandu plan`).
4. **Cruzamentos são produtos** com entradas e saídas declaradas e **não alteram** artefatos de outros produtos.
5. **Rotas da API e tools do MCP nascem de capacidades declaradas** (`serve/capabilities/`); API e MCP são cascas finas sobre o
   mesmo código de leitura.
6. **O frontend compõe blocos por entidade**, e cada bloco declara de que dado depende.
7. **Tudo em arquivos, sem banco de dados em runtime.** Se o volume crescer, tabelas colunares geradas no build e lidas por
   `mmap` (`core/colunar.py`), mantendo os documentos JSON como contrato público.

O que **não** fazer: orquestrador pesado (Airflow, Dagster, Prefect: o grafo é pequeno e o executor `arandu` basta),
microsserviços (API e MCP separados só somariam operação), reescrever o frontend, meta numérica de cobertura de testes (cubra
contratos, cenários plantados e regras de negócio).

### Snapshots e publicação

- **O publicado é imutável.** Nada em `published/{data}/` é reescrito depois do manifesto. Mudança de formato em disco só com
  `layout_version` novo e leitor que entende os dois. Refatoração do pipeline se valida por *replay* de um snapshot real
  (`scripts/replay.py`): zero diferenças novas, e as explicadas ficam em `scripts/replay_expected.json`.
- **A data do snapshot não quer dizer "tudo coletado nesse dia".** O manifesto traz a data de cada fonte (`as_of`) e a interface
  mostra as duas datas.
- **Snapshot semanal, coleta por fonte.** Um só cron e um só `arandu run`: a cadência de cada fonte decide o que roda no dia. A
  coleta pode ser mais frequente que o snapshot onde houver ganho, sempre em doses pequenas e com estado persistente; produto e
  publicação respeitam a cadência semanal.
- **Rodízio com orçamento** para fontes grandes ou lentas (`core/rodizio.py`): por execução, no máximo N itens, os sem leitura
  primeiro e depois os de leitura mais antiga; a idade de cada leitura é publicada e a cobertura é declarada ("N de M ASNs").
  Ausência de leitura não é zero.

### Honestidade semântica e política editorial

- Todo número exibido tem **fonte e data**. Estimativa, inferência ou hipótese do projeto **nunca aparece como número oficial** da
  fonte: tem rótulo, margem de erro e período de referência visíveis.
- A política editorial vale para interface, API e MCP: só dados e comparações, sem juízo de valor,
  causa ou intenção ("sem declaração", não "omitiu"); ranking nominal só com dado medido ou declarado e regra visível; inferido de
  risco alto para a empresa não entra em ranking nominal; a revisão humana é da metodologia, não de cada resultado.
- **Linguagem de evidência** para achados negativos ("sessões Spoofer observadas", "resultado de item publicado no PNCP,
  consultado em …"). Ausência de dado não é "rede limpa".
- Governança antes da exposição: política, direito de resposta e privacidade entram antes do primeiro dado que os exija.
- Nomes de empresa são publicados como vêm da fonte.

### Coleta

- `User-Agent` identificado, uma requisição por vez **por destino (host)**, pausa mínima de 1 s (ou a que a fonte pedir), orçamento
  por rodada, parar ao
  primeiro sinal de bloqueio (403, 429, conexão derrubada) e registrar. O limite de 1 s é garantido em toda requisição, repetições
  incluídas (`core.rodizio.Limitador`). Destinos diferentes podem ser consultados ao mesmo tempo, o mesmo destino nunca (decisão do
  mantenedor em 2026-11-22): o executor segura um lock por host (`data/ops/destinos/`) enquanto a etapa roda, também entre o pipeline
  e a trilha contínua. O host vem do `origem.url` das fontes da etapa; o que mais ela consultar vai em `destinos` no catálogo.
- **`robots.txt` é respeitado.** Exceção só por decisão do mantenedor, por host e com registro no catálogo (hoje: `lg.de-cix.net`,
  cuja página convida ao uso da API em scripts).
- **Só fontes abertas, sem depender de pedido nem de parceria.** Dados restritos, exclusivos ou sob termo de acesso
  ficam fora. **Sem medição ativa** (varredura, AXFR, teste de recursão aberta) sem política própria.
- Fonte cujo bruto traz dado pessoal: **agregar em fluxo e não gravar o bruto**; o teste T1 planta os campos sensíveis e exige que
  nenhum chegue ao agregado (modelo: `ooni_bloqueios`, `consumidor_gov`, `peeringdb_fac`).
- Campos de terceiros entram por **lista branca**: campo novo que a fonte criar nasce descartado. URL só passa com esquema
  conhecido e sem credencial embutida.

### Privacidade e licenças

- Contatos (PeeringDB, RDAP, e-mail e telefone de cadastro) e dados de pessoa física **não vão** para rota pública nem para o
  MCP; CPF e nome de pessoa física são descartados ou mascarados: o CPF embutido na razão social de EI/MEI, na publicação
  (`core.cpf.mascarar_snapshot`, no fechamento do snapshot), e o sócio pessoa física, no pipeline e na leitura.
- **Contatos só com conta e com cota** (`api/contatos_cota.py`): custo por ASN revelado, janelas por conta, por rede e global,
  suspensão automática de quem bate no teto repetidamente, nunca cacheáveis. A meta é que montar a lista inteira pelo site seja bem
  mais lento do que consultar as fontes diretamente. Do PeeringDB, só POCs de visibilidade `Public`: o login do site é uma classe só
  (Google, LinkedIn ou PeeringDB, sem distinção) e não pode honrar a restrição `Users`. Bruto com contato não vai para `raw/`.
- IPs de clientes ou de hosts comprometidos (Spoofer, abuse.ch, Shodan) só **agregados por ASN, UF ou faceta**; nunca lista de IPs
  nem host individual.
- **Nenhuma saída pública devolve latitude, longitude ou cidade por prefixo ou por IP.** O cálculo com coordenadas fica no
  servidor; as saídas trazem resultados agregados.
- Agregados de fonte com pessoas físicas têm **bases mínimas** (no `consumidor_gov`: índices só com 30 casos ou mais, células só
  com 5 ou mais reclamações).
- **Cada fonte é avaliada pela cláusula que de fato a restringe** (redistribuição, identificação de terceiros, obra derivada,
  retenção, atribuição), registrada no `source.yaml` com a citação e a data da leitura. "Somente uso não comercial" não é veto por
  si: o projeto é gratuito e sem receita; qualquer recebimento financeiro reabre essas avaliações.
- **Atribuição em todo derivado** (interface, API, MCP, catálogo e [docs/licencas.md](docs/licencas.md)) quando a fonte pede.

### Contas, chave de MCP e registro de uso

- A chave de MCP é aleatória de 256 bits (`arandu_mcp_<id>_<segredo>`), guardada só como HMAC-SHA-256 com *pepper*; uma por conta,
  com rotação, revogação, limite de tentativas inválidas e chave de desligamento (`MCP_KEY_ATIVA`). O MCP verifica pela API, com
  cache curto. A cota diária por conta no MCP só responde 429 com `Retry-After`, sem suspensão (`MCP_COTA_DIARIA`).
- A chave, o segredo, o hash, o *pepper* e o cabeçalho `Authorization` **nunca** aparecem em log, resposta pública, contrato nem
  fixture (`tests/unit/test_chave_mcp_nao_vaza.py`).
- O log de uso anônimo (`api/usage_log.py`) nunca grava IP, cookie, e-mail nem querystring. O registro **por conta**
  (`api/uso_conta.py`) é separado, sem IP, com detalhe por 90 dias e agregados por 12 meses.
- Exclusão de conta: o pedido desativa na hora e a exclusão efetiva ocorre 30 dias depois (`python -m api.auth.manutencao`), para
  que ninguém crie conta, abuse e apague o rastro em seguida.
- Textos de privacidade, consentimento e termos têm redação do mantenedor: não reescreva sem pedido.

### Interface

- **Os públicos (técnico, gestor, regulador) chegam pelas mesmas entidades** (AS, operadora, município, PTT) e querem lentes
  diferentes: separar por **aba dentro da entidade**, nunca por área do site para cada público. A aba fica na URL (`?aba=`).
- **Página de entidade:** ficha-resumo com KPIs e referência (mediana da UF, do porte ou do país, ou posição no ranking);
  frase-síntese **gerada por regras** (`features/*/sintese.ts`), reproduzível e rotulada; entidades relacionadas como links; abas
  sem conteúdo somem e cada aba carrega só os seus dados; blocos com título; "Como ler" recolhível; ações de citar, comparar e
  exportar.
- Tabelas longas: paginação, "ver todas" ou virtualização; **nunca milhares de linhas no DOM**. Ordenação pelo título da coluna,
  com `aria-sort`, quando a API permitir.
- **IPv6 antes de IPv4** em toda ordem visual, texto e documentação (`frontend/src/lib/familias.ts`).
- **Acessibilidade:** ABNT NBR 17225 / WCAG 2.2 AA, conferida com axe-core (`tests/e2e/acessibilidade.js`); alvo de toque de
  24 px, contraste AA e `aria-controls` só para elemento que existe.
- Hover não dispara estado do React (use CSS); mapas e gráficos não re-renderizam por hover. Qualquer 401 abre o modal de login.

### Texto gerado automaticamente

A frase-síntese é por regras, sem LLM. Se algum dia houver texto gerado por modelo de linguagem, ele segue o padrão **fatos →
texto → verificação**: um programa monta o pacote de fatos (valor, fonte, data, selo de fato, estimativa ou inferência); o modelo
escreve com marcadores (`{{usuarios}}`), nunca com números; um verificador determinístico rejeita número fora do pacote, marcador
inexistente, vocabulário vetado pela política editorial e afirmação sobre dado inferido sem o termo de inferência; texto rejeitado
não é publicado; modelo, versão do prompt e hash dos fatos ficam gravados com o artefato.

### Limites por cliente

- **Identidade:** conta (cookie ou chave de MCP), allowlist ou rede de origem, com IPv6 agregado pelo /64 (`api/limites.py`). Nunca o
  endereço IPv6 inteiro: trocar o sufixo dentro do prefixo do assinante não pode renovar limite nenhum.
- **Tolerante a rajada, restritivo no acumulado:** janelas de minuto, hora e dia ao mesmo tempo, com custo por rota (as caras pesam
  mais), e no máximo poucos cálculos simultâneos por cliente além do teto global (`api/concurrency.py`).
- **Camadas independentes:** Cloudflare e nginx seguram inundação; a aplicação segura identidade, custo e janelas longas. Nenhuma
  confia que a anterior funcionou. Atrás de proxy, o IP real só vem de quem está na frente (`docker/nginx-real-ip*.inc`); sem isso todos os
  clientes dividem o mesmo limite.
- 429 sempre com `Retry-After`, mensagem que diz qual limite e quanto esperar, e `no-store`.

### Memória e desempenho da API

- Rota pesada precisa de cache e, se devolve MBs, de uma rota-resumo para listas. Uma rota pesada atrasa as triviais (GIL).
- **Nada de recalcular índice por requisição:** o que depende só do snapshot é gravado pelo pipeline (`snapshot_detail.json`,
  `maps/global_prefixes.col`) e a rota só lê. Medido: a rota de detalhe de snapshot que recalculava índices somava centenas de MiB
  retidos por data.
- O alocador do Python retém memória liberada (arenas fragmentadas): picos de carga deixam o processo grande. Prefira carregar um
  item por vez, arquivos estáticos servidos pelo nginx com cache imutável (`?v=`) e leitura por `mmap`, que fica no *page cache*
  compartilhado entre processos.

---

## Estrutura de diretórios

```
arandu/                       (raiz do repositório)
├── sources/<id>/      coleta (collect.py) e fontes derivadas (enrich.py), uma pasta por fonte do catálogo
├── products/<id>/     análises e cruzamentos (build.py); products/passos.py lista os passos de publicação
├── publish/           montagem do snapshot publicável (snapshot_builder, manifesto, conferências da coleta)
├── catalog/           sources/, products/ e steps/ em YAML, mais retencao.yaml: a fonte única da documentação de docs/
├── arandu/            executor e CLI do pipeline (python -m arandu)
├── core/              utilitários compartilhados; core/catalog/ lê e valida o catálogo; core/store/ é o armazém de versões
├── api/               API REST (FastAPI): main.py, routes/, services/, repos/, schemas/, auth/
├── mcp_server/        servidor MCP
├── serve/capabilities/  capacidades declaradas, de onde nascem rotas e tools; _manuais.yaml cobre as rotas escritas à mão
├── frontend/          interface web (React, Vite, TypeScript, Tailwind)
├── config/            configuração curada (PTTs, PIX, CDNs, communities, relações entre ASNs, marcas)
├── docker/            nginx, includes de IP real, unidades do systemd
├── scripts/           instalação, operação, geradores de documentação, CI
├── docs/              documentação gerada do catálogo e do código (não edite à mão)
├── tests/             testes T0 a T7, dataset sintético, amostras por fonte, carga, E2E
├── collector/ enrich/ analysis/   atalhos para os nomes antigos dos módulos (emitem DeprecationWarning)
├── data/              dados gerados (fora do repositório)
├── docker-compose.exemplo.yml (+ .prod.yml e .no-nginx.yml)   api, mcp, frontend; worker e rpki por perfil (copiar para docker-compose.yml)
├── restart-safe.sh    implantação (api, mcp e frontend, com retorno à versão anterior)
└── delete-snapshot.sh remove um snapshot e seus artefatos
```

Cada pasta de código tem um `descricao-da-pasta.md` com o papel de cada arquivo.

---

## Pipeline de dados

O pipeline é executado pelo `arandu` (seção "Executor" abaixo), no contêiner `worker`, chamado pelo cron por
[`scripts/arandu-weekly.sh`](scripts/arandu-weekly.sh). Cada etapa é um módulo Python invocado com `python -m`, identificado pelo
`id` do catálogo (`catalog/steps/<id>.yaml`). A lista completa, na ordem em que roda, está em [docs/etapas.md](docs/etapas.md); cada
fonte em [docs/fontes/](docs/fontes/) e cada produto em [docs/produtos/](docs/produtos/).

```
fontes externas ──coleta──→ raw/<data>/ ──normalização──→ normalized/<data>/      (sources/<id>/collect.py)
normalized ──fontes derivadas (geocodificação, RDAP, grupos societários…)──→ normalized/<data>/   (sources/<id>/enrich.py)
normalized ──produtos (parser BGP, métricas, relações entre ASNs, estabilidade…)──→ published/ ou data/build/   (products/<id>/)
build ──passos de publicação (products/passos.py)──→ published/<data>/ (índices, mapas, resumo…)
       ──saude_asn──→ documentos de ASN finais (alertas, RPKI)
       ──manifesto (último passo)──→ published/<data>/manifest.json + snapshot_detail.json
```

A API só lista o snapshot quando o manifesto existe: a visibilidade é atômica.

| Camada | Onde | Exemplos de etapa (`id`) |
|---|---|---|
| Coleta | `sources/<id>/collect.py` | `lg_ixbr` (LGs do IX.br por Telnet), `fulltable_routeviews` (tabela global, MRT), `registro_br`, `lacnic_delegated`, `peeringdb_ixps`, `anatel_sici`, `rpki_collector` |
| Fontes derivadas | `sources/<id>/enrich.py` | `rdap` (organização e CNPJ dos ASNs), `cnpj_geo` (sede por CNPJ), `prefix_geo` e `global_prefix_geo` (DB-IP City Lite), `scm_geo` |
| Produtos | `products/<id>/build.py` | `bgp_ixp` (parser BGP), `metricas_ixp_asn` (documentos por PTT e por ASN), `routing_analysis`, `bgp_stability`, `bgp_stability_deep_publicacao` |
| Publicação | `products/passos.py`, `publish/` | `snapshot_completo` (executa os passos em sequência), `saude_asn`, `manifesto` |

Utilitários da coleta: `core/common.py` (caminhos, logging, YAML, JSON gzip) e `core/telnet.py` (cliente Telnet assíncrono).

### Catálogo de fontes e produtos (`catalog/`, `core/catalog/`)

Cada fonte (coletor, enriquecedor ou arquivo curado de `config/`) e cada produto publicado é descrito em
`catalog/sources/<id>.yaml` e `catalog/products/<id>.yaml`: origem, licença, `uso_comercial`, `publicavel`, cadência,
política de falha, saídas, chaves e dicionário de campos. É a fonte única da documentação gerada em `docs/`
(`python3 scripts/gen_docs.py`; `--check` falha se estiver desatualizada). Valide com
`python3 scripts/catalog_validate.py`. Módulo novo em `sources/` sem `source.yaml`, ou arquivo novo
publicado sem declaração, falha em `tests/products/test_t3_catalogo.py`. Valor desconhecido: escreva `nao_verificado`
e explique em `pendencias`; não invente.

### Executor `arandu` (`arandu/`, `catalog/steps/`)

O pipeline é descrito por **etapas** (`catalog/steps/<id>.yaml`): módulo e argumentos, o que produz (fontes e
produtos), `depois_de`, política de falha e janelas por marcador. A ordem é **calculada** a partir das
`entradas` do catálogo; `ordem` só desempata entre etapas sem dependência entre si. `docs/etapas.md` mostra o resultado, e
`tests/contracts/ordem_etapas.json` o fixa (mudança intencional: regrave o arquivo e revise o diff). `arandu` roda no container worker:

```
docker compose run --rm worker python -m arandu plan
docker compose run --rm worker python -m arandu run --date AAAA-MM-DD [--only ETAPA…] [--due] [--retomar] [--dry-run]
docker compose run --rm worker python -m arandu run --date AAAA-MM-DD --compare --out relatorio.json
docker compose run --rm worker python -m arandu status | doctor | memoria | repair --dry-run | store list | gc --dry-run
```

`run` grava `data/ops/runs/AAAA-MM-DD.json` (por etapa: status, tempo, saída, motivo; `falhas_criticas` e `avisos`),
usa lock (`data/ops/arandu.lock`) e, com `--retomar`, continua as etapas já concluídas no dia; com `--due`, coleta só o que a cadência do catálogo manda e restaura, para as demais fontes, a última versão do armazém (`data/sources/<id>/<as_of>/`). Etapa crítica que falha
aborta; opcional vira aviso; `usar_ultima_valida` (sócios) copia a última coleta. Etapas `host` (aquecimento,
basemap, disco) rodam em `scripts/host-steps.sh`. `--compare` reexecuta as etapas reprodutíveis (`replay: true`) num
diretório temporário e compara com o publicado pelo critério do `scripts/replay.py` (0 diferenças novas).
`status` lê o `as_of` do armazém de versões (ou da data da pasta, para snapshots antigos).

Etapas de rede podem ter `tentativas`/`espera_s` no catálogo (erro transitório não derruba a execução). As etapas de host
(aquecimento da API, basemap, disco) rodam, depois de `arandu run`, em `bash scripts/host-steps.sh --date AAAA-MM-DD`, com o tempo
de cada uma em `data/ops/runs/AAAA-MM-DD.host.jsonl`. Ids de etapa renomeados seguem aceitos em `--only` e na retomada
(`ALIASES_ETAPA` em `core/catalog/loader.py`).
O pipeline inteiro pelo executor (worker + etapas de host + compare opcional) é `bash scripts/arandu-weekly.sh`.

**Trilha contínua.** As coletas em rodízio diário com orçamento (`continua: true` na etapa; hoje `ixbr_alice`, `ixbr_alice_rotas` e `rdap_contatos`) não rodam no pipeline: `arandu continuo` as roda à parte (`scripts/arandu-continuo.sh`, no serviço `worker_continuo`, com teto de memória próprio), com lock (`data/ops/arandu-continuo.lock`) e relatório (`data/ops/runs/continuo/`) próprios, num horário que termina antes do pipeline das 04:00. No pipeline a etapa só restaura do armazém a última versão registrada pela trilha contínua (o `as_of` fica no relatório e no manifesto); quem depende dela roda normalmente. `arandu run --only <id>` ainda a roda à mão.

**Coletas em paralelo.** `arandu run --paralelo N` (ou `ARANDU_PARALELO`; padrão 1, em série) deixa até N coletas rodarem ao mesmo tempo. Só rodam lado a lado as coletas puras (fontes `bruta`) com destino conhecido e `memoria_mb` declarado que caiba no orçamento (`ARANDU_MEM_ORCAMENTO_MB` ou 80% do teto do contêiner): uma por destino, e a soma dos `memoria_mb` em curso nunca passa do orçamento. As demais (processamento e coletas sem medição) rodam sozinhas, na ordem do plano, e toda etapa espera as dependências. A saída de cada etapa sai com o prefixo `[id]` no log.

**Memória por etapa.** Cada etapa roda num subprocesso, esperado com `wait4`: o relatório guarda o `pico_mem_mb` (maior RSS do processo da etapa entre as tentativas). `arandu memoria` junta os relatórios gravados e mostra, por etapa, o pico medido, a duração máxima e o `memoria_mb` declarado no catálogo, apontando as sem declaração e as que passaram dela. O `memoria_mb` é o pico medido com folga; sem ele a etapa nunca roda ao lado de outra.

### Armazém de versões, cadência e retenção (`data/sources/`, `catalog/retencao.yaml`, `arandu gc`)

**Armazém.** Cada coleta bem-sucedida entra em `data/sources/<fonte>/<as_of>/` (`meta.json` + `data/`), imutável; o hash é de
**conteúdo** (campos voláteis como `generated_at` não contam), então reexecutar não cria versão nova. `arandu store list` mostra o que há.
O campo `armazem` da fonte no catálogo diz o que entra na versão (`incluir`, ex.: o bruto dos LGs em `.txt.gz`) e quantas versões o `gc`
guarda (`manter_versoes`, ex.: 365 para RPKI, `nicbr-asn-blk`, `delegated-lacnic` e as listas do Registro.br e do LACNIC).
Versão registrada sem um arquivo declarado em `incluir` não é reutilizada pelo `--due`: a fonte é coletada de novo.

**Cadência.** `cadencia.coleta_atual` de cada fonte (`diaria`, `semanal`, `mensal`) é o que `arandu run --due` usa para decidir se
coleta ou restaura a última versão. O cron instalado pelo `scripts/instalar.sh` usa `ARANDU_MODO=due bash scripts/arandu-weekly.sh`; sem a variável, o script usa
`retomar`, que roda tudo e pula só o que concluiu no dia (o modo da execução manual). `arandu run --due --dry-run --date AAAA-MM-DD` mostra o que rodaria.

**Disco.** `arandu doctor` avisa a 70% de uso e erra a 85%; a partir de 85% as etapas com `pesada: true` no catálogo (full table,
updates BGP, BGP deep) **não começam** (variável `ARANDU_BLOQUEIO_DISCO_PCT` ajusta o limite) e o `host-steps.sh` não reconstrói o
basemap. Reconstruir o basemap exige ~2× o tamanho de uma versão (o `doctor` informa).

**Retenção (`arandu gc`).** A política é um **perfil** de `catalog/retencao.yaml`, escolhido por `--perfil` ou `ARANDU_RETENCAO`:

| Perfil | Uso | `published` | `normalized` | `raw` | armazém |
|---|---|---|---|---|---|
| `desenvolvimento` (padrão) | ambientes de teste e desenvolvimento | indefinido | 2 datas mais recentes | 2 datas mais recentes | 4 versões + `manter_versoes` da fonte |
| `producao` | sugestão para produção; ajuste ao disco disponível | 12 semanas + 1 por mês | 52 semanas | 4 datas | idem |

Camadas aceitam `tudo: true`, `datas: N`, `semanas: N` e `um_por_mes: true`; `protegidas:` lista datas que nunca saem (a data de
referência do replay, 2026-10-11). **Os pisos do código valem para qualquer perfil e ninguém os desliga** (`arandu/retencao.py`): as 4 datas mais recentes
de `published` e as 2 de `raw`/`normalized`, a data do dia, as protegidas, a versão mais recente de cada fonte (mínimo de 2) e
toda versão do armazém ainda citada em `sources[]` de um `published`. Perfil errado só pode resultar em "não apagou". O basemap
guarda a versão servida (`data/tiles/current.json`) e a anterior.

```
docker compose run --rm worker python -m arandu gc --dry-run [--perfil producao] [--date AAAA-MM-DD]   # lista e registra a revisão
docker compose run --rm worker python -m arandu gc --apply                                              # só depois de um --dry-run
```

`--apply` recusa sem um `--dry-run` anterior e com execução em andamento (`arandu.lock`), remove só caminhos exatos (sem
symlink) e grava `data/ops/gc/AAAA-MM-DD.json`. O `gc` não roda sozinho: o `scripts/instalar.sh` não
o agenda, e cada instalação decide se e quando rodá-lo.

**Fragmentos e `compose` do documento de ASN.** Cada produto escreve **seu pedaço** do `asns/{asn}.json` em
`data/build/<data>/fragments/asn/<produto>.jsonl.gz` (uma linha por ASN, em ordem de ASN): `base` (documento de `metricas_ixp_asn`), `ixp_paths`, `sici` e `saude`
(`saude_asn`: alertas, ROAs, validação RPKI). `core/compose.py` junta os pedaços na ordem de `PRODUTOS_ASN` e grava cada documento **uma só vez**,
no fim do `saude_asn`. O índice (`asns/index.json`), os nomes e os caminhos de IXP leem o fragmento `base` em streaming; o RPKI roda **antes** do
índice de ASNs (`asn_indice`), que já nasce com `has_rpki`. O SICI do SCM vira o fragmento `build/<data>/fragments/scm/sici.json.gz`, aplicado na única
escrita de `scm.json.gz` e `maps/scms.geojson`. Produto novo no documento do ASN = um fragmento e o nome em `PRODUTOS_ASN`.
`ARANDU_COMPOSE=off` usa o fluxo sem fragmentos (documentos editados no lugar); `tests/products/test_t2_compose.py` garante o
publicado idêntico nos dois fluxos e uma escrita por arquivo no fluxo com fragmentos (a contagem do fluxo sem fragmentos, para
comparação, está em `tests/contracts/escritas_por_arquivo.json`). O `gc` guarda 2 datas de `build/`.

**Alertas por ASN (`products/alerts/`).** Cada regra é um arquivo em `products/alerts/regras/<id>.py` com `REGRA` (`id`, categoria, severidade,
`versao`, descrição) e `avaliar(ctx)`, que devolve os achados; `registro.py` fixa a ordem de emissão (que desempata a ordenação por severidade e
categoria) e monta o alerta `{id, category, severity, title, detail, refs, desde_versao}`. Regra nova = um arquivo, a entrada em `registro.MODULOS`
e um cenário em `tests/unit/test_alerts_regras.py` (o teste falha se faltar). **Suba `versao` quando a SEMÂNTICA mudar** (limiar, fonte): o manifesto
registra `rules_version` (hash de `id@versão`) e `rules`; séries de alertas só se comparam com a mesma versão (`registro.comparavel`).
`arandu build alerts --recompute --date AAAA-MM-DD` recalcula um snapshot antigo com as regras atuais em `data/alerts/<rules_version>/<data>/`, sem tocar
no publicado. A camada de produtos não importa `api` nem `publish` (`tests/unit/test_camadas.py`).

### Relações entre ASNs (`products/as_relationships`)

Princípios, calibração por estrato, limites e referências: [docs/metodologia-relacoes-asns.md](docs/metodologia-relacoes-asns.md).

Infere provedor/cliente/par/irmão entre ASNs com ao menos um brasileiro (**ARC v1**), com probabilidade, **nível** (`declarado` = ASPA, `confirmado`, `provavel`, `possivel`) e a evidência de cada fonte. Substitui a leitura de "vizinho à esquerda no AS_PATH" como provedor (`upstreams_*` seguem como adjacência, alias deprecado).

- **Entradas:** rampa dos route servers do IX.br (`normalized/<data>/<ptt>/routes-*`), caminhos únicos com ponto de observação por coletor (`normalized/<data>/summary/aspaths-<afi>/<coletor>.tsv.gz`, gravados por `sources/fulltable_routeviews` — `ARANDU_CAMINHOS_VP=0` desliga; fora do armazém de versões; na falta da data usa a coleta semanal anterior, até 10 dias), ASPA (`published/<data>/rpki/aspa_list.json.gz`), CAIDA `as-rel2` (fonte `caida_asrel`: prior e régua, nunca verdade) e CNPJ raiz (irmãos, só `possivel`).
- **Algoritmo** (`sanitiza` → `evidencias` → `propagacao` → `decisao` → `arc`): E0 sanitização; E1/E2 evidência por elo e âncoras (ASPA positivo, rampa RS com suporte, clique do topo); E3 propagação *valley-free* nos caminhos dos coletores (generalização do CoreToLeaf; o elo VP→1º AS não vota); decisão por soma de pesos (log-verossimilhanças aproximadas em `config/as_relationships.yaml`, que é **semântica**: mudar valor = suba `versao` e registre no CHANGELOG) e posterior por softmax. O nível exige fontes **independentes** (ASPA, RS, coletores, clique); CAIDA e irmãos sozinhos nunca passam de `possivel`; ASPA é evidência de alto peso, **não veto** (a disputa vai em `evid.contra`).
- **Saídas:** `published/<data>/as_relationships.json.gz` (um registro por elo) e o fragmento `relacoes` do documento do ASN (`por_asn.py`: provedores, clientes, pares, irmãos, `n_provedores`, `visibilidade`, `single_homed`/`multihomed` — `null` = indeterminado por pouca visibilidade). O alerta `single_homed` (v2) lê o fragmento.
- **Régua:** `python -m products.as_relationships.validacao --date AAAA-MM-DD` roda o algoritmo **sem o ASPA como entrada** e mede precisão/recall contra ele (BR e global), calibração por faixa de `p`, subconjuntos difíceis, retirada de PTT/coletor e estabilidade entre snapshots; a seção "Relações entre ASNs" do painel (`scripts/scorecard.py`) lê o resultado em `data/ops/relacoes/`.

### Como adicionar uma fonte

Fonte nova de CSV, do catálogo até a publicação, em **6 arquivos criados e 2 editados à mão**:

```
python3 -m arandu source new ptts_parceiros --nome "PTTs parceiros" --url https://…/ptts.csv
```

1. O comando cria `catalog/sources/<id>.yaml`, `sources/<id>/{__init__,collect}.py`, `tests/fixtures/raw/<id>/{amostra.csv,README.md}` e
   `tests/sources/test_t1_<id>.py`. A **etapa** (`etapa:`) e a **publicação** (`publicar:`) ficam declaradas no próprio YAML da fonte: nenhum arquivo
   de `catalog/steps/`, nenhum produto e nenhum arquivo existente é editado.
2. Você troca a amostra por um recorte do arquivo real (README: origem, data e o que foi anonimizado), ajusta `parse_csv` ao formato e preenche no
   YAML a descrição, a licença e os campos (`nao_verificado` até conferir; vira pendência).
3. `pytest tests/sources/test_t1_<id>.py` (T1 sem rede), `python3 scripts/catalog_validate.py`, `python3 scripts/gen_docs.py` (regenera `docs/`).
4. `arandu run --only <id> --date AAAA-MM-DD`: grava o bruto comprimido, o normalizado, **copia para `published/<data>/<id>.json.gz`**, registra a
   versão no armazém e a fonte passa a constar em `sources[]` e nos checksums do manifesto.

Fonte que precisa de agregação ou cruzamento continua precisando de um produto (`products/<id>`); para uma de outorga da Anatel há também
`scripts/novo_servico_outorga.py`.

**Backfill do LACNIC (`sources/lacnic_historico`).** Etapa manual (`so_com_only`): guarda o `delegated-lacnic-extended` diário (desde 2020) e as
versões do log de transferências (desde 2016) em `data/historico/lacnic/`, comprimidos, conferidos pelo md5 e retomáveis:
`docker compose run --rm worker python -m sources.lacnic_historico.collect --tipo delegated --desde 2020-01-01 --limite 500` (e `--tipo transfers`).

**Outorgas da Anatel (SCM, SMP, STFC, SeAC).** Vêm do mesmo CSV, baixado uma vez por data
(`sources/anatel_outorgas/download.py`, bruto `anatel-outorgas-AAAA-MM-DD.csv.gz`). `core/outorgas.py::SERVICOS` é o registro dos
serviços; coleta, geocodificação, publicação (`products/outorgas`), leitura na API (`api/outorgas_store.py`) e manifesto derivam dele.
Serviço novo: entrada no registro e `python3 scripts/novo_servico_outorga.py <sigla> --nome "…"` (gera os módulos finos e o catálogo).

## Convenção de diretórios de dados

```
data/
├── raw/<data>/            saídas brutas das coletas (imutáveis)
│   ├── <ptt>/             saída Telnet dos LGs (bgp-v4-*.txt, bgp-v6-*.txt)
│   └── summary/           dumps MRT, arquivos delegated etc.
├── normalized/<data>/     JSON estruturado (por PTT e em summary/), mais caches persistentes de geocodificação
├── build/<data>/          fragmentos intermediários (documento de ASN e outros)
├── sources/<fonte>/<as_of>/   armazém de versões de cada fonte
├── published/<data>/      artefatos servidos: ixps/, asns/, bgp/, rpki/, maps/, summary.json, snapshot_detail.json e,
│                          por último, manifest.json (checksums SHA-256)
└── ops/                   relatórios de execução, uso, disco, memória
```

Os snapshots são **imutáveis** depois de publicados: o `manifest.json` é sempre o último arquivo escrito, e a presença dele indica
que o snapshot está completo e íntegro. A API serve direto de `published/`, sem banco de dados. O formato de cada arquivo publicado
está em [docs/produtos/](docs/produtos/) e no [dicionário](docs/dicionario.md).

---

## Servindo os dados

Em contêineres, a API escuta na porta 8000, o *gate* de acesso na 8001 do contêiner da API e o MCP na 8001 do contêiner `mcp`.
Nenhuma delas é publicada no host: só o nginx do `frontend` (porta 80), que encaminha `/api/`, `/auth/`, `/mcp` e `/health`. Numa
instalação local, portanto:

| O quê | Endereço |
|---|---|
| Interface web | `http://localhost` |
| API REST | `http://localhost/api/v1/…` |
| Documentação interativa e OpenAPI | `http://localhost/api/v1/docs` e `/api/v1/openapi.json` |
| MCP (Streamable HTTP) | `http://localhost/mcp` |

### API REST (`api/`)

FastAPI servida pelo uvicorn. `api/store.py` lê `published/` e mantém em memória, por data, o que cada assunto precisa. O papel de
cada arquivo está em [api/descricao-da-pasta.md](api/descricao-da-pasta.md); os principais:

- `api/main.py`: aplicação, middlewares (CORS, GZip, limites, cabeçalhos de cache) e registro das rotas;
- `api/routes/`: rotas por domínio; `api/services/` e `api/repos/`: regras e leitura dos arquivos por assunto;
- `api/query.py` e `api/query_catalogo.py`: consulta genérica (filtros compostos, agregações, proximidade) usada pela API e pelo MCP;
- `api/limites.py`, `api/concurrency.py` e `api/ratelimit.py`: orçamento por cliente, simultaneidade e limites por rota;
- `api/auth/`: contas e sessão (login OAuth com Google, LinkedIn ou PeeringDB), política de acesso, chaves de MCP e manutenção.

A lista completa de rotas está no OpenAPI e, com a tool do MCP que atende cada uma, em [docs/cobertura.md](docs/cobertura.md).

### Servidor MCP (`mcp_server/`)

Expõe os snapshots como tools, resources e prompts. Usa o mesmo `Store` e os mesmos serviços da API: só a forma das tools é própria.
A API é consultada só para verificar a chave de MCP.

As tools são definidas em `tools_*.py` com o nome original; `mcp_server/nomes.py` registra o nome por domínio (`asn_*`, `ixp_*`,
`rota_*`, `operadora_*`, `municipio_*`, `uf_*`, `outorga_*`, `infra_*`, `historico_*`) e oculta o nome original como alias (não
aparece em `tools/list`, segue chamável e devolve `aviso_obsoleta`). As tools consolidadas (`viz`, `asn_rede`, `ixp_participantes`…)
estão em `consolidadas.py`. `guia.py` é a tabela *tarefa → tool* que gera as instruções e o bloco `tarefas` do `describe_schema`.
**Tool nova:** nome de domínio, linha em `guia.py` (o T5 falha se uma tool visível não estiver lá) e argumentos de teste em
`tests/products/mcp_contract.py`. Resources por entidade (`arandurape://asn/{n}`…) e prompts temáticos ficam em `recursos.py`.

### Frontend (`frontend/`)

React, Vite, TypeScript e Tailwind. Consome a API REST; o build estático é servido pelo nginx do contêiner `frontend`. As páginas de
entidade são compostas por blocos que declaram de que dado dependem e de que fontes vêm (`features/<entidade>/index.ts`).

**Rota nova da SPA e o 404 real.** O nginx (`docker/nginx-frontend.conf`) só responde 200 com o `index.html` quando o primeiro
segmento do caminho é uma rota da SPA, listada no `map $uri $rota_spa`; qualquer outro caminho recebe o mesmo `index.html` com status
404, e a SPA mostra a página "não encontrada". Sem essa lista, toda URL inventada respondia 200 (*soft 404*): buscadores indexavam
páginas vazias, verificadores de link não achavam link quebrado e a resposta HTTP contradizia a tela. O nginx não executa o
roteador do React, então a lista das rotas válidas tem de estar nele. Ao criar uma rota em `frontend/src/main.tsx`, acrescente o
primeiro segmento dela à expressão do `map`; `frontend/src/components/layout/rotas.test.ts` compara as duas listas nos dois sentidos e falha se uma
rota de `main.tsx` faltar no `map` (ou sobrar no `map` sem rota). Caminhos com `location` própria (`/api/`, `/auth/`, `/mcp`,
`/health`, `/tiles/`, `/meta/`, sitemaps, `robots.txt`, `llms.txt`, `/.well-known/`) e arquivos que existem no build não passam
pelo `map`. Conferir depois de mudar: `bash tests/nginx/test_gate.sh` e as páginas de `config/paginas_publicas.json` respondendo
200.

---

## Configuração

### Arquivos de configuração (`config/`)

| Arquivo | Conteúdo |
|---|---|
| `settings.yaml` | Parâmetros globais (`pipeline.data_dir`, paralelismo etc.) |
| `ixps.yaml` | PTTs do IX.br coletados, com host Telnet, porta e timeout |
| `pix.yaml` | Coordenadas dos PIX (pontos de interconexão) |
| `peeringdb_ixps.yaml` | IXPs externos e do IX.br para a coleta no PeeringDB |
| `cdns.yaml` | CDNs e CAPs acompanhadas, com seus ASNs |
| `bgp_communities.yaml` | Communities BGP conhecidas |
| `as_relationships.yaml` | Pesos do algoritmo de relações entre ASNs (semântico: mudou, suba a versão) |
| `curada_marcas_operadoras.yaml` | Marcas comerciais das operadoras |
| `municipios-centroides.json`, `municipios-referencia.json` | Centroides e cadastro de referência dos municípios |
| `paginas_publicas.json` | Páginas públicas do site (sitemap e conferência pós-implantação) |

[config/descricao-da-pasta.md](config/descricao-da-pasta.md) traz os detalhes.

### Variáveis de ambiente (`.env`)

O [`.env.example`](.env.example) lista as variáveis, comentadas. As principais:

| Variável | Uso |
|---|---|
| `APP_BASE_URL` | Endereço público da aplicação (CORS e retorno do OAuth) |
| `JWT_SECRET`, `INTERNAL_API_TOKEN` | Assinatura das sessões e token das chamadas internas (aquecimento) |
| `GOOGLE_*`, `LINKEDIN_*`, `PEERINGDB_CLIENT_*` | Login OAuth |
| `MCP_KEY_ATIVA`, `MCP_KEY_PEPPER` | Chave de MCP por conta |
| `ALLOWED_IPS`, `ACCESS_POLICY_MODE` | Redes isentas de login e modo da política de acesso |
| `SITE_*` | Identidade da instância: nome, endereço, contato e código-fonte (`core/site.py`) |
| `PEERINGDB_API_KEY` | Chave da API do PeeringDB para as coletas (opcional) |
| `WEB_NETWORK_NAME` | Rede Docker externa, com o overlay `docker-compose.no-nginx.yml` |
| `NGINX_REAL_IP_INC` | Include de IP real do nginx (`docker/nginx-real-ip*.inc`) |

`DATA_DIR` (raiz dos dados; `/data` nos contêineres) e `LOG_FORMAT` (`json` ou `text`) só valem fora dos contêineres, ao rodar um
módulo direto no host.

---

## Execução e implantação

### Pipeline

```bash
# Execução manual:
bash scripts/arandu-weekly.sh

# Cron (o scripts/instalar.sh instala esta linha, com o horário escolhido):
0 4 * * *  cd /opt/arandurape && ARANDU_MODO=due flock -n /tmp/arandurape-run.lock bash scripts/arandu-weekly.sh >> logs/arandu.log 2>&1
```

### Implantação

```bash
sudo bash restart-safe.sh       # com Docker rootless: bash restart-safe.sh, como o usuário do serviço
```

O `restart-safe.sh` reconstrói e recria `api`, `mcp` e `frontend` juntos, verifica a saúde e volta à imagem anterior (`:previous`)
se algo falhar. Fora da implantação, `docker compose up -d` também serve, desde que suba os serviços juntos: **nunca** suba um serviço
isolado num ambiente com nginx, porque ele resolve o host `api` na partida e derruba o site.

### RPKI

Não há serviço Routinator permanente. `scripts/rpki-avulso.sh` roda `routinator vrps` (perfil `rpki` do compose, no bridge padrão do Docker, sem rede própria) antes
do worker, dentro do lock do pipeline, grava `data/cache/rpki/vrps.json` e o contêiner termina; a etapa `rpki_collector` só lê o
arquivo (recusa arquivo com mais de `RPKI_MAX_IDADE_H`, padrão 12 h). O cache RPKI fica no volume `rpki_cache`; sem ele a primeira
execução é longa (timeout `RPKI_TIMEOUT_FRIO_S`, padrão 4 h; a morno `RPKI_TIMEOUT_S`, 45 min). A imagem é fixada por tag e digest
em `docker-compose.exemplo.yml` (`ROUTINATOR_TAG` sobrepõe); para atualizar, troque os dois e confira a saída com `sources.rpki_collector`.

### Executar um módulo individualmente

```bash
# Exemplo: reexecutar só o parser BGP de uma data, com o lock do pipeline
bash scripts/arandu-exclusivo.sh -- docker compose --profile worker run --rm worker python -m arandu run --only bgp_ixp --date AAAA-MM-DD
```

### Reparar um snapshot com falha

```bash
docker compose --profile worker run --rm worker python -m arandu repair --date AAAA-MM-DD --dry-run   # lista o que falta
bash scripts/arandu-exclusivo.sh -- docker compose --profile worker run --rm worker python -m arandu repair --date AAAA-MM-DD
```

O `arandu repair` reexecuta, com os dependentes, toda etapa do catálogo cuja saída primária não existe no snapshot. Se a etapa
for a do RPKI, rode antes `bash scripts/rpki-avulso.sh` (a etapa só lê `data/cache/rpki/vrps.json`).

### Remover um snapshot

```bash
bash delete-snapshot.sh --date AAAA-MM-DD
```

---

## Dependências principais

| Biblioteca | Uso |
|---|---|
| `fastapi`, `uvicorn` | API REST e servidor ASGI |
| `mcp` | SDK do Model Context Protocol (servidor MCP) |
| `mrtparse` | Dumps MRT (RouteViews, RIPE RIS) |
| `maxminddb` | Leitura da base de geolocalização DB-IP City Lite (formato `.mmdb`) |
| `structlog` | Logging estruturado |
| `pydantic` | Validação do catálogo e esquemas da API |
| `slowapi` | Limites por rota |
| `cachetools` | Caches LRU |
| `pyjwt` | Tokens de sessão |
| `pyyaml` | Configuração e catálogo |

As dependências diretas, com versões fixadas, estão em `requirements.txt` (e `requirements-dev.txt` para os testes); os locks
`requirements.lock` e `requirements-dev.lock` trazem também as transitivas, com hash de cada arquivo, e são regravados por
`bash scripts/travar-dependencias.sh` depois de qualquer mudança nos `.txt`.

**SBOM e vulnerabilidades.** `bash scripts/sbom.sh` gera o SBOM (CycloneDX) das dependências Python de produção, do frontend e dos
componentes que o build compila (o nginx do repositório do nginx.org e o ngx_brotli, que nenhum scanner de imagem detecta) e o
verifica com o Grype; `--imagens` acrescenta as imagens construídas. Reprova vulnerabilidade alta ou crítica com correção publicada no
que vai para produção; o ferramental de desenvolvimento só aparece no relatório. A CI roda o das dependências a cada push e o das
imagens à noite (sobre a última versão publicada, não a `main`) e na tag, quando anexa os SBOMs à release. Exceção — componente
afetado no papel, mas não na prática — vai para `config/vex.openvex.json` (OpenVEX) com a justificativa, nunca desligando a
verificação. O Dependabot (`.github/dependabot.yml`) propõe as atualizações; num PR de pip, regrave os locks.

---

## Para quem chega (pessoas e modelos de linguagem)

- **Regras de trabalho:** [AGENTS.md](AGENTS.md). **Princípios, com o porquê:** a seção "Diretrizes de projeto" deste guia.
- **Onde estão os dados de um snapshot:** `data/published/<data>/`. Formato de cada arquivo: [docs/produtos/](docs/produtos/) e
  [docs/dicionario.md](docs/dicionario.md).
- **Como a API e o MCP leem os dados:** sem banco de dados, pelo `Store` (`api/store.py`), compartilhado pelos dois.
- **Como consultar dados em lote:** `api/query.py`, com filtros compostos (`and`/`or`/`not`), operadores (`eq`, `ne`, `gt`,
  `contains`, `ncontains`, `within_radius`, `near`…), agregações e ordenação. As coleções e seus campos estão em
  `api/query_catalogo.py` (`COLLECTIONS`) e são servidos por `GET /api/v1/schema` e pela tool `describe_schema` do MCP.
- **Onde estão os PTTs do IX.br:** `config/ixps.yaml`.
- **Como acrescentar uma fonte:** a seção "Como adicionar uma fonte" acima (`python -m arandu source new`). Fonte que exige
  agregação ou cruzamento precisa também de um produto em `products/<id>`.
- **Conceitos:**
  - *ASN direto* × *ASN originador*: direto é o primeiro AS do AS_PATH (tem sessão com o route server do PTT); originador é o
    último (anuncia o prefixo).
  - *Snapshot imutável*: gravado o `manifest.json`, nada muda em `published/<data>/`.
  - *Idempotência*: cada módulo aceita `--date` e pula o que já está feito; `--force` refaz.
