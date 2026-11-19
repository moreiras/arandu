<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Shodan — contagens de serviços expostos por ASN do Brasil (API principal, atribuição obrigatória)

`shodan_exposicao` · tipo **bruta** · ativa

Contagens da API principal do Shodan (`/shodan/host/count`, só contagens, sem listar hosts) por ASN do Brasil, em rodízio de dias: total de serviços observados, portas mais vistas, serviços em portas de risco (acesso remoto, gestão de roteador/CPE, banco de dados, compartilhamento) e, se o plano da conta tiver a faceta, CVEs mais vistas. Nunca lista de IPs nem host individual. Requer a chave da API (variável `SHODAN` do .env, entregue ao worker como `SHODAN_API_KEY`).

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.shodan_exposicao.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | usar_ultima_valida |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | diaria → diaria |
| Frescor máximo | 14d |
| Chaves | `asn` |
| Entradas | `rdap` |
| Amostra de teste | `tests/fixtures/raw/shodan_exposicao/` |

## Origem e licença

- **URL:** https://api.shodan.io/shodan/host/count
- **Formato:** JSON (`total`, `facets`; `matches` sempre vazio)
- **Licença:** Shodan API — uso em produtos permitido com atribuição ao Shodan
- **Uso comercial:** `nao_verificado`
- **Termos:** nao_verificado
- **Evidência / ressalvas:** O mantenedor leu em account.shodan.io/billing (exige login; o executor não conferiu o texto) "you can integrate the API in your products as long as the data is attributed to Shodan". Os termos completos não foram lidos pelo executor (uso_comercial e termos nao_verificado). Segundo a documentação (lida em 2026-11-10), `host/count` não consome créditos de consulta, mas a página não informa o limite de taxa nem os filtros pagos e diz que o método se comporta como a busca (que gasta 1 crédito com filtro): o coletor confere `/api-info` e para se os créditos caírem; a medição na conta real (facetas e filtros do plano, créditos, tempo) é a sondagem `python -m sources.shodan_exposicao.collect --sondar`. Atribuição ao Shodan em tudo que derive dele. A chave vai na querystring (exigência da API): o coletor cala o log do httpx e nunca registra URL nem exceção de rede.

## Saídas

- **Normalizado (normalized/):** `summary/shodan_exposicao.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn]` | dict | Leitura do ASN: `em` (data), `total` (serviços observados, banners e não IPs únicos), `portas` (as 20 mais vistas, [porta, n]), `risco` (contagem exata de cada porta de risco com serviço), `risco_total` (serviços em qualquer porta de risco) e `vulns` (CVEs mais vistas [cve, n]; nulo se o plano não tem a faceta ou o ASN não foi consultado por ela). | Rodízio de `SHODAN_ASNS_POR_EXECUCAO` ASNs por execução (padrão 1.500), os nunca lidos primeiro e depois os de leitura mais antiga. Três consultas por ASN com serviço (geral, portas de risco, CVEs), uma só se não há serviço. `total` 0 = o Shodan não observou serviço; ASN ausente = não consultado. | exposicao → exposicao/asns.json.gz#asns |
| `plano` | dict | Facetas que a conta aceita (`port`; `vuln` pode ser `indisponivel`, com a data do teste). | A faceta `vuln` recusada é registrada e só reexperimentada depois de 30 dias. | exposicao → exposicao/asns.json.gz#plano |
| `licenca / atribuicao` | str | Licença/termos resumidos e o texto de atribuição ao Shodan, que acompanha todo derivado. | — | exposicao → exposicao/asns.json.gz#licenca; exposicao → exposicao/asns.json.gz#fonte |

## Limites

Contagem observada pelo Shodan na data da leitura; não é prova de vulnerabilidade nem inventário. Cobre só o que o Shodan varreu. Rodízio (cada ASN com a sua data). Banners, não hosts únicos. CVEs só se o plano tem a faceta.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `exposicao`

## Pendências (nao_verificado)

- Termos completos da API do Shodan não lidos pelo executor (uso_comercial, termos nao_verificado); só a frase da página de cobrança lida pelo mantenedor.
- Medir com a chave real (`--sondar`): facetas e filtros do plano, créditos, limite de taxa, ASNs do Brasil com contagem e tempo por ASN; ajustar `SHODAN_INTERVALO_S` e `SHODAN_ASNS_POR_EXECUCAO`.
- Fixtures sintéticas: o formato real da resposta (`facets`, `total`, `error`) só foi conferido na documentação; a sondagem confirma.
