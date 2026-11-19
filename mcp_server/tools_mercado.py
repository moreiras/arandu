# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tools de mercado e regulação do MCP: perfis consolidados (operadora, município, UF) e SICI."""
from __future__ import annotations

import re
from typing import Optional

from api.routes.perfis import UFS as _UFS_VALIDAS, montar_perfil_operadora
from mcp_server.contexto import _resolve, _store, mcp

# ---------------------------------------------------------------------------
# Perfis consolidados: a mesma forma de dado das rotas /operadoras, /municipios e /ufs
# ---------------------------------------------------------------------------

def _blocos_validos(blocos: Optional[list[str]], validos: set[str]) -> Optional[set[str]]:
    # `rede` vem sempre (a descrição o chama de bloco): pedido explícito é aceito e não muda nada
    sel = {b.strip() for b in (blocos or []) if b and b.strip() and b.strip() != "rede"}
    if not sel:
        return None
    if not sel <= validos:
        raise ValueError(f"blocos inválidos: {sorted(sel - validos)}; válidos: {sorted(validos)}")
    return sel


@mcp.tool()
def get_operator(cnpj: str, blocos: Optional[list[str]] = None, date: Optional[str] = None) -> dict:
    """Perfil de uma operadora pelo CNPJ, em uma chamada: o que está em `get_scm` + `operator_accesses` + STFC/SeAC/SMP.

    Retorna blocos `scm` (outorgas SCM, SICI fixo, ASNs, grupo econômico), `smp` (móvel), `stfc` e `seac`
    — cada um nulo quando o CNPJ não tem o serviço — e `rede` (agregação de rede dos ASNs: BGP, RPKI, IX.br) uma
    vez só. Contatos NÃO vêm aqui (só `contacts_available` com a contagem). DUAS DATAS no SICI: cite o
    `mes_referencia` e o `snapshot_date`. Com `acessos_compartilhados` verdadeiro não some ASes do mesmo CNPJ.

    Args:
        cnpj: CNPJ (14 dígitos, com ou sem formatação).
        blocos: Subconjunto de ["scm", "smp", "stfc", "seac"]; omita para todos.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    from fastapi import HTTPException
    d = _resolve(date)
    try:
        return montar_perfil_operadora(_store, cnpj, d, _blocos_validos(blocos, {"scm", "smp", "stfc", "seac"}))
    except HTTPException as exc:
        raise ValueError(str(exc.detail))


@mcp.tool()
def get_municipio(ibge: str, blocos: Optional[list[str]] = None, date: Optional[str] = None) -> dict:
    """Perfil de um município pelo código IBGE: banda larga fixa, telefonia móvel, % de fibra e PTTs mais próximos.

    Retorna `fixo` (acessos, operadores com share, HHI, `fibra_pct`), `movel`, `centroide` e `ptts_proximos`
    (os 5 mais próximos, com a distância `km` em linha reta do centróide — não é o trajeto de fibra). Satélite
    atende quase todo município: olhe o share e o HHI, não a contagem de operadoras. `fibra_pct` pode faltar em
    snapshots anteriores à coleta do meio de acesso por município.

    Args:
        ibge: Código IBGE do município (7 dígitos). Para achar pelo nome use `municipality_broadband(municipio=...)`.
        blocos: Subconjunto de ["fixo", "movel", "ptts"]; omita para todos.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    perfil = _store.perfil_municipio(d, str(ibge).strip(), _blocos_validos(blocos, {"fixo", "movel", "ptts"}))
    if perfil is None:
        raise ValueError(f"Município IBGE {ibge} sem acessos declarados em {d}.")
    return perfil


@mcp.tool()
def get_uf(uf: Optional[str] = None, blocos: Optional[list[str]] = None, date: Optional[str] = None) -> dict:
    """Perfil de uma UF: totais, PTTs, municípios com a distância ao PTT mais próximo e maiores operadoras. Sem `uf`, o resumo das 27 UFs.

    `totais` traz municípios, acessos fixos, `fibra_pct`, ASNs BR e `usuarios` (estimativa APNIC dos ASNs da UF
    pela geolocalização da organização — não é censo), e quantos municípios/acessos ficam a mais de 100 km de
    um PTT. `ixps` são os PTTs da UF; `municipios` vêm ordenados por acessos; `operadoras` são as 10 maiores com sede
    na UF e o total.

    Sem `uf` devolve uma linha por UF (PTTs, municípios, acessos fixos, % de fibra, ASNs, usuários estimados e municípios a mais de 100 km
    de um PTT), a mesma de `GET /ufs`.

    Args:
        uf: Sigla da UF (2 letras, ex.: "SP"). Omita para o resumo das 27 UFs.
        blocos: Subconjunto de ["ptts", "municipios", "operadoras"]; omita para todos (os `totais` vêm sempre). Só com `uf`.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    if uf is None:
        itens = _store.resumo_ufs(d)
        return {"snapshot_date": d, "mes_referencia": (_store.sici_meta(d) or {}).get("mes_referencia"), "total": len(itens), "items": itens}
    sigla = uf.strip().upper()
    if sigla not in _UFS_VALIDAS:
        raise ValueError(f"UF '{uf}' desconhecida. Use a sigla de 2 letras (ex.: SP).")
    return _store.perfil_uf(d, sigla, _blocos_validos(blocos, {"ptts", "municipios", "operadoras"}))


# ---------------------------------------------------------------------------
# SICI — Acessos de banda larga fixa declarados à Anatel
# ---------------------------------------------------------------------------

SERVICOS_SICI = ("fixa", "movel")


class _Sici:
    """Acessores do SICI de um serviço: `fixa` lê `sici_*`/`operadora_index`; `movel`, `sici_movel_*`/`operadora_movel_index`.
    As duas famílias têm a mesma forma, então as tools de acessos servem aos dois serviços."""

    def __init__(self, servico: str):
        if servico not in SERVICOS_SICI:
            raise ValueError(f"servico inválido: {servico!r}; válidos: {', '.join(SERVICOS_SICI)}")
        self.servico = servico
        p = "sici_movel_" if servico == "movel" else "sici_"
        for nome in ("meta", "for_cnpj", "for_asn", "cnpj_for_asn", "serie", "serie_total", "municipio", "municipios"):
            setattr(self, nome, getattr(_store, p + nome))
        self.operadoras = _store.operadora_movel_index if servico == "movel" else _store.operadora_index
        self.distribuicao = (("distrib_modalidade", _store.sici_movel_distrib_modalidade) if servico == "movel"
                             else ("distrib_velocidade", _store.sici_distrib_velocidade))

    def meta_ou_erro(self, d: str) -> dict:
        meta = self.meta(d)
        if not meta:
            raise ValueError(f"Dados de acessos {'móveis ' if self.servico == 'movel' else ''}(SICI) indisponíveis no snapshot {d}. "
                             f"Rode {'anatel_sici_movel e sici_movel' if self.servico == 'movel' else 'anatel_sici e sici'}.")
        return meta


def _sici_meta_or_raise(d: str, servico: str = "fixa") -> dict:
    return _Sici(servico).meta_ou_erro(d)


@mcp.tool()
def operator_accesses(
    cnpj: Optional[str] = None,
    asn: Optional[int] = None,
    servico: str = "fixa",
    date: Optional[str] = None,
) -> dict:
    """Base de assinantes declarada à Anatel (SICI) por uma operadora.

    Retorna, para o mês de referência mais recente: acessos totais, split B2C
    (Pessoa Física) × B2B (Pessoa Jurídica), capacidade CONTRATADA, velocidade
    média e mediana, municípios atendidos, mix de tecnologia e meio, série
    histórica mensal e a comparação com os usuários estimados pelo APNIC.

    DUAS DATAS: o `mes_referencia` da declaração é diferente do `snapshot_date`.
    Cite as duas.

    ATENÇÃO a `acessos_compartilhados`: quando o CNPJ tem mais de um ASN, o total é
    atribuído integralmente a CADA ASN. Somar ASes do mesmo CNPJ conta o mesmo
    assinante várias vezes — agregue por CNPJ ou por grupo econômico.

    Args:
        cnpj: CNPJ da operadora (com ou sem formatação). Use este OU asn.
        asn: Número do AS — resolve o CNPJ que o detém.
        servico: fixa (banda larga fixa, padrão) | movel (telefonia móvel).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    sici = _Sici(servico)
    meta = sici.meta_ou_erro(d)
    if asn is not None:
        agg = sici.for_asn(d, int(asn))
        clean = sici.cnpj_for_asn(d, int(asn))
        if not agg:
            raise ValueError(
                f"AS{asn} não tem CNPJ com acessos declarados em {meta['mes_referencia']}."
            )
    elif cnpj:
        clean = re.sub(r"\D", "", cnpj)
        agg = sici.for_cnpj(d, clean)
        if not agg:
            raise ValueError(
                f"CNPJ {clean} não declarou acessos em {meta['mes_referencia']}."
            )
    else:
        raise ValueError("Informe cnpj ou asn.")

    municipios = sorted(
        ({"ibge": k, **v} for k, v in agg.get("por_municipio", {}).items()),
        key=lambda m: -m["acessos"],
    )
    out = {
        "snapshot_date": d,
        "servico": servico,
        "mes_referencia": meta["mes_referencia"],
        "cnpj": clean,
        **{k: v for k, v in agg.items() if k != "por_municipio"},
        "top_municipios": municipios[:25],
        "serie": sici.serie(d, clean),
    }
    if asn is not None:
        out["asn"] = int(asn)
        if servico == "fixa":                       # a divergência APNIC × Anatel só existe para banda larga fixa
            out["divergencia_apnic_anatel"] = _store.sici_divergencia(d, int(asn))
    return out


@mcp.tool()
def municipality_broadband(
    ibge: Optional[str] = None,
    municipio: Optional[str] = None,
    uf: Optional[str] = None,
    limit: int = 25,
    servico: str = "fixa",
    date: Optional[str] = None,
) -> dict:
    """Quem oferece banda larga (ou telefonia móvel, com `servico="movel"`) em um município, com share e concentração.

    Responde "quais provedores atendem a cidade X", "qual a fatia de cada um",
    "o mercado é concentrado". Traz o HHI (10000 = monopólio; abaixo de 1500 é
    considerado competitivo) e quais operadoras têm ASN próprio.

    ATENÇÃO: operadoras de satélite (Starlink, Hughes) declaram acessos em
    praticamente todos os 5.570 municípios. Por isso nenhum município aparece com
    operador único — para avaliar competição local, olhe o share e o HHI, não a
    contagem bruta de operadoras.

    Args:
        ibge: Código IBGE do município (7 dígitos). Preferível — é inequívoco.
        municipio: Nome do município (usado se ibge não for informado).
        uf: UF, para desambiguar nomes repetidos (ex.: "Bom Jesus").
        limit: Quantas operadoras retornar (ordenadas por acessos).
        servico: fixa (padrão) | movel.
        date: Data do snapshot (YYYY-MM-DD).
    """
    d = _resolve(date)
    sici = _Sici(servico)
    meta = sici.meta_ou_erro(d)
    muns = sici.municipios(d)

    if ibge:
        mun = muns.get(str(ibge).strip())
        if not mun:
            raise ValueError(f"Município IBGE {ibge} sem acessos declarados em {d}.")
        matches = [mun]
    elif municipio:
        # sem acento e sem caixa, com "Nome, UF" / "Nome (UF)" aceitos e igualdade antes de trecho
        from mcp_server.entrada import casa_municipio
        matches, perto = casa_municipio(municipio, list(muns.values()), uf)
        if not matches:
            raise ValueError(f"Nenhum município encontrado para '{municipio}'." + (f" Parecidos: {', '.join(perto)}." if perto else "")
                             + " Use o nome (com uf= se houver homônimos) ou o código IBGE de 7 dígitos.")
        matches.sort(key=lambda m: -m.get("acessos", 0))
    else:
        raise ValueError("Informe ibge ou municipio.")

    if len(matches) > 1:
        return {
            "snapshot_date": d,
            "servico": servico,
            "mes_referencia": meta["mes_referencia"],
            "ambiguo": True,
            "candidatos": [
                {"ibge": m["ibge"], "nome": m["nome"], "uf": m["uf"],
                 "acessos": m["acessos"]}
                for m in matches[:20]
            ],
        }

    mun = dict(matches[0])
    mun["operadores"] = mun.get("operadores", [])[:limit]
    return {"snapshot_date": d, "servico": servico, "mes_referencia": meta["mes_referencia"], **mun}


@mcp.tool()
def top_operators(
    uf: Optional[str] = None,
    ibge: Optional[str] = None,
    com_asn: Optional[bool] = None,
    min_acessos: Optional[int] = None,
    metric: str = "acessos",
    limit: int = 25,
    servico: str = "fixa",
    date: Optional[str] = None,
) -> dict:
    """Ranking de operadoras por acessos declarados, capacidade ou municípios (banda larga fixa ou telefonia móvel).

    Sem filtro, é o ranking nacional. Com `ibge`, é o ranking dentro do município.
    Com `com_asn=False` e `min_acessos`, responde a pergunta operacional mais útil
    desta base: "operadoras grandes que ainda não têm ASN próprio".

    Args:
        uf: UF da SEDE da operadora (cadastro SCM) — não é onde estão os clientes.
        ibge: Código IBGE — ranking dentro de um município específico.
        com_asn: True/False para filtrar por ter ASN próprio.
        min_acessos: Mínimo de acessos declarados.
        metric: acessos | capacidade (só fixa) | municipios.
        limit: Quantas operadoras retornar.
        servico: fixa (padrão) | movel.
        date: Data do snapshot (YYYY-MM-DD).
    """
    d = _resolve(date)
    sici = _Sici(servico)
    meta = sici.meta_ou_erro(d)
    limit = max(1, min(limit, 200))
    if servico == "movel" and metric == "capacidade":
        raise ValueError("metric 'capacidade' não existe para o serviço móvel; use acessos ou municipios.")

    if ibge:
        mun = sici.municipio(d, str(ibge).strip())
        if not mun:
            raise ValueError(f"Município IBGE {ibge} sem acessos declarados.")
        rows = [dict(o) for o in mun.get("operadores", [])]
        if com_asn is not None:
            rows = [r for r in rows if bool(r.get("asns")) is com_asn]
        if min_acessos is not None:
            rows = [r for r in rows if r.get("acessos", 0) >= min_acessos]
        return {
            "snapshot_date": d, "servico": servico, "mes_referencia": meta["mes_referencia"],
            "escopo": {"ibge": ibge, "municipio": mun.get("nome"), "uf": mun.get("uf")},
            "total": len(rows), "items": rows[:limit],
        }

    rows = [r for r in sici.operadoras(d) if r.get("ativo")]
    if uf:
        u = uf.upper()
        rows = [r for r in rows if (r.get("uf_sede") or "").upper() == u]
    if com_asn is not None:
        rows = [r for r in rows if bool(r.get("asns")) is com_asn]
    if min_acessos is not None:
        rows = [r for r in rows if r.get("acessos", 0) >= min_acessos]
    key = {"acessos": "acessos", "capacidade": "capacidade_mbps",
           "municipios": "municipios"}.get(metric, "acessos")
    rows.sort(key=lambda r: r.get(key) or 0, reverse=True)
    fields = ("cnpj", "empresa", "razao_social", "uf_sede", "acessos", "acessos_pf",
              "acessos_pj", "municipios", "capacidade_mbps", "tecnologia", "asns",
              "grupo_economico", "acessos_compartilhados")
    if servico == "movel":
        fields = ("cnpj", "empresa", "razao_social", "uf_sede", "acessos", "acessos_pf", "acessos_pj", "acessos_m2m", "municipios",
                  "geracao_predominante", "asns", "grupo_economico", "acessos_compartilhados")
    return {
        "snapshot_date": d, "servico": servico, "mes_referencia": meta["mes_referencia"],
        "metric": key, "total": len(rows),
        "items": [{k: r.get(k) for k in fields} for r in rows[:limit]],
    }


@mcp.tool()
def access_history(
    cnpj: Optional[str] = None,
    asn: Optional[int] = None,
    meses: int = 24,
    servico: str = "fixa",
    date: Optional[str] = None,
) -> dict:
    """Série histórica mensal de acessos de uma operadora, com crescimento — ou a série nacional.

    Cada ponto é [mes, acessos, pessoa_fisica, pessoa_juridica]. Devolve também as
    variações de 1, 6 e 12 meses. Útil para detectar crescimento, estagnação, ou
    quedas abruptas (venda, falência, reorganização societária).

    Sem `cnpj` nem `asn` devolve a SÉRIE NACIONAL do serviço (`serie_nacional`) e a distribuição por
    UF — de velocidade contratada na banda larga fixa (`distrib_velocidade`), de modalidade na
    telefonia móvel (`distrib_modalidade`).

    Args:
        cnpj: CNPJ da operadora. Use este OU asn; omita os dois para a série nacional.
        asn: Número do AS — resolve o CNPJ que o detém.
        meses: Quantos meses retornar (do mais recente para trás).
        servico: fixa (padrão) | movel.
        date: Data do snapshot (YYYY-MM-DD).
    """
    d = _resolve(date)
    sici = _Sici(servico)
    meta = sici.meta_ou_erro(d)
    if asn is None and not cnpj:
        nome, distrib = sici.distribuicao
        serie = sici.serie_total(d)
        return {"snapshot_date": d, "servico": servico, "mes_referencia": meta["mes_referencia"],
                "serie_nacional": serie[-max(1, meses):], "meses_disponiveis": len(serie), nome: distrib(d)}
    if asn is not None:
        clean = sici.cnpj_for_asn(d, int(asn))
        if not clean:
            raise ValueError(f"AS{asn} não tem CNPJ com acessos declarados.")
    else:
        clean = re.sub(r"\D", "", cnpj)

    serie = sici.serie(d, clean)
    if not serie:
        raise ValueError(f"Sem série de acessos para o CNPJ {clean}.")
    janela = serie[-max(1, meses):]

    def _delta(n: int) -> Optional[dict]:
        if len(serie) <= n:
            return None
        atual, antes = serie[-1][1], serie[-1 - n][1]
        if not antes:
            return None
        return {"de": serie[-1 - n][0], "para": serie[-1][0],
                "absoluto": atual - antes,
                "percentual": round(100 * (atual - antes) / antes, 2)}

    return {
        "snapshot_date": d,
        "servico": servico,
        "mes_referencia": meta["mes_referencia"],
        "cnpj": clean,
        "meses_disponiveis": len(serie),
        "serie": janela,
        "variacao_1m": _delta(1),
        "variacao_6m": _delta(6),
        "variacao_12m": _delta(12),
    }


@mcp.tool()
def access_divergence(
    asn: Optional[int] = None,
    classificacao: Optional[str] = None,
    limit: int = 25,
    date: Optional[str] = None,
) -> dict:
    """Divergência entre usuários estimados (APNIC) e acessos declarados (Anatel).

    São duas medições independentes e de naturezas diferentes: o APNIC OBSERVA
    usuários e atribui a ASN; a operadora DECLARA contratos por CNPJ. A razão
    usuários/acesso deveria orbitar o número de pessoas por domicílio — a mediana
    medida é 3,97.

    A divergência é HIPÓTESE A INVESTIGAR, nunca "erro" de uma das fontes. Ao
    responder, ofereça as leituras possíveis, não um veredito:
      - `apnic_alto` (razão > 20): CGNAT concentrando usuários, tráfego de terceiros
        (trânsito/atacado) no AS, ou CNPJ mal atribuído no APNIC.
      - `apnic_baixo` (razão < 1): acessos do CNPJ distribuídos por vários ASes,
        tráfego saindo por AS de trânsito, ou links B2B sem usuários observáveis.
      - `nao_comparavel`: o CNPJ tem mais de um ASN e cada um recebe o total
        integral — comparar produziria artefato.

    Args:
        asn: Um AS específico. Omita para listar o ranking.
        classificacao: normal | apnic_alto | apnic_baixo | nao_comparavel | sem_dados.
        limit: Quantos ASes retornar no ranking.
        date: Data do snapshot (YYYY-MM-DD).
    """
    d = _resolve(date)
    meta = _sici_meta_or_raise(d)
    if asn is not None:
        div = _store.sici_divergencia(d, int(asn))
        if not div:
            raise ValueError(f"AS{asn} não tem divergência calculada em {d}.")
        return {"snapshot_date": d, "mes_referencia": meta["mes_referencia"],
                "asn": int(asn), "cnpj": _store.sici_cnpj_for_asn(d, int(asn)), **div}

    divs = _store.sici_divergencias(d)
    names = {a["asn"]: a.get("name", "") for a in _store.asn_index(d)}
    dist: dict = {}
    rows = []
    for asn_str, div in divs.items():
        dist[div["classificacao"]] = dist.get(div["classificacao"], 0) + 1
        if classificacao and div["classificacao"] != classificacao:
            continue
        if "razao" not in div:
            continue
        a = int(asn_str)
        rows.append({"asn": a, "name": names.get(a, ""), **div})
    rows.sort(key=lambda r: r["razao"], reverse=(classificacao != "apnic_baixo"))
    return {
        "snapshot_date": d, "mes_referencia": meta["mes_referencia"],
        "distribuicao": dist, "total": len(rows), "items": rows[:max(1, min(limit, 200))],
    }


# ---------------------------------------------------------------------------
# Outorgas da Anatel unificadas: a mesma consulta de GET /outorgas
# ---------------------------------------------------------------------------

def _http_para_valor(fn, *a, **kw):
    """Chama uma função das rotas e converte `HTTPException` em `ValueError` (o MCP recusa com mensagem, como `get_operator`)."""
    from fastapi import HTTPException
    try:
        return fn(*a, **kw)
    except HTTPException as exc:
        raise ValueError(str(exc.detail))


@mcp.tool()
def list_outorgas(
    servico: Optional[str] = None,
    todos: bool = False,
    uf: Optional[str] = None,
    municipio: Optional[str] = None,
    q: Optional[str] = None,
    com_asn: Optional[bool] = None,
    ativo: Optional[bool] = None,
    porte: Optional[str] = None,
    min_acessos: Optional[int] = None,
    sort_by: str = "acessos",
    sort_desc: bool = True,
    page: int = 1,
    limit: int = 50,
    date: Optional[str] = None,
) -> dict:
    """Outorgas da Anatel (SCM, SMP, STFC, SeAC) numa lista só: UMA LINHA POR CNPJ, com os serviços que ele tem.

    Cada linha traz `servicos`, `outorgas`, sede, `asns`, `porte` (declarado ao SICI) e os acessos declarados
    (`acessos_fixo`, `acessos_movel`, `acessos`; `ativo` = declarou algum). `data_outorga` é a mais antiga entre os
    serviços. Sem contatos. Responde "quais empresas têm STFC e SeAC", "provedores SCM de uma UF sem ASN",
    "quem tem outorga mas não declara acessos". Para o detalhe de um CNPJ use `get_outorgas`.

    Args:
        servico: SCM, SMP, STFC e/ou SeAC, separados por vírgula (ex.: "SCM,SMP"). Omita para todos.
        todos: Com vários serviços, exige TODOS (E) em vez de qualquer um (OU).
        uf: UF da sede.
        municipio: Município da sede (substring).
        q: Razão social, nome fantasia ou CNPJ.
        com_asn: True = só com ASN; False = só sem ASN.
        ativo: True = só quem declara acessos ao SICI (fixo ou móvel).
        porte: Porte declarado ao SICI (ex.: "Pequeno Porte", "Grande Porte").
        min_acessos: Mínimo de acessos declarados.
        sort_by: razao_social | cnpj | uf | municipio | acessos | acessos_fixo | acessos_movel | pj_fixo | pj_movel | municipios_fixo |
            municipios_movel | outorgas | servicos | asns | data_outorga.
        sort_desc: Ordem decrescente (padrão).
        page: Página (>=1). limit: itens por página (1..500).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    from api.routes.outorgas import montar_lista
    d = _resolve(date)
    return _http_para_valor(montar_lista, _store, d, servico=servico, todos=todos, uf=uf, municipio=municipio, q=q, com_asn=com_asn,
                            ativo=ativo, porte=porte, min_acessos=min_acessos, sort_by=sort_by, sort_desc=sort_desc,
                            page=max(1, page), limit=max(1, min(limit, 500)))


@mcp.tool()
def get_outorgas(cnpj: str, servico: Optional[str] = None, date: Optional[str] = None) -> dict:
    """As outorgas de um CNPJ em cada serviço (SCM, SMP, STFC, SeAC), sem telefone nem e-mail.

    Retorna `servicos` = {SCM: [...], SMP: [...], ...} com as outorgas do CNPJ (geolocalização e ASNs inclusos). Recusa se o CNPJ
    não tem nenhuma. Substitui `get_scm` quando o serviço não é só SCM; para o perfil completo (SICI, rede, grupo) use `get_operator`.

    Args:
        cnpj: CNPJ (14 dígitos, com ou sem formatação).
        servico: Restringe a estes serviços (ex.: "SCM,SMP"). Omita para todos.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    from api.routes.outorgas import montar_do_cnpj
    return _http_para_valor(montar_do_cnpj, _store, _resolve(date), cnpj, servico)


# ---------------------------------------------------------------------------
# Grupos econômicos e assinantes por PTT
# ---------------------------------------------------------------------------

@mcp.tool()
def economic_group(
    grupo_id: Optional[str] = None,
    cnpj: Optional[str] = None,
    limit: int = 25,
    date: Optional[str] = None,
) -> dict:
    """Grupo econômico (societário) de uma empresa ou pelo id do grupo: CNPJs membros, assinantes, usuários APNIC e relações diretas.

    Cruza o quadro de sócios da Receita Federal. Com `cnpj` devolve o grupo da empresa (`individual` = sem relação societária com outra
    da base, `grupo_id` = `ind_{cnpj básico}`) e, em `relacionadas`, as empresas com relação DIRETA (nunca por transitividade):
    `mesmo_grupo` (quadro de sócios idêntico ou controle exclusivo) e `relacionadas_parcial` (sócio em comum, com a contagem, ou controle
    não exclusivo — CPF de PF vem parcialmente mascarado, não é certeza). `assinantes` são os acessos FIXOS declarados ao SICI (não
    inclui móvel). `visibilidade_bgp` = algum AS do grupo origina bloco na tabela global. Para filtrar/cruzar grupos em lote use
    `query(collection="socios")`.

    Args:
        grupo_id: Id do grupo (de `economic_group(cnpj=...)` ou da página Grupos de Empresas). Use este OU cnpj.
        cnpj: CNPJ da empresa (com ou sem formatação).
        limit: Quantos CNPJs e municípios do grupo retornar (1..200); os totais vêm em `cnpjs_total` e `municipios_total`.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    limit = max(1, min(limit, 200))
    limpo = re.sub(r"\D", "", cnpj) if cnpj else None
    if not grupo_id and not limpo:
        raise ValueError("Informe grupo_id ou cnpj.")
    if limpo is not None and len(limpo) != 14:
        raise ValueError("CNPJ inválido — informe 14 dígitos (com ou sem formatação).")
    grupos = _store.grupos_societarios_overview(d)
    if not grupos:
        raise ValueError(f"Grupos econômicos indisponíveis no snapshot {d}.")
    grupo = next((g for g in grupos if (g["grupo_id"] == grupo_id if grupo_id else any(c["cnpj"] == limpo for c in g["cnpjs"]))), None)
    if grupo is None:
        raise ValueError(f"Grupo não encontrado no snapshot {d}: {grupo_id or limpo}.")
    out = {
        "snapshot_date": d,
        **{k: v for k, v in grupo.items() if k not in ("cnpjs", "municipios")},
        "cnpjs_total": len(grupo["cnpjs"]), "cnpjs": grupo["cnpjs"][:limit],
        "municipios_total": len(grupo["municipios"]), "municipios": grupo["municipios"][:limit],
    }
    if limpo:
        rel = _store.empresas_relacionadas(d, limpo)
        out["relacionadas"] = {k: _sem_nomes_de_socios(v) for k, v in rel.items() if k != "snapshot_date"}
    return out


def _sem_nomes_de_socios(v):
    """Tira `nomes_em_comum` (nomes de sócios pessoa física) das relações: no MCP fica só a contagem `socios_em_comum` (AGENTS.md, privacidade).
    O campo só traz nomes de sócios PJ (`core.cpf.sem_socios_pessoa_fisica`); no MCP sai igual."""
    if isinstance(v, list):
        return [{k: x for k, x in i.items() if k != "nomes_em_comum"} if isinstance(i, dict) else i for i in v]
    return v


@mcp.tool()
def ixp_assinantes(code: str, limit: int = 25, date: Optional[str] = None) -> dict:
    """Assinantes (acessos SICI) alcançáveis por um PTT do IX.br: dos peers diretos e dos clientes que eles anunciam.

    `assinantes_diretos` = acessos dos CNPJs dos ASNs em peering direto; `assinantes_total` inclui os ASNs dos AS-paths anunciados por
    esses peers (clientes), deduplicados por CNPJ. `asns` lista os maiores peers por assinantes diretos (empresa, selos de outorga,
    usuários APNIC); `peers_top` os que mais alcançam, por família. `mes_referencia` é o mês do SICI, diferente da data do snapshot.
    Só banda larga fixa (o SICI móvel não entra). O que não cabe vem resumido: veja `asns_total` e `municipios_*_total`.

    Args:
        code: Código do PTT (minúsculo; ex.: "sp", "rj", "vix").
        limit: Quantos peers e municípios listar (1..200).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    limit = max(1, min(limit, 200))
    r = _store.ixp_assinantes(d, code.lower())
    if r is None:
        raise ValueError(f"IXP '{code}' não encontrado no snapshot {d}.")
    asns = sorted(r["asns"].items(), key=lambda kv: -(kv[1].get("assinantes_diretos") or 0))
    return {
        "snapshot_date": d, "code": code.lower(), "mes_referencia": r["mes_referencia"],
        "assinantes_diretos": r["assinantes_diretos"], "assinantes_total": r["assinantes_total"],
        "asns_total": len(asns), "asns": [{"asn": int(a), **v} for a, v in asns[:limit]],
        "peers_top": {afi: [{"asn": int(a), "assinantes_total": n} for a, n in sorted(por.items(), key=lambda kv: -kv[1])[:limit]]
                      for afi, por in r["peers"].items()},
        "municipios_diretos_total": len(r["municipios_diretos"]), "municipios_diretos": r["municipios_diretos"][:limit],
        "municipios_totais_total": len(r["municipios_totais"]), "municipios_totais": r["municipios_totais"][:limit],
    }
