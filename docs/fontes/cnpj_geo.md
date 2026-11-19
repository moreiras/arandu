<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Cadastro e geolocalização das organizações (BrasilAPI + Nominatim)

`cnpj_geo` · tipo **derivada** · ativa

Para cada CNPJ das organizações BR, obtém dados cadastrais (BrasilAPI) e geocodifica o endereço (Nominatim), com cache persistente em geo_cache/cnpj.json.gz (o primeiro run leva horas).

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.cnpj_geo.enrich` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 8d |
| Chaves | `asn`, `cnpj`, `ibge`, `uf`, `ponto` |
| Entradas | `rdap` |
| Amostra de teste | `tests/fixtures/raw/brasilapi/` |

## Origem e licença

- **URL:** https://brasilapi.com.br/api/cnpj/v1/{cnpj}
- **Formato:** JSON (dados cadastrais do CNPJ) + Nominatim
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Termos:** https://brasilapi.com.br/
- **Evidência / ressalvas:** BrasilAPI é uma iniciativa comunitária e pede para não abusar do serviço; não declara licença dos dados (originários da Receita Federal). Geocodificação: Nominatim/ODbL (ver scm_geo).

## Saídas

- **Normalizado (normalized/):** `summary/geo_orgs.json.gz`, `../geo_cache/cnpj.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `orgs[asn].razao_social / nome_fantasia` | str | Razão social e nome fantasia no cadastro do CNPJ. | — | asn_docs → asns/{asn}.json#geo_org |
| `orgs[asn].cnae_fiscal / cnae_fiscal_descricao` | int\|str | Atividade econômica principal (CNAE). | — | asn_docs → asns/{asn}.json#geo_org |
| `orgs[asn].situacao_cadastral` | int\|str | Situação cadastral do CNPJ (ativa, baixada, suspensa…) e motivo. | Cache: pode estar defasado até o próximo refresh. | asn_docs → asns/{asn}.json#geo_org |
| `orgs[asn].natureza_juridica / porte` | str | Natureza jurídica e porte (ME, EPP, demais). | — | asn_docs → asns/{asn}.json#geo_org |
| `orgs[asn].data_inicio_atividade` | str | Data de início de atividade. | — | asn_docs → asns/{asn}.json#geo_org |
| `orgs[asn].logradouro … cep / municipio / uf` | str | Endereço cadastral da organização (pessoa jurídica). | Endereço de PJ exposto nas rotas públicas listadas (decisão 2026-10-11). | asn_docs → asns/{asn}.json#geo_org |
| `orgs[asn].email / ddd_telefone_1 / ddd_telefone_2` ⚠️ dado pessoal/contato | str | Contato cadastral do CNPJ. | Presente no arquivo publicado; removido das rotas públicas (T4). | asn_docs → asns/{asn}.json#geo_org |
| `orgs[asn].lat / lon / geo_confidence / geo_source` | float\|str | Coordenadas do endereço e como foram obtidas. | Mesmos rótulos de confiança das outorgas. | asn_docs → asns/{asn}.json#geo_org |

## Limites

Cadastro do CNPJ pode divergir do endereço operacional; empresa de grupo pode ter outro CNPJ para a rede (ver socios_grupos).

## Retenção

- **normalizado:** 52 semanas; cache permanente

## Quem usa

- **Produtos:** `asn_docs`, `mapas_prefixos`, `regiao_municipios`

## Pendências (nao_verificado)

- Licença/termos de uso da BrasilAPI e dos dados de CNPJ expostos por ela.
- Atribuição OSM/ODbL para a geocodificação.
