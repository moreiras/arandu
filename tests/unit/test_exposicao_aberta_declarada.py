# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — as 11 fontes com `exposicao: aberta` por decisão do projeto (D9, FONT-E7) declaram a decisão e a atribuição, no catálogo e em /fontes."""
import json
from pathlib import Path

import pytest

from core.catalog.loader import load_catalog

ROOT = Path(__file__).resolve().parents[2]
ABERTAS_POR_DECISAO = ["cloudflare_radar", "ooni_bloqueios", "peeringdb_fac", "peeringdb_intl_geo", "peeringdb_ixps", "peeringdb_networks",
                       "scm_geo", "seac_geo", "smp_geo", "stfc_geo", "telegeography_cables"]
PEERINGDB = ["peeringdb_fac", "peeringdb_intl_geo", "peeringdb_ixps", "peeringdb_networks"]


@pytest.fixture(scope="module")
def catalogo():
    return load_catalog()


@pytest.mark.parametrize("id_", ABERTAS_POR_DECISAO)
def test_fonte_aberta_por_decisao_declara_decisao_e_atribuicao(catalogo, id_):
    s = catalogo.sources[id_]
    assert s.publicavel and s.exposicao == "aberta"
    assert s.decisao_exposicao and "decisão do projeto" in s.decisao_exposicao and "D9" in s.decisao_exposicao
    assert s.atribuicao and len(s.atribuicao) >= 10


@pytest.mark.parametrize("id_", PEERINGDB)
def test_fontes_peeringdb_registram_a_abertura_como_decisao_do_projeto_sem_a_aup(catalogo, id_):
    """PT-12b (revisão da D9, 2026-11-25): o PTT externo não exige login; o catálogo não justifica a abertura (nem o login) pela AUP."""
    t = catalogo.sources[id_].decisao_exposicao
    assert "decisão do projeto" in t
    assert "AUP" not in t and "redistribuição" not in t and "exigem login" not in t and "exige login" not in t


def test_atribuicao_cita_a_licenca_que_o_catalogo_declara(catalogo):
    esperado = {"cloudflare_radar": "CC BY-NC 4.0", "ooni_bloqueios": "CC BY-NC-SA 4.0", "telegeography_cables": "CC BY-SA 4.0",
                "scm_geo": "ODbL", "seac_geo": "ODbL", "smp_geo": "ODbL", "stfc_geo": "ODbL", "peeringdb_intl_geo": "ODbL"}
    for id_, licenca in esperado.items():
        assert licenca in catalogo.sources[id_].atribuicao, id_
        assert licenca.split()[0] in catalogo.sources[id_].origem.licenca, id_
    for id_ in ("scm_geo", "seac_geo", "smp_geo", "stfc_geo"):
        assert catalogo.sources[id_].atribuicao.startswith("Fonte: Anatel") and "ODbL" in catalogo.sources[id_].atribuicao, id_
    for id_ in PEERINGDB:
        a = catalogo.sources[id_].atribuicao
        assert a.startswith("Fonte: PeeringDB") and "AUP" not in a and "verificada" not in a, id_
    for id_ in ("peeringdb_fac", "peeringdb_ixps", "peeringdb_networks"):
        assert catalogo.sources[id_].atribuicao == "Fonte: PeeringDB", id_


def test_decisao_so_vale_com_exposicao_aberta(catalogo):
    from core.catalog.schema import Source

    s = catalogo.sources["peeringdb_contacts"].model_dump()          # exposição `login`
    with pytest.raises(ValueError, match="decisao_exposicao"):
        Source(**{**s, "decisao_exposicao": "x"})


def test_fontes_publicas_levam_decisao_e_atribuicao_ao_frontend():
    """`frontend/public/catalogo.json` (a base de /fontes) traz os dois campos das 11 fontes e `exposicao` de todas."""
    cat = json.loads((ROOT / "frontend" / "public" / "catalogo.json").read_text(encoding="utf-8"))
    por_id = {f["id"]: f for f in cat["fontes"]}
    for id_ in ABERTAS_POR_DECISAO:
        assert por_id[id_]["exposicao"] == "aberta" and por_id[id_]["decisao_exposicao"] and por_id[id_]["atribuicao"], id_
    assert all("exposicao" in f for f in cat["fontes"])
