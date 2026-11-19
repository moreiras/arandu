# caida_as2org — API GraphQL do CAIDA AS Rank (SINTÉTICO)
Origem: https://api.asrank.caida.org/v2/graphql (consulta `asns(asns:[…]) { edges { node { asn organization { orgId orgName country members } } } }`, formato medido em 2026-11-06).
`resposta.json` imita o formato real com ASNs de documentação (RFC 5398), nomes e identificadores inventados; nenhum registro real do CAIDA foi copiado. O ASN 64501 vem sem
organização (como acontece com ASNs que o AS Rank não conhece). Citação exigida: "The CAIDA UCSD AS Rank, https://asrank.caida.org".
