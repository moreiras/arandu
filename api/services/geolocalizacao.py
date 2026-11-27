# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Geolocalização: leitor da base de geolocalização (DB-IP), PIX, geo de IXPs (membros, origens, prefixos) e geo de ASes por camada.

Serviço sobre o `Store`; as camadas e o Mapa Explorer (`api/services/mapas.py`) o usam.
"""
from __future__ import annotations

import gzip
import json
import threading
from ipaddress import ip_network
from pathlib import Path
from typing import Optional

from api import store as _store_mod        # `_maxminddb`/`_yaml` lidos em tempo de chamada (os testes os substituem)
from api.geo import haversine_km
from core import ixp_geo
from core.common import codigo_valido
from api.store import _MMDB_UNINIT, _SafeLRU, _extract_geo, _first_ip, _log, _normalize_city, _slash20_blocks


class GeolocalizacaoService:
    def __init__(self, store):
        self._s = store
        # eram `dict` sem limite, chaveados pelo que o cliente pede (20 mil ASNs inexistentes
        # viraram 20 mil entradas). LRU com teto e sem guardar o resultado vazio.
        self._ixp_geo_cache = _SafeLRU(maxsize=512)                              # (data, ixp, camada): 2 datas × ~40 PTTs × 5 camadas
        self._mmdb: object = _MMDB_UNINIT                                          # leitor lazy; None se indisponível
        self._pix_config: Optional[dict] = _MMDB_UNINIT  # type: ignore[assignment]  # config/pix.yaml, lido uma vez
        self._pix_cadastro: dict = {}                     # contagem de locais do cadastro (com e sem coordenadas), da mesma leitura
        self._asn_geo_cache = _SafeLRU(maxsize=2048)                             # (data, asn, camada) → FeatureCollection
        self._origin_prefixes_cache = _SafeLRU(maxsize=256)                      # "{data}/{ixp}/{afi}" → {asn: [prefixos]}

    def __getattr__(self, nome):
        if nome == "_s":
            raise AttributeError(nome)
        return getattr(self._s, nome)

    def _mmdb_reader(self):
        """Abre o mmdb mais recente. Retorna None se indisponível. Cacheado."""
        if self._mmdb is not _MMDB_UNINIT:
            return self._mmdb
        if _store_mod._maxminddb is None:
            self._mmdb = None
            return None
        # DB-IP City Lite; o GeoLite2 antigo só vale enquanto o novo arquivo não foi baixado.
        mmdb_files = sorted((self.base / "raw" / "dbip").glob("dbip-city-lite-*.mmdb")) or \
            sorted((self.base / "raw" / "geolite2").glob("GeoLite2-City-*.mmdb"))
        if not mmdb_files:
            self._mmdb = None
            return None
        try:
            self._mmdb = _store_mod._maxminddb.open_database(str(mmdb_files[-1]))
            _log.info("mmdb loaded: %s", mmdb_files[-1])
        except Exception as exc:
            _log.warning("mmdb load failed: %s", exc)
            self._mmdb = None
        return self._mmdb

    def _load_ixp_prefix_set(self, date_str: str, code: str, afi: str) -> list[str]:
        """Carrega normalized/{date}/{code}/prefix-set-{afi}.json.gz."""
        if not codigo_valido(code):                                  # o código vira nome de pasta
            return []
        path = self.base / "normalized" / date_str / code / f"prefix-set-{afi}.json.gz"
        if not path.exists():
            return []
        try:
            with gzip.open(path) as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def ixp_geo(self, date_str: str, code: str, layer: str) -> Optional[dict]:
        """
        Retorna GeoJSON FeatureCollection para o mapa do IXP.

        layer = asns_members | asns_direct | asns_origin |
                prefixes_v4 | prefixes_v6
        """
        key = (date_str, code, layer)
        guardado = self._ixp_geo_cache.get(key)
        if guardado is not None:
            return guardado

        result = self._compute_ixp_geo(date_str, code, layer)
        if result is not None:
            self._ixp_geo_cache[key] = result
        return result

    def pix_config(self) -> dict:
        """Carrega config/pix.yaml uma vez. Retorna dict {code: [{name, lat, lon}, ...]}."""
        if self._pix_config is not _MMDB_UNINIT:
            return self._pix_config or {}  # type: ignore[return-value]
        if _store_mod._yaml is None:
            self._pix_config = {}
            return {}
        pix_path = Path(__file__).resolve().parents[2] / "config" / "pix.yaml"
        if not pix_path.exists():
            self._pix_config = {}
            return {}
        try:
            cfg = _store_mod._yaml.safe_load(pix_path.read_text(encoding="utf-8")) or {}
            raw = cfg.get("pix") or {}
            # Filtra apenas entradas com lat/lon
            result: dict = {}
            for code, entries in raw.items():
                geolocated = [
                    {"name": e["name"], "lat": e["lat"], "lon": e["lon"]}
                    for e in (entries or [])
                    if e.get("lat") is not None and e.get("lon") is not None
                ]
                if geolocated:
                    result[code] = geolocated
            # PIX sem coordenada fica fora do mapa e da distância ao PTT: avisa em vez de descartar calado
            sem = sorted(f"{code}:{e.get('name')}" for code, entries in raw.items() for e in (entries or [])
                         if e.get("lat") is None or e.get("lon") is None)
            if sem:
                _log.warning("pix.yaml: %d PIX sem coordenada fora do mapa: %s", len(sem), ", ".join(sem))
            self._pix_config = result
            todos = [e for entries in raw.values() for e in (entries or [])]
            self._pix_cadastro = {"locais": len(todos), "com_coordenadas": len(todos) - len(sem), "data_cadastro": str(cfg.get("data_cadastro") or "") or None}
        except Exception as exc:
            _log.warning("failed to load pix.yaml: %s", exc)
            self._pix_config = {}
        return self._pix_config  # type: ignore[return-value]

    def pix_cadastro(self) -> dict:
        """{locais, com_coordenadas, data_cadastro} do `config/pix.yaml` (a mesma leitura de `pix_config`): quantos locais o cadastro tem e quantos entram no mapa."""
        self.pix_config()
        return dict(self._pix_cadastro)

    def _compute_ixp_geo(self, date_str: str, code: str, layer: str) -> Optional[dict]:
        ixp_doc = self.ixp_detail(date_str, code)
        if ixp_doc is None:
            return None

        if layer.startswith("asns_"):
            result = self._ixp_geo_asns(date_str, code, layer, ixp_doc)
        elif layer.startswith("prefixes_"):
            afi = layer.split("_")[1]  # "v4" or "v6"
            result = self._ixp_geo_prefixes(date_str, code, afi)
        else:
            return None

        # PIX do IXP — de config/pix.yaml (se disponível) ou fallback de geo_orgs
        pix_cfg = self._s._load_pix_config()
        if code in pix_cfg:
            result["ixp_pix"] = pix_cfg[code]
        else:
            uf   = ixp_doc.get("uf") or ""
            name = ixp_doc.get("name") or ""
            if uf and name:
                coords = self._ixp_city_coords(date_str, uf, name)
                if coords:
                    result["ixp_pix"] = [{"name": name, "lat": coords["lat"], "lon": coords["lon"]}]

        return result

    def _ixp_city_coords(self, date_str: str, uf: str, name: str) -> Optional[dict]:
        """Calcula lat/lon do IXP a partir da mediana dos ASNs geolocalizados na mesma cidade."""
        path = self.base / "normalized" / date_str / "summary" / "geo_orgs.json.gz"
        if not path.exists():
            return None
        try:
            with gzip.open(path) as f:
                data = json.load(f)
        except Exception:
            return None

        norm_name = _normalize_city(name)
        lats: list[float] = []
        lons: list[float] = []
        for org in data.get("orgs", {}).values():
            if org.get("uf") == uf and _normalize_city(org.get("city") or "") == norm_name:
                lat = org.get("lat")
                lon = org.get("lon")
                if lat is not None and lon is not None:
                    lats.append(float(lat))
                    lons.append(float(lon))

        if not lats:
            return None

        lats.sort()
        lons.sort()
        mid = len(lats) // 2
        return {"lat": lats[mid], "lon": lons[mid]}

    def _load_ixp_members(self, date_str: str, code: str) -> set[int]:
        """Carrega ASNs membros do IX.br a partir de raw/{date}/{code}/ixbr_members.json."""
        if not codigo_valido(code):                                  # o código vira nome de pasta
            return set()
        path = self.base / "raw" / date_str / code / "ixbr_members.json"
        if not path.exists():
            return set()
        try:
            data = json.loads(path.read_bytes())
            return {int(m["asn"]) for m in data.get("members") or [] if m.get("asn")}
        except Exception:
            return set()

    def _ixp_geo_asns(self, date_str: str, code: str, layer: str, ixp_doc: dict) -> dict:
        """Filtra maps/asns.geojson pelos ASNs do IXP conforme camada solicitada."""
        asn_geojson = self.geo_map(date_str, "asns")
        if asn_geojson is None:
            return {"type": "FeatureCollection", "features": []}

        v4 = ixp_doc.get("v4") or {}
        v6 = ixp_doc.get("v6") or {}

        direct_set: set[int] = set()
        if layer == "asns_members":
            asn_set = self._load_ixp_members(date_str, code)
        elif layer == "asns_direct":
            asn_set = (
                set(v4.get("asn_direct") or [])
                | set(v6.get("asn_direct") or [])
            )
        elif layer == "asns_origin":
            norm = self._norm_dir(date_str, code)
            origins_v4 = self._read_json_gz(norm / "origin-prefixes-v4.json.gz") or {}
            origins_v6 = self._read_json_gz(norm / "origin-prefixes-v6.json.gz") or {}
            asn_set = (
                {int(a) for a in origins_v4}
                | {int(a) for a in origins_v6}
            )
            direct_set = (
                set(v4.get("asn_direct") or [])
                | set(v6.get("asn_direct") or [])
            )
        else:
            asn_set = set()

        features = []
        for f in asn_geojson.get("features", []):
            asn = (f.get("properties") or {}).get("asn")
            if asn not in asn_set:
                continue
            if direct_set and asn in direct_set:
                props = {**(f.get("properties") or {}), "is_direct": True}
                features.append({**f, "properties": props})
            else:
                features.append(f)

        return {"type": "FeatureCollection", "features": features}

    def _ixp_routes_parsed(
        self, date_str: str, code: str, afi: str,
    ) -> list[dict]:
        """Carrega e parseia routes-{afi}.json.gz, dedupando prepends no aspath.

        Retorna lista de dicts {prefix, origin_asn, peer_asn} onde:
        - origin_asn = último AS do caminho deduplicado (quem origina o prefixo)
        - peer_asn   = primeiro AS do caminho (quem anuncia diretamente ao route server)
        Cacheado em _origin_paths com chave especial para evitar reprocessamento.
        """
        cache_key = f"__parsed_{date_str}/{code}/{afi}"
        try:
            return self._origin_paths[cache_key]  # type: ignore[return-value]
        except KeyError:
            pass

        result = ixp_geo.rotas(self._read_json_gz(self._norm_dir(date_str, code) / f"routes-{afi}.json.gz"))
        self._origin_paths[cache_key] = result  # type: ignore[assignment]
        return result

    def _ixp_origin_asns_from_routes(
        self, date_str: str, code: str, afi: str,
        exclude_asns: Optional[frozenset] = None,
        include_asns: Optional[frozenset] = None,
    ) -> set[int]:
        """Retorna ASes origem das rotas do PTT, filtrados opcionalmente por AS no caminho.

        Exemplo — "ASes originando no SP sem passar pelo AS 6939":
            exclude_asns={6939}
        """
        result: set[int] = set()
        for r in self._ixp_routes_parsed(date_str, code, afi):
            if exclude_asns and r["aspath_set"] & exclude_asns:
                continue
            if include_asns and not include_asns.issubset(r["aspath_set"]):
                continue
            result.add(r["origin_asn"])
        return result

    def _ixp_geo_prefixes(
        self, date_str: str, code: str, afi: str,
        exclude_asns: Optional[frozenset] = None,
        include_asns: Optional[frozenset] = None,
    ) -> dict:
        """Geolocaliza prefixos do route table do PTT via mmdb, agregando por cidade.

        Carrega sempre as rotas (routes-{afi}.json.gz) para preservar info de origem.
        Cada ponto no resultado inclui:
        - block_count: número de blocos /20 (v4) ou prefixos (v6) no agrupamento
        - origin_asns: lista dos ASes que originam prefixos nesta cidade (até 20)
        - peer_asns:   lista dos ASes que anunciam diretamente ao route server (até 20)

        Fallback para prefix-set se as rotas não existirem (sem info de AS). Sem filtro de AS, lê a camada pré-calculada
        (`maps/ixp_prefixes/`, `core.ixp_geo`) e só calcula quando ela falta.
        """
        if not exclude_asns and not include_asns:
            pronto = ixp_geo.ler(self.base, date_str, code, afi)        # pré-calculado pelo pipeline (`mapas_geo`)
            if pronto is not None:
                return pronto
        reader = self._mmdb_reader()
        if reader is None:
            return {"type": "FeatureCollection", "features": []}
        routes = self._ixp_routes_parsed(date_str, code, afi)
        if routes:
            prefix_info = ixp_geo.prefixos_das_rotas(routes, exclude_asns, include_asns)
        else:
            prefix_info = {p: {"origin_asns": set(), "peer_asns": set()} for p in self._load_ixp_prefix_set(date_str, code, afi)}
        return ixp_geo.geolocalizar(prefix_info, reader, afi)

    def _load_origin_prefixes(self, date_str: str, ixp_code: str, afi: str) -> dict:
        """Carrega e cacheia normalized/{date}/{ixp_code}/origin-prefixes-{afi}.json.gz."""
        key = f"{date_str}/{ixp_code}/{afi}"
        guardado = self._origin_prefixes_cache.get(key)
        if guardado is not None:
            return guardado
        path = self._norm_dir(date_str, ixp_code) / f"origin-prefixes-{afi}.json.gz"
        dados = self._read_json_gz(path) or {}
        if dados:
            self._origin_prefixes_cache[key] = dados
        return dados

    def asn_geo(self, date_str: str, asn: int, layer: str) -> Optional[dict]:
        """GeoJSON FeatureCollection para mapa do ASN. Cacheado por (date, asn, layer)."""
        key = (date_str, asn, layer)
        guardado = self._asn_geo_cache.get(key)
        if guardado is not None:
            return guardado
        result = self._compute_asn_geo(date_str, asn, layer)
        if result is not None:                                   # ASN inexistente não vira entrada
            self._asn_geo_cache[key] = result
        return result

    def _compute_asn_geo(self, date_str: str, asn: int, layer: str) -> Optional[dict]:
        doc = self.asn_detail(date_str, asn)
        if doc is None:
            return None
        afi = "v4" if layer.endswith("v4") else "v6"
        if layer.startswith("fulltable_"):
            return self._asn_geo_fulltable(date_str, doc, afi)
        if layer.startswith("ixp_"):
            return self._asn_geo_ixp(date_str, doc, afi)
        return None

    @staticmethod
    def _geo_agg_add(
        city_agg: dict,
        geo: dict,
        block_count: int,
        role: str,
        extra: Optional[dict] = None,
    ) -> None:
        """Acumula um bloco geocodificado em city_agg[(lat,lon,role)]."""
        key = (round(geo["lat"], 2), round(geo["lon"], 2), role)
        if key not in city_agg:
            city_agg[key] = {
                "lat": geo["lat"], "lon": geo["lon"],
                "city": geo["city"], "uf": geo["uf"], "country": geo["country"],
                "block_count": 0, "role": role,
                **(extra or {}),
            }
        city_agg[key]["block_count"] += block_count

    def _geocode_prefixes_agg(
        self,
        prefixes: list[str],
        afi: str,
        role: str,
        city_agg: dict,
        extra: Optional[dict] = None,
    ) -> None:
        """Geolocaliza lista de prefixos via mmdb e acumula em city_agg."""
        reader = self._mmdb_reader()
        if reader is None:
            return
        for prefix in prefixes:
            try:
                if afi == "v4":
                    blocks = _slash20_blocks(prefix)
                else:
                    ip_network(prefix, strict=False)
                    blocks = [prefix]
            except ValueError:
                continue
            for block in blocks:
                try:
                    record = reader.get(_first_ip(block))
                except Exception:
                    continue
                geo = _extract_geo(record)
                if geo is None:
                    continue
                self._geo_agg_add(city_agg, geo, 1, role, extra)

    @staticmethod
    def _city_agg_to_features(city_agg: dict, block_unit: str) -> list[dict]:
        features = []
        for agg in city_agg.values():
            props: dict = {
                "role": agg["role"],
                "city": agg["city"],
                "uf": agg["uf"],
                "country": agg["country"],
                "block_count": agg["block_count"],
                "block_unit": block_unit,
            }
            for k, v in agg.items():
                if k not in ("lat", "lon", "city", "uf", "country", "block_count", "role"):
                    props[k] = v
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [agg["lon"], agg["lat"]]},
                "properties": props,
            })
        return features

    def _asn_geo_fulltable(self, date_str: str, doc: dict, afi: str) -> dict:
        block_unit = "/20" if afi == "v4" else "prefix"
        city_agg: dict = {}

        # Prefixos próprios, geolocalizados pela base mmdb (DB-IP City Lite)
        own_prefixes: list[str] = doc.get(f"global_prefixes_{afi}") or []
        self._geocode_prefixes_agg(own_prefixes, afi, "own", city_agg)

        # Prefixos de downstreams via maps/prefixes.geojson (BR)
        ip_ver = 4 if afi == "v4" else 6
        downstreams: set = set(doc.get(f"downstreams_global_{afi}") or []) | set(doc.get(f"downstreams_{afi}") or [])
        if downstreams:
            prefixes_gj = self.geo_map(date_str, "prefixes")
            for feat in (prefixes_gj or {}).get("features", []):
                props = feat.get("properties") or {}
                if props.get("ip_version") != ip_ver:
                    continue
                if props.get("origin_asn") not in downstreams:
                    continue
                coords = (feat.get("geometry") or {}).get("coordinates") or [0, 0]
                lon, lat = float(coords[0]), float(coords[1])
                prefix = props.get("prefix", "")
                if afi == "v4":
                    try:
                        cnt = len(_slash20_blocks(prefix))
                    except ValueError:
                        cnt = 1
                else:
                    cnt = 1
                geo = {"lat": lat, "lon": lon, "city": props.get("city", ""), "uf": props.get("uf", ""), "country": props.get("country", "")}
                self._geo_agg_add(city_agg, geo, cnt, "downstream")

        features = self._city_agg_to_features(city_agg, block_unit)
        return {"type": "FeatureCollection", "features": features}

    def _asn_geo_ixp(self, date_str: str, doc: dict, afi: str) -> dict:
        block_unit = "/20" if afi == "v4" else "prefix"
        features: list[dict] = []
        ixp_pix: list[dict] = []
        pix_cfg = self._s._load_pix_config()

        ixp_presence: dict = doc.get("ixp_presence") or {}
        downstreams: set = set(doc.get(f"downstreams_global_{afi}") or []) | set(doc.get(f"downstreams_{afi}") or [])

        for ixp_code, pres_data in ixp_presence.items():
            afi_pres: dict = (pres_data or {}).get(afi) or {}
            if not afi_pres.get("origin"):
                continue
            is_direct = bool(afi_pres.get("direct"))

            # PIX deste IXP
            for pix in pix_cfg.get(ixp_code, []):
                ixp_pix.append({"ixp_code": ixp_code, "name": pix["name"], "lat": pix["lat"], "lon": pix["lon"]})

            # Prefixos próprios do ASN neste IXP
            own_prefixes: list[str] = afi_pres.get("prefixes") or []
            city_agg: dict = {}
            self._geocode_prefixes_agg(own_prefixes, afi, "own", city_agg, {"direct": is_direct, "ixp_code": ixp_code})
            features.extend(self._city_agg_to_features(city_agg, block_unit))

            # Prefixos de downstreams — apenas em IXPs diretos
            if is_direct and downstreams:
                origins = self._load_origin_prefixes(date_str, ixp_code, afi)
                ds_agg: dict = {}
                for asn_str, ds_prefixes in origins.items():
                    try:
                        ds_asn = int(asn_str)
                    except ValueError:
                        continue
                    if ds_asn not in downstreams:
                        continue
                    self._geocode_prefixes_agg(
                        ds_prefixes or [], afi, "downstream", ds_agg,
                        {"direct": True, "ixp_code": ixp_code},
                    )
                features.extend(self._city_agg_to_features(ds_agg, block_unit))

        result: dict = {"type": "FeatureCollection", "features": features}
        if ixp_pix:
            result["ixp_pix"] = ixp_pix
        return result
