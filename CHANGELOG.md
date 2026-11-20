# Notas de versão

## v2.0.5

- Chave de MCP com o prefixo da instância: `<SITE_MCP_ESQUEMA>_mcp_<id>_<segredo>` (ex.: `obint_mcp_…`), antes fixo em `arandu_mcp_`. A
  verificação aceita qualquer esquema no formato, porque quem autentica é o id com o HMAC do segredo: as chaves já emitidas
  (`arandu_mcp_…`) continuam válidas. Formato e prefixo ficam em `core/site.py`, usados pela API, pelo servidor MCP e pelo perfil.

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
