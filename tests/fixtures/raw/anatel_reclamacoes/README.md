# anatel_reclamacoes — reclamações de consumidores (SINTÉTICA)
`consumidor_reclamacoes_sintetico.zip` é **sintética**: linhas inventadas nos dois arquivos do `consumidor_reclamacoes.zip` real da Anatel
(`https://www.anatel.gov.br/dadosabertos/paineis_de_dados/consumidor/consumidor_reclamacoes.zip`, medido em 2026-11-06): `reclamacoes_contexto.csv` (2020 em diante, com a coluna `Linha`) e
`reclamacoes.csv` (legado 2015–2020), UTF-8 com BOM, separador `;`. Os arquivos reais já são agregados da Anatel (mês × município × canal × serviço × marca × assunto), sem texto livre nem dado de
quem reclamou, e aqui também não há. Casos plantados: marca em caixa diferente (`Alfa`/`ALFA`), "NÃO LOCALIZEI A MINHA EMPRESA", pedido de informação (não é reclamação), linha do legado que se
sobrepõe ao `contexto` (2020-01, descartada) e linhas do legado anteriores a ele. Empresas e municípios inventados. Os arquivos reais (356 MB, 4,1 GB descompactado) não entram no repositório.
