<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Quedas de Internet por país e ASN (IODA)

`ioda_outages` · tipo **bruta** · inativa

BLOQUEADA: o IODA (Internet Outage Detection and Analysis, Georgia Tech / CAIDA) serviria a linha do tempo de quedas por UF e ASN. Os termos de uso dos dados não foram localizados e a fonte só entra com termos lidos ou autorização escrita. O módulo apenas avisa e sai com código 2, sem fazer requisição.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.ioda_outages.collect` |
| Publicável | não (exposição: nenhuma) |
| Política de falha | opcional |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | nao_verificado |
| Chaves | — |
| Entradas | — |

## Origem e licença

- **URL:** https://api.ioda.caida.org/
- **Formato:** JSON (API do IODA; entidades por país/região/ASN)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** Em 2026-11-06: o host api.ioda.inetintelligence.cc.gatech.edu não resolve; o host correto é api.ioda.caida.org, que não respondeu nos testes (rede inalcançável/tempo esgotado); ioda.live é o painel web. O repositório InetIntel/ioda-api diz que o software é restrito a pesquisa e educação acadêmica sem permissão; os dados têm copyright da Georgia Tech Research Corporation. Nenhum termo de dados localizado. Nenhuma requisição de coleta foi feita.

## Saídas


## Dicionário de campos

_Sem dicionário de campos declarado._

## Limites

Sem coleta. Pedir autorização escrita ao IODA (Georgia Tech) antes de ativar.

## Pendências (nao_verificado)

- Termos de uso dos dados do IODA e autorização escrita.
- Confirmar o host da API (api.ioda.caida.org) e o formato quando a rede e os termos permitirem.
