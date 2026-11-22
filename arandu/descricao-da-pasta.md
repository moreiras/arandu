# arandu/ — executor e linha de comando do pipeline

> Licença: AGPL-3.0-or-later — Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit

Executa o pipeline a partir do catálogo (`catalog/`): calcula a ordem das etapas, aplica a política de falha de cada uma, grava um
relatório por execução, usa lock e retoma execuções interrompidas. Roda no contêiner `worker`
(`docker compose --profile worker run --rm worker python -m arandu …`); o cron o chama por `scripts/arandu-weekly.sh`. O uso está
na seção "Executor `arandu`" do [guia do desenvolvedor](../guia-do-desenvolvedor.md).

## Arquivos

| Arquivo | Papel |
|---|---|
| `__main__.py`, `cli.py` | Linha de comando: `plan`, `run`, `continuo`, `memoria`, `status`, `doctor`, `repair`, `store`, `source new`, `build alerts --recompute`, `gc`. |
| `executor.py` | Ordem calculada, política de falha por etapa (crítica, opcional, `usar_ultima_valida`), relatório em `data/ops/runs/AAAA-MM-DD.json`, retomada (`--retomar`) e modo por cadência (`--due`). |
| `runner.py` | Executa uma etapa: subprocesso em produção, no próprio processo no `--compare` e nos testes. |
| `publicacao.py` | Janela de publicação: no `--due`, as etapas sem fonte (produtos, manifesto) só rodam a cada `ARANDU_PUBLICACAO_DIAS` dias. |
| `lockfile.py` | Lock por `flock` em `data/ops/arandu.lock` (sobrevive a contêiner morto, ao contrário de lock por pid). |
| `compare.py` | `run --compare`: reexecuta as etapas reprodutíveis num diretório temporário e compara com o publicado, pelo critério do `scripts/replay.py`. |
| `repair.py` | `repair`: acha etapas sem saída primária num snapshot e as reexecuta, com as dependentes. |
| `medicao.py` | `memoria`: pico de memória (`pico_mem_mb` dos relatórios) e duração por etapa contra o `memoria_mb` do catálogo. |
| `status.py` | `status`: última versão de cada fonte, frescor e falhas recentes. |
| `ops.py` | `doctor`: disco, inodes, lock, versões, catálogo e última execução. |
| `retencao.py` | `gc`: plano e remoção pelos perfis de `catalog/retencao.yaml`, com pisos em código que nenhum perfil desliga. |
| `compactacao.py` | `gc --compactar`: passa um snapshot ao `layout_version` 2 (`core/layout.py`) e desfaz, com verificação byte a byte. |
| `novafonte.py` | `source new <id>`: gera uma fonte nova de CSV, do catálogo à publicação. |

## Invariantes

- A ordem das etapas sai do catálogo e é fixada em `tests/contracts/ordem_etapas.json`; mudança intencional regrava o arquivo.
- Ids de etapa renomeados seguem aceitos em `--only`, `build`/`collect` e na retomada (`ALIASES_ETAPA` em `core/catalog/loader.py`).
- `gc --apply` só roda depois de um `--dry-run` e nunca com uma execução em andamento.
