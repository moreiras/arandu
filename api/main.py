# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Arandurape — API mínima.

Endpoints:
  GET /health                    — status + último snapshot disponível
  GET /api/v1/snapshots          — lista de snapshots disponíveis
  GET /api/v1/snapshots/{date}   — summary + metadados de um snapshot
  GET /api/v1/ixps               — lista de IXPs (do ixps/index.json)
  GET /api/v1/ixps/{code}        — documento completo de um IXP
  GET /api/v1/asns               — lista paginada de ASNs (do asns/index.json)
  GET /api/v1/asns/{asn}         — documento completo de um ASN
  GET /api/v1/asns/{asn}/geo     — geolocalização de um ASN (org + prefixos)
  GET /api/v1/prefixes           — lista paginada de prefixos BR geolocalizados
  GET /api/v1/prefixes/{prefix}  — detalhes de um prefixo
  GET /api/v1/map/asns           — GeoJSON com ASNs geolocalizados
  GET /api/v1/map/prefixes       — GeoJSON com prefixos BR geolocalizados

Dados servidos diretamente de published/{date}/ — sem banco de dados.

Uso:
  uvicorn api.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import secrets
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.exception_handlers import http_exception_handler as default_http_exception_handler
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.auth.anon_session import (
    load_anon_config,
    peek_limit_reached,
    COOKIE_NAME as ANON_COOKIE_NAME,
    FINGERPRINT_HEADER,
)
from api.auth.config import init_auth_config
from api.auth import access_policy as _politica
from api.auth.access import BLOCK_LOGIN, evaluate_access, limite_anonimo, recent_dates
from api.auth.jwt_utils import verify_token
from api.auth.router import router as auth_router
from api.concurrency import ConcurrencyLimitMiddleware
from api.cache import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_ENTRY_BYTES,
    LatestCacheMiddleware,
    LatestResponseCache,
    prewarm_latest,
    prewarm_perfis,
    prewarm_top_asns,
)
from api import heap
from api.memoria import GuardaMemoria, ligado as memoria_ligada
from api.schemas import HealthResponse
from api.store import Store
from api.usage_log import UsageLogMiddleware
from api.auth.perfil import router as perfil_router
from api.auth.internas import router as internas_router
from api import deprecation
from api.precompressao import PreBrotliMiddleware
from api.routes import meta
from api.routes import limites as limites_routes
from api.routes import documentacao
from api.routes import brasil as brasil_routes
from core.site import SITE
from api.routes import ipv4, regulatorio, prontidao, erbs, cetic, acessos, acessos_movel, asn_geo, asns, bgp_stability, bgp_stability_deep, cdns, external_ixps, grupos, hilbert, historico, ixp_compare, ixp_geo, ixps, map, outorgas, perfis, prefixes, query, rpki, routing_analysis, scms, seac, seguranca, sici_indicadores, sitemap, smp, snapshots, stfc, territorio, route_servers, rs_policy, regiao
from api.routes import ipv4, regulatorio, prontidao, erbs, cetic, acessos, acessos_movel, asn_geo, asns, bgp_stability, bgp_stability_deep, cdns, external_ixps, grupos, hilbert, historico, ixp_compare, ixp_geo, ixps, map, outorgas, perfis, prefixes, query, rpki, routing_analysis, scms, seac, seguranca, sici_indicadores, sitemap, smp, snapshots, stfc, territorio, route_servers, regiao, as2org
from api.routes import ipv4, consumidor, empresas, financiamento, qualidade, regulatorio, prontidao, erbs, cetic, acessos, acessos_movel, asn_geo, asns, bgp_stability, bgp_stability_deep, cdns, external_ixps, grupos, hilbert, historico, ixp_compare, ixp_geo, ixps, map, outorgas, perfis, prefixes, query, rpki, routing_analysis, scms, seac, seguranca, sici_indicadores, sitemap, smp, snapshots, stfc, territorio, route_servers, regiao
from api.routes import transito
from api.routes import ipv4, regulatorio, prontidao, erbs, cetic, acessos, acessos_movel, asn_geo, asns, bgp_stability, bgp_stability_deep, cdns, external_ixps, grupos, hilbert, historico, ixp_compare, ixp_geo, ixps, map, outorgas, perfis, prefixes, query, rpki, routing_analysis, scms, seac, seguranca, sici_indicadores, sitemap, smp, snapshots, stfc, territorio, route_servers, regiao, as2org, instalacoes
from api.routes import bloqueios
from api.routes import radar as radar_routes
from api.routes import contratos as contratos_routes
from api.routes import exposicao as exposicao_routes
from core.common import app_version, data_dir

_log = logging.getLogger("arandurape")


def _configure_app_logging() -> None:
    """Liga os loggers da aplicação (`arandurape.*`, `api.*`) no stderr.

    O uvicorn só configura os próprios loggers; sem isto, `_log.info(...)` do
    projeto (auditoria `contact_access`, `access_decision`) é descartado — o
    handler "last resort" do Python só emite WARNING+. Nível via LOG_LEVEL.
    """
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    for name in ("arandurape", "api"):
        lg = logging.getLogger(name)
        lg.setLevel(level)
        if not lg.handlers:
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
            lg.addHandler(h)
        lg.propagate = False


_configure_app_logging()

# Token para endpoints internos (warmup). Configurado via INTERNAL_API_TOKEN no env.
# Se ausente, o endpoint aceita apenas chamadas loopback (fallback para compatibilidade).
_INTERNAL_TOKEN: str = os.environ.get("INTERNAL_API_TOKEN", "")

_DESCRIPTION = """
API de análise de ASNs e IXPs brasileiros. Combina dados do **IX.br** (Looking Glasses
dos pontos de troca), do **Registro.br** (alocações RIR) e da **tabela de roteamento global**
para produzir métricas de cobertura e presença em IXPs.

## Fontes de dados

| Fonte | O que fornece |
|---|---|
| **IX.br LGs** | Rotas BGP observadas em cada ponto de troca |
| **Registro.br** | Prefixos IPv6/IPv4 atribuídos a ASNs brasileiros |
| **Full table global** | Tabela de roteamento BGP completa (via coletor dedicado) |

## Conceitos

**Snapshot** — conjunto de dados coletados e analisados em uma data específica.
Todos os endpoints aceitam `?date=YYYY-MM-DD`; sem esse parâmetro, usam o snapshot mais recente.

**ASN direto vs. originador** — um AS é *direto* quando aparece no primeiro hop do AS_PATH
(tem sessão com o route server do PTT, vista no looking glass); é *originador* quando seus prefixos são visíveis no IXP,
possivelmente via um upstream.

**Prefixos RIR vs. global** — `rir_prefixes` vêm do Registro.br (fonte autoritativa de alocação);
`global_prefixes` são observados na full table BGP e podem incluir prefixos não declarados
ou omitir prefixos declarados mas não anunciados.

## Pipeline

```
Coleta LGs  →  Parser BGP (bgp_ixp)  →  Métricas IXP e documentos ASN (metricas_ixp_asn)
Coleta registro_br  →  ↗
Full table  →  ↗
```
"""


async def _warmup(store: Store, date_str: str):
    loop = asyncio.get_event_loop()
    # Carrega em background sem bloquear o startup — evita pico de memória na inicialização.
    # As primeiras requisições que precisarem desses índices os carregarão sob demanda (lazy).
    # Devolve o future: o congelamento do heap (api/heap.py) espera o aquecimento terminar.
    return loop.run_in_executor(None, _warmup_sync, store, date_str)


def _warmup_sync(store: Store, date_str: str) -> None:
    """Carrega os índices pesados sequencialmente em uma única thread de background."""
    store.asn_member_ixps(date_str, 0)
    store._load_vrps(date_str)
    if os.environ.get("PREWARM_BUSCA", "1") != "0":          # índice da busca (1.6.x): ~25 s na 1ª vez; sem isso o 1º visitante esperava
        try:
            from api import busca
            busca.indice(store, date_str)
        except Exception as exc:                             # aquecimento nunca derruba a API
            _log.warning("warm-up da busca falhou: %s", exc)
    _log.info("warm-up concluído (%s)", date_str)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from pathlib import Path
    _data_dir = data_dir()
    store = Store(_data_dir)
    app.state.store = store
    app.state.latest_cache = LatestResponseCache(
        store,
        max_bytes=int(os.environ.get("LATEST_CACHE_MAX_BYTES", DEFAULT_MAX_BYTES)),
        max_entry_bytes=int(os.environ.get("LATEST_CACHE_MAX_ENTRY_BYTES", DEFAULT_MAX_ENTRY_BYTES)),
    )
    # Teto de memória (api/memoria.py): datas residentes e guarda perto do limite do contêiner. Sem isto, cada data antiga
    # consultada somava ~1,7 GB que nunca voltava (medido num ambiente de teste em 2026-11-18) e duas levavam a API ao OOM.
    # no crítico da guarda, o cache de respostas prontas (recalculável) é esvaziado antes de se tocar nas bases da data mais recente
    app.state.guarda_memoria = (GuardaMemoria(store, app.state.latest_cache.current_latest, liberar=app.state.latest_cache.esvaziar)
                                if memoria_ligada() else None)
    if app.state.guarda_memoria is not None:
        asyncio.create_task(app.state.guarda_memoria.laco())
    app.state.auth_config = init_auth_config(_data_dir)
    app.state.anon_config = load_anon_config()
    try:
        date_str = store.resolve_date(None)
        if date_str:
            tarefas = [await _warmup(store, date_str)]
            # Pré-materializa o byte-cache do latest em background (não bloqueia startup).
            # PREWARM_LATEST=0 desliga; PREWARM_TOP_ASNS=N muda o tamanho (0 desliga). Servem para medir/ajustar o pico de memória
            # do aquecimento em máquinas pequenas (um ambiente de teste chegou a ~4 GiB só com ele, antes de qualquer visita).
            if os.environ.get("PREWARM_LATEST", "1") != "0":
                tarefas.append(asyncio.create_task(prewarm_latest(app, date_str)))
            # Pré-aquece os ASNs mais acessados (top 1000 por clientes), baixa prioridade.
            n_top = int(os.environ.get("PREWARM_TOP_ASNS", "1000"))
            if n_top > 0:
                tarefas.append(asyncio.create_task(prewarm_top_asns(app, date_str, limit=n_top)))
            # Perfis das páginas de entidade como a interface os pede (com include=): PTTs, UFs e os mais procurados (api/cache.py).
            if os.environ.get("PREWARM_PERFIS", "1") != "0":
                tarefas.append(asyncio.create_task(prewarm_perfis(app, date_str)))
            # Séries horárias de estabilidade BGP das últimas semanas (página do AS, 1.4.2.1): ~5 s por semana na 1ª vez.
            if os.environ.get("PREWARM_ESTABILIDADE", "1") != "0":
                tarefas.append(asyncio.create_task(asyncio.to_thread(store.aquecer_estabilidade, date_str)))
            # O que o aquecimento carregou sai da coleta de lixo completa (pausas de 1 a 2 s; api/heap.py).
            asyncio.create_task(heap.congelar_depois(tarefas, "aquecimento"))
        asyncio.create_task(heap.manter_congelado())
    except Exception as exc:
        _log.warning("warm-up inicial falhou: %s", exc)
    yield


from api.respostas import JSONResponse as JSONComIdentidade  # noqa: E402

app = FastAPI(
    title=SITE.nome,
    description=_DESCRIPTION,
    version=app_version(),
    # o contato é o próprio site; as licenças de cada fonte estão em /fontes.
    contact={"name": SITE.nome, "url": f"{SITE.url}/sobre"},
    license_info={"name": "Dados: licença de cada fonte (ver /fontes)", "url": f"{SITE.url}/fontes"},
    # Swagger servido por api/routes/documentacao.py (sem script embutido, que a CSP bloqueia).
    docs_url=None,
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
    # o nome do site no lugar do nome do software nos textos dos artefatos (api/respostas.py)
    default_response_class=JSONComIdentidade,
)

from core.site import com_identidade  # noqa: E402


def _indice_pessoa_natural():
    """Titulares EI/MEI do `Store` do app (D1, PT-11), para a saída das respostas (`api/respostas.py`); sem `Store` ainda, nada a trocar."""
    store = getattr(app.state, "store", None)
    return store.pessoa_natural_indice() if store is not None and hasattr(store, "pessoa_natural_indice") else None


from api import respostas as _respostas  # noqa: E402

_respostas.provedor_de_indice = _indice_pessoa_natural

_identidade_aplicada = False


def _openapi_com_identidade() -> dict:
    """OpenAPI com o nome do site do `.env` nas descrições; os textos das rotas usam o nome do software ("Arandurapé") como marcador."""
    global _identidade_aplicada
    if not _identidade_aplicada:
        app.openapi_schema = com_identidade(FastAPI.openapi(app))
        _identidade_aplicada = True
    return app.openapi_schema


app.openapi = _openapi_com_identidade  # type: ignore[method-assign]

from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from api.ratelimit import limiter

# Rate limiting (anti-abuso). O middleware aplica o limite global padrão; rotas
# caras/sensíveis reforçam com @limiter.limit(...). Adicionado antes do GZip/CORS
# para que requisições barradas sejam rejeitadas cedo.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


async def _value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


app.add_exception_handler(ValueError, _value_error_handler)


async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
    """`?opcional=1`: "não existe" deixa de ser erro. A página que consulta um serviço que a entidade pode não ter
    (SEAC de uma operadora que só tem SCM) pede assim e recebe 204: o navegador registra todo 4xx no console, mesmo tratado.
    Sem o parâmetro nada muda (404 continua 404, para o MCP e para quem consome a API)."""
    if exc.status_code == 404 and request.query_params.get("opcional") in ("1", "true"):
        return Response(status_code=204, headers={"Cache-Control": "no-store"})
    return await default_http_exception_handler(request, exc)


app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
app.add_middleware(SlowAPIMiddleware)
# Pré-compressão brotli-11 das camadas `?v=`: o mais interno, para ver o corpo antes do GZip.
app.add_middleware(PreBrotliMiddleware, data_dir=data_dir, caminhos=frozenset(map._CAMADAS_ESTATICAS.values()))     # só as camadas estáticas

app.add_middleware(GZipMiddleware, minimum_size=1024)

# CORS: restringe às origens controladas (APP_BASE_URL + dev local).
# Nunca usa "*" — ampliaria superfície de abuso cross-origin.
_CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:4173"]
_APP_BASE = os.environ.get("APP_BASE_URL", "").rstrip("/")
if _APP_BASE and _APP_BASE not in _CORS_ORIGINS:
    _CORS_ORIGINS.append(_APP_BASE)
    # Suporta http:// e https:// se a URL de produção for https.
    if _APP_BASE.startswith("https://"):
        _CORS_ORIGINS.append(_APP_BASE.replace("https://", "http://", 1))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", FINGERPRINT_HEADER, "X-Arandu-Area"],
    expose_headers=["X-Anon-Limit-Reached", "X-Login-Required"],
    allow_credentials=True,
)


# Datas de snapshot existentes (publicadas), reconsultadas no máx. a cada 60 s: o
# `?date=` só vira `immutable` se o snapshot de fato existe (data inventada não
# pode ficar um ano no cache do navegador).
_SNAP_DATES: tuple[float, frozenset[str]] = (0.0, frozenset())


def _existing_snapshot_dates(app_) -> frozenset[str]:
    global _SNAP_DATES
    at, dates = _SNAP_DATES
    now = time.monotonic()
    if now - at >= 60.0:
        store_ = getattr(app_.state, "store", None)
        dates = frozenset(store_.list_snapshots()) if store_ is not None else frozenset()
        _SNAP_DATES = (now, dates)
    return dates


def _etag_for_latest(latest: str) -> str:
    # Sem `date`, a resposta é função do latest + versão do código: o ETag não
    # precisa de hash do corpo (barato e válido até a próxima publicação/deploy).
    return f'W/"{latest}-{app_version()}"'


# o corpo do `/query` podia ter até 1 MB (padrão do nginx). Uma consulta legítima, mesmo com os
# tetos de `api/query.py::limitar`, cabe em poucos KB; o que passar de 64 KB é recusado antes de o JSON ser lido.
_MAX_CORPO_QUERY = 64 * 1024


@app.middleware("http")
async def limitar_corpo_da_consulta(request: Request, call_next):
    if request.method == "POST" and request.url.path.startswith("/api/v1/query/"):
        tamanho = request.headers.get("content-length")
        if tamanho is None or not tamanho.isdigit() or int(tamanho) > _MAX_CORPO_QUERY:
            return JSONResponse({"detail": f"corpo da consulta ausente de tamanho ou acima de {_MAX_CORPO_QUERY // 1024} KB"}, status_code=413)
    return await call_next(request)


# Rotas com `?date=` cuja resposta depende também do código (não só de `published/{data}/`): nunca `immutable`.
_SAIDA_DEPENDE_DO_CODIGO = frozenset({"/api/v1/busca"})


@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    path = request.url.path
    # o que é `login` para o anônimo (lista expandida, histórico) só chega a quem tem login ou
    # allowlist; com `public`/`immutable` o cache do nginx (sem identidade na chave) o entregaria a anônimos se o gate falhasse aberto.
    classe = _politica.classify(request.method, path, request.query_params, recent_dates(request)).cls if path.startswith("/api/v1/") else None
    e_login = classe == _politica.LOGIN
    # `metered` fora da lista de borda: a Cloudflare não passa pelo gate e entregaria a resposta a quem esgotou o orçamento.
    # `Cloudflare-CDN-Cache-Control` vale só para a borda; navegador e nginx (depois do gate) seguem o `Cache-Control`.
    sem_borda = classe == _politica.METERED and not _politica.cache_na_borda(path)
    cacheable_get = (
        request.method == "GET"
        and path.startswith("/api/v1/")
        and not e_login
        and not path.endswith("/contacts")
        and not request.query_params.get("date")
        and not request.query_params.get("v")
    )
    etag = None
    if cacheable_get:
        cache = getattr(request.app.state, "latest_cache", None)
        latest = cache.current_latest() if cache is not None else None
        if latest:
            etag = _etag_for_latest(latest)
            if request.headers.get("if-none-match") == etag:
                return Response(status_code=304, headers={
                    "ETag": etag,
                    "Cache-Control": "public, max-age=60, stale-while-revalidate=30",
                    **({"Cloudflare-CDN-Cache-Control": "no-store"} if sem_borda else {}),
                })
    response = await call_next(request)
    if sem_borda:
        response.headers["Cloudflare-CDN-Cache-Control"] = "no-store"
    # Contatos: resposta autenticada e sensível — nunca cachear (browser/CDN/proxy).
    if path.endswith("/contacts"):
        response.headers["Cache-Control"] = "private, no-store"
        return response
    if e_login:
        response.headers["Cache-Control"] = "private, no-store"
        return response
    if path.startswith("/api/v1/") and response.status_code == 200:
        date = request.query_params.get("date")
        if getattr(request.state, "cache_imutavel", False):
            # Camada endereçada por hash do conteúdo (`?v=`): a URL identifica os bytes.
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif path in _SAIDA_DEPENDE_DO_CODIGO:
            # A resposta não é função só do snapshot: o índice da busca muda com o código (a razão social entrou na 2.0.19). Com
            # `immutable` o navegador guardaria por um ano o "nada encontrado" de uma versão anterior.
            response.headers["Cache-Control"] = "public, max-age=300"
        elif date and date in _existing_snapshot_dates(request.app):
            # Snapshot publicado é imutável (D-: published/{data}/ nunca muda) e o
            # front sempre envia a data. Campo novo numa rota que já existe NÃO muda
            # a URL sozinho: o front tem de mudá-la (parâmetro `esquema`, como em
            # fetchBrasilIndicadores), senão navegador e nginx servem a resposta velha.
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif date:
            # Data inexistente/inválida: não deixar o navegador guardar.
            response.headers["Cache-Control"] = "public, max-age=60"
        else:
            # Sem date (resolve latest no servidor): pode virar a cada publicação semanal.
            response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=30"
            if etag:
                response.headers["ETag"] = etag
    return response


# Teto de pedidos calculando ao mesmo tempo (ver api/concurrency.py). Adicionado ANTES do cache do latest: acerto de cache não gasta vaga.
app.add_middleware(ConcurrencyLimitMiddleware)

# Cache de bytes do latest — antes deste ponto, outermost entre os middlewares
# acima, de modo que captura a resposta já com Cache-Control (add_cache_headers),
# CORS e gzip aplicados.
app.add_middleware(LatestCacheMiddleware)

# Orçamento por cliente (conta, allowlist ou rede /64), em janelas de minuto, hora e dia (api/limites.py). Fora do cache do latest, para contar
# tudo o que chega à API; guarda a identidade no escopo para a concorrência por cliente, que fica dentro.
from api.limites import OrcamentoMiddleware  # noqa: E402

app.add_middleware(OrcamentoMiddleware, perfil="api")

# Parâmetros não declarados nas rotas GET (contorno de cache; api/parametros.py): registra por padrão, rejeita com API_PARAMETROS_DESCONHECIDOS=rejeitar.
from api.parametros import ParametrosMiddleware  # noqa: E402

app.add_middleware(ParametrosMiddleware)


def _cors_headers_for(request: Request) -> dict[str, str]:
    """Replica manualmente o header de CORS necessário na resposta 403 do guard.

    O guard é registrado como o middleware mais externo (ver comentário abaixo),
    de propósito: precisa interceptar a requisição ANTES do LatestCacheMiddleware,
    senão um hit no byte-cache compartilhado (servido para qualquer usuário,
    autenticado ou não) contornaria o bloqueio de limite atingido. Isso o coloca
    fora do CORSMiddleware, então a resposta 403 não passaria pelo CORS
    automaticamente — replicamos aqui só o necessário para o fetch (com
    credentials: 'include') no frontend conseguir ler essa resposta em dev
    (frontend e API em origens diferentes).
    """
    origin = request.headers.get("origin")
    if origin and origin in _CORS_ORIGINS:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }
    return {}


@app.middleware("http")
async def avisar_rotas_descontinuadas(request: Request, call_next):
    """`Deprecation` + `Link: rel=successor-version` nas rotas substituídas por contratos unificados (`api/deprecation.py`)."""
    response = await call_next(request)
    for k, v in deprecation.cabecalhos(request.url.path).items():
        response.headers[k] = v
    return response


@app.middleware("http")
async def guarda_de_memoria(request: Request, call_next):
    """Datas residentes (api/memoria.py): a data antiga de `?date=` fica protegida do expurgo enquanto a requisição roda e, ao fim,
    a guarda expurga o que ficou fora da política. Nada é recusado: perto do teto a guarda expurga tudo, não devolve 503."""
    guarda = getattr(request.app.state, "guarda_memoria", None)
    data = request.query_params.get("date")
    if guarda is None or not data:
        return await call_next(request)
    with guarda.usando(data):
        return await call_next(request)


@app.middleware("http")
async def anon_session_guard(request: Request, call_next):
    """Bloqueia requisições de sessão anônima que já atingiram o limite de tempo.

    IPs em ALLOWED_IPS e usuários com JWT válido são isentos (mesmo guard de
    entrada de allowed_ips). Não cria nem
    atualiza sessão anônima aqui — isso só acontece em /auth/me e
    /auth/heartbeat; este middleware só faz uma leitura (peek) do estado já
    resolvido via cookie, para decidir se bloqueia e para sinalizar o header
    em qualquer resposta relevante.
    """
    decision = evaluate_access(request, request.url.path, via="middleware")
    if decision is not None:
        request.state.access_tier = decision.tier  # lido pelo log de uso (api/usage_log.py)
    if decision is None or not decision.blocked:
        # Só o "true" (no 403 abaixo) tem efeito no front; um "false" numa resposta pública ficaria guardado em cache.
        return await call_next(request)

    if decision.kind == BLOCK_LOGIN:
        return JSONResponse(
            {
                "detail": "Esta ação exige login. Faça login para continuar.",
                "login_required": True,
                "reason": decision.reason,
            },
            status_code=401,
            headers={"X-Login-Required": "true", **_cors_headers_for(request)},
        )
    # Orçamento esgotado: 429 com Retry-After (D9), e não 403: um script distingue "espere" de "proibido", e o corpo diz o limite e a saída.
    return limite_anonimo(_cors_headers_for(request))


# Log de uso: registrado DEPOIS do guard para ser o middleware mais externo
# e medir também as respostas barradas (401/403). Não bloqueia nada.
app.add_middleware(UsageLogMiddleware, data_dir=data_dir, src="api")

app.include_router(auth_router)
app.include_router(perfil_router)       # perfil da conta, chave de MCP, exclusão em 30 dias
app.include_router(internas_router)     # verificação da chave e uso por conta, só para o MCP
app.include_router(sici_indicadores.router, prefix="/api/v1", tags=["sici_indicadores"])
app.include_router(territorio.router, prefix="/api/v1", tags=["territorio"])
app.include_router(regiao.router, prefix="/api/v1", tags=["territorio"])
app.include_router(seguranca.router, prefix="/api/v1", tags=["seguranca"])
app.include_router(cetic.router, prefix="/api/v1", tags=["cetic"])
app.include_router(erbs.router, prefix="/api/v1", tags=["erbs"])
app.include_router(regulatorio.router, prefix="/api/v1", tags=["regulatorio"])
app.include_router(qualidade.router, prefix="/api/v1", tags=["qualidade"])
app.include_router(empresas.router, prefix="/api/v1", tags=["empresas"])
app.include_router(financiamento.router, prefix="/api/v1", tags=["financiamento"])
app.include_router(consumidor.router, prefix="/api/v1", tags=["consumidor"])
app.include_router(prontidao.router, prefix="/api/v1", tags=["prontidao"])
app.include_router(ipv4.router, prefix="/api/v1", tags=["ipv4"])
app.include_router(route_servers.router, prefix="/api/v1", tags=["route-servers"])
app.include_router(rs_policy.router, prefix="/api/v1", tags=["route-servers"])
app.include_router(as2org.router, prefix="/api/v1", tags=["organizacao"])
app.include_router(transito.router, prefix="/api/v1", tags=["transito"])
app.include_router(bloqueios.router, prefix="/api/v1", tags=["bloqueios"])
app.include_router(radar_routes.router, prefix="/api/v1", tags=["radar"])
app.include_router(contratos_routes.router, prefix="/api/v1", tags=["contratos"])
app.include_router(exposicao_routes.router, prefix="/api/v1", tags=["exposicao"])
app.include_router(instalacoes.router, prefix="/api/v1", tags=["instalacoes"])
app.include_router(historico.router, prefix="/api/v1", tags=["historico"])      # antes de snapshots: /snapshots/diff não pode cair em /snapshots/{date_str}
app.include_router(snapshots.router, prefix="/api/v1", tags=["snapshots"])
app.include_router(ixps.router, prefix="/api/v1", tags=["ixps"])
app.include_router(ixp_geo.router, prefix="/api/v1", tags=["ixps"])
app.include_router(external_ixps.router, prefix="/api/v1", tags=["external-ixps"])
app.include_router(ixp_compare.router, prefix="/api/v1", tags=["ixps"])
app.include_router(cdns.router, prefix="/api/v1", tags=["cdns"])
app.include_router(asns.router, prefix="/api/v1", tags=["asns"])
app.include_router(asn_geo.router, prefix="/api/v1", tags=["asns"])
app.include_router(hilbert.router, prefix="/api/v1", tags=["hilbert"])
app.include_router(map.router, prefix="/api/v1", tags=["geo"])
app.include_router(prefixes.router, prefix="/api/v1", tags=["geo"])
app.include_router(query.router, prefix="/api/v1", tags=["query"])
app.include_router(rpki.router, prefix="/api/v1", tags=["rpki"])
app.include_router(routing_analysis.router, prefix="/api/v1", tags=["routing-analysis"])
app.include_router(bgp_stability.router, prefix="/api/v1", tags=["bgp-stability"])
app.include_router(bgp_stability_deep.router, prefix="/api/v1", tags=["bgp-stability"])
app.include_router(scms.router, prefix="/api/v1", tags=["scms"])
app.include_router(acessos.router, prefix="/api/v1", tags=["acessos"])
app.include_router(smp.router, prefix="/api/v1", tags=["smp"])
app.include_router(stfc.router, prefix="/api/v1", tags=["stfc"])
app.include_router(seac.router, prefix="/api/v1", tags=["seac"])
app.include_router(acessos_movel.router, prefix="/api/v1", tags=["acessos-movel"])
app.include_router(grupos.router, prefix="/api/v1", tags=["grupos"])
app.include_router(perfis.router, prefix="/api/v1", tags=["perfis"])
app.include_router(outorgas.router, prefix="/api/v1", tags=["outorgas"])
app.include_router(sitemap.router)
app.include_router(documentacao.router)
app.include_router(limites_routes.router, prefix="/api/v1", tags=["limites"])
app.include_router(brasil_routes.router, prefix="/api/v1", tags=["brasil"])
from api.routes import busca as busca_rota  # noqa: E402
app.include_router(busca_rota.router, prefix="/api/v1", tags=["busca"])
app.include_router(meta.router)

# O OpenAPI também marca como `deprecated` as rotas substituídas por contratos unificados: mesmo critério dos cabeçalhos.
for _rota in app.routes:
    if getattr(_rota, "methods", None) and deprecation.sucessor(re.sub(r"\{[^}]+\}", "1", _rota.path)):
        _rota.deprecated = True


@app.get(
    "/health",
    tags=["health"],
    response_model=HealthResponse,
    summary="Status da API",
    description="Verifica se a API está no ar e informa o snapshot mais recente disponível.",
)
def health(request: Request) -> dict:
    store: Store = request.app.state.store
    latest = store.latest()
    snapshots_available = store.list_snapshots()
    return {
        "status": "ok",
        "version": app_version(),
        "latest_snapshot": latest,
        "snapshots_available": len(snapshots_available),
    }


@app.get(
    "/api/v1/internal/diag",
    tags=["health"],
    summary="Diagnóstico de memória do processo (interno)",
    description=(
        "RSS, cgroup e tamanho de cada cache do Store, por data. `deep=1` estima o tamanho "
        "em bytes por amostragem (segura o GIL por segundos). Restrito a loopback ou X-Internal-Token."
    ),
    include_in_schema=False,
)
def internal_diag(request: Request, deep: int = Query(0, ge=0, le=1), sample: int = Query(64, ge=8, le=512)) -> dict:
    from fastapi import HTTPException

    from api.diag import collect

    token_hdr = request.headers.get("X-Internal-Token", "")
    client_ip = (request.client.host if request.client else "") or ""
    is_loopback = client_ip in ("127.0.0.1", "::1", "localhost")
    is_token_ok = bool(_INTERNAL_TOKEN) and secrets.compare_digest(token_hdr, _INTERNAL_TOKEN)
    if not is_loopback and not is_token_ok:
        raise HTTPException(403, "Acesso restrito")
    out = collect(request.app.state.store, getattr(request.app.state, "latest_cache", None), bool(deep), sample)
    guarda = getattr(request.app.state, "guarda_memoria", None)
    out["memoria"] = guarda.estado() if guarda is not None else {"ligado": False}
    return out


@app.post(
    "/api/v1/warmup",
    tags=["health"],
    summary="Forçar warm-up de snapshot",
    description=(
        "Pré-carrega os índices pesados (membro-IXP e VRPs RPKI) de um snapshot na memória. "
        "Chamado automaticamente pelo pipeline semanal após publicação. "
        "Restrito a chamadas locais (loopback)."
    ),
    include_in_schema=False,
)
async def warmup(
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
) -> dict:
    from fastapi import HTTPException
    # Restringe a chamadas internas. Aceita via token (preferido, funciona em qualquer
    # topologia Docker) ou via loopback (fallback para deployments sem token configurado).
    token_hdr = request.headers.get("X-Internal-Token", "")
    client_ip = (request.client.host if request.client else "") or ""
    is_loopback = client_ip in ("127.0.0.1", "::1", "localhost")
    is_token_ok = bool(_INTERNAL_TOKEN) and secrets.compare_digest(token_hdr, _INTERNAL_TOKEN)
    if not is_loopback and not is_token_ok:
        raise HTTPException(403, "Acesso restrito")
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    try:
        # Backfill: se sici.json.gz foi publicado depois que a API já leu este snapshot,
        # o cache guarda um None negativo. Descarta antes de aquecer.
        heap.descongelar()                  # o que for solto (snapshot e caches anteriores) volta a poder ser liberado
        store.invalidate_sici(date_str)
        tarefas = [await _warmup(store, date_str)]
        # Invalida o byte-cache (pode haver snapshot novo) e re-materializa o latest.
        cache = getattr(request.app.state, "latest_cache", None)
        if cache is not None:
            cache.clear()
        tarefas.append(asyncio.create_task(prewarm_latest(request.app, date_str)))
        tarefas.append(asyncio.create_task(prewarm_top_asns(request.app, date_str)))
        if os.environ.get("PREWARM_PERFIS", "1") != "0":
            tarefas.append(asyncio.create_task(prewarm_perfis(request.app, date_str)))
        asyncio.create_task(heap.congelar_depois(tarefas, "aquecimento depois de publicar"))
        return {"status": "ok", "snapshot": date_str}
    except Exception as exc:
        _log.warning("warm-up forçado falhou (%s): %s", date_str, exc)
        return {"status": "error", "snapshot": date_str, "detail": str(exc)}
