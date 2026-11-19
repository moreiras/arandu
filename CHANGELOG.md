# Notas de versão

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
