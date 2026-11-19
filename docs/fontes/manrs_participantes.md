<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# MANRS — participantes do programa de operadores de rede

`manrs_participantes` · tipo **bruta** · ativa

Tabela pública de participantes do programa de operadores de rede do MANRS (organização, data de aprovação, países, ASNs e situação das ações). Só guardada, comprimida; serve para calcular agregados (participação por UF e porte e comparação de prontidão). O registro por organização ou ASN nunca é publicado.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.manrs_participantes.collect` |
| Publicável | não (exposição: nenhuma) |
| Política de falha | opcional |
| Cadência (origem atualiza) | semanal |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 21d |
| Chaves | `asn` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/manrs_participantes/` |

## Origem e licença

- **URL:** https://manrs.org/netops/participants/
- **Formato:** HTML (`<table id="participant-table">`); o botão "CSV" da página é gerado no navegador a partir da mesma tabela
- **Licença:** MANRS/GCA, termos de serviço (cláusula 2)
- **Uso comercial:** `restrito`
- **Termos:** https://manrs.org/terms-of-service/
- **Evidência / ressalvas:** Termos lidos em 2026-11-03: dados de outras redes só podem ser divulgados de forma agregada, sem identificá-las e sem dado pessoal; uso apenas não comercial, sem revenda nem sublicença; atribuição obrigatória em toda publicação ("Provided by the MANRS with support from the Global Cyber Alliance"); proibido sugerir endosso do MANRS ou da GCA. O robots.txt permite (search=yes, use=reference). A API do Observatório (observatory.manrs.org/api/v2) lista participantes só com chave; a chave não foi pedida.

## Saídas

- **Bruto (raw/):** `summary/manrs-participantes-AAAA-MM-DD.html.gz`
- **Normalizado (normalized/):** `summary/manrs_participantes.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `participantes[]` | lista | Uma entrada por organização participante, com `org`, `aprovado`, `areas`, `asns` e as ações (`filtragem`, `anti_spoofing`, `coordenacao`, `roteamento`) como a tabela as mostra (marca de ação atendida ou pontuação em %). | Nunca sai de data/normalized: só `products.manrs.build` lê, e só publica agregados com mínimo de 5 ASNs participantes por recorte. | — |
| `medido_em` | str | Data da última medição do Observatório, informada na legenda da tabela. | — | — |

## Limites

A lista é o que as organizações declaram ao se juntar; a tabela do site muda sem aviso (cláusula 2.5). Falha alto se vier com menos de 500 organizações ou 100 com área BR.

## Retenção

- **bruto:** 4 versões
- **normalizado:** 52 semanas

## Pendências (nao_verificado)

- Pedir a chave da API do Observatório; se sair, trocar só o coletor.
