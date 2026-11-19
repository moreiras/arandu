# ixbr_alice_rotas — API do Alice-LG do IX.br, rotas por vizinho (RECONSTRUÍDOS)
Origem: `https://lg.ix.br/api/v1/routeservers/{rs}/neighbors/{id}/routes/{filtered|received}?page=0&page_size=250` (Alice 6.1.0, formato conferido em 2026-11-06 contra respostas reais:
`api`, `pagination`, `filters_available` com a contagem de cada community sobre o conjunto inteiro, e `filtered` ou `imported` com as rotas). Recortes mínimos reconstruídos à mão.
Nenhum dado real de membro: ASNs de documentação (64496–64498, 4200000200), prefixos de documentação (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24).
- `filtered_SP-rs1-v4_AS64496.json`: 3 rotas na página, `total_results` 7 e contagens exatas (RPKI inválido 4, bogon 2): a amostra é menor que o total de propósito.
- `received_SP-rs1-v4_AS64497.json`: 1 rota na página, `total_results` 100, com communities de não exportar (padrão 65000:N, estendida rt:65000:N, grande 65000:0:N e 65004:0:PTT) e blackhole 65535:666.
- `received_SP-rs1-v4_AS64498.json`: sem `filters_available` (Alice antigo): a contagem sai da página e fica `contagem: "amostra"`.
- `dicionario.json`: o `ixbr_communities` (dicionário do `/api/v1/config` do Alice, informação pública e não pessoal) de 2026-11-01, reduzido (só 3 PTTs na lista de `65004`).
