# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — Cetic.br (microdados da TIC Domicílios → estimativas por UF): base sintética no layout original, sem rede."""
import gzip
import math

import httpx
import pytest
import respx

from core import cetic, cetic_microdados as md
from core.common import read_json_gz
from sources.cetic_tic_domicilios_microdados import collect as fonte

CSV = "tic_domicilios_2025_domicilios_base_de_microdados_v1.0.csv"


def _base(fx) -> bytes:
    return gzip.decompress(fx("cetic", "tic_domicilios_microdados_sintetico.csv.gz").read_bytes())


def test_estimativa_bate_com_o_calculo_direto_nas_200_replicas(fx):
    grupos, lidas = md.estimar(_base(fx))
    assert lidas == 26 * 36 + 12 and set(grupos) >= {"BR", "SP", "Sudeste"} and sum(g["tipo"] == "uf" for g in grupos.values()) == 27
    import csv
    leitor = csv.DictReader(gzip.decompress(fx("cetic", "tic_domicilios_microdados_sintetico.csv.gz").read_bytes()).decode("latin-1").splitlines(), delimiter=";")
    sp = [r for r in leitor if r["COD_UF"] == "35"]
    num = lambda x: float(x.replace(",", "."))
    w = sum(num(r["PESO"]) for r in sp)
    p = 100 * sum(num(r["PESO"]) for r in sp if r["A4"] == "1") / w
    reps = [100 * sum(num(r[f"REP{i}"]) for r in sp if r["A4"] == "1") / sum(num(r[f"REP{i}"]) for r in sp) for i in range(1, 201)]
    se = math.sqrt(sum((x - p) ** 2 for x in reps) / 200)
    e = grupos["SP"]["indicadores"]["internet"]
    assert e["proporcao"] == pytest.approx(p, abs=0.001) and e["erro_padrao"] == pytest.approx(se, abs=0.001) and e["margem"] == pytest.approx(1.96 * se, abs=0.002)
    assert grupos["SP"]["n"] == 36 and grupos["SP"]["domicilios"] == round(w) and e["total"] == round(sum(num(r["PESO"]) for r in sp if r["A4"] == "1"))


def test_uf_com_amostra_pequena_e_suprimida_sem_inventar_numero(fx):
    grupos, _ = md.estimar(_base(fx))
    ap = grupos["AP"]
    assert ap["n"] == 12 and all(set(v) == {"suprimido"} for v in ap["indicadores"].values())
    assert "menos de 30" in ap["indicadores"]["internet"]["suprimido"]
    assert "proporcao" in grupos["BR"]["indicadores"]["internet"]                        # o Brasil usa todos os domicílios, inclusive os do AP


def test_layout_diferente_falha_alto():
    with pytest.raises(RuntimeError, match="colunas ausentes"):
        md.estimar('"COD_UF";"PESO"\n"11";"1,0"\n'.encode("latin-1"))


def test_validacao_contra_a_tabela_oficial_usa_o_mesmo_recorte(fx):
    grupos, _ = md.estimar(_base(fx))
    t, linhas = cetic.normalizar(fx("cetic", "tic_domicilios_2025_domicilios_tabelas_xlsx_v1.0.zip").read_bytes(), 10)
    v = md.validar(grupos, {"linhas": linhas})
    assert v["comparados"] == 12 and v["tabelas"] == ["A1", "A4"]                      # Brasil + 5 regiões, em dois indicadores
    assert md.validar(grupos, None) is None


@respx.mock
def test_run_grava_bruto_comprimido_e_so_agregados_no_normalizado(fx, tmp_path):
    corpo = _base(fx)
    html = '<a href="https://cetic.br/media/microdados/1018/' + CSV + '">CSV</a>'
    respx.get("https://cetic.br/pt/pesquisa/domicilios/microdados/").mock(return_value=httpx.Response(200, text=html))
    respx.get("https://cetic.br/media/microdados/1018/" + CSV).mock(return_value=httpx.Response(200, content=corpo))

    class Log:
        def info(self, *a, **k): pass

    monkey = pytest.MonkeyPatch()
    monkey.setattr(fonte, "MINIMO_LINHAS", 500)
    try:
        r = fonte.run("2026-11-01", tmp_path, Log(), dormir=lambda s: None)
    finally:
        monkey.undo()
    assert r == {"edicao": 2025, "domicilios": 26 * 36 + 12, "grupos": 33}
    assert gzip.decompress((tmp_path / "raw" / "2026-11-01" / "summary" / (CSV + ".gz")).read_bytes()) == corpo
    doc = read_json_gz(tmp_path / "normalized" / "2026-11-01" / "summary" / "cetic_tic_domicilios_uf.json.gz")
    assert doc["natureza"] == "estimativa_arandurape" and doc["metodo"]["replicas"] == 200 and doc["edicao"] == 2025
    assert "QUEST" not in str(doc) and "ID_DOMICILIO" not in str(doc) and "REP1" not in str(doc)       # só agregados
