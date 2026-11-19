# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Sub-asignações de IPv4: artefato aguardando a fonte oficial e, com a fonte hipotética ativada, validações e eventos."""
import json

from core.common import write_json_gz
from core.jsonio import carregar_json_gz
from products.ipv4_subasig import build as B


class _Log:
    def info(self, *a, **k): pass
    warning = info


def test_sem_fonte_oficial_o_artefato_diz_aguardando_e_traz_o_vigia(tmp_path):
    pasta = tmp_path / "ops" / "vigia" / "ipv4"
    pasta.mkdir(parents=True)
    (pasta / "2026-11-01.json").write_text(json.dumps({"alertas": []}))
    (pasta / "2026-11-02.json").write_text(json.dumps({"alertas": [{"tipo": "padrao_novo", "url": "u/", "nome": "bitacora.json", "padrao": "bitacora.json", "data": "x", "tamanho": "1K"}]}))
    r = B.publicar_ipv4_subasig(tmp_path, "2026-11-02", _Log())
    assert r == {"ativa": False, "registros": 0, "eventos": 0}
    d = carregar_json_gz(tmp_path / "published" / "2026-11-02" / "ipv4" / "subasignacoes.json.gz")
    assert d["ativa"] is False and d["aguardando"] is True and "Aguardando a publicação oficial" in d["aviso"] and d["natureza"] == "indisponivel" and d["esquema_hipotetico"] is True
    assert d["vigia"]["ultima_varredura"] == "2026-11-02" and d["vigia"]["alertas_30_dias"][0]["nome"] == "bitacora.json" and d["indicador_terceiros"]["com_registro"] is None
    assert set(d["validacoes"]) == {"receptor_origina", "tem_roa", "tamanho", "receptor_ipv6", "prazo_3_anos", "nao_infra_critica"}


def test_com_a_fonte_ativada_valida_cada_registro_e_separa_anuncios_com_e_sem_registro(tmp_path):
    d = "2026-12-02"
    norm = tmp_path / "normalized" / d / "summary"
    write_json_gz(norm / "ipv4_subasignacoes.json.gz", {"ignoradas": 1, "registros": [
        {"id": "a", "bloco": "198.18.0.0/24", "receptor_asn": 64500, "inicio": "2026-12-01", "fim": None, "cedente_asn": 64496, "rir": None},
        {"id": "b", "bloco": "198.18.2.0/24", "receptor_asn": 64501, "inicio": "2026-12-01", "fim": None, "cedente_asn": None, "rir": None}]})
    write_json_gz(norm / "origin-prefixes-v4.json.gz", {"64500": ["198.18.0.0/24"], "300": ["198.18.2.0/24"], "64502": ["198.18.3.0/24"]})
    write_json_gz(tmp_path / "published" / d / "rpki" / "vrp_list.json.gz", [{"asn": 64500, "prefix": "198.18.0.0/24", "maxLength": 24}])
    write_json_gz(norm / "ipv4_listas.json.gz", {"transferencias_registrobr": [{"data": "2025-06-01", "blocos": ["198.18.0.0/24"]}]})
    write_json_gz(tmp_path / "published" / d / "ipv4" / "uso_por_terceiros.json.gz", {"itens": [
        {"inicio": "198.18.0.0", "quantidade": 256, "origens": [64500], "sinais": [{"id": "S1"}]}, {"inicio": "198.18.2.0", "quantidade": 256, "origens": [300], "sinais": [{"id": "S1"}]},
        {"inicio": "198.18.3.0", "quantidade": 256, "origens": [64502], "sinais": [{"id": "S3"}]}]})
    r = B.publicar_ipv4_subasig(tmp_path, d, _Log())
    doc = carregar_json_gz(tmp_path / "published" / d / "ipv4" / "subasignacoes.json.gz")
    a, b = doc["subasignacoes"]
    assert r["ativa"] is True and doc["aguardando"] is False and doc["aviso"] is None and doc["natureza"] == "observado" and doc["ignoradas"] == 1
    assert a["validacoes"]["receptor_origina"] is True and a["validacoes"]["tem_roa"] is True and a["validacoes"]["prazo_3_anos"] is False and a["em_conformidade"] is False
    assert b["validacoes"]["receptor_origina"] is False and b["validacoes"]["tem_roa"] is False and "receptor_ipv6" in b["pendentes"] and "nao_infra_critica" in b["pendentes"]
    assert doc["indicador_terceiros"]["com_registro"] == 1 and doc["indicador_terceiros"]["sem_registro"] == 2              # só o bloco de 64500 tem sub-asignação do anunciante
    assert [e["tipo"] for e in doc["eventos"]] == ["subasignacao_inicio", "subasignacao_inicio"]


def test_eventos_inicio_e_fim_entre_snapshots():
    ant = [{"id": "a", "bloco": "x", "receptor_asn": 1, "fim": None}, {"id": "b", "bloco": "y", "receptor_asn": 2, "fim": None}]
    atu = [{"id": "b", "bloco": "y", "receptor_asn": 2, "fim": None}, {"id": "c", "bloco": "z", "receptor_asn": 3, "fim": None}]
    ev = B.eventos(ant, atu, "2026-12-03")
    assert {(e["tipo"], e["id"]) for e in ev} == {("subasignacao_inicio", "c"), ("subasignacao_fim", "a")}
