# catalog/ — catálogo declarativo de fontes, produtos e etapas

> Licença: AGPL-3.0-or-later — Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit

Descreve, em YAML, tudo o que o pipeline coleta, produz e publica. É a fonte única da documentação de `docs/`
(`python3 scripts/gen_docs.py`; `--check` no CI) e o que o executor `arandu` lê para calcular a ordem das etapas. O esquema de cada
arquivo é validado por `core/catalog/schema.py` (`python3 scripts/catalog_validate.py`); campo desconhecido é erro.

## Conteúdo

| Caminho | Papel |
|---|---|
| `sources/<id>.yaml` | Uma fonte (coletada, derivada ou curada): origem, licença, `uso_comercial`, `publicavel`, cadência, armazém de versões, saídas e dicionário de campos. Vira `docs/fontes/<id>.md`. |
| `products/<id>.yaml` | Um produto publicado: entradas, arquivos em `published/`, chaves e dicionário de campos. Vira `docs/produtos/<id>.md`. |
| `steps/<id>.yaml` | Uma etapa do pipeline: módulo e argumentos, o que produz, `depois_de`, política de falha, tentativas, janelas. A ordem resultante está em `docs/etapas.md`. |
| `retencao.yaml` | Perfis de retenção do `arandu gc` (`desenvolvimento`, `producao`). |

## Regras

- Valor desconhecido é `nao_verificado`, com a explicação em `pendencias`; nunca um valor inventado.
- Licença e termos citam o trecho lido e a data da leitura.
- O `id` é o nome estável da fonte, do produto ou da etapa: logs, relatórios e documentação o usam. Etapa renomeada ganha alias em
  `ALIASES_ETAPA` (`core/catalog/loader.py`).
- Módulo novo em `sources/` sem `source.yaml`, ou arquivo publicado sem declaração, falha em `tests/products/test_t3_catalogo.py`.
