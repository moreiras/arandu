# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Descrições das tools vistas pelo modelo (`tools/list`), curtas e no formato "use para / não use para".

Medidas contra os docstrings com modelos locais: o texto longo dos docstrings (870 a 1.500
caracteres nas 20 maiores) custava ~20 mil tokens por turno e o modelo escolhia pior. Os docstrings seguem como documentação para quem
mantém o código; o que vai ao cliente é este mapa, aplicado em `app.py`. `date` é sempre opcional e não é repetido. Tool nova: escreva
a descrição aqui (o T5 confere que toda tool visível tem uma).
"""
from __future__ import annotations

DESCRICOES: dict[str, str] = {
    'asn_bloqueios': (
        'Medições do OONI numa rede (WhatsApp, Telegram, Signal, Tor…): medições e anomalias declaradas pela sonda. Não é '
        'censura confirmada. Vários AS: query(collection="bloqueios_asn"). Cite OONI, CC BY-NC-SA 4.0. Args: asn.'
    ),
    'asn_detalhe': (
        'Perfil completo de UM AS: nome, CNPJ, UF, PTTs diretos e como originador, prefixos (Registro.br × tabela global), '
        'RPKI, usuários APNIC, IXPs externos, relações inferidas. Não use para vários AS (asn_lote) nem para achar o número '
        'pelo nome (asn_lista). Sem contatos (asn_contatos). Args: asn.'
    ),
    'asn_exposicao': (
        'Serviços expostos que o Shodan viu (Telnet, RDP, gestão de roteador, bancos de dados) num AS ou, somados, numa UF. '
        'Só contagens; não prova vulnerabilidade. Args: asn OU uf.'
    ),
    'asn_interconexao': (
        'Onde UM AS origina prefixos sem ser membro direto, sessões ausentes ou de uma só família nos route servers e rotas '
        'rejeitadas. Fatos observados; peering bilateral não é visível. Args: asn.'
    ),
    'asn_lista': (
        'Acha o número de AS pelo nome (ou confirma um número). Não use para filtrar ou ordenar por métrica: use '
        'query(collection="asns"). Args: q (trecho do nome), br_only, sort_by, limit.'
    ),
    'asn_lote': (
        'Vários AS numa chamada (até 100), com `fields` para trazer só alguns campos (ex.: '
        '["name","apnic_users","ixps_direct"]). Use para comparar ou somar AS conhecidos. Args: asns, fields.'
    ),
    'asn_peering': (
        'O que o AS declara no PeeringDB: política, IPv6, multicast, "nunca via route server", looking glass, portas em PTTs '
        'externos. Autodeclarado. Datacenters do AS: facility_lista(asn=). Args: asn.'
    ),
    'asn_politica': (
        'Rotas de UM AS rejeitadas pelos route servers do IX.br (por motivo) e as communities de exportação que ele usa, por '
        'PTT. Só quem foi coletado. Para um PTT inteiro use ixp_rejeicoes. Args: asn, ixp.'
    ),
    'asn_radar': (
        'Cloudflare Radar de UM AS: % IPv6 das requisições, tráfego (só AS de topo) e papel em eventos BGP. Por UF: uf_radar.'
        ' CC BY-NC 4.0. Args: asn.'
    ),
    'asn_rede': (
        'Como um AS aparece nos PTTs: visao="caminhos" = cadeias AS_PATH onde ele só origina; visao="ixp_peers" = '
        'estatísticas onde é membro direto. Args: asn, visao.'
    ),
    'cdn_presenca': (
        'Em quais PTTs (IX.br e externos) cada CDN/CAP (Google, Cloudflare, Netflix…) está presente, com seus ASNs. Sem '
        'argumentos.'
    ),
    'describe_schema': (
        'Campos, tipos, enums e exemplos de UMA collection de `query`, com as receitas dela e a sintaxe. Chame com collection'
        ' (ex.: "municipios") antes de filtrar campos que você não conhece. Sem collection devolve o índice das collections. '
        'Args: collection.'
    ),
    'facility_detalhe': (
        'UMA instalação do PeeringDB (id de facility_lista): organização, PTTs, carriers, redes vinculadas. Args: id.'
    ),
    'facility_lista': (
        'Datacenters e pontos de interconexão do PeeringDB no Brasil: por uf, nome (q), PTT, estado do cadastro (recente, '
        'parado, antigo), ou os de uma rede (asn). Args: uf, q, ptt, asn, cadastro, limit.'
    ),
    'geo_localizar': (
        'Coordenadas de um AS (endereço da organização) e/ou dos PIX de um PTT. Args: asn, ixp.'
    ),
    'grupo_perfil': (
        'Perfil de um grupo econômico (grupo_id grp_… ou ind_…): composição e blocos mercado, regulatorio, tecnico, relacoes.'
        ' Args: grupo_id, blocos.'
    ),
    'historico_acessos': (
        'Série mensal de acessos de uma operadora (cnpj ou asn) com variação de 1, 6 e 12 meses; sem cnpj nem asn, a série '
        'nacional. Args: cnpj, asn, meses, servico.'
    ),
    'historico_mudancas': (
        'Eventos entre snapshots: AS novo ou sumido, entrada ou saída de PTT, mudança de origem de prefixo, RPKI inválido, '
        'outorga nova. tipo (ex.: "asn_novo,ixp_entrada,mudanca_origem"), uf, asn, resumo=true só as contagens. Diferença '
        'observada, sem causa. Args: de, ate, tipo, uf, asn, estado, limit, resumo.'
    ),
    'historico_serie': (
        'Série de uma entidade ao longo dos snapshots: escopo "asn:28126", "ixp:sp", "operadora:<cnpj>", "uf:BA" ou "brasil";'
        ' metrica opcional (users, p4, n_roa, n_asns…) devolve a tendência. Args: escopo, metrica, metrics, de, ate.'
    ),
    'historico_snapshots': (
        'Sem date: as datas dos snapshots disponíveis e o mais recente. Com date: o resumo daquele snapshot (totais, '
        'cobertura IPv6/IPv4, status das fontes).'
    ),
    'infra_proximos': (
        'Infraestrutura física a até raio_km de um ponto (lat, lon): cabos submarinos, pontos de aterrissagem, enlaces, '
        'linhas de transmissão; rodovias só se pedidas em camadas. Coordenadas: municipio_resolver ou geo_localizar. Args: '
        'lat, lon, raio_km, camadas, limit.'
    ),
    'ixp_assinantes': (
        'Assinantes de banda larga fixa (SICI, Anatel) alcançáveis via os peers de um PTT, diretos e dos clientes deles. '
        'Args: code, limit.'
    ),
    'ixp_communities': (
        'Communities dos route servers do IX.br: significado e quem usa. community exata (ex.: "65535:666") ou busca q '
        '(trecho, rótulo ou ASN-alvo de "não exportar para"). Args: community, q, ixp, classe.'
    ),
    'ixp_detalhe': (
        'Métricas de UM PTT do IX.br (code): ASes diretos e originadores, rotas e prefixos por família, cobertura de prefixos'
        ' BR. Lista de membros: ixp_participantes. Args: code.'
    ),
    'ixp_externo': (
        'PTTs fora do IX.br (PeeringDB): sem code, a lista (filtre country="BR"); com code (ex.: "decix-sp", "equinix-sp"), '
        'os membros com nome e velocidade, com br_only. Args: code, country, br_only.'
    ),
    'ixp_lista': (
        'Os 40 PTTs do IX.br com métricas-resumo; filtra por uf ou status de coleta (ok, partial, missing). Args: uf, status.'
    ),
    'ixp_participantes': (
        'Quem participa de UM PTT: visao="membros" = listas de ASNs diretos e originadores; visao="peers" = estatística por '
        'peer (afi v4|v6). Args: code, visao, afi.'
    ),
    'ixp_portas': (
        'Portas de um PTT externo no PeeringDB: quantidade, velocidades, soma de capacidade declarada. Não vale para o IX.br.'
        ' Args: code.'
    ),
    'ixp_potencial': (
        'Indicadores de potencial de um PTT: ASes a ≤ 80 km que não participam, prefixos e usuários do potencial. Raio livre:'
        ' ixp_proximos. Args: code.'
    ),
    'ixp_proximos': (
        'ASes com prefixos a até radius_km de um PTT, com status direct (membro), origin (só originador) ou absent (não '
        'participa), e o resumo por status em "summary". Args: code, radius_km, limit.'
    ),
    'ixp_rejeicoes': (
        'Rotas rejeitadas pelo route server de UM PTT, por motivo e por AS. Para um AS: asn_politica. Args: code, motivo, '
        'limit.'
    ),
    'ixp_usuarios': (
        'Usuários finais (estimativa APNIC) alcançáveis pelos prefixos vistos num PTT; sem code, todos os PTTs. Args: code.'
    ),
    'municipio_banda_larga': (
        'Quem oferece banda larga num município (ibge ou municipio + uf): operadoras com acessos, share, ASNs e HHI. '
        'servico="movel" para móvel. Args: ibge, municipio, uf, limit, servico.'
    ),
    'municipio_detalhe': (
        'Perfil de UM município pelo código IBGE (7 dígitos): banda larga fixa e móvel, % de fibra, PTTs mais próximos com '
        'distância. Só o nome: municipio_banda_larga(municipio=, uf=) devolve o ibge. Args: ibge, blocos.'
    ),
    'municipio_resolver': (
        'Coordenadas (lat, lon) de um município pelo nome, para near.point ou infra_proximos. Args: place.'
    ),
    'operadora_acessos': (
        'Assinantes declarados à Anatel por UMA operadora (cnpj ou asn): total, PF × PJ, velocidade, municípios, tecnologia, '
        'mes_referencia. servico="movel" para telefonia móvel. Args: cnpj, asn, servico.'
    ),
    'operadora_alcance': (
        'Usuários finais alcançados por um conjunto de ASNs de uma operadora através dos PTTs (ptt_count, reach_users_dedup).'
        ' Precisa da lista completa de ASNs: pegue em operadora_resolver(name) ou em operadora_ranking/operadora_acessos '
        '(campo asns). Args: asns.'
    ),
    'operadora_contratos': (
        'Contratos públicos (resultados no PNCP) de uma operadora (raiz do CNPJ): valor homologado, órgãos, ano. '
        '`resultado="sem_leitura"` = ainda não lida (não quer dizer sem contratos). Args: cnpj.'
    ),
    'operadora_detalhe': (
        'Perfil de UMA operadora pelo CNPJ (14 dígitos): outorgas SCM/SMP/STFC/SeAC, assinantes SICI, ASNs, rede. Sem CNPJ: '
        'ache com outorga_lista(q=nome). Args: cnpj, blocos.'
    ),
    'operadora_divergencia': (
        'Divergência entre usuários APNIC e acessos declarados à Anatel, por AS (apnic_alto, apnic_baixo…). Hipótese a '
        'investigar, não erro. Args: asn, classificacao, limit.'
    ),
    'operadora_financiamento': (
        'Financiamentos do BNDES de uma operadora (raiz do CNPJ): contratado e desembolsado em R$ nominais. '
        '`resultado="sem_registro"` = não consta neste recorte. Args: cnpj.'
    ),
    'operadora_grupo': (
        'Grupo econômico de uma empresa (cnpj) ou de um grupo_id: CNPJs membros (cnpjs_total), assinantes somados, empresas '
        'ligadas por sócios (só a contagem de sócios em comum). Inferido do quadro societário; S.A.: `grupo_inferivel`=false. '
        'Args: cnpj, grupo_id, limit.'
    ),
    'operadora_ranking': (
        'Ranking das operadoras por acessos (ou capacidade, municípios): nacional, por UF da sede ou dentro de um município '
        '(ibge); com_asn=false para quem não tem AS brasileiro vinculado (CNPJ, raiz ou marca). servico="movel" para móvel. '
        'Cada item traz cnpj, empresa, asns (mesmo CNPJ) e asn_vinculo (cnpj, raiz, marca, estrangeiro, nenhum). Args: '
        'uf, ibge, com_asn, min_acessos, metric, limit, servico.'
    ),
    'operadora_resolver': (
        'Marca ou operadora → ASNs (Vivo, Claro, Brisanet, Google…), pela tabela curada de marcas, pelo SICI, pelas CDNs e, '
        'por último, pelo nome do AS. A resposta diz o `metodo` e os nomes dos ASNs: confira. Use os ASNs em '
        'operadora_alcance. Args: name.'
    ),
    'operadora_sancoes': (
        'Sanções no CEIS e no CNEP (CGU) de uma operadora (raiz do CNPJ). `resultado="sem_registro"` = não consta neste '
        'recorte (não prova que não exista). Descreva como "consta em", nunca como acusação. Args: cnpj.'
    ),
    'outorga_detalhe': (
        'As outorgas de UM CNPJ em cada serviço (SCM, SMP, STFC, SeAC). Perfil completo: operadora_detalhe. Args: cnpj, '
        'servico.'
    ),
    'outorga_lista': (
        'Empresas com outorga da Anatel (SCM, SMP, STFC, SeAC), uma linha por CNPJ, com serviços, sede, asns e acessos. '
        'Filtra por servico (todos=true exige todos), uf, q (nome ou CNPJ), com_asn, ativo, porte. "total" = quantas. Args: '
        'servico, todos, uf, municipio, q, com_asn, ativo, porte, min_acessos, limit.'
    ),
    'query': (
        'Lista, filtra, ordena, conta, soma e agrupa linhas de uma collection; use para rankings, contagens e cruzamentos de '
        'condições. Não use para o perfil de UMA entidade (use asn_detalhe, ixp_detalhe…). Collections e sintaxe nas '
        'instruções; campos em describe_schema(collection). Ex.: {"collection":"asns","filter":{"and":[{"field":"ixps_direct"'
        ',"op":"contains","value":"ce"},{"field":"uf","op":"eq","value":"CE"}]}, '
        '"sort":[{"field":"apnic_users","dir":"desc"}],"limit":10}. Contagem: use "total" da resposta. Agregação: group_by + '
        'aggregate [{"fn":"count"},{"fn":"sum","field":"apnic_users"}].'
    ),
    'rota_analise': (
        'Análise da tabela global para prefixos brasileiros: tamanhos de prefixo, more specifics, agregação, MOAS (moas e moas_resumo; nulos em snapshot sem a coleta de todas as origens), AS_PATH. '
        'Sem secao devolve o índice das seções; depois peça a seção. Args: secao, limit, offset.'
    ),
    'rota_estabilidade': (
        'Estabilidade BGP (eventos por prefixo por dia). Com asn: o AS. Sem asn: modo="resumo" = ranking dos mais ruidosos; '
        '"visao_geral"; "historico"; "carga" = ASes com mais updates em weeks semanas, por família. Args: asn, modo, weeks, limit.'
    ),
    'rota_prefixo': (
        'UM prefixo (qualquer grafia CIDR): detentor no Registro.br, origem observada (tabela global ou route servers), RPKI do '
        'anúncio e UF. Com ip (sem máscara) acha a alocação mais específica que contém o endereço. Args: prefix OU ip.'
    ),
    'rota_prefixos': (
        'Lista prefixos BR do Registro.br com filtro simples (origin_asn, uf, ip_version 4|6). Contagem ou agrupamento: '
        'query(collection="prefixes"). Args: origin_asn, uf, ip_version, limit.'
    ),
    'rota_rpki': (
        'RPKI: sem prefix, a adoção de ROA/ASPA nos AS brasileiros; com prefix, a validade ROA da origem observada (ou do asn '
        'informado), com motivo e ROAs que cobrem. Args: prefix, asn.'
    ),
    'uf_detalhe': (
        'Perfil de uma UF (totais, PTTs, municípios com distância ao PTT, maiores operadoras); sem uf, uma linha por UF (bom '
        'para comparar UFs). Args: uf, blocos.'
    ),
    'uf_radar': (
        'Cloudflare Radar agregado por UF (mediana e média ponderada de IPv6, eventos BGP), derivado dos AS da UF. Args: uf.'
    ),
    'viz': (
        '[Avançada] Dados para desenhar mapas (GeoJSON ou curva de Hilbert); por padrão resumo + amostra, full=true o blob '
        'inteiro. kind: asn_geo (asn, layer=fulltable_v4|fulltable_v6|ixp_v4|ixp_v6) · ixp_geo (code, '
        'layer=asns_members|asns_direct|asns_origin|prefixes_v4|prefixes_v6) · hilbert_v4 · hilbert_v6 · hilbert_v4_detail '
        '(slash8) · ixp_hilbert_v4/ixp_hilbert_v6 (code) · map_asns/map_prefixes (uf) · map_pix. Para coordenadas em texto '
        'use geo_localizar.'
    ),
    'asn_contatos': (
        'Contatos de UM AS (PeeringDB, RDAP do Registro.br, Receita, Anatel), com origem e função. Só com chave de MCP; gasta 1 da '
        'cota de contatos da conta, a mesma do site. Um AS por chamada, nunca em lote. Args: asn.'
    ),
    'operadora_contatos': (
        'Contatos de UMA operadora por CNPJ (PeeringDB dos ASNs, Receita, Anatel). Só com chave de MCP; custa o número de ASNs do '
        'CNPJ na cota de contatos da conta. Args: cnpj, servico=fixa|movel.'
    ),
}
