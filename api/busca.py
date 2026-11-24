# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Busca universal: um índice em memória por snapshot e a consulta sobre ele.

O índice é montado uma vez por data (primeira busca) a partir dos índices que o `Store` já mantém (ASNs, operadoras, PTTs, instalações, CDNs,
grupos) e de `config/` (municípios, marcas curadas). **Só entra dado de pessoa jurídica ou do próprio recurso de rede**: nenhum contato,
e-mail, telefone, sócio nem nome de pessoa física; as operadoras entram pelo nome de exibição já público nas páginas de operadora.

Reconhecimento pela forma da consulta (antes da busca por texto): número ou `AS<n>` → AS; IP ou prefixo → página do prefixo; CNPJ completo
(com ou sem máscara) → operadora; raiz de 8 dígitos → operadoras da raiz; 7 dígitos → município (código IBGE); sigla de 2 letras → UF.
Resultados saem agrupados por tipo, com o motivo do acerto (`reconhecido`) quando veio da forma e não do texto."""
from __future__ import annotations

import ipaddress
import json
import re
import threading
import unicodedata
from bisect import bisect_right
from pathlib import Path
from typing import Any

import structlog
import yaml

log = structlog.get_logger(__name__)

CONFIG = Path(__file__).resolve().parents[1] / "config"
LIMITE_PADRAO = 5
LIMITE_MAX = 20
TAMANHO_MAX_CONSULTA = 80

# (tipo, rótulo do grupo) na ordem de exibição.
TIPOS = (
    ("tema", "Páginas e temas"), ("asn", "Sistemas autônomos"), ("operadora", "Operadoras"), ("grupo", "Grupos econômicos"),
    ("municipio", "Municípios"), ("uf", "Estados"), ("ptt", "PTTs"), ("cdn", "CDNs"), ("datacenter", "Datacenters"), ("prefixo", "Prefixos"),
)

UFS = {"AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal",
       "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
       "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
       "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins"}

# Temas: palavras-chave → página. Manter curto e em sincronia com `menu.ts` (o teste confere que toda rota existe no frontend).
TEMAS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("Panorama técnico", "/panorama/tecnico", "Rede brasileira em números: roteamento, PTTs, endereços e segurança", ("panorama", "visao geral", "panorama tecnico", "numeros", "hilbert", "tabela global")),
    ("Panorama de mercado", "/panorama/mercado", "Banda larga, telefonia e TV por assinatura, por serviço", ("panorama de mercado", "estatisticas", "banda larga", "telefonia", "tv por assinatura", "sici")),
    ("Panorama de IPv6", "/panorama/ipv6", "Adoção de IPv6, espaço de endereços e cobertura nos PTTs", ("ipv6", "panorama de ipv6", "adocao de ipv6", "v6")),
    ("Segurança de roteamento", "/seguranca-de-roteamento", "RPKI, ROA, ROV, ASPA e MANRS", ("rpki", "roa", "rov", "aspa", "manrs", "seguranca", "hijack", "sequestro")),
    ("Route servers e communities", "/communities", "Communities BGP e políticas dos route servers", ("communities", "community", "route server", "blackhole")),
    ("Qualidade e reclamações", "/qualidade", "RQUAL, reclamações e consumidor", ("qualidade", "reclamacao", "reclamacoes", "rqual", "consumidor", "anatel")),
    ("Regulatório e FUST", "/regulatorio", "Outorgas, obrigações e financiamento", ("fust", "regulatorio", "outorga", "outorgas", "licenca")),
    ("Uso da Internet", "/uso-da-internet", "Domicílios, acesso e uso (Cetic.br)", ("uso da internet", "cetic", "domicilios", "tic")),
    ("Mercado de endereços IPv4", "/mercado-ipv4", "Transferências e preço de blocos IPv4", ("ipv4", "transferencia", "transferencias", "leilao", "mercado ipv4", "esgotamento")),
    ("Estabilidade BGP", "/bgp", "Flaps, EPPPD e estabilidade das rotas", ("bgp", "estabilidade", "flap", "epppd")),
    ("Rankings do SICI", "/rankings", "Maiores operadoras por acessos", ("ranking", "rankings", "sici", "maiores", "assinantes")),
    ("Grupos econômicos", "/grupos", "Empresas ligadas por sócios em comum ou participação societária", ("grupo economico", "grupos", "holding", "controladora")),
    ("Operadoras", "/operadoras", "Provedores e operadoras outorgados pela Anatel", ("operadoras", "provedores", "provedor", "scm", "smp", "stfc", "seac")),
    ("O que mudou", "/mudancas", "Mudanças entre snapshots", ("mudancas", "mudou", "novidades", "diff")),
    ("Mapa", "/mapa", "Mapa da Internet brasileira", ("mapa", "mapas")),
    ("Comparar", "/comparar", "Comparar ASes, PTTs ou municípios", ("comparar", "comparacao")),
    ("Estados", "/estados", "Panorama por UF", ("estados", "uf", "ufs")),
    ("PTTs", "/ixps", "PTTs do IX.br e participantes", ("ptt", "ptts", "ix.br", "ixbr", "ix", "pix", "interconexao", "peering")),
    ("CDNs e conteúdo", "/cdns", "Onde cada CDN está presente", ("cdn", "cdns", "conteudo", "cap")),
    ("Datacenters", "/instalacoes", "Instalações de colocation e redes presentes", ("datacenter", "datacenters", "colocation", "instalacoes")),
    ("Dados, API e MCP", "/dados", "API REST, servidor MCP e exemplos", ("api", "mcp", "dados", "download", "swagger", "openapi")),
    ("Fontes e metodologia", "/fontes", "Cada fonte, licença e periodicidade", ("fontes", "metodologia", "licenca", "licencas")),
    ("Privacidade", "/privacidade", "Que dados o site registra", ("privacidade", "lgpd")),
)


def normalizar(texto: str) -> str:
    """Minúsculas, sem acento, só letras/dígitos/espaço/ponto, espaços colapsados."""
    t = unicodedata.normalize("NFD", (texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9.+]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def slug(nome: str) -> str:
    """Igual a `cdnSlug` do frontend (`lib/cdn.ts`)."""
    t = unicodedata.normalize("NFD", nome or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", t))


def _item(tipo: str, titulo: str, detalhe: str, url: str, chaves: list[str], peso: float = 0.0, selo: str | None = None) -> dict[str, Any]:
    return {"tipo": tipo, "titulo": titulo, "detalhe": detalhe, "url": url, "selo": selo, "peso": float(peso),
            "chaves": [k for k in (normalizar(c) for c in chaves) if k]}


def _marcas_por_raiz() -> dict[str, list[str]]:
    try:
        dados = yaml.safe_load((CONFIG / "curada_marcas_operadoras.yaml").read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    por_raiz: dict[str, list[str]] = {}
    for m in dados.get("marcas", []):
        for r in m.get("raizes", []):
            por_raiz.setdefault(str(r), []).append(str(m.get("marca", "")).title())
    return por_raiz


def _municipios() -> dict[str, tuple[str, str, float]]:
    """{ibge: (nome, UF, área em km²)}. O arquivo não traz população: a área só desempata homônimos (município maior primeiro)."""
    try:
        bruto = json.loads((CONFIG / "municipios-referencia.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(k): (v[0], v[1], float(v[2] or 0)) for k, v in bruto.items()}


def montar(store: Any, date_str: str) -> list[dict[str, Any]]:
    """Todos os itens pesquisáveis do snapshot. Custa algumas centenas de ms; chamado uma vez por data."""
    itens: list[dict[str, Any]] = []
    marcas = _marcas_por_raiz()

    # Operadoras e nomes alternativos dos ASNs que elas operam.
    nomes_do_asn: dict[int, list[str]] = {}
    grupos_sici: dict[str, int] = {}
    for o in store.operadora_index(date_str) or []:
        cnpj = str(o.get("cnpj") or "")
        if not cnpj:
            continue
        nome = o.get("empresa") or o.get("nome_fantasia") or o.get("razao_social") or cnpj
        marca = marcas.get(cnpj[:8], [])
        local = f"{o['municipio_sede']}/{o['uf_sede']}" if o.get("municipio_sede") and o.get("uf_sede") else ""
        itens.append(_item("operadora", nome, " · ".join(x for x in (f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}" if len(cnpj) == 14 else cnpj, local) if x),
                           f"/operadora/{cnpj}", [nome, o.get("razao_social"), o.get("nome_fantasia"), cnpj, *marca], o.get("acessos") or 0,
                           selo=(f"marca {marca[0]}" if marca else None)))
        for a in o.get("asns") or []:
            nomes_do_asn.setdefault(int(a), []).extend(x for x in (o.get("razao_social"), o.get("nome_fantasia"), *marca) if x)
        g = o.get("grupo_economico")
        if g and g != "OUTROS":
            grupos_sici[g] = grupos_sici.get(g, 0) + int(o.get("acessos") or 0)

    # Razão social e nome fantasia da Receita pelo CNPJ do AS (coleção `asns`): o nome no Registro.br vem abreviado
    # ("Núcleo de Inf. e Coord. do Ponto BR") e não casava com o nome por extenso.
    try:
        for r in store.query_table(date_str, "asns") or []:
            if r.get("asn") is not None:
                nomes_do_asn.setdefault(int(r["asn"]), []).extend(x for x in (r.get("razao_social"), r.get("nome_fantasia")) if x)
    except Exception:  # snapshot sem a coleção: a busca segue com os nomes do índice
        pass

    for a in store.asn_index(date_str) or []:
        n = a.get("asn")
        if n is None:
            continue
        itens.append(_item("asn", f"AS{n}", a.get("name") or "", f"/asn/{n}", [f"as{n}", str(n), a.get("name"), *nomes_do_asn.get(int(n), [])],
                           a.get("apnic_users") or 0, selo="BR" if a.get("is_br") else None))

    # Grupos econômicos: rótulo do SICI (ex.: TELECOM AMERICAS) e grupos societários pelos nomes das empresas (só PJ).
    try:
        grupos = store.grupos_societarios_overview(date_str) or []
    except Exception:  # índice ausente em snapshot antigo: a busca segue sem grupos
        grupos = []
    for g in grupos:
        membros = [m for m in g.get("cnpjs", []) if m.get("empresa")]
        if g.get("tamanho", 0) < 2 or not membros:
            continue
        membros.sort(key=lambda m: -(m.get("assinantes") or 0))
        titulo = f"Grupo de {membros[0]['empresa']}"
        itens.append(_item("grupo", titulo, f"{g['tamanho']} empresas · classificação {g.get('classificacao', '')}".strip(" ·"),
                           f"/grupo/{g['grupo_id']}", [m["empresa"] for m in membros], g.get("assinantes") or 0))

    for ibge, (nome, uf, area_km2) in _municipios().items():
        itens.append(_item("municipio", f"{nome}/{uf}", f"município · IBGE {ibge}", f"/municipio/{ibge}", [nome, f"{nome} {uf}", ibge], area_km2))
    for sigla, nome in UFS.items():
        itens.append(_item("uf", nome, f"estado · {sigla}", f"/uf/{sigla}", [nome, sigla], 1e9))

    for i in store.ixp_index(date_str) or []:
        cod = str(i.get("code") or "")
        if cod:
            itens.append(_item("ptt", f"PTT {cod.upper()}", " · ".join(x for x in (i.get("name"), i.get("uf")) if x), f"/ixp/{cod}",
                               [cod, i.get("name"), f"ptt {cod}", i.get("uf")], i.get("asn_direct_union_count") or 0, selo="IX.br"))
    try:
        externos = (store.external_ixp_index(date_str) or {}).get("ixps", [])
    except Exception:
        externos = []
    for i in externos:
        cod = str(i.get("code") or "")
        if cod:
            itens.append(_item("ptt", i.get("name") or cod.upper(), " · ".join(x for x in (i.get("city"), i.get("country")) if x), f"/ixp-externo/{cod}",
                               [cod, i.get("name"), i.get("city")], i.get("br_member_count") or 0, selo="externo"))

    try:
        for c in (store.cdn_presence(date_str) or {}).get("cdns", []):
            if c.get("name"):
                itens.append(_item("cdn", c["name"], f"{len(c.get('asns') or [])} ASN", f"/cdncap/{slug(c['name'])}", [c["name"]], len(c.get("ixbr") or []) + 1))
    except Exception:
        pass
    try:
        for f in ((store.instalacoes_doc(date_str) or {}).get("instalacoes") or {}).values():
            if f.get("escopo", "brasil") == "brasil" and f.get("nome"):
                itens.append(_item("datacenter", f["nome"], " · ".join(x for x in (f.get("org_nome"), f.get("cidade") and f"{f['cidade']}/{f.get('uf')}") if x),
                                   f"/instalacao/{f['id']}", [f["nome"], f.get("org_nome"), f.get("cidade")], f.get("redes_declaradas") or 0))
    except Exception:
        pass

    for titulo, url, desc, palavras in TEMAS:
        itens.append(_item("tema", titulo, desc, url, [titulo, *palavras], 1e12))
    return itens


# ── Consulta ────────────────────────────────────────────────────────────────

_CNPJ = re.compile(r"^\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}$")
_RAIZ = re.compile(r"^\d{2}\.?\d{3}\.?\d{3}$")
_ASN = re.compile(r"^(?:as\s?)?(\d{1,10})$")


def _prefixo(q: str) -> str | None:
    try:
        if "/" in q:
            return str(ipaddress.ip_network(q, strict=False))
        return str(ipaddress.ip_address(q))
    except ValueError:
        return None


def pontuar(item: dict[str, Any], q: str) -> int | None:
    """0 = chave igual; 1 = começa por; 2 = palavra começa por; 3 = contém; None = não casa."""
    melhor = None
    for k in item["chaves"]:
        if k == q:
            return 0
        if k.startswith(q):
            p = 1
        elif f" {q}" in k:
            p = 2
        elif q in k:
            p = 3
        else:
            continue
        melhor = p if melhor is None or p < melhor else melhor
    return melhor


class _Tipo:
    """Itens de um tipo com um *blob* de busca: `\x00chave\x01chave\x00chave…`; `str.find` varre MBs em milissegundos (em C)."""

    CAPS = (600, 1200, 2500)   # candidatos por passada: começa por, palavra começa por, contém

    def __init__(self, itens: list[dict[str, Any]]):
        self.itens = sorted(itens, key=lambda i: -i["peso"])
        partes, self.inicio, pos = [], [], 0
        for it in self.itens:
            txt = "\x00" + "\x01".join(it["chaves"])
            self.inicio.append(pos)
            pos += len(txt)
            partes.append(txt)
        self.blob = "".join(partes)

    def candidatos(self, q: str) -> list[dict[str, Any]]:
        padroes = [("\x00" + q, 1), ("\x01" + q, 1), (" " + q, 0)]
        if len(q) >= 3:
            padroes.append((q, 0))
        idx: set[int] = set()
        for n, (pad, desloca) in enumerate(padroes):
            cap = self.CAPS[min(n, 2)]
            achou, pos = 0, 0
            while achou < cap:
                pos = self.blob.find(pad, pos)
                if pos < 0:
                    break
                idx.add(bisect_right(self.inicio, pos) - 1)
                achou += 1
                pos += 1
        return [self.itens[i] for i in sorted(idx)]


class Indice:
    """Itens de um snapshot por tipo. Como os itens estão ordenados por peso, o corte de candidatos preserva os mais relevantes."""

    def __init__(self, itens: list[dict[str, Any]]):
        lotes: dict[str, list[dict[str, Any]]] = {t: [] for t, _ in TIPOS}
        for i in itens:
            lotes.setdefault(i["tipo"], []).append(i)
        self.por_tipo = {t: _Tipo(v) for t, v in lotes.items()}
        self.por_url = {i["url"]: i for i in itens}
        self.por_cnpj = {i["url"].rsplit("/", 1)[1]: i for i in lotes["operadora"]}
        self.asn_por_numero = {i["url"].rsplit("/", 1)[1]: i for i in lotes["asn"]}
        self.por_ibge = {i["url"].rsplit("/", 1)[1]: i for i in lotes["municipio"]}
        self.total = len(itens)

    def buscar(self, consulta: str, limite: int) -> dict[str, Any]:
        bruta = (consulta or "").strip()[:TAMANHO_MAX_CONSULTA]
        q = normalizar(bruta)
        achados: dict[str, list[dict[str, Any]]] = {t: [] for t, _ in TIPOS}
        totais: dict[str, int] = {t: 0 for t, _ in TIPOS}
        reconhecido: list[str] = []
        vistos: set[str] = set()

        def fixar(tipo: str, item: dict[str, Any] | None, motivo: str) -> None:
            if item and item["url"] not in vistos:
                vistos.add(item["url"])
                achados[tipo].append({**item, "motivo": motivo})
                if tipo not in reconhecido:
                    reconhecido.append(tipo)

        m = _ASN.match(q)
        if m:
            fixar("asn", self.asn_por_numero.get(m.group(1)), "número de AS")
        digitos = re.sub(r"\D", "", bruta)
        if _CNPJ.match(bruta):
            fixar("operadora", self.por_cnpj.get(digitos), "CNPJ")
        elif _RAIZ.match(bruta) or (digitos.isdigit() and len(digitos) == 8 and bruta == digitos):
            for cnpj, it in self.por_cnpj.items():
                if cnpj.startswith(digitos):
                    fixar("operadora", it, "raiz do CNPJ")
        if bruta.isdigit() and len(bruta) == 7:
            fixar("municipio", self.por_ibge.get(bruta), "código IBGE")
        if len(bruta) == 2 and bruta.upper() in UFS:
            fixar("uf", self.por_url.get(f"/uf/{bruta.upper()}"), "sigla de UF")
        pref = _prefixo(bruta) if re.match(r"^[0-9a-fA-F:.]+(/\d{1,3})?$", bruta) else None
        if pref:
            achados["prefixo"].append({"tipo": "prefixo", "titulo": pref, "detalhe": "prefixo" if "/" in pref else "endereço IP", "selo": None, "peso": 0,
                                       "url": f"/prefixo/{pref}", "motivo": "prefixo" if "/" in pref else "endereço IP"})
            reconhecido.append("prefixo")

        if len(q) >= 2 and not (pref and "/" in bruta):
            for tipo, bloco in self.por_tipo.items():
                if tipo == "prefixo":
                    continue
                cand = []
                for it in bloco.candidatos(q):
                    p = pontuar(it, q)
                    if p is not None:
                        cand.append((p, -it["peso"], len(it["titulo"]), it))
                cand.sort(key=lambda c: c[:3])
                totais[tipo] = len(cand)
                for *_, it in cand:
                    if len(achados[tipo]) >= limite:
                        break
                    if it["url"] not in vistos:
                        vistos.add(it["url"])
                        achados[tipo].append({**it, "motivo": "texto"})
        for t in achados:
            totais[t] = max(totais[t], len(achados[t]))

        grupos = []
        for tipo, rotulo in TIPOS:
            if achados[tipo]:
                grupos.append({"tipo": tipo, "rotulo": rotulo, "total": totais[tipo], "itens": [
                    {k: v for k, v in i.items() if k in ("tipo", "titulo", "detalhe", "url", "selo", "motivo")} for i in achados[tipo][:limite]]})
        # Quem foi reconhecido pela forma vai para o topo.
        grupos.sort(key=lambda g: 0 if g["tipo"] in reconhecido else 1)
        return {"q": bruta, "reconhecido": reconhecido, "grupos": grupos}


_CACHE: dict[tuple[int, str], Indice] = {}
_TRAVA = threading.Lock()


def indice(store: Any, date_str: str) -> Indice:
    """Índice do snapshot, em memória (uma entrada por data; só a data mais recente costuma ser pedida).

    Montado sob trava: leva ~25 s e, sem ela, cada pedido simultâneo a frio montaria o seu. O aquecimento da API
    (`api.main._warmup_sync`, `PREWARM_BUSCA`) o monta no fundo depois do restart, para o primeiro visitante não esperar."""
    chave = (id(store), date_str)
    pronto = _CACHE.get(chave)
    if pronto is not None:
        return pronto
    with _TRAVA:
        pronto = _CACHE.get(chave)
        if pronto is None:
            pronto = Indice(montar(store, date_str))
            while len(_CACHE) >= 2:
                _CACHE.pop(next(iter(_CACHE)))  # no máximo 2 datas em memória
            _CACHE[chave] = pronto
            log.info("busca_indice_montado", date=date_str, itens=pronto.total)
    return pronto
