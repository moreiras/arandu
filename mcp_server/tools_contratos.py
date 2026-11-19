# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tool de contratos públicos do MCP: `operadora_contratos`.

Mesma fonte da rota `/contratos/operadoras/{cnpj}` (`api.services.contratos` sobre `contratos/operadoras.json.gz`). Resultados de itens publicados no PNCP, não contratos assinados nem pagamentos.
"""
from __future__ import annotations

from typing import Optional

from api.services import contratos as ctr
from api.services.empresas import EmpresasErro
from mcp_server.contexto import _resolve, _store, mcp


@mcp.tool()
def operadora_contratos(cnpj: str, date: Optional[str] = None) -> dict:
    """Contratos públicos de uma operadora (raiz do CNPJ): resultados de itens publicados no PNCP (Lei 14.133, Compras.gov.br) com valor homologado, órgãos, UF, ano, esfera e as 20 contratações mais recentes.

    É resultado publicado, NÃO contrato assinado nem pagamento. Coleta em rodízio e só do CNPJ de matriz: leia `lida_em`/`idade_dias` e `cobertura`. `resultado=sem_resultado_na_consulta` = lida e sem item (com a data);
    `resultado=sem_leitura` = ainda sem leitura, NÃO "sem contratos". Esfera, município (do órgão, não da entrega) e objeto só nas contratações detalhadas. Sem ranking. Cite a fonte, a data da leitura e o snapshot.

    Args:
        cnpj: Raiz (8 dígitos) ou CNPJ completo, com ou sem pontuação.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    doc = _store.contratos_operadoras_doc(d)
    if not doc:
        raise ValueError(f"Contratos públicos não publicados no snapshot {d}.")
    try:
        return ctr.operadora(doc, ctr.raiz_do_cnpj(cnpj))
    except EmpresasErro as e:
        if e.status == 404:          # "ainda sem leitura" é resposta, não falha da chamada
            from mcp_server.tools_financiamento import sem_registro
            return {**sem_registro(d, ctr.raiz_do_cnpj(cnpj), e.mensagem), "resultado": "sem_leitura"}
        raise ValueError(e.mensagem)
