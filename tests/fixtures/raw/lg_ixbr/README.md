# lg_ixbr — saída Telnet do Looking Glass do IX.br (FRR)
Origem: `lg.sp.ix.br`, comandos `show ip bgp` e `show bgp ipv6 unicast`, coletado em 2026-09-20. Recorte: banner e
cabeçalho reais, 12 (v4) / 24 (v6) linhas de rota e o rodapé `Displayed N routes…`. O IPv6 usa o formato de
2 linhas (prefixo/nexthop + caminho). O `Displayed` original reflete a tabela completa, não o recorte.

`bgp-empty.sample.txt` — resposta real de `lg.ap.ix.br` (Macapá) em 2026-10-11 a `show ip bgp` e
`show bgp ipv6 unicast` com os route servers sem nenhum prefixo: uma linha, sem cabeçalho nem `Displayed`.
