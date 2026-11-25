<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Cadastro das empresas de telecom (dados abertos do CNPJ — Receita Federal)

`receita_cnpj` · tipo **bruta** · ativa

Lê, em fluxo e arquivo a arquivo, as partes de Estabelecimentos, Empresas e Simples do dump mensal do CNPJ e guarda só o recorte de telecom (CNPJs das outorgas SCM, SMP, STFC e SeAC e do SICI, e todo estabelecimento com CNAE 61 principal ou secundário), mais as tabelas de município, natureza jurídica e CNAE. Por estabelecimento: CNPJ, matriz ou filial, situação, datas, UF, município (código da Receita), CNAE principal e secundários; por empresa: natureza, capital, porte, Simples e MEI. Não guarda o dump (≈ 7,5 GB por mês), e-mail, telefone, rua nem CEP.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.receita_cnpj.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | mensal |
| Coleta hoje → alvo | mensal → mensal |
| Frescor máximo | 45d |
| Chaves | `cnpj` |
| Entradas | `anatel_scm`, `anatel_smp`, `anatel_stfc`, `anatel_seac`, `anatel_sici` |
| Amostra de teste | `tests/fixtures/raw/receita_cnpj/` |

## Origem e licença

- **URL:** https://arquivos.receitafederal.gov.br/index.php/s/YggdBLfdninEJX9
- **Formato:** zip/csv (`;`, aspas, latin-1, sem cabeçalho; Estabelecimentos com 30 colunas, Empresas e Simples com 7) via WebDAV Nextcloud, uma pasta por mês (AAAA-MM)
- **Licença:** Dados Abertos (Decreto 8.777/2016)
- **Uso comercial:** `nao_verificado`
- **Termos:** https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos/cadastros/cnpj
- **Evidência / ressalvas:** Coleta autorizada expressamente pelo mantenedor em 2026-11-07, apesar do `robots.txt` do host (`User-agent: *` / `Disallow: /`, lido em 2026-11-06). Condições: `User-Agent` identificado, uma requisição por vez, pausa entre downloads (`RECEITA_PAUSA_S`, padrão 2 s), só os arquivos do mês corrente. Layout conferido em 2026-11-07 contra o arquivo real Estabelecimentos1.zip de 2026-10 (30 colunas). Empresário individual (natureza 213-5): sem razão social nem nome fantasia, porque o nome é o da pessoa física.

## Saídas

- **Normalizado (normalized/):** `summary/receita_cnpj.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `estabelecimentos[cnpj8][]` | lista | Estabelecimentos do recorte de telecom por CNPJ básico. `c` CNPJ de 14 dígitos, `m` 1 matriz ou 2 filial, `s` situação cadastral (02 ativa, 08 baixada), `d` início da atividade, `ds` data da situação, `u` UF, `mu` código de município da Receita, `p` CNAE principal, `x` CNAEs secundários (até 20), `n` nome fantasia (ausente em empresário individual). | Sem rua, número, complemento, bairro, CEP, telefone nem e-mail. O município é código da Receita (não é IBGE): a tradução é feita no produto, por nome e UF. | — |
| `empresa[cnpj8]` | dict | Natureza jurídica, capital social, porte (00 não informado, 01 micro, 03 pequeno, 05 demais) e razão social. | Empresário individual (natureza 2135) não leva razão social. | — |
| `simples[cnpj8]` | dict | Opção pelo Simples Nacional e pelo MEI, com as datas de opção e de exclusão. | — | — |
| `municipios_rfb / naturezas / cnaes` | dict | Tabelas de apoio da Receita (código → nome), restritas aos CNAEs que aparecem no recorte. | — | — |
| `dump_reference / linhas_lidas / estabelecimentos_guardados / universo_cnpjs_basicos` | dict | Mês (AAAA-MM) do dump, linhas lidas, estabelecimentos guardados e tamanho do universo de CNPJs das outorgas e do SICI. | — | — |

## Limites

Uma passada pelos Estabelecimentos: uma filial de CNAE diferente de 61 de uma empresa que só se revela telecom por outro estabelecimento, e que não está nas outorgas nem no SICI, não entra. O cadastro é o da data do dump (mensal), não o de hoje. Município por nome e UF: homônimos na mesma UF não existem, mas grafias diferentes entre a Receita e o IBGE podem ficar sem casamento.

## Retenção

- **normalizado:** 3 versões

## Quem usa

- **Fontes derivadas:** `siasg_contratos`, `socios_grupos`
- **Produtos:** `cadastro_empresas`, `contratos`

## Pendências (nao_verificado)

- Termos de uso do conjunto CNPJ e uso comercial não lidos (a página oficial exige JavaScript); revisão jurídica em aberto.
- O `robots.txt` do host segue `Disallow: /` e a coleta vale pela autorização expressa do mantenedor; ela para se a Receita pedir.
