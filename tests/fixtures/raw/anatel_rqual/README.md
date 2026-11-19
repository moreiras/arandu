# anatel_rqual — indicadores de qualidade (SINTÉTICA)
`indicadores_rqual_sintetico.zip` é **sintética**: 10 linhas inventadas no layout do `indicadores_rqual.zip` real da Anatel
(`https://www.anatel.gov.br/dadosabertos/paineis_de_dados/qualidade/indicadores_rqual.zip`, medido em 2026-11-06): `Tabela_CSV_Indicadores_RQUAL.csv` em UTF-8 com BOM, separador `;`, 21 colunas,
decimais com vírgula. Casos plantados: dois meses para o mesmo município (vale o último), resultado `NO`, `NA` e `NI` (contados, não somados), linha com 100 e outra com 10 coletores
(estatística SIM e NÃO), indicador informativo, três serviços e prestadoras de nome genérico (ALFA, BETA, GAMA). Municípios (Alfa/RO, Beta/AC) e empresas inventados; sem dado pessoal. O arquivo real
(265 MB, ~18 milhões de linhas) não entra no repositório.
