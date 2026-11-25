# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Resources e prompt do MCP: a semântica do projeto, para a LLM não inventar terminologia."""
from __future__ import annotations

import json

from api.query import OPS_GUIDE, RECIPES
from core.common import app_version
from core.site import SITE, com_identidade
from mcp_server.contexto import _resolve, _store, mcp

# ---------------------------------------------------------------------------
# Resources — semântica do projeto (evitam a LLM inventar terminologia)
# ---------------------------------------------------------------------------

@mcp.resource(SITE.uri("overview"))
def overview() -> str:
    """O que é o Arandurape e quais são as fontes de dados."""
    d = _store.latest() or "(nenhum)"
    return f"""# {SITE.nome}

O {SITE.nome} mapeia a Internet brasileira a partir de dados de roteamento. Coleta
semanalmente as tabelas BGP dos looking glasses Telnet do IX.br e a tabela
global (NIC.br/Registro.br e RouteViews), cruza com a base de ASNs e prefixos do
Registro.br, e enriquece com PeeringDB, RPKI e estimativas de usuários do APNIC.

Versão do sistema: **{app_version()}** · Snapshot mais recente disponível: **{d}**.

## Fontes de dados
- **IX.br LGs (40 PTTs)** — rotas BGP observadas em cada ponto de troca.
- **Registro.br** — prefixos IPv6/IPv4 atribuídos a ASNs brasileiros (autoritativo).
- **LACNIC delegated** — ASNs alocados ao Brasil.
- **Tabela global** — tabela de roteamento BGP completa (full table).
- **PeeringDB** — IXPs globais, listas de membros, metadados de peering.
- **RPKI (Routinator)** — VRPs (ROAs validados) e objetos ASPA.
- **APNIC Labs** — estimativas de usuários finais por AS.
- **Anatel (dados abertos)** — outorgas SCM (Serviço de Comunicação Multimídia),
  cruzadas com ASNs por CNPJ e geolocalizadas via Nominatim.

Todos os dados são imutáveis após escrita e servidos a partir de um snapshot
datado. Cite sempre a data do snapshot ao responder.
"""


@mcp.resource(SITE.uri("glossario"))
def glossario() -> str:
    """Conceitos-chave para interpretar os dados corretamente."""
    return com_identidade("""# Glossário Arandurape

- **Sessão em route server × membro × originador** — três conjuntos de ASNs de um PTT do
  IX.br, de tamanhos muito diferentes. *Sessão com o route server* (`ixps_sessao_rs` na
  collection `asns`, `ixps_direct` no documento do AS e `ixps_direct_count`): o AS aparece
  como primeiro hop do AS_PATH no looking glass; não é peering bilateral. *Membro do
  cadastro* (`ixps_membro`; `ixps_direct` da collection `asns` é o nome antigo dele):
  consta na lista oficial de participantes, com ou sem sessão. *Originador*: seus
  prefixos são visíveis no PTT, possivelmente via um upstream.

- **ASN brasileiro** — `is_br`: os ASNs que a LACNIC delegou ao Brasil. A lista do
  Registro.br (`registro_br_asns`) tem alguns ASNs a mais e é a base da análise de rotas.

- **Prefixos RIR vs. global** — `rir_prefixes` vêm do Registro.br (fonte
  autoritativa de alocação); `global_prefixes` são observados na tabela global e
  podem incluir prefixos não declarados ou omitir prefixos declarados mas não
  anunciados.

- **Espaço /24 e /48** — o espaço de endereçamento é medido em unidades /24 (IPv4)
  e /48 (IPv6) para permitir comparação de cobertura.

- **Cobertura (%)** — fração do espaço/prefixos BR visível em determinado escopo
  (um IXP, a tabela global) frente ao total.

- **Snapshot** — conjunto de dados coletados e analisados em uma data específica.
  Imutável. Sem `date`, as ferramentas usam o mais recente.

- **RPKI / TA** — validação de origem (valid/invalid/not_found) por âncora de
  confiança (LACNIC, RIPE, ARIN, APNIC, AFRINIC).

- **ASPA** — objeto RPKI que declara os upstreams autorizados de um AS. Cada ASPA
  tem um *customer* (o AS que publicou) e uma lista de *providers* (upstreams
  autorizados). O campo `aspa_providers` mostra os ASPAs publicados pelo próprio AS;
  `aspa_customers` mostra outros ASes que declararam o AS em questão como provider.

- **Relações inferidas (`relacoes`)** — provedores, clientes, pares e irmãos de um AS, inferidos (ARC v1) da
  rampa dos route servers do IX.br, de caminhos de coletores públicos, do ASPA e do CAIDA. Cada item traz `p`
  (probabilidade, não calibrada na v1) e `nivel`: *declarado* (o próprio AS o listou no ASPA), *confirmado*
  (p ≥ 0,95 e duas fontes independentes), *provavel* (p ≥ 0,70 e uma fonte) ou *possivel*. `single_homed` e
  `multihomed` só são afirmados com visibilidade mínima (`null` = indeterminado). Não é contrato nem acordo
  comercial. `upstreams_*`/`downstreams_*` são apenas **vizinhos observados** no AS_PATH (deprecado; não
  distinguem provedor de par ou do ponto de observação).

- **Geolocalização** — ASNs BR são geolocalizados pelo endereço da organização
  (CNPJ → BrasilAPI → Nominatim); membros internacionais, via PeeringDB.

- **CAP** — Provedor de Aplicações de Conteúdo (Content/Application Provider),
  tratado junto com CDNs na matriz de presença.

- **Usuários estimados** — estimativa do APNIC Labs por AS. Por IXP, é a estimativa de
  usuários alcançáveis (IPv4), ponderada pelo espaço visível no PTT, e não é aditiva: o
  mesmo usuário conta em cada PTT onde o seu AS aparece (a soma dos 40 PTTs passa de
  três vezes o total do país). Por UF, vale a UF da sede do AS, não a de quem usa.

- **SCM (Serviço de Comunicação Multimídia)** — serviço de telecomunicação
  (código 045 Anatel) que engloba provedores de acesso à internet (ISPs),
  operadoras de dados corporativos e demais prestadoras de SCM. Os dados
  vêm dos dados abertos da Anatel (dadosabertos.anatel.gov.br) e são cruzados
  com ASNs por CNPJ. Use `list_scms` ou `query(collection="scms")` para filtrar.

- **Outorga SCM** — autorização regulatória (não é licença) concedida pela Anatel
  para prestar o SCM. Situação: ATI (ativa), EXT (extinta), SUS (suspensa).
  Ter outorga NÃO significa estar operando: cerca de metade dos CNPJs com outorga SCM não
  declara nenhum acesso fixo ao SICI. Os totais de declarantes dependem do universo (CNPJs
  no SICI fixo, CNPJs com outorga SCM que declararam acesso fixo, ou fixo ou móvel).

- **SICI (Sistema de Coleta de Informações)** — declaração mensal obrigatória das
  prestadoras à Anatel: quantos acessos em serviço, em que município, com que
  velocidade contratada, tecnologia, meio e tipo de cliente. É dado DECLARADO pelo
  operador, com prazo regulatório (dia 1 a 15 do mês seguinte), não uma estimativa.

- **Mês de referência** — os acessos do SICI têm data PRÓPRIA (`mes_referencia`),
  diferente da data do snapshot. Toda resposta que use acessos deve citar AS DUAS
  datas.

- **Acesso** — um contrato de banda larga fixa em serviço, não uma pessoa. A razão
  entre usuários estimados (APNIC) e acessos (Anatel) tem mediana 3,97 — é o número
  de pessoas por contrato.

- **acessos_compartilhados** — quando um CNPJ tem mais de um ASN, o total declarado
  é atribuído INTEGRALMENTE a cada ASN (dividir inventaria número). NUNCA some ASes
  do mesmo CNPJ: 73 CNPJs nessa condição concentram 48,6% dos acessos do país.
  Agregue por CNPJ ou por grupo econômico.

- **Capacidade contratada** — soma de (velocidade × acessos), em Mbps. NÃO é
  capacidade de trânsito, de backhaul nem de rede instalada. Links de backbone
  declarados como "acesso" distorcem a média, por isso use
  `velocidade_mediana_mbps` junto da média, e as variantes `_internet` (que
  excluem LINHA_DEDICADA, M2M e OUTROS).

- **B2C / B2B** — no SICI, `Tipo de Pessoa`: Pessoa Física (89,3% dos acessos) e
  Pessoa Jurídica (10,7%). Refinado por `Tipo de Produto` (INTERNET × LINHA_DEDICADA).

- **Grupo econômico (SICI)** — campo com apenas 24 valores. Consolida os grandes
  multi-CNPJ (OI, TELEFONICA, TELECOM AMERICAS, ALGAR...), mas "OUTROS" cobre 99,7%
  dos CNPJs. Não serve como agrupador geral — para a cauda longa, o identificador é
  o CNPJ, e o nome comercial é o campo `empresa`.

- **HHI** — índice de concentração do município (soma dos quadrados dos shares):
  10000 é monopólio; faixas do projeto: abaixo de 1500, 1500 a 2499, 2500 ou mais
  (mesmos limiares do Guia H do CADE, 2016; o HHI municipal é cálculo do projeto). Cuidado: operadoras de satélite
  declaram acessos em quase todos os 5.570 municípios, então a CONTAGEM de
  operadores superestima a competição local — use share e HHI.
""")


@mcp.resource(SITE.uri("summary"))
def summary_resource() -> str:
    """summary.json do snapshot mais recente (números agregados)."""
    d = _resolve(None)
    return json.dumps(_store.summary(d) or {}, ensure_ascii=False, indent=2)


@mcp.resource(SITE.uri("schema"))
def schema_resource() -> str:
    """Catálogo de campos/ops das collections consultáveis pela tool `query`."""
    return json.dumps(_store.query_schema(), ensure_ascii=False, indent=2)


@mcp.resource(SITE.uri("recipes"))
def recipes_resource() -> str:
    """Receitas: perguntas comuns → sequência exata de ferramentas (com args prontos)."""
    return json.dumps(
        {"operator_guide": OPS_GUIDE, "recipes": RECIPES},
        ensure_ascii=False, indent=2,
    )


# ---------------------------------------------------------------------------
# Resources por entidade: o mesmo documento da tool de detalhe, endereçável por URI
# ---------------------------------------------------------------------------

def _json(dados) -> str:
    return json.dumps(dados, ensure_ascii=False, indent=2, default=str)


@mcp.resource(SITE.uri("changes/latest"), mime_type="application/json")
def recurso_changes_latest() -> str:
    """Eventos confirmados do snapshot com histórico mais recente (o que mudou). Diferenças observadas, sem causa; provedor é inferência."""
    from mcp_server.tools_historico import _historico
    repo = _historico()
    datas = repo.datas()
    if not datas:
        return _json({"snapshot_date": None, "items": [], "nota": "Ainda não há snapshot com histórico."})
    from api.services import historico as h
    return _json({"snapshot_date": datas[-1], **h.mudancas(repo, datas[-1], datas[-1], limit=100)})


@mcp.resource(SITE.uri("tendencias"), mime_type="application/json")
def recurso_tendencias() -> str:
    """Tendências nacionais (soma das UFs) nos snapshots com histórico: ASNs BR, usuários estimados, prefixos e RPKI. Poucos pontos no início."""
    from api.services import historico as h
    from mcp_server.tools_historico import _historico
    repo = _historico()
    out = {}
    for m in ("n_asns", "users", "p4", "p6", "rpki_valid", "rpki_invalid", "rpki_not_found"):
        try:
            out[m] = h.tendencia(repo, "brasil", m)
        except h.HistoricoErro:
            out[m] = None
    return _json({"escopo": "brasil", "snapshots_com_historico": len(repo.datas()), "tendencias": out})


@mcp.resource(SITE.uri("seguranca/manrs"), mime_type="application/json")
def recurso_manrs() -> str:
    """Participação agregada de ASNs e usuários do Brasil no programa de operadores do MANRS (total, por porte e por UF; nenhum recorte suprimido: os pequenos ou dominados por um ASN trazem `avisos`, `n_asns_com_dado` e `peso_top1`) e a comparação agregada de prontidão. Atribuição: "Provided by the MANRS with support from the Global Cyber Alliance"."""
    d = _resolve(None)
    return _json(_store.manrs_doc(d) or {"snapshot_date": d, "disponivel": False})


@mcp.resource(SITE.uri("asn/{n}"), mime_type="application/json")
def recurso_asn(n: str) -> str:
    """Documento de um AS (o de `asn_detalhe`, sem contatos). Ex.: arandurape://asn/28573."""
    from mcp_server.tools_entidades import get_asn
    return _json(get_asn(int(n)))


@mcp.resource(SITE.uri("ixp/{code}"), mime_type="application/json")
def recurso_ixp(code: str) -> str:
    """Documento de um PTT do IX.br (o de `ixp_detalhe`). Ex.: arandurape://ixp/sp."""
    from mcp_server.tools_entidades import get_ixp
    return _json(get_ixp(code.lower()))


@mcp.resource(SITE.uri("operadora/{cnpj}"), mime_type="application/json")
def recurso_operadora(cnpj: str) -> str:
    """Perfil de uma operadora por CNPJ (o de `operadora_detalhe`: outorgas, SICI, ASNs, rede e grupo)."""
    from mcp_server.tools_mercado import get_operator
    return _json(get_operator(cnpj))


@mcp.resource(SITE.uri("uf/{uf}"), mime_type="application/json")
def recurso_uf(uf: str) -> str:
    """Perfil de uma UF (o de `uf_detalhe`). Ex.: arandurape://uf/es."""
    from mcp_server.tools_mercado import get_uf
    return _json(get_uf(uf))


@mcp.resource(SITE.uri("municipio/{ibge}"), mime_type="application/json")
def recurso_municipio(ibge: str) -> str:
    """Perfil de um município por código IBGE de 7 dígitos (o de `municipio_detalhe`)."""
    from mcp_server.tools_mercado import get_municipio
    return _json(get_municipio(ibge))


# ---------------------------------------------------------------------------
# Prompt — priming da LLM
# ---------------------------------------------------------------------------

@mcp.prompt(name=SITE.mcp_esquema)                     # nome do prompt = esquema do site
def arandurape(pergunta: str = "") -> str:
    """Template de priming para perguntas sobre a Internet brasileira."""
    return f"""Você responde sobre a Internet brasileira usando os dados do {SITE.nome}.

Para perguntas analíticas (filtros, cruzamentos, agregações, proximidade geográfica),
prefira a tool `query` — leia antes `describe_schema` (campos, enums e receitas prontas)
ou {SITE.uri("recipes")}. Para análises específicas use `ixp_nearby` (potencial por raio) e
`operator_reach` (alcance de um operador); `resolve_operator`/`resolve_place` traduzem
marcas e lugares. Use get_asn/get_ixp para drill-down de uma entidade.

Consulte {SITE.uri("overview")} e {SITE.uri("glossario")} para a terminologia (direto vs.
originador, RIR vs. global, etc.). Cite números com a data do snapshot e não invente.

Pergunta: {pergunta}
"""


# ---------------------------------------------------------------------------
# Prompts temáticos: roteiros de análise que encadeiam as tools certas
# ---------------------------------------------------------------------------

@mcp.prompt()
def diagnostico_de_as(asn: int) -> str:
    """Diagnóstico de um AS: quem é, onde está, como se conecta, se tem RPKI e quantos assinantes declara."""
    return f"""Faça o diagnóstico do AS{asn} com os dados do {SITE.nome}, citando a data do snapshot em cada seção.

1. `asn_detalhe(asn={asn})`: nome, organização, prefixos, presença em IXPs, RPKI/ASPA e relações inferidas (são inferências, diga "provável").
2. `asn_rede(asn={asn}, visao="ixp_peers")` e `visao="caminhos"`: como aparece em cada PTT.
3. `rota_estabilidade(asn={asn})`: estabilidade BGP recente.
4. Se houver CNPJ: `operadora_detalhe(cnpj=…, blocos=["sici","rede"])` e `operadora_grupo(cnpj=…)`.
5. Feche com 3 pontos fortes, 3 lacunas e a evidência de cada um. Não invente números.
"""


@mcp.prompt()
def potencial_de_ptt(code: str, raio_km: int = 80) -> str:
    """Potencial de crescimento de um PTT: ASes e assinantes próximos que ainda não participam."""
    return f"""Avalie o potencial do PTT '{code}' do IX.br com os dados do {SITE.nome}.

1. `ixp_detalhe(code="{code}")` e `ixp_usuarios(code="{code}")`: porte atual e usuários estimados.
2. `ixp_proximos(code="{code}", radius_km={raio_km})`: ASes a ≤ {raio_km} km; os de status `absent` são o potencial.
3. `ixp_assinantes(code="{code}")`: assinantes já alcançáveis pelo PTT.
4. `operadora_resolver` / `operadora_acessos` para os 5 maiores `absent`: quantos assinantes declaram.
Entregue um ranking dos ASes a convidar, com a razão de cada um. Cite a data do snapshot e o mês de referência do SICI.
"""


@mcp.prompt()
def mercado_de_municipio(ibge: str) -> str:
    """Mercado de banda larga de um município: quem atende, concentração e fibra."""
    return f"""Descreva o mercado de acesso do município {ibge} com os dados do {SITE.nome}.

1. `municipio_detalhe(ibge="{ibge}")`: acessos fixos e móveis, % de fibra e PTTs mais próximos.
2. `municipio_banda_larga(ibge="{ibge}")`: operadoras, share e HHI. Operadoras de satélite inflam a contagem: julgue pelo share e pelo HHI.
3. Para as 3 maiores: `operadora_grupo` (pertencem ao mesmo grupo?) e `operadora_acessos`.
Cite as duas datas (snapshot e mês de referência do SICI) e nunca some acessos de ASes do mesmo CNPJ.
"""


@mcp.prompt()
def grupo_economico_oculto(cnpj: str) -> str:
    """Grupo econômico de uma operadora a partir dos sócios em comum (QSA da Receita Federal)."""
    return f"""Investigue o grupo econômico da empresa {cnpj} com os dados do {SITE.nome}.

1. `operadora_grupo(cnpj="{cnpj}")`: grupo, CNPJs e relações diretas.
2. `query(collection="socios", filter=…)`: separe `mesmo_grupo` (quadro idêntico ou controle exclusivo) de `relacionadas_parcial` (parte dos sócios).
3. `outorga_detalhe` e `operadora_acessos` para cada CNPJ do grupo: o que o grupo opera e quantos assinantes declara.
CPF de pessoa física vem parcialmente mascarado: trate como indício, não como certeza, e não exponha dados pessoais.
"""
