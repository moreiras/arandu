# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Consultas ao histórico: uma implementação para a API REST, o MCP e o `/query`.

Cada função recebe o `HistoricoRepo` e devolve o corpo da resposta; erro de uso ou ausência levanta `HistoricoErro(status, mensagem)`, que a
rota converte em HTTP e o MCP em `ValueError`. Os eventos descrevem diferenças observadas entre snapshots, sem causa nem intenção e sem nome de
empresa; os de provedor (`provedor_novo`, `provedor_perdido`) vêm de uma inferência (ARC v1) e saem com `natureza: "inferido"`."""
from __future__ import annotations

import re
from typing import Callable, Optional
from urllib.parse import urlparse

from api.repos.historico import HistoricoRepo
from core.site import SITE


def _autoridade_tag() -> str:
    """Autoridade dos `tag:` URIs do feed (RFC 4151): o host do `SITE_URL`, para os ids não apontarem para outra instância."""
    return urlparse(SITE.url).hostname or "localhost"


class HistoricoErro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


# Colunas das séries de ASN. `metrics=` aceita os apelidos do plano (prefixes_v4, roa, ixps…) e as colunas; hashes não saem.
_METRICAS_ASN = {
    "users": ["users"], "v6users": ["v6users"], "prefixes_v4": ["p4"], "prefixes_v6": ["p6"], "prefixes": ["p4", "p6"],
    "ixps": ["n_ixd", "n_ixm"], "provedores": ["n_provedores"], "roa": ["n_roa"], "aspa": ["n_aspa"],
    "rpki": ["rpki_valid", "rpki_invalid", "rpki_not_found"], "alertas": ["n_alertas"],
}
_COLUNAS_ASN = ["users", "v6users", "p4", "p6", "n_ixd", "n_ixm", "n_provedores", "n_roa", "n_aspa", "rpki_valid", "rpki_invalid", "rpki_not_found", "n_alertas"]
_INFERIDOS = {"provedor_novo", "provedor_perdido"}
_ESTADOS = {"confirmado", "pendente", "revertido"}
_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _data(valor: Optional[str], nome: str) -> Optional[str]:
    if valor is not None and not _DATA.match(valor):
        raise HistoricoErro(400, f"`{nome}` deve ser uma data AAAA-MM-DD (ex.: 2026-11-06); recebido {valor!r}")
    return valor


def _recorte(datas: list[str], de: Optional[str], ate: Optional[str]) -> list[str]:
    return [d for d in datas if (de is None or d >= de) and (ate is None or d <= ate)]


def _colunas(metrics: Optional[str]) -> list[str]:
    if not metrics:
        return list(_COLUNAS_ASN)
    pedidas, colunas = [m.strip() for m in metrics.split(",") if m.strip()], []
    ruins = [m for m in pedidas if m not in _METRICAS_ASN and m not in _COLUNAS_ASN]
    if ruins:
        raise HistoricoErro(400, f"metrics inválidas: {ruins}; válidas: {sorted(_METRICAS_ASN) + _COLUNAS_ASN}")
    for m in pedidas:
        for c in _METRICAS_ASN.get(m, [m]):
            if c not in colunas:
                colunas.append(c)
    return colunas


def _serie(repo: HistoricoRepo, de, ate, leitor, projetar, entidade: dict, rotulo: str) -> dict:
    datas = _recorte(repo.datas(), _data(de, "from"), _data(ate, "to"))
    pontos = []
    for d in datas:
        linha = leitor(repo, d)
        if linha is not None:
            pontos.append({"date": d, **projetar(linha)})
    if not pontos:
        raise HistoricoErro(404, f"Sem histórico para {rotulo} no período (snapshots com histórico: {len(repo.datas())}).")
    return {**entidade, "total": len(pontos), "snapshots": pontos}


def serie_asn(repo: HistoricoRepo, asn: int, metrics: Optional[str] = None, de: Optional[str] = None, ate: Optional[str] = None) -> dict:
    cols = _colunas(metrics)
    return _serie(repo, de, ate, lambda r, d: r.linha_asn(d, asn),
                  lambda ln: {k: ln[k] for k in ["is_br", *cols] if k in ln}, {"asn": asn, "metrics": cols}, f"AS{asn}")


def serie_ixp(repo: HistoricoRepo, code: str, de: Optional[str] = None, ate: Optional[str] = None) -> dict:
    return _serie(repo, de, ate, lambda r, d: r.linha_ixp(d, code),
                  lambda ln: {k: v for k, v in ln.items() if k != "ixp"}, {"ixp": code}, f"o PTT {code}")


def serie_operadora(repo: HistoricoRepo, cnpj: str, de: Optional[str] = None, ate: Optional[str] = None) -> dict:
    digitos = re.sub(r"\D", "", cnpj)
    if len(digitos) != 14:
        raise HistoricoErro(400, "cnpj deve ter 14 dígitos")
    return _serie(repo, de, ate, lambda r, d: r.linha_operadora(d, digitos),
                  lambda ln: {k: v for k, v in ln.items() if k != "cnpj"}, {"cnpj": digitos}, f"o CNPJ {digitos}")


def serie_uf(repo: HistoricoRepo, uf: str, de: Optional[str] = None, ate: Optional[str] = None) -> dict:
    sigla = uf.strip().upper()
    return _serie(repo, de, ate, lambda r, d: r.linha_uf(d, sigla),
                  lambda ln: {k: v for k, v in ln.items() if k != "uf"}, {"uf": sigla}, f"a UF {sigla}")


def eventos_brutos(repo: HistoricoRepo, de, ate, tipos: Optional[set], uf, asn, estados: Optional[set], ixp: Optional[str] = None) -> list[dict]:
    out = []
    for d in _recorte(repo.datas(), _data(de, "from"), _data(ate, "to")):
        for e in repo.eventos(d):
            if tipos and e["tipo"] not in tipos:
                continue
            if estados and e["estado"] not in estados:
                continue
            if uf and e.get("uf") != uf:
                continue
            if asn is not None and e.get("asn") != asn:
                continue
            if ixp and (e.get("detalhe") or {}).get("ixp") != ixp:
                continue
            out.append({**e, "natureza": "inferido" if e["tipo"] in _INFERIDOS else "observado"})
    return out


def filtro_estados(estado: str) -> Optional[set]:
    if estado == "todos":
        return None
    sel = {x.strip() for x in estado.split(",") if x.strip()}
    if not sel or not sel <= _ESTADOS:
        raise HistoricoErro(400, f"estado inválido: use {sorted(_ESTADOS)} ou 'todos'")
    return sel


def mudancas(repo: HistoricoRepo, de=None, ate=None, tipo: Optional[str] = None, uf: Optional[str] = None, asn: Optional[int] = None,
             estado: str = "confirmado", limit: int = 100, offset: int = 0, ixp: Optional[str] = None) -> dict:
    tipos = {t.strip() for t in (tipo or "").split(",") if t.strip()} or None
    itens = eventos_brutos(repo, de, ate, tipos, uf.upper() if uf else None, asn, filtro_estados(estado), ixp.strip().lower() if ixp else None)
    itens.sort(key=lambda e: (e["data"], e["tipo"], e["entidade"], e["chave"]), reverse=True)
    return {"total": len(itens), "limit": limit, "offset": offset, "items": itens[offset:offset + limit]}


def mudancas_resumo(repo: HistoricoRepo, de=None, ate=None) -> dict:
    itens = eventos_brutos(repo, de, ate, None, None, None, None)
    por_tipo: dict[str, dict[str, int]] = {}
    por_data: dict[str, int] = {}
    for e in itens:
        t = por_tipo.setdefault(e["tipo"], {"confirmado": 0, "pendente": 0, "revertido": 0})
        t[e["estado"]] += 1
        por_data[e["data"]] = por_data.get(e["data"], 0) + 1
    return {"total": len(itens), "por_tipo": dict(sorted(por_tipo.items())), "por_data": dict(sorted(por_data.items())),
            "snapshots_com_historico": len(_recorte(repo.datas(), de, ate))}


_SOMAS_UF = ["n_asns", "users", "v6users", "p4", "p6", "n_roa", "rpki_valid", "rpki_invalid", "rpki_not_found"]


def diferenca(repo: HistoricoRepo, a: str, b: str) -> dict:
    _data(a, "a"), _data(b, "b")
    for d in (a, b):
        if d not in repo.entradas():
            raise HistoricoErro(404, f"Sem histórico em {d} (snapshots com histórico: {', '.join(repo.datas()) or 'nenhum'}).")

    def totais(d: str) -> dict:
        ufs, ixps = repo.linhas_uf(d), repo.linhas_ixp(d)
        t = {k: sum(u.get(k, 0) for u in ufs) for k in _SOMAS_UF}
        t["ptts_coletados"] = sum(1 for i in ixps if i.get("status") == "ok")
        t["ptts_membros"] = sum(i.get("n_membros") or 0 for i in ixps)
        return t

    ta, tb = totais(a), totais(b)
    de, ate = sorted((a, b))
    ev = [e for d in repo.datas() if de < d <= ate for e in repo.eventos(d)]
    resumo: dict[str, dict[str, int]] = {}
    for e in ev:
        resumo.setdefault(e["tipo"], {"confirmado": 0, "pendente": 0, "revertido": 0})[e["estado"]] += 1
    return {"a": a, "b": b, "totais": {k: {"a": ta[k], "b": tb[k], "variacao": tb[k] - ta[k]} for k in ta},
            "eventos": {"entre": [de, ate], "total": len(ev), "por_tipo": dict(sorted(resumo.items()))},
            "nota": "Totais por UF somam ASNs com sede na UF; usuários são estimativas da APNIC."}


def tendencia(repo: HistoricoRepo, escopo: str, metrica: str, de: Optional[str] = None, ate: Optional[str] = None) -> dict:
    """Série de UMA métrica num escopo (`brasil`, `uf:SP`, `ixp:sp`, `operadora:<cnpj>`, `asn:<n>`), com a variação do primeiro ao último ponto."""
    tipo, _, chave = escopo.partition(":")
    if tipo == "brasil":
        datas = _recorte(repo.datas(), _data(de, "from"), _data(ate, "to"))
        pontos = [{"date": d, **{k: sum(u.get(k, 0) for u in repo.linhas_uf(d)) for k in _SOMAS_UF}} for d in datas if repo.linhas_uf(d)]
        corpo = {"snapshots": pontos}
    else:
        leitor = {"uf": lambda: serie_uf(repo, chave, de, ate), "ixp": lambda: serie_ixp(repo, chave, de, ate),
                  "operadora": lambda: serie_operadora(repo, chave, de, ate), "asn": lambda: serie_asn(repo, int(chave) if chave.isdigit() else -1, None, de, ate)}.get(tipo)
        if leitor is None:
            raise HistoricoErro(400, "escopo deve ser brasil, uf:XX, ixp:código, operadora:cnpj ou asn:número")
        corpo = leitor()
    serie = [{"date": p["date"], "valor": p[metrica]} for p in corpo["snapshots"] if metrica in p]
    if not serie:
        raise HistoricoErro(404, f"Sem a métrica '{metrica}' no escopo '{escopo}' (use uma coluna das séries, ex.: users, p4, n_roa).")
    primeiro, ultimo = serie[0]["valor"], serie[-1]["valor"]
    return {"escopo": escopo, "metrica": metrica, "total": len(serie), "serie": serie,
            "variacao": {"de": serie[0]["date"], "para": serie[-1]["date"], "absoluta": ultimo - primeiro,
                         "pct": round(100 * (ultimo - primeiro) / primeiro, 2) if primeiro else None}}


# ── bloco `historico` dos perfis consolidados (ASN, PTT, operadora, UF) ────────────────────────────────────────────────────────────
# Colunas por escopo. `n_provedores` fica de fora da interface (ARC v1 varia entre snapshots), embora a API de séries o traga.
_COLUNAS_PERFIL = {
    "asn": ["users", "v6users", "p4", "p6", "n_ixd", "n_ixm", "n_roa", "n_aspa", "rpki_valid", "rpki_invalid", "rpki_not_found", "n_alertas"],
    "ixp": ["status", "n_direct", "n_br_direct", "n_origin", "n_br_origin", "n_membros", "v4_rotas", "v4_prefixos", "v6_rotas", "v6_prefixos"],
    "operadora": ["n_asns", "users", "users_ma4", "n_ma4", "v6users", "p4", "p6", "n_ixd", "n_roa", "rpki_valid", "rpki_invalid", "rpki_not_found", "n_alertas"],
    "uf": ["n_asns", "n_cnpjs", "users", "users_ma4", "n_ma4", "v6users", "p4", "p6", "n_roa", "rpki_valid", "rpki_invalid", "rpki_not_found"],
}
LIMITE_EVENTOS_PERFIL = 30


def perfil(repo: HistoricoRepo, escopo: str, chave: str, completo: bool, recentes: list[str]) -> Optional[dict]:
    """O bloco `historico` do perfil de uma entidade: série e eventos recentes. `completo=False` (anônimo) limita às datas atuais (`recentes`),
    como a política de acesso exige para a série inteira. None se a entidade não tem linha em nenhuma data. Eventos de provedor ficam de fora."""
    datas = [d for d in repo.datas() if completo or d in recentes]
    leitor = {"asn": lambda d: repo.linha_asn(d, int(chave)), "ixp": lambda d: repo.linha_ixp(d, chave),
              "operadora": lambda d: repo.linha_operadora(d, chave), "uf": lambda d: repo.linha_uf(d, chave)}[escopo]
    cols = _COLUNAS_PERFIL[escopo]
    serie = []
    for d in datas:
        ln = leitor(d)
        if ln is not None:
            serie.append({"date": d, **{k: ln[k] for k in cols if k in ln}})
    if not serie:
        return None
    # Candidatos pelo índice do repositório (nada de varrer todos os eventos a cada perfil); o filtro `casa` continua valendo.
    if escopo == "operadora":
        asns = set(repo.asns_do_cnpj(datas[-1], chave))
        casa = lambda e: e.get("asn") in asns or e["entidade"] == f"cnpj:{chave}"      # noqa: E731
        vistos: set[int] = set()
        candidatos = []
        for e in [x for a in asns for x in repo.eventos_de("asn", a)] + repo.eventos_de("entidade", f"cnpj:{chave}"):
            if id(e) not in vistos:
                vistos.add(id(e))
                candidatos.append(e)
        candidatos.sort(key=repo.posicao)                    # a ordem de todos_eventos, inclusive entre empates da chave
    elif escopo == "asn":
        casa = lambda e: e.get("asn") == int(chave)                                     # noqa: E731
        candidatos = repo.eventos_de("asn", int(chave))
    elif escopo == "ixp":
        casa = lambda e: e["tipo"].startswith("ixp_") and e["chave"] == chave           # noqa: E731
        candidatos = repo.eventos_de("ixp", chave)
    else:
        # Em UF os alertas (centenas por snapshot) afogariam o resto; ficam na página do AS e em /changes
        casa = lambda e: e.get("uf") == chave and not e["tipo"].startswith("alerta_")   # noqa: E731
        candidatos = repo.eventos_de("uf", chave)
    eventos = []
    no_recorte = set(datas)
    todos = [e for e in candidatos if e["data"] in no_recorte and e["estado"] != "revertido" and e["tipo"] not in _INFERIDOS and casa(e)]
    for e in todos[:LIMITE_EVENTOS_PERFIL]:
        eventos.append({k: e[k] for k in ("data", "tipo", "entidade", "chave", "de", "para", "estado", "destaque") if k in e})
    return {"completo": completo, "snapshots_com_historico": len(repo.datas()), "colunas": [c for c in cols if any(c in p for p in serie)],
            "serie": serie, "eventos": eventos, "eventos_total": len(todos)}


# ── Feed Atom ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# Uma entrada por (data, tipo) com as contagens e até ITENS_POR_ENTRADA eventos. Só eventos CONFIRMADOS, só as datas atuais (o feed é aberto: a série
# antiga exige login) e sem provedor (inferência do ARC v1). Linguagem de evidência: diferença observada, sem causa, intenção ou nome de empresa.
ITENS_POR_ENTRADA = 25
_DESCRICAO = {
    "asn_novo": "ASes passaram a aparecer na tabela de roteamento", "asn_sumido": "ASes deixaram de aparecer na tabela de roteamento",
    "ixp_entrada": "ASes passaram a constar como membros de PTTs", "ixp_saida": "ASes deixaram de constar como membros de PTTs",
    "ixp_entrada_observada": "ASes passaram a ser vistos em par direto em PTTs", "ixp_saida_observada": "ASes deixaram de ser vistos em par direto em PTTs",
    "mudanca_origem": "prefixos mudaram de origem", "roa_ganho": "ASes passaram a ter ROA", "roa_perdido": "ASes deixaram de ter ROA",
    "aspa_ganho": "ASes passaram a publicar ASPA", "aspa_perdido": "ASes deixaram de publicar ASPA",
    "rpki_invalido_novo": "ASes passaram a ter prefixo com RPKI inválido", "rpki_invalido_resolvido": "ASes deixaram de ter prefixo com RPKI inválido",
    "outorga_nova": "novas outorgas no cadastro da Anatel", "outorga_baixa": "outorgas deixaram de constar no cadastro da Anatel",
    "alerta_novo": "novos pontos de atenção", "alerta_resolvido": "pontos de atenção deixaram de aparecer",
}


def _item_feed(e: dict) -> str:
    ent = e["entidade"]
    if e["tipo"] == "mudanca_origem":
        return f"{ent.replace('prefixo:', '')}: de AS{e.get('de')} para AS{e.get('para')}" + (" (novo estado: RPKI inválido)" if e.get("destaque") else "")
    base = ent.replace("asn:", "AS").replace("cnpj:", "CNPJ ")
    return f"{base} ({e['chave']})" if e["chave"] and e["tipo"] not in ("outorga_nova", "outorga_baixa") else base


def feed_atom(repo: HistoricoRepo, recentes: list[str], base_url: str) -> str:
    from xml.sax.saxutils import escape

    datas = [d for d in reversed(repo.datas()) if d in recentes]
    entradas = []
    for d in datas:
        por_tipo: dict[str, list[dict]] = {}
        for e in repo.eventos(d):
            if e["estado"] == "confirmado" and e["tipo"] in _DESCRICAO:
                por_tipo.setdefault(e["tipo"], []).append(e)
        for tipo in sorted(por_tipo):
            evs = sorted(por_tipo[tipo], key=lambda e: (e["entidade"], e["chave"]))
            itens = "".join(f"<li>{escape(_item_feed(e))}</li>" for e in evs[:ITENS_POR_ENTRADA])
            resto = f"<p>e mais {len(evs) - ITENS_POR_ENTRADA}.</p>" if len(evs) > ITENS_POR_ENTRADA else ""
            corpo = (f"<p>Diferença observada entre o snapshot anterior e o de {d}; não indica causa nem intenção.</p><ul>{itens}</ul>{resto}"
                     f"<p><a href=\"{base_url}/mudancas\">Ver em O que mudou</a></p>")
            entradas.append(
                f"<entry><title>{escape(f'{len(evs)} {_DESCRICAO[tipo]} ({d})')}</title><id>tag:{_autoridade_tag()},{d}:mudancas/{tipo}</id>"
                f"<updated>{d}T00:00:00Z</updated><link href=\"{base_url}/mudancas\"/><content type=\"html\">{escape(corpo)}</content></entry>")
    atualizado = f"{datas[0]}T00:00:00Z" if datas else "1970-01-01T00:00:00Z"
    return ("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<feed xmlns=\"http://www.w3.org/2005/Atom\">"
            f"<title>{escape(SITE.nome)} — O que mudou</title><subtitle>Diferenças observadas entre snapshots da Internet brasileira, só as confirmadas. "
            "Sem causa nem intenção atribuída.</subtitle>"
            f"<id>tag:{_autoridade_tag()},2026:mudancas</id><updated>{atualizado}</updated>"
            f"<link rel=\"self\" href=\"{base_url}/api/v1/feed/mudancas.atom\"/><link href=\"{base_url}/mudancas\"/>"
            f"<author><name>{escape(SITE.nome)}</name></author>{''.join(entradas)}</feed>\n")
