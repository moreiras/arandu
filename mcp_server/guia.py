# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Guia de escolha de tool do MCP: uma tabela *tarefa → tool* que gera as instruções do servidor e o bloco `tarefas` do `describe_schema`.

Fonte única: para mudar o que o modelo lê sobre "qual tool usar", edite `TAREFAS`. O T5 confere que toda tool citada existe
e que toda tool visível aparece aqui ou em `FORA_DO_GUIA`. Módulo sem dependências: o `contexto.py` o importa antes de criar o servidor.
"""
from __future__ import annotations
from core.site import com_identidade

# (tarefa, tools, dica)
TAREFAS: list[tuple[str, tuple[str, ...], str]] = [
    ("Filtrar, cruzar ou agregar conjuntos (a maioria das perguntas analíticas)", ("query",),
     'leia `describe_schema` ANTES: campos, enums e receitas. Proximidade: `near` ({"place"|"ixp"|"point":[lat,lon],"radius_km":N}).'),
    ("Uma entidade em uma chamada (perfil completo)", ("asn_detalhe", "ixp_detalhe", "operadora_detalhe", "municipio_detalhe", "uf_detalhe"),
     "`blocos` omite seções pesadas."),
    ("Achar um AS pelo nome ou buscar vários de uma vez", ("asn_lista", "asn_lote"), "`asn_lista(q=)`; `asn_lote` aceita até 100 ASNs e `fields`."),
    ("Snapshots disponíveis ou resumo de um", ("historico_snapshots",), ""),
    ("Evolução no tempo e o que mudou", ("historico_serie", "historico_mudancas"), "escopo asn:N, ixp:código, operadora:cnpj, uf:XX, brasil."),
    ("Dados de um IXP", ("ixp_participantes", "ixp_potencial", "ixp_proximos", "ixp_usuarios", "ixp_assinantes", "ixp_area_influencia", "ixp_externo", "ixp_lista"),
     "`ixp_proximos` = ASes a ≤ raio km do PTT (direct/origin/absent); `ixp_externo` = PeeringDB."),
    ("Um AS nos IXPs ou no mapa", ("asn_rede", "geo_localizar", "cdn_presenca"), ""),
    ("Alcance de um operador (usuários nos PTTs)", ("operadora_resolver", "operadora_alcance"),
     "resolva a marca antes (Claro e Vivo têm vários ASNs)."),
    ("Assinantes de banda larga (SICI, Anatel)", ("operadora_acessos", "operadora_ranking", "municipio_banda_larga", "historico_acessos",
                                                  "operadora_divergencia"),
     '`servico="movel"` (padrão `fixa`); sem CNPJ, `historico_acessos` é a série nacional.'),
    ("Outorgas Anatel (SCM, SMP, STFC, SeAC)", ("outorga_lista", "outorga_detalhe"),
     "ou `query` com `scms`, `smps`, `stfcs`, `seacs`."),
    ("Grupo econômico / sócios em comum", ("operadora_grupo", "query"),
     '`query(collection="socios")`: `mesmo_grupo` = quadro idêntico ou controle exclusivo; `relacionadas_parcial` = parte dos sócios (CPF mascarado: indício).'),
    ("Rejeições e communities nos route servers", ("asn_politica", "ixp_rejeicoes", "ixp_communities"), ""),
    ("Prefixos, roteamento e RPKI", ("rota_prefixos", "rota_prefixo", "rota_analise", "rota_estabilidade", "rota_rpki"),
     "`rota_prefixo(ip=)` acha o prefixo mais específico; `rota_analise` sem argumento dá o índice."),
    ("Interconexão de um AS (origina sem ser direto, route servers, rejeições)", ("asn_interconexao",), "só fatos observados; peering bilateral não é visível."),
    ("Grupo econômico com mercado, regulatório e técnico", ("grupo_perfil",), "grupo inferido; `blocos=[mercado,regulatorio,tecnico]`; sem ranking por multa."),
    ("Crédito público e sanções de uma operadora", ("operadora_financiamento", "operadora_sancoes"), ""),
    ("Contratos públicos de uma operadora (PNCP)", ("operadora_contratos",), ""),
    ("Bloqueios medidos (OONI)", ("asn_bloqueios",), ""),
    ("IPv6, tráfego e BGP (Cloudflare Radar)", ("asn_radar", "uf_radar"), ""),
    ("Serviços expostos (Shodan, só contagens)", ("asn_exposicao",), "`asn=` ou `uf=`; não prova vulnerabilidade."),
    ("Instalações e peering no PeeringDB", ("facility_lista", "facility_detalhe", "asn_peering", "ixp_portas"), ""),
    ("Infraestrutura física perto de um ponto", ("infra_proximos",), "cabos, enlaces, linhas e rodovias; devolve resumo, sem GeoJSON."),
    ("Mapas e blobs de visualização", ("viz",), "avançada (GeoJSON/Hilbert); para localizar em texto, `geo_localizar`."),
    ("Município por nome → coordenadas", ("municipio_resolver",), ""),
]

# tools visíveis que não são o destino de uma tarefa (ferramentas do próprio guia)
FORA_DO_GUIA = {"describe_schema", "asn_contatos", "operadora_contatos"}   # contatos: na regra 9 das instruções

# collection do `query` → tool que traz o detalhe de uma linha; None = nenhuma tool de detalhe (a linha da própria `query` é o dado)
DETALHE_DA_COLLECTION: dict[str, str | None] = {
    "asns": "asn_detalhe", "ixps": "ixp_detalhe", "external_ixps": "ixp_externo", "cdns": "cdn_presenca",
    "prefixes": "rota_prefixo", "global_prefixes": "rota_prefixo",
    "scms": "outorga_detalhe", "smps": "outorga_detalhe", "stfcs": "outorga_detalhe", "seacs": "outorga_detalhe",
    "operadoras": "operadora_detalhe", "operadoras_movel": "operadora_detalhe", "socios": "operadora_grupo",
    "acessos_municipio": "municipio_detalhe", "acessos_movel_municipio": "municipio_detalhe",
    "eventos": "historico_mudancas", "series_asn": "historico_serie",
    "indicadores_operadora": "operadora_detalhe", "sem_declaracao_sici": "operadora_detalhe", "multas_empresa": "operadora_detalhe",
    "reclamacoes_marca": "operadora_detalhe", "consumidor_marca": "operadora_detalhe",
    "municipios": "municipio_detalhe", "erbs_municipio": "municipio_detalhe", "fust_municipio": "municipio_detalhe",
    "cetic_indicadores": "uf_detalhe", "cetic_estimativas_uf": "uf_detalhe", "demanda_oferta": "uf_detalhe",
    "transito_uf": "uf_detalhe", "qualidade_uf": "uf_detalhe",
    "seguranca_asn": "asn_detalhe", "prontidao_agregado": "asn_detalhe", "prontidao_asn": "asn_detalhe",
    "organizacoes_asn": "asn_detalhe", "transito_asn": "asn_detalhe", "bloqueios_asn": "asn_bloqueios",
    "rs_sessoes": "ixp_detalhe", "rs_communities": "asn_politica", "rs_filtradas": "ixp_rejeicoes",
    "facilities": "facility_detalhe", "facilidades_rede": "facility_detalhe", "redes_peering": "asn_peering",
    "transferencias_ipv4": "rota_prefixo", "recuperacao_ipv4": "rota_prefixo", "eventos_bloco": "rota_prefixo",
    "espaco_ipv4": "rota_prefixo", "subasignacoes_ipv4": "rota_prefixo", "uso_por_terceiros_ipv4": "rota_prefixo",
    "faixas_espectro": None, "satelites_direitos": None,        # quadros de norma/direitos: sem tool própria (historico_snapshots só lista datas)
}

# Grupos das collections do `query` nas instruções. O T5 confere que toda collection do catálogo está em um grupo: a descrição do `query`
# citava 15 das 49 e o modelo respondia "não disponível" para o que existia.
GRUPOS_COLLECTIONS: list[tuple[str, list[tuple[str, str]]]] = [
    ("Redes", [("asns", "AS: nome, uf, usuários APNIC, ixps_sessao_rs, ixps_membro, ixps_origin, RPKI, IPv6, cnpj"), ("prefixes", "prefixos BR do Registro.br"),
               ("global_prefixes", "tabela global"), ("ixps", "PTTs do IX.br"), ("external_ixps", ""), ("cdns", ""),
               ("organizacoes_asn", "organização e ASNs irmãos"), ("transito_asn", "cone de clientes"),
               ("transito_uf", "mercado de trânsito por UF"), ("seguranca_asn", "ROV, DNSSEC, bogons"),
               ("prontidao_asn", "índice de prontidão em segurança de roteamento"), ("prontidao_agregado", ""),
               ("redes_peering", "PeeringDB"), ("facilities", "datacenters"), ("facilidades_rede", ""),
               ("rs_sessoes", "route servers do IX.br"), ("rs_communities", ""), ("rs_filtradas", ""), ("bloqueios_asn", "OONI")]),
    ("IPv4", [("espaco_ipv4", "blocos e anúncio"), ("uso_por_terceiros_ipv4", ""), ("transferencias_ipv4", ""), ("recuperacao_ipv4", ""),
              ("subasignacoes_ipv4", ""), ("eventos_bloco", "")]),
    ("Anatel e mercado", [("operadoras", "banda larga fixa por CNPJ"), ("operadoras_movel", ""),
                          ("acessos_municipio", "operadora × município, com share e HHI"), ("acessos_movel_municipio", ""),
                          ("indicadores_operadora", "variação, declínio"), ("sem_declaracao_sici", "outorga SCM sem declaração ao SICI no mês"),
                          ("scms", "outorgas"), ("smps", ""), ("stfcs", ""), ("seacs", ""), ("socios", "grupos econômicos"),
                          ("multas_empresa", ""), ("qualidade_uf", "RQUAL"), ("reclamacoes_marca", "Anatel"),
                          ("consumidor_marca", "Consumidor.gov.br"), ("faixas_espectro", ""), ("satelites_direitos", "")]),
    ("Território", [("municipios", "população, penetração, ptt_proximo, km_ptt"), ("erbs_municipio", "estações 2G a 5G"),
                    ("fust_municipio", ""), ("cetic_indicadores", "pesquisas TIC"), ("cetic_estimativas_uf", ""), ("demanda_oferta", "")]),
    ("Histórico", [("eventos", "mudanças entre snapshots"), ("series_asn", "")]),
]

_TEXTO = """\
Arandurape: dados da Internet brasileira (BGP do IX.br, tabela global, Registro.br, PeeringDB, RPKI, APNIC, Anatel) num snapshot datado e
imutável. Cite a data do snapshot. Nunca invente números: todo número da resposta vem de uma tool.

COMO ESCOLHER (pela pergunta):
1. UMA entidade com identificador → a tool de detalhe:
   AS → asn_detalhe(asn) · vários AS → asn_lote(asns, fields) · PTT do IX.br → ixp_detalhe(code) · operadora por CNPJ → operadora_detalhe(cnpj)
   município → municipio_detalhe(ibge) · UF → uf_detalhe(uf) · prefixo ou IP → rota_prefixo(prefix | ip) · outorgas de um CNPJ → outorga_detalhe
2. Só tenho o NOME → resolva antes: AS → asn_lista(q) · município → municipio_banda_larga(municipio, uf) devolve o IBGE · empresa → outorga_lista(q)
   devolve o CNPJ · marca de operadora → operadora_resolver(name) devolve os ASNs.
3. Lista filtrada, ranking, contagem, soma, agrupamento, cruzamento de condições → query(collection, filter, sort, group_by, aggregate).
   As collections estão abaixo; describe_schema(collection) dá os campos e enums de UMA collection.
4. Pergunta temática sobre um AS → asn_peering (PeeringDB), asn_politica (rejeições nos route servers), asn_interconexao (origina sem ser
   direto, sessões ausentes), asn_bloqueios (OONI), asn_radar (Cloudflare Radar), asn_exposicao (Shodan), asn_rede (AS_PATH),
   rota_estabilidade (BGP ruidoso; modo="carga": mais updates em semanas), geo_localizar (coordenadas).
5. Pergunta temática sobre um PTT → ixp_participantes (membros), ixp_proximos (ASes num raio; direct/origin/absent), ixp_potencial,
   ixp_usuarios (usuários APNIC alcançáveis), ixp_assinantes (assinantes SICI alcançáveis), ixp_rejeicoes, ixp_communities, ixp_lista,
   ixp_externo/ixp_portas (PTTs fora do IX.br), cdn_presenca (CDNs nos PTTs).
6. Operadora e mercado (Anatel) → operadora_acessos (assinantes de uma), operadora_ranking (maiores), historico_acessos (série mensal),
   municipio_banda_larga (quem atende a cidade), operadora_divergencia (APNIC × Anatel), operadora_grupo/grupo_perfil (grupo econômico),
   operadora_financiamento (BNDES), operadora_sancoes (CEIS/CNEP), operadora_contratos (PNCP), operadora_alcance (usuários via PTTs, com a
   lista de ASNs), outorga_lista/outorga_detalhe (SCM, SMP, STFC, SeAC).
7. Tempo → historico_snapshots (datas), historico_serie (série de uma entidade), historico_mudancas (eventos entre snapshots).
8. Lugar → municipio_resolver (coordenadas de cidade), infra_proximos (cabos e linhas perto de um ponto), facility_lista/facility_detalhe
   (datacenters do PeeringDB), rota_prefixos/rota_rpki/rota_analise (prefixos, RPKI, tabela global). Mapas para desenhar → viz.
9. Contatos (e-mail, telefone) → asn_contatos ou operadora_contatos, só com chave de MCP e na cota do site; um por chamada.

CÓDIGOS DOS PTTs DO IX.br (sempre minúsculos): {ptts}

COLLECTIONS DE query:
{collections}

SINTAXE DE query:
  filter: {{"field":"uf","op":"eq","value":"SC"}} ou {{"and":[…]}} / {{"or":[…]}} / {{"not":…}}. ops: eq ne gt gte lt lte in nin contains ncontains exists.
  Campo lista (ixps_sessao_rs, ixps_membro, ixps_origin, asns) usa contains/ncontains. Ex.: RS em Fortaleza, não em Salvador =
  {{"and":[{{"field":"ixps_sessao_rs","op":"contains","value":"ce"}},{{"field":"ixps_sessao_rs","op":"ncontains","value":"ba"}}]}}
  sort: [{{"field":"apnic_users","dir":"desc"}}] · select: ["asn","name"] · limit: N (a resposta traz "total": use-o para contar)
  group_by: ["uf"] + aggregate: [{{"fn":"count"}}, {{"fn":"sum","field":"apnic_users"}}]
  near: {{"ixp":"vix","radius_km":50}} | {{"place":"Mossoró","radius_km":100}} | {{"point":[lat,lon],"radius_km":N}}

REGRAS:
- Omita `date` para usar o snapshot mais recente; não invente datas.
- O SICI (Anatel) tem duas datas: a do snapshot e o mes_referencia; cite as duas. Com acessos_compartilhados=true não some ASes do mesmo CNPJ.
- Sessão com RS (ixps_sessao_rs) não é membro do cadastro (ixps_membro); originador = prefixo visto no PTT. Usuários APNIC: estimativa.
- Resultado vazio costuma ser valor errado (código de PTT, sigla, enum): confira antes de concluir que não existe.
- A resposta pode trazer `ajustes`: o que o servidor interpretou nos seus argumentos (ex.: "Fortaleza" → "ce"). Se mudar o sentido, diga.
- Sem chave de MCP: prévia (listas até 100, 1ª página, 2 snapshots recentes); o erro diz como obter a chave.
- Terminologia: arandurape://glossario; receitas: arandurape://recipes.
"""


def tarefas() -> list[dict]:
    return [{"tarefa": t, "tools": list(tools), **({"dica": d} if d else {})} for t, tools, d in TAREFAS]


def _linhas_collections() -> str:
    linhas = []
    for grupo, cols in GRUPOS_COLLECTIONS:
        itens = " · ".join(f"{c} ({d})" if d else c for c, d in cols)
        linhas.append(f"- {grupo}: {itens}")
    return "\n".join(linhas)


def _linha_ptts() -> str:
    from core.common import load_ixps
    return " ".join(f"{i['code']}={i['name']}" for i in load_ixps())


def instrucoes() -> str:
    """O texto enviado ao cliente no `initialize`: árvore de decisão, códigos de PTT (de config/ixps.yaml), collections e sintaxe do `query`.
    Medido contra o texto anterior (lista tarefa → tool) com modelos locais."""
    # nome do site e esquema de URI do .env; o texto acima usa o nome do software ("Arandurapé") como marcador
    return com_identidade(_TEXTO.format(ptts=_linha_ptts(), collections=_linhas_collections()))
