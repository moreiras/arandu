# cetic — tabelas oficiais da TIC Domicílios 2025 e da TIC Provedores 2024 (REAIS)
`tic_domicilios_2025_domicilios_tabelas_xlsx_v1.0.zip` e `tic_provedores_2024_tabela_xlsx_v1.0.zip` são os arquivos originais, sem alteração, baixados de
https://cetic.br/pt/pesquisa/{domicilios,provedores}/microdados/ em 2026-11-01 (licença CC BY 4.0, citação Cetic.br|NIC.br). Cada um traz quatro planilhas XLSX
(proporção, margem de erro, total e margem de erro do total). São agregados por recorte (região, área, renda, porte): nenhum dado pessoal nem microdado.
`pagina_domicilios.html` e `pagina_provedores.html` são **reconstruídas**: só a lista de links da página de microdados, com os nomes reais dos arquivos
(o `<id>` numérico da URL muda por arquivo) e um link de edição antiga para testar a escolha da mais recente.

`tic_domicilios_microdados_sintetico.csv.gz` é **sintética** (gerada por `gerar_microdados_sintetico.py`, semente fixa): 27 UFs, 36 domicílios cada (AP com 12, para testar a supressão), 200 pesos de réplica, no layout da base real (Latin-1, `;`, vírgula decimal). Só tem as colunas que o estimador lê. A base real (27.177 domicílios, 36 MB) não entra no repositório.
