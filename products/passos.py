# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Passos do build do snapshot, um por produto (`cnpj_geo`.3 e `cnpj_geo`.4).

Cada produto tem um **passo**
(`Passo`: id, produto do catálogo, função `executar(ctx)`) e este módulo guarda a ORDEM única (`ORDEM`), usada pelo `snapshot_builder.run`
(caminho num só processo) e conferida por teste contra o grafo do catálogo (uma etapa do arandu por passo, `catalog/steps/<passo>.yaml`).
Cada passo lê o que o anterior deixou em `published/` e em `build/<data>/intermediarios/`, então roda sozinho:

    python -m products.passos --passo asn_indice --date 2026-10-24

Os passos pressupõem o fluxo de fragmentos (`ARANDU_COMPOSE`, padrão ligado): o SICI vem antes do SCM.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from core.common import configure_logging, data_dir, load_ixps, load_peeringdb_ixps_config, today_str
from core.outorgas import SERVICOS
from products.asn_docs import build as asn_docs
from products.cdns.build import publicar_cdn_presence
from products.grupos_societarios.build import publicar_grupos_societarios
from products.ixp_docs import build as ixp_docs
from products.mapas_infraestrutura.build import publicar_infra_maps
from products.mapas_prefixos import build as mapas_prefixos
from products.outorgas.build import publicar_outorgas
from products.penetracao.build import publicar_penetracao
from products.cetic.build import publicar_cetic
from products.demanda_oferta.build import publicar_demanda_oferta
from products.erbs.build import publicar_erbs
from products.regulatorio.build import publicar_regulatorio
from products.cadastro_empresas.build import publicar_cadastro_empresas
from products.financiamento_sancoes.build import publicar_financiamento_sancoes
from products.qualidade.build import publicar_qualidade
from products.consumidor.build import publicar_consumidor
from products.ipv4.build import publicar_ipv4
from products.ipv4_uso.build import publicar_ipv4_uso
from products.ipv4_subasig.build import publicar_ipv4_subasig
from products.route_servers.build import publicar_route_servers
from products.rs_policy.build import publicar_rs_policy
from products.decix_rs.build import publicar_decix_rs
from products.as2org.build import publicar_abuso_agregado, publicar_as2org
from products.bloqueios.build import publicar_bloqueios
from products.radar.build import publicar_radar
from products.contratos.build import publicar_contratos
from products.exposicao.build import publicar_exposicao
from products.instalacoes.build import publicar_instalacoes
from products.seguranca.build import publicar_seguranca
from products.sici.build import publicar_sici, publicar_sici_movel
from products.sici_indicadores.build import publicar_sici_indicadores
from products.snapshot import build as snapshot


@dataclass
class Contexto:
    """O que um passo recebe: onde estão os dados e as duas configurações que os testes e o replay substituem."""
    base: Path
    date: str
    log: object
    ixps: Callable[[], list] = field(default=lambda: load_ixps())
    config_peeringdb: Callable[[], dict] = field(default=lambda: load_peeringdb_ixps_config())


@dataclass(frozen=True)
class Passo:
    id: str
    produto: str                               # produto do catálogo a que o passo contribui
    descricao: str
    executar: Callable[[Contexto], dict]


def _outorgas_demais(c: Contexto) -> dict:
    r: dict = {}
    for sigla, svc in SERVICOS.items():
        if sigla != "scm":
            r[sigla] = publicar_outorgas(svc, c.base, c.date, c.log)
    return r


PASSOS: dict[str, Passo] = {p.id: p for p in (
    Passo("asn_indice", "asn_docs", "Índice de ASNs (asns/index.json) e conjuntos de prefixos", lambda c: asn_docs.executar_indice(c.base, c.date, c.log)),
    Passo("ixp_indice", "ixp_docs", "Índice de IXPs (ixps/index.json)", lambda c: ixp_docs.executar_indice(c.base, c.date, c.log, c.ixps())),
    Passo("mapas_hilbert", "mapas_prefixos", "Densidade Hilbert v4 e v6", lambda c: mapas_prefixos.executar_hilbert(c.base, c.date, c.log)),
    Passo("snapshot_resumo", "snapshot", "Resumo do snapshot (summary.json)", lambda c: {"summary": bool(snapshot.executar_resumo(c.base, c.date, c.log, c.ixps()))}),
    Passo("ixp_externos", "ixp_docs", "IXPs externos do PeeringDB", lambda c: ixp_docs.executar_externos(c.base, c.date, c.log, c.config_peeringdb)),
    Passo("cdns", "cdns", "Presença de CDNs nos IXPs", lambda c: {"cdn_count": publicar_cdn_presence(c.base, c.date, c.log)}),
    Passo("asn_ixp_paths", "asn_docs", "Caminhos de IXP por ASN (fragmento ixp_paths)", lambda c: asn_docs.executar_ixp_paths(c.base, c.date, c.log)),
    Passo("asn_nomes", "asn_docs", "Nomes de ASNs (asns/names.json)", lambda c: asn_docs.executar_nomes(c.base, c.date, c.log)),
    Passo("mapas_geo", "mapas_prefixos", "Mapas GeoJSON de prefixos e ASNs", lambda c: mapas_prefixos.executar_mapas(c.base, c.date, c.log)),
    Passo("sici", "sici", "Acessos SICI fixos (fragmentos de ASN e de SCM)", lambda c: publicar_sici(c.base, c.date, c.log)),
    Passo("outorgas_scm", "outorgas", "Outorgas SCM (já com o SICI)", lambda c: publicar_outorgas(SERVICOS["scm"], c.base, c.date, c.log)),
    Passo("outorgas_demais", "outorgas", "Outorgas SMP, STFC e SeAC", _outorgas_demais),
    Passo("mapas_infraestrutura", "mapas_infraestrutura", "Camadas de infraestrutura física", lambda c: publicar_infra_maps(c.base, c.date, c.log)),
    Passo("sici_movel", "sici", "Acessos SICI móveis", lambda c: publicar_sici_movel(c.base, c.date, c.log)),
    Passo("grupos_societarios", "grupos_societarios", "Grupos societários", lambda c: publicar_grupos_societarios(c.base, c.date, c.log)),
    Passo("sici_indicadores", "sici_indicadores", "Indicadores do SICI e outorgas sem declaração", lambda c: publicar_sici_indicadores(c.base, c.date, c.log)),
    Passo("penetracao", "penetracao", "Penetração de banda larga fixa e mercado não visto (IBGE × SICI)", lambda c: publicar_penetracao(c.base, c.date, c.log)),
    Passo("route_servers", "route_servers", "Route servers do IX.br: sessões do Alice × cadastro de membros", lambda c: publicar_route_servers(c.base, c.date, c.log, c.ixps())),
    Passo("rs_policy", "rs_policy", "Política de roteamento nos route servers do IX.br: rejeições, communities e perfil", lambda c: publicar_rs_policy(c.base, c.date, c.log, c.ixps())),
    Passo("decix_rs", "decix_rs", "DE-CIX Rio e São Paulo: sessões e rotas dos route servers, ASNs diretos e originadores e comparação por cidade", lambda c: publicar_decix_rs(c.base, c.date, c.log)),
    Passo("cetic", "cetic", "Pesquisas TIC do Cetic.br: tabelas oficiais em formato longo", lambda c: publicar_cetic(c.base, c.date, c.log)),
    Passo("demanda_oferta", "demanda_oferta", "Demanda × oferta de banda larga fixa (TIC × IBGE × SICI)", lambda c: publicar_demanda_oferta(c.base, c.date, c.log)),
    Passo("erbs", "erbs", "Estações do SMP licenciadas por município, UF e operadora", lambda c: publicar_erbs(c.base, c.date, c.log)),
    Passo("regulatorio", "regulatorio", "Regulatório complementar: FUST, multas, espectro e satélites", lambda c: publicar_regulatorio(c.base, c.date, c.log)),
    Passo("qualidade", "qualidade", "Qualidade (RQUAL) e reclamações da Anatel, com a ligação marca → CNPJ", lambda c: publicar_qualidade(c.base, c.date, c.log)),
    Passo("consumidor", "consumidor", "Reclamações no Consumidor.gov.br (operadoras), com a ligação empresa → CNPJ", lambda c: publicar_consumidor(c.base, c.date, c.log)),
    Passo("cadastro_empresas", "cadastro_empresas", "Cadastro das empresas de telecom (Receita) cruzado com o SICI: presença física e entradas no mercado", lambda c: publicar_cadastro_empresas(c.base, c.date, c.log)),
    Passo("financiamento_sancoes", "financiamento_sancoes", "Crédito público (BNDES) e sanções (CEIS e CNEP) por operadora", lambda c: publicar_financiamento_sancoes(c.base, c.date, c.log)),
    Passo("ipv4", "ipv4", "Mercado de IPv4: transferências, recuperação e blocos do Brasil", lambda c: publicar_ipv4(c.base, c.date, c.log)),
    Passo("ipv4_uso", "ipv4_uso", "Espaço IPv4 sem uso e hipóteses de uso por terceiros", lambda c: publicar_ipv4_uso(c.base, c.date, c.log)),
    Passo("ipv4_subasig", "ipv4_subasig", "Sub-asignações de IPv4 (aluguel regulado): bitácora, validações e vigia", lambda c: publicar_ipv4_subasig(c.base, c.date, c.log)),
    Passo("seguranca_asn", "seguranca_asn", "Segurança de roteamento por ASN, parte A (ROV, DNSSEC, AS Rank, bogons)", lambda c: publicar_seguranca(c.base, c.date, c.log)),
    Passo("as2org", "as2org", "Organização por ASN (CAIDA) e irmãos do Brasil", lambda c: publicar_as2org(c.base, c.date, c.log)),
    Passo("abuso_agregado", "abuso_agregado", "Abuso agregado por ASN (Feodo Tracker)", lambda c: publicar_abuso_agregado(c.base, c.date, c.log)),
    Passo("bloqueios", "bloqueios", "Bloqueios e interferência medidos pelo OONI, por ASN", lambda c: publicar_bloqueios(c.base, c.date, c.log)),
    Passo("radar", "radar", "Cloudflare Radar por ASN e UF: IPv6, tráfego, velocidade e eventos de BGP", lambda c: publicar_radar(c.base, c.date, c.log)),
    Passo("contratos", "contratos", "Contratos públicos (PNCP, Lei 14.133) por operadora e município", lambda c: publicar_contratos(c.base, c.date, c.log)),
    Passo("exposicao", "exposicao", "Exposição de serviços por ASN e UF (contagens do Shodan, com a data da leitura)", lambda c: publicar_exposicao(c.base, c.date, c.log)),
    Passo("instalacoes", "instalacoes", "Instalações do PeeringDB, vínculos, atributos das redes e portas externas", lambda c: publicar_instalacoes(c.base, c.date, c.log)),
)}
ORDEM: tuple[str, ...] = tuple(PASSOS)

# Dependências entre passos (as das etapas do catálogo): `asn_ixp_paths` antes do `sici` porque reescrever um fragmento invalida os seguintes.
DEPENDE_DE: dict[str, tuple[str, ...]] = {
    "mapas_hilbert": ("asn_indice",),
    "snapshot_resumo": ("asn_indice", "ixp_indice", "mapas_hilbert"),
    "ixp_externos": ("asn_indice",),
    "cdns": ("ixp_indice", "ixp_externos"),
    "mapas_geo": ("asn_indice",),
    "sici": ("asn_ixp_paths",),
    "outorgas_scm": ("sici",),
    "outorgas_demais": ("outorgas_scm",),
    "sici_movel": ("sici",),
    "sici_indicadores": ("asn_indice", "sici", "outorgas_scm", "grupos_societarios"),
    "penetracao": ("sici",),
    "demanda_oferta": ("penetracao", "cetic"),
    "erbs": ("outorgas_demais", "sici_movel"),
    "qualidade": ("outorgas_demais", "sici_movel"),
    "consumidor": ("outorgas_demais",),
    "cadastro_empresas": ("outorgas_demais", "sici_movel"),
    "financiamento_sancoes": ("outorgas_demais",),
    "ipv4": ("asn_indice",),
    "ipv4_uso": ("ipv4",),
    "ipv4_subasig": ("ipv4_uso",),
    "seguranca_asn": ("asn_indice", "sici"),
    "as2org": ("asn_indice",),
    "abuso_agregado": ("asn_indice",),
    "bloqueios": ("asn_indice",),
    "radar": ("asn_indice",),
    "contratos": ("asn_indice",),
    "exposicao": ("asn_indice",),
    "instalacoes": ("asn_indice",),
    "decix_rs": ("asn_indice", "ixp_externos"),
}


def executar(passo_id: str, ctx: Contexto) -> dict:
    return PASSOS[passo_id].executar(ctx)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Passo do build do snapshot")
    p.add_argument("--passo", required=True, choices=list(PASSOS))
    p.add_argument("--date", default=today_str())
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        r = executar(a.passo, Contexto(data_dir(), a.date, log, ixps=_ixps_atual, config_peeringdb=_config_atual))
    except Exception:
        log.exception("falha no passo", passo=a.passo)
        return 1
    log.info("passo concluído", passo=a.passo, resultado=r)
    return 0


def _ixps_atual() -> list:
    return load_ixps()


def _config_atual() -> dict:
    return load_peeringdb_ixps_config()


if __name__ == "__main__":
    sys.exit(main())
