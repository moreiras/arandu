# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4/T5 (PT-10b, decisão P8): S.A. no agrupamento societário, cenário 12 do dataset sintético. SemASN2 e SemASN3 são S.A. com quadro só de diretoria e conselho em comum
(não se ligam); SemASN2 é sócia com participação da Ltda SemASN1, e essa ligação, que vem do quadro da Ltda, continua."""
import asyncio
import json

import pytest

from tests.products.api_contract import ALLOWED
from tests.products.conftest import fake_pix
from tests.synth.world import T1, make_cnpj

LTDA = make_cnpj(200)       # Provedor Sem ASN 1 Ltda
SA_SOCIA = make_cnpj(201)   # Provedor Sem ASN 2 S.A.: sócia (22) da Ltda
SA_SOZINHA = make_cnpj(202)  # Provedor Sem ASN 3 S.A.: só gestão em comum com a outra S.A.
ROTULO = "grupo não inferível pelo quadro societário (S.A.)"


def _get(api, caminho, **params):
    r = api.get(f"/api/v1{caminho}", params={"date": T1, **params}, headers=ALLOWED)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_sa_ligada_so_por_diretores_nao_liga_e_aparece_nao_inferivel(api):
    rel = _get(api, f"/grupos/empresa/{SA_SOZINHA}")
    assert rel["grupo_id"] == f"ind_{SA_SOZINHA[:8]}" and not rel["mesmo_grupo"] and not rel["relacionadas_parcial"]
    assert rel["grupo_inferivel"] is False and rel["grupo_inferivel_rotulo"] == ROTULO and "diretoria e conselho, não acionistas" in rel["como_ler"]
    gs = rel["grupo_societario"]
    assert gs["classificacao"] == "individual" and gs["tamanho"] == 1 and gs["grupo_inferivel"] is False and gs["grupo_inferivel_motivo"] == "sa_quadro_sem_acionistas"
    g = _get(api, f"/grupos/{rel['grupo_id']}")
    assert g["grupo_inferivel"] is False and g["grupo_inferivel_rotulo"] == ROTULO and g["sociedades_anonimas"] == 1
    assert "Diretor SA Comum" not in json.dumps(rel, ensure_ascii=False)


def test_sa_socia_de_ltda_continua_ligada_pelo_quadro_da_ltda(api):
    sa = _get(api, f"/grupos/empresa/{SA_SOCIA}")
    ltda = _get(api, f"/grupos/empresa/{LTDA}")
    assert sa["grupo_id"] == ltda["grupo_id"] and sa["grupo_societario"]["tamanho"] == 2 and not sa["grupo_id"].startswith("ind_")
    assert sa["grupo_inferivel"] is False and "grupo_inferivel" not in ltda
    assert [r["cnpj"] for r in sa["relacionadas_parcial"] + sa["mesmo_grupo"]] == [LTDA]
    assert SA_SOZINHA not in {c["cnpj"] for c in _get(api, f"/grupos/{sa['grupo_id']}")["cnpjs"]}       # a outra S.A. não entra por diretor em comum


def test_lista_e_grupo_marcam_a_empresa_sa(api):
    grupos = _get(api, "/grupos")["grupos"]
    ind = next(g for g in grupos if g["grupo_id"] == f"ind_{SA_SOZINHA[:8]}")
    assert ind["grupo_inferivel"] is False and ind["grupo_inferivel_rotulo"] == ROTULO and ind["cnpjs"][0]["grupo_inferivel"] is False
    com = next(g for g in grupos if SA_SOCIA in {c["cnpj"] for c in g["cnpjs"]})
    assert "grupo_inferivel" not in com and com["sociedades_anonimas"] == 1
    assert {c["cnpj"] for c in com["cnpjs"] if c.get("grupo_inferivel") is False} == {SA_SOCIA}


def test_efeito_da_regra_conta_as_sa_no_publicado(pipeline):
    base, _ = pipeline
    from core.jsonio import carregar_json_gz
    d = carregar_json_gz(base / "published" / T1 / "grupos_societarios.json.gz")
    assert d["efeito_da_regra"]["sociedades_anonimas_sem_inferencia"] == 2 and d["regra_sociedade_anonima"]["naturezas"] == {"2046": "Sociedade Anônima Aberta", "2054": "Sociedade Anônima Fechada"}


@pytest.fixture(scope="module")
def srv(pipeline, api):
    base, _ = pipeline
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATA_DIR", str(base))
        from api.store import Store
        from mcp_server import app as m

        mp.setattr(m, "_store", Store(base))
        mp.setattr(Store, "_load_pix_config", lambda self: fake_pix())
        yield m


def _call(srv, nome, args):
    out = asyncio.run(srv.mcp.call_tool(nome, args))
    blocos = out[0] if isinstance(out, tuple) else out
    return json.loads("".join(getattr(b, "text", "") for b in blocos))


def test_mcp_operadora_grupo_traz_o_rotulo_da_sa(srv):
    g = _call(srv, "operadora_grupo", {"cnpj": SA_SOZINHA})
    assert g["grupo_inferivel"] is False and g["grupo_inferivel_rotulo"] == ROTULO and g["relacionadas"]["grupo_inferivel"] is False and "como_ler" in g["relacionadas"]
    assert "grupo_inferivel" not in _call(srv, "operadora_grupo", {"cnpj": LTDA})
    assert _call(srv, "grupo_perfil", {"grupo_id": g["grupo_id"]})["grupo_inferivel_rotulo"] == ROTULO
