# T7 IPv6: o Arandurapé visto de clientes IPv4, IPv6, NAT64 e SIIT

O T7 sobe um laboratório de rede e confere, ponta a ponta (nginx → gate → API), como o Arandurapé enxerga
cada tipo de cliente. Os outros níveis de teste nunca passam um pacote IPv6 pela rede: o pytest usa
`TestClient`, o E2E roda em localhost e a rede do Compose não tem IPv6. A lógica de IP tem testes
unitários (`tests/test_client_ip.py`, `tests/unit/test_anon_rede_s12.py`); o T7 confere que ela continua
valendo quando um pacote IPv6, ou traduzido, atravessa a pilha real.

Não depende de servidores de produção, de certificados nem da Internet durante a execução: só Docker e
Kathará. Roda sem root e sem módulo de kernel, no macOS (OrbStack ou Docker Desktop) e no Linux.

## O laboratório

É o [v6bench](https://github.com/CEPTRO-br/v6bench) do Ceptro.br, numa **cópia modificada** em
[v6bench/](v6bench/). O que mudou, e por quê, está em [v6bench/MODIFICACOES.md](v6bench/MODIFICACOES.md).

| Dispositivo | Endereços | Papel |
|---|---|---|
| `gateway` | `192.168.0.1`, `2001:db8:1::1` | roteador da LAN; rotas para NAT64 e SIIT |
| `dns` | `192.168.0.53`, `2001:db8:1::53` | BIND com a zona `lab.arandurape.test` e DNS64 só para o cliente NAT64 |
| `nat64` | `192.168.0.64`, `2001:db8:1::64` | TAYGA + NAT44, prefixo `2001:db8:64::/96` |
| `siit` | `192.168.0.46`, `2001:db8:1::46` | TAYGA: `192.168.0.40 ↔ 2001:db8:4::28`, `192.168.46.1 ↔ 2001:db8:1::80` |
| `alvo` | `192.168.0.80`, `2001:db8:1::80` | Arandurapé: gate (8001), API (8000) e nginx (8080, IPv4 e IPv6) |
| `dual_client` | `192.168.0.10`, `2001:db8:1::10` | cenários `dual`, `ipv4`, `ipv6` |
| `ipv4_client` | `192.168.0.40` | cenários `dual`, `ipv4`, `siit` |
| `ipv6_strict_client` | `2001:db8:1::60` | cenários `dual`, `ipv6`; sem rota para o NAT64 |
| `ipv6_nat64_client` | `2001:db8:1::664` | cenários `ipv4` (DNS64 + NAT64), `ipv6` |

Cada cenário é um nome: `dual.lab.arandurape.test` (A e AAAA), `ipv4.…` (só A), `ipv6.…` (só AAAA) e
`siit.…` (A `192.168.46.1`, que o SIIT leva ao IPv6 do alvo).

**O alvo** ([alvo/Dockerfile](alvo/Dockerfile)) é a imagem real da API (`Dockerfile.api`) com o nginx e os
**mesmos arquivos de configuração do frontend** (`docker/nginx-frontend.conf`, `nginx-api-proxy.inc`,
`nginx-security-headers.conf`). O `real-ip.inc` é o do exemplo "sem borda": no laboratório o nginx é a
borda e não confia em `X-Forwarded-For` de ninguém. O dado é o dataset sintético (`tests/synth`). A
allowlist do alvo tem um IPv6 e um IPv4: `2001:db8:1::10/128` e `192.168.0.40/32`.

O nginx é o do Debian, com brotli, e não o alpine da imagem do frontend. O que se testa é a configuração
(`listen [::]`, `real_ip`, `auth_request`, `X-Real-IP`), não o binário.

## O que é verificado

Em cada cenário de cada cliente ([checks/run](checks/run)), depois conferido por
[verificar.py](verificar.py):

1. **O que a API vê** (`GET /auth/diag`): IP, versão, se está na allowlist e o nível (`allowed` ou
   `anon`), contra [esperado.json](esperado.json). Esse arquivo é contrato: mudou, revise como mudança de
   comportamento.
2. **Cabeçalho forjado é ignorado:** com `X-Forwarded-For` e `X-Real-IP` falsos vindos do cliente, o IP
   visto não muda.
3. **Plano do ScanAPI** ([scanapi.yaml](scanapi.yaml)): `/health`, `/api/v1/snapshots` e `/api/v1/ixps`
   respondem 200. É poucas rotas `open` de propósito: o plano gerado do OpenAPI inteiro mediria sobretudo
   limite de taxa, cota anônima e parâmetros, não IPv6.
4. **Log de uso sem IP:** o `data/ops/usage/*.jsonl` do alvo existe, não está vazio e não contém nenhum
   endereço do laboratório (regra de privacidade do `AGENTS.md`).

## O que o resultado esperado mostra

| Cliente / cenário | A API vê | Allowlist |
|---|---|---|
| dual, por IPv6 | `2001:db8:1::10` | sim |
| dual, por IPv4 | `192.168.0.10` | não |
| só IPv4 | `192.168.0.40` | sim |
| só IPv4, **via SIIT** | `2001:db8:4::28` | **não**: o IPv4 da allowlist aparece como IPv6 |
| só IPv6 | `2001:db8:1::60` | não |
| IPv6, nome só com A (**NAT64**) | `192.168.0.64` (o IPv4 do tradutor) | não |

Duas consequências, que são do desenho e não defeitos do teste:

- **Atrás de SIIT, todo cliente IPv4 traduzido cai no mesmo /64.** O orçamento anônimo agrupa IPv6 por /64
  (`rede_do_ip`), então esses clientes dividem um único orçamento. Num SIIT-DC (RFC 7755, Informational)
  seria a Internet IPv4 inteira num balde só.
- **Atrás de NAT64, os usuários só-IPv6 aparecem como o IPv4 do tradutor** e dividem o orçamento, como num
  CGNAT.

## Como rodar

Kathará num venv próprio, para não misturar com o `.venv-mcp`:

```bash
python3 -m venv ~/.venvs/kathara
~/.venvs/kathara/bin/pip install -r tests/ipv6/requirements.txt
~/.venvs/kathara/bin/python -m kathara check     # instala o plugin de rede do Kathará no Docker
KATHARA="$HOME/.venvs/kathara/bin/python -m kathara" bash tests/ipv6/run.sh
```

- `--sem-build` reaproveita as imagens já construídas.
- `RESULTADOS=DIR` escolhe onde ficam os resultados; o padrão é um temporário, impresso no fim.
- Em `RESULTADOS` ficam:
  - `status/` com o estado de cada cliente e cenário;
  - `diag/` com o `/auth/diag` normal e o forjado;
  - os CSV do ScanAPI;
  - `logs/`;
  - `alvo/` com o log de uso e os logs da API e do gate.
- Código de saída 0 só se o laboratório e a verificação passarem.

**Requisitos:** Docker com o plugin do Kathará (o `kathara check` instala; no macOS é o
`katharanp_vde`), Python 3.11 ou mais novo no host para o `zonefile_creator.py` e o `verificar.py`. Na
primeira vez, as imagens `kathara/base` e `kathara/bind` são baixadas.

**Num ambiente de teste Linux** vale o mesmo, num diretório de trabalho próprio. O laboratório só cria redes e contêineres
do Kathará e não toca no Compose do Arandurapé. Coleta e produto pesados continuam passando pelo
`scripts/arandu-exclusivo.sh`; o T7 é leve.

**Na CI:** job `ipv6 (T7, noturno)` em `.github/workflows/ci.yml`. Roda no agendamento noturno e no
`workflow_dispatch`, como o E2E, e guarda os resultados como artefato `t7-ipv6`.

## Execuções

| Data | Ambiente | Resultado |
|---|---|---|
| 2026-11-16 | macOS arm64, OrbStack (Docker 29.8.2), Kathará 3.8.4 | 10/10 cenários conforme `esperado.json`; 30 requisições do ScanAPI com 200; log de uso com 22 linhas e nenhum IP; 32 s do zero (construindo as imagens), 20 s com `--sem-build` |
| — | Linux (ambiente de teste, GitHub Actions) | não executado ainda |
