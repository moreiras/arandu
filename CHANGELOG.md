# Notas de versão

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
