<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Malha municipal do IBGE (limites dos municípios e UFs, em tiles)

`ibge_malha_municipal` · tipo **curada** · ativa

Limites dos 5.571 municípios do Brasil (Malha Municipal 2024 do IBGE, shapefile em SIRGAS 2000), simplificados e servidos como tiles vetoriais PMTiles com duas camadas (`municipios` e `ufs`, zoom 0 a 7) para os mapas coropléticos. Gerado por `scripts/build-malha-municipal.py` a partir de um ZIP baixado à mão (um arquivo, ~200 MB).

## Resumo

| | |
|---|---|
| Módulo / arquivo | `frontend/public/malha-municipal.pmtiles` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | anual |
| Coleta hoje → alvo | sob_demanda → sob_demanda |
| Frescor máximo | 800d |
| Chaves | `ibge`, `uf` |
| Entradas | — |

## Origem e licença

- **URL:** https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2024/Brasil/BR_Municipios_2024.zip
- **Formato:** PMTiles v3 (MVT, gzip) derivado de zip/shapefile (SIRGAS 2000)
- **Licença:** IBGE, dados abertos; citar "Fonte: IBGE" (uso autorizado pelo mantenedor em 2026-11-11; texto de licença não lido)
- **Uso comercial:** `nao_verificado`
- **Termos:** https://www.ibge.gov.br/acesso-informacao/institucional/termo-de-uso.html
- **Evidência / ressalvas:** As páginas de termos do IBGE respondem HTTP 403 a acesso automatizado (2026-11-11), então o texto não foi lido. O mantenedor autorizou o uso da malha com a atribuição "Fonte: IBGE". As lagoas dos Patos e Mirim (4300001, 4300002) ficam de fora. Simplificação topológica de 1 pixel por zoom: não serve para medir área nem fronteira, só para desenhar.

## Saídas


## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `municipios.ibge / nome / uf` | str | Código IBGE de 7 dígitos, nome e sigla da UF de cada município. | — | frontend → /malha-municipal.pmtiles |
| `ufs.uf / nome` | str | Sigla e nome de cada UF (união dos municípios simplificados). | — | frontend → /malha-municipal.pmtiles |

## Limites

Geometria simplificada (tolerância de 1 pixel do zoom, até o zoom 7), serve para mapas temáticos, não para área, fronteira nem georreferenciamento. A malha muda quando o IBGE publica a de um ano novo; o código e a data de origem ficam em `frontend/public/malha-municipal.json`.

## Retenção

- **normalizado:** git

## Quem usa

- **Produtos:** `area_influencia_ptt`

## Pendências (nao_verificado)

- Texto da licença/termos de uso do IBGE (páginas respondem 403 a acesso automatizado); até lá o uso vale pela autorização do mantenedor de 2026-11-11, com a atribuição "Fonte: IBGE".
