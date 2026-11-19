<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Instalações do PeeringDB, vínculos, atributos das redes e portas externas

`instalacoes` · produto

Instalações (datacenters, pontos de interconexão) do Brasil e as dos PTTs externos cadastrados, com PTTs, carriers, campus, redes vinculadas, o indicador de cadastro vivo ou abandonado (inferido das datas de atualização), os atributos de peering autodeclarados das redes do Brasil e as portas (velocidade declarada) nos PTTs externos. Cadastro autodeclarado no PeeringDB; sem contatos.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.instalacoes.build` |
| Chaves de junção | `asn`, `facilidade` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [peeringdb_fac](../fontes/peeringdb_fac.md) — uso comercial: `nao_verificado`
- fonte [peeringdb_ixps](../fontes/peeringdb_ixps.md) — uso comercial: `restrito`
- produto [asn_docs](asn_docs.md)

## Saídas

- **Publicado:** `instalacoes/instalacoes.json.gz`, `instalacoes/vinculos.json.gz`, `instalacoes/atributos_rede.json.gz`, `instalacoes/portas_externas.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `instalacoes[id]` | dict | Instalação com organização, localização, datas, PTTs (com o código do Arandurapé quando conhecido), carriers, campus, número de redes coletadas e o indicador `cadastro`. | Autodeclarado. `cadastro` (recente até 12 meses, parado de 1 a 3 anos, antigo acima de 3 anos desde a última atualização do registro ou dos vínculos) é INFERÊNCIA; mede a manutenção do cadastro, não a operação da instalação nem da empresa. | instalacoes → instalacoes/instalacoes.json.gz#instalacoes |
| `carriers[id] / campus[id]` | dict | Carriers e campus referenciados pelas instalações. | — | instalacoes → instalacoes/instalacoes.json.gz#carriers; instalacoes → instalacoes/instalacoes.json.gz#campus |
| `cobertura / limiares_cadastro_dias` | dict | Instalações do Brasil, com coordenadas, PTT, carrier e campus; PTTs do IX.br e externos com instalação cadastrada; ASNs do Brasil com instalação; distribuição do indicador de cadastro e seus limiares. | Medidas de cobertura da fonte, não de qualidade. | instalacoes → instalacoes/instalacoes.json.gz#cobertura; instalacoes → instalacoes/instalacoes.json.gz#limiares_cadastro_dias |
| `por_instalacao / por_asn / redes` | dict | Redes por instalação e instalações por ASN (vínculo netfac com as datas de criação e atualização), e o nome e a marca de Brasil de cada rede citada. | Declaração no cadastro; não indica tráfego nem contrato. | instalacoes → instalacoes/vinculos.json.gz#por_instalacao; instalacoes → instalacoes/vinculos.json.gz#por_asn; instalacoes → instalacoes/vinculos.json.gz#redes |
| `asns[asn]` | dict | Atributos de peering declarados pela rede no PeeringDB (escopo, IPv6, multicast, unicast, nunca via route server, looking glass, route server, contagens) e o `cadastro` inferido das datas. | Autodeclarado; URLs não verificadas. | instalacoes → instalacoes/atributos_rede.json.gz#asns |
| `ixps[code] / por_asn` | dict | Por PTT externo, portas, membros, soma, mediana, maior velocidade e histograma por velocidade (Mbps); por ASN do Brasil, as velocidades das portas em cada PTT externo. | Velocidade declarada; a soma é capacidade contratada declarada, não tráfego. | instalacoes → instalacoes/portas_externas.json.gz#ixps; instalacoes → instalacoes/portas_externas.json.gz#por_asn |
| `fonte / limites / coletado_em` | dict | Fonte (PeeringDB, com citação e AUP), limitações e instante da coleta. | — | instalacoes → instalacoes/instalacoes.json.gz#fonte; instalacoes → instalacoes/instalacoes.json.gz#limites; instalacoes → instalacoes/instalacoes.json.gz#coletado_em; instalacoes → instalacoes/vinculos.json.gz#fonte; instalacoes → instalacoes/vinculos.json.gz#limites; instalacoes → instalacoes/vinculos.json.gz#coletado_em; instalacoes → instalacoes/atributos_rede.json.gz#fonte; instalacoes → instalacoes/atributos_rede.json.gz#limites; instalacoes → instalacoes/atributos_rede.json.gz#coletado_em; instalacoes → instalacoes/portas_externas.json.gz#fonte; instalacoes → instalacoes/portas_externas.json.gz#limites; instalacoes → instalacoes/portas_externas.json.gz#coletado_em |
| `snapshot_date / generated_at` | str | Data do snapshot e instante UTC de geração. | — | instalacoes → instalacoes/instalacoes.json.gz#snapshot_date; instalacoes → instalacoes/instalacoes.json.gz#generated_at; instalacoes → instalacoes/vinculos.json.gz#snapshot_date; instalacoes → instalacoes/vinculos.json.gz#generated_at; instalacoes → instalacoes/atributos_rede.json.gz#snapshot_date; instalacoes → instalacoes/atributos_rede.json.gz#generated_at; instalacoes → instalacoes/portas_externas.json.gz#snapshot_date; instalacoes → instalacoes/portas_externas.json.gz#generated_at |
