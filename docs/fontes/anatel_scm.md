<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Outorgas SCM (Serviço de Comunicação Multimídia)

`anatel_scm` · tipo **derivada** · ativa

Prestadoras com outorga código 045 no cadastro de prestadoras de serviços de telecomunicações da Anatel (provedores de banda larga fixa), filtradas do CSV nacional por código de serviço, com endereço da sede e contato.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.anatel_scm.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | irregular |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 8d |
| Chaves | `cnpj`, `uf`, `ibge` |
| Entradas | `anatel_outorgas` |
| Amostra de teste | `tests/fixtures/raw/anatel_outorgas/` |

## Origem e licença

- **URL:** https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/prestadoras_servicos_telecomunicacoes.zip
- **Formato:** zip/csv (;-delimitado, UTF-8 com BOM, ~79 MB)
- **Licença:** Dados Abertos Anatel (licença aberta, crédito à fonte)
- **Uso comercial:** `permitido`
- **Termos:** https://www.gov.br/anatel/pt-br/dados/dados-abertos
- **Evidência / ressalvas:** Plano de Dados Abertos da Anatel (verificado em 2026-10-13): dados 'disponibilizados sob licença aberta que permita sua livre utilização, consumo ou cruzamento, limitando-se a creditar a autoria ou a fonte' (Decreto 8.777/2016). A licença específica do conjunto em dados.gov.br não pôde ser lida (exige JavaScript/token).

## Saídas

- **Normalizado (normalized/):** `summary/anatel_scm.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `cnpj` | str | CNPJ (14 dígitos) da prestadora outorgada. | Chave de junção com SICI, Registro.br e Receita. | outorgas → scm.json.gz |
| `razao_social / nome_fantasia` | str | Razão social e nome fantasia da prestadora. | — | outorgas → scm.json.gz |
| `data_outorga` | str | Data de inclusão da outorga no cadastro da Anatel. | — | outorgas → scm.json.gz |
| `num_servico` | str | Código do serviço da notificação (045 SCM, 010 SMP, 171 STFC, 750 SeAC). | — | outorgas → scm.json.gz |
| `logradouro / numero / complemento / bairro / cep` | str | Endereço da sede da prestadora na notificação. | Endereço de pessoa jurídica; exposto nas rotas públicas listadas (decisão do mantenedor 2026-10-11). | outorgas → scm.json.gz |
| `municipio / uf / codigo_ibge` | str | Município e UF da sede e código IBGE do município. | — | outorgas → scm.json.gz |
| `telefone / email` ⚠️ dado pessoal/contato | str | Contato declarado na notificação. | Removido das rotas públicas; só via /asns/{asn}/contacts com login (teste T4). | outorgas → scm.json.gz |

## Limites

Outorga/notificação não prova prestação efetiva de serviço nem tamanho da operação (usar SICI). Endereço é o da sede, não da área de cobertura. Mesmo arquivo-fonte dos demais serviços Anatel: em 2026-10-11 os 4 CSVs brutos (SCM, SMP, STFC, SeAC) têm MD5 idêntico (45d83b2a21013a16d5fa9dd31822cac2, 79.361.097 bytes) — o SCM não é outra base: é o mesmo arquivo; o filtro por código de serviço faz a diferença. Candidato a download único (anatel_outorgas).

## Retenção

- **bruto:** 4 versões (alvo: 1 download compartilhado)
- **normalizado:** 52 semanas

## Quem usa

- **Fontes derivadas:** `bndes_operacoes`, `cgu_ceis_cnep`, `curada_marcas_operadoras`, `receita_cnpj`, `scm_geo`, `siasg_contratos`, `socios_grupos`
- **Produtos:** `cadastro_empresas`, `consumidor`, `outorgas`, `qualidade`, `sici_indicadores`

## Pendências (nao_verificado)

- Confirmar a licença no registro do conjunto em dados.gov.br (página exige JavaScript; API pública responde 401).
- Frequência real de atualização do CSV da Anatel não medida (fonte_atualiza irregular).
