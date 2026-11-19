# anatel_outorgas — prestadoras_servicos_telecomunicacoes.zip (SCM, SMP, STFC, SeAC)
Origem: dados abertos da Anatel (https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/),
coletado em 2026-09-20. Os quatro coletores (SCM, SMP, STFC, SeAC) leem o MESMO CSV e filtram por serviço.
Recorte: 14 linhas reais de 8 serviços (045 e 047 SCM; 010 e 110 SMP; 171 e 175 STFC; 750 SeAC; 302 de controle),
mais 1 linha de pessoa física **fictícia**. E-mail e telefone cadastrais substituídos por valores
genéricos (`contato@example.org`, `N/I`). Os testes empacotam o CSV em um ZIP, como a fonte entrega.
