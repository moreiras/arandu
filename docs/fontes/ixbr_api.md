<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Cadastro de membros do IX.br (dashboard.ix.br)

`ixbr_api` · tipo **bruta** · ativa

Lista de membros cadastrados em cada IXP do IX.br via `dashboard.ix.br/generate_json?ixp={code}`, inclusive os que trocam tráfego só bilateralmente e por isso não aparecem no Route Server.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.ixbr_api.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | critica |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 8d |
| Chaves | `ixp`, `asn` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/ixbr_api/` |

## Origem e licença

- **URL:** https://dashboard.ix.br/generate_json?ixp={code}
- **Formato:** JSON (members[].asn, name)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** Endpoint público do dashboard do IX.br. Termos de uso do dashboard não localizados (a raiz dashboard.ix.br responde 404 em 2026-10-13).

## Saídas

- **Bruto (raw/):** `{ixp}/ixbr_members.json`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ixp` | str | Código do IXP (ex.: sp, rj). | — | — |
| `fetched_at` | datetime | Instante UTC em que a lista foi obtida. | — | — |
| `members_count` | int | Quantidade de membros cadastrados no IXP (>= ASNs vistos no Route Server). | — | ixp_docs → ixps/index.json#ixbr_members_count |
| `members[].asn` | int | ASN do membro cadastrado. | Servido pela API lendo raw/{date}/{ixp}/ixbr_members.json (o raw não pode ser removido antes da retenção do snapshot). | ixp_docs → ixps/index.json#ixbr_members_count |
| `members[].name` | str | Nome do membro como cadastrado no IX.br. | Servido pela API lendo o raw (ver members[].asn). | — |

## Limites

Cadastro autodeclarado/administrativo: membro cadastrado não implica sessão BGP ativa nem tráfego.

## Retenção

- **bruto:** 4 versões

## Quem usa

- **Fontes derivadas:** `peeringdb_intl_geo`
- **Produtos:** `ixp_docs`, `route_servers`

## Pendências (nao_verificado)

- Termos de uso do dashboard.ix.br não localizados.
