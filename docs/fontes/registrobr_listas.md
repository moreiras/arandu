<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Listas de numeração do Registro.br (transferências e recuperação)

`registrobr_listas` · tipo **bruta** · ativa

Transferências diretas de IPv4 (com e sem bloco original) e recursos em recuperação e já recuperados, publicados pelo Registro.br. Só guardadas, comprimidas, todo dia (a origem mantém só a versão atual).

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.registrobr_listas.collect` |
| Publicável | não (exposição: nenhuma) |
| Política de falha | opcional |
| Cadência (origem atualiza) | diaria |
| Coleta hoje → alvo | diaria → diaria |
| Frescor máximo | 3d |
| Chaves | `prefixo`, `asn` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/listas_numeracao/` |

## Origem e licença

- **URL:** https://ftp.registro.br/pub/numeracao/{transferencias-diretas-latest, transferencias-diretas-lacnic-latest, recuperacao-latest, recuperados-latest}
- **Formato:** texto delimitado por | (Latin-1)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** Sem termos de uso explícitos no diretório (estudo de 2026-10-09); confirmar com o NIC.br antes de publicar derivados.

## Saídas

- **Bruto (raw/):** `summary/registrobr-transferencias-diretas-{as_of}.gz`, `summary/registrobr-transferencias-diretas-lacnic-{as_of}.gz`, `summary/registrobr-recuperacao-{as_of}.gz`, `summary/registrobr-recuperados-{as_of}.gz`

## Dicionário de campos

_Sem dicionário de campos declarado._

## Limites

Só guarda o bruto comprimido; quem os lê é a fonte derivada `ipv4_listas`. Arquivos em Latin-1 no Registro.br.

## Retenção

- **bruto:** 365 versões no armazém (as listas públicas só guardam a versão atual)

## Quem usa

- **Fontes derivadas:** `ipv4_listas`

## Pendências (nao_verificado)

- Termos de uso das listas do Registro.br não confirmados.
