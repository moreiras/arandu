<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# DE-CIX Rio e São Paulo nos route servers (estende os IXPs externos)

`decix_rs` · produto

Por PTT do DE-CIX no Brasil (decix-sp e decix-rj): route servers e sessões BGP dos membros vistos no Alice-LG, ASNs diretos (sessão up no route server), ASNs originadores das rotas lidas por vizinho em rodízio (um piso, com a cobertura declarada), membros com nome do LG e cruzamento com o PeeringDB, e a comparação por cidade com o IX.br (São Paulo e Rio) e com o Equinix cadastrado (São Paulo). Fatos medidos no route server na data da coleta, sem veredito.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.decix_rs.build` |
| Chaves de junção | `ixp`, `asn` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [decix_alice](../fontes/decix_alice.md) — uso comercial: `nao_verificado`
- produto [ixp_docs](ixp_docs.md)
- produto [asn_docs](asn_docs.md)

## Saídas

- **Publicado:** `decix_rs/ixps.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ixps[ixp].resumo` | dict | Route servers (total e consultados), sessões up e down, membros (ASNs com sessão), ASNs diretos e originadores (contagens, total e brasileiros). | `asn_direct` = sessão up no route server (não é o primeiro salto do AS_PATH do IX.br); `asn_origin` é um piso (leitura parcial por vizinho). | decix_rs → decix_rs/ixps.json.gz#ixps |
| `ixps[ixp].asn_direct / asn_origin / br_asns_direct / br_asns_origin` | list | ASNs com sessão up, ASNs de origem das rotas lidas e a parte brasileira de cada conjunto. | Sem leitura de rotas não há originador (não é zero); `rotas.parcial` e `rotas.cobertura` dizem quanto foi lido. | decix_rs → decix_rs/ixps.json.gz#ixps |
| `ixps[ixp].membros[]` | list | Por ASN, o nome do LG (organização), sessões up e down por família e rotas recebidas pelo route server. | Rótulo público do LG; nunca contatos. | decix_rs → decix_rs/ixps.json.gz#ixps |
| `ixps[ixp].peeringdb` | dict | Cadastrados no PeeringDB sem sessão up, sessão up sem cadastro e totais. | Cadastro e sessão medem coisas diferentes: cadastrado sem sessão pode ser peering bilateral; sessão sem cadastro, desatualização do PeeringDB. | decix_rs → decix_rs/ixps.json.gz#ixps |
| `ixps[ixp].comparacao_cidade` | dict | Para a cidade do PTT, ASNs diretos do IX.br e do DE-CIX, interseção, só em cada um, ASNs com sessão no DE-CIX e sem direto no IX.br, e o Equinix cadastrado (São Paulo). | Critérios diferentes entre as redes (sessão, primeiro salto, cadastro): compara conjuntos de ASNs, não tráfego nem qualidade. | decix_rs → decix_rs/ixps.json.gz#ixps |
| `bloqueio` | dict | Presente quando a coleta parou por sinal de bloqueio do servidor (403, 429 ou conexão derrubada). | — | decix_rs → decix_rs/ixps.json.gz#bloqueio |
| `snapshot_date / generated_at / coletado_em / rotas_coletadas_em / fonte / versao_alice / aviso` | str | Data do snapshot, instantes UTC de geração e das coletas, fonte, versão do Alice e o aviso sobre o que o dado é. | — | decix_rs → decix_rs/ixps.json.gz#snapshot_date; decix_rs → decix_rs/ixps.json.gz#generated_at; decix_rs → decix_rs/ixps.json.gz#coletado_em; decix_rs → decix_rs/ixps.json.gz#rotas_coletadas_em; decix_rs → decix_rs/ixps.json.gz#fonte; decix_rs → decix_rs/ixps.json.gz#versao_alice; decix_rs → decix_rs/ixps.json.gz#aviso |
