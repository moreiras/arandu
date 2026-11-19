# rdap_contatos — respostas do RDAP do Registro.br para `autnum` (SINTÉTICO)

Origem do formato: `https://rdap.registro.br/autnum/{asn}` (RDAP, RFC 9083), conferido em 2026-11-10 só nos NOMES das chaves e dos papéis (`registrant`, `administrative`,
`abuse`), sem copiar nenhum valor. Os `.json` desta pasta são **inventados**: ASNs de documentação (RFC 5398, AS64496–AS64499), nomes e handles fictícios, e-mails em
`example.net` (RFC 2606) e endereços inexistentes. Só a forma segue a API real (o `administrative` aninhado dentro do `registrant`, `vcardArray`, `legalRepresentative`).

- `autnum_64496.json`: resposta completa, `administrative` aninhado e `abuse` no topo.
- `autnum_64497.json`: resposta completa (e-mail com maiúsculas, para testar a normalização).
- `autnum_64497_incompleto.json`: o MESMO ASN sem os e-mails, como o servidor responde sob ritmo alto (HTTP 200).

Nada de dado pessoal real nem de resposta real do Registro.br. A 404 e a conexão derrubada são simuladas nos testes (respx).
