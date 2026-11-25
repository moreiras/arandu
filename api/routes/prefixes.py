# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoints de prefixos: GET /prefixes, GET /prefixes/{prefix} e GET /prefixes/lookup.

Serve os prefixos IPv6/IPv4 alocados ao Brasil (Registro.br) com UF e país; o detalhe também abre rotas observadas fora das
alocações e separa o detentor (Registro.br) da origem observada (tabela global, route servers do IX.br). A posição individual (latitude, longitude e
cidade) de um prefixo ou IP não sai da API: ela só é usada por dentro, e o mapa traz posição agregada.
"""
from __future__ import annotations

import ipaddress
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.privacidade import geo_org_publico
from api.store import Store
from core.geoip import sem_posicao

router = APIRouter()


def _features_to_items(features: list[dict]) -> list[dict]:
    """Converte features GeoJSON em dicts planos para listagem, sem a posição individual do prefixo."""
    return [sem_posicao(f.get("properties") or {}) for f in features]


@router.get(
    "/prefixes",
    summary="Listar prefixos BR geolocalizados (paginado)",
    description="""
Retorna a lista paginada de prefixos BR declarados no Registro.br com a UF segundo a
base de geolocalização (DB-IP City Lite). Requer que a etapa `prefix_geo` tenha sido executada para o snapshot.

Campos retornados: `prefix`, `ip_version`, `origin_asn` (AS a que o Registro.br associa o prefixo, não a origem observada), `uf`, `country`,
`geo_confidence`, `geo_source`. Latitude, longitude e cidade por prefixo não são servidas.

Use `?ip_version=4` ou `?ip_version=6` para filtrar por versão.
Use `?uf=SP` para filtrar por estado.
""",
)
def list_prefixes(
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
    page: int = Query(1, ge=1, description="Número da página (começa em 1)"),
    limit: int = Query(100, ge=1, le=1000, description="Itens por página (máx 1000)"),
    ip_version: Optional[int] = Query(
        None,
        description="Filtrar por versão IP (4 ou 6).",
        ge=4,
        le=6,
    ),
    uf: Optional[str] = Query(
        None,
        description="Filtrar por UF (sigla de dois caracteres, ex: SP, RJ).",
        min_length=2,
        max_length=2,
    ),
    origin_asn: Optional[int] = Query(
        None,
        description="Filtrar pelo AS a que o Registro.br associa o prefixo (detentor; não é a origem observada).",
    ),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    geojson = store.geo_map(date_str, "prefixes")
    if geojson is None:
        raise HTTPException(404, "Dados de geolocalização de prefixos não disponíveis para este snapshot")

    features = geojson.get("features", [])

    if ip_version is not None:
        features = [
            f for f in features
            if (f.get("properties") or {}).get("ip_version") == ip_version
        ]
    if uf is not None:
        uf_upper = uf.upper()
        features = [
            f for f in features
            if (f.get("properties") or {}).get("uf", "").upper() == uf_upper
        ]
    if origin_asn is not None:
        features = [
            f for f in features
            if (f.get("properties") or {}).get("origin_asn") == origin_asn
        ]

    total = len(features)
    start = (page - 1) * limit
    page_features = features[start: start + limit]

    return {
        "snapshot_date": date_str,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 0,
        "items": _features_to_items(page_features),
    }


_INDICE_LPM: dict[str, dict] = {}


def _indice_lpm(store: Store, date_str: str) -> Optional[dict]:
    """{(versão, tamanho): {rede como inteiro: properties}} dos prefixos geolocalizados da data; guarda só as 2 últimas datas.

    Os valores são as próprias `properties` do GeoJSON (sem cópia): a busca exata e o longest-prefix match saem do mesmo índice."""
    if date_str in _INDICE_LPM:
        return _INDICE_LPM[date_str]
    geojson = store.geo_map(date_str, "prefixes")
    if geojson is None:
        return None
    indice: dict[tuple[int, int], dict[int, dict]] = {}
    for f in geojson.get("features", []):
        props = f.get("properties") or {}
        try:
            rede = ipaddress.ip_network(props.get("prefix"), strict=False)
        except (TypeError, ValueError):
            continue
        indice.setdefault((rede.version, rede.prefixlen), {})[int(rede.network_address)] = props
    while len(_INDICE_LPM) >= 2:
        _INDICE_LPM.pop(next(iter(_INDICE_LPM)))
    _INDICE_LPM[date_str] = indice
    return indice


def _lpm(indice: dict, addr, ate: int) -> Optional[dict]:
    """`properties` da alocação mais específica, de tamanho até `ate`, que contém `addr`; None se nenhuma."""
    bits = addr.max_prefixlen
    n = int(addr)
    for tam in range(ate, -1, -1):
        nivel = indice.get((addr.version, tam))
        if not nivel:
            continue
        props = nivel.get(n >> (bits - tam) << (bits - tam))
        if props:
            return props
    return None


def prefixo_mais_especifico(store: Store, date_str: str, addr) -> str:
    """O prefixo BR geolocalizado mais específico que contém `addr` (longest-prefix match). Levanta `HTTPException` 404 se não há."""
    indice = _indice_lpm(store, date_str)
    if indice is None:
        raise HTTPException(404, "Dados de geolocalização de prefixos não disponíveis para este snapshot")
    props = _lpm(indice, addr, addr.max_prefixlen)
    if props:
        return props["prefix"]
    raise HTTPException(404, f"Nenhum prefixo conhecido contém {addr} no snapshot '{date_str}'")


class PrefixoInvalido(ValueError):
    """A grafia não é um prefixo CIDR (422 na REST)."""


class PrefixoAusente(LookupError):
    """Nem alocação do Registro.br nem rota observada no snapshot (404 na REST)."""


def canonizar(texto: str):
    """`ip_network` na forma canônica (bits de host zerados, IPv6 comprimido). Exige a barra: endereço solto vai para `lookup`."""
    t = (texto or "").strip()
    if "/" not in t:
        raise PrefixoInvalido(f"Grafia não reconhecida: '{texto}' não é um prefixo CIDR (endereço IP solto: use /prefixes/lookup?ip=).")
    try:
        return ipaddress.ip_network(t, strict=False)
    except ValueError:
        raise PrefixoInvalido(f"Grafia não reconhecida: '{texto}' não é um prefixo CIDR válido.")


def _observado_nos_rs(store: Store, date_str: str, canon: str) -> Optional[int]:
    """Origem do prefixo nos route servers do IX.br (`global_prefixes`), só pela tabela colunar: sem ela (snapshot antigo) a
    consulta cairia no GeoJSON, segundos por pedido, e a camada é pulada."""
    if store.colunar(date_str, "global_prefixes") is None:
        return None
    r = store.query(date_str, "global_prefixes", {"filter": {"field": "prefix", "op": "eq", "value": canon},
                                                  "select": ["prefix", "origin_asn"], "limit": 1})
    itens = r.get("items") or []
    asn = itens[0].get("origin_asn") if itens else None
    return int(asn) if asn is not None else None


def detalhe_prefixo(store: Store, date_str: str, texto: str) -> dict:
    """Detalhe de um prefixo, o mesmo para a REST (`GET /prefixes/{prefix}`) e o MCP (`rota_prefixo`).

    Separa o **detentor** (AS a que o Registro.br associa a alocação igual ao prefixo ou que o contém) da **origem observada**
    (último AS do caminho na tabela global coletada; se o prefixo não está nela, a origem vista nos route servers do IX.br).
    O RPKI só é avaliado para o par efetivamente anunciado. Levanta `PrefixoInvalido` ou `PrefixoAusente`."""
    rede = canonizar(texto)
    canon = str(rede)
    indice = _indice_lpm(store, date_str)
    exata = None
    alocacao = None
    if indice is not None:
        exata = (indice.get((rede.version, rede.prefixlen)) or {}).get(int(rede.network_address))
        alocacao = exata or (_lpm(indice, rede.network_address, rede.prefixlen - 1) if rede.prefixlen else None)

    origem = store.origin_by_prefix(date_str, f"v{rede.version}").get(canon)
    fonte = "tabela_global" if origem is not None else None
    if origem is None:
        origem = _observado_nos_rs(store, date_str, canon)
        fonte = "route_servers_ixbr" if origem is not None else None

    if alocacao is None and origem is None:
        raise PrefixoAusente(
            f"{canon} não consta das alocações do Registro.br nem da tabela global ou dos route servers do IX.br coletados no "
            f"snapshot '{date_str}'; isso não prova que não seja anunciado em outro ponto da Internet.")

    if indice is None:
        escopo = "registro_br_indisponivel"
    elif exata is not None:
        escopo = "alocacao_registro_br"
    elif alocacao is not None:
        escopo = "rota_dentro_de_alocacao"
    else:
        escopo = "fora_do_registro_br"

    registro_asn = (alocacao or {}).get("origin_asn")
    nomes = store.asn_names(date_str) or {}
    geo = sem_posicao(exata) if exata is not None else {}
    result = {
        "prefix": canon,
        "ip_version": rede.version,
        "escopo": escopo,
        "alocacao_registro_br": (alocacao or {}).get("prefix"),
        "registro_asn": registro_asn,
        "registro_asn_nome": nomes.get(str(registro_asn)) if registro_asn is not None else None,
        "observed_origin_asn": origem,
        "observed_origin_nome": nomes.get(str(origem)) if origem is not None else None,
        "observed_origin_fonte": fonte,
        "origin_asn": registro_asn,       # depreciado: é o AS do Registro.br (= registro_asn), não a origem observada
        "uf": geo.get("uf"),
        "country": geo.get("country"),
        "geo_confidence": geo.get("geo_confidence"),
        "geo_source": geo.get("geo_source"),
        "rpki_observado": store.rpki_diagnostico(date_str, canon, origem),
        "snapshot_date": date_str,
        "geo_org": None,
    }
    if canon != texto.strip():
        result["prefixo_informado"] = texto.strip()
    if registro_asn is not None:
        asn_doc = store.asn_detail(date_str, int(registro_asn))
        if asn_doc:
            result["geo_org"] = geo_org_publico(asn_doc.get("geo_org"))      # do detentor; sem contato, endereço nem coordenada
    return result


def resumo_do_ip(store: Store, date_str: str, ip: str) -> dict:
    """`GET /prefixes/lookup` e `rota_prefixo(ip=)`: o prefixo do Registro.br mais específico que contém o IP, sem posição."""
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        raise PrefixoInvalido(f"'{ip}' não é um endereço IP válido")
    pref = prefixo_mais_especifico(store, date_str, addr)
    d = detalhe_prefixo(store, date_str, pref)
    return {"prefix": pref, "ip_version": d["ip_version"], "origin_asn": d["origin_asn"], "registro_asn": d["registro_asn"],
            "observed_origin_asn": d["observed_origin_asn"], "snapshot_date": date_str, "consulta": str(addr)}


@router.get(
    "/prefixes/lookup",
    summary="Prefixo mais específico que contém um IP",
    description="""
Dado um endereço IPv6 ou IPv4 (`?ip=200.160.2.3`), devolve o **prefixo mais específico** (longest-prefix match) entre as
alocações do Registro.br do snapshot, com o AS do Registro.br (`registro_asn`; `origin_asn` traz o mesmo valor e está
depreciado) e a origem observada na tabela global (`observed_origin_asn`), mais o campo `consulta`. É uma consulta de
roteamento: não traz posição nenhuma (nem UF), para que a API não funcione como serviço de geolocalização de IP. O detalhe do
prefixo está em `GET /prefixes/{prefix}`. 404 se nenhum prefixo conhecido o contém.
""",
)
def lookup_prefix(
    request: Request,
    ip: str = Query(..., description="Endereço IPv6 ou IPv4 (sem máscara)."),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente."),
) -> dict:
    try:
        ipaddress.ip_address(ip.strip())
    except ValueError:
        raise HTTPException(422, f"'{ip}' não é um endereço IP válido")
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return resumo_do_ip(store, date_str, ip)


@router.get(
    "/prefixes/{prefix:path}",
    summary="Detalhes de um prefixo",
    description="""
Retorna os dados de um prefixo (ex.: `2804::/32` ou `177.75.0.0/20`). Aceita qualquer grafia CIDR válida e responde na forma
canônica (`prefix`; a grafia recebida vem em `prefixo_informado` quando difere): bits de host zerados, IPv6 comprimido.

Abre alocações do Registro.br e também rotas observadas fora delas. Dois papéis, cada um com sua fonte:
- **detentor** (`registro_asn`, `registro_asn_nome`, `alocacao_registro_br`): o AS a que o Registro.br associa a alocação igual
  ao prefixo ou a que o contém;
- **origem observada** (`observed_origin_asn`, `observed_origin_nome`, `observed_origin_fonte`): o último AS do caminho na
  tabela global coletada (`tabela_global`, uma origem por prefixo) ou, se o prefixo não está nela, nos route servers do IX.br
  (`route_servers_ixbr`). Nula quando o prefixo não é anunciado como está neste snapshot.

`escopo`: `alocacao_registro_br`, `rota_dentro_de_alocacao`, `fora_do_registro_br` ou `registro_br_indisponivel`.
`rpki_observado`: validação de origem (RFC 6811) do par prefixo × origem observada, com `estado` (`valid`, `invalid`,
`not_found`; `nao_avaliado` quando não há anúncio), `motivo` (`origem_diferente`, `maxlength_excedido`, `sem_roa`,
`sem_anuncio`) e os VRPs de qualquer AS que cobrem o prefixo (`roas_que_cobrem`, com `autoriza_origem`); nulo sem VRPs no
snapshot. `origin_asn` está depreciado: é o AS do Registro.br (igual a `registro_asn`), não a origem observada.

UF e país (DB-IP City Lite) só para a alocação exata; `geo_org` é do detentor. Latitude, longitude e cidade não são servidas.
422 para grafia não reconhecida; 404 quando o prefixo não está nas alocações nem nas rotas observadas do snapshot.
""",
)
def get_prefix(
    prefix: str,
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    try:
        return detalhe_prefixo(store, date_str, prefix)
    except PrefixoInvalido as exc:
        raise HTTPException(422, str(exc))
    except PrefixoAusente as exc:
        raise HTTPException(404, str(exc))
