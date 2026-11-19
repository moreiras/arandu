<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Listas do LACNIC (transferências e infraestrutura crítica)

`lacnic_listas` · tipo **bruta** · ativa

Log de transferências de recursos (transfers_latest.json, append-only) e lista de recursos de infraestrutura crítica do LACNIC. Só guardados, comprimidos, todo dia.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.lacnic_listas.collect` |
| Publicável | não (exposição: nenhuma) |
| Política de falha | opcional |
| Cadência (origem atualiza) | diaria |
| Coleta hoje → alvo | diaria → diaria |
| Frescor máximo | 3d |
| Chaves | `prefixo`, `asn` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/listas_numeracao/` |

## Origem e licença

- **URL:** https://ftp.lacnic.net/pub/stats/lacnic/{transfers/transfers_latest.json, critical_infra/critical-infra-AAAAMMDD}
- **Formato:** JSON (transferências) e CSV rir|pais|tipo|recurso|cantidad|fecha|estado|orgid|id_documento|nombre (infraestrutura crítica)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** README do diretório não declara termos (estudo de 2026-10-09).

## Saídas

- **Bruto (raw/):** `summary/lacnic-transfers-{as_of}.gz`, `summary/lacnic-critical-infra-{as_of}.gz`

## Dicionário de campos

_Sem dicionário de campos declarado._

## Limites

Só guarda o bruto comprimido; quem os lê é a fonte derivada `ipv4_listas`. Arquivos em Latin-1 no Registro.br.

## Retenção

- **bruto:** 365 versões no armazém (as listas públicas só guardam a versão atual)

## Quem usa

- **Fontes derivadas:** `ipv4_listas`

## Pendências (nao_verificado)

- Termos de uso dos arquivos do LACNIC não confirmados.
