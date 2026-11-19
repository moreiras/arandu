# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixtures: app FastAPI com auth configurada em diretório temporário (sem Store/lifespan)."""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Orçamento por cliente e cota de contatos desligados na suíte: o TestClient é um cliente só e as baterias
# (T4, fuzz) passam de qualquer teto real. Os testes de tests/unit/test_limites.py e test_contatos_cota.py ligam explicitamente o que medem.
for _v in ("API_ORCAMENTO_ANON", "API_ORCAMENTO_CONTA", "MCP_ORCAMENTO_ANON", "MCP_ORCAMENTO_CONTA", "API_MAX_INFLIGHT_POR_CLIENTE",
           "MCP_MAX_INFLIGHT_POR_CLIENTE", "CONTATOS_CONTA_RAJADA", "CONTATOS_CONTA_HORA", "CONTATOS_CONTA_DIA", "CONTATOS_CONTA_30D",
           "CONTATOS_CONTA_NOVA_DIA", "CONTATOS_REDE_RAJADA", "CONTATOS_REDE_HORA", "CONTATOS_REDE_DIA", "CONTATOS_GLOBAL_DIA"):
    os.environ.setdefault(_v, "0")
# Congelamento do heap (api/heap.py) desligado: cada TestClient congelaria o que estivesse vivo na suíte. test_heap.py liga o seu.
os.environ.setdefault("GC_CONGELAR", "0")
# Alertas (Telegram): a suíte roda os scripts de verdade e o .env local tem o token. Nenhum teste manda mensagem: o comando de
# alerta do pipeline e do vigia fica vazio, e o alerta-telegram.sh não lê o .env nem as variáveis do ambiente. Quem testa o alerta passa
# as suas (curl falso no PATH).
os.environ["ALERTA_CMD"] = ""
os.environ["VIGIA_ALERTA_CMD"] = ""
os.environ["ALERTA_ENV"] = "/nonexistent/arandurape-alerta.env"
for _v in ("TELEGRAM_BOT_KEY", "TELEGRAM_CHAT_ID"):
    os.environ.pop(_v, None)


def pytest_addoption(parser):
    parser.addoption("--update-golden", action="store_true", default=False,
                     help="regrava os arquivos de ouro dos testes de produto (T2); revise o diff antes de commitar")


@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "a")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "b")
    monkeypatch.setenv("ALLOWED_IPS", "203.0.113.128/25,2001:db8:a110::/48")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("APP_BASE_URL", "https://teste.local")
    monkeypatch.setenv("ANON_SESSION_LIMIT_MINUTES", "10")
    from fastapi.testclient import TestClient

    from api.auth.anon_session import load_anon_config
    from api.auth.config import init_auth_config
    from api.main import app

    app.state.auth_config = init_auth_config(tmp_path)
    app.state.anon_config = load_anon_config()
    return TestClient(app), app, tmp_path
