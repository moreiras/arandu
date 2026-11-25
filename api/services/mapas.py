# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Mapas e geolocalização: camadas GeoJSON, geo de IXPs e de ASes (mmdb), PIX, recorte do Mapa Explorer.

Serviço sobre o `Store`: guarda os caches e a lógica dos mapas; o que lê de outros artefatos (índices, SICI, rotas) pede ao `Store`
por `__getattr__`, então o `Store` segue sendo a fachada e a única fonte desses dados. O `Store` delega aqui os métodos públicos.
"""
from __future__ import annotations

import gzip
import json
import threading
from ipaddress import ip_network
from pathlib import Path
from typing import Optional

from api import store as _store_mod        # `_store_mod._maxminddb`/`_store_mod._yaml` lidos aqui em tempo de chamada (os testes os substituem)
from api.geo import haversine_km
from core import layout
from api.store import (
    _MMDB_UNINIT, _SafeLRU, _env_int, _extract_geo, _first_ip, _log, _normalize_city, _slash20_blocks,
)


class MapasService:
    def __init__(self, store):
        self._s = store
        self._geo_maps: dict[str, dict[str, Optional[dict]]] = {}
        self._geo_grande_lock = threading.Lock()
        # Mapa Explorer: recorte de ASes (matched_asns) por hash de filter/near/near_prefixes/near_ix. O front dispara uma
        # consulta por camada com o mesmo recorte, e as consultas paralelas reaproveitam o mesmo cálculo.
        self._map_recorte_cache: _SafeLRU = _SafeLRU(maxsize=_env_int("STORE_MAP_RECORTE_LRU", 32))

    def __getattr__(self, nome):
        # só chega aqui o que o serviço não define: dados e leituras que continuam do Store
        if nome == "_s":
            raise AttributeError(nome)
        return getattr(self._s, nome)

    def _camada(self, date_str: str, layer: str) -> Path:
        """Arquivo de maps/{layer}.geojson: no snapshot ou, se compactado (layout 2), em `_shared/` (`core/layout.py`)."""
        pub = self._pub(date_str)
        return layout.caminho(pub, f"maps/{layer}.geojson") or pub / "maps" / f"{layer}.geojson"

    def geo_map(self, date_str: str, layer: str) -> Optional[dict]:
        """Carrega maps/{layer}.geojson (layer = 'asns' ou 'prefixes'). Cacheado por data."""
        path = self._camada(date_str, layer)
        if self._camada_grande(path):
            # global_prefixes (~100 MB) e ibge_rodovias (~135 MB) viram 1–2 GB de objetos Python; guardados por data, estouram o
            # limite do container (OOM). Lê-se sob demanda, um por vez, e solta-se; quem só repassa o
            # arquivo (rota /map/rodovias sem filtro) nem passa por aqui: usa `geo_map_arquivo`.
            with self._geo_grande_lock:
                return self._read_json(path)
        if date_str not in self._geo_maps:
            self._geo_maps[date_str] = {}
        if layer not in self._geo_maps[date_str]:
            self._geo_maps[date_str][layer] = self._read_json(path)
        return self._geo_maps[date_str][layer]

    def geo_map_prefixos_agregado(self, date_str: str) -> Optional[dict]:
        """`maps/prefixes.geojson` agregado por (ASN, versão IP, município), sem o prefixo nem a posição individual.
        É o que as rotas e as camadas públicas devolvem; o cálculo interno usa `geo_map(date, "prefixes")`. Guarda as 2 últimas datas."""
        from core.geoip import agrega_prefixos

        agregados = self.__dict__.setdefault("_geo_prefixos_agregado", {})
        if date_str not in agregados:
            geojson = self.geo_map(date_str, "prefixes")
            if geojson is None:
                return None
            while len(agregados) >= 2:
                agregados.pop(next(iter(agregados)))
            agregados[date_str] = {**{k: v for k, v in geojson.items() if k != "features"},
                                   "features": agrega_prefixos(geojson.get("features", []))}
        return agregados[date_str]

    #: acima disto a camada não fica em memória (ver `geo_map`)
    GEO_CAMADA_GRANDE_BYTES = 32 * 1024 * 1024

    def _camada_grande(self, path: Path) -> bool:
        try:
            return path.stat().st_size > self.GEO_CAMADA_GRANDE_BYTES
        except OSError:
            return False

    def geo_map_filtrado(self, date_str: str, layer: str, aceita) -> Optional[dict]:
        """FeatureCollection de maps/{layer}.geojson só com as feições que `aceita(feature)` aprova.

        Decodifica uma feição por vez (`raw_decode`) e descarta as recusadas na hora: o pico é o texto do arquivo (~135 MB) e não os
        ~2 GB de objetos de um `json.loads` inteiro. Um arquivo por vez (lock). Nada fica em cache."""
        path = self._camada(date_str, layer)
        if not path.exists():
            return None
        with self._geo_grande_lock:
            try:
                texto = path.read_text(encoding="utf-8")
                chave = texto.index('"features"')
                pos = texto.index("[", chave) + 1
                dec = json.JSONDecoder()
                escolhidas: list = []
                n = len(texto)
                while True:
                    while pos < n and texto[pos] in " \t\r\n,":
                        pos += 1
                    if pos >= n or texto[pos] == "]":
                        break
                    feicao, pos = dec.raw_decode(texto, pos)
                    if aceita(feicao):
                        escolhidas.append(feicao)
                meta = json.loads(texto[:chave] + '"features":[]' + texto[pos + 1:])
            except Exception:  # noqa: BLE001 — arquivo ilegível = camada indisponível, como no `_read_json`
                return None
            finally:
                texto = ""
        return {**meta, "features": escolhidas}

    def geo_map_arquivo(self, date_str: str, layer: str) -> Optional[Path]:
        """Caminho de maps/{layer}.geojson para repassar o arquivo sem parsear (None se não existe)."""
        path = self._camada(date_str, layer)
        return path if path.exists() else None

    def asns_overview_map(self, date_str: str) -> Optional[dict]:
        """GeoJSON da home: ASNs BR com visibilidade FT + PIX de PTTs."""
        geo = self.geo_map(date_str, "asns")
        if geo is None:
            return None

        asn_lkp = self.asn_map(date_str)

        features: list[dict] = []
        for f in geo.get("features", []):
            props = f.get("properties") or {}
            asn = props.get("asn")
            row = asn_lkp.get(asn)
            if row is None or not row.get("is_br"):
                continue
            v4 = (row.get("global_prefixes_v4_count") or 0) > 0
            v6 = (row.get("global_prefixes_v6_count") or 0) > 0
            if v4 and v6:
                vis = "both"
            elif v4:
                vis = "v4_only"
            elif v6:
                vis = "v6_only"
            else:
                vis = "none"
            features.append({**f, "properties": {**props, "role": "asn", "visibility": vis}})

        features.extend(self._pix_features(date_str))
        return {"type": "FeatureCollection", "features": features, "snapshot_date": date_str}

    def _pix_features(self, date_str: str) -> list[dict]:
        """Features GeoJSON dos PIX (PTTs) do IX.br com lat/lon conhecidos."""
        pix_cfg = self._s._load_pix_config()
        ixp_lkp = {e["code"]: e for e in self.ixp_index(date_str)}
        feats: list[dict] = []
        for code, pix_list in sorted(pix_cfg.items()):
            ixp_name = ixp_lkp.get(code, {}).get("name", code.upper())
            for pix in pix_list:
                feats.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [pix["lon"], pix["lat"]]},
                    "properties": {
                        "role": "pix",
                        "ixp_code": code,
                        "name": pix["name"],
                        "ixp_name": ixp_name,
                    },
                })
        return feats

    def pix_map(self, date_str: str) -> dict:
        """GeoJSON apenas com os PIX (PTTs) do IX.br geolocalizados."""
        return {
            "type": "FeatureCollection",
            "features": self._pix_features(date_str),
            "snapshot_date": date_str,
        }

    # -------------------------------------------------------------------------
    # Mapa Explorer — consulta composável com filtro booleano
    # -------------------------------------------------------------------------

    _VALID_MAP_LAYERS = frozenset({
        "asns_geo", "prefixes_v4", "prefixes_v6", "pix",
        "prefixos_ix_v4", "prefixos_ix_v6",
        "asns_ix_direct", "asns_ix_origin",
        "scms", "outorgas_scm",
    })
    _VALID_SCM_MODES  = frozenset({"todas", "com_asn", "sem_asn"})
    # Camadas cujo conteúdo depende do recorte de ASes (matched_asns).
    _RECORTE_LAYERS   = frozenset({
        "asns_geo", "asns_ix_direct", "asns_ix_origin",
        "prefixes_v4", "prefixes_v6", "outorgas_scm",
    })
    _VALID_COLOR_BY   = frozenset({"solid", "visibility", "rpki", "aspa", "porte", "pct_v6", "outorga"})

    def map_query(self, date_str: str, body: dict) -> dict:
        """GeoJSON composável para o Mapa Explorer.

        Parâmetros do body (todos opcionais):

        ``filter``
            Filtro booleano sobre a collection ``asns`` (DSL padrão do sistema:
            ``and / or / not``). Campos disponíveis: os mesmos de
            ``POST /query/asns``. Exemplo::

                {"and": [
                    {"field": "has_rpki",  "op": "eq",  "value": false},
                    {"field": "ixps_sessao_rs", "op": "contains", "value": "sp"}
                ]}

        ``near``
            Conveniência geográfica sobre a **sede** do AS (CNPJ → Nominatim).
            Aceita ``{"ixp": "mao", "radius_km": 80}`` ou
            ``{"place": "Palmas", "radius_km": 300}`` ou
            ``{"point": [lat, lon], "radius_km": N}``.
            É aplicado como AND com o filtro principal.

        ``near_prefixes``
            Mesma sintaxe de ``near``, mas filtra ASes cujos **prefixos
            geolocalizados** (maps/prefixes.geojson) estejam dentro do raio —
            em vez da sede.

        ``layers``
            Lista de camadas a incluir no GeoJSON retornado.
            Valores válidos: ``asns_geo``, ``prefixes_v4``, ``prefixes_v6``, ``pix``,
            ``prefixos_ix_v4``, ``prefixos_ix_v6``.
            Default: ``["asns_geo", "pix"]``.

        ``color_by``
            Atributo de cor para a camada ``asns_geo``.
            Valores: ``visibility`` (default), ``rpki``, ``aspa``, ``porte``, ``pct_v6``.

        ``ix_code``
            Código do PTT do IX.br (ex: ``"sp"``, ``"rj"``, ``"mao"``).
            Obrigatório quando ``layers`` inclui ``prefixos_ix_v4`` ou ``prefixos_ix_v6``.
            Essas camadas mostram todos os prefixos observados no looking glass do PTT,
            geolocalizados pela base DB-IP City Lite — independente do filtro de ASes, a menos
            que ``ix_apply_filter`` seja verdadeiro.

        ``ix_apply_filter``
            Se verdadeiro e houver recorte (filter/near/near_prefixes/near_ix),
            mantém só os prefixos do PTT com alguma origem no recorte.

        ``scm_mode``
            Para a camada ``outorgas_scm``: ``todas`` (default), ``com_asn`` ou ``sem_asn``.

        Retorna um FeatureCollection com propriedade ``layer`` em cada feature.
        ``matched_asns`` é ``None`` quando nenhuma camada pedida depende do recorte.
        """
        from api import query as _q

        body = dict(body or {})
        raw_layers       = body.pop("layers",              ["asns_geo", "pix"])
        color_by         = body.pop("color_by",           "visibility")
        near_pfx_spec    = body.pop("near_prefixes",      None)
        near_spec        = body.pop("near",               None)
        near_ix_spec     = body.pop("near_ix",            None)
        ix_code          = body.pop("ix_code",            None)
        ix_afi_raw       = body.pop("ix_afi",             "v4") or "v4"
        ix_afi           = "v6" if str(ix_afi_raw).lower() == "v6" else "v4"
        ix_exclude_raw   = body.pop("ix_exclude_asns",    None) or []
        ix_include_raw   = body.pop("ix_include_asns",    None) or []
        ix_apply_filter  = bool(body.pop("ix_apply_filter", False))
        scm_mode         = body.pop("scm_mode",           "todas") or "todas"
        flt              = body.get("filter")

        def _parse_asn_list(lst) -> Optional[frozenset]:
            if not lst:
                return None
            items = [int(a) for a in lst if str(a).strip().isdigit() or isinstance(a, int)]
            return frozenset(items) if items else None

        ix_exclude_asns = _parse_asn_list(ix_exclude_raw)
        ix_include_asns = _parse_asn_list(ix_include_raw)

        # Validações rápidas dos enums do endpoint
        layers = set(raw_layers)
        unknown_layers = layers - self._VALID_MAP_LAYERS
        if unknown_layers:
            raise _q.QueryError(
                f"layer(s) inválido(s): {sorted(unknown_layers)}. "
                f"Válidos: {sorted(self._VALID_MAP_LAYERS)}"
            )
        if color_by not in self._VALID_COLOR_BY:
            raise _q.QueryError(
                f"color_by '{color_by}' inválido. "
                f"Válidos: {sorted(self._VALID_COLOR_BY)}"
            )
        if scm_mode not in self._VALID_SCM_MODES:
            raise _q.QueryError(
                f"scm_mode '{scm_mode}' inválido. Válidos: {sorted(self._VALID_SCM_MODES)}"
            )
        ix_prefix_layers = layers & {"prefixos_ix_v4", "prefixos_ix_v6"}
        ix_as_layers     = layers & {"asns_ix_direct", "asns_ix_origin"}
        if (ix_prefix_layers | ix_as_layers) and not ix_code:
            raise _q.QueryError(
                f"layer(s) {sorted(ix_prefix_layers | ix_as_layers)} requerem 'ix_code' (código do PTT, ex: 'sp')"
            )

        needs_recorte = bool(layers & self._RECORTE_LAYERS) or (
            ix_apply_filter and bool(ix_prefix_layers)
        )
        has_recorte = any(x is not None for x in (flt, near_spec, near_pfx_spec, near_ix_spec))
        if needs_recorte:
            matched_asns, asn_row_map = self._map_recorte(
                date_str, flt, near_spec, near_pfx_spec, near_ix_spec,
            )
        else:
            matched_asns, asn_row_map = frozenset(), {}
        # Mapa completo asn → org (cnpj/nome) para enriquecer prefixos com a
        # origem (independe do filtro: prefixos do PTT mostram qualquer origem).
        asn_org_map: dict[int, dict] = self._map_asn_rows(date_str)[1]

        features: list[dict] = []

        # Cache local — evita chamadas repetidas a geo_map nas camadas de ASes
        _asn_geo_fc_cache: Optional[dict] = None
        def _asn_geo_fc() -> dict:
            nonlocal _asn_geo_fc_cache
            if _asn_geo_fc_cache is None:
                _asn_geo_fc_cache = self.geo_map(date_str, "asns") or {}
            return _asn_geo_fc_cache

        # --- Camada: asns_geo -----------------------------------------------------
        if "asns_geo" in layers:
            for f in _asn_geo_fc().get("features", []):
                asn = (f.get("properties") or {}).get("asn")
                if asn not in matched_asns:
                    continue
                row = asn_row_map.get(asn, {})
                props = {**(f.get("properties") or {}), "layer": "asns_geo"}
                cv = self._map_color_value(row, color_by)
                if cv is not None:
                    props["color_value"] = cv
                props.update(self._asn_export_props(row))
                features.append({**f, "properties": props})

        # --- Camada: asns_ix_direct -----------------------------------------------
        # ASes do cadastro do PTT (ixps_membro contains ix_code), interseção
        # com os ASes já filtrados pelo bloco builder (matched_rows).
        if "asns_ix_direct" in layers:
            code_low = ix_code.lower()
            for f in _asn_geo_fc().get("features", []):
                asn = (f.get("properties") or {}).get("asn")
                if asn not in matched_asns:
                    continue
                row = asn_row_map.get(asn, {})
                if code_low not in (row.get("ixps_membro") or []):
                    continue
                props = {**(f.get("properties") or {}), "layer": "asns_ix_direct"}
                cv = self._map_color_value(row, color_by)
                if cv is not None:
                    props["color_value"] = cv
                props.update(self._asn_export_props(row))
                features.append({**f, "properties": props})

        # --- Camada: asns_ix_origin -----------------------------------------------
        # ASes que originam prefixos no route table do PTT, filtrados opcionalmente
        # por AS no caminho (ix_exclude_asns / ix_include_asns) e depois interseção
        # com os ASes do bloco builder.
        if "asns_ix_origin" in layers:
            origin_asns = self._ixp_origin_asns_from_routes(
                date_str, ix_code.lower(), ix_afi,
                ix_exclude_asns or None, ix_include_asns or None,
            )
            for f in _asn_geo_fc().get("features", []):
                asn = (f.get("properties") or {}).get("asn")
                if asn not in matched_asns or asn not in origin_asns:
                    continue
                row = asn_row_map.get(asn, {})
                props = {**(f.get("properties") or {}), "layer": "asns_ix_origin"}
                cv = self._map_color_value(row, color_by)
                if cv is not None:
                    props["color_value"] = cv
                props.update(self._asn_export_props(row))
                features.append({**f, "properties": props})

        # --- Camadas: prefixes_v4 / prefixes_v6 -----------------------------------
        need_pfx = layers & {"prefixes_v4", "prefixes_v6"}
        if need_pfx and matched_asns:
            pfx_fc = self.geo_map_prefixos_agregado(date_str) or {}
            for f in pfx_fc.get("features", []):
                props = f.get("properties") or {}
                ver  = props.get("ip_version")
                asn  = props.get("origin_asn")
                if asn not in matched_asns:
                    continue
                lname = f"prefixes_v{ver}"
                if lname not in need_pfx:
                    continue
                org = asn_org_map.get(asn) or {}
                features.append({**f, "properties": {
                    **props, "layer": lname,
                    "origin_cnpj": org.get("cnpj"),
                    "origin_name": org.get("name"),
                }})

        # --- Camada: pix (sempre completa, sem filtro de AS) ----------------------
        if "pix" in layers:
            for pf in self._pix_features(date_str):
                features.append({**pf, "properties": {**(pf.get("properties") or {}), "layer": "pix"}})

        # --- Camadas: prefixos_ix_v4 / prefixos_ix_v6 ----------------------------
        # Prefixos do looking glass do PTT, geolocalizados via mmdb.
        # Independente do filtro de ASes; opcionalmente filtrados por AS no caminho.
        for lname in ("prefixos_ix_v4", "prefixos_ix_v6"):
            if lname not in layers:
                continue
            afi = "v4" if lname == "prefixos_ix_v4" else "v6"
            # A chave de cache inclui os filtros de AS para não misturar resultados.
            cache_key = (
                date_str, ix_code.lower(), f"ix_prefixes_{afi}",
                ix_exclude_asns, ix_include_asns,
            )
            cache_geo = self._s._geolocalizacao._ixp_geo_cache                  # LRU: lê uma vez, sem depender de a entrada continuar lá
            ix_fc = cache_geo.get(cache_key)
            if ix_fc is None:
                ix_fc = self._ixp_geo_prefixes(
                    date_str, ix_code.lower(), afi,
                    exclude_asns=ix_exclude_asns or None,
                    include_asns=ix_include_asns or None,
                )
                if ix_fc is not None:
                    cache_geo[cache_key] = ix_fc
            ix_fc = ix_fc or {}
            for f in ix_fc.get("features", []):
                props = f.get("properties") or {}
                extra: dict = {}
                # CNPJ/nome só quando a origem é única (lista com múltiplos ASes
                # ficaria poluída no tooltip).
                origins = props.get("origin_asns") or []
                if ix_apply_filter and has_recorte and not any(a in matched_asns for a in origins):
                    continue
                if len(origins) == 1:
                    org = asn_org_map.get(origins[0]) or {}
                    extra = {"origin_cnpj": org.get("cnpj"), "origin_name": org.get("name")}
                features.append({**f, "properties": {**props, "layer": lname, **extra}})

        # --- Camada: scms (outorgas SCM SEM ASN) ---------------------------------
        # Operadores licenciados que não estão presentes no BGP (has_asn=false).
        # Independente do filtro de ASes — a interseção AS∩SCM aparece via asns_geo
        # (color_by="outorga"), evitando plotar o mesmo operador duas vezes.
        if "scms" in layers:
            scm_fc = self.scm_geo_map(date_str) or {}
            for f in scm_fc.get("features", []):
                props = f.get("properties") or {}
                if props.get("has_asn"):
                    continue
                features.append({**f, "properties": {**props, "layer": "scms"}})

        # --- Camada: outorgas_scm (todas as outorgas, com e sem ASN) -------------
        # Com ASN: mantida se algum ASN do CNPJ está no recorte. Sem ASN: não é AS,
        # então um filtro por atributos a exclui; com só proximidade, o raio é
        # aplicado à localização da própria outorga.
        if "outorgas_scm" in layers:
            near_geo = near_spec if near_spec is not None else near_pfx_spec
            geo_centers: Optional[list] = None
            geo_radius = 0.0
            if near_geo is not None:
                geo_centers, geo_radius, _ = self.near_centers(date_str, near_geo)
            attr_filter = flt is not None or near_ix_spec is not None
            scm_fc = self.scm_geo_map(date_str) or {}
            for f in scm_fc.get("features", []):
                props = f.get("properties") or {}
                has_asn = bool(props.get("has_asn"))
                if scm_mode == "com_asn" and not has_asn:
                    continue
                if scm_mode == "sem_asn" and has_asn:
                    continue
                if has_asn:
                    if has_recorte and not any(a in matched_asns for a in (props.get("asns") or [])):
                        continue
                elif has_recorte:
                    if attr_filter:
                        continue
                    coords = (f.get("geometry") or {}).get("coordinates") or []
                    if len(coords) < 2 or not any(
                        haversine_km(coords[1], coords[0], c[0], c[1]) <= geo_radius
                        for c in geo_centers or []
                    ):
                        continue
                features.append({**f, "properties": {**props, "layer": "outorgas_scm", "has_asn": has_asn}})

        return {
            "type": "FeatureCollection",
            "features": features,
            "snapshot_date": date_str,
            "matched_asns": len(matched_asns) if needs_recorte else None,
        }

    def _map_asn_rows(self, date_str: str) -> tuple[list[dict], dict[int, dict]]:
        """Linhas de ASes enriquecidas com has_scm (campo virtual p/ filtro/cor) e
        o índice asn → linha. Cópia rasa: não muta os dicts cacheados em query_table."""
        key = ("rows", date_str)
        if key not in self._map_recorte_cache:
            scm_asns = self.scm_asn_set(date_str)
            rows = [{**r, "has_scm": r.get("asn") in scm_asns}
                    for r in self.query_table(date_str, "asns")]
            self._map_recorte_cache[key] = (rows, {r["asn"]: r for r in rows})
        return self._map_recorte_cache[key]

    def _map_recorte(
        self, date_str: str, flt, near_spec, near_pfx_spec, near_ix_spec,
    ) -> tuple[frozenset, dict[int, dict]]:
        """Resolve o recorte de ASes do Mapa Explorer → (matched_asns, asn → linha).

        Cacheado por hash dos parâmetros: o front dispara uma consulta por camada
        com o mesmo recorte, e near_prefixes varre a tabela inteira de prefixos.
        """
        from api import query as _q

        key = ("recorte", date_str, json.dumps(
            [flt, near_spec, near_pfx_spec, near_ix_spec], sort_keys=True, default=str,
        ))
        if key in self._map_recorte_cache:
            return self._map_recorte_cache[key]

        def _parse_asn_list(lst) -> Optional[frozenset]:
            if not lst:
                return None
            items = [int(a) for a in lst if str(a).strip().isdigit() or isinstance(a, int)]
            return frozenset(items) if items else None

        # --- near_ix → ASes origem no route table do PTT, filtrados por caminho ---
        # Exemplo: "ASes originando no SP sem passar pelo AS 6939"
        #   near_ix = {"code": "sp", "afi": "v4", "exclude_asns": [6939]}
        if near_ix_spec is not None:
            ni_code = str(near_ix_spec.get("code") or "").lower()
            ni_afi  = "v4" if str(near_ix_spec.get("afi") or "v4").lower() != "v6" else "v6"
            ni_exc  = _parse_asn_list(near_ix_spec.get("exclude_asns"))
            ni_inc  = _parse_asn_list(near_ix_spec.get("include_asns"))
            if ni_code:
                ni_asns = self._ixp_origin_asns_from_routes(date_str, ni_code, ni_afi, ni_exc, ni_inc)
                asn_pred_ni: dict = {"field": "asn", "op": "in", "value": sorted(ni_asns)}
                flt = {"and": [asn_pred_ni, flt]} if flt else asn_pred_ni

        # --- near_prefixes → injeta "asn in [...]" no filtro ---------------------
        if near_pfx_spec is not None:
            centers, radius, _ = self.near_centers(date_str, near_pfx_spec)
            asns_near_pfx: set[int] = set()
            for row in self.query_table(date_str, "prefixes"):
                lat, lon = row.get("lat"), row.get("lon")
                asn = row.get("origin_asn")
                if lat is None or lon is None or asn is None:
                    continue
                if any(haversine_km(lat, lon, c[0], c[1]) <= radius for c in centers):
                    asns_near_pfx.add(int(asn))
            asn_pred: dict = {"field": "asn", "op": "in", "value": sorted(asns_near_pfx)}
            flt = {"and": [asn_pred, flt]} if flt else asn_pred

        # --- near (sede do AS) → injeta within_radius ----------------------------
        if near_spec is not None:
            centers, radius, _ = self.near_centers(date_str, near_spec)
            wr: dict = {"op": "within_radius", "centers": centers, "radius_km": radius}
            flt = {"and": [wr, flt]} if flt else wr

        all_rows, _ = self._map_asn_rows(date_str)
        if flt is not None:
            _q.validate("asns", {"filter": flt}, all_rows[0] if all_rows else None)

        # Sem paginação — queremos TODOS
        matched_rows = [r for r in all_rows if _q._eval_filter(r, flt)]
        result = (frozenset(r["asn"] for r in matched_rows), {r["asn"]: r for r in matched_rows})
        self._map_recorte_cache[key] = result
        return result

    @staticmethod
    def _asn_export_props(row: dict) -> dict:
        """Campos extras incluídos em features de ASes para exportação CSV."""
        return {
            "has_rpki": row.get("has_rpki"),
            "has_aspa": row.get("has_aspa"),
            "porte": row.get("porte") or "",
            "pct_v6": row.get("pct_v6"),
            "ixps_direct": ",".join(sorted(row.get("ixps_membro") or [])),     # coluna do CSV mantida; o valor é o cadastro de participantes
            "has_scm": bool(row.get("has_scm")),
        }

    @staticmethod
    def _map_color_value(row: dict, color_by: str):
        """Deriva o valor de cor de um AS para o Mapa Explorer."""
        if color_by == "solid":
            return None  # cor fixa no frontend, sem color_value
        if color_by == "visibility":
            v4 = (row.get("global_prefixes_v4_count") or 0) > 0
            v6 = (row.get("global_prefixes_v6_count") or 0) > 0
            if v4 and v6:  return "both"
            if v4:         return "v4_only"
            if v6:         return "v6_only"
            return "none"
        if color_by == "rpki":
            v = row.get("has_rpki")
            if v is True:  return "yes"
            if v is False: return "no"
            return "unknown"
        if color_by == "aspa":
            v = row.get("has_aspa")
            if v is True:  return "yes"
            if v is False: return "no"
            return "unknown"
        if color_by == "porte":
            return row.get("porte") or "unknown"
        if color_by == "pct_v6":
            return row.get("pct_v6")  # número 0–100 ou None
        if color_by == "outorga":
            return "with_scm" if row.get("has_scm") else "without_scm"
        return None

    # -------------------------------------------------------------------------
    # ASN geo map
    # -------------------------------------------------------------------------
