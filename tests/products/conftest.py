# SPDX-License-Identifier: AGPL-3.0-or-later
"""T2 — produtos: dataset sintético (Arandurápolis) → pipeline real (`bgp_ixp` → `metricas_ixp_asn` → `snapshot_completo`) → published/."""
import pytest

from core.common import configure_logging
from tests.synth.generate import generate
from tests.synth.world import MUNICIPIOS, PTTS, T0, T1


def fake_pix():
    """Coordenadas dos PTTs fictícios (substituem config/pix.yaml, que descreve os PTTs reais)."""
    mun = {m[1]: m for m in MUNICIPIOS}
    return {c: [{"name": n, "lat": mun[n][3], "lon": mun[n][4]}] for c, n, _ in PTTS}


def fake_centroides():
    """Centroides (lon, lat) dos municípios fictícios (o IBGE 99… não está em config/municipios-centroides.json)."""
    return {m[0]: (m[4], m[3]) for m in MUNICIPIOS}


def fake_pix_cadastro():
    """Cadastro de PIX para a área de influência: za com coordenada; zb com um PIX sem endereço reconhecível (vai para a sede); zc só com endereço (vai para o município dele)."""
    mun = {m[1]: m for m in MUNICIPIOS}
    return {"za": [{"name": "[PIX A]", "address": "", "lat": mun["Arandurápolis"][3], "lon": mun["Arandurápolis"][4]}],
            "zb": [{"name": "[PIX B1]", "address": "", "lat": mun["Tupãnópolis"][3], "lon": mun["Tupãnópolis"][4]}, {"name": "[PIX B2]", "address": "Rua Sem Cidade, 10"}],
            "zc": [{"name": "[PIX C]", "address": "Rua A, 1 - Mbaracayú Novo - PR"}]}


def patch_area_influencia(mp):
    """Entradas de `config/` do produto `area_influencia_ptt` trocadas pelas do dataset sintético (no pipeline, no compare e no replay)."""
    from products.area_influencia_ptt import build as area_influencia

    mp.setattr(area_influencia, "carregar_centroides", fake_centroides)
    mp.setattr(area_influencia, "carregar_pix", fake_pix_cadastro)
    mp.setattr(area_influencia, "carregar_referencia", lambda: {})


def fake_ixps():
    return [{"code": c, "name": n, "uf": uf, "telnet_host": f"lg.{c}.ix.br", "telnet_port": 23, "timeout": 60}
            for c, n, uf in PTTS]


@pytest.fixture(scope="session")
def dataset(tmp_path_factory):
    out = tmp_path_factory.mktemp("arandurapolis")
    generate(out, seed=1)
    return out


def run_pipeline(base, date, monkeypatch):
    """`bgp_ixp` → `metricas_ixp_asn` → `snapshot_completo` sobre o `base`, com a lista de PTTs fictícia."""
    from products.bgp_routes import build as bgp_parser
    from products.ixp_metrics import build as metrics
    from publish import snapshot_builder

    for mod in (bgp_parser, metrics, snapshot_builder):
        monkeypatch.setattr(mod, "load_ixps", fake_ixps, raising=False)
    from api.store import Store
    from tests.synth.infra import EXTERNAL_IXP

    monkeypatch.setattr(snapshot_builder, "load_peeringdb_ixps_config",
                        lambda: {"external": [EXTERNAL_IXP], "ixbr": [{"code": c, "pdb_ix_id": 9000 + i} for i, (c, _, _) in enumerate(PTTS)]})

    monkeypatch.setattr(Store, "_load_pix_config", lambda self: fake_pix())
    from core import marcas as marcas_mod
    from tests.synth.qualidade import CURADA

    monkeypatch.setattr(marcas_mod, "CAMINHO_CURADA", CURADA)            # tabela marca → CNPJ sintética (a real é config/curada_marcas_operadoras.yaml)
    from sources.socios_grupos import enrich as socios_grupos

    # holdings externas: sem rede — cadastro vazio
    monkeypatch.setattr(socios_grupos, "_fetch_cartao_cnpj", lambda cnpj, client: {
        "razao_social": "HOLDING EXEMPLO PARTICIPACOES SA", "nome_fantasia": "", "situacao_cadastral": "ATIVA",
        "natureza_juridica": "Sociedade Anônima Fechada", "porte": "DEMAIS", "capital_social": 1000000,
        "data_inicio_atividade": "2010-01-01", "cnae_fiscal_descricao": "Holdings de instituições não-financeiras",
        "logradouro": "", "numero": "", "complemento": "", "bairro": "", "municipio": "Arandurápolis", "uf": "SP", "cep": ""})
    monkeypatch.setattr(socios_grupos, "BRASILAPI_DELAY", 0)
    log = configure_logging()
    for code, _, _ in PTTS:
        bgp_parser.parse_ixp(code, date, base, log)
    socios_grupos.run(date, base, log)                                    # `socios_grupos`: grupos societários
    metrics.run(date, base, log=log)
    result = snapshot_builder.run(date, base, log)
    snapshot_builder.run_asn_health_only(base, date, log)             # alerts + RPKI por ASN e índice (passo `saude_asn`)
    from products.prontidao import build as prontidao
    from publish import coleta_checks

    prontidao.publicar_prontidao(base, date, log)                      # depois do `saude_asn`: precisa da validação RPKI de cada prefixo
    from products.manrs import build as manrs
    manrs.publicar_manrs(base, date, log)                              # agregado do MANRS, depois da prontidão
    from products.regiao import build as regiao
    regiao.publicar_regiao(base, date, log)                            # ASNs por município, depois do SICI e das relações
    from products.rede_territorio import build as rede_territorio
    rede_territorio.publicar_rede_territorio(base, date, log)           # IPv6, ROV e trânsito no território (depois da região e da segurança)
    from products.area_influencia_ptt import build as area_influencia

    patch_area_influencia(monkeypatch)
    area_influencia.publicar_area_influencia(base, date, log)         # área de influência dos PTTs (depois do SICI e dos documentos de ASN)
    coleta_checks.refresh_manifest(base, date, log, checksums=True)    # o manifesto passa a conter o arquivo novo
    return result


@pytest.fixture(scope="session")
def pipeline(dataset, tmp_path_factory):
    """Cópia do dataset + pipeline executado para T0 e T1 (uma vez por sessão; os testes só LEEM)."""
    import shutil

    base = tmp_path_factory.mktemp("pipeline") / "data"
    shutil.copytree(dataset, base)
    with pytest.MonkeyPatch.context() as mp:
        results = {d: run_pipeline(base, d, mp) for d in (T0, T1)}
    from products.history import build as historico

    for d in (T0, T1):                                                    # camada de histórico para a API de histórico (T4)
        historico.construir(base, d, configure_logging())
    return base, results


@pytest.fixture(scope="module")
def api(pipeline):
    """API real (FastAPI + lifespan + Store) servindo o publicado do dataset sintético (T4)."""
    base, _ = pipeline
    from fastapi.testclient import TestClient

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATA_DIR", str(base))
        mp.setenv("JWT_SECRET", "x" * 32)
        mp.setenv("GOOGLE_CLIENT_ID", "a")
        mp.setenv("GOOGLE_CLIENT_SECRET", "b")
        mp.setenv("ALLOWED_IPS", "203.0.113.128/25")
        mp.setenv("APP_BASE_URL", "http://localhost")
        mp.setenv("ANON_SESSION_LIMIT_MINUTES", "10")
        mp.setenv("ACCESS_POLICY_MODE", "enforce")      # como em produção
        mp.setenv("ANON_API_CLIENT_COST_SECONDS", "0")  # o IP anônimo dos testes faz centenas de pedidos; test_anon_rede_s12 liga o custo
        mp.setenv("USAGE_LOG", "off")
        from api.main import app
        from api.store import Store

        mp.setattr(Store, "_load_pix_config", lambda self: fake_pix())   # PIX fictícios (como no pipeline)
        from core import marcas as marcas_mod
        from tests.synth.qualidade import CURADA

        mp.setattr(marcas_mod, "CAMINHO_CURADA", CURADA)                # marca → CNPJ sintética também na API (vínculo ASN ↔ CNPJ, cenário 10)
        from api.ratelimit import limiter

        # o limite por IP (120/min) é do anti-abuso, não do contrato: com ele ligado, o resultado dos testes
        # dependeria de quantas chamadas os outros módulos já fizeram na mesma janela
        mp.setattr(limiter, "enabled", False)
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
        # a app é um singleton de módulo: não deixa Store/cache para os testes que a usam sem lifespan
        for attr in ("store", "latest_cache"):
            if hasattr(app.state, attr):
                delattr(app.state, attr)
