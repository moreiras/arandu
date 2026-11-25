# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Versão vigente da política de privacidade, fonte única do registro técnico do aceite (`contas.politica_versao`).

O aceite é o do texto de `Login.tsx` ("Ao entrar, você concorda com a política de privacidade"). Este módulo só guarda QUAL versão estava
vigente quando a pessoa entrou; não define nem altera o texto da política (redação do mantenedor).
"""
from __future__ import annotations

# Mude o identificador a cada revisão da política que o público veja; quem já aceitou uma versão anterior passa a constar com a nova
# no próximo login.
POLITICA_VERSAO_VIGENTE = "2026-11-25"

# Contas criadas antes do registro: a versão do aceite não é conhecida até o próximo login.
POLITICA_NAO_REGISTRADA = "não registrada"
