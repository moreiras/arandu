# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Pré-compressão brotli-11 das camadas imutáveis."""
import json
from concurrent.futures import Executor, Future

import brotli
from starlette.applications import Starlette
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from api.precompressao import PreBrotliMiddleware

DOC = {"type": "FeatureCollection", "features": [{"id": i, "name": "cabo " * 20} for i in range(400)]}
H = "0123456789abcdef"


class Sincrono(Executor):
    """Roda a compressão na hora, para o teste não depender de tempo."""

    def submit(self, fn, *a, **kw):
        f = Future()
        f.set_result(fn(*a, **kw))
        return f


def _validada(request):
    """Como a rota real (`api/routes/map.py::_data_da_camada`): o `v` existe, então a resposta é imutável."""
    request.state.cache_imutavel = True
    return JSONResponse(DOC)


def _app(tmp_path, chamadas):
    def camada(request):
        chamadas.append(1)
        return _validada(request)

    app = Starlette(routes=[Route("/api/v1/map/cabos", camada), Route("/api/v1/ixps", camada)])
    app.add_middleware(PreBrotliMiddleware, data_dir=tmp_path, executor=Sincrono())
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    return TestClient(app)


def test_primeira_resposta_sai_normal_sem_cache_no_proxy_e_a_segunda_vem_do_arquivo_brotli_11(tmp_path):
    chamadas: list = []
    c = _app(tmp_path, chamadas)
    r1 = c.get(f"/api/v1/map/cabos?v={H}", headers={"Accept-Encoding": "br"})
    assert r1.status_code == 200 and r1.json() == DOC
    assert r1.headers["x-accel-expires"] == "0" and "content-encoding" not in r1.headers      # o nginx comprime; não guarda por 7 dias
    arquivos = list((tmp_path / "cache" / "br11").glob("*.br"))
    assert len(arquivos) == 1
    r2 = c.get(f"/api/v1/map/cabos?v={H}", headers={"Accept-Encoding": "gzip, br"})
    assert r2.headers["content-encoding"] == "br" and r2.headers["vary"] == "Accept-Encoding"
    assert r2.headers["cache-control"] == "public, max-age=31536000, immutable" and "x-accel-expires" not in r2.headers
    assert r2.json() == DOC and len(chamadas) == 1                                          # a rota não rodou de novo
    bruto = arquivos[0].read_bytes()
    assert json.loads(brotli.decompress(bruto)) == DOC and int(r2.headers["content-length"]) == len(bruto)
    assert len(bruto) < len(json.dumps(DOC, separators=(",", ":")).encode()) * 0.2


def test_quem_nao_aceita_brotli_e_o_que_nao_e_camada_por_hash_seguem_o_caminho_normal(tmp_path):
    chamadas: list = []
    c = _app(tmp_path, chamadas)
    assert c.get(f"/api/v1/map/cabos?v={H}", headers={"Accept-Encoding": "gzip"}).headers["content-encoding"] == "gzip"
    assert c.get("/api/v1/map/cabos", headers={"Accept-Encoding": "br"}).status_code == 200            # sem v
    assert c.get("/api/v1/map/cabos?v=nao-e-hash", headers={"Accept-Encoding": "br"}).status_code == 200
    assert c.get(f"/api/v1/ixps?v={H}", headers={"Accept-Encoding": "br"}).status_code == 200          # fora de /map/
    assert not (tmp_path / "cache").exists() and len(chamadas) == 4


def test_resposta_de_erro_nao_gera_arquivo(tmp_path):
    app = Starlette(routes=[Route("/api/v1/map/cabos", lambda r: JSONResponse({"detail": "x"}, status_code=404))])
    app.add_middleware(PreBrotliMiddleware, data_dir=tmp_path, executor=Sincrono())
    r = TestClient(app).get(f"/api/v1/map/cabos?v={H}", headers={"Accept-Encoding": "br"})
    assert r.status_code == 404 and "x-accel-expires" not in r.headers and not (tmp_path / "cache").exists()


def test_data_dir_pode_ser_funcao_e_arquivo_corrompido_nao_derruba(tmp_path):
    c = _app(tmp_path, [])
    c.get(f"/api/v1/map/cabos?v={H}", headers={"Accept-Encoding": "br"})
    arq = next((tmp_path / "cache" / "br11").glob("*.br"))
    assert arq.stat().st_size > 0
    app = Starlette(routes=[Route("/api/v1/map/cabos", _validada)])
    app.add_middleware(PreBrotliMiddleware, data_dir=lambda: tmp_path, executor=Sincrono())
    assert TestClient(app).get(f"/api/v1/map/cabos?v={H}", headers={"Accept-Encoding": "br"}).headers["content-encoding"] == "br"


def test_arquivo_servido_marca_a_camada_como_imutavel_para_o_middleware_de_cabecalhos(tmp_path):
    """A rota não roda ao servir o `.br`; sem o estado `cache_imutavel` o middleware externo trocaria o Cache-Control por max-age=60."""
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request

    vistos: list = []

    async def cabecalhos(request: Request, call_next):
        resp = await call_next(request)
        vistos.append(getattr(request.state, "cache_imutavel", False))
        if vistos[-1]:
            resp.headers["x-imutavel"] = "1"
        return resp

    rodou: list = []

    def stub(request):                                   # 1º pedido: a rota valida o v, marca o estado e o arquivo é gerado
        rodou.append(1)
        return _validada(request)

    app = Starlette(routes=[Route("/api/v1/map/cabos", stub)])
    app.add_middleware(PreBrotliMiddleware, data_dir=tmp_path, executor=Sincrono())
    app.add_middleware(BaseHTTPMiddleware, dispatch=cabecalhos)
    c = TestClient(app)
    c.get(f"/api/v1/map/cabos?v={H}", headers={"Accept-Encoding": "br"})                 # gera o arquivo
    r = c.get(f"/api/v1/map/cabos?v={H}", headers={"Accept-Encoding": "br"})              # vem do arquivo: a rota não roda
    assert rodou == [1] and vistos == [True, True] and r.headers["x-imutavel"] == "1"


def test_camada_acima_do_limite_nao_e_pre_comprimida(tmp_path):
    app = Starlette(routes=[Route("/api/v1/map/cabos", _validada)])
    app.add_middleware(PreBrotliMiddleware, data_dir=tmp_path, executor=Sincrono(), max_corpo=1000)
    r = TestClient(app).get(f"/api/v1/map/cabos?v={H}", headers={"Accept-Encoding": "br"})
    assert r.status_code == 200 and r.json() == DOC and not (tmp_path / "cache").exists()


def test_s05_outro_parametro_alem_de_v_nao_entra_no_cache(tmp_path):
    """`?v=<hash>&sigla=<nada>` gravava uma resposta que passava a ser servida a todos por 1 ano."""
    chamadas: list = []
    c = _app(tmp_path, chamadas)
    for qs in (f"v={H}&sigla=XX", f"sigla=XX&v={H}", f"v={H}&v={H}", f"v={H}&x="):
        r = c.get(f"/api/v1/map/cabos?{qs}", headers={"Accept-Encoding": "br"})
        assert r.status_code == 200 and "x-accel-expires" not in r.headers, qs
    assert not (tmp_path / "cache").exists() and len(chamadas) == 4


def test_s05_v_que_a_rota_nao_reconhece_nao_grava_arquivo(tmp_path):
    """Rota que não marcou `cache_imutavel` (o `v` não é de nenhuma camada) não gera arquivo: `v` aleatório não enche o disco."""
    app = Starlette(routes=[Route("/api/v1/map/cabos", lambda r: JSONResponse(DOC))])
    app.add_middleware(PreBrotliMiddleware, data_dir=tmp_path, executor=Sincrono())
    c = TestClient(app)
    for i in range(5):
        assert c.get(f"/api/v1/map/cabos?v={i:016x}", headers={"Accept-Encoding": "br"}).status_code == 200
    assert not (tmp_path / "cache").exists()


def test_s05_so_as_rotas_das_camadas_estaticas(tmp_path):
    app = Starlette(routes=[Route("/api/v1/map/cabos", _validada), Route("/api/v1/map/outra", _validada)])
    app.add_middleware(PreBrotliMiddleware, data_dir=tmp_path, executor=Sincrono(), caminhos=frozenset({"/api/v1/map/cabos"}))
    c = TestClient(app)
    c.get(f"/api/v1/map/outra?v={H}", headers={"Accept-Encoding": "br"})
    assert not (tmp_path / "cache").exists()
    c.get(f"/api/v1/map/cabos?v={H}", headers={"Accept-Encoding": "br"})
    assert len(list((tmp_path / "cache" / "br11").glob("*.br"))) == 1


def test_s05_fila_de_compressao_tem_teto(tmp_path):
    class Parado(Executor):                              # nunca termina: as compressões ficam pendentes
        def __init__(self):
            self.n = 0

        def submit(self, fn, *a, **kw):
            self.n += 1
            return Future()

    ex = Parado()
    app = Starlette(routes=[Route("/api/v1/map/cabos", _validada)])
    app.add_middleware(PreBrotliMiddleware, data_dir=tmp_path, executor=ex, max_pendentes=2)
    c = TestClient(app)
    for i in range(5):
        c.get(f"/api/v1/map/cabos?v={i:016x}", headers={"Accept-Encoding": "br"})
    assert ex.n == 2


def test_camadas_estaticas_da_api_real_estao_no_middleware():
    from api.main import app
    from api.routes.map import _CAMADAS_ESTATICAS
    mw = [m for m in app.user_middleware if m.cls is PreBrotliMiddleware]
    assert mw and mw[0].kwargs.get("caminhos") == frozenset(_CAMADAS_ESTATICAS.values())
