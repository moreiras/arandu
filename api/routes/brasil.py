# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`GET /brasil/indicadores`: agregados nacionais para "O Brasil em números" (home) e o Panorama
técnico, numa chamada só e aberta (a home é página de entrada).

- `ipv6`: adoção de IPv6 pelos usuários, somando as estimativas do APNIC por ASN do Brasil (Σ usuários IPv6 ÷ Σ usuários). É agregado dos
  ASes, não o número que o APNIC publica por país (que usa a própria amostra por país); a diferença costuma ser pequena e vem rotulada;
- `dnssec` e `rov`: o agregado nacional do produto de segurança de roteamento (medições do APNIC por ASN, com amostra mínima);
- `ixbr`: ASNs brasileiros no IX.br pela regra do índice de ASNs: diretos (sessão com o route server de algum PTT) e indiretos (originam prefixos vistos
  em algum PTT, mas não têm sessão em nenhum; o prefixo chega por outro participante). Cada ASN conta uma vez, qualquer que seja o número de PTTs;
- `mercado`: o HHI nacional do mercado fixo por CNPJ (acessos declarados ao SICI), com o mês de referência;
- `por_regiao`: o retrato por macro-região da sede do AS (ASNs, usuários, IPv6, ROA e sessão em route server do IX.br; as linhas fecham o total);
- `prontidao`: o índice de prontidão em segurança de roteamento do país (classes, média ponderada por usuários, pilares e componentes);
- `rpki` (Panorama técnico): `publicacao` (ASNs com ROA e ASPA, o mesmo corpo de `/rpki/summary`) e `rotas` (estado RPKI de origem das
  rotas brasileiras e totais de saúde da tabela, de `routing_analysis_resumo.json`; null em snapshot sem o arquivo).

Só números agregados do país: não é ranking de empresas. Fontes, datas e limites vêm na resposta."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.store import Store
from core import moas

router = APIRouter()
_CACHE: dict[tuple, dict] = {}


def ipv6_apnic(store: Store, date_str: str) -> dict:
    br = [a for a in store.asn_index(date_str) if a.get("is_br") and (a.get("apnic_users") or 0) > 0]
    usuarios = sum(a["apnic_users"] for a in br)
    v6 = sum(a.get("apnic_v6_users") or 0 for a in br)
    return {
        "usuarios": usuarios, "usuarios_ipv6": v6, "pct_usuarios_ipv6": round(100 * v6 / usuarios, 1) if usuarios else None,
        "asns_com_estimativa": len(br), "asns_com_ipv6": sum(1 for a in br if (a.get("apnic_v6_users") or 0) > 0),
        "fonte": "APNIC Labs: estimativas de usuários por ASN e de usuários com IPv6 (medição por anúncios, janela de 60 dias)",
        "nota": "Soma das estimativas por ASN do Brasil; não é o número que o APNIC publica por país, que usa a amostra do país.",
    }


_REGIOES = ("N", "NE", "CO", "SE", "S")
_NOMES_REGIAO = {"N": "Norte", "NE": "Nordeste", "CO": "Centro-Oeste", "SE": "Sudeste", "S": "Sul"}


def por_regiao(store: Store, date_str: str) -> Optional[dict]:
    """Retrato por macro-região (IBGE) da sede da organização dona do AS (PT-22 / PANORAMA TÉCNICO 5.2): ASNs do Registro.br, usuários estimados pelo
    APNIC, usuários em ASNs com IPv6, com ROA e com sessão em route server do IX.br. Soma os mesmos números do agregado nacional, de modo que as linhas
    (mais `sem_regiao`) fecham o total. A região é a da sede da empresa, não a dos usuários. None sem o cadastro de organizações (sem número, não zero)."""
    from api.query_catalogo import REGION_BY_UF
    try:
        geo = store._load_geo_orgs(date_str)
    except Exception:
        return None
    if not geo:
        return None
    zero = lambda: {"asns": 0, "usuarios": 0, "usuarios_ipv6": 0, "usuarios_com_roa": 0, "usuarios_sessao_rs": 0, "asns_com_ipv6": 0}
    linhas = {r: zero() for r in _REGIOES}
    linhas["sem_regiao"] = zero()
    for a in store.asn_index(date_str):
        if not a.get("is_br"):
            continue
        uf = (geo.get(a.get("asn")) or {}).get("uf")
        reg = REGION_BY_UF.get(uf)
        l = linhas[reg if reg in _REGIOES else "sem_regiao"]
        u = a.get("apnic_users") or 0
        l["asns"] += 1
        l["usuarios"] += u
        l["usuarios_ipv6"] += a.get("apnic_v6_users") or 0
        if a.get("has_rpki"):
            l["usuarios_com_roa"] += u
        if (a.get("ixps_direct_count") or 0) >= 1:
            l["usuarios_sessao_rs"] += u
    total = zero()
    for l in linhas.values():
        for k in total:
            total[k] += l[k]
    return {
        "regioes": [{"regiao": r, "nome": _NOMES_REGIAO[r], **linhas[r]} for r in _REGIOES],
        "sem_regiao": linhas["sem_regiao"], "total": total,
        "fonte": "APNIC Labs (usuários por ASN), RPKI (ROA), looking glasses do IX.br (sessão em route server) e cadastro de organizações (região da sede)",
        "nota": "A região é a da sede da empresa dona do AS, não a dos usuários: uma operadora nacional sediada em uma região conta todos os seus usuários nela. "
                "Sessão em route server não inclui acordos bilaterais nem interligação privada.",
    }


def ixbr_asns_br(store: Store, date_str: str) -> dict:
    """ASNs brasileiros (`is_br`) no IX.br, cada um contado uma vez no país: `diretos` têm sessão com o route server de ao menos um PTT; `indiretos` originam
    prefixos vistos em ao menos um PTT e não têm sessão em nenhum (o prefixo chega por outro participante); `originam` é a união dos dois grupos que aparecem como origem
    (um direto sem prefixo visto não entra nela). Calculado do índice de ASNs, sem I/O extra."""
    br = [a for a in store.asn_index(date_str) if a.get("is_br")]
    diretos = sum(1 for a in br if (a.get("ixps_direct_count") or 0) >= 1)
    originam = sum(1 for a in br if (a.get("ixps_origin_count") or 0) >= 1)
    indiretos = sum(1 for a in br if (a.get("ixps_origin_count") or 0) >= 1 and (a.get("ixps_direct_count") or 0) == 0)
    return {
        "asns_br_total": len(br), "asns_br_diretos": diretos, "asns_br_indiretos": indiretos, "asns_br_originam": originam,
        "fonte": "looking glasses do IX.br (sessão com route server e origem das rotas) sobre os ASNs do Registro.br",
        "nota": "Direto: sessão com o route server de algum PTT; não inclui peering bilateral. Indireto: só origina prefixos vistos em PTTs, levados por outro participante.",
    }


def indicadores(store: Store, date_str: str) -> dict:
    chave = (id(store), str(store.base), date_str)
    if chave in _CACHE:
        return _CACHE[chave]
    out: dict = {"snapshot_date": date_str, "ipv6": ipv6_apnic(store, date_str)}
    regioes = por_regiao(store, date_str)
    if regioes:
        out["por_regiao"] = regioes
    seg = store.seguranca_doc(date_str)
    if seg:
        b = seg.get("brasil") or {}
        fontes = seg.get("fontes") or {}
        out["dnssec"] = {**(b.get("dnssec") or {}), "fonte": fontes.get("dnssec")}
        out["rov"] = {**(b.get("rov") or {}), "fonte": fontes.get("rov")}
        out["asns"] = b.get("asns")
    out["ixbr"] = ixbr_asns_br(store, date_str)
    ind = store.sici_indicadores(date_str) or {}
    nac = ind.get("brasil")
    if nac and nac.get("hhi") is not None:
        out["mercado"] = {"hhi_cnpj": nac.get("hhi"), "acessos": nac.get("acessos"), "n_cnpjs": nac.get("n_operadoras"), "mes_referencia": ind.get("mes_referencia"),
                          "fonte": "SICI, Anatel (acessos fixos declarados pelas operadoras)",
                          "nota": "HHI do país inteiro por CNPJ, de 0 a 10.000, sobre os acessos fixos declarados; não agrupa CNPJs de um mesmo grupo econômico e difere do HHI local."}
    pr = store.prontidao_doc(date_str)
    if pr:
        from api.services import prontidao as p
        r = p.resumo(pr, None)
        regras = r.get("regras") or {}
        out["prontidao"] = {
            "natureza": r.get("natureza"), "agregado": r.get("agregado"),
            "pilares": {k: {"nome": v.get("nome"), "peso": v.get("peso"), "descricao": v.get("descricao"),
                            "componentes": {c: {"descricao": d.get("descricao")} for c, d in (v.get("componentes") or {}).items()}}
                        for k, v in (regras.get("pilares") or {}).items()},
            "limites": r.get("limites"),
        }
    from api.routes.rpki import montar_resumo
    publicacao = montar_resumo(store, date_str)
    publicacao.pop("snapshot_date", None)
    # `saude.moas` por família quando a coleta guardou todas as origens; nulo, com o motivo, nos que gravaram 0 sem medir (core/moas.py)
    out["rpki"] = {"publicacao": publicacao, "rotas": moas.resumo_publicado(store._read_json(store._pub(date_str) / "routing_analysis_resumo.json"))}
    if len(_CACHE) > 16:
        _CACHE.clear()
    _CACHE[chave] = out
    return out


@router.get(
    "/brasil/indicadores",
    summary="O Brasil em números: IPv6 (APNIC), DNSSEC, ROV, RPKI e prontidão em segurança de roteamento, no agregado do país",
    description="""
Agregados nacionais para a home e o Panorama técnico: `ipv6` (Σ usuários com IPv6 ÷ Σ usuários nas estimativas do APNIC por ASN do Brasil; não é o número por país do
APNIC), `dnssec` e `rov` (percentual medido pelo APNIC, mediana e média ponderada, só ASNs com amostra suficiente) e `prontidao` (índice do país por classe, média ponderada
por usuários, pilares e componentes, com as regras) e `por_regiao` (retrato por macro-região da sede do AS, com as linhas fechando o total) e `rpki` (`publicacao`: ASNs com ROA e ASPA; `rotas`: estado RPKI de origem das rotas brasileiras, válidas,
inválidas e sem ROA, com o espaço de cada estado, e totais de saúde da tabela; `rotas` é null em snapshot anterior ao resumo). Só números do país: o detalhe por UF e porte está em `/seguranca/resumo` e `/prontidao/resumo`. Fontes e limites na resposta.
""",
)
def brasil_indicadores(request: Request, date: Optional[str] = Query(None)) -> dict:
    store: Store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return indicadores(store, d)


# ── Destaques da home: números fixos, no lugar de `/query/*` genérico (D9, TRANSV-E20) ──────────────────────────────────────────────
# As mesmas consultas dos cartões de `frontend/src/features/home/cartoes.json` (`tests/unit/test_destaques_home.py` confere que não divergem),
# executadas aqui com `limit` 1 só para o `total`. A rota é fixa e aberta; `/query` continua medido, porque aceita qualquer corpo.
_DESTAQUES_QUERY: dict[str, tuple[str, dict]] = {
    "grandes-sem-asn": ("operadoras", {"filter": {"and": [{"field": "acessos", "op": "gte", "value": 5000}, {"field": "com_asn", "op": "eq", "value": False}]}}),
    "sem-rpki": ("asns", {"filter": {"and": [{"field": "is_br", "op": "eq", "value": True}, {"field": "global_prefixes_v6_count", "op": "gte", "value": 1},
                                             {"field": "has_rpki", "op": "eq", "value": False}, {"field": "ixps_direct_count", "op": "gte", "value": 3}]}}),
    "monopolio-local": ("acessos_municipio", {"filter": {"and": [{"field": "share", "op": "gte", "value": 80}, {"field": "municipio_acessos", "op": "gte", "value": 1000}]}}),
}
_DIVERGENCIAS = {"k_pf": 5, "k_pj": 30, "min_razao": 10}          # os parâmetros padrão de `/acessos/divergencias/scm`, que é a lista de destino
_O_QUE_MUDOU = {"filter": {"and": [{"field": "tipo", "op": "eq", "value": "asn_novo"}, {"field": "estado", "op": "eq", "value": "confirmado"}]},
                "select": ["asn", "uf", "data"], "sort": [{"field": "data", "dir": "desc"}], "limit": 1}
_CACHE_DESTAQUES: dict[tuple, dict] = {}


# Tipos de evento mostrados na Home em "O que mudou" (PT-22 / HOME 5.4), na ordem de leitura. Fora os de provedor (inferência) e os de alerta.
_TIPOS_JANELA = ("asn_novo", "asn_sumido", "ixp_entrada", "ixp_saida", "roa_ganho", "roa_perdido", "rpki_invalido_novo", "rpki_invalido_resolvido",
                 "outorga_nova", "outorga_baixa")


def _por_tipo_da_janela(store: Store, de: str, ate: str) -> dict:
    """Contagem por tipo e estado dos eventos entre `de` e `ate` (a mesma de `/changes/summary`, restrita a `_TIPOS_JANELA`), mais as datas atípicas."""
    from api.repos.historico import HistoricoRepo
    from api.services import historico as h
    r = h.mudancas_resumo(HistoricoRepo(store.base), de, ate, tipo=",".join(_TIPOS_JANELA))
    out = {"por_tipo": {t: r["por_tipo"].get(t, {"confirmado": 0, "pendente": 0, "revertido": 0}) for t in _TIPOS_JANELA}}
    if r.get("datas_atipicas"):
        out["datas_atipicas"] = r["datas_atipicas"]
    return out


def destaques_home(store: Store, date_str: str) -> dict:
    chave = (id(store), str(store.base), date_str)
    if chave in _CACHE_DESTAQUES:
        return _CACHE_DESTAQUES[chave]
    from api.auth.access_policy import N_DATAS_ATUAIS
    out: dict = {"snapshot_date": date_str, "destaques": {}}
    for id_, (colecao, corpo) in _DESTAQUES_QUERY.items():
        out["destaques"][id_] = {"total": store.query(date_str, colecao, {**corpo, "limit": 1}).get("total", 0)}
    out["destaques"]["divergencias"] = {"total": len(store.sici_divergencias_scm(date_str, **_DIVERGENCIAS))}
    # "O que mudou" só na janela dos snapshots atuais: a rota é aberta e a mesma URL serve a todos, então não alcança o histórico (EXP-E4)
    janela_de = store.list_snapshots()[-N_DATAS_ATUAIS:][0]
    r = store.query(date_str, "eventos", {**_O_QUE_MUDOU, "de": janela_de})
    ultimo = (r.get("items") or [None])[0]
    out["o_que_mudou"] = {"total": r.get("total", 0), "de": janela_de, "mais_recente": (ultimo or {}).get("data"),
                         "ate": date_str, **_por_tipo_da_janela(store, janela_de, date_str)}
    if len(_CACHE_DESTAQUES) > 16:
        _CACHE_DESTAQUES.clear()
    _CACHE_DESTAQUES[chave] = out
    return out


@router.get(
    "/brasil/destaques",
    summary="Destaques da home: o total de cada pergunta pronta e os ASes novos da janela atual",
    description="""
Os números fixos dos destaques da página inicial, numa chamada aberta: `destaques` traz o `total` de cada pergunta pronta (operadoras com mais de 5 mil acessos sem ASN
próprio, ASes brasileiros em 3 ou mais PTTs com IPv6 e sem ROA, municípios com uma operadora de 80% ou mais da banda larga fixa e ASNs com usuários APNIC 10 vezes ou mais acima do esperado
pelos acessos SCM) e `o_que_mudou` os ASes brasileiros novos e confirmados desde `de`, a data do snapshot atual mais antigo (a rota é aberta, então não alcança o histórico), com `por_tipo` (eventos entre `de` e `ate` por tipo e estado: confirmado, pendente e revertido; diferença observada entre snapshots, sem causa). Cada total é
o da lista de destino do destaque. As consultas são fixas; a consulta genérica (`/query`) segue medida.
""",
)
def brasil_destaques(request: Request, date: Optional[str] = Query(None)) -> dict:
    store: Store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return destaques_home(store, d)
