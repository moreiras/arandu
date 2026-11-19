<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Histórico do LACNIC (delegated-extended diário e log de transferências)

`lacnic_historico` · tipo **bruta** · ativa

Backfill, comprimido e retomável, dos arquivos diários do LACNIC: o delegated-lacnic-extended do archive/ (uma versão por dia, desde 2003; coletado desde 2020) e as versões diárias do log de transferências (desde 2016-08-30). Serve ao ciclo de vida do IPv4; nenhum produto lê estes arquivos ainda.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.lacnic_historico.collect` |
| Publicável | não (exposição: nenhuma) |
| Política de falha | opcional |
| Cadência (origem atualiza) | diaria |
| Coleta hoje → alvo | manual → manual |
| Frescor máximo | nao_verificado |
| Chaves | `asn`, `prefixo` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/lacnic_historico/` |

## Origem e licença

- **URL:** https://ftp.lacnic.net/pub/stats/lacnic/{archive/AAAA/delegated-lacnic-extended-AAAAMMDD, transfers/AAAA/transfers_AAAAMMDDThhmmssZ.json}
- **Formato:** texto delimitado por | (delegated) e JSON (transferências)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** README do diretório não declara termos (estudo de 2026-10-09). Arquivos públicos do LACNIC; a coleta é gentil (1 conexão, pausa, limite por execução).

## Saídas


## Dicionário de campos

_Sem dicionário de campos declarado._

## Limites

Fora de raw/ e normalized/ (data/historico/lacnic/...): o gc não toca. Retomável: o que já existe é pulado. Os md5 do archive/ são conferidos.

## Retenção

- **bruto:** indefinida (histórico); ~1 MB comprimido por dia no delegated

## Quem usa

- **Fontes derivadas:** `ipv4_delegated`

## Pendências (nao_verificado)

- Termos de uso dos arquivos do LACNIC não confirmados.
- Só `ipv4_delegated` lê o histórico.
