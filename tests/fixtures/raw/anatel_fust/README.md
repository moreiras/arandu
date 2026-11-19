# anatel_fust — compromissos do FUST (SINTÉTICA)
`fust_sintetico.zip` é **sintética**: 6 compromissos inventados no layout do `fust.zip` real da Anatel
(`https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acompanhamento_e_controle/fust.zip`, medido em 2026-11-02): `Base_FUST.csv` com 41 colunas, UTF-8 com BOM, separador `;`,
decimal com vírgula, `N/A` no que não se aplica, tabulação dentro do nome do programa e cronograma com quebra de linha entre aspas. Mais um `Base_SEI.csv` mínimo (o zip real traz
as bases do ônus contratual, que não são lidas). Casos plantados: situação Atendido/A vencer/Em apuração, malhas IBGE_2010 e IBGE_2022, investimento `N/A` e vazio, prazo inválido,
município fora do cadastro do IBGE (código inexistente), nível Localidade. Sem dado pessoal; o arquivo real (1 MB) não entra no repositório.
