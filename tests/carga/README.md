# Teste de carga e capacidade

Mede quantos usuários simultâneos o serviço aguenta, navegando no site e consultando o MCP ao mesmo tempo, em cenários diferentes
(`cenarios.yaml`). Fora do CI: roda contra um ambiente real, com os dados de verdade.

## Peças

| Arquivo | O que faz |
|---|---|
| `gravar_paginas.js` | Visita cada tipo de página num navegador real e grava o que ela pede (HTML, estáticos, tiles, API), com a entidade trocada por marcador (`{asn}`, `{cnpj}`, `{data}`…). |
| `locustfile.py` | Repete as páginas sem navegador. Tipos de usuário: **visitante** (visita com carga inicial do app e navegação dentro dele, leitura entre as páginas, cache do navegador), **assistente** (conversa no MCP: sessão, `tools/list`, 5 a 20 chamadas com pausa, sessão encerrada), **api** (scripts que paginam e consultam) e **abusivo** (um IP só, sem pausa, nas rotas caras). Entidades sorteadas com Zipf sobre listas ordenadas por procura. |
| `canario.js` | Navegador real visitando páginas durante a carga: tempo até o conteúdo e erros de console. |
| `rodar.sh` | Mede a rede até o alvo, liga o amostrador no servidor (`scripts/mem_sample.py`, a cada 5 s), roda o canário e o Locust, recolhe as amostras e o log do nginx do período e gera o relatório. |
| `relatorio.py` | Por degrau de usuários: req/s, falhas, tempo no servidor (log do nginx, sem a rede), memória e CPU, canário; aplica os critérios (`slo`) e diz o maior degrau que os cumpriu. |

## Como rodar

```bash
python3.12 -m venv .venv-carga && .venv-carga/bin/pip install -r tests/carga/requirements.txt
bash tests/carga/rodar.sh fumaca --alvo http://HOST --ssh HOST_SSH          # valida o testador (~2 min)
bash tests/carga/rodar.sh misto  --alvo http://HOST --ssh HOST_SSH          # ~32 min, até 1.000 usuários
```

`CARGA_ALVO` e `CARGA_SSH` no ambiente dispensam as opções. Saída em `tests/carga/saida/<cenário>-<UTC>/` (`relatorio.md`,
`resumo.json`, brutos). `--regravar` grava as páginas de novo (depois de mudar o frontend ou de trocar o snapshot).

## Requisitos do alvo

- **Confiar no `X-Forwarded-For` vindo do gerador.** Cada usuário virtual tem um IP próprio (198.18.0.0/15, faixa de testes da
  RFC 2544; IPv6 em 2001:db8::/32), para os orçamentos por cliente se comportarem como na vida real. Sem isso todos dividem o
  orçamento de um IP e o teste mede o limite, não a capacidade. Inclua no `real-ip.inc` do alvo o endereço com que o gerador chega a ele
  (`/auth/diag`, campo `ip_visto`, sem o cabeçalho): `set_real_ip_from ENDEREÇO;` e `nginx -s reload` no frontend. Tráfego externo
  entra no contêiner por DNAT, com a origem preservada: o gateway da bridge só aparece para quem acessa do próprio host. O `rodar.sh`
  recusa rodar se o alvo não honrar o cabeçalho.
- **IP do gerador na allowlist** (`CARGA_XFF_SETUP`, padrão: o host do alvo) só para montar as listas de entidades.
- **Log do nginx com tempos** (`log_format temporizado` em `docker/nginx-frontend.conf`): sem ele o relatório sai sem o tempo no
  servidor.
- SSH sem senha ao servidor para o amostrador e o log; sem `--ssh`, só o lado do cliente.
- Não rode ao lado do pipeline, a menos que esse seja o cenário: `rodar.sh` registra se ele estava rodando.

## Limites do gerador

- **Rede:** o tempo do cliente inclui a rede do gerador até o alvo (o relatório mostra o RTT e a banda medidos antes). Estáticos e
  tiles ficam fora por padrão (`estaticos: false`): em produção vêm do cache da Cloudflare. Se o gerador receber mais de 80% da banda
  medida, o relatório avisa, e os degraus seguintes medem a rede: rode de uma máquina mais perto do alvo.
- **CPU:** um processo do Locust ocupa um núcleo; com aviso de CPU alta no `locust.log`, use `--processos N`.

## Fidelidade e simplificações

- A página é repetida como foi gravada, com outras entidades. Tiles do mapa repetem as faixas gravadas (o mapa de cada município pediria
  outras), o que favorece o cache.
- Navegação dentro do app: sem HTML e sem as chamadas que toda página faz na carga inicial; GET repetido na mesma visita não volta ao
  servidor (cache do navegador e do React Query, simplificado).
- O assistente segue uma mistura fixa de tools (`TOOLS` no `locustfile.py`), não um modelo de verdade.
- Teste de carga gera linhas no log de uso e no log do nginx do alvo (User-Agent `arandu-carga/1`).
