# apnic_labs — páginas de país do APNIC Labs (RECONSTRUÍDAS)
Origem: https://stats.labs.apnic.net/rpki/BR e https://stats.labs.apnic.net/dnssec/BR (tabela por ASN embutida em JavaScript, 1,3 a 1,5 MB reais).
`rpki_BR.html` e `dnssec_BR.html` imitam a estrutura real (gráfico de série com `new Date(...)`, tabela `['ASN', 'AS Name', ...]` com links `/rpki/ASn?c=BR&w=...`,
valores `{v: x, f:'x%'}`, linha sem medição com `""`, e uma tabela regional depois) com **ASNs de documentação (RFC 5398) e nomes fictícios**; só o ASN 64497 repete,
de propósito, os números reais de um ASN grande (0,26% e 290.351 amostras; DNSSEC 7,69% e 12,43%) conferidos com o JSON por ASN em 2026-10-31.
Os nomes reais de AS não são copiados porque alguns são nomes de pessoas físicas. Direitos: "(c) APNIC Pty/Ltd. re-use with attribution permitted".
