# serve/ — capacidades servidas pela API e pelo MCP

> Licença: AGPL-3.0-or-later — Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit

`capabilities/` declara o que a API e o MCP servem. De uma capacidade declarada (`<entidade>.yaml`) nascem as rotas REST
(`api/capacidades.py`), a tool do MCP (`mcp_server/capacidades.py`) e as entradas do contrato; a matriz API × MCP × interface fica em
[docs/cobertura.md](../docs/cobertura.md) (`python3 scripts/gen_cobertura.py`).

## Arquivos

| Arquivo | Papel |
|---|---|
| `capabilities/scm.yaml`, `smp.yaml`, `stfc.yaml`, `seac.yaml` | Outorgas da Anatel por serviço: operações (lista, detalhe), filtros, privacidade e descrições para a API e o MCP. |
| `capabilities/_manuais.yaml` | Rotas escritas à mão em `api/routes/` e como cobrem o MCP: `mcp:` (a tool que atende) ou `sem_mcp:` (justificativa); `sem_ui:` justifica a ausência na interface. |

## Regras

- Toda rota GET de dados que não esteja `deprecated` precisa de uma capacidade declarada ou de uma entrada em `_manuais.yaml`; lacuna
  sem justificativa falha o CI (`tests/unit/test_cobertura.py`).
- Gerar a cobertura não pode alterar o OpenAPI (`python3 scripts/gen_openapi.py --check`) nem o inventário do MCP.
