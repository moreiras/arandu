# peeringdb_fac (PeeringDB: instalações, carriers, campus e atributos das redes)

- **Origem:** formato dos recursos `fac` e `net` da API do PeeringDB (https://www.peeringdb.com/api), conferido ao vivo em 2026-11-06.
- **Natureza:** **sintética**, no formato original (mesmos nomes de campo, incluindo os de contato). Todos os valores são inventados: instalações e redes fictícias, ASNs de documentação (64496-64511),
  domínios `example.org`, e-mails e telefones falsos.
- **Recorte:** duas instalações e duas redes. Plantadas de propósito para o teste de privacidade: `tech_email`, `sales_email`, `*_phone`, `notes` com e-mail, `social_media`, endereço de rua e CEP
  (devem ser descartados na normalização), site que não é URL, looking glass com credencial embutida e route server que é um e-mail (devem virar ausência).
- **Anonimização:** nenhum dado real; nada de PeeringDB POC.
- Os demais recursos (`ixfac`, `netfac`, `carrierfac`, `carrier`, `campus`, `ix`) são montados no próprio teste a partir de poucas linhas.
