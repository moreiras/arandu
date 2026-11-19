<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Acessos SICI publicados (fixo e móvel)

`sici` · produto

Acessos por CNPJ e por município (fixo e móvel), série mensal, vínculo CNPJ↔ASN e divergência APNIC×Anatel.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `publish.snapshot_builder` |
| Chaves de junção | `cnpj`, `asn`, `ibge`, `uf`, `mes_referencia` |
| Cenários de teste (dataset sintético) | `cnpj_dois_asns`, `scm_sem_sici` |

## Entradas

- fonte [anatel_sici](../fontes/anatel_sici.md) — uso comercial: `permitido`
- fonte [anatel_sici_movel](../fontes/anatel_sici_movel.md) — uso comercial: `permitido`
- fonte [registro_br](../fontes/registro_br.md) — uso comercial: `nao_verificado`
- fonte [apnic_pop](../fontes/apnic_pop.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `sici.json.gz`, `sici_municipios.json.gz`, `sici_movel.json.gz`, `sici_movel_municipios.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `cnpj_to_asns / asn_to_cnpj` | dict | Vínculos CNPJ↔ASN usados para ligar SICI a ASN. | Vêm do Registro.br; vários ASNs por CNPJ ⇒ acessos_compartilhados. | sici → sici.json.gz#cnpj_to_asns |
| `cnpjs[cnpj].acessos_compartilhados / asns` | bool / list[int] | Verdadeiro quando o CNPJ tem mais de um ASN: não somar acessos por ASN. | — | sici → sici.json.gz#cnpjs |
| `divergencia[asn].classificacao / razao` | str / float | Razão acessos SICI × usuários APNIC e classe (normal, acima, abaixo, nao_comparavel). | Hipótese de comparação entre duas estimativas diferentes; rotular. | sici → sici.json.gz#divergencia |
| `municipios[ibge].operadores / hhi / share_maior` | list / int / float | Operadoras do município, índice HHI de concentração e parcela da maior. | HHI sobre acessos declarados, não sobre receita. | sici → sici_municipios.json.gz#municipios |
| `municipios[ibge].acessos / pf / pj / capacidade_mbps` | int / float | Acessos fixos declarados no município. | — | sici → sici_municipios.json.gz#municipios |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | sici → sici.json.gz#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | sici → sici.json.gz#generated_at |
| `fonte` | str | URL do arquivo da Anatel de origem. | — | sici → sici.json.gz#fonte |
| `meses_disponiveis` | list[str] | Meses de declaração disponíveis (SICI fixo). | — | sici → sici.json.gz#meses_disponiveis |
| `total_acessos` | int | Total nacional de acessos no último mês. | — | sici → sici.json.gz#total_acessos |
| `total_cnpjs` | int | CNPJs com acessos no último mês. | — | sici → sici.json.gz#total_cnpjs |
| `matched_cnpjs` | int | CNPJs do SICI com ASN vinculado. | — | sici → sici.json.gz#matched_cnpjs |
| `matched_acessos` | int | Acessos desses CNPJs. | — | sici → sici.json.gz#matched_acessos |
| `serie_por_cnpj` | dict | Série mensal de acessos por CNPJ: lista de [mês, acessos, pf, pj]. | — | sici → sici.json.gz#serie_por_cnpj |
| `serie_total` | list[dict] | Série mensal nacional (mês, acessos, CNPJs). | — | sici → sici.json.gz#serie_total |
| `cnpj_to_asns` | dict | CNPJ → ASNs. | — | sici → sici.json.gz#cnpj_to_asns |
| `asn_to_cnpj` | dict | ASN → CNPJ. | — | sici → sici.json.gz#asn_to_cnpj |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | sici → sici_movel.json.gz#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | sici → sici_movel.json.gz#generated_at |
| `fonte` | str | URL do arquivo da Anatel de origem. | — | sici → sici_movel.json.gz#fonte |
| `meses_disponiveis` | list[str] | Meses de declaração disponíveis (SICI móvel). | — | sici → sici_movel.json.gz#meses_disponiveis |
| `total_acessos` | int | Total nacional de acessos no último mês. | — | sici → sici_movel.json.gz#total_acessos |
| `total_cnpjs` | int | CNPJs com acessos no último mês. | — | sici → sici_movel.json.gz#total_cnpjs |
| `matched_cnpjs` | int | CNPJs do SICI com ASN vinculado. | — | sici → sici_movel.json.gz#matched_cnpjs |
| `matched_acessos` | int | Acessos desses CNPJs. | — | sici → sici_movel.json.gz#matched_acessos |
| `serie_por_cnpj` | dict | Série mensal de acessos por CNPJ: lista de [mês, acessos, pf, pj]. | — | sici → sici_movel.json.gz#serie_por_cnpj |
| `serie_total` | list[dict] | Série mensal nacional (mês, acessos, CNPJs). | — | sici → sici_movel.json.gz#serie_total |
| `cnpj_to_asns` | dict | CNPJ → ASNs. | — | sici → sici_movel.json.gz#cnpj_to_asns |
| `asn_to_cnpj` | dict | ASN → CNPJ. | — | sici → sici_movel.json.gz#asn_to_cnpj |
| `asn_to_cnpj` | dict | ASN → CNPJ (Registro.br). | — | sici → sici.json.gz#asn_to_cnpj |
| `distrib_modalidade` | dict | Acessos por UF, PF×PJ e modalidade de cobrança (Pós-pago/Pré-pago). | — | sici → sici_movel.json.gz#distrib_modalidade |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | sici → sici_municipios.json.gz#snapshot_date |
| `mes_referencia` | str | Mês de referência da declaração. | — | sici → sici_municipios.json.gz#mes_referencia |
| `total` | int | Quantidade de municípios. | — | sici → sici_municipios.json.gz#total |
| `municipios` | dict | Código IBGE do município → acessos, PF/PJ e operadoras. | — | sici → sici_municipios.json.gz#municipios |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | sici → sici_movel_municipios.json.gz#snapshot_date |
| `mes_referencia` | str | Mês de referência da declaração. | — | sici → sici_movel_municipios.json.gz#mes_referencia |
| `total` | int | Quantidade de municípios. | — | sici → sici_movel_municipios.json.gz#total |
| `municipios` | dict | Código IBGE do município → acessos, PF/PJ e operadoras. | — | sici → sici_movel_municipios.json.gz#municipios |

## Limites

Dois meses de referência distintos (fixo × móvel). Divergência APNIC×Anatel não é erro: são medições de naturezas diferentes.
