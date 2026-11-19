<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# ASNs por município e fatos de rede

`regiao_municipios` · produto

Para cada município, os ASNs do Brasil ligados a ele por um de três vínculos (a operadora declara acessos no SICI, a sede do CNPJ está nele, ou o DB-IP geolocaliza prefixos dele ali) e, por ASN, os PTTs em que está (direto e indireto), os ASNs vizinhos observados nos caminhos dos PTTs (carregadores) e os provedores de trânsito inferidos pelo ARC v1 com a probabilidade. Inferência; nenhuma posição de prefixo sai daqui.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.regiao.build` |
| Chaves de junção | `asn`, `ibge` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [anatel_sici](../fontes/anatel_sici.md) — uso comercial: `permitido`
- fonte [anatel_sici_movel](../fontes/anatel_sici_movel.md) — uso comercial: `permitido`
- fonte [registro_br](../fontes/registro_br.md) — uso comercial: `nao_verificado`
- fonte [prefix_geo](../fontes/prefix_geo.md) — uso comercial: `permitido`
- fonte [cnpj_geo](../fontes/cnpj_geo.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `territorio/regiao.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `municipios` | dict | Por código IBGE, os ASNs com vínculo SICI (acessos fixo e móvel), sede ou prefixos geolocalizados (só a contagem). | — | regiao_municipios → territorio/regiao.json.gz#municipios |
| `asns` | dict | Por ASN, nome, PTTs diretos (d) e de origem (o), carregadores observados (c) e provedores de trânsito com probabilidade e nível (p). | — | regiao_municipios → territorio/regiao.json.gz#asns |
| `natureza / limites / fontes / snapshot_date / generated_at` | str | Rótulo de inferência, limites, fontes e data. | — | regiao_municipios → territorio/regiao.json.gz#natureza; regiao_municipios → territorio/regiao.json.gz#limites; regiao_municipios → territorio/regiao.json.gz#fontes; regiao_municipios → territorio/regiao.json.gz#snapshot_date; regiao_municipios → territorio/regiao.json.gz#generated_at |
