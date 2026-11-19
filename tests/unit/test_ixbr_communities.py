# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Decodificação das communities do IX.br pelo dicionário do Alice: dicionário real reduzido de `tests/fixtures/raw/ixbr_alice_rotas/`."""
import json
from pathlib import Path

import pytest

from core.ixbr_communities import Dicionario, chaves_da_rota

DIC = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "raw" / "ixbr_alice_rotas" / "dicionario.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def d():
    return Dicionario(DIC)


@pytest.mark.parametrize("c,classe,rotulo", [
    ("26162:190:4", "rejeicao", "Never via route server"),
    ("26162:100:0", "rejeicao", "Invalid on Registro.br"),
    ("26162:300:0", "rejeicao", "Invalid on RPKI"),
    ("26162:400:0", "rejeicao", "Invalid on RIRs"),
    ("26162:300:1", "rpki", "RPKI válido"),
    ("26162:300:2", "rpki", "RPKI desconhecido (not found)"),
    ("65535:666", "blackhole", "Blackhole"),
    ("65535:616:666", "blackhole", "Blackhole"),
    ("26162:616:666", "blackhole", "Confirmed blackhole"),
    ("65000:0:4200000200", "nao_exportar_para", "No export to AS4200000200"),
    ("65001:0:64496", "exportar_somente_para", "Only export to AS64496"),
    ("65002:0:5", "nao_exportar_rir", "No export to Brasil ASNs"),
    ("65003:0:3", "exportar_somente_rir", "Only export to Lacnic ASNs"),
    ("65004:0:65021", "nao_exportar_ptt", "No export to IX.br Rio de Janeiro/RJ"),
    ("65010:0:100", "nao_exportar_rtt", "No export to RTT > 100ms"),
    ("65011:0:10", "nao_exportar_perda", "No export to packet loss > 10%"),
    ("26162:0:65085", "informativa", "IX.br Fortaleza/CE"),
    ("26162:0:64496", "informativa", "Prefix being announced by AS64496"),
    ("26162:100:2", "informativa", "Unknown on Registro.br"),
    ("26162:6939", "informativa", "Prefix being announced by AS6939"),
])
def test_classes_pelo_dicionario(d, c, classe, rotulo):
    r = d.classificar(c)
    assert (r["classe"], r["rotulo"]) == (classe, rotulo)


def test_communities_padrao_e_estendida_de_acao_sao_lidas_como_a_grande_equivalente_e_rotuladas():
    d = Dicionario(DIC)
    p, e = d.classificar("65000:64510"), d.classificar("rt:65000:262704")
    assert (p["classe"], p["alvo"], p["forma"], p["rotulo"]) == ("nao_exportar_para", 64510, "equivalente_padrao", "No export to AS64510")
    assert (e["classe"], e["alvo"], e["forma"]) == ("nao_exportar_para", 262704, "equivalente_padrao")
    assert d.classificar("65001:64496")["classe"] == "exportar_somente_para"
    assert d.classificar("ro:26162:6939")["classe"] == "outra"          # origem/route-target do próprio IX.br: sem decodificação no dicionário
    assert d.classificar("64496:10")["forma"] == "nao_decodificada"      # community própria do membro


def test_motivo_so_vale_na_community_grande_e_dicionario_vazio_nao_quebra():
    d = Dicionario(DIC)
    assert d.motivo_de_rejeicao("26162:65130") is None                  # a padrão 26162:65130 é só informativa (o motivo vem da grande: sem contar duas vezes)
    assert d.classificar("26162:65130")["classe"] == "informativa"
    vazio = Dicionario(None)
    assert vazio.vazio and vazio.classificar("26162:190:4")["classe"] == "outra" and vazio.classificar("65535:666")["classe"] == "blackhole"


def test_chaves_da_rota_juntam_as_tres_formas():
    bgp = {"communities": [[65000, 1]], "large_communities": [[26162, 190, 4]], "ext_communities": [["rt", 65000, 7]]}
    assert chaves_da_rota(bgp) == ["65000:1", "26162:190:4", "rt:65000:7"] and chaves_da_rota({}) == []
