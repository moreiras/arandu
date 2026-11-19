# SPDX-License-Identifier: AGPL-3.0-or-later
"""API mínima para testar o nginx do frontend: app real (guard + /auth/*) sem Store.

Uso: ver tests/nginx/test_gate.sh. Env: STUB_DATA_DIR, ALLOWED_IPS.
"""
import os
import sys
import time

from fastapi import Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("JWT_SECRET", "x" * 32)
os.environ.setdefault("GOOGLE_CLIENT_ID", "a")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "b")
os.environ.setdefault("APP_BASE_URL", "https://teste.local")
DATA = Path(os.environ["STUB_DATA_DIR"])
DATA.mkdir(parents=True, exist_ok=True)

from api.auth.anon_session import load_anon_config  # noqa: E402
from api.auth.config import init_auth_config  # noqa: E402
from api.main import app  # noqa: E402


@asynccontextmanager
async def _lifespan(a):
    a.state.auth_config = init_auth_config(DATA)
    a.state.anon_config = load_anon_config()
    yield


app.router.lifespan_context = _lifespan


# Substitui as rotas reais (que dependem do Store) por stubs com o mesmo caminho.
app.router.routes = [
    r for r in app.router.routes
    if getattr(r, "path", None) not in ("/api/v1/ixps", "/api/v1/asns", "/api/v1/ping", "/api/v1/ixps/estimated-users")
]


@app.get("/api/v1/ping")
def ping():
    return {"t": time.time()}


@app.get("/api/v1/ixps")
def ixps():
    return {"ixps": []}


@app.get("/api/v1/asns")
def asns(page: int = 1, limit: int = 100):
    return {"page": page, "items": []}


# a pré-compressão só vale para as camadas estáticas e só depois que a rota reconhece o `v`; a camada fictícia entra na lista e
# marca o estado como a rota real (`api/routes/map.py::_data_da_camada`).
from api.precompressao import PreBrotliMiddleware  # noqa: E402

for _m in app.user_middleware:
    if _m.cls is PreBrotliMiddleware:
        _m.kwargs["caminhos"] = frozenset(_m.kwargs.get("caminhos") or ()) | {"/api/v1/map/eco"}


@app.get("/api/v1/map/eco")
def eco(request: Request, v: str = ""):
    """Camada estática fictícia: devolve o Accept-Encoding que a API recebeu do nginx (pré-compressão brotli-11)."""
    if v:
        request.state.cache_imutavel = True
    return JSONResponse({"linhas": [{"codigo": f"ix{i}", "nome": "ponto de troca de trafego", "usuarios": i} for i in range(3000)]},
                        headers={"X-Upstream-AE": request.headers.get("accept-encoding", "")})


@app.get("/api/v1/ixps/estimated-users")
def grande():
    # Rota de entrada (open) com corpo > 1 KB e compressível, para testar gzip/brotli.
    return {"linhas": [{"codigo": f"ix{i}", "nome": "ponto de troca de trafego", "usuarios": i} for i in range(400)]}


@app.get("/meta/{tipo}/{ident}")
def meta(tipo: str, ident: str):
    """Stub do HTML de metatags: marca no corpo que a API respondeu, para o teste do desvio por agente."""
    from fastapi.responses import HTMLResponse
    if ident == "inexistente":
        return HTMLResponse("nao", status_code=404)
    return HTMLResponse(f"<title>META {tipo} {ident}</title>")


# Os stubs precisam vir antes das rotas reais: as com parâmetro (ex.: /ixps/{code}) capturariam o caminho e, no FastAPI 0.138, os routers
# incluídos ficam como `_IncludedRouter` (o filtro por caminho acima não os alcança), então a /api/v1/asns real atendia antes do stub e dava
# 500 sem o Store (sem isso, o test_gate.sh falha em 3 casos). Todos os endpoints deste módulo vão para o começo.
_stubs = [r for r in app.router.routes if getattr(getattr(r, "endpoint", None), "__module__", None) == __name__]
app.router.routes[:] = _stubs + [r for r in app.router.routes if r not in _stubs]
