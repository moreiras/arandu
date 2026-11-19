# decix_alice — API do Alice-LG do DE-CIX (SINTÉTICOS, no formato real)
Origem do formato: `https://lg.de-cix.net/api/v1/{status,routeservers,routeservers/{id}/neighbors,routeservers/{id}/neighbors/{id}/routes/received}` (Alice-LG 6.2.0 no `/status` e nos
`neighbors`, 2.0.0 no bloco `api` das rotas), conferido em 2026-11-10 com poucas leituras reais (status, routeservers, `neighbors` do rs1 Rio IPv4 e uma página de rotas de um vizinho
pequeno; autorizadas pela exceção ao `robots.txt` registrada em `catalog/sources/decix_alice.yaml`). **O que foi aproveitado do real:** nomes e tipos dos campos, o id do route server (`rs1_rio_ipv4_de-cix`, com o sufixo `_de-cix`), o nome do route
server no `/status` (`rs1.rio.de-cix.net (IPv4)`, é por ele que o estado se liga ao id), o id do vizinho no `neighbors` (`R93_12`, não `AS{asn}_{ip}`) e o bloco `pagination`.
**Tudo o que é dado ficou sintético:** nenhum membro real, nenhum prefixo real.
- ASNs de documentação (64496–64500, 64510, 64520, 64521); prefixos de documentação (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24) e `10.x.y.0/24` nas páginas geradas; IPs da LAN do IX em
  198.18.0.0/15 (faixa de teste, não os 45.68.93.0/24 reais).
- `routeservers.json`: 8 route servers do escopo (Rio e São Paulo, rs1/rs2, IPv4/IPv6) e 1 de Frankfurt (fora do escopo, tem de ser ignorado).
- `status.json`: versão 6.2.0 e o estado das rotas de cada RS; o rs1 de São Paulo está `BUSY` de propósito (a leitura de rotas deve ir pelo rs2).
- `neighbors_rs{1,2}_{rio,sao}_{ipv4,ipv6}.json`: Rio rs1 v4 com 5 vizinhos (3 rotas, 600 rotas, sem rotas, down, 12 rotas); Rio rs2 v4 com 3 dos mesmos (um vizinho só é consultado
  em um RS); São Paulo com 1 vizinho; as listas IPv6 vazias.
- `routes_received_pequeno.json`: página 0 de um vizinho de 3 rotas (2 de origem 64496, 1 de origem 64510 pelo AS_PATH).
- `routes_received_molde.json`: molde de uma página do vizinho de 600 rotas (3 páginas, 250 + 250 + 100); o teste gera as rotas de cada página a partir dele.
- Sem `filters_available` útil: no DE-CIX o filtro `asns` veio vazio nas leituras reais, então a origem sai do último ASN do AS_PATH de cada rota lida.
