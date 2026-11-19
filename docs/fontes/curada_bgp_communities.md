<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Communities BGP de operadores (config/bgp_communities.yaml)

`curada_bgp_communities` · tipo **curada** · ativa

Tabela de communities BGP (≈ 15 mil linhas) de operadores brasileiros com ASN, valor, tipo, categoria e descrição, usada para interpretar rotas.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `config/bgp_communities.yaml` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | irregular |
| Coleta hoje → alvo | semanal → sob_demanda |
| Frescor máximo | 400d |
| Chaves | `asn` |
| Entradas | — |

## Origem e licença

- **URL:** —
- **Formato:** YAML mantido à mão em config/
- **Licença:** Curadoria do projeto (dados factuais; fontes citadas)
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** Fontes citadas no arquivo: docs.ix.br (política de communities v4.3 e tabela v2.1, 2024-08-14) e wiki do Brasil Peering Forum (Lista de Communities BGP); gerado em 2026-06-28.

## Saídas


## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `communities[].asn / operator` | int\|str | ASN e nome do operador que define a community. | — | routing_analysis → routing_analysis.json |
| `communities[].community` | str | Valor (standard AAAA:NNN, extended ou large). | — | routing_analysis → routing_analysis.json |
| `communities[].type / category` | str | Tipo (standard/extended/large) e categoria funcional (local_preference, blackhole…). | — | routing_analysis → routing_analysis.json |
| `communities[].description` | str | Descrição do efeito, em texto livre. | Reproduz documentação de terceiros. | routing_analysis → routing_analysis.json |
| `communities[].source` | str | Origem da linha (ex.: bpf_wiki). | Proveniência por linha. | — |

## Limites

Transcrição de documentação de operadores e de uma wiki; pode estar desatualizada e conter erros.

## Retenção

- **normalizado:** git

## Quem usa

- **Produtos:** `routing_analysis`

## Pendências (nao_verificado)

- Licença da wiki do Brasil Peering Forum e dos PDFs do IX.br para republicação das descrições.
