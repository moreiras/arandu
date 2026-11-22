# scripts/ — instalação, operação, geradores, testes e ferramentas avulsas

> Licença: AGPL-3.0-or-later — Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit

Scripts executados diretamente (`bash scripts/x.sh` ou `python3 scripts/x.py`), fora dos pacotes do pipeline. O cabeçalho de cada
um traz o uso e as variáveis.

## Instalação e operação do servidor

| Arquivo | Papel |
|---|---|
| `instalar.sh` | Prepara um servidor: `.env` com segredos gerados, `data/` para a API sem root, fontes do mapa, serviços no ar, cron do pipeline e da manutenção das contas, vigia de saúde (`--simular`, `--coletar`). |
| `preparar-dados-api-sem-root.sh` | Entrega `data/auth/`, `ops/usage`, `ops/uso_conta` e `cache/br11` ao UID da API com permissões restritas, para ela rodar sem root e com `data/` só leitura. |
| `arandu-weekly.sh` | O que o cron roda: RPKI avulso, `arandu run` no worker, etapas de host e, se ligado, a comparação de paridade; alerta em caso de falha. |
| `arandu-exclusivo.sh` | Roda um comando segurando o mesmo lock do pipeline, para coleta ou produto feito à mão nunca rodar ao lado dele. |
| `rpki-avulso.sh` | Roda o Routinator avulso (perfil `rpki`), grava `data/cache/rpki/vrps.json` e termina; a etapa `rpki_collector` só lê o arquivo. |
| `host-steps.sh` | Etapas de host do pipeline (aquecimento da API, mapa de fundo, relatório de disco), que dependem do `docker compose` no host. |
| `lib-steps.sh` | Cronometragem das etapas do pipeline (para ser carregado com `source`). |
| `lib-docker.sh` | Detecta o Docker rootless e o endereço do daemon do usuário (para ser carregado com `source`; usado por `instalar.sh`, `restart-safe.sh` e `preparar-dados-api-sem-root.sh`). |
| `vigia-saude.sh` | Reinicia, com recuo, o serviço que o Docker marcou como `unhealthy` (timer do systemd em `docker/systemd/`). |
| `vigia-externo.sh` | Verificação de ponta a ponta pela URL pública: frontend, API e MCP, cada um com o seu critério. |
| `espelhar-dados.sh` | Espelha o `data/` (menos o bruto) em outra instância por rsync sobre SSH quando há snapshot publicado novo; agendado depois do pipeline (`ESPELHO_*` no `.env`). |
| `alerta-telegram.sh` | Envia ao chat configurado a mensagem lida da entrada padrão (só falhas), com intervalo mínimo entre repetições. |
| `atualiza-faixas-cloudflare.sh` | Regera `docker/nginx-real-ip-cloudflare.inc` a partir das faixas publicadas pela Cloudflare. |
| `post-deploy-check.sh`, `post_deploy_check.py` | Verificação pós-implantação, só leitura contra a instância no ar (`/health` e versão, rotas-chave, contatos exigem login, MCP, páginas). |
| `disk-report.sh` | Uso de disco por tipo e por data e inodes, em `data/ops/disk/`. |
| `mem_sample.py` | Amostrador de memória da API e do worker durante o pipeline. |
| `fetch-basemap-fonts.sh` | Baixa os glifos do mapa de fundo para `data/tiles/_assets/fonts/` (idempotente). |
| `build-basemap-tiles.sh` | Gera uma nova versão do mapa de fundo vetorial (PMTiles). |
| `validate-basemap-tiles.sh` | Valida um mapa de fundo recém-gerado e o promove a versão atual. |
| `rollback-basemap.sh` | Invalida uma versão do mapa de fundo e volta à anterior válida. |

## Geradores (arquivos versionados derivados)

| Arquivo | Gera |
|---|---|
| `gen_docs.py` | `docs/` a partir do catálogo (fontes, produtos, etapas, dicionário, licenças) e `frontend/public/catalogo.json`; `--check` no CI. |
| `gen_cobertura.py` | `docs/cobertura.md`, a matriz API × MCP × interface; rota sem decisão falha o CI. |
| `gen_openapi.py` | `frontend/src/types/openapi.json` (o OpenAPI da API). |
| `gen_sitemap.py` | `config/paginas_publicas.json` (sitemap, `robots.txt`, `llms.txt`). |
| `catalog_validate.py` | Valida o catálogo. |
| `novo_servico_outorga.py` | Os arquivos de um novo serviço de outorga da Anatel a partir da entrada em `core/outorgas.py`. |
| `build-malha-municipal.py` | `frontend/public/malha-municipal.pmtiles` e `.json` (malha municipal do IBGE). |
| `build-municipio-centroides.py` | `municipios-centroides.json` (em `frontend/public/` e `config/`). |
| `build-municipios-referencia.py` | `config/municipios-referencia.json` (nome, UF e área dos municípios). |
| `scrape_pix_locations.py`, `geocode_pix_entries.py`, `inject_pix_from_llm.py` | `config/pix.yaml`: endereços dos PIX das páginas do IX.br, geocodificação dos que faltam e inclusão manual dos que o raspador não processa. |

## Testes e conferência

| Arquivo | Papel |
|---|---|
| `ci.sh` | O mesmo que a integração contínua roda: regras de camada, sintaxe dos scripts e pytest (T0–T5); `--docker` na imagem-base de produção, `--quick` sem a suíte lenta. |
| `front-test.sh` | Testes do frontend em contêiner: tsc, vitest e build; `--gen-tipos` regenera os tipos do OpenAPI. |
| `sbom.sh` | SBOM CycloneDX (dependências Python e do frontend, componentes compilados; `--imagens` inclui as imagens) e verificação com o Grype; o mesmo que os jobs `sbom` da CI. |
| `travar-dependencias.sh` | Regrava `requirements.lock` e `requirements-dev.lock` (transitivas e hashes) a partir dos `requirements*.txt`, na imagem-base de produção. |
| `replay.py`, `replay_expected.json` | Reconstrói o publicado de uma data e compara com o original; as diferenças explicadas ficam no JSON. |
| `scorecard.py` | Painel com testes, contratos, replay, tempos, disco, uso e coleta (`data/ops/scorecard/`). |
| `conferir_estratos_snapshot.py` | Confere as relações entre ASNs de um snapshot publicado: rebaixo por estrato, cobertura da probabilidade calibrada e estabilidade. |
| `codemod_1_2_2.py` | Codemod da renomeação das pastas de coleta e análise para `sources/` e `products/`; os testes dos atalhos (`collector/`, `enrich/`, `analysis/`) o usam como referência do mapeamento. |

## Medições e ferramentas avulsas

| Arquivo | Papel |
|---|---|
| `mem-profile.py` | Perfil de memória da API sobre um `data/` local, por cache e por número de processos. |
| `medir_rdap_contatos.py` | Mede o ritmo seguro do RDAP do Registro.br (nunca grava valores de contato). |
| `medir_rodizio_alice.py` | Mede a cobertura do rodízio de leitura do Alice-LG sobre os normalizados já gravados. |
| `medir_siasg_contratos.py` | Mede o custo da coleta de contratos públicos numa amostra e projeta a varredura completa. |
| `fetch_br_routes_one_collector.py` | Baixa um só coletor do RouteViews e grava `br-routes-v4.json.gz` de um snapshot, para depurar a análise de AS_PATH. |
| `spike_relacoes_vp.py` | Mede o custo de registrar o ponto de observação por caminho no parse do MRT. |
| `sici-fase0/` | Validação exploratória do arquivo bruto do SICI (totais por CNPJ e mês, cruzamentos com outorgas e APNIC). |
