# irr_route_objects — dumps do TC e do RADB (SINTÉTICOS)
`tc.db.gz` e `radb.db.gz` são **sintéticos**, no formato RPSL dos dumps reais (`https://ftp.bgp.net.br/tc.db.gz` e `ftp://ftp.radb.net/radb/dbase/radb.db.gz`, medidos em 2026-11-02): objetos separados por linha em
branco, `atributo: valor`, cabeçalho de comentário `%`, linha de continuação com espaços. Os reais têm 50 mil (TC) e 1,3 milhão (RADB) de objetos route/route6; aqui são ~8 objetos de cada com prefixos de
documentação (198.51.100.0/24, 203.0.113.0/24, 2001:db8::/32) e ASNs de documentação (64500–64502). Casos plantados: mesmo prefixo/origem nos dois IRRs, objeto duplicado dentro do mesmo IRR, `route6`, continuação de
linha, origem não brasileira (AS15169, AS64999), prefixo inválido, origem mal formada, `aut-num` brasileiro e não brasileiro, objetos de outras classes (`mntner`). `TC.CURRENTSERIAL` e `RADB.CURRENTSERIAL` imitam
os arquivos de serial. Não há dado pessoal (os dumps reais têm contatos em objetos `person`/`role`; o parser os ignora).
