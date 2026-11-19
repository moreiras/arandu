# anatel_multas — multas constituídas (SINTÉTICA)
`arrecadacao_sintetico.zip` é **sintética**: 10 multas inventadas no layout do `arrecadacao.zip` real da Anatel
(`https://www.anatel.gov.br/dadosabertos/paineis_de_dados/arrecadacao/arrecadacao.zip`, medido em 2026-11-02): `multas_constituidas.csv` em UTF-8 com BOM, separador `;`, CNPJ formatado
(`00.000.000/0000-00`), valores `R$1.234,56`. Só as colunas lidas pelo parser foram preenchidas (o arquivo real tem ~60). Casos plantados: matriz e filial da mesma raiz (SCM), SMP, STFC, SeAC por
dois nomes de serviço, radiodifusão (fora), multa sem serviço (fora), pessoa física com CPF mascarado `***.999.999-**` (descartada) e data de aplicação em branco (usa o ano de referência).
Empresas e CNPJ inventados; sem dado pessoal. O arquivo real (5 MB) não entra no repositório.
