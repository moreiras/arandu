# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Mercado de IPv4 do Brasil.

  * `GET /ipv4/transferencias` — operações de transferência com o Brasil (Registro.br e LACNIC), com filtros por ano, direção, ASN, bloco e nome.
  * `GET /ipv4/transferencias/resumo` — volumes por ano, direção e tamanho, concentração, maior operação, defasagem e casamento com ASN.
  * `GET /ipv4/recuperacao` — recursos em recuperação, recuperados e eventos de recuperação e liberação por mês.
  * `GET /ipv4/blocos/{prefixo}/ciclo-de-vida` — linha do tempo de um bloco: estado atual, eventos do `delegated`, transferências declaradas e recuperação.
  * Coleções `transferencias_ipv4`, `recuperacao_ipv4` e `eventos_bloco` do `/query`.

São **diferenças observadas** e o que as listas declaram, sem causa nem intenção (não é "aluguel" nem "venda"). Nome de pessoa física provável é omitido. Fontes: Registro.br e LACNIC.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import ipv4 as s

router = APIRouter()


def _store(request: Request):
    return request.app.state.store


def _data(request: Request, date: Optional[str]) -> str:
    d = _store(request).resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return d


def _doc(request: Request, date: Optional[str], nome: str) -> tuple[str, dict]:
    d = _data(request, date)
    doc = getattr(_store(request), f"ipv4_{nome}_doc")(d)
    if not doc:
        raise HTTPException(404, f"Mercado de IPv4 ({nome}) não publicado no snapshot {d}.")
    return d, doc


@router.get(
    "/ipv4/transferencias",
    summary="Transferências de IPv4 com o Brasil, por operação",
    description="""
Operações de transferência de blocos IPv4 em que o Brasil é origem ou destino (listas do Registro.br e log do LACNIC). Uma operação é o mesmo dia e as mesmas partes (um lote de blocos
é uma operação). `direcao` = `br_br`, `br_exterior` ou `exterior_br`; `asn` filtra pelo ASN atual do destino; `prefixo` pelas operações que tocam o bloco; `q` busca no nome das partes.
`primeira_vez_visto` é a primeira data de snapshot em que a lista mostrou a operação (`anterior_a_coleta` = já estava na primeira lista coletada). Nome de pessoa física provável é omitido.
É o que as listas declaram, sem causa nem intenção.
""",
)
def ipv4_transferencias(
    request: Request, ano: Optional[str] = Query(None, description="AAAA."), direcao: Optional[str] = Query(None), asn: Optional[int] = Query(None),
    prefixo: Optional[str] = Query(None, description="Bloco IPv4, ex.: 198.18.0.0/22."), q: Optional[str] = Query(None), date: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=500), page: int = Query(1, ge=1),
) -> dict:
    _, doc = _doc(request, date, "transferencias")
    try:
        return s.transferencias(doc, ano, direcao, q, asn, prefixo, limit, (page - 1) * limit)
    except s.Ipv4Erro as e:
        raise HTTPException(e.status, e.mensagem)


@router.get(
    "/ipv4/transferencias/resumo",
    summary="Mercado de IPv4: volumes por ano, direção e tamanho",
    description="Operações, blocos e endereços por ano e direção, por classe de tamanho, as maiores partes, a maior operação, a defasagem mediana de publicação e o percentual de destinos casados com ASN.",
)
def ipv4_resumo(request: Request, date: Optional[str] = Query(None)) -> dict:
    return s.resumo(_doc(request, date, "mercado")[1])


@router.get(
    "/ipv4/recuperacao",
    summary="Recursos em recuperação e recuperados (Registro.br)",
    description="Blocos IPv4, blocos IPv6 e ASNs em recuperação (com a janela e, para IPv4, o status atual no delegated), recuperados por tipo e os eventos de recuperação e liberação por mês.",
)
def ipv4_recuperacao(request: Request, date: Optional[str] = Query(None)) -> dict:
    return s.recuperacao(_doc(request, date, "recuperacao")[1])


@router.get(
    "/ipv4/blocos/{prefix:path}/ciclo-de-vida",
    summary="Ciclo de vida de um bloco IPv4",
    description="""
Linha do tempo do bloco (ou dos blocos do Brasil que o tocam): estado atual no `delegated` (status, país, `opaque-id`, ASN e organização), eventos observados (titularidade, recuperação, liberação,
novo, removido, país), transferências declaradas e recuperação. Diferenças observadas entre fotos diárias, sem causa nem intenção.
""",
)
def ipv4_ciclo_de_vida(prefix: str, request: Request, date: Optional[str] = Query(None)) -> dict:
    store = _store(request)
    d = _data(request, date)
    try:
        return s.ciclo_de_vida(prefix, store.ipv4_transferencias_doc(d), store.ipv4_recuperacao_doc(d), store.ipv4_blocos_br_doc(d), store.ipv4_eventos_br(), d, store.ipv4_espaco_doc(d), store.ipv4_uso_doc(d))
    except s.Ipv4Erro as e:
        raise HTTPException(e.status, e.mensagem)


@router.get(
    "/ipv4/espaco",
    summary="Espaço IPv4 do Brasil que não está plenamente anunciado",
    description="""
Blocos IPv4 do Brasil (delegated) pela tabela de origens do snapshot: `nao_anunciado`, `roa_sem_anuncio`, `parcial` (anunciado só em parte) e `em_recuperacao`, com o resumo por classe e UF e as
tabelas de origem consultadas para a duração (`tabelas_sem_anuncio`). **Não anunciado não é sem uso**: rede interna, enlace, reserva técnica e CGNAT não aparecem na tabela global. Inferido.
""",
)
def ipv4_espaco(
    request: Request, classe: Optional[str] = Query(None), asn: Optional[int] = Query(None), cnpj: Optional[str] = Query(None), uf: Optional[str] = Query(None),
    date: Optional[str] = Query(None), limit: int = Query(25, ge=1, le=500), page: int = Query(1, ge=1),
) -> dict:
    _, doc = _doc(request, date, "espaco")
    try:
        return s.espaco(doc, classe, asn, cnpj, uf, limit, (page - 1) * limit)
    except s.Ipv4Erro as e:
        raise HTTPException(e.status, e.mensagem)


@router.get(
    "/ipv4/uso-por-terceiros",
    summary="Blocos IPv4 com sinais de uso por terceiros (hipótese)",
    description="""
Blocos com ao menos um sinal que **sugere** uso por quem não é o titular: S1 origem diferente do titular, S2 ROA de outro ASN, S3 bloco sem ASN titular anunciado por terceiro, S4 origem mudou sem
transferência registrada (S5 a S7 ainda sem fonte; a resposta diz por quê). É **hipótese**, nunca "aluguel": cada sinal traz confiança, evidência e os falsos positivos conhecidos (o caso comum é o
provedor que anuncia o bloco do cliente). Dois ou mais sinais sobem a confiança um nível.
""",
)
def ipv4_uso_por_terceiros(
    request: Request, sinal: Optional[str] = Query(None, description="S1 a S4."), confianca: Optional[str] = Query(None, description="baixa, media ou alta."), asn: Optional[int] = Query(None),
    cnpj: Optional[str] = Query(None), date: Optional[str] = Query(None), limit: int = Query(25, ge=1, le=500), page: int = Query(1, ge=1),
) -> dict:
    _, doc = _doc(request, date, "uso")
    try:
        return s.uso_por_terceiros(doc, sinal, confianca, asn, cnpj, limit, (page - 1) * limit)
    except s.Ipv4Erro as e:
        raise HTTPException(e.status, e.mensagem)


@router.get(
    "/ipv4/asns/{asn}",
    summary="Recursos IPv4 de um ASN",
    description="Blocos IPv4 alocados ao ASN (delegated), os não plenamente anunciados e os sinais de uso por terceiros, como titular e como origem de bloco alheio. 404 se o ASN não tem nada disso.",
)
def ipv4_asn(asn: int, request: Request, date: Optional[str] = Query(None)) -> dict:
    store = _store(request)
    d = _data(request, date)
    r = s.recursos_do_asn(asn, store.ipv4_blocos_br_doc(d), store.ipv4_espaco_doc(d), store.ipv4_uso_doc(d))
    if r is None:
        raise HTTPException(404, f"Nenhum recurso IPv4 do Brasil para AS{asn}.")
    return r


@router.get(
    "/ipv4/subasignacoes",
    summary="Sub-asignações de IPv4 (aluguel regulado, política LAC-2025-5)",
    description="""
Estado das sub-asignações previstas na política LAC-2025-5 (ratificada em 24/03/2026). **Enquanto a bitácora pública oficial não existir, `ativa` é falso, `aguardando` é verdadeiro e `items` vem vazio**: o campo `vigia`
mostra a última varredura diária dos diretórios do Registro.br e do LACNIC e os alertas (arquivo novo). Com a fonte ativada, cada registro traz as validações da política (receptor origina o bloco, ROA, tamanho
/24 a /22, IPv6, prazo de 3 anos, infraestrutura crítica; `null` = sem dado) e `indicador_terceiros` separa anúncios de terceiros com e sem registro. O esquema é hipotético até o formato oficial ser conhecido.
""",
)
def ipv4_subasignacoes(
    request: Request, asn: Optional[int] = Query(None, description="ASN do receptor."), conforme: Optional[bool] = Query(None, description="Só as em conformidade com todas as validações (ou só as que não estão)."),
    date: Optional[str] = Query(None), limit: int = Query(25, ge=1, le=500), page: int = Query(1, ge=1),
) -> dict:
    _, doc = _doc(request, date, "subasig")
    return s.subasignacoes(doc, asn, conforme, limit, (page - 1) * limit)
