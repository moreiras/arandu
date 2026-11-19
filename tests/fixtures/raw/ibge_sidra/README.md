# ibge_sidra — API SIDRA do IBGE (RECONSTRUÍDA)
`sidra_6579.json` (Estimativas de População 2026) e `sidra_7307-serie.json` (domicílios da PNAD por UF, 2022 a 2025, crescimento sintético de 6% a 10% com semente fixa) foram acrescentados no 1.5.3.3; Boa Esperança do Norte (5101837) só tem estimativa, como na SIDRA (município criado depois do Censo).
Origem: https://apisidra.ibge.gov.br/values (tabelas 4714 e 4712 do Censo 2022, por município; 7307 da PNAD Contínua anual, por UF).
`sidra_4714.json` e `sidra_4712.json` seguem o formato real da resposta (cabeçalho como 1º elemento, `D1C` = código do município, `V` = valor como texto)
com 6 municípios; os valores de São Paulo, Rio de Janeiro, Brasília e Alta Floresta D'Oeste foram conferidos com a SIDRA em 2026-10-31, os demais são
plausíveis, não reais. Dom Feliciano vem com `...` em domicílios (sem valor na SIDRA). `sidra_7307.json` tem as 27 UFs com números **sintéticos** (semente fixa).
Nada de dado pessoal: são agregados. Termos de uso do IBGE ainda não verificados (HTTP 403 na página de termos em 2026-10-31).
