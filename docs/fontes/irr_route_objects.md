<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# IRR (TC e RADB) — objetos route/route6 dos ASNs brasileiros

`irr_route_objects` · tipo **bruta** · ativa

Dumps públicos do TC IRR (bgp.net.br) e do RADB (Merit), lidos em fluxo; ficam só os pares prefixo/origem (`route`/`route6`) cuja origem é ASN brasileiro (Registro.br) e quais ASNs brasileiros têm `aut-num`. Serve para medir quanto dos prefixos que o ASN anuncia tem objeto IRR. Mantenedor, contato e texto dos objetos não são guardados.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.irr_route_objects.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | diaria |
| Coleta hoje → alvo | semanal → mensal |
| Frescor máximo | 45d |
| Chaves | `asn`, `prefixo` |
| Entradas | `registro_br` |
| Amostra de teste | `tests/fixtures/raw/irr_route_objects/` |

## Origem e licença

- **URL:** https://ftp.bgp.net.br/tc.db.gz e ftp://ftp.radb.net/radb/dbase/radb.db.gz
- **Formato:** RPSL (texto, gzip); serial em TC.CURRENTSERIAL e RADB.CURRENTSERIAL
- **Licença:** TC termos de uso; RADB ToS (cópia arquivada)
- **Uso comercial:** `nao_verificado`
- **Termos:** https://bgp.net.br/terms.html e https://www.radb.net/terms-of-service
- **Evidência / ressalvas:** TC (terms.html, lido em 2026-11-02): permite consultar dados técnicos e "usar as informações para operação, segurança, auditoria e pesquisa de redes"; proíbe automação agressiva e objetos proxy; sem cláusula de redistribuição, de uso comercial nem de citação. RADB: o ToS é um contrato de registrante; a informação "não é confidencial" e fica à disposição de quem acessa o Registry; o suporte diz que o dump FTP é público, sem assinatura, e que se deve consultar o serial antes de baixar; revenda de serviços é proibida. O site do RADB responde 403 a requisição automática, então o ToS foi lido em cópia arquivada (TOSTracker, 2026-07-09) e a Acceptable Use policy da Merit não foi lida. Decisão do mantenedor (2026-11-02): RADB considerado OK, coletar e usar como ativo, publicando só derivados por ASN.

## Saídas

- **Bruto (raw/):** `summary/irr-tc-AAAA-MM-DD.db.gz`, `summary/irr-radb-AAAA-MM-DD.db.gz`
- **Normalizado (normalized/):** `summary/irr_route_objects.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `rotas[irr][asn]` | lista | Prefixos (CIDR) de objetos `route`/`route6` com o ASN brasileiro como origem, por IRR (TC e RADB). | Só o par prefixo/origem. O RADB aceita objetos criados por terceiros (o provedor, por exemplo) e o TC não: a existência do objeto não prova que o ASN o criou. | — |
| `aut_num[irr]` | lista | ASNs brasileiros com objeto `aut-num` no IRR. | — | — |
| `politicas[irr][asn]` | lista | Por `aut-num` brasileiro, as linhas `import`/`export` com par ASN explícito, reduzidas a sentido (in ou out), ASN do par e classe do filtro (any, proprio, par, as_set, outro). | Só a classe do filtro; o texto da política, mantenedor e contato não são guardados. Linhas com conjunto no lugar do par, refine/except e fatores múltiplos são ignoradas. Declarado não é praticado: serve de referência e de evidência candidata do 1.5.30, nunca de verdade. | — |
| `fontes[irr]` | dict | URL, serial, tamanho, hash, contagem de objetos do dump (todos, não só brasileiros), ASNs brasileiros com route, prefixos e `aut-num`; `reaproveitado_de` quando o serial não mudou. | — | — |

## Limites

Objeto IRR documenta política ou intenção de roteamento; não substitui delegação nem RPKI. TC e RADB cobrem 95% dos ASNs brasileiros que anunciam prefixos, mas RIPE, ARIN, LACNIC e outros IRRs não são lidos (acrescentariam 13 ASNs na medição de 2026-11-02). Objetos `as-set` não são lidos (não há vínculo confiável entre o as-set e o ASN).

## Retenção

- **bruto:** 2 versões
- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `prontidao`

## Pendências (nao_verificado)

- Confirmação formal do RADB (support@radb.net) sobre o uso do dump em derivados é opcional; ler a Acceptable Use policy da Merit.
