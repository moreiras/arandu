# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Mapeamento PTT do IX.br <-> registro do PeeringDB (PT-24 / INST-E5.1): a cobertura "N de 40 PTTs em alguma instalação" só vale se o mapeamento bate com os PTTs do site.

O defeito apontado na análise (um código `santa-maria` que não é PTT do site e nenhuma entrada para Ribeirão Preto) não se reproduz na configuração atual; este teste
impede a volta: todo código `ixbr` do mapeamento existe em `config/ixps.yaml` e todo PTT do site tem entrada no mapeamento ou consta de `SEM_REGISTRO_NO_PEERINGDB`.
"""
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2] / "config"
#: PTTs do site sem registro ligado no PeeringDB (a cobertura os nomeia à parte, não os soma como "sem instalação"); vazio hoje
SEM_REGISTRO_NO_PEERINGDB: set[str] = set()


def _carregar():
    site = {x["code"] for x in yaml.safe_load((RAIZ / "ixps.yaml").read_text(encoding="utf-8"))["ixps"]}
    mapa = yaml.safe_load((RAIZ / "peeringdb_ixps.yaml").read_text(encoding="utf-8"))
    return site, mapa


def test_todo_codigo_ixbr_do_mapeamento_e_ptt_do_site():
    site, mapa = _carregar()
    estranhos = sorted(x["code"] for x in mapa["ixbr"] if x["code"] not in site)
    assert not estranhos, f"códigos do mapeamento que não são PTT do site (a página de instalação apontaria para /ixp/<código> inexistente): {estranhos}"


def test_todo_ptt_do_site_tem_entrada_ou_esta_na_lista_de_sem_registro():
    site, mapa = _carregar()
    com_entrada = {x["code"] for x in mapa["ixbr"]}
    assert not (site - com_entrada - SEM_REGISTRO_NO_PEERINGDB), sorted(site - com_entrada - SEM_REGISTRO_NO_PEERINGDB)


def test_cada_registro_do_peeringdb_serve_a_um_so_ptt_e_nao_ha_codigo_repetido():
    _, mapa = _carregar()
    ids = [x["pdb_ix_id"] for x in mapa["ixbr"] + mapa["external"] if x.get("pdb_ix_id") is not None]
    codigos = [x["code"] for x in mapa["ixbr"]]
    assert len(ids) == len(set(ids)), "pdb_ix_id repetido: dois PTTs ligados ao mesmo registro do PeeringDB"
    assert len(codigos) == len(set(codigos))
