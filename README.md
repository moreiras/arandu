<p align="center"><img src="marca/arandurape-logo.svg" alt="Arandurapé" width="260"></p>

# Arandurapé

**Arandurapé** mapeia a Internet brasileira em *snapshots* datados e imutáveis: BGP do IX.br e da tabela global, Registro.br e LACNIC,
PeeringDB, RPKI, APNIC e dados abertos da Anatel (outorgas e acessos declarados ao SICI), entre outras fontes públicas. Os dados saem
por uma interface web, uma API REST e um servidor MCP (Model Context Protocol), para consulta por assistentes de IA.
O projeto é uma iniciativa da **Internet Bit a Bit**, livre, gratuita e de código aberto.

> *Arandu*, em guarani, é conhecimento, sabedoria; *rape* é caminho.

Todo número tem fonte e data: o snapshot e, quando a fonte tem calendário próprio, o mês de referência. O que é inferido ou estimado
vem rotulado como tal. Contatos e dados de pessoa física não são públicos.

## Licenças: código e dados são diferentes

- **Código:** [GNU Affero General Public License v3 ou posterior](LICENSE) (AGPL-3.0-or-later). Se você modificar o software e o
  oferecer a outras pessoas pela rede, a AGPL (§13) exige que ofereça a elas o código-fonte modificado. A página *Sobre* de cada
  instância mostra o endereço do código-fonte (variável `SITE_CODIGO_FONTE` do `.env`; o padrão é
  [github.com/moreiras/arandu](https://github.com/moreiras/arandu)) e a versão em execução (arquivo `VERSION`, também no rodapé).
  Se você modificar o software, aponte `SITE_CODIGO_FONTE` para o seu código.
- **Dados:** cada fonte segue a licença e os termos de quem a publica, com a atribuição correspondente; a AGPL **não** se aplica a
  eles. A tabela de fontes, licenças e usos permitidos está em [docs/licencas.md](docs/licencas.md) e, fonte a fonte, em
  [docs/fontes/](docs/fontes/). Fontes marcadas como `nao_verificado` ou `restrito` não devem ser reaproveitadas comercialmente sem
  ler os termos de origem.
- **Terceiros:** `tests/ipv6/v6bench/` é uma cópia modificada do [v6bench](https://github.com/CEPTRO-br/v6bench) e continua sob a
  licença MIT do original (ver `tests/ipv6/v6bench/MODIFICACOES.md`).

## Como funciona

```
sources/<fonte>/     coleta (collect.py) e fontes derivadas (enrich.py), uma pasta por fonte
products/<produto>/  análises sobre os dados coletados
publish/             monta o snapshot publicado (manifesto e checksums)
arandu/  catalog/    executor do pipeline e catálogo declarativo das fontes, etapas e produtos (licença, cadência, campos)
api/  mcp_server/    API REST (FastAPI) e servidor MCP; leem os arquivos publicados, sem banco de dados em tempo de execução
frontend/            interface web (React, Vite, TypeScript)
core/                utilitários compartilhados
config/  docker/     configuração e imagens
scripts/             instalação, operação, geradores de documentação e execução dos testes
tests/               testes automatizados (T0 a T7) e o dataset sintético
```

Os dados ficam em `data/{raw,normalized,published}/<data>/` e **não** fazem parte deste repositório. Cada pasta de código tem um
`descricao-da-pasta.md` com o papel de cada arquivo; a arquitetura e as diretrizes de projeto estão no
[guia do desenvolvedor](guia-do-desenvolvedor.md).

## Instalar e rodar

Pré-requisitos: Docker e Docker Compose v2. Node e npm não são necessários na máquina: o frontend é construído e testado em contêiner.

**Num servidor**, use o instalador, como o usuário do serviço (no grupo `docker`), na raiz do clone:

```bash
bash scripts/instalar.sh --simular   # mostra o que faria, sem mudar nada
bash scripts/instalar.sh             # 1ª vez: cria o .env com os segredos gerados e para (código 3) para você preencher o resto
bash scripts/instalar.sh             # 2ª vez: confere o .env, prepara data/, sobe os serviços, agenda o pipeline e o vigia de saúde
```

O instalador prepara `data/` para a API rodar sem root, baixa as fontes do mapa de fundo, constrói e sobe os serviços, instala o cron
diário do pipeline e da manutenção das contas e o vigia de saúde (systemd). Ele não coleta: `--coletar` dispara a primeira coleta e
publicação; sem ele, o cron faz isso. Por padrão exige 80 GB livres em disco (`INSTALAR_DISCO_MIN_GB`). Na implantação, ponha o
serviço atrás de um proxy de borda, com o firewall do host aceitando só esse proxy, e mantenha cópia de segurança cifrada, fora do
servidor, de `data/auth`, `data/published`, `data/sources` e do `.env`.

Com **Docker rootless** (recomendado), rode o instalador e o `restart-safe.sh` como o usuário dono do daemon, sem sudo: os dois
detectam o modo. O instalador acerta as permissões de `data/` de dentro de um contêiner, passa o `DOCKER_HOST` ao cron e instala o
vigia no systemd do usuário. Veja a seção 9 do [recomendacoes-deployment.md](recomendacoes-deployment.md).

**O `docker-compose.yml` é local.** O repositório traz o `docker-compose.exemplo.yml`; o instalador o copia para `docker-compose.yml`
(fora do git) na primeira execução, e é essa cópia que os scripts usam. Edite a cópia se a sua instalação precisar (portas, tetos de
memória, volumes). Sem o instalador, copie à mão: `cp docker-compose.exemplo.yml docker-compose.yml`. Ao atualizar o repositório,
compare a cópia com o exemplo (`diff docker-compose.exemplo.yml docker-compose.yml`) e traga o que mudou.

**Para desenvolvimento local:**

```bash
cp .env.example .env                 # preencha ao menos APP_BASE_URL e JWT_SECRET (openssl rand -hex 32); nunca versione o .env
cp docker-compose.exemplo.yml docker-compose.yml   # cópia local (fora do git); edite se preciso
sudo bash restart-safe.sh            # constrói e sobe api, mcp e frontend juntos, com verificação de saúde e retorno à versão anterior
```

Suba sempre os serviços juntos (`restart-safe.sh` ou `docker compose up -d`), nunca um isolado: o nginx do frontend resolve o
endereço da API na partida. Atrás de um proxy reverso que já existe no host, defina `WEB_NETWORK_NAME` no `.env` para usar o overlay
`docker-compose.no-nginx.yml`.

Só o nginx do frontend é publicado no host (porta 80); ele encaminha a API e o MCP:

| Serviço | Endereço padrão |
|---|---|
| Interface web | `http://localhost` |
| API REST | `http://localhost/api/v1/…` |
| Documentação interativa da API e OpenAPI | `http://localhost/api/v1/docs` e `/api/v1/openapi.json` |
| Servidor MCP (Streamable HTTP) | `http://localhost/mcp` |

## Pipeline

Sem dados coletados, a interface mostra "nenhum snapshot". O pipeline (coleta, produtos e publicação) roda pelo executor `arandu`, no
contêiner `worker`:

```bash
W="docker compose --profile worker run --rm worker"
$W python -m arandu plan                          # ordem calculada das etapas
$W python -m arandu run --date AAAA-MM-DD          # executa o pipeline do dia
$W python -m arandu repair --date AAAA-MM-DD --dry-run   # etapas sem saída num snapshot
bash scripts/arandu-weekly.sh                     # o que o cron roda: RPKI avulso, worker, etapas de host
```

[docs/etapas.md](docs/etapas.md) descreve cada etapa e [docs/fontes/](docs/fontes/) cada fonte. As fontes têm limites de taxa e termos
próprios; leia-os antes de coletar. Coleta ou produto rodado à mão passa por `scripts/arandu-exclusivo.sh`, que usa o mesmo lock do
pipeline.

## Usar a API e o MCP

Numa instância no ar (os exemplos usam `http://localhost`; troque pelo endereço dela):

```bash
curl -s http://localhost/api/v1/snapshots                 # snapshots publicados
curl -s http://localhost/api/v1/asns/1916                 # documento de um AS
curl -s http://localhost/api/v1/schema                    # coleções e campos da consulta genérica (POST /api/v1/query/<coleção>)
```

Toda rota aceita `?date=AAAA-MM-DD`; sem ela, vale o snapshot mais recente. A documentação completa das rotas está em
`/api/v1/docs`. Sem login, a API e o MCP entregam uma prévia (listas curtas, as datas mais recentes, orçamento por minuto, hora e dia);
o resto exige conta. Contatos nunca saem pelo MCP e, pela API, só com conta e com cota.

**MCP:** o endereço é `/mcp` (Streamable HTTP). Sem chave, o cliente recebe a prévia. Com conta, a página *Perfil* do site gera uma
chave pessoal e mostra o comando pronto para cada cliente, por exemplo:

```bash
claude mcp add --transport http arandurape http://localhost/mcp --header "Authorization: Bearer arandu_mcp_…"
```

A chave de MCP precisa estar ligada na instância (`MCP_KEY_ATIVA=1` e `MCP_KEY_PEPPER` no `.env`). O próprio servidor MCP manda ao
cliente as instruções de uso e a tabela tarefa → tool, e a tool `describe_schema` lista as coleções e receitas de consulta.

## Desenvolvimento e testes

```bash
pip install --require-hashes -r requirements-dev.lock   # Python 3.12, a versão da imagem de produção
bash scripts/ci.sh            # o mesmo que a integração contínua roda: regras de camada, sintaxe dos scripts e pytest (T0 a T5)
bash scripts/ci.sh --docker   # idem, na imagem-base de produção
bash scripts/front-test.sh    # frontend: tsc, vitest e build, em contêiner
```

Os testes rodam sobre um dataset sintético (`tests/synth/`) e amostras de cada fonte (`tests/fixtures/raw/<fonte>/`, com a origem
descrita no README de cada pasta); nenhum precisa de rede nem de `data/`. Os níveis que exigem ambiente próprio (E2E com Playwright,
laboratório IPv6) estão descritos em [AGENTS.md](AGENTS.md), seção "Como testar"; o teste de carga, em
[tests/carga/README.md](tests/carga/README.md).

[AGENTS.md](AGENTS.md) reúne as regras de trabalho no código (para pessoas e para agentes de programação) e o
[guia do desenvolvedor](guia-do-desenvolvedor.md) traz a arquitetura e as diretrizes de projeto.

### Sobre o uso de IA

O código, os testes e a documentação deste projeto foram escritos com uso extensivo do Claude (Anthropic), sob direção e revisão do
mantenedor. As regras que orientam esse trabalho são as mesmas para qualquer contribuição e estão em [AGENTS.md](AGENTS.md).

## Reportar problemas

- **Erro nos dados ou na interface:** escreva para arandurape@internetbitabit.com.br com o endereço da página, a data do snapshot e o
  que esperava ver.
- **Vulnerabilidade de segurança:** veja [SECURITY.md](SECURITY.md); não abra uma discussão pública.
