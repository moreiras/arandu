# publish/ — publicação do snapshot

> Licença: AGPL-3.0-or-later — Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit

Fecha o snapshot em `published/{date}/`. Os documentos de cada assunto são escritos pelos produtos (`products/`); aqui ficam a
sanidade da coleta, o manifesto com os checksums e o caminho de build em um só processo.

## Arquivos

| Arquivo | Papel |
|---|---|
| `manifesto.py` | Última etapa do build: grava `manifest.json` (metadados do pipeline, `checks` da coleta, `sources[]`, `rules_version`) e os checksums SHA-256 de todos os arquivos publicados (`python -m publish.manifesto --date AAAA-MM-DD`). |
| `coleta_checks.py` | Sanidade da coleta: compara o snapshot com o anterior e com limites fixos (PTTs coletados, número de ASNs…) e marca `coleta_ok`/`parcial` no manifesto, sem bloquear a publicação. |
| `snapshot_builder.py` | Executa os passos de `products/passos.py` em sequência, num só processo, e fecha com o manifesto. Usado pelo replay e por operações pontuais sobre snapshots já publicados: `--asn-health-only` (RPKI e alertas por ASN, depois da coleta RPKI) e `--detail-only` (grava `snapshot_detail.json`). O pipeline normal roda os mesmos passos pelo `arandu`. |

## Invariantes

- `manifest.json` é o **último** arquivo escrito: a API só lista datas que o têm, então o snapshot só aparece completo.
- `published/{date}/` é imutável depois de publicado; as operações aditivas (`--detail-only`, arquivos novos de um produto) não
  reescrevem o que já existe.
- A saúde do ASN (`--asn-health-only`) roda depois da coleta RPKI, porque usa os VRPs de `rpki/vrp_list.json.gz`.
