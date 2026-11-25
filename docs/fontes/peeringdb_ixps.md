<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# IXPs e membros (PeeringDB netixlan)

`peeringdb_ixps` · tipo **bruta** · ativa

Para os IXPs externos configurados e para os 40 IXPs do IX.br, consulta /api/netixlan do PeeringDB e lista os ASNs presentes em cada um; cruza o cadastro do PeeringDB com o do IX.br.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.peeringdb_ixps.collect` |
| Publicável | sim (exposição: aberta) |
| Decisão sobre a exposição | Aberta por decisão do projeto (D9, 2026-11-24): o que a fonte alimenta é servido sem login na interface, na API e no MCP, salvo o que está dito a seguir, e a abertura é intencional, não um padrão esquecido. Dado do PeeringDB (AUP). A lista de IXPs externos com contagens de membros é aberta; a lista completa de membros de um PTT externo (`/external-ixps/{code}`) e o comparador com `ext:` exigem login, porque é a redistribuição em massa que a AUP restringe e que a rota já declarava "Requer autenticação". Os membros dos PTTs do IX.br seguem abertos (origem: IX.br). A diferença é uma escolha de risco do projeto, não uma conclusão jurídica; a consulta jurídica segue aberta. |
| Atribuição exigida | PeeringDB (https://www.peeringdb.com). Uso sujeito à AUP (https://www.peeringdb.com/aup); a forma de atribuição que o PeeringDB exige não foi verificada. |
| Política de falha | critica |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | semanal → diaria |
| Frescor máximo | 8d |
| Chaves | `ixp`, `asn` |
| Entradas | `curada_peeringdb_ixps` |
| Amostra de teste | `tests/fixtures/raw/peeringdb/` |

## Origem e licença

- **URL:** https://www.peeringdb.com/api/netixlan?ixlan_id={id}
- **Formato:** JSON (API REST)
- **Licença:** PeeringDB AUP
- **Uso comercial:** `restrito`
- **Termos:** https://www.peeringdb.com/aup
- **Evidência / ressalvas:** PeeringDB AUP (https://www.peeringdb.com/aup, verificado em 2026-10-13): fora de 'finalidades operacionais de Internet' aprovadas, nenhuma parte dos dados pode ser reproduzida ou repassada em massa sem autorização; o uso excluído inclui 'listas de marketing, mapeamento demográfico ou qualquer outra aplicação comercial'.

## Saídas

- **Bruto (raw/):** `summary/peeringdb-ixps-{as_of}.json`
- **Normalizado (normalized/):** `summary/peeringdb_ixps.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `external_ixps[code].name/city/country` | str | Nome, cidade e país do IXP externo (da configuração, não da API). | — | ixp_docs → external-ixps/{ixp}.json |
| `external_ixps[code].pdb_ix_id` | int | Identificador do IX no PeeringDB. | — | ixp_docs → external-ixps/{ixp}.json#pdb_ix_id |
| `external_ixps[code].members[]` | list[dict] | Membros do IXP externo (asn, velocidade da porta). | Marca is_br pelo universo LACNIC-BR. O nome do membro vem de asn_names na publicação (o `name` do netixlan é o nome do PTT; se um snapshot o tiver gravado como nome do membro, a API o corrige na leitura). | ixp_docs → external-ixps/{ixp}.json#members |
| `ixbr_ixps[code].asns` | list[int] | ASNs que declaram presença no IXP do IX.br no PeeringDB. | Comparado ao Route Server e ao cadastro do IX.br; diferença = membro sem cadastro PDB. | asn_docs → asns/{asn}.json#ixp_member_codes |
| `per_asn[asn].external / ixbr` | list[str] | Códigos de IXPs externos e do IX.br em que o ASN declara presença. | — | asn_docs → asns/{asn}.json#external_ixps |

## Limites

Presença autodeclarada no PeeringDB; ausência não significa que a rede não esteja no IXP. Limite de 250 req/h sem chave de API (1000 com PEERINGDB_API_KEY); resposta 429 espera 65 s.

## Retenção

- **bruto:** 4 versões
- **normalizado:** 52 semanas

## Quem usa

- **Fontes derivadas:** `peeringdb_fac`
- **Produtos:** `asn_docs`, `instalacoes`, `ixp_docs`

## Pendências (nao_verificado)

- Uso comercial e redistribuição de dados do PeeringDB dependem de autorização do PeeringDB (AUP); confirmar com o PeeringDB e o jurídico.
