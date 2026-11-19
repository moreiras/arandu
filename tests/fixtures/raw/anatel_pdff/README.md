# anatel_pdff — quadro de faixas (SINTÉTICA)
`pdff_sintetico.zip` é **sintética**: 7 linhas de destinação e 4 de atribuição no layout do `pdff.zip` real da Anatel
(`https://www.anatel.gov.br/dadosabertos/paineis_de_dados/espectro_e_orbita/pdff.zip`, medido em 2026-11-02): UTF-8 com BOM, `;`, vírgula decimal. As faixas e os serviços lembram as reais
(700 MHz, 3,3–3,6 GHz, 2,4 GHz), com campos simplificados. Caso plantado: `ID_FREQ` repetido entre kHz e MHz (`3400-3500` em kHz, que em MHz é 0,0034–0,0035, e a de mesmos números em MHz), que o parser trata
usando as colunas `*_MHz`. Sem dado pessoal.
