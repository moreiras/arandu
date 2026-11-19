# tests/ — testes automatizados

> Licença: AGPL-3.0-or-later — Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit

Nenhum teste do CI precisa de rede nem de `data/`: rodam sobre amostras de cada fonte e sobre um dataset sintético. Os comandos de
cada nível estão na seção "Como testar" do [AGENTS.md](../AGENTS.md).

## Níveis

| Nível | O que confere | Onde |
|---|---|---|
| T0 | Unidade: regras, utilitários, política de acesso, limites, privacidade | `unit/`, `test_*.py` desta pasta |
| T1 | Coletores e fontes derivadas sobre amostras gravadas, sem rede | `sources/`, `fixtures/raw/<fonte>/` |
| T2 | Pipeline sobre o dataset sintético, com resultados de referência (`--update-golden` regrava; revise o diff) | `products/test_t2_*.py`, `synth/` |
| T3 | Formato dos artefatos publicados e catálogo | `products/test_t3_*.py`, `contracts/schemas/` |
| T4 | API: contrato por operação, privacidade, cache, paginação e fuzz do OpenAPI | `products/test_t4_*.py`, `contracts/api_contract.json` |
| T5 | MCP: inventário e uma chamada por tool | `products/test_t5_mcp.py`, `contracts/mcp_contract.json` |
| T6 | E2E no navegador (Playwright): acesso, listas, acessibilidade, orçamento de requisições, erros de console | `e2e/` |
| T7 | IPv6: laboratório Kathará com clientes IPv4, IPv6, NAT64 e SIIT | `ipv6/` |

T0 a T5 rodam em `scripts/ci.sh`; T6 e T7, no agendamento noturno da integração contínua.

## Pastas

| Pasta | Papel |
|---|---|
| `unit/` | Testes de unidade (T0). |
| `sources/` | Um teste T1 por fonte. |
| `fixtures/raw/<fonte>/` | Amostras de cada fonte, com um README de origem, data, recorte e anonimização. |
| `synth/` | Gerador do dataset sintético e resultados de referência ([synth/README.md](synth/README.md)). |
| `products/` | T2 a T5. |
| `contracts/` | Contratos e esquemas: API, MCP, ordem das etapas, orçamento de páginas, esquemas dos artefatos. |
| `fakes/` | Dublês: LG por Telnet, etapa falsa do executor. |
| `e2e/` | T6 (`run.sh`; pré-requisitos no cabeçalho). |
| `ipv6/` | T7 ([ipv6/README.md](ipv6/README.md)); `ipv6/v6bench/` é cópia modificada do v6bench, sob MIT. |
| `nginx/` | Teste do gate no nginx (`test_gate.sh`). |
| `carga/` | Teste de carga e capacidade, fora do CI ([carga/README.md](carga/README.md)). |
