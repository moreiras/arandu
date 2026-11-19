# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Contratos públicos de operadoras (Compras.gov.br / PNCP, Lei 14.133).

  * `GET /contratos/operadoras/{cnpj}` — resultados de itens publicados no PNCP para a raiz do CNPJ: valor, órgãos, UF, ano, esfera e contratações recentes.
  * `GET /contratos/municipios/{ibge}` — operadoras com contratação de órgão sediado no município.
  * `GET /contratos/resumo?uf=` — cobertura do rodízio e totais por ano, UF e esfera.

Registro de resultado publicado, não contrato assinado nem pagamento; sem ranking de fornecedor; ausência não é zero (rodízio: cada raiz tem a data da sua leitura).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import contratos as s
from api.services.empresas import EmpresasErro

router = APIRouter()


def _doc(request: Request, date: Optional[str], qual: str) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = getattr(store, f"contratos_{qual}_doc")(d)
    if not doc:
        raise HTTPException(404, f"Contratos públicos não publicados no snapshot {d}.")
    return doc


@router.get(
    "/contratos/operadoras/{cnpj}",
    summary="Contratos públicos (PNCP) de uma operadora, pela raiz do CNPJ",
    description="""
Resultados de itens de contratação publicados no PNCP (Lei 14.133, espelhados no Compras.gov.br) em que a raiz do CNPJ é a fornecedora: itens, contratações, órgãos, **valor homologado** (sem os itens
cancelados, contados à parte), séries por ano, UF e esfera, órgãos principais e as 20 contratações mais recentes. Aceita a raiz (8 dígitos) ou o CNPJ completo.

Cada linha é um resultado publicado, não um contrato assinado nem um pagamento. A coleta consulta só o CNPJ de matriz e roda em rodízio de dias: `lida_em` e `idade_dias` dizem quando a raiz foi lida e
`cobertura` quanto do universo já foi. `resultado = sem_resultado_na_consulta` quer dizer que a raiz foi lida e o PNCP não devolveu item (com a data); 404 quer dizer "ainda sem leitura", não "sem contratos".
Esfera, município e objeto só existem para as contratações já detalhadas. Dados abertos pela LAI e pela Lei 14.133, sem licença nominal publicada (`licenca`).
""",
)
def contratos_operadora(request: Request, cnpj: str, date: Optional[str] = Query(None)) -> dict:
    doc = _doc(request, date, "operadoras")
    try:
        return s.operadora(doc, s.raiz_do_cnpj(cnpj))
    except EmpresasErro as e:
        raise HTTPException(e.status, e.mensagem)


@router.get(
    "/contratos/municipios/{ibge}",
    summary="Operadoras com contratação de órgão sediado no município (PNCP)",
    description="""
Para um município (código IBGE de 7 dígitos), contratações, itens e valor homologado das operadoras cujo contratante é um órgão **sediado** no município, e as até 20 operadoras de maior valor registrado.
O município é o do órgão comprador (detalhe da contratação ou unidade de compra), **não o local de entrega** do serviço, e a ordem é por valor numa leitura parcial (rodízio): não é ranking de mercado nem
prova de que a operadora atende o município. 404 quer dizer "sem contratação nas leituras", não "sem contratação".
""",
)
def contratos_municipio(request: Request, ibge: str, date: Optional[str] = Query(None)) -> dict:
    doc = _doc(request, date, "municipios")
    try:
        return s.municipio(doc, ibge)
    except EmpresasErro as e:
        raise HTTPException(e.status, e.mensagem)


@router.get(
    "/contratos/resumo",
    summary="Contratos públicos de operadoras: cobertura do rodízio e totais por ano, UF e esfera",
    description="""
Cobertura da coleta (raízes lidas e sem leitura, datas da leitura mais antiga e mais recente, contratações detalhadas) e totais do que foi lido, por ano, UF e esfera (como informada no PNCP). Sem ranking de
fornecedor. A soma só inclui o que já foi lido: raiz sem leitura não entra como zero. `uf` restringe ao total da UF do órgão.
""",
)
def contratos_resumo(request: Request, uf: Optional[str] = Query(None, description="UF (sigla) do órgão"), date: Optional[str] = Query(None)) -> dict:
    doc = _doc(request, date, "resumo")
    try:
        return s.resumo(doc, uf)
    except EmpresasErro as e:
        raise HTTPException(e.status, e.mensagem)
