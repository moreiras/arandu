# anatel_sici — acessos_banda_larga_fixa.zip (SICI)
Origem: https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/acessos_banda_larga_fixa.zip
(~1 GB). O bruto não é retido (o coletor lê por HTTP Range e só guarda agregados). Estas amostras foram
**reconstruídas** linha a linha a partir do cache agregado real (`normalized/sici_cache/months`, 2026-09-20):
3 provedores pequenos (1–2 municípios), meses 2026-06 e 2026-07, com o cabeçalho do CSV anual
(`Ano;Mês;Grupo Econômico;Empresa;CNPJ;…;Acessos`) e 3 linhas de controle (produto LINHA_DEDICADA,
CNPJ inválido, acessos = 0). `Total.sample.csv` é o membro sentinela `Ano;Mês;Acessos`.
Os testes empacotam os CSVs em um ZIP e o servem com suporte a `Range`, como a Anatel faz.
