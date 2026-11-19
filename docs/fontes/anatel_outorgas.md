<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Cadastro de prestadoras da Anatel (CSV nacional de outorgas)

`anatel_outorgas` · tipo **bruta** · ativa

O CSV nacional de prestadoras de serviços de telecomunicações da Anatel, baixado uma vez por data e guardado comprimido. SCM, SMP, STFC e SeAC são filtros deste mesmo arquivo (fontes derivadas, cada uma com o seu tratamento).

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.anatel_outorgas.collect` |
| Publicável | não (exposição: nenhuma) |
| Política de falha | opcional |
| Cadência (origem atualiza) | irregular |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 8d |
| Chaves | `cnpj` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/anatel_outorgas/` |

## Origem e licença

- **URL:** https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/prestadoras_servicos_telecomunicacoes.zip
- **Formato:** zip/csv (;-delimitado, UTF-8 com BOM, ~79 MB)
- **Licença:** Dados Abertos Anatel (licença aberta, crédito à fonte)
- **Uso comercial:** `permitido`
- **Termos:** https://www.gov.br/anatel/pt-br/dados/dados-abertos
- **Evidência / ressalvas:** Plano de Dados Abertos da Anatel (verificado em 2026-10-13): dados 'disponibilizados sob licença aberta que permita sua livre utilização, consumo ou cruzamento, limitando-se a creditar a autoria ou a fonte' (Decreto 8.777/2016). A licença específica do conjunto em dados.gov.br não pôde ser lida (exige JavaScript/token).

## Saídas

- **Bruto (raw/):** `summary/anatel-outorgas-{as_of}.csv.gz`

## Dicionário de campos

_Sem dicionário de campos declarado._

## Limites

Só o bruto (sem normalização): cada serviço lê este arquivo e o trata à sua maneira. O ZIP é baixado uma vez por data.

## Retenção

- **bruto:** 4 versões no armazém

## Quem usa

- **Fontes derivadas:** `anatel_scm`, `anatel_seac`, `anatel_smp`, `anatel_stfc`
