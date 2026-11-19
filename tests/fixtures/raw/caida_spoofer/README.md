# caida_spoofer — sessões do Spoofer (SINTÉTICA)
`pagina1.json` e `pagina2.json` são **sintéticas**: duas páginas (14 sessões) no formato Hydra/JSON de `https://api.spoofer.caida.org/sessions?country=bra&...` (medido em 2026-11-02): `hydra:member`,
`hydra:view` com `hydra:next`, campos `session`, `timestamp`, `asn4`/`asn6` (texto), `nat4`/`nat6`, `privatespoof`, `routedspoof`, `privatespoof6`, `routedspoof6` e os campos `client4`/`client6`
(aqui com endereços de documentação `192.0.2.0/24` e `2001:db8::/48`; o teste confere que não chegam ao disco). ASNs de documentação (64500–64503). Casos plantados: ASN com 6 sessões conclusivas fora
de NAT e um `received` roteado (suficiente), ASN só atrás de NAT, ASN com IPv6 conclusivo (sem NAT) e IPv4 atrás de NAT, ASN com poucas sessões e uma sem resultado, `rewritten` e `unknown`.
Não há dado pessoal. A resposta real tem ~160 KB por página de 500 sessões e não entra no repositório.
