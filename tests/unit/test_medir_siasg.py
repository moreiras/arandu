# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — `scripts/medir_siasg_contratos.py`: mede numa amostra, projeta e não grava no armazém de dados (API simulada com respx)."""
import importlib.util
from pathlib import Path

import httpx
import respx

from core import siasg
from core.common import write_json_gz
from sources.siasg_contratos import collect as fonte

ROOT = Path(__file__).resolve().parents[2]
RAIZES = ["11222333", "44555666", "77888999", "12345678"]


def _modulo():
    spec = importlib.util.spec_from_file_location("medir_siasg_contratos", ROOT / "scripts" / "medir_siasg_contratos.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _universo(base):
    norm = base / "normalized" / "2026-11-10" / "summary"
    norm.mkdir(parents=True)
    cn = {siasg.cnpj_matriz(r): {} for r in RAIZES}
    write_json_gz(norm / "anatel_scm.json.gz", {"by_cnpj": cn})
    write_json_gz(norm / "sici_acessos.json.gz", {"cnpjs": {siasg.cnpj_matriz(r): {"acessos": 5} for r in RAIZES[:2]}})


def _item(cnpj, n, compra):
    return {"idCompraItem": f"9100{n:05d}", "sequencialResultado": 1, "numeroControlePNCPCompra": compra, "unidadeOrgaoCodigoUnidade": "910001", "unidadeOrgaoUfSigla": "DF", "niFornecedor": cnpj,
            "tipoPessoa": "PJ", "orgaoEntidadeCnpj": "11000000000191", "quantidadeHomologada": 1, "valorTotalHomologado": 100.0 * n, "situacaoCompraItemResultadoNome": "Informado", "dataResultadoPncp": "2026-05-01T00:00:00"}


def test_mede_a_amostra_projeta_o_universo_e_nao_grava_no_armazem(tmp_path):
    base = tmp_path / "data"
    _universo(base)
    antes = sorted(p.relative_to(base).as_posix() for p in base.rglob("*"))

    def despachar(request: httpx.Request):
        p = dict(request.url.params)
        if request.url.path == siasg.ENDPOINT_RESULTADOS:
            ni = p["niFornecedor"]
            itens = [_item(ni, 1, "11000000000191-1-000001/2026"), _item(ni, 2, "11000000000191-1-000002/2026")] if ni.startswith("11222333") else []
            return httpx.Response(200, json={"resultado": itens, "totalRegistros": len(itens), "totalPaginas": 1 if itens else 0})
        return httpx.Response(200, json={"resultado": [{"numeroControlePNCP": p["codigo"], "orgaoEntidadeRazaoSocial": "ORGAO", "orgaoEntidadeEsferaId": "F", "unidadeOrgaoCodigoIbge": 5300108, "unidadeOrgaoMunicipioNome": "BRASÍLIA"}]})

    with respx.mock(base_url=siasg.BASE_URL, assert_all_called=False) as m:
        m.route().mock(side_effect=despachar)
        rel = _modulo().medir("2026-11-10", base, amostra=4, compras=5, espera_s=0)
    assert rel["universo"] == 4 and rel["faixa_a"] == 2 and rel["amostra_lida"] == 4 and rel["parada"] is None
    assert rel["por_raiz"]["fracao_com_resultado"] == 0.25 and rel["por_raiz"]["itens_media_das_com_resultado"] == 2.0 and rel["por_raiz"]["falhas"] == 0
    d = rel["detalhe_contratacao"]
    assert d["contratacoes_nas_raizes_lidas"] == 2 and d["amostra"] == 2 and d["com_esfera"] == 2 and d["com_municipio"] == 2 and d["contratacoes_por_item"] == 1.0
    assert rel["projecao_universo_inteiro"]["itens"] == 2 and rel["estado_comprimido_bytes_da_amostra"] > 0
    assert sorted(p.relative_to(base).as_posix() for p in base.rglob("*")) == antes                  # nada foi gravado no armazém


def test_bloqueio_encerra_a_medicao_e_diz_por_que(tmp_path):
    base = tmp_path / "data"
    _universo(base)
    with respx.mock(base_url=siasg.BASE_URL, assert_all_called=False) as m:
        m.route().mock(return_value=httpx.Response(403, text="forbidden"))
        rel = _modulo().medir("2026-11-10", base, amostra=4, compras=5, espera_s=0)
    assert "403" in rel["parada"] and rel["amostra_lida"] == 0 and rel["projecao_universo_inteiro"] is None
    assert fonte.Bloqueio.__name__ == "Bloqueio"
