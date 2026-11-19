<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Contatos dos ASNs do Brasil no RDAP do Registro.br (administrativo e abuso)

`rdap_contatos` · tipo **bruta** · ativa

Consulta `GET https://rdap.registro.br/autnum/{asn}` (RDAP, RFC 9083) em rodízio lento, um ASN por vez, e guarda o e-mail e o `handle` dos contatos `administrative` e `abuse`. Dado de contato: nunca em rota pública nem no MCP; é servido apenas ao usuário logado (`/asns/{asn}/contacts`) e NÃO é copiado para published/. A resposta do servidor fica incompleta (sem e-mails, HTTP 200) sob ritmo alto; cada resposta tem a completude verificada e a incompleta não conta como leitura. Não confundir com `rdap` (mapa derivado ASN→nome/CNPJ, sem consulta externa).

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.rdap_contatos.collect` |
| Publicável | sim (exposição: login) |
| Política de falha | opcional |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | diaria → diaria |
| Frescor máximo | 30d |
| Chaves | `asn` |
| Entradas | `rdap` |
| Amostra de teste | `tests/fixtures/raw/rdap_contatos/` |

## Origem e licença

- **URL:** https://rdap.registro.br/autnum/
- **Formato:** JSON RDAP (RFC 9083; entidades `registrant`, `administrative`, `abuse` com `vcardArray`)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Termos:** nao_verificado
- **Evidência / ressalvas:** Serviço público do Registro.br. Termos de uso do RDAP não lidos pelo executor (sem página de termos localizada na medição de 2026-11-10); tratar como dado de contato de uso restrito (só login). Medição de 2026-11-09 e 2026-11-10: sob ritmo alto a resposta vem sem e-mails e com HTTP 200; em rajada o servidor fecha a conexão. Coletor com User-Agent identificado, uma consulta por vez e intervalo de `RDAP_INTERVALO_S` (padrão 12 s, com folga: a medição a 10 s deu 100% de respostas completas).

## Saídas

- **Normalizado (normalized/):** `summary/rdap_contatos.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `contatos[asn].contatos[].papel` | str | Papel do contato no RDAP (`administrative` ou `abuse`). | — | asn_docs → /api/v1/asns/{asn}/contacts |
| `contatos[asn].contatos[].email` ⚠️ dado pessoal/contato | str | E-mail do contato, em minúsculas. | Só via /asns/{asn}/contacts com login; nunca em log, rota pública nem MCP. | asn_docs → /api/v1/asns/{asn}/contacts |
| `contatos[asn].contatos[].handle` ⚠️ dado pessoal/contato | str | Identificador do contato no Registro.br (pode identificar pessoa física; mantenedor decide se fica). | Só via login. | — |
| `contatos[asn].em / tentou_em / status / incompletas` | dict | Data da última leitura VÁLIDA (`em`; nula se só houve respostas incompletas), data da última tentativa, situação (`completo`, `parcial_confirmado`, `nao_encontrado`, `incompleto`) e quantas respostas incompletas em ritmo saudável o ASN acumulou. | Incompleta não conta como leitura válida: a leitura anterior continua valendo com a data dela. `parcial_confirmado` = faltou e-mail em duas consultas com a fonte respondendo bem (ausência real, não degradação). | asn_docs → /api/v1/asns/{asn}/contacts |
| `cobertura` | dict | ASNs no universo (Registro.br), com leitura válida, completos, parcial confirmado, não encontrados, só incompletos, datas da leitura mais antiga e mais recente. | Declarada ("N de M ASNs com contato lido; leitura mais antiga em AAAA-MM-DD"); ASN sem leitura não é ASN sem contato. | asn_docs → /api/v1/asns/{asn}/contacts |

## Limites

Cobertura em rodízio (dias até cobrir o universo dependem do ritmo). Contatos do Registro.br, autodeclarados pelo titular. ASN sem leitura válida não quer dizer ASN sem contato. Sem nome, endereço, telefone nem representante legal.

## Retenção

- **normalizado:** 2 versões (dado de contato; o estado do rodízio vive no mais recente)

## Pendências (nao_verificado)

- Termos de uso do RDAP do Registro.br não lidos (licenca/uso_comercial/termos nao_verificado). Aprovar o recorte mínimo (handle fica ou sai) e a retenção do dado de contato.
- Ritmo (RDAP_INTERVALO_S) e doses por execução: confirmar a medição com `arandu run` real.
