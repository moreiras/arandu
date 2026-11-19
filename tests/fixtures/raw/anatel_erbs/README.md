# anatel_erbs — estações do SMP licenciadas (SINTÉTICA)
`estacoes_smp_sintetico.zip` é **sintética** (gerada por `gerar_estacoes_sinteticas.py`): 12 estações inventadas, no layout do `estacoes_smp.zip` real da Anatel
(`https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/estacoes_smp.zip`, medido em 2026-11-02): 41 colunas, UTF-8 com BOM, separador `;`,
uma linha por estação × setor × frequência e cada registro repetido 3 vezes, com o código IBGE só em uma das cópias. Operadoras e CNPJ inventados (Vivo/Claro/TIM/Brisanet
com razão social real, CNPJ fictício onde não é o da empresa). Casos plantados: IBGE em 1 de 3 linhas, CNPJ em branco em parte das linhas, estação sem posição, fora do Brasil,
posição que varia entre linhas, só 2G, 5G SA e NSA, estação sem nenhuma linha com IBGE. O arquivo real (94 MB, 995 MB descomprimido) não entra no repositório. Sem dado pessoal.
