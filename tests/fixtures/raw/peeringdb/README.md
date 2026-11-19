# peeringdb — /api/net, /api/netixlan, /api/poc
- `net.sample.json`: 5 registros reais de `/api/net` (coletados em 2026-09-20), envelope `{"data": [...]}`.
- `netixlan.sample.json`: 5 membros de um IXP externo; recriado a partir do raw guardado
  (asn/nome/velocidade) com os demais campos do esquema da API.
- `poc.sample.json`: 5 registros de `/api/poc` da amostra de `net`, **anonimizados**: nome,
  telefone e e-mail substituídos por valores fictícios (`@example.org`); `net_id`, `role` e
  `visible` originais. Nenhum dado pessoal real.
- `org.sample.json`: 3 registros de `/api/org` (SINTÉTICOS, esquema documentado) para o enriquecimento de ASNs internacionais.
