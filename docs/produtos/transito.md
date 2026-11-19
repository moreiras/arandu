<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Trânsito por UF e cone de clientes (inferido)

`transito` · produto

Para cada UF, os provedores inferidos (ARC v2, nível provável ou superior) dos ASNs do Brasil com sede nela, com a participação de cada um e a concentração (HHI, top 1 e top 3, fração de provedores estrangeiros); para cada ASN com cliente inferido, o cone de clientes (todos, do Brasil, usuários estimados e UFs). Tudo é inferência sobre relações inferidas; a UF é a da sede da organização.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.transito.build` |
| Chaves de junção | `asn`, `uf` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- produto [as_relationships](as_relationships.md)
- fonte [registro_br](../fontes/registro_br.md) — uso comercial: `nao_verificado`
- fonte [caida_as2org](../fontes/caida_as2org.md) — uso comercial: `nao_verificado`
- produto [asn_docs](asn_docs.md)

## Saídas

- **Publicado:** `transito/ufs.json.gz`, `transito/asns.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ufs[uf].asns_br / asns_com_provedor / pct_com_provedor` | int / int / float | ASNs do Brasil com sede na UF, quantos têm ao menos um provedor inferido (nível provável ou superior) e a fração. | UF = sede da organização (geo_org do ASN), não onde o trânsito é entregue; provedor = relação p2c inferida pelo ARC v2. | transito → transito/ufs.json.gz#ufs |
| `ufs[uf].hhi_clientes / top1_share / top3_share` | int / float / float | Concentração da participação de cada provedor nos pares (ASN da UF, provedor), com HHI de 0 a 10.000, maior provedor e três maiores. | Mede quem os ASNs têm como provedor inferido, não volume de tráfego nem contratos. | transito → transito/ufs.json.gz#ufs |
| `ufs[uf].provedores[]` | list | Os 20 maiores provedores da UF (ASN, nome, se é brasileiro, clientes e usuários estimados na UF, e a participação). | Usuários são estimativa APNIC e se repetem entre ASNs da mesma operadora, e share_usuarios é rotulado como estimativa. | transito → transito/ufs.json.gz#ufs |
| `asns[asn].cone_asns / cone_br / cone_usuarios / cone_ufs / clientes_diretos` | int | Cone de clientes do ASN pelas relações p2c firmes (busca em largura, segura com ciclos), sem o próprio ASN e os irmãos (mesmo CNPJ raiz ou organização do CAIDA). | Só existem elos com ao menos um ASN brasileiro; o cone de um ASN estrangeiro só conta o que tem ligação com o Brasil. | transito → transito/asns.json.gz#asns |
| `cobertura / limites / fonte` | dict | ASNs do Brasil com provedor, elos p2c usados, algoritmo e data das relações, limites e as coletas dos coletores. | — | transito → transito/ufs.json.gz#cobertura; transito → transito/ufs.json.gz#limites; transito → transito/ufs.json.gz#fonte |
| `snapshot_date / generated_at` | str | Data do snapshot e instante UTC de geração. | — | transito → transito/ufs.json.gz#snapshot_date; transito → transito/ufs.json.gz#generated_at |

## Limites

Inferência sobre inferência. O cone ignora elos de nível possível e as relações complexas; a concentração é sobre quem é provedor, não sobre o tráfego.
