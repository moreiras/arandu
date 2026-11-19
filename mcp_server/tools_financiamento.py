# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tools de crédito público e sanções do MCP: `operadora_financiamento` e `operadora_sancoes`.

Mesma fonte da rota `/financiamento/operadoras/{cnpj}` (`api.services.financiamento` sobre `financiamento/operadoras.json.gz`). Registro de fonte oficial, sem julgamento.
"""
from __future__ import annotations

from typing import Optional

from api.services import financiamento as fin
from api.services.empresas import EmpresasErro
from mcp_server.contexto import _resolve, _store, mcp


def _parte(cnpj: str, parte: str, date: Optional[str]) -> dict:
    d = _resolve(date)
    doc = _store.financiamento_doc(d)
    if not doc:
        raise ValueError(f"Crédito público e sanções não publicados no snapshot {d}.")
    try:
        return fin.operadora(doc, fin.raiz_do_cnpj(cnpj), parte)
    except EmpresasErro as e:
        if e.status == 404:          # ausência é resposta, não falha da chamada
            return sem_registro(d, fin.raiz_do_cnpj(cnpj), e.mensagem)
        raise ValueError(e.mensagem)


def sem_registro(d: str, raiz: str, ressalva: str) -> dict:
    """Resultado normal para "não consta": um erro de tool fazia o modelo tentar outra coisa como se a chamada tivesse falhado."""
    return {"snapshot_date": d, "cnpj_raiz": raiz, "registros": 0, "resultado": "sem_registro", "ressalva": ressalva}


@mcp.tool()
def operadora_financiamento(cnpj: str, date: Optional[str] = None) -> dict:
    """Operações de financiamento do BNDES de uma operadora (raiz do CNPJ): total contratado e desembolsado em R$ NOMINAIS (da data da contratação), por ano e UF, e as 50 mais recentes.

    Só operações diretas e não automáticas (as indiretas, via banco credenciado, têm o CNPJ mascarado e ficam de fora). `resultado="sem_registro"` = sem registro nesse recorte, NÃO "nunca recebeu crédito".
    Dados abertos do BNDES sob ODbL: cite o BNDES, a licença e a data do snapshot.

    Args:
        cnpj: Raiz (8 dígitos) ou CNPJ completo, com ou sem pontuação.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    return _parte(cnpj, "financiamento", date)


@mcp.tool()
def operadora_sancoes(cnpj: str, date: Optional[str] = None) -> dict:
    """Sanções do CEIS e do CNEP (CGU) de uma operadora (raiz do CNPJ): vigentes, futuras e encerradas na data do snapshot, com órgão sancionador, fundamento legal, período e, no CNEP, a multa.

    É o registro do órgão sancionador na data do arquivo da CGU, sem julgamento: pode já ter sido suspensa ou anulada. `sem_fim_informado` = a fonte não traz data final (inclui multa e publicação do CNEP e o 2099-12-31 da CGU, `sem_prazo`); "vigentes" quer dizer "constam sem fim ou com fim futuro". `resultado="sem_registro"` = sem registro nesse recorte.
    Descreva como "consta no CEIS/CNEP em <data>", nunca como acusação; cite a CGU e a data do snapshot.

    Args:
        cnpj: Raiz (8 dígitos) ou CNPJ completo, com ou sem pontuação.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    return _parte(cnpj, "sancoes", date)
