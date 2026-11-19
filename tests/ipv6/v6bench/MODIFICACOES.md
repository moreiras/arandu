# v6bench: cópia modificada para o Arandurapé

Esta pasta é uma cópia **modificada** do [v6bench](https://github.com/CEPTRO-br/v6bench), o laboratório
Kathará do Ceptro.br que implementa as recomendações de teste de integração do Internet-Draft
[draft-ietf-v6ops-ipv6-app-testing](https://datatracker.ietf.org/doc/draft-ietf-v6ops-ipv6-app-testing/)
(ainda não é RFC). Ela é a base do nível de teste **T7 IPv6** do Arandurapé ([../README.md](../README.md)).

## Origem e licença

| Item | Valor |
|---|---|
| Repositório | https://github.com/CEPTRO-br/v6bench |
| Commit de origem | `c61474ecdf7dcd8da63cd77cc141955a3d58cf93` (2026-11-06) |
| Licença | MIT ([LICENSE](LICENSE), mantido sem alteração) |
| Importação no Arandurapé | commit `testes(ipv6): importa o v6bench original (CEPTRO-br, commit c61474e, MIT)` |

Os arquivos vindos do v6bench, modificados ou não, **continuam sob a licença MIT** do original, com o aviso
de copyright do [LICENSE](LICENSE). Assim as mudanças podem voltar ao projeto de origem sem relicenciamento.
Só os arquivos novos que existem apenas para o Arandurapé levam o cabeçalho AGPL-3.0-or-later
([comparar_com_original.sh](comparar_com_original.sh) e, fora desta pasta, todo o `tests/ipv6/`).

**Ficaram de fora da importação** os quatro `.deb` do Jool 4.1.15
(`kathara/{nat64,siit}/jool_debfiles/`): são binários GPLv2, cuja distribuição exigiria oferecer o
código-fonte, e o laboratório deixou de usar o Jool (modificação 1).

## Como ver as diferenças

- No histórico do Arandurapé: `git log -- tests/ipv6/v6bench` (o primeiro commit é o original intacto) e
  `git diff <commit da importação> -- tests/ipv6/v6bench`.
- Sem depender do histórico: `bash tests/ipv6/v6bench/comparar_com_original.sh` clona o original no commit de
  origem e mostra o `diff -ruN`.

## Modificações

Cada uma resolve um problema concreto. As de 1 a 9 são genéricas, sem nada do Arandurapé, e servem
para propor ao projeto de origem. A coluna "Issue" aponta a issue do v6bench que a modificação atende.

| # | Modificação | Arquivos | Issue |
|---|---|---|---|
| 1 | TAYGA no lugar do Jool | `kathara/nat64.startup`, `kathara/siit.startup`, `images/translator/Dockerfile`, `kathara/lab.conf` | — |
| 2 | Laboratório sem root | `kathara/lab.conf`, `kathara/gateway.startup`, `run_lab.sh` | — |
| 3 | SIIT aponta para o alvo | `kathara/siit.startup`, `zonefile_creator.py` | — |
| 4 | DNS64 só para o cliente NAT64 | `kathara/dns/etc/bindfiles/named.conf.options` | — |
| 5 | Prefixo NAT64 específico da rede | `nat64.startup`, `gateway.startup`, `ipv6_strict_client.startup`, `named.conf.options` | — |
| 6 | Alvo local dentro do laboratório | `zonefile_creator.py`, `run_lab.sh` | #3 |
| 7 | Imagens prontas, laboratório sem Internet na execução | `images/client/Dockerfile`, `images/translator/Dockerfile`, `kathara/lab.conf` | #2 |
| 8 | Execução orquestrada, cópia descartável e código de saída | `run_lab.sh`, `test_runner.sh`, `kathara/lab.conf`, `kathara/dns.startup`; removido `srv_entrypoint.sh` | — |
| 9 | Porta configurável e verificações próprias por cenário | `test_runner.sh` | #5 |
| 10 | Correções menores | `zonefile_creator.py`, `scanapi_conversor.sh` | — |

### 1. TAYGA no lugar do Jool

**Problema.** O Jool é módulo de kernel: os nós `nat64` e `siit` eram privilegiados, montavam `/usr/src` e
`/lib/modules` e compilavam o módulo (dkms) contra o kernel do host a partir de `.deb` só amd64. Não roda
em macOS (Docker Desktop e OrbStack rodam numa VM sem cabeçalhos do kernel), nem em arm64, e altera o kernel
do host.

**Mudança.** O TAYGA 0.9.2 do Debian (imagem `v6bench/translator:local`, sobre a `kathara/base`) traduz em
espaço de usuário sobre um TUN.
- **NAT64 com estado:** tradução sem estado para um pool IPv4 privado (`192.168.255.0/24`) mais NAT44
  (`MASQUERADE`) no mesmo nó.
- **SIIT:** o TAYGA 0.9.2 não tem as faixas de EAM da RFC 7757, só `map` de um endereço para um endereço.
  Basta: `192.168.0.40 ↔ 2001:db8:4::28` (o cliente IPv4) e `192.168.46.1 ↔ <IPv6 do alvo>`.

**Limites.** O TAYGA 0.9.2 segue a RFC 6145 (substituída pela RFC 7915), é menos completo que o Jool em
ICMP e fragmentação, e os resultados não são estritamente comparáveis aos de um laboratório com Jool. Para
o teste de aplicações HTTP isso não pesa.

### 2. Laboratório sem root

**Problema.** O Kathará recusa dispositivos privilegiados sem root ("You must be root in order to start
Kathara devices in privileged mode"), por isso o `run_lab.sh` original usava `sudo`.

**Mudança.** Nenhum dispositivo é privilegiado. O TUN é criado com `mknod /dev/net/tun c 10 200` dentro
do contêiner (o Docker permite esse dispositivo por padrão) e o encaminhamento IPv4/IPv6 é ligado com
`[sysctl]` no `lab.conf` (antes, `sysctl -w` nos `.startup`, que só funciona com privilégio). O
`run_lab.sh` não usa mais `sudo`.

### 3. SIIT aponta para o alvo

**Problema.** O `siit.startup` original calculava `BASE_IPV6` e não o usava: o mapeamento apontava para um
IPv6 fixo (`2a00:1450:4001:c21::8b`, de um serviço de terceiros). O cenário SIIT do `ipv4_client` não
testava o alvo.

**Mudança.** O `zonefile_creator.py` grava `TARGET_IPV4` e `TARGET_IPV6` em `shared/env/target.env`, a
partir dos **mesmos** endereços da zona de DNS, e o `siit.startup` mapeia `192.168.46.1` para
`TARGET_IPV6` (o primeiro IPv6 da zona, em ordem). Sem IPv6 do alvo, o nó falha alto em vez de montar um
cenário que "passa" sem testar nada.

### 4. DNS64 só para o cliente NAT64

**Problema.** Com `dns64 … { clients { any; }; }`, o cliente dual-stack também recebia AAAA sintetizado
para nomes só com A. Preferindo IPv6 (RFC 6724), o cenário "ipv4" do `dual_client` passava pelo NAT64.

**Mudança.** `clients { 2001:db8:1::664; }` (o `ipv6_nat64_client`) e `mapped { any; }`. O teste T7
confirma: o `dual_client` no cenário `ipv4` chega ao alvo por IPv4.

### 5. Prefixo NAT64 específico da rede

**Problema.** A RFC 6052 proíbe usar o prefixo bem conhecido `64:ff9b::/96` para endereços IPv4 não globais,
e o TAYGA aplica essa regra. Com o alvo dentro do laboratório (IPv4 privado), o NAT64 não funcionaria.

**Mudança.** `2001:db8:64::/96` em todo o laboratório: tradutor, rota no `gateway`, bloqueio no
`ipv6_strict_client` e DNS64.

### 6. Alvo local dentro do laboratório

**Problema.** O original só testa um serviço na Internet: depende de rede externa, de um serviço de
terceiros e de IPv6 na saída do Docker.

**Mudança.**
- `zonefile_creator.py` aceita `--target-ipv4` e `--target-ipv6` (então não resolve o domínio), além de
  `--out-dir` e `--env-out`.
- `run_lab.sh -t DIR` mescla um overlay no laboratório: `lab.conf.fragment` é acrescentado ao `lab.conf`, e
  o resto (pastas de dispositivo, `*.startup`, `shared/`) é copiado por cima.
- Com `-4`/`-6`, o laboratório não usa a Internet.

O modo original (alvo na Internet, domínio resolvido) continua no código, mas **não foi testado depois das
mudanças**.

### 7. Imagens prontas

**Problema.** Os clientes instalavam o ScanAPI com `pip` a cada execução, e os tradutores, o Jool com `apt`:
lento e dependente da Internet.

**Mudança.** `images/client/Dockerfile` (`kathara/base` + ScanAPI 2.13.2) e `images/translator/Dockerfile`
(`kathara/base` + TAYGA), construídas antes (`v6bench/client:local`, `v6bench/translator:local`).

### 8. Execução orquestrada, cópia descartável e código de saída

**Problema.** No original, os servidores rodavam `srv_entrypoint.sh` (dormir 30 s e esperar os clientes
pararem de responder a ping) e o `run_lab.sh` segurava um `kathara exec gateway sleep infinity` até o fim.
Os arquivos gerados (zona, ambiente, resultados) iam para a própria árvore do repositório. E o resultado
saía sempre com código 0, inútil para CI.

**Mudança.**
- `run_lab.sh` copia `kathara/` para um temporário, gera ali zona e variáveis e sobe o laboratório.
- Confere que todos os dispositivos estão rodando (falha na hora se algum saiu) e roda o `test_runner.sh` de
  cada cliente com `kathara exec`.
- Copia `shared/results` para `-r` e sai com 0 só se todo cenário de todo cliente terminou `ok`. Os arquivos
  de estado ficam em `results/status/<cliente>-<cenário>`.
- `-w DISPOSITIVO` espera `/shared/target/ready.sh` dar certo no dispositivo antes de rodar os clientes
  (até `WAIT_SECONDS`) e falha com mensagem clara se ele nunca ficar pronto. Sem isso, um alvo quebrado
  custava `WAIT_SECONDS` por cenário.
- `-x DISPOSITIVO` roda `/shared/target/collect.sh` no dispositivo depois dos testes, para coletar o que
  existe só no alvo.
- Removidos `srv_entrypoint.sh` e os `[entrypoint]` do `lab.conf`. O `dns.startup` passa a iniciar o `named`
  como daemon, em vez de `exec`.

### 9. Porta configurável e verificações próprias por cenário

**Mudança no `test_runner.sh`.**
- **Porta:** `BASE_PORT` (vazio = porta padrão do protocolo).
- **Espera genérica:** até o alvo responder pelo caminho do cenário, com `curl` e limite em `WAIT_SECONDS`,
  padrão 120. Substitui as esperas separadas por DNS, SIIT e NAT64.
- **Variáveis exportadas** (`set -a`): o ScanAPI resolve `${VAR}` do ambiente.
- **ScanAPI opcional:** só roda se houver plano.
- **Verificações próprias:** um executável em `/shared/checks/run` é chamado por cenário com `CLIENT`, `SDOM`
  e `BASE_URL` (issue #5: outro cliente além do ScanAPI).

### 10. Correções menores

- `zonefile_creator.py`: o NS padrão era `2001:db8::53`, e o `dns` do laboratório é `2001:db8:1::53`. O
  registro NS apontava para `ns.lab.`, fora da zona, e passou a apontar para `ns`. Endereços em ordem,
  para zona determinística.
- `scanapi_conversor.sh`: nova opção `-o` (onde gravar o plano). Deixou de gravar
  `kathara/shared/env/test_vars.env`; imprime o modelo do arquivo de variáveis para o `run_lab.sh -e`.
  Continua usando `sed -r` e `grep -P` do GNU, como o original (não roda no `sed`/`grep` do macOS).
- `README.md`: aviso de cópia modificada no topo, requisitos (TAYGA no lugar do Jool, Kathará sem root) e
  fluxo de uso novo do `run_lab.sh`.

## O que não foi feito

- **HTTPS com o nome real (issue #4):** a proposta de views no BIND por endereço de resolvedor não foi
  implementada. O T7 usa HTTP, que é o que o nginx do Arandurapé serve (TLS termina na borda, fora do
  repositório).
- **Jool como opção:** removido, não mantido em paralelo, porque não há como testá-lo sem módulo de kernel.
- **Modo "alvo na Internet":** mantido, mas sem teste depois das mudanças.

## Onde foi testado

| Ambiente | Resultado |
|---|---|
| macOS arm64, OrbStack (Docker 29.8.2), Kathará 3.8.4 | 2026-11-16: as 10 combinações de cliente e cenário passaram com o alvo local (detalhes em [../README.md](../README.md), seção "Execuções") |
| Linux (ambiente de teste, GitHub Actions) | não testado ainda |
