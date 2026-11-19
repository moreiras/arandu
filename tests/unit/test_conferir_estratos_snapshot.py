# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`scripts/conferir_estratos_snapshot.py`: critérios dos estratos de evidência sobre um documento publicado de relações."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("conferir", Path(__file__).resolve().parents[2] / "scripts" / "conferir_estratos_snapshot.py")
conf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(conf)


def _l(a, b, nivel="provavel", estrato="ambos", p_cal=0.9, afi=("v4",), tipo="p2c"):
    return {"a": a, "b": b, "tipo": tipo, "nivel": nivel, "afi": list(afi), "estrato": estrato, "p_calibrada": p_cal}


def _doc(linhas, data="2026-11-13", coletores=None):
    return {"snapshot_date": data, "algoritmo": "ARC v2", "estratos": {"ativo": True, "medido_em": "2026-11-11", "rebaixados": {}, "elos_por_estrato": {}},
            "entradas": {"coletores": coletores or {"v4": ["rv2", "rv4"], "v6": ["rv2"]}}, "relacoes": linhas}


def test_snapshot_antigo_sem_estratos_sai_com_codigo_de_ausencia():
    r = conf.conferir({"snapshot_date": "2026-11-06", "relacoes": [{"a": 1, "b": 2, "tipo": "p2c", "nivel": "provavel", "afi": ["v4"]}]})
    assert r["tem_campos_v1_5_63"] is False and r["ok"] is False


def test_rebaixo_so_deixa_declarado_e_confirmado_nos_estratos_sem_evidencia():
    """Só `provavel` vira `possivel`; `declarado` (ASPA) e `confirmado` (route server) ficam."""
    ok = conf.rebaixo(_doc([_l(1, 2), _l(3, 4, "declarado", "sem_evidencia", None), _l(5, 6, "possivel", "conflito", None),
                            _l(7, 8, "confirmado", "conflito", None)]))
    assert ok == {"por_estrato": {"ambos": 1, "conflito": 1, "sem_evidencia": 1}, "mantidos_por_nivel": {"confirmado": 1, "declarado": 1}, "indevidos": 0, "ok": True}
    ruim = conf.rebaixo(_doc([_l(1, 2, "provavel", "conflito", None)]))
    assert ruim["indevidos"] == 1 and ruim["ok"] is False


def test_cobertura_por_familia_contra_o_piso_de_70_por_cento():
    linhas = [_l(i, i + 100, afi=("v4",)) for i in range(7)] + [_l(i, i + 200, p_cal=None, afi=("v4",)) for i in range(3)]      # v4: 7 de 10
    linhas += [_l(i, i + 300, afi=("v6",)) for i in range(2)] + [_l(i, i + 400, p_cal=None, afi=("v6",)) for i in range(3)]    # v6: 2 de 5
    c = conf.cobertura(_doc(linhas))
    assert c["v4"]["fracao"] == 0.7 and c["v4"]["ok"] is True
    assert c["v6"]["fracao"] == 0.4 and c["v6"]["ok"] is False


def test_estabilidade_dentro_dos_limites_e_coletores_iguais():
    base = [_l(i, i + 1000) for i in range(100)]
    atual = _doc(base[:99] + [_l(5000, 5001)], "2026-11-13")                    # 1 saiu, 1 entrou
    e = conf.estabilidade(atual, _doc(base, "2026-11-06"))
    assert e["saiu_pct"] == 1.0 and e["entrou_pct"] == 1.0 and e["mudou_de_classe_pct"] == 0.0 and e["mesmos_coletores"] is True
    assert e["jaccard"] == round(99 / 101, 4) and e["ok"] is True


def test_estabilidade_falha_com_coletores_diferentes_ou_muita_mudanca():
    base = [_l(i, i + 1000) for i in range(100)]
    outros = conf.estabilidade(_doc(base, coletores={"v4": ["rv2"], "v6": ["rv2"]}), _doc(base, "2026-11-06"))
    assert outros["mesmos_coletores"] is False and outros["ok"] is False and "conjunto de coletores diferente" in outros["nota"]
    muita = conf.estabilidade(_doc([_l(i, i + 1000) for i in range(90)] + [_l(i, i + 9000) for i in range(10)]), _doc(base, "2026-11-06"))
    assert muita["saiu_pct"] == 10.0 and muita["ok"] is False
    inverte = conf.estabilidade(_doc([_l(i + 1000, i) for i in range(100)]), _doc(base, "2026-11-06"))                      # o provedor virou cliente
    assert inverte["mudou_de_classe_pct"] == 100.0 and inverte["ok"] is False
