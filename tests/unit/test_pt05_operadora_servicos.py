# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Credenciamento de rede virtual não é outorga SMP (OPERADORA-E8, OPERADORA-E9, REL-E3)."""
from types import SimpleNamespace

from core.outorgas import eh_outorga

CRED = {"cnpj": "1", "situacao": "Credenciada de Rede Virtual (sem outorga SMP própria)", "rede_virtual": {"papel": "credenciada"}}


# ── OPERADORA-E8/E9: credenciamento de rede virtual não é outorga SMP ──

def test_registro_sintetico_de_credenciada_nao_e_outorga():
    assert eh_outorga(CRED) is False
    assert eh_outorga({"situacao": ""}) is True
    assert eh_outorga({"situacao": "Credenciada", "rede_virtual": {"papel": "credenciada"}}) is True   # outorga própria marcada como credenciada (Algar)
    assert eh_outorga({}) is True


def test_flags_e_asn_set_ignoram_credenciada_sem_outorga():
    from api.outorgas_store import OutorgasPublicadas
    from api.services.operadoras import OperadorasService

    doc = {"by_cnpj": {"1": [CRED], "2": [{"cnpj": "2", "situacao": ""}]}, "cnpj_to_asns": {"1": [64500], "2": [64501], "3": [64502]}}
    st = OutorgasPublicadas.__new__(OutorgasPublicadas)
    st.sigla, st._asn_set, st.load = "smp", {}, (lambda d: doc)
    assert st.asn_set("2026-01-01") == frozenset({64501})
    fake = SimpleNamespace(_load_smp=lambda d: doc, _load_scm=lambda d: None, _load_stfc=lambda d: None, _load_seac=lambda d: None)
    assert OperadorasService.outorgas_flags_for_cnpj(fake, "d", "1")["has_smp"] is False
    assert OperadorasService.outorgas_flags_for_cnpj(fake, "d", "2")["has_smp"] is True
