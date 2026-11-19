<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# VRPs e ASPA validados (Routinator)

`rpki_collector` · tipo **bruta** · ativa

Lê a saída do Routinator avulso (scripts/rpki-avulso.sh grava data/cache/rpki/vrps.json antes do worker) e grava os VRPs (ROAs validados) e os objetos ASPA validados diretamente em published/{date}/rpki/. Base do status RPKI (valid/invalid/not-found) por rota.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.rpki_collector.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | diaria → diaria |
| Frescor máximo | 2d |
| Chaves | `asn`, `prefixo` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/rpki/` |

## Origem e licença

- **URL:** rsync/RRDP dos Trust Anchors dos 5 RIRs (via Routinator, `routinator vrps -f json`)
- **Formato:** JSON do Routinator (VRPs, ASPA)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** Dados RPKI dos Trust Anchors dos 5 RIRs validados localmente; termos de cada TAL (em especial ARIN) não verificados.

## Saídas

- **Publicado direto (published/):** `rpki/vrp_list.json.gz`, `rpki/aspa_list.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `vrps[].asn` | str\|int | ASN autorizado a originar o prefixo pela ROA. | — | rpki_collector → rpki/vrp_list.json.gz#asn |
| `vrps[].prefix` | str | Prefixo coberto pela ROA. | — | rpki_collector → rpki/vrp_list.json.gz#prefix |
| `vrps[].maxLength` | int | Comprimento máximo de prefixo autorizado (mais específicos até este valor são cobertos). | — | rpki_collector → rpki/vrp_list.json.gz#maxLength |
| `vrps[].ta` | str | Trust Anchor (RIR) que emitiu a ROA. | — | rpki_collector → rpki/vrp_list.json.gz#ta |
| `aspa[].customer` | int | ASN que publicou o objeto ASPA (cliente). | — | rpki_collector → rpki/aspa_list.json.gz#customer |
| `aspa[].providers` | list[int] | ASNs provedores autorizados pelo objeto ASPA. | — | rpki_collector → rpki/aspa_list.json.gz#providers |
| `aspa[].tal` | str | Trust Anchor (RIR) que emitiu o objeto ASPA. | — | rpki_collector → rpki/aspa_list.json.gz#tal |

## Limites

Instantâneo da validação feita logo antes do pipeline; com o cache frio (instalação nova) a primeira execução leva horas num disco lento (2 h 58 min, medido); a morno, ~20 min. O coletor recusa arquivo com mais de RPKI_MAX_IDADE_H (12 h). ROAs expiram/mudam rápido (alvo diário). ASPA ainda tem baixa adoção.

## Retenção

- **publicado:** imutável; bruto não retido (data/cache/rpki/vrps.json é sobrescrito a cada execução)

## Quem usa

- **Produtos:** `as_relationships`, `asn_saude`, `routing_analysis`, `rpki`

## Pendências (nao_verificado)

- Lacuna conhecida: rpki_collector e coletores de rede não entram no replay.
