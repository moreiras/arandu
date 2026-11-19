# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — leitura das outorgas no Store: uma implementação, a mesma interface pública dos quatro serviços."""
import gzip
import json

import pytest

from api import outorgas_store as os_
from api.store import Store

DATA = "2026-10-11"


def _publicar(base, sigla, chave):
    pub = base / DATA
    (pub / "maps").mkdir(parents=True)
    dados = {
        chave: [{"cnpj": "1", "razao_social": "A", "telefone": "11", "email": "a@x"},
                {"cnpj": "2", "razao_social": "B", "telefone": "22", "email": "b@x"}],
        "by_cnpj": {"1": [{"cnpj": "1", "telefone": "11", "email": "a@x"}], "2": [{"cnpj": "2", "telefone": "22", "email": "b@x"}]},
        "cnpj_to_asns": {"1": [64500], "2": [64501], "3": [64502]},        # o 3 não tem outorga
    }
    with gzip.open(pub / f"{sigla}.json.gz", "wt", encoding="utf-8") as f:
        json.dump(dados, f)
    (pub / "maps" / os_.SERVICOS[sigla][1]).write_text(json.dumps({"type": "FeatureCollection", "features": []}))
    return lambda d: base / d


@pytest.mark.parametrize("sigla", sorted(os_.SERVICOS))
def test_contatos_so_saem_por_asn_e_pelo_caminho_protegido(sigla, tmp_path):
    chave = os_.SERVICOS[sigla][0]
    o = os_.OutorgasPublicadas(_publicar(tmp_path, sigla, chave), sigla)
    assert [r["cnpj"] for r in o.index(DATA)] == ["1", "2"]
    assert all("telefone" not in r and "email" not in r for r in o.index(DATA))
    assert all("telefone" not in r for r in o.for_cnpj(DATA, "1"))
    assert o.for_cnpj_with_contacts(DATA, "1")[0]["telefone"] == "11"
    assert o.for_asn(DATA, 64501)[0]["email"] == "b@x"                     # único caminho per-AS mantém contato
    assert o.asn_set(DATA) == frozenset({64500, 64501})                    # 64502 não tem outorga
    assert o.geo_map(DATA) == {"type": "FeatureCollection", "features": []}


def test_sem_arquivo_devolve_vazio_sem_quebrar(tmp_path):
    o = os_.OutorgasPublicadas(lambda d: tmp_path / d, "scm")
    assert o.load(DATA) is None and o.index(DATA) == [] and o.for_cnpj(DATA, "1") == []
    assert o.for_asn(DATA, 1) == [] and o.asn_set(DATA) == frozenset() and o.geo_map(DATA) is None


def test_arquivo_corrompido_vira_none(tmp_path):
    (tmp_path / DATA).mkdir()
    (tmp_path / DATA / "smp.json.gz").write_bytes(b"nao e gzip")
    assert os_.OutorgasPublicadas(lambda d: tmp_path / d, "smp").load(DATA) is None


def test_store_mantem_a_interface_publica_dos_quatro_servicos():
    esperados = {f"{s}_{m}" for s in os_.SERVICOS for m in ("index", "for_cnpj", "for_cnpj_with_contacts", "for_asn", "asn_set", "geo_map")}
    esperados |= {f"_load_{s}" for s in os_.SERVICOS}
    assert esperados <= set(dir(Store))
    assert Store.scm_index.__name__ == "scm_index" and "SEM contatos" in Store.smp_index.__doc__
