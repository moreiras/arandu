<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# CGU — sanções a empresas (CEIS e CNEP), recorte de telecom

`cgu_ceis_cnep` · tipo **bruta** · ativa

Cadastro de Empresas Inidôneas e Suspensas (CEIS) e Cadastro Nacional de Empresas Punidas (CNEP), da CGU, no Portal da Transparência. Guarda só pessoa jurídica do universo de telecom (CNPJ básico nas outorgas, no SICI ou nos estabelecimentos de CNAE 61 da Receita). Por sanção: cadastro, código, categoria, datas de início, fim e publicação, abrangência, órgão sancionador (UF e esfera), fundamento legal, número do processo e, no CNEP, o valor da multa. Pessoa física (CPF) é descartada na leitura.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.cgu_ceis_cnep.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | diaria |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 14d |
| Chaves | `cnpj` |
| Entradas | `anatel_scm`, `anatel_smp`, `anatel_stfc`, `anatel_seac`, `anatel_sici` |
| Amostra de teste | `tests/fixtures/raw/cgu_ceis_cnep/` |

## Origem e licença

- **URL:** https://portaldatransparencia.gov.br/sancoes
- **Formato:** ZIP diário `download-de-dados/{ceis,cnep}/AAAAMMDD` com um CSV latin-1 (`;`, aspas, cabeçalho; CEIS 24 colunas, CNEP 25); redireciona para dadosabertos-download.cgu.gov.br; sem chave
- **Licença:** Dados abertos do Governo Federal (Decreto 8.777/2016). Termo de Uso do Portal (§3, lido em 2026-11-10): o cidadão pode "visualizar e utilizar os dados disponíveis da forma que melhor lhe convier"; o termo não nomeia licença nem exige atribuição
- **Uso comercial:** `permitido`
- **Termos:** https://portaldatransparencia.gov.br/termos-de-uso
- **Evidência / ressalvas:** Endereço e layout conferidos em 2026-11-08 contra os arquivos reais de 2026-11-06 (CEIS 23.746 linhas, 14.588 de pessoa jurídica; CNEP 1.854 linhas). Nem todo dia tem arquivo (fim de semana e atraso respondem 403, "AccessDenied"): o coletor volta até 10 dias. Uma requisição por cadastro por execução, com User-Agent identificado. Linguagem de evidência: registro do órgão sancionador na data do arquivo, sem adjetivo; vigência calculada no produto. Termos lidos em 2026-11-10 a partir do PDF colado pelo mantenedor (o site responde 405 com desafio anti-bot a acesso automatizado, I-012): sem restrição de uso comercial, de redistribuição, de base derivada nem de acesso automatizado; atribuição "CGU, Portal da Transparência" adotada por prática, não por exigência. Leitura do executor, não parecer jurídico. Dicionários do CEIS e do CNEP lidos em 2026-11-10 (PDF colado pelo mantenedor, colunas completas e descrições cortadas à direita): 24 colunas no CEIS e 25 no CNEP, como o layout medido; campos de pessoa: TIPO DE PESSOA, CPF OU CNPJ, NOME DO SANCIONADO, NOME INFORMADO PELO ÓRGÃO, RAZÃO SOCIAL e NOME FANTASIA (Receita) e OBSERVAÇÕES (texto livre); nenhum é guardado. Por dicionário, sanção inativada sai do CEIS e multa paga sai do CNEP: ausência no arquivo não prova que nunca houve sanção.

## Saídas

- **Normalizado (normalized/):** `summary/cgu_ceis_cnep.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `sancoes[cnpj14][]` | lista | Sanções do CNPJ (matriz ou filial) com cadastro (CEIS ou CNEP), código, categoria, início, fim, publicação, abrangência, órgão sancionador, UF e esfera, fundamento legal, processo e valor da multa (CNEP). | Registro do órgão sancionador, sem julgamento. A fonte usa data final 2099-12-31 para sanção sem prazo; o produto trata como "sem prazo". | — |
| `arquivos / linhas_lidas / linhas_pessoa_juridica / sancoes_guardadas / cnpjs / universo_cnpjs_basicos` | dict | Data dos arquivos de origem de cada cadastro, linhas lidas, linhas de pessoa jurídica e o recorte guardado. | — | — |

## Limites

Só pessoa jurídica do universo de telecom. A sanção pode já ter sido suspensa, anulada ou cumprida sem que o arquivo do dia reflita; vale a data de referência. Pode haver sanção a uma filial; o produto agrupa por raiz de CNPJ e mostra o CNPJ.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `financiamento_sancoes`
