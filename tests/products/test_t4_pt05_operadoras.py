# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 (PT-05): Operadoras SMP: universo da aba e credenciada sem selo SMP (OPERADORAS-E2, OPERADORA-E8/E9)."""
from tests.products.api_contract import ALLOWED
from tests.synth import market
from tests.synth.world import T1, build_world

OPS = market.operators(build_world(T1))
CRED = OPS[33]                       # credenciada de rede virtual sem outorga SMP própria (com ASN e SCM, sem SICI móvel)


def _get(api, caminho, **params):
    r = api.get(f"/api/v1{caminho}", params={"date": T1, **params}, headers=ALLOWED)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_aba_smp_sem_ativo_lista_o_universo(api):
    """OPERADORAS-E2: sem `ativo` a lista móvel é o universo (antes caía no padrão `true` da lista fixa)."""
    todos = _get(api, "/acessos/operadoras", servico="movel")
    sim = _get(api, "/acessos/operadoras", servico="movel", ativo="true")
    nao = _get(api, "/acessos/operadoras", servico="movel", ativo="false")
    assert sim["total"] == 3 and nao["total"] == 1
    assert todos["total"] == sim["total"] + nao["total"] == 4
    assert [r["cnpj"] for r in nao["items"]] == [CRED["cnpj"]]
    # a lista fixa mantém o padrão de sempre (só quem declara)
    assert _get(api, "/acessos/operadoras")["total"] == _get(api, "/acessos/operadoras", ativo="true")["total"]


def test_credenciada_de_rede_virtual_nao_tem_selo_smp(api):
    """OPERADORA-E8/E9: o registro de credenciamento continua nas outorgas do CNPJ, mas não acende `has_smp`."""
    asn = CRED["asns"][0]
    linhas = _get(api, "/asns", q=str(asn), limit=50)["items"]
    a = next(x for x in linhas if x["asn"] == asn)
    assert a["has_smp"] is False and a["has_scm"] is True
    smp = _get(api, f"/outorgas/{CRED['cnpj']}")["servicos"]["SMP"]
    assert smp[0]["rede_virtual"]["papel"] == "credenciada"
    # quem tem outorga SMP própria continua com o selo
    proprio = OPS[34]
    if proprio["asns"]:
        b = next(x for x in _get(api, "/asns", q=str(proprio["asns"][0]), limit=50)["items"] if x["asn"] == proprio["asns"][0])
        assert b["has_smp"] is True
