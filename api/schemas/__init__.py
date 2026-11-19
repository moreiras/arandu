# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Modelos Pydantic para documentação OpenAPI e validação de resposta."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = Field("ok", description="Sempre 'ok' se a API está no ar")
    version: Optional[str] = Field(
        None,
        description="Versão do sistema (arquivo VERSION; ex.: 1.1.1)",
        examples=["1.0.3"],
    )
    latest_snapshot: Optional[str] = Field(
        None,
        description="Data do snapshot mais recente disponível (YYYY-MM-DD)",
        examples=["2026-06-06"],
    )
    snapshots_available: int = Field(
        description="Número total de snapshots armazenados",
        examples=[3],
    )


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

class SnapshotListResponse(BaseModel):
    count: int = Field(description="Total de snapshots disponíveis", examples=[3])
    latest: Optional[str] = Field(
        None,
        description="Data do snapshot mais recente (YYYY-MM-DD)",
        examples=["2026-06-06"],
    )
    snapshots: list[str] = Field(
        description="Lista de datas disponíveis, ordem cronológica",
        examples=[["2026-06-04", "2026-06-05", "2026-06-06"]],
    )


class GlobalTableStats(BaseModel):
    model_config = {"extra": "allow"}
    v4_prefixes: int
    v4_space_24: int
    v4_br_coverage_pct: Optional[float] = Field(
        None,
        description="% do espaço IPv4 alocado ao BR (Registro.br) visível na tabela global",
    )
    v4_br_pct_of_ft: Optional[float] = Field(
        None,
        description="% do espaço total IPv4 da FT que é alocado ao BR (rir_br_visible / global_all)",
    )
    v6_prefixes: int
    v6_space_48: float
    v6_br_coverage_pct: Optional[float] = Field(
        None,
        description="% do espaço IPv6 alocado ao BR (Registro.br) visível na tabela global",
    )
    v6_br_pct_of_ft: Optional[float] = Field(
        None,
        description="% do espaço total IPv6 da FT que é alocado ao BR (rir_br_visible / global_all)",
    )
    total_asns: int
    br_asns_in_ft: Optional[int] = Field(
        None,
        description="ASNs BR com ao menos um prefixo visível na tabela global",
    )


class IXPAggregateStats(BaseModel):
    asn_direct_union_count: int = Field(description="ASNs em peering direto em qualquer IXP (união v4∪v6, sem repetição)")
    asn_origin_union_count: int = Field(description="ASNs originando prefixos em qualquer IXP (união v4∪v6, sem repetição)")
    br_asns_origin_union_count: int = Field(description="ASNs BR originando prefixos em qualquer IXP (união v4∪v6, exato)")
    v4_prefixes: int
    v4_space_24: int
    v4_coverage_pct: float = Field(description="% do espaço IPv4 global coberto pelo agregado dos IXPs")
    v4_br_coverage_pct: float = Field(default=0.0, description="% do espaço IPv4 declarado pelo Registro.br coberto pelo agregado")
    v6_prefixes: int
    v6_space_48: float
    v6_coverage_pct: float = Field(description="% do espaço IPv6 global coberto pelo agregado dos IXPs")
    v6_br_coverage_pct: float = Field(default=0.0, description="% do espaço IPv6 declarado pelo Registro.br coberto pelo agregado")


class SnapshotSummary(BaseModel):
    model_config = {"extra": "allow"}

    snapshot_date: str = Field(examples=["2026-06-06"])
    generated_at: str = Field(examples=["2026-06-06T13:20:43+00:00"])
    pipeline_version: str = Field(examples=["1.0.0"])
    ixps_configured: int = Field(description="IXPs configurados para coleta", examples=[39])
    ixps_ok: int = Field(description="IXPs com coleta completa (v4 + v6)", examples=[12])
    ixps_partial: int = Field(description="IXPs com coleta parcial (apenas v4 ou v6)", examples=[8])
    ixps_missing: int = Field(description="IXPs sem dados coletados", examples=[19])
    total_asns_br: int = Field(description="ASNs brasileiros segundo o Registro.br", examples=[9104])
    total_asns_global: int = Field(description="Total de ASNs observados (BR + globais)", examples=[86885])
    br_asns_with_ipv6: int = Field(description="ASNs BR com algum IPv6: alocado no Registro.br, visível na tabela global ou visto num PTT do IX.br (não é o mesmo que anunciar; para anúncio veja br_asns_ft_v6)", examples=[1823])
    br_ipv6_pct: float = Field(description="% dos ASNs BR alocados com algum IPv6 (alocado, na tabela global ou num PTT); não mede anúncio", examples=[20.02])
    registro_br_prefixes_v4: int = Field(description="Prefixos IPv4 declarados no Registro.br", examples=[18432])
    registro_br_prefixes_v6: int = Field(description="Prefixos IPv6 declarados no Registro.br", examples=[4201])
    m3_prefixes_v4: int = Field(description="O mesmo que registro_br_prefixes_v4 (nome mantido por compatibilidade)", examples=[18432])
    m3_prefixes_v6: int = Field(description="O mesmo que registro_br_prefixes_v6 (nome mantido por compatibilidade)", examples=[4201])
    global_table: Optional[GlobalTableStats] = None
    ixp_aggregate: Optional[IXPAggregateStats] = None


class SnapshotManifest(BaseModel):
    pipeline_version: str = Field(examples=["1.0.0"])
    generated_at: str = Field(examples=["2026-06-06T13:20:43+00:00"])
    ixps_configured: list[str] = Field(description="Códigos dos IXPs configurados")
    ixps_collected: list[str] = Field(description="IXPs com coleta bem-sucedida")
    ixps_failed: list[str] = Field(description="IXPs com falha ou sem dados")
    coleta: Optional[str] = Field(default=None, description="completa | parcial | pendente (sanidade de coleta); null em snapshots antigos")
    coleta_ok: Optional[bool] = Field(default=None, description="false quando algum check de sanidade falhou")
    checks: Optional[dict] = Field(default=None, description="resultado de cada verificação (limite, valor, anterior)")
    layout_version: Optional[int] = Field(default=None, description="versão do layout dos arquivos publicados")
    sources: Optional[list[dict]] = Field(default=None, description="de que versão de cada fonte o snapshot é feito: id, as_of, coletado_em, hash, origem (armazem | legado | ausente) e frescor (ok | atrasado | sem_limite | desconhecido | ausente)")


class SnapshotDetailResponse(BaseModel):
    date: str = Field(examples=["2026-06-06"])
    summary: Optional[SnapshotSummary]
    manifest: Optional[SnapshotManifest]


# ---------------------------------------------------------------------------
# IXPs
# ---------------------------------------------------------------------------

class IXPIndexAfi(BaseModel):
    total_routes: int = Field(description="Total de rotas recebidas neste AFI", examples=[892341])
    unique_prefixes: int = Field(description="Prefixos únicos observados", examples=[62418])
    ixp_space: int = Field(description="Espaço de endereços coberto (número de endereços)", examples=[1073741824])
    asn_direct_count: int = Field(description="ASNs em peering direto no IXP", examples=[487])
    asn_origin_count: int = Field(description="ASNs originadores de prefixos visíveis", examples=[23104])
    asn_stub_count: int = Field(description="ASNs diretos com exatamente 1 originador (stubs)", examples=[312])
    br_prefix_coverage_pct: float = Field(
        description="% do espaço IPv4 BR declarado no Registro.br visível neste IXP",
        examples=[72.34],
    )
    ixp_vs_fulltable_space_pct: float = Field(
        description="% do espaço global da full table coberto pelos prefixos deste IXP",
        examples=[18.91],
    )


class IXPIndexEntry(BaseModel):
    code: str = Field(description="Código do IXP (slug do IX.br)", examples=["sp"])
    name: str = Field(description="Nome da cidade", examples=["São Paulo"])
    uf: str = Field(description="Unidade Federativa", examples=["SP"])
    status: str = Field(
        description="Status da coleta: **ok** (v6+v4), **partial** (só v6 ou v4), **missing** (sem dados)",
        examples=["ok"],
    )
    asn_direct_union_count: Optional[int] = Field(
        None, description="ASNs em peering direto (união v6 ∪ v4)", examples=[487]
    )
    asn_origin_union_count: Optional[int] = Field(
        None, description="ASNs originadores de prefixos — aproximação de max(v6, v4)", examples=[23104]
    )
    br_asns_origin_union_count: Optional[int] = Field(
        None, description="ASNs brasileiros originadores (união v6 ∪ v4, exato)", examples=[8531]
    )
    ixbr_members_count: Optional[int] = Field(
        None, description="Membros registrados neste IXP no dashboard IX.br (inclui quem não usa RS)", examples=[312]
    )
    v4: Any = Field(description="Métricas IPv4. `{status: 'missing'}` se sem dados.")
    v6: Any = Field(description="Métricas IPv6. `{status: 'missing'}` se sem dados.")


class IXPListResponse(BaseModel):
    snapshot_date: str = Field(examples=["2026-06-06"])
    count: int = Field(description="Total de IXPs retornados", examples=[39])
    ixps: list[IXPIndexEntry]


class IXPAfiFull(BaseModel):
    total_routes: int = Field(examples=[892341])
    unique_prefixes: int = Field(examples=[62418])
    ixp_space: int = Field(description="Espaço de endereços do IXP (nº de endereços)", examples=[1073741824])
    asn_direct_count: int = Field(examples=[487])
    asn_origin_count: int = Field(examples=[23104])
    asn_stub_count: int = Field(description="Peers diretos com exatamente 1 ASN originador", examples=[312])
    asn_direct: list[int] = Field(description="Lista de ASNs em peering direto")
    asn_stub: list[int] = Field(description="Subconjunto de asn_direct identificados como stubs")
    br_asns_direct: list[int] = Field(description="ASNs BR em peering direto")
    br_asns_direct_count: int = Field(examples=[203])
    br_asns_direct_pct: float = Field(description="% de ASNs BR entre os diretos", examples=[41.68])
    br_asns_origin: list[int] = Field(description="ASNs BR originadores de prefixos visíveis aqui")
    br_asns_origin_count: int = Field(examples=[8741])
    br_asns_origin_pct: float = Field(examples=[96.02])
    br_prefix_covered_space: int = Field(
        description="Espaço IPv4 BR coberto por este IXP (nº de endereços)"
    )
    br_prefix_declared_space: int = Field(
        description="Espaço IPv4 BR total declarado no Registro.br"
    )
    br_prefix_coverage_pct: float = Field(examples=[72.34])
    ft_space: int = Field(description="Espaço total da full table global (nº de endereços)")
    ixp_vs_fulltable_space_pct: float = Field(examples=[18.91])


class IXPDocumentResponse(BaseModel):
    ixp: str = Field(description="Código do IXP", examples=["sp"])
    name: str = Field(examples=["São Paulo"])
    uf: str = Field(examples=["SP"])
    snapshot_date: str = Field(examples=["2026-06-06"])
    generated_at: str = Field(examples=["2026-06-06T13:20:43+00:00"])
    v4: Any = Field(description="Métricas IPv4 completas. `{status: 'missing'}` se sem dados.")
    v6: Any = Field(description="Métricas IPv6 completas. `{status: 'missing'}` se sem dados.")
    asn_members: Optional[list[int]] = Field(None, description="ASNs membros registrados no IX.br (ixbr_members.json).")
    ixbr_members_count: Optional[int] = Field(None, description="Total de membros registrados.")


# ---------------------------------------------------------------------------
# ASNs
# ---------------------------------------------------------------------------

class ASNIndexEntry(BaseModel):
    asn: int = Field(description="Número do AS", examples=[1916])
    name: str = Field(description="Nome do AS (fonte: Registro.br)", examples=["Rede Nacional de Ensino e Pesquisa"])
    is_br: bool = Field(description="True se o AS está registrado no Registro.br", examples=[True])
    has_ipv6: bool = Field(description="True se o AS tem prefixos IPv6 observados", examples=[True])
    rir_prefixes_v4_count: int = Field(
        description="Prefixos IPv4 atribuídos ao AS pelo RIR/Registro.br",
        examples=[38],
    )
    rir_prefixes_v6_count: int = Field(
        description="Prefixos IPv6 atribuídos ao AS pelo RIR/Registro.br",
        examples=[1],
    )
    global_prefixes_v4_count: int = Field(
        description="Prefixos IPv4 observados na tabela de roteamento global",
        examples=[55],
    )
    global_prefixes_v6_count: int = Field(
        description="Prefixos IPv6 observados na tabela de roteamento global",
        examples=[26],
    )
    ixps_direct_count: int = Field(description="Número de IXPs onde este AS faz peering direto", examples=[12])
    ixps_origin_count: int = Field(description="Número de IXPs onde prefixos deste AS são visíveis", examples=[38])
    ixps_origin_v4_count: Optional[int] = Field(None, description="Número de IXPs onde este AS origina prefixos IPv4")
    ixps_origin_v6_count: Optional[int] = Field(None, description="Número de IXPs onde este AS origina prefixos IPv6")
    apnic_users: Optional[int] = Field(None, description="Estimativa APNIC de usuários totais (janela 60 dias)")
    apnic_v6_users: Optional[int] = Field(None, description="Estimativa APNIC de usuários IPv6 (janela 60 dias)")
    pct_v6: Optional[float] = Field(None, description="% de usuários IPv6 = apnic_v6_users / apnic_users × 100")
    has_rpki: Optional[bool] = Field(None, description="True se o AS possui pelo menos um ROA no RPKI")
    has_aspa: Optional[bool] = Field(None, description="True se o AS possui pelo menos um objeto ASPA publicado no RPKI")
    pdb_registered: Optional[bool] = Field(None, description="True se o AS tem cadastro no PeeringDB")
    has_scm: Optional[bool] = Field(None, description="True se o AS possui outorga SCM na Anatel (cruzamento por CNPJ)")
    has_smp: Optional[bool] = Field(None, description="True se o AS possui outorga SMP na Anatel (cruzamento por CNPJ)")
    has_stfc: Optional[bool] = Field(None, description="True se o AS possui outorga STFC na Anatel (cruzamento por CNPJ)")
    has_seac: Optional[bool] = Field(None, description="True se o AS possui outorga SeAC na Anatel (cruzamento por CNPJ)")
    cnpj: Optional[str] = Field(None, description="CNPJ da organização do AS (Registro.br), 14 dígitos sem formatação")
    external_ixps_count: Optional[int] = Field(None, description="Número de IXPs externos (PeeringDB) onde o AS é membro")
    uf: Optional[str] = Field(None, description="UF da organização do AS (geolocalização do CNPJ); nulo fora do Brasil ou sem geo")
    epppd: Optional[float] = Field(None, description="Só com `include=bgp_stability`: eventos de update BGP por prefixo por dia (total)")
    epppd_v4: Optional[float] = Field(None, description="Só com `include=bgp_stability`: o mesmo, IPv4")
    epppd_v6: Optional[float] = Field(None, description="Só com `include=bgp_stability`: o mesmo, IPv6")
    prontidao_indice: Optional[float] = Field(None, description="Só com `include=prontidao` e a lista nominal liberada: índice de prontidão em segurança de roteamento (0 a 100; soma ponderada de medições de terceiros, não veredito)")
    prontidao_classe: Optional[str] = Field(None, description="Só com `include=prontidao` e a lista nominal liberada: pronto, em_progresso, atrasado ou sem_dados")


class PaginatedASNsResponse(BaseModel):
    snapshot_date: str = Field(examples=["2026-06-06"])
    total: int = Field(description="Total de ASNs após filtros", examples=[9104])
    page: int = Field(examples=[1])
    limit: int = Field(examples=[100])
    pages: int = Field(description="Total de páginas", examples=[92])
    items: list[ASNIndexEntry]


class IXPPresenceAfi(BaseModel):
    direct: bool = Field(description="True se o AS faz peering direto neste IXP")
    origin: bool = Field(description="True se prefixos do AS são visíveis neste IXP")
    prefixes: list[str] = Field(
        description="Prefixos deste AS observados neste IXP",
        examples=[["200.130.0.0/16", "200.131.0.0/16"]],
    )


class IXPPresence(BaseModel):
    v4: IXPPresenceAfi
    v6: IXPPresenceAfi


class Alert(BaseModel):
    id: str = Field(description="Identificador estável do tipo de alerta", examples=["sem_rpki"])
    category: str = Field(description="roteamento | rpki | v4v6 | presenca | geo", examples=["rpki"])
    severity: str = Field(description="critico | aviso | info", examples=["aviso"])
    title: str = Field(examples=["Sem RPKI (ROA)"])
    detail: str = Field(description="Explicação legível do ponto de atenção")
    refs: dict = Field(default_factory=dict, description="Dados de apoio (prefixos, IXPs, ASNs, distâncias)")


class ASNDocumentResponse(BaseModel):
    asn: int = Field(examples=[1916])
    snapshot_date: str = Field(examples=["2026-06-06"])
    generated_at: str = Field(examples=["2026-06-06T13:20:43+00:00"])
    is_br: bool = Field(examples=[True])
    name: str = Field(examples=["Rede Nacional de Ensino e Pesquisa"])
    cnpj: Optional[str] = Field(None, description="CNPJ do responsável (ASNs BR)", examples=["03.508.097/0001-36"])
    rir_prefixes_v4: list[str] = Field(
        description="Prefixos IPv4 **atribuídos** ao AS pelo RIR/Registro.br",
        examples=[["200.129.0.0/16", "200.130.0.0/16"]],
    )
    rir_prefixes_v6: list[str] = Field(
        description="Prefixos IPv6 atribuídos ao AS pelo RIR/Registro.br",
        examples=[["2001:12f0::/32"]],
    )
    rir_prefixes_v4_count: int = Field(examples=[38])
    rir_prefixes_v6_count: int = Field(examples=[1])
    global_prefixes_v4: list[str] = Field(
        description="Prefixos IPv4 observados na **tabela de roteamento global** (full table)",
        examples=[["132.255.96.0/22", "150.161.0.0/16"]],
    )
    global_prefixes_v6: list[str] = Field(
        description="Prefixos IPv6 observados na tabela global",
        examples=[["2001:12f0::/36"]],
    )
    global_prefixes_v4_count: int = Field(examples=[55])
    global_prefixes_v6_count: int = Field(examples=[26])
    has_ipv6: bool = Field(examples=[True])
    ixps_direct: list[str] = Field(
        description="Códigos dos IXPs onde este AS faz peering direto",
        examples=[["sp", "rj", "bsb"]],
    )
    ixps_origin: list[str] = Field(
        description="Códigos dos IXPs onde prefixos deste AS são visíveis (via upstream)",
        examples=[["sp", "rj", "bsb", "curitiba"]],
    )
    ixp_presence: dict[str, IXPPresence] = Field(
        description="Detalhes por IXP: presença direta/origem e lista de prefixos observados"
    )
    upstreams: list[int] = Field(
        description="[Deprecado: use `relacoes`] Vizinhos à esquerda no AS_PATH dos LGs dos IXPs (adjacência, não relação comercial; união IPv6+IPv4, mantido para compatibilidade)",
        examples=[[2, 3356]],
    )
    downstreams: list[int] = Field(
        description="[Deprecado: use `relacoes`] Vizinhos à direita no AS_PATH dos LGs dos IXPs (adjacência, não relação comercial; união IPv6+IPv4, mantido para compatibilidade)",
        examples=[[64512, 64513]],
    )
    upstreams_v4: list[int] = Field(
        default_factory=list,
        description="Upstreams inferidos dos IXPs, somente IPv4",
    )
    upstreams_v6: list[int] = Field(
        default_factory=list,
        description="Upstreams inferidos dos IXPs, somente IPv6",
    )
    downstreams_v4: list[int] = Field(
        default_factory=list,
        description="Downstreams inferidos dos IXPs, somente IPv4",
    )
    downstreams_v6: list[int] = Field(
        default_factory=list,
        description="Downstreams inferidos dos IXPs, somente IPv6",
    )
    upstreams_global_v4: list[int] = Field(
        default_factory=list,
        description="Upstreams inferidos do RouteViews (múltiplos vantage points), IPv4",
    )
    upstreams_global_v6: list[int] = Field(
        default_factory=list,
        description="Upstreams inferidos do RouteViews (múltiplos vantage points), IPv6",
    )
    downstreams_global_v4: list[int] = Field(
        default_factory=list,
        description="Downstreams inferidos do RouteViews, IPv4",
    )
    downstreams_global_v6: list[int] = Field(
        default_factory=list,
        description="Downstreams inferidos do RouteViews, IPv6",
    )
    is_multihomed_v4: bool = Field(
        default=False,
        description="[Deprecado: use `relacoes.multihomed`] True se há mais de um vizinho à esquerda na tabela global IPv4 (adjacência; não distingue provedor de par)",
    )
    is_multihomed_v6: bool = Field(
        default=False,
        description="[Deprecado: use `relacoes.multihomed`] True se há mais de um vizinho à esquerda na tabela global IPv6 (adjacência; não distingue provedor de par)",
    )
    single_upstream_v4: Optional[int] = Field(
        None,
        description="[Deprecado: use `relacoes.single_homed`] ASN do único vizinho à esquerda na tabela global IPv4; None caso contrário (adjacência, não prova provedor)",
    )
    single_upstream_v6: Optional[int] = Field(
        None,
        description="[Deprecado: use `relacoes.single_homed`] ASN do único vizinho à esquerda na tabela global IPv6; None caso contrário (adjacência, não prova provedor)",
    )
    relacoes: Optional[dict] = Field(
        None,
        description=(
            "Relações inferidas do AS (ARC v1): `provedores`, `clientes`, `pares`, `irmaos` e `sem_classificacao`, cada "
            "item com {asn, p, nivel, afi}; `n_provedores` (nível confirmado ou superior), `visibilidade` e `single_homed`/`multihomed` "
            "por família (null = indeterminado por falta de visibilidade). É inferência com probabilidade e nível, não contrato. "
            "Ausente em snapshots anteriores ao ARC; `upstreams_*` e `downstreams_*` seguem como adjacência observada (alias deprecado)."
        ),
    )
    ixp_member_codes: Optional[list[str]] = Field(
        None,
        description="IXPs onde este AS é membro registrado no IX.br (independente de anúncio de rotas)",
    )
    path_node_meta: Optional[dict[str, dict]] = Field(
        None,
        description="Metadados dos ASNs no AS_PATH intermediário: name, is_br e ixp_stats por IXP relevante",
    )
    roa_list: Optional[list[dict]] = Field(
        None,
        description="ROAs que autorizam este AS a anunciar prefixos: [{prefix, maxLength, ta}]",
    )
    rpki_validation: Optional[dict[str, str]] = Field(
        None,
        description="Status RPKI de cada prefixo anunciado pelo AS: {prefix: 'valid'|'invalid'|'not_found'}",
    )
    aspa_providers: Optional[list[dict]] = Field(
        None,
        description="Objetos ASPA publicados por este AS como customer: [{providers: [int, ...], tal: str}]",
    )
    aspa_customers: Optional[list[dict]] = Field(
        None,
        description="Objetos ASPA de outros ASes que listam este AS como provider: [{customer: int, tal: str}]",
    )
    pdb_registered: Optional[bool] = Field(None, description="True se o AS tem cadastro no PeeringDB")
    external_ixps: Optional[list[str]] = Field(None, description="Códigos de IXPs externos onde este AS aparece no PeeringDB")
    pdb: Optional[dict] = Field(None, description="Metadados da rede no PeeringDB")
    # APNIC Labs — estimativas de usuários (janela de 60 dias)
    apnic_users: Optional[int] = Field(
        None,
        description="Estimativa de usuários totais do AS (APNIC Labs, janela 60 dias)",
        examples=[20771435],
    )
    apnic_users_pct_cc: Optional[float] = Field(
        None,
        description="Porcentagem da população brasileira de internet atribuída a este AS",
        examples=[12.66],
    )
    apnic_v6_users: Optional[int] = Field(
        None,
        description="Estimativa de usuários IPv6 do AS (APNIC Labs)",
        examples=[16116420],
    )
    apnic_v6_pct_as: Optional[float] = Field(
        None,
        description="Porcentagem dos usuários do AS que utilizam IPv6",
        examples=[82.08],
    )
    announced_ipv4_addresses: Optional[int] = Field(
        None,
        description="Total de endereços IPv4 anunciados pelo AS na full table (soma dos /32 equivalentes dos prefixos observados)",
        examples=[10338304],
    )
    users_per_ip: Optional[float] = Field(
        None,
        description="Usuários estimados por endereço IPv4 alocado — proxy de intensidade de CGNAT",
        examples=[2.01],
    )
    announced_ipv6_48s: Optional[int] = Field(
        None,
        description="Total de /48 equivalentes IPv6 anunciados pelo AS na full table",
        examples=[131072],
    )
    users_per_v6_48: Optional[float] = Field(
        None,
        description="Usuários IPv6 estimados por /48 anunciado",
        examples=[123.5],
    )
    alerts: Optional[list[Alert]] = Field(
        None,
        description="Pontos de atenção: divergências e práticas possivelmente mal feitas, cruzando RIR, full table, RPKI, PeeringDB, IX.br e geolocalização",
    )
    scm: Optional[list[dict]] = Field(
        None,
        description="Outorgas SCM (Serviço de Comunicação Multimídia) da Anatel vinculadas ao CNPJ deste AS",
    )
    has_scm: Optional[bool] = Field(
        None, description="True se o CNPJ deste AS possui outorga SCM na Anatel",
    )
    smp: Optional[list[dict]] = Field(
        None,
        description="Outorgas SMP (Serviço Móvel Pessoal) da Anatel vinculadas ao CNPJ deste AS",
    )
    has_smp: Optional[bool] = Field(
        None, description="True se o CNPJ deste AS possui outorga SMP na Anatel",
    )
    stfc: Optional[list[dict]] = Field(
        None,
        description="Outorgas STFC (Serviço Telefônico Fixo Comutado) da Anatel vinculadas ao CNPJ deste AS",
    )
    has_stfc: Optional[bool] = Field(
        None, description="True se o CNPJ deste AS possui outorga STFC na Anatel",
    )
    seac: Optional[list[dict]] = Field(
        None,
        description="Outorgas SeAC (Serviço de Acesso Condicionado) da Anatel vinculadas ao CNPJ deste AS",
    )
    has_seac: Optional[bool] = Field(
        None, description="True se o CNPJ deste AS possui outorga SeAC na Anatel",
    )
    same_cnpj_asns: Optional[list[dict]] = Field(
        None, description="Outros ASNs do Registro.br com o mesmo CNPJ: [{asn, name}]",
    )
    alt_names: Optional[list[dict]] = Field(
        None, description="Nomes alternativos com origem: [{name, source}]",
    )
    contacts_available: Optional[dict] = Field(
        None,
        description="Contagens de contatos disponíveis por origem (sem valores): "
                    "{peeringdb, anatel, receita, total}. Os valores ficam em "
                    "GET /asns/{asn}/contacts (protegido por login).",
    )
