# shodan_exposicao — respostas de `/shodan/host/count` e `/api-info` (SINTÉTICO)

Origem do formato: documentação pública da API do Shodan (https://developer.shodan.io/api): `host/count` devolve `{"matches": [], "facets": {<faceta>: [{"value", "count"}]}, "total"}`;
`/api-info` devolve plano e créditos. **Nada foi consultado na conta real** (a chave só existe no ambiente de teste; a medição é a sondagem `--sondar`, a cargo do coordenador). Os arquivos são
**inventados**: contagens arbitrárias, ASNs de documentação (RFC 5398, AS64496), CVEs fictícios (`CVE-2099-*`) e textos de erro de exemplo. Nenhum IP nem host individual (diretriz de privacidade do guia do desenvolvedor: só agregados por ASN, UF ou faceta).

- `geral_64496.json`: consulta A (`asn:AS64496`, faceta `port`); `geral_vazio.json`: ASN sem serviço observado.
- `risco_64496.json`: consulta B (`asn:AS64496 port:<portas de risco>`).
- `vuln_64496.json`: consulta C (faceta `vuln`), quando o plano permite; `erro_plano.json`: a recusa por plano (HTTP 4xx com `error`); `erro_chave.json`: chave inválida (HTTP 401).
