# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Exporta respostas REAIS da API sobre o dataset sintético para os testes do frontend (msw).

    python -m tests.synth.export_front_fixtures [--out frontend/src/test/fixtures]

Respostas pequenas (limite baixo) de rotas de entrada; o frontend testa o cliente HTTP, o tratamento de
401/403 e a política de acesso contra o formato que a API de fato devolve.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

ROUTES = {
    "snapshots": "/api/v1/brasil/snapshots",
    "ixps": "/api/v1/ixps",
    "asns_page1": "/api/v1/asns?page=1&limit=5",
    "asn_detail": "/api/v1/asns/{asn}",
    "health": "/health",
}


def export(out: Path) -> dict:
    import pytest
    from fastapi.testclient import TestClient

    from tests.products.conftest import fake_pix
    from tests.synth.publish import publish

    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "data"
        publish(base)
        with pytest.MonkeyPatch.context() as mp:
            for k, v in {"DATA_DIR": str(base), "JWT_SECRET": "x" * 32, "GOOGLE_CLIENT_ID": "a",
                         "GOOGLE_CLIENT_SECRET": "b", "ALLOWED_IPS": "203.0.113.128/25",
                         "APP_BASE_URL": "http://localhost", "USAGE_LOG": "off"}.items():
                mp.setenv(k, v)
            from api.main import app
            from api.store import Store

            mp.setattr(Store, "_load_pix_config", lambda self: fake_pix())
            with TestClient(app, raise_server_exceptions=False) as c:
                h = {"X-Real-IP": "203.0.113.129"}
                asn = c.get("/api/v1/asns?limit=1", headers=h).json()["items"][0]["asn"]
                written = {}
                for name, route in ROUTES.items():
                    r = c.get(route.format(asn=asn), headers=h)
                    assert r.status_code == 200, (route, r.status_code)
                    (out / f"{name}.json").write_text(json.dumps(r.json(), ensure_ascii=False, indent=1) + "\n",
                                                      encoding="utf-8")
                    written[name] = route.format(asn=asn)
    return written


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "frontend" / "src" / "test" / "fixtures"))
    for name, route in export(Path(ap.parse_args(argv).out)).items():
        print(f"{name:12s} <- {route}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
