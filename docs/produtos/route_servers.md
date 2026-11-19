<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Route servers do IX.br, sessões × cadastro

`route_servers` · produto

Por PTT do IX.br: estado dos route servers, sessões BGP dos membros (up e down), membros cadastrados com e sem sessão e membros com todas as sessões down há 7 dias ou mais. Por ASN: as sessões em cada PTT, com família, estado, há quantos dias, último erro, rotas e uso do limite de importação. Fatos medidos no route server na data da coleta, sem veredito.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.route_servers.build` |
| Chaves de junção | `ixp`, `asn` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [ixbr_alice](../fontes/ixbr_alice.md) — uso comercial: `nao_verificado`
- fonte [ixbr_api](../fontes/ixbr_api.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `route_servers/ixps.json.gz`, `route_servers/asns.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ixps[ixp].resumo` | dict | Route servers (total, consultados, com cache de rotas pronto e com vizinhos atuais), membros cadastrados com e sem sessão, sessões sem cadastro, sessões up e down, membros down e perto do limite. | Medição no route server na data da coleta; "cadastrado sem sessão" pode ser membro com peering bilateral. | route_servers → route_servers/ixps.json.gz#ixps |
| `ixps[ixp].membros[]` | list | Por ASN do PTT (cadastrado ou com sessão), contagem de sessões up e down, maior tempo de queda e maior uso do limite de importação. | membro down = todas as sessões down há 7 dias ou mais e nenhuma sem frescor confirmado (rs_incerto: cache de vizinhos do Alice com mais de 24 h, sem cached_at ou consulta que falhou); perto do limite = rotas recebidas em 80% ou mais do import_limit. | route_servers → route_servers/ixps.json.gz#ixps |
| `asns[asn].ixps[ixp].lista` | list | Cada sessão do ASN no PTT (route server, família, estado, dias no estado, último erro, rotas e limite). | Dado do route server; o motivo da queda é o que o Alice reporta, sem causa atribuída. | route_servers → route_servers/asns.json.gz#asns |
| `snapshot_date` | str | Data do snapshot em que o artefato foi gerado. | — | route_servers → route_servers/ixps.json.gz#snapshot_date; route_servers → route_servers/asns.json.gz#snapshot_date |
| `generated_at` | str | Instante UTC em que o artefato foi gerado. | — | route_servers → route_servers/ixps.json.gz#generated_at; route_servers → route_servers/asns.json.gz#generated_at |
| `coletado_em` | str | Instante UTC da coleta no Alice-LG: a data do dado (o snapshot só o guarda). | — | route_servers → route_servers/ixps.json.gz#coletado_em; route_servers → route_servers/asns.json.gz#coletado_em |
| `fonte` | str | Fonte das sessões (Alice-LG do IX.br). | — | route_servers → route_servers/ixps.json.gz#fonte; route_servers → route_servers/asns.json.gz#fonte |
| `versao_alice` | str | Versão do Alice-LG que respondeu. | — | route_servers → route_servers/ixps.json.gz#versao_alice; route_servers → route_servers/asns.json.gz#versao_alice |
| `dias_down` | str | Dias de queda a partir dos quais um membro com todas as sessões down conta como membro down (7). | — | route_servers → route_servers/ixps.json.gz#dias_down; route_servers → route_servers/asns.json.gz#dias_down |
| `uso_limite` | str | Fração do limite de importação (rotas recebidas ÷ import_limit) a partir da qual a sessão está perto do limite (0,8). | — | route_servers → route_servers/ixps.json.gz#uso_limite; route_servers → route_servers/asns.json.gz#uso_limite |
| `idade_max_vizinhos_h` | int | Idade máxima, em horas, do cache de vizinhos do Alice (cached_at) para as sessões de um route server valerem como estado atual (24). | — | route_servers → route_servers/ixps.json.gz#idade_max_vizinhos_h; route_servers → route_servers/asns.json.gz#idade_max_vizinhos_h |
