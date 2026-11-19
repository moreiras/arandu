# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — ligação por referência entre camadas: a API pede o enriquecedor sem importar `products`."""
import pytest

from core import plugins


def test_enriquecedor_padrao_e_o_do_produto(monkeypatch):
    monkeypatch.delenv("ARANDU_ENRIQUECEDOR", raising=False)
    from products.asn_saude.enrich import enrich_asn_document
    assert plugins.enriquecedor_de_asn() is enrich_asn_document


@pytest.mark.parametrize("valor", ["off", "OFF", "", "none", "nenhum"])
def test_desligar_o_enriquecedor_por_configuracao(monkeypatch, valor):
    monkeypatch.setenv("ARANDU_ENRIQUECEDOR", valor)
    assert plugins.enriquecedor_de_asn() is None


def test_referencia_invalida_falha_alto(monkeypatch):
    with pytest.raises(ValueError):
        plugins.resolver("sem_dois_pontos")
    with pytest.raises(ImportError):
        plugins.resolver("modulo.que.nao.existe:f")
    with pytest.raises(AttributeError):
        plugins.resolver("core.plugins:nao_existe")


def test_store_serve_sem_enriquecedor_quando_desligado(tmp_path, monkeypatch):
    """Com o enriquecedor desligado, `asn_full` devolve o documento publicado como está (sem tocar em `products`)."""
    import json
    from api.store import Store
    monkeypatch.setenv("ARANDU_ENRIQUECEDOR", "off")
    pub = tmp_path / "published" / "2026-10-24" / "asns"
    pub.mkdir(parents=True)
    (pub / "64500.json").write_text(json.dumps({"asn": 64500, "is_br": False}), encoding="utf-8")
    (tmp_path / "published" / "2026-10-24" / "manifest.json").write_text("{}", encoding="utf-8")
    assert Store(tmp_path).asn_full("2026-10-24", 64500) == {"asn": 64500, "is_br": False}
