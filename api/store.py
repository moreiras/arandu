# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Camada de acesso aos dados — lê de published/{date}/ sem banco de dados.

Todos os dados são pré-computados pelo pipeline (`metricas_ixp_asn` e os passos do build) e salvos como
arquivos JSON imutáveis. A Store carrega índices na primeira requisição e os
mantém em memória; arquivos de detalhe individuais são lidos do disco por demanda.
"""

from __future__ import annotations

import gzip
import ipaddress
import json
import logging
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from ipaddress import ip_network
from pathlib import Path
from typing import Optional

import os
import threading

from cachetools import LRUCache

from api import outorgas_store
from api.repos.documentos import DocumentosRepo
from api.repos.rpki import RpkiRepo
from api.repos.sici import SiciRepo
from api.repos.sici_indicadores import SiciIndicadoresRepo
from api.repos.cetic import CeticRepo
from api.repos.erbs import ErbsRepo
from api.repos.regulatorio import RegulatorioRepo
from api.repos.empresas import EmpresasRepo
from api.repos.financiamento import FinanciamentoRepo
from api.repos.qualidade import QualidadeRepo
from api.repos.consumidor import ConsumidorRepo
from api.repos.ipv4 import Ipv4Repo
from api.repos.route_servers import RouteServersRepo
from api.repos.rs_policy import RsPolicyRepo
from api.repos.decix_rs import DecixRsRepo
from api.repos.as2org import As2orgRepo
from api.repos.transito import TransitoRepo
from api.repos.bloqueios import BloqueiosRepo
from api.repos.radar import RadarRepo
from api.repos.contratos import ContratosRepo
from api.repos.exposicao import ExposicaoRepo
from api.repos.instalacoes import InstalacoesRepo
from api.repos.seguranca import SegurancaRepo
from api.repos.prontidao import ProntidaoRepo
from api.repos.territorio import TerritorioRepo
from api.services import delegar, delegar_como
from core import layout, plugins
from api.geo import haversine_km


def _env_int(name: str, default: int) -> int:
    """Tamanho de LRU ajustável por variável de ambiente (ver docker-compose.prod.yml)."""
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


class _SafeLRU:
    """LRU com RLock — seguro para acessos simultâneos de múltiplas threads."""

    __slots__ = ("_cache", "_lock")

    def __init__(self, maxsize: int) -> None:
        self._cache: LRUCache = LRUCache(maxsize=maxsize)
        self._lock = threading.RLock()

    def __contains__(self, key: object) -> bool:
        with self._lock:
            return key in self._cache

    def __getitem__(self, key):
        with self._lock:
            return self._cache[key]  # raises KeyError se ausente

    def __setitem__(self, key, value) -> None:
        with self._lock:
            self._cache[key] = value

    def get(self, key, default=None):
        """Leitura atômica: entre um `in` e um `[]` outra thread pode despejar a entrada."""
        with self._lock:
            return self._cache.get(key, default)

try:
    import maxminddb as _maxminddb
except ImportError:
    _maxminddb = None  # type: ignore[assignment]

try:
    import yaml as _yaml
except ImportError:
    _yaml = None  # type: ignore[assignment]

from core.common import codigo_valido, published_path
from core.cpf import mascarar_cpf_em, pode_ter_cpf
from core.geoip import extrair_geo
from core.ixp_geo import first_ip, slash20_blocks

_log = logging.getLogger("arandurape")

_MMDB_UNINIT = object()  # sentinela — distingue "não tentou" de "não disponível"

_strip_scm_contacts = outorgas_store.strip_contacts      # nome histórico; vale para os quatro serviços

# ---------------------------------------------------------------------------
# Helpers de geolocalização
# ---------------------------------------------------------------------------

_slash20_blocks = slash20_blocks      # nomes antigos; o cálculo mora em core.ixp_geo (o pipeline também o usa)
_first_ip = first_ip


# Raio (km) para considerar um AS "próximo" de um PTT na seção "Potencial".
IXP_POTENTIAL_PROXIMITY_KM = 80.0


def _normalize_city(s: str) -> str:
    """Remove diacríticos e normaliza para uppercase ASCII para comparação."""
    return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode().upper()


def _collapsed_nets(prefixes, version: int) -> list:
    """Converte e colapsa uma lista de prefixos (CIDR) de uma única família."""
    nets = []
    for p in prefixes or []:
        try:
            n = ip_network(p, strict=False)
        except ValueError:
            continue
        if n.version == version:
            nets.append(n)
    return list(ipaddress.collapse_addresses(nets)) if nets else []


def _space_gap_units(allocated: list, announced: list, unit_prefixlen: int) -> float:
    """Unidades (ex.: /24s ou /48s) cobertas por `allocated` mas não por `announced`.

    Ambas as listas devem vir colapsadas (sem sobreposição interna) — nesse caso a
    soma das interseções par-a-par entre os dois conjuntos equivale exatamente à
    interseção das uniões, sem precisar enumerar endereço a endereço.
    """
    if not allocated:
        return 0.0
    unit_size = 1 << (allocated[0].max_prefixlen - unit_prefixlen)
    allocated_addrs = sum(n.num_addresses for n in allocated)
    overlap_addrs = 0
    for a in allocated:
        a_lo, a_hi = int(a.network_address), int(a.broadcast_address)
        for b in announced:
            if b.version != a.version:
                continue
            lo = max(a_lo, int(b.network_address))
            hi = min(a_hi, int(b.broadcast_address))
            if hi >= lo:
                overlap_addrs += hi - lo + 1
    gap_addrs = max(0, allocated_addrs - overlap_addrs)
    return gap_addrs / unit_size


def _extract_geo(record: dict) -> Optional[dict]:
    """Extrai lat/lon/city/uf/country de um registro mmdb (DB-IP; o formato do GeoLite2 segue lido). None se incompleto."""
    return extrair_geo(record)

# ---------------------------------------------------------------------------
# Hilbert IPv6 — constantes de blocos RIR (espelha snapshot_builder.py)
# ---------------------------------------------------------------------------

_V6_UNIT_SHIFT = 96  # 128 - 32

_V6_BLOCKS_META: dict[str, tuple[int, int, int]] = {
    name: (
        int(ipaddress.ip_address(base_str)),
        1 << (128 - base_len),
        1 << (32 - base_len),
    )
    for name, (base_str, base_len) in {
        "legacy":  ("2001::", 16),
        "lacnic":  ("2800::", 12),
        "arin":    ("2600::", 12),
        "ripe":    ("2a00::", 12),
        "apnic":   ("2400::", 12),
        "afrinic": ("2c00::", 12),
    }.items()
}


def _v6_to_sparse(prefixes) -> dict[str, list[int]]:
    """Converte lista de prefixos IPv6 em índices esparsos de /32 por bloco RIR."""
    cells: dict[str, set[int]] = {name: set() for name in _V6_BLOCKS_META}
    for prefix_str in prefixes:
        try:
            net = ipaddress.ip_network(prefix_str, strict=False)
        except ValueError:
            continue
        if net.version != 6:
            continue
        net_int = int(net.network_address)
        net_end = net_int + (1 << (128 - net.prefixlen))
        for block_name, (base_int, block_addr_size, block_cells) in _V6_BLOCKS_META.items():
            block_end = base_int + block_addr_size
            start = max(net_int, base_int)
            end = min(net_end, block_end)
            if start >= end:
                continue
            cell_start = (start - base_int) >> _V6_UNIT_SHIFT
            if net.prefixlen >= 32:
                cell_end = cell_start + 1
            else:
                cell_end = min((end - base_int) >> _V6_UNIT_SHIFT, block_cells)
            if cell_start < cell_end:
                cells[block_name].update(range(cell_start, cell_end))
    return {name: sorted(s) for name, s in cells.items()}


class Store:
    """Cache lazy de dados de snapshot. Seguro para leitura concorrente (GIL)."""

    def __init__(self, base: Path):
        self.base = base
        # (assinatura de published/, datas, diretórios ainda sem manifesto): ver list_snapshots. Tupla, não mapeamento: a guarda de
        # memória (api/memoria.py) não a trata como cache por data.
        self._snapshots_cache: Optional[tuple] = None
        # documentos de nível de snapshot lidos inteiros (resumo, manifesto, índices, Hilbert, BGP…): api/repos/documentos.py
        self._docs = DocumentosRepo(self._pub)
        self._asn_map: dict[str, dict[int, dict]] = {}
        self._ixp_br_sets: dict[str, dict] = {}
        # LRU-24: "{date}/{code}/{afi}" → {origin_asn: [(path_tuple, count), ...]}
        # Bounded para limitar footprint: 40 IXPs × 2 AFIs = 80 chaves possíveis,
        # mas só os ~12 maiores IXPs são acessados com frequência (v6+v4 = 24 entradas).
        self._origin_paths: _SafeLRU = _SafeLRU(maxsize=_env_int("STORE_ORIGIN_PATHS_LRU", 24))
        # Cache: date_str → parsed VRP index structure (or None if unavailable)
        self._rpki = RpkiRepo(self._pub)
        self._outorgas = outorgas_store.criar_todas(self._pub)       # os `<sigla>_*` e `_load_<sigla>` do Store delegam a ele
        from api.services.mapas import MapasService     # import tardio: o serviço importa helpers deste módulo
        self._mapas = MapasService(self)
        from api.services.geolocalizacao import GeolocalizacaoService
        self._geolocalizacao = GeolocalizacaoService(self)
        from api.services.consultas import ConsultasService
        self._consultas = ConsultasService(self)
        from api.services.bgp_estabilidade import BgpEstabilidadeService
        self._bgp = BgpEstabilidadeService(self)
        from api.services.ixps import IxpsService
        self._ixps = IxpsService(self)
        from api.services.hilbert import HilbertService
        self._hilbert = HilbertService(self)
        from api.services.asns import AsnsService
        self._asns = AsnsService(self)
        from api.services.perfis import PerfisService
        self._perfis = PerfisService(self)
        from api.services.operadoras import OperadorasService
        self._operadoras = OperadorasService(self)
        from api.services.ixp_potencial import IxpPotencialService
        self._ixp_potencial = IxpPotencialService(self)
        # Cache: date_str → {"asns": geojson_dict, "prefixes": geojson_dict}
        # Cache: (date_str, code, layer) → GeoJSON FeatureCollection
        # Cache LRU simples para documentos individuais de ASN — evita releituras de disco
        # em requisições consecutivas do mesmo AS (grafo de relações, geo, etc.)
        self._asn_detail_cache: dict[str, dict[int, dict]] = {}
        # Cache do documento JÁ ENRIQUECIDO (alerts, RPKI, path_node_meta) — usado só
        # quando o snapshot não foi pré-enriquecido no publish; memoiza a augmentação
        # cara por (date, asn) para não recomputar a cada request.
        self._asn_full_cache: dict[str, dict[int, dict]] = {}
        # LRU-24: "{date}/{code}/{afi}" → {str(asn): stats} ou None se arquivo ausente.
        # Parsear routes-{afi}.json.gz é caro; IXPs populares são compartilhados entre
        # Mapa Explorer: recorte de ASes (matched_asns) por hash do filtro. O front
        # dispara uma consulta por camada com o mesmo recorte, e elas reaproveitam o mesmo cálculo.
        # Cache para documentos de IXP — número pequeno de IXPs, tudo cabe em memória
        self._ixp_detail_cache: dict[str, dict[str, dict]] = {}
        # Cache: (date_str, asn, layer) → GeoJSON FeatureCollection
        # Cache: "{date}/{ixp_code}/{afi}" → {str(asn): [prefixes]}
        # Cache: date_str → hilbert_v4/hilbert_v6 JSON (leitura única por snapshot)
        # Cache: date_str → summary/manifest JSON
        # date_str → {camada: hash}: só os checksums de maps/*.geojson (ver `_hashes_das_camadas`)
        self._camadas_hash_cache: dict[str, dict[str, str]] = {}
        # Cache: date_str → external-ixps index JSON
        self._external_ixps_br_union_cache: dict[str, set] = {}
        # Cache: date_str → cdns JSON
        # Cache: date_str → routing_analysis JSON
        # Cache: date_str → índice reverso {asn: {"m": [codes], "o": [codes]}}
        # (m = IXes onde o AS é membro IX.br; o = IXes onde origina prefixos BR)
        self._asn_ix_presence_cache: dict[str, dict] = {}
        # Cache: "{date}/{collection}" → tabela consultável (lista de dicts enriquecida)
        self._query_tables: dict[str, list[dict]] = {}
        # Acessos Anatel/SICI, fixo e móvel: repositórios em api/repos
        self._sici = SiciRepo(self._pub, "sici")
        self._sici_movel = SiciRepo(self._pub, "sici_movel")
        self._sici_ind = SiciIndicadoresRepo(self._pub)         # indicadores e omissão
        self._territorio = TerritorioRepo(self._pub)            # penetração e mercado não visto
        self._prontidao = ProntidaoRepo(self._pub)              # prontidão em segurança de roteamento
        self._seguranca = SegurancaRepo(self._pub)              # segurança de roteamento por ASN
        self._ipv4 = Ipv4Repo(self._pub, self.base)             # mercado de IPv4
        self._erbs = ErbsRepo(self._pub)                        # estações do SMP licenciadas
        self._regulatorio = RegulatorioRepo(self._pub)          # FUST e demais bases regulatórias
        self._qualidade = QualidadeRepo(self._pub)              # RQUAL e reclamações da Anatel
        self._consumidor = ConsumidorRepo(self._pub)            # reclamações no Consumidor.gov.br
        self._financiamento = FinanciamentoRepo(self._pub)    # crédito público (BNDES) e sanções (CEIS/CNEP) por operadora
        self._empresas = EmpresasRepo(self._pub)                # cadastro das empresas de telecom, Receita × SICI
        self._cetic = CeticRepo(self._pub)                      # pesquisas TIC do Cetic.br
        self._route_servers = RouteServersRepo(self._pub)       # sessões dos route servers do IX.br
        self._rs_policy = RsPolicyRepo(self._pub)               # rejeições, communities e política nos route servers
        self._decix_rs = DecixRsRepo(self._pub)                 # DE-CIX Rio e São Paulo nos route servers
        self._bloqueios = BloqueiosRepo(self._pub)                # bloqueios medidos pelo OONI, por ASN
        self._radar = RadarRepo(self._pub)                        # Cloudflare Radar por ASN e UF
        self._contratos = ContratosRepo(self._pub)                # contratos públicos (PNCP) por operadora e município
        self._exposicao = ExposicaoRepo(self._pub)                # exposição de serviços (Shodan) por ASN e UF
        self._as2org = As2orgRepo(self._pub)                    # organização por ASN e abuso agregado
        self._transito = TransitoRepo(self._pub)                # trânsito por UF e cone de clientes
        self._instalacoes = InstalacoesRepo(self._pub)          # instalações do PeeringDB, atributos das redes e portas externas
        # Cache: "{date}/grupo_cnpjs" → {grupo: [{cnpj, empresa}, ...]} (SICI fixo+móvel)
        self._grupo_cnpjs_cache: dict[str, dict[str, list[dict]]] = {}

    # -------------------------------------------------------------------------
    # Descoberta de snapshots
    # -------------------------------------------------------------------------

    def list_snapshots(self) -> list[str]:
        """Retorna datas disponíveis (diretórios com manifest.json), ordenadas.

        Guardada em memória: era chamada várias vezes por pedido (política de acesso, middleware, estabilidade BGP, guarda de memória) e
        cada chamada fazia dois `stat` por data publicada. Com 19 datas e a API ocupada, cada `stat` esperava o GIL na volta e a lista
        custava 0,65 s (perfil medido na produção em 2026-11-21). Agora custa um `stat` de `published/`: data nova, removida ou
        renomeada muda o diretório; um diretório ainda sem manifesto (publicação em andamento) é reconferido até ganhá-lo."""
        pub = self.base / "published"
        try:
            st = pub.stat()
        except OSError:
            return []
        assinatura = (st.st_mtime_ns, st.st_ino, st.st_nlink)
        cache = self._snapshots_cache
        if cache is not None and cache[0] == assinatura and not any((pub / d / "manifest.json").exists() for d in cache[2]):
            return list(cache[1])
        datas, pendentes = [], []
        for d in pub.iterdir():
            if d.is_dir():
                (datas if (d / "manifest.json").exists() else pendentes).append(d.name)
        datas.sort()
        self._snapshots_cache = (assinatura, tuple(datas), tuple(pendentes))
        return datas

    def latest(self) -> Optional[str]:
        snaps = self.list_snapshots()
        return snaps[-1] if snaps else None

    _DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    def resolve_date(self, date_str: Optional[str]) -> Optional[str]:
        """Retorna date_str se fornecido, caso contrário o snapshot mais recente."""
        if date_str and not self._DATE_RE.fullmatch(date_str):
            raise ValueError(f"Parâmetro 'date' inválido: {date_str!r}. Use YYYY-MM-DD.")
        return date_str or self.latest()

    # -------------------------------------------------------------------------
    # Helpers internos
    # -------------------------------------------------------------------------

    def _pub(self, date_str: str) -> Path:
        return published_path(self.base, date_str)

    def _read_json(self, path: Path) -> Optional[dict | list]:
        dados = layout.ler_bytes_de_caminho(path)      # snapshot nos dois formatos (asns.zip, _shared/)
        if dados is None:
            return None
        try:
            doc = json.loads(dados)
        except Exception:
            return None
        return mascarar_cpf_em(doc) if pode_ter_cpf(dados) else doc      # CPF embutido na razão social de EI/MEI

    # -------------------------------------------------------------------------
    # Nível de snapshot
    # -------------------------------------------------------------------------

    def _hashes_das_camadas(self, date_str: str) -> dict[str, str]:
        """{camada: hash curto} de maps/*.geojson no manifesto da data (16 hex do sha256).

        Só estas ~12 entradas ficam guardadas por data: o manifesto inteiro tem milhares de checksums de ASN e, lido para
        procurar um hash desconhecido em todas as datas, custou ~8 s e centenas de MiB retidos. Manifesto já em memória
        (latest) é reaproveitado; os demais são lidos e soltos. Snapshot publicado é imutável, então o resumo vale para sempre."""
        if date_str not in self._camadas_hash_cache:
            man = self._docs.manifest_em_memoria(date_str) or self._read_json(self._pub(date_str) / "manifest.json")
            if man is None:
                return {}
            self._camadas_hash_cache[date_str] = {
                k[len("maps/"):-len(".geojson")]: v.split(":", 1)[-1][:16]
                for k, v in ((man.get("checksums") or {}).items())
                if k.startswith("maps/") and k.endswith(".geojson") and k.count("/") == 1
            }
        return self._camadas_hash_cache[date_str]

    def camada_hash(self, date_str: str, layer: str) -> Optional[str]:
        """Hash curto do conteúdo de maps/{layer}.geojson; None se a camada não existe na data."""
        return self._hashes_das_camadas(date_str).get(layer)

    def data_da_camada(self, layer: str, hash_: str) -> Optional[str]:
        """Snapshot mais recente cuja camada tem este hash (conteúdo idêntico entre semanas): endereça por conteúdo."""
        for d in reversed(self.list_snapshots()):
            if self.camada_hash(d, layer) == hash_:
                return d
        return None

    # -------------------------------------------------------------------------
    # IXPs externos (PeeringDB)
    # -------------------------------------------------------------------------

    def external_ixp_detail(self, date_str: str, code: str) -> Optional[dict]:
        """Documento completo de um IXP externo, com o nome de cada membro pelo ASN (`asns/names.json`).

        Snapshots podem trazer o nome do PTT como nome de todo membro (o `name` do netixlan do PeeringDB é o do PTT):
        esse valor nunca é servido como nome de rede."""
        if not codigo_valido(code):
            return None
        doc = self._read_json(self._pub(date_str) / "external-ixps" / f"{code}.json")
        if isinstance(doc, dict) and doc.get("members"):
            nomes, do_ptt = self.asn_names(date_str), doc.get("name")
            doc["members"] = [{**m, "name": nomes.get(str(m.get("asn"))) or (m.get("name") if m.get("name") != do_ptt else None) or ""}
                              for m in doc["members"]]
        return doc

    def external_ixps_br_asn_union(self, date_str: str) -> set:
        """União de ASNs BR membros de qualquer IXP externo (PeeringDB). Cacheado.

        Um mesmo AS frequentemente é membro de vários IXPs externos (ex.: AMS-IX,
        DE-CIX, Equinix em cidades diferentes) — somar `br_member_count` por IXP
        contaria o mesmo AS múltiplas vezes; esta união deduplica por ASN.
        """
        if date_str not in self._external_ixps_br_union_cache:
            union: set = set()
            idx = self.external_ixp_index(date_str) or {}
            for entry in idx.get("ixps", []):
                doc = self.external_ixp_detail(date_str, entry["code"])
                if not doc:
                    continue
                for m in doc.get("members", []):
                    if m.get("is_br"):
                        union.add(m["asn"])
            self._external_ixps_br_union_cache[date_str] = union
        return self._external_ixps_br_union_cache[date_str]

    def ixp_br_origin_sets(self, date_str: str) -> dict:
        """Conta BR ASNs originando só IPv4, só IPv6, ou ambos na união de IXPs. Cacheado."""
        if date_str not in self._ixp_br_sets:
            union_v4: set = set()
            union_v6: set = set()
            ixp_dir = self._pub(date_str) / "ixps"
            if ixp_dir.exists():
                for f in ixp_dir.glob("*.json"):
                    if f.name == "index.json":
                        continue
                    doc = self._read_json(f) or {}
                    v4 = doc.get("v4", {})
                    v6 = doc.get("v6", {})
                    if isinstance(v4, dict):
                        union_v4.update(v4.get("br_asns_origin", []))
                    if isinstance(v6, dict):
                        union_v6.update(v6.get("br_asns_origin", []))
            self._ixp_br_sets[date_str] = {
                "br_ixp_origin_v4":      len(union_v4),
                "br_ixp_origin_v6":      len(union_v6),
                "br_ixp_origin_v4_only": len(union_v4 - union_v6),
                "br_ixp_origin_v6_only": len(union_v6 - union_v4),
                "br_ixp_origin_both":    len(union_v4 & union_v6),
            }
        return self._ixp_br_sets[date_str]

    def asn_ix_presence(self, date_str: str) -> dict:
        """Índice reverso {asn: {"m": [codes], "o": [codes]}} de participação em IXes.

        m (membro)  — IXes onde o AS consta como membro do IX.br (ixbr_members.json).
        o (origem)  — IXes onde o AS origina prefixos BR (br_asns_origin v6 ∪ v4).

        Construído a partir dos docs de IXP já publicados + listas de membros raw.
        Cacheado por data — payload grande, mas servido uma vez (proxy_cache + gzip).
        """
        if date_str in self._asn_ix_presence_cache:
            return self._asn_ix_presence_cache[date_str]

        member: dict[int, list[str]] = {}
        origin: dict[int, list[str]] = {}
        for entry in self.ixp_index(date_str):
            code = entry.get("code")
            if not code:
                continue
            for asn in self._load_ixp_members(date_str, code):
                member.setdefault(asn, []).append(code)
            doc = self.ixp_detail(date_str, code) or {}
            o: set[int] = set()
            for afi in ("v4", "v6"):
                v = doc.get(afi)
                if isinstance(v, dict):
                    o.update(v.get("br_asns_origin") or [])
            for asn in o:
                origin.setdefault(asn, []).append(code)

        asns: dict[str, dict] = {}
        for asn in set(member) | set(origin):
            asns[str(asn)] = {
                "m": sorted(member.get(asn, [])),
                "o": sorted(origin.get(asn, [])),
            }
        result = {"snapshot_date": date_str, "asns": asns}
        self._asn_ix_presence_cache[date_str] = result
        return result

    # -------------------------------------------------------------------------
    # Camada de consulta genérica (api/query.py)
    # -------------------------------------------------------------------------

    def _pix_points(self, date_str: str, code: Optional[str] = None) -> list[tuple]:
        """Lista de (lat, lon) dos PIX do IX.br — todos, ou de um IXP."""
        pts: list[tuple] = []
        for f in self._pix_features(date_str):
            if code and f.get("properties", {}).get("ixp_code") != code:
                continue
            c = f.get("geometry", {}).get("coordinates") or []
            if len(c) >= 2:
                pts.append((c[1], c[0]))  # [lon, lat] → (lat, lon)
        return pts

    def resolve_place(self, date_str: str, name: str, uf: Optional[str] = None) -> Optional[dict]:
        """Centroide (mediana) das organizações geolocalizadas em um município (de uma UF, se informada: sem ela, homônimos se misturam)."""
        target = _normalize_city(name)
        lats: list[float] = []
        lons: list[float] = []
        for g in self._load_geo_orgs(date_str).values():
            city = g.get("city")
            if uf and (g.get("uf") or "").upper() != uf.upper():
                continue
            if city and _normalize_city(city) == target and g.get("lat") is not None:
                lats.append(g["lat"])
                lons.append(g["lon"])
        if not lats:
            return None
        lats.sort()
        lons.sort()

        def _median(xs: list[float]) -> float:
            n = len(xs)
            return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2

        return {"lat": _median(lats), "lon": _median(lons), "n": len(lats)}

    def near_centers(self, date_str: str, near: dict) -> tuple[list[list[float]], float, str]:
        """Resolve a conveniência `near` em (centros, radius_km, rótulo)."""
        from api.query import QueryError

        if not isinstance(near, dict):
            raise QueryError("near deve ser um objeto")
        radius = near.get("radius_km")
        if radius is None:
            raise QueryError("near exige 'radius_km'")
        if "point" in near:
            pt = near["point"]
            try:
                centers = [[float(pt[0]), float(pt[1])]]
            except (TypeError, IndexError, ValueError):
                raise QueryError("near.point deve ser [lat, lon]")
            return centers, radius, f"point [{pt[0]}, {pt[1]}]"
        if "ixp" in near:
            code = str(near["ixp"]).lower()
            centers = [[lat, lon] for (lat, lon) in self._pix_points(date_str, code)]
            if not centers:
                raise QueryError(f"PTT '{code}' sem PIX geolocalizado")
            return centers, radius, f"ixp {code} ({len(centers)} PIX)"
        if "place" in near:
            r = self.resolve_place(date_str, str(near["place"]))
            if r is None:
                raise QueryError(f"local '{near['place']}' não encontrado (sem orgs geolocalizadas)")
            return [[r["lat"], r["lon"]]], radius, f"place {near['place']} (n={r['n']})"
        raise QueryError("near exige um de: point | ixp | place")

    # -------------------------------------------------------------------------
    # Analíticos parametrizados (junções multi-hop)
    # -------------------------------------------------------------------------

    def ixp_detail(self, date_str: str, code: str) -> Optional[dict]:
        """Documento completo de um IXP (de ixps/{code}.json). Cacheado em memória."""
        if not codigo_valido(code):
            return None
        cache = self._ixp_detail_cache.get(date_str)                 # data inventada não cria entrada (só o que foi lido entra)
        if cache is not None and code in cache:
            return cache[code]
        result = self._read_json(self._pub(date_str) / "ixps" / f"{code}.json")
        if result is not None:
            self._ixp_detail_cache.setdefault(date_str, {})[code] = result
        return result

    # -------------------------------------------------------------------------
    # ASNs
    # -------------------------------------------------------------------------

    def asn_map(self, date_str: str) -> dict[int, dict]:
        """Dict de ASN → linha do índice. Cacheado por data."""
        if date_str not in self._asn_map:
            self._asn_map[date_str] = {row["asn"]: row for row in self.asn_index(date_str)}
        return self._asn_map[date_str]

    _ASN_DETAIL_CACHE_SIZE = 3000

    def asn_detail(self, date_str: str, asn: int) -> Optional[dict]:
        """Documento completo de um ASN (de asns/{asn}.json). Cacheado em memória."""
        cache = self._asn_detail_cache.get(date_str)                 # data inventada não cria entrada (só o que foi lido entra)
        if cache is not None and asn in cache:
            return cache[asn]
        result = self._read_json(self._pub(date_str) / "asns" / f"{asn}.json")
        if result is not None:
            cache = self._asn_detail_cache.setdefault(date_str, {})
            if len(cache) >= self._ASN_DETAIL_CACHE_SIZE:
                try:
                    cache.pop(next(iter(cache)))
                except StopIteration:
                    pass
            cache[asn] = result
        return result

    def asn_full(self, date_str: str, asn: int) -> Optional[dict]:
        """Documento de ASN com a augmentação cara (alerts, RPKI, path_node_meta).

        Se o arquivo publicado já foi pré-enriquecido (tem `alerts`), serve direto —
        o custo é só a leitura do disco (já cacheada em `asn_detail`). Caso contrário,
        roda a augmentação uma única vez por processo e memoiza o resultado.
        """
        base = self.asn_detail(date_str, asn)
        if base is None:
            return None
        # Pré-enriquecido no publish: o próprio asn_detail já cacheia o doc completo.
        if "alerts" in base:
            return base

        cache = self._asn_full_cache.setdefault(date_str, {})
        cached = cache.get(asn)
        if cached is not None:
            return cached

        enriquecer = plugins.enriquecedor_de_asn()      # por referência (core/plugins.py): `api` não importa `products`
        full = enriquecer(self, date_str, asn, base) if enriquecer else base
        if len(cache) >= self._ASN_DETAIL_CACHE_SIZE:
            try:
                cache.pop(next(iter(cache)))
            except StopIteration:
                pass
        cache[asn] = full
        return full

    # -------------------------------------------------------------------------
    # SEAC — Outorgas Anatel (Serviço de Acesso Condicionado)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # SICI — Acessos de banda larga fixa declarados à Anatel
    # -------------------------------------------------------------------------

    # SICI fixo e móvel: leitura e consultas diretas vivem em `api/repos/sici.py`; aqui, a fachada de sempre.
    def sici_indicadores(self, date_str: str) -> Optional[dict]:
        return self._sici_ind.indicadores(date_str)

    def mercado_grupos(self, date_str: str) -> Optional[dict]:
        return self._sici_ind.mercado_grupos(date_str)

    def sici_serie_municipio(self, date_str: str) -> Optional[dict]:
        return self._sici_ind.serie_municipio(date_str)

    def omissao_sici(self, date_str: str) -> Optional[dict]:
        return self._sici_ind.omissao(date_str)

    def territorio_doc(self, date_str: str) -> Optional[dict]:
        return self._territorio.municipios_doc(date_str)

    def rede_territorio_doc(self, date_str: str) -> Optional[dict]:
        return self._territorio.rede_doc(date_str)

    def regiao_doc(self, date_str: str) -> Optional[dict]:
        return self._territorio.regiao_doc(date_str)

    def seguranca_doc(self, date_str: str) -> Optional[dict]:
        return self._seguranca.asns_doc(date_str)

    def prontidao_doc(self, date_str: str) -> Optional[dict]:
        return self._prontidao.asns_doc(date_str)

    def manrs_doc(self, date_str: str) -> Optional[dict]:
        return self._prontidao.manrs_doc(date_str)

    def cetic_doc(self, date_str: str, pesquisa: str) -> Optional[dict]:
        return self._cetic.doc(date_str, pesquisa)

    def cetic_uf_doc(self, date_str: str) -> Optional[dict]:
        return self._cetic.uf_doc(date_str)

    def ipv4_transferencias_doc(self, date_str: str) -> Optional[dict]:
        return self._ipv4.transferencias_doc(date_str)

    def ipv4_mercado_doc(self, date_str: str) -> Optional[dict]:
        return self._ipv4.mercado_doc(date_str)

    def ipv4_recuperacao_doc(self, date_str: str) -> Optional[dict]:
        return self._ipv4.recuperacao_doc(date_str)

    def ipv4_blocos_br_doc(self, date_str: str) -> Optional[dict]:
        return self._ipv4.blocos_br_doc(date_str)

    def ipv4_espaco_doc(self, date_str: str) -> Optional[dict]:
        return self._ipv4.espaco_doc(date_str)

    def ipv4_uso_doc(self, date_str: str) -> Optional[dict]:
        return self._ipv4.uso_doc(date_str)

    def ipv4_subasig_doc(self, date_str: str) -> Optional[dict]:
        return self._ipv4.subasig_doc(date_str)

    def ipv4_eventos_br(self) -> list[dict]:
        return self._ipv4.eventos_br()

    def erbs_doc(self, date_str: str) -> Optional[dict]:
        return self._erbs.resumo_doc(date_str)

    def erbs_grade_doc(self, date_str: str) -> Optional[dict]:
        return self._erbs.grade_doc(date_str)

    def fust_doc(self, date_str: str) -> Optional[dict]:
        return self._regulatorio.fust_doc(date_str)

    def multas_doc(self, date_str: str) -> Optional[dict]:
        return self._regulatorio.multas_doc(date_str)

    def faixas_doc(self, date_str: str) -> Optional[dict]:
        return self._regulatorio.faixas_doc(date_str)

    def satelites_doc(self, date_str: str) -> Optional[dict]:
        return self._regulatorio.satelites_doc(date_str)

    def rqual_doc(self, date_str: str) -> Optional[dict]:
        return self._qualidade.rqual_doc(date_str)

    def rqual_municipios_uf(self, date_str: str, uf: str) -> Optional[dict]:
        return self._qualidade.rqual_municipios_uf(date_str, uf)

    def reclamacoes_doc(self, date_str: str) -> Optional[dict]:
        return self._qualidade.reclamacoes_doc(date_str)

    def reclamacoes_municipios_uf(self, date_str: str, uf: str) -> Optional[dict]:
        return self._qualidade.reclamacoes_municipios_uf(date_str, uf)

    def consumidor_doc(self, date_str: str) -> Optional[dict]:
        return self._consumidor.consumidor_doc(date_str)

    def financiamento_doc(self, date_str: str) -> Optional[dict]:
        return self._financiamento.doc(date_str)

    def cadastro_empresas_doc(self, date_str: str) -> Optional[dict]:
        return self._empresas.cadastro_doc(date_str)

    def cadastro_empresas_faixa(self, date_str: str, faixa: str) -> Optional[dict]:
        return self._empresas.operadoras_faixa(date_str, faixa)

    def consumidor_municipios_uf(self, date_str: str, uf: str) -> Optional[dict]:
        return self._consumidor.consumidor_municipios_uf(date_str, uf)

    def demanda_oferta_doc(self, date_str: str) -> Optional[dict]:
        return self._cetic.demanda_oferta_doc(date_str)

    def route_servers_ixps_doc(self, date_str: str) -> Optional[dict]:
        return self._route_servers.ixps_doc(date_str)

    def route_servers_asns_doc(self, date_str: str) -> Optional[dict]:
        return self._route_servers.asns_doc(date_str)

    def decix_rs_doc(self, date_str: str) -> Optional[dict]:
        return self._decix_rs.ixps_doc(date_str)

    def rs_policy_ixps_doc(self, date_str: str) -> Optional[dict]:
        return self._rs_policy.ixps_doc(date_str)

    def rs_policy_asns_doc(self, date_str: str) -> Optional[dict]:
        return self._rs_policy.asns_doc(date_str)

    def rs_policy_communities_doc(self, date_str: str) -> Optional[dict]:
        return self._rs_policy.communities_doc(date_str)

    def rs_policy_grafo_doc(self, date_str: str) -> Optional[dict]:
        return self._rs_policy.grafo_doc(date_str)

    def rs_policy_linhas_doc(self, date_str: str) -> Optional[dict]:
        return self._rs_policy.linhas_doc(date_str)
    def bloqueios_doc(self, date_str: str) -> Optional[dict]:
        return self._bloqueios.asns_doc(date_str)

    def radar_doc(self, date_str: str) -> Optional[dict]:
        return self._radar.asns_doc(date_str)

    def contratos_operadoras_doc(self, date_str: str) -> Optional[dict]:
        return self._contratos.operadoras_doc(date_str)

    def contratos_municipios_doc(self, date_str: str) -> Optional[dict]:
        return self._contratos.municipios_doc(date_str)

    def contratos_resumo_doc(self, date_str: str) -> Optional[dict]:
        return self._contratos.resumo_doc(date_str)
    def exposicao_doc(self, date_str: str) -> Optional[dict]:
        return self._exposicao.asns_doc(date_str)

    def as2org_doc(self, date_str: str) -> Optional[dict]:
        return self._as2org.asns_doc(date_str)

    def abuso_doc(self, date_str: str) -> Optional[dict]:
        return self._as2org.abuso_doc(date_str)

    def transito_ufs_doc(self, date_str: str) -> Optional[dict]:
        return self._transito.ufs_doc(date_str)

    def transito_asns_doc(self, date_str: str) -> Optional[dict]:
        return self._transito.asns_doc(date_str)

    def instalacoes_doc(self, date_str: str) -> Optional[dict]:
        return self._instalacoes.instalacoes_doc(date_str)

    def vinculos_instalacoes_doc(self, date_str: str) -> Optional[dict]:
        return self._instalacoes.vinculos_doc(date_str)

    def atributos_rede_doc(self, date_str: str) -> Optional[dict]:
        return self._instalacoes.atributos_doc(date_str)

    def portas_externas_doc(self, date_str: str) -> Optional[dict]:
        return self._instalacoes.portas_doc(date_str)

    def portas_ixbr_doc(self, date_str: str) -> Optional[dict]:
        return self._instalacoes.portas_ixbr_doc(date_str)

    def sici_distrib_velocidade(self, date_str: str) -> dict[str, dict]:
        return self._sici.distribuicao(date_str, "distrib_velocidade")

    def sici_movel_distrib_modalidade(self, date_str: str) -> dict[str, dict]:
        return self._sici_movel.distribuicao(date_str, "distrib_modalidade")

    def invalidate_sici(self, date_str: str) -> None:
        """Descarta o cache de SICI de um snapshot.

        `_load_sici` memoiza `None` quando o arquivo não existe. Sem isso, publicar
        sici.json.gz num snapshot que a API já serviu (backfill, bootstrap do
        histórico) continuaria devolvendo 404 até reiniciar o processo. O warm-up
        chama este método, então o pipeline não precisa de restart.
        """
        self._sici.invalidar(date_str)
        self._grupo_cnpjs_cache.pop(f"{date_str}/grupo_cnpjs", None)
        for coll in ("operadoras", "acessos_municipio", "scms"):
            self._query_tables.pop(f"{date_str}/{coll}", None)

    def _grupo_cnpjs_index(self, date_str: str) -> dict[str, list[dict]]:
        """Grupo econômico (SICI) → [{cnpj, empresa}, ...], fixo + móvel combinados.

        Anatel declara o mesmo texto de "Grupo Econômico" em CNPJs distintos quando
        pertencem ao mesmo grupo; não há tabela de grupos, então este é um índice
        invertido sobre `cnpjs` de sici.json.gz/sici_movel.json.gz, cacheado.
        """
        key = f"{date_str}/grupo_cnpjs"
        cached = self._grupo_cnpjs_cache.get(key)
        if cached is not None:
            return cached
        idx: dict[str, list[dict]] = {}
        seen: set[tuple[str, str]] = set()
        for data in (self._load_sici(date_str), self._load_sici_movel(date_str)):
            for cnpj, agg in (data or {}).get("cnpjs", {}).items():
                grupo = (agg.get("grupo") or "").strip()
                if not grupo or grupo == "OUTROS":
                    continue
                if (grupo, cnpj) in seen:
                    continue
                seen.add((grupo, cnpj))
                idx.setdefault(grupo, []).append({
                    "cnpj": cnpj,
                    "empresa": agg.get("empresa", ""),
                    **self.outorgas_flags_for_cnpj(date_str, cnpj),
                })
        for entries in idx.values():
            entries.sort(key=lambda e: e["empresa"] or e["cnpj"])
        self._grupo_cnpjs_cache[key] = idx
        return idx

    def grupo_irmaos(self, date_str: str, grupo: str, exclude_cnpj: str) -> list[dict]:
        """Outros CNPJs do mesmo grupo econômico (SICI), exceto `exclude_cnpj`."""
        if not grupo or grupo == "OUTROS":
            return []
        entries = self._grupo_cnpjs_index(date_str).get(grupo, [])
        return [e for e in entries if e["cnpj"] != exclude_cnpj]

    def sici_divergencias_scm(self, date_str: str, k_pf: float = 5, k_pj: float = 30,
                              min_razao: float = 1, min_users: int = 100) -> list[dict]:
        """APNIC × usuários esperados a partir dos acessos SCM declarados ao SICI.

        esperado = k_pf × acessos PF (B2C) + k_pj × acessos PJ (B2B). k_pf reflete
        pessoas por domicílio; k_pj é uma estimativa folgada de usuários por empresa.
        Só entram ASNs com usuários APNIC ≥ min_razao × esperado (e acima do esperado);
        esperado 0 (razão infinita) sempre entra.

        Parte das outorgas SCM (e não do SICI) para que um CNPJ outorgado que não
        declara acessos apareça com esperado 0. CNPJs com mais de um ASN ficam de fora
        pelo mesmo motivo de `nao_comparavel` na divergência total. Ordenado por
        usuários APNIC, decrescente.
        """
        scm = self._load_scm(date_str)
        if not scm:
            return []
        licensed = scm.get("by_cnpj", {})
        sici_cnpjs = (self._load_sici(date_str) or {}).get("cnpjs", {})
        asn_map = self.asn_map(date_str)
        rows = []
        for cnpj, asns in scm.get("cnpj_to_asns", {}).items():
            if cnpj not in licensed or len(asns) != 1:
                continue
            asn = int(asns[0])
            row = asn_map.get(asn) or {}
            users = row.get("apnic_users") or 0
            if users < min_users:
                continue
            agg = sici_cnpjs.get(cnpj) or {}
            pf, pj = agg.get("pf", 0), agg.get("pj", 0)
            esperado = round(k_pf * pf + k_pj * pj)
            if users <= esperado or users < min_razao * esperado:
                continue
            empresa = agg.get("empresa") or (licensed[cnpj][0].get("razao_social")
                                             if licensed[cnpj] else "")
            rows.append({
                "asn": asn,
                "name": row.get("name", ""),
                "cnpj": cnpj,
                "empresa": empresa or "",
                "apnic_users": users,
                "acessos_pf": pf,
                "acessos_pj": pj,
                "esperado": esperado,
                "excesso": users - esperado,
                "razao": round(users / esperado, 2) if esperado else None,
            })
        rows.sort(key=lambda r: -r["apnic_users"])
        return rows

    # -------------------------------------------------------------------------
    # Outorgas unificadas: uma linha por CNPJ, com os serviços que ele tem
    # -------------------------------------------------------------------------

    _SERVICOS_SIGLAS = ("scm", "smp", "stfc", "seac")
    _SERVICOS_NOMES = {"scm": "SCM", "smp": "SMP", "stfc": "STFC", "seac": "SeAC"}   # como a API as chama

    def invalidate_sici_movel(self, date_str: str) -> None:
        """Descarta o cache de SICI móvel de um snapshot. Ver invalidate_sici (mesmo
        motivo: sem isso, publicar sici_movel.json.gz num snapshot já servido pela API
        continuaria devolvendo 404 até reiniciar o processo)."""
        self._sici_movel.invalidar(date_str)
        self._grupo_cnpjs_cache.pop(f"{date_str}/grupo_cnpjs", None)
        for coll in ("operadoras_movel", "acessos_movel_municipio", "smps"):
            self._query_tables.pop(f"{date_str}/{coll}", None)

    def _load_pix_config(self) -> dict:
        return self._geolocalizacao.pix_config()

    def _mmdb_reader(self):
        return self._geolocalizacao._mmdb_reader()

    # -------------------------------------------------------------------------
    # Hilbert
    # -------------------------------------------------------------------------

    def _load_vrps(self, date_str: str) -> Optional[dict]:
        return self._rpki.vrps(date_str)

    def rpki_vrps_for_asn(self, date_str: str, asn: int) -> list[dict]:
        """Returns all ROAs authorizing this ASN. Each dict: {prefix, maxLength, ta}."""
        return self._rpki.vrps_do_asn(date_str, asn)

    def rpki_validate_prefixes(self, date_str: str, asn: int, prefixes: list[str]) -> dict[str, str]:
        """Valida cada prefixo contra o RPKI (RFC 6483): {prefixo: 'valid'|'invalid'|'not_found'}."""
        return self._rpki.validar_prefixos(date_str, asn, prefixes)

    def aspa_as_customer(self, date_str: str, asn: int) -> list[dict]:
        """Objetos ASPA publicados por este AS (como customer). Cada dict: {providers, tal}."""
        return self._rpki.como_customer(date_str, asn)

    def aspa_as_provider(self, date_str: str, asn: int) -> list[dict]:
        """Objetos ASPA de outros ASes que listam este AS como provider. Cada dict: {customer, tal}."""
        return self._rpki.como_provider(date_str, asn)


# Métodos públicos scm_*/smp_*/stfc_*/seac_* (index, for_cnpj, for_cnpj_with_contacts, for_asn, asn_set, geo_map)
outorgas_store.instalar(Store)

# Métodos que o `Store` apenas repassa ao serviço que os implementa (api/services/): mesma interface pública de antes.
delegar(Store, "_ixp_potencial", "all_ixp_estimated_users", "ixp_estimated_users", "ixp_estimated_users_aggregate", "ixp_nearby_breakdown", "ixp_potential", "operator_reach")
delegar(Store, "_perfis", "asns_por_uf", "municipio_centroide", "outorgas_do_cnpj", "outorgas_unificadas", "perfil_municipio", "perfil_uf", "territorio_linhas", "ptt_mais_proximo", "ptts_pontos", "ptts_proximos", "resumo_ufs")
delegar(Store, "_operadoras", "_display_name_for_cnpj", "_load_socios_grupos", "acessos_movel_municipio_index", "acessos_municipio_index", "cnpj_asns_index", "empresas_relacionadas", "grupo_prefixos_geo", "grupos_societarios_overview", "operadora_index", "operadora_movel_index", "outorgas_flags_for_cnpj", "peeringdb_contacts_for_asn", "rdap_contatos_for_asn", "socios_grupos_index")
delegar(Store, "_asns", "announced_starts", "asn_coords", "asn_ixp_peers", "asn_names", "asn_paths", "bgp_stability_por_asn", "bgp_stability_resumo", "nomes_asns", "origin_by_prefix")
delegar(Store, "_mapas", "_pix_features", "asns_overview_map", "geo_map", "geo_map_prefixos_agregado", "geo_map_arquivo", "geo_map_filtrado", "map_query", "pix_map")
delegar(Store, "_geolocalizacao", "_ixp_city_coords", "_ixp_geo_prefixes", "_ixp_origin_asns_from_routes", "_load_ixp_members", "_load_ixp_prefix_set", "_load_origin_prefixes", "asn_geo", "ixp_geo")
delegar(Store, "_hilbert", "_norm_dir", "_prefixes_to_density16", "_read_json_gz", "_space24", "_space48", "asn_member_ixps", "hilbert_v4", "hilbert_v4_detail", "hilbert_v6", "ixp_origin_paths")
delegar(Store, "_ixps", "ixp_assinantes", "ixp_hilbert_v4", "ixp_hilbert_v4_detail", "ixp_hilbert_v6", "ixp_peers_stats")
delegar(Store, "_bgp", "aquecer_estabilidade", "bgp_stability", "bgp_stability_asn", "bgp_stability_datas_semanais", "bgp_stability_deep", "bgp_stability_historico_resumo", "bgp_stability_history", "bgp_stability_visao_geral")
delegar(Store, "_consultas", "_load_geo_orgs", "colunar", "query", "query_schema", "query_table", "resolve_operator")
delegar_como(Store, "_docs", {"summary": "summary", "manifest": "manifest", "external_ixp_index": "external_ixp_index", "cdn_presence": "cdns", "routing_analysis": "routing_analysis", "ixp_index": "ixp_index", "asn_index": "asn_index"})
delegar_como(Store, "_sici", {"_load_sici": "dados", "_load_sici_municipios": "municipios_doc", "sici_meta": "meta", "sici_for_cnpj": "for_cnpj", "sici_for_asn": "for_asn", "sici_cnpj_for_asn": "cnpj_for_asn", "sici_serie": "serie", "sici_serie_total": "serie_total", "sici_divergencia": "divergencia", "sici_divergencias": "divergencias", "sici_municipio": "municipio", "sici_municipios": "municipios"})
delegar_como(Store, "_sici_movel", {"_load_sici_movel": "dados", "_load_sici_movel_municipios": "municipios_doc", "sici_movel_meta": "meta", "sici_movel_for_cnpj": "for_cnpj", "sici_movel_for_asn": "for_asn", "sici_movel_cnpj_for_asn": "cnpj_for_asn", "sici_movel_serie": "serie", "sici_movel_serie_total": "serie_total", "sici_movel_municipio": "municipio", "sici_movel_municipios": "municipios"})
