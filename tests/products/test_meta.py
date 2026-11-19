# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — metatags por tipo de entidade: `/meta/{tipo}/{id}` devolve HTML mínimo com título, descrição e Open Graph."""
import re

import pytest
from core.site import SITE


def _primeiro(api, caminho: str, campo: str):
    r = api.get(caminho)
    assert r.status_code == 200, r.text
    corpo = r.json()
    itens = corpo.get("items") if isinstance(corpo, dict) else corpo
    return itens[0][campo]


@pytest.fixture(scope="module")
def ids(api):
    asn = _primeiro(api, "/api/v1/asns?limit=1", "asn")
    from api.store import Store
    store: Store = api.app.state.store
    d = store.latest()
    ptt = next(i["code"] for i in store.ixp_index(d) if i.get("code"))
    op = next(o["cnpj"] for o in store.operadora_index(d) if o.get("ativo"))
    return {"asn": str(asn), "ixp": ptt, "operadora": str(op), "uf": "ES"}


def test_cada_tipo_de_entidade_tem_titulo_descricao_e_open_graph(api, ids):
    for tipo, ident in ids.items():
        r = api.get(f"/meta/{tipo}/{ident}")
        assert r.status_code == 200, (tipo, r.text[:200])
        assert r.headers["content-type"].startswith("text/html")
        h = r.text
        assert re.search(rf"<title>[^<]+ · {re.escape(SITE.nome)}</title>", h), tipo
        assert re.search(r'<meta name="description" content="[^"]{40,}"', h), tipo
        for og in ("og:title", "og:description", "og:url", "og:type", "og:site_name"):
            assert f'property="{og}"' in h, (tipo, og)
        assert f'<link rel="canonical" href="{SITE.url}/{tipo}/{ident}"' in h


def test_entidade_inexistente_ou_tipo_desconhecido_da_404(api):
    assert api.get("/meta/asn/999999999").status_code == 404
    assert api.get("/meta/asn/abc").status_code == 404
    assert api.get("/meta/uf/XX").status_code == 404
    assert api.get("/meta/cdncap/google").status_code == 404


def test_html_escapa_e_nao_traz_contato_nem_pessoa_fisica():
    from api.routes.meta import html_meta
    h = html_meta("operadora", "1", 'Fulano "Telecom" <script>', 'a & b "c"')
    assert "<script>" not in h and "&lt;script&gt;" in h
    assert "&quot;" in h


def test_meta_nao_entra_no_openapi(api):
    assert not any(p.startswith("/meta") for p in api.get("/api/v1/openapi.json").json()["paths"])
