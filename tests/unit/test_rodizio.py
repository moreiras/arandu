# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — peças comuns da coleta em rodízio (`core/rodizio.py`)."""
from core import rodizio
from core.common import write_json_gz


def _grava(base, dia, arquivo, doc):
    d = base / "normalized" / dia / "summary"
    d.mkdir(parents=True, exist_ok=True)
    write_json_gz(d / arquivo, doc)


def test_anterior_normalizado_pega_o_mais_recente_antes_da_data(tmp_path):
    _grava(tmp_path, "2026-11-01", "x.json.gz", {"d": 1})
    _grava(tmp_path, "2026-11-03", "x.json.gz", {"d": 3})
    _grava(tmp_path, "2026-11-05", "x.json.gz", {"d": 5})
    (tmp_path / "normalized" / "2026-11-04" / "summary").mkdir(parents=True)          # pasta sem o arquivo: ignorada
    assert rodizio.anterior_normalizado(tmp_path, "2026-11-05", "x.json.gz") == {"d": 3}
    assert rodizio.anterior_normalizado(tmp_path, "2026-11-05", "x.json.gz", incluir_data=True) == {"d": 5}
    assert rodizio.anterior_normalizado(tmp_path, "2026-11-01", "x.json.gz") == {}
    assert rodizio.anterior_normalizado(tmp_path / "nada", "2026-11-05", "x.json.gz") == {}


def test_escolher_por_idade_sem_leitura_primeiro_depois_a_mais_antiga():
    lidas = {1: "2026-11-03", 2: "2026-11-01", 3: None, 4: "", 5: "2026-11-02"}
    assert rodizio.escolher_por_idade([1, 2, 3, 4, 5], lidas.get, 3) == [3, 4, 2]
    assert rodizio.escolher_por_idade([5, 4, 3, 2, 1], lidas.get, 3) == [3, 4, 2]          # estável, independe da ordem de entrada
    assert rodizio.escolher_por_idade([1, 2], lidas.get, 0) == [2, 1]                      # sem limite: todos, mesma ordem


def test_limitador_dorme_so_o_que_falta():
    t = [0.0]
    dormiu = []

    def dormir(s):
        dormiu.append(round(s, 3))
        t[0] += s

    lim = rodizio.Limitador(1.0, relogio=lambda: t[0], dormir=dormir)
    lim.esperar()                      # primeira: sem espera
    t[0] += 0.4                        # a requisição levou 0,4 s
    lim.esperar()
    lim.esperar()
    assert dormiu == [0.6, 1.0]


def test_orcamento_para_por_requisicoes_tempo_ou_falhas_seguidas():
    t = [0.0]
    o = rodizio.Orcamento(requisicoes=3, tempo_max_s=100, falhas_seguidas_max=2, relogio=lambda: t[0])
    assert o.motivo_parada() is None
    o.falha()
    o.sucesso()
    o.falha()
    assert o.motivo_parada() is None and o.falhas == 2             # a falha isolada não para
    o.falha()
    assert "falhas seguidas" in o.motivo_parada()
    o2 = rodizio.Orcamento(requisicoes=2)
    o2.gastar(2)
    assert "orçamento" in o2.motivo_parada()
    t[0] = 101
    assert "tempo máximo" in o.motivo_parada()
    o3 = rodizio.Orcamento(tempo_max_s=10, relogio=lambda: t[0])
    t[0] += 11
    assert "tempo máximo" in o3.motivo_parada()
    assert rodizio.Orcamento().motivo_parada() is None              # sem limites: nunca para


def test_herdar_mantem_o_que_a_rodada_nao_renovou_com_a_data_original():
    ant = {"a": {"v": 1, "em": "2026-11-01T00:00:00Z"}, "b": {"v": 2, "em": "2026-11-02T00:00:00Z"}, "c": {"v": 3, "em": "2026-09-01T00:00:00Z"}}
    novos = {"b": {"v": 20, "em": "2026-11-09T00:00:00Z"}}
    out = rodizio.herdar(ant, novos)
    assert out["b"] == {"v": 20, "em": "2026-11-09T00:00:00Z"} and "herdado" not in out["b"]
    assert out["a"] == {"v": 1, "em": "2026-11-01T00:00:00Z", "herdado": True}
    assert "c" in out
    assert "a" not in rodizio.herdar(ant, novos, vivos={"b", "c"})                            # item que saiu do universo
    assert "c" not in rodizio.herdar(ant, novos, max_idade_dias=30, data="2026-11-09")        # velho demais
    assert "a" in rodizio.herdar(ant, novos, max_idade_dias=30, data="2026-11-09")


def test_limitador_continuar_de_conta_a_partir_da_ultima_requisicao_do_outro():
    t = [0.0]
    dormiu = []

    def dormir(s):
        dormiu.append(round(s, 3))
        t[0] += s

    rapido = rodizio.Limitador(1.0, relogio=lambda: t[0], dormir=dormir)
    rapido.esperar()
    t[0] += 0.2
    lento = rodizio.Limitador(10.0, relogio=lambda: t[0], dormir=dormir).continuar_de(rapido)
    lento.esperar()                       # a última requisição foi há 0,2 s: faltam 9,8 s
    assert dormiu == [9.8]
