<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Acessos de banda larga fixa (SICI/Anatel)

`anatel_sici` · tipo **bruta** · ativa

Acessos em serviço declarados mensalmente por prestadora (CNPJ), município, velocidade, tecnologia, meio e tipo de cliente (PF/PJ). Leitura incremental do ZIP de ~1 GB por HTTP Range; só baixa o ano corrente quando há mês novo e mantém cache imutável por mês.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.anatel_sici.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | mensal |
| Coleta hoje → alvo | semanal → diaria_se_novo_mes |
| Frescor máximo | 45d |
| Chaves | `cnpj`, `ibge`, `uf`, `mes_referencia` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/anatel_sici/` |

## Origem e licença

- **URL:** https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/acessos_banda_larga_fixa.zip
- **Formato:** zip/csv (~1 GB; leitura por HTTP Range)
- **Licença:** Dados Abertos Anatel (licença aberta, crédito à fonte)
- **Uso comercial:** `permitido`
- **Termos:** https://www.gov.br/anatel/pt-br/dados/dados-abertos
- **Evidência / ressalvas:** Plano de Dados Abertos da Anatel (verificado em 2026-10-13): dados 'disponibilizados sob licença aberta que permita sua livre utilização, consumo ou cruzamento, limitando-se a creditar a autoria ou a fonte' (Decreto 8.777/2016). A licença específica do conjunto em dados.gov.br não pôde ser lida (exige JavaScript/token).

## Saídas

- **Normalizado (normalized/):** `summary/sici_acessos.json.gz`, `../sici_cache/state.json`, `../sici_cache/months/{AAAA-MM}.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `mes_referencia` | str | Último mês de declaração disponível (AAAA-MM). Distinto da data do snapshot. | Citar sempre as duas datas. | sici → sici.json.gz#mes_referencia |
| `cnpjs[cnpj].acessos` | int | Contratos de acesso à Internet em serviço declarados no mês. Não é usuário nem domicílio. | Somar por CNPJ; não somar ASNs do mesmo CNPJ (acessos_compartilhados). | sici → sici.json.gz#cnpjs |
| `cnpjs[cnpj].pf / pj` | int | Acessos de clientes pessoa física e pessoa jurídica. | — | sici → sici.json.gz#cnpjs |
| `cnpjs[cnpj].capacidade_mbps` | float | Soma da velocidade contratada dos acessos (Mbps). | Soma de contratados, não de tráfego. | sici → sici.json.gz#cnpjs |
| `cnpjs[cnpj].por_tecnologia / por_meio / por_faixa / por_produto / por_municipio` | dict | Acessos por tecnologia, meio físico, faixa de velocidade, produto e município. | — | sici → sici.json.gz#cnpjs |
| `cnpjs[cnpj].velocidade_mediana_mbps / velocidade_media_mbps` | float | Mediana e média ponderada da velocidade contratada. | — | sici → sici.json.gz#cnpjs |
| `serie_por_cnpj / serie_total` | list | Série mensal de acessos por CNPJ e total nacional. | — | sici → sici.json.gz#serie_total |
| `distrib_velocidade[uf]` | dict | Distribuição de acessos por faixa de velocidade e UF, PF×PJ. | — | sici → sici.json.gz#distrib_velocidade |

## Limites

Autodeclarado; ausência pode ser omissão, não inexistência. Um CNPJ pode ter vários ASNs (acessos_compartilhados).

## Retenção

- **bruto:** cache incremental (1 arquivo por mês, imutável)
- **normalizado:** 52 semanas

## Quem usa

- **Fontes derivadas:** `bndes_operacoes`, `cgu_ceis_cnep`, `receita_cnpj`, `siasg_contratos`
- **Produtos:** `asn_docs`, `asn_saude`, `demanda_oferta`, `outorgas`, `penetracao`, `rede_territorio`, `regiao_municipios`, `sici`, `sici_indicadores`

## Pendências (nao_verificado)

- Confirmar a licença no registro do conjunto em dados.gov.br (página exige JavaScript; API pública responde 401).
