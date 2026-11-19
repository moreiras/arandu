<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Anatel — quadro de atribuição e destinação de faixas (PDFF)

`anatel_pdff` · tipo **bruta** · ativa

Plano de Destinação de Frequências de Radiocomunicação da Anatel: para cada faixa (kHz a GHz) os serviços destinados e atribuídos no Brasil, com o caráter (primário ou secundário). É o quadro normativo; não diz quem explora a faixa nem se ela está em uso.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.anatel_pdff.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | irregular |
| Coleta hoje → alvo | semanal → mensal |
| Frescor máximo | 90d |
| Chaves | — |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/anatel_pdff/` |

## Origem e licença

- **URL:** https://www.anatel.gov.br/dadosabertos/paineis_de_dados/espectro_e_orbita/pdff.zip
- **Formato:** ZIP com 8 CSVs (UTF-8 com BOM, separador `;`); `Destinacao.csv` (1.428 linhas) e `Atribuicao_BR.csv` (1.668 linhas) são lidos
- **Licença:** Dados Abertos Anatel
- **Uso comercial:** `permitido`
- **Termos:** https://www.gov.br/anatel/pt-br/dados/dados-abertos
- **Evidência / ressalvas:** Endereço achado por padrão de nome e verificado em 2026-11-02 (HTTP 200, 225.508 bytes). O `ID_FREQ` não é único (a mesma faixa numérica aparece em kHz e em MHz); a chave é o par início/fim em MHz. Uma requisição, com User-Agent identificado.

## Saídas

- **Bruto (raw/):** `summary/pdff-AAAA-MM-DD.zip`
- **Normalizado (normalized/):** `summary/anatel_pdff.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `faixas[].ini_mhz / fim_mhz` | float | Início e fim da faixa em MHz. | Lidos das colunas `*_MHz` (vírgula decimal). | — |
| `faixas[].destinacao[] / atribuicao[]` | lista | Serviços destinados e atribuídos à faixa no Brasil, cada um com o caráter (Primário ou Secundário). | — | — |
| `resumo / data_arquivo / sha256` | dict | Faixas lidas e quantas têm destinação e atribuição; data de modificação do arquivo na Anatel e seu hash. | — | — |

## Limites

É norma, não licença. Não diz quem explora a faixa, nem se está em uso, nem a largura efetivamente licenciada a cada operadora.

## Retenção

- **bruto:** 2 versões
- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `regulatorio`
