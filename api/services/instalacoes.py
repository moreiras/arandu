# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Instalações do PeeringDB: lista, detalhe, blocos do PTT e do ASN, portas externas e tabelas do `/query`. Funções puras sobre `instalacoes/*.json.gz`.

É cadastro autodeclarado no PeeringDB (datacenters e pontos de interconexão, com as redes, PTTs e carriers que declaram estar neles). O campo `cadastro` é INFERÊNCIA a partir das
datas de atualização do registro e não diz nada sobre a operação da instalação nem da empresa. Não há contato aqui: o coletor os descarta.
"""
from __future__ import annotations

from typing import Callable, Optional

CADASTRO = ("recente", "parado", "antigo")
ORDENS = {
    "redes": "número de redes vinculadas à instalação no PeeringDB, decrescente",
    "ptts": "número de PTTs na instalação, decrescente",
    "nome": "nome da instalação, A–Z",
    "atualizado": "atualização mais recente do cadastro, da mais recente para a mais antiga",
}


class InstalacoesErro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status, self.mensagem = status, mensagem


def _meta(doc: dict) -> dict:
    return {"snapshot_date": doc["snapshot_date"], "coletado_em": doc.get("coletado_em"), "fonte": doc.get("fonte"), "limites": doc.get("limites"), "regra_cadastro": doc.get("regra_cadastro")}


def _ptts_da_instalacao(f: dict) -> list[dict]:
    """PTTs da instalação com código e tipo: primeiro os do IX.br, depois os externos e por fim os do PeeringDB que o site não acompanha (sem `code`)."""
    ordem = {"ixbr": 0, "externo": 1}
    return [{k: v for k, v in {"ix_id": x["ix_id"], "code": x.get("code"), "tipo": x.get("tipo")}.items() if v is not None}
            for x in sorted(f.get("ixps") or [], key=lambda x: (ordem.get(x.get("tipo"), 2), x.get("code") or "~", x["ix_id"]))]


def cobertura_nomeada(doc: dict, ptts_do_site: Optional[dict[str, str]]) -> Optional[dict]:
    """Cobertura do snapshot com os PTTs do IX.br do site nomeados (`ptts_ixbr_nomes`, `{código: cidade}`) e quem o mapeamento com o PeeringDB não alcança. Calculado na leitura, também
    para snapshots antigos: `ptts_ixbr_sem_mapeamento` são os PTTs do site que não aparecem em nenhuma instalação nem na lista de "sem instalação" (sem registro ligado no PeeringDB), e
    `ptts_ixbr_fora_do_site` os códigos que o produto trouxe e que não são PTT do site. Com instalação + sem instalação + sem mapeamento = PTTs do site."""
    cob = doc.get("cobertura")
    if cob is None or not ptts_do_site:
        return cob
    site = set(ptts_do_site)
    com = {x["code"] for f in doc["instalacoes"].values() for x in f.get("ixps") or [] if x.get("tipo") == "ixbr" and x.get("code")}
    sem = set(cob.get("ptts_ixbr_sem_instalacao") or [])
    return {**cob, "ptts_ixbr_nomes": dict(sorted(ptts_do_site.items())), "ptts_ixbr_site": len(site), "ptts_ixbr_com_instalacao": len(com & site),
            "ptts_ixbr_sem_instalacao": sorted(sem & site), "ptts_ixbr_sem_mapeamento": sorted(site - com - sem), "ptts_ixbr_fora_do_site": sorted((com | sem) - site)}
def resumo(f: dict) -> dict:
    """Linha de lista/bloco: o essencial de uma instalação, sem as listas de vínculos."""
    c = f.get("cadastro") or {}
    out = {"id": f["id"], "nome": f.get("nome"), "org_nome": f.get("org_nome"), "cidade": f.get("cidade"), "uf": f.get("uf"), "pais": f.get("pais"), "lat": f.get("lat"), "lon": f.get("lon"),
           "escopo": f.get("escopo"), "n_redes": f.get("n_redes"), "redes_declaradas": f.get("redes_declaradas"), "n_ptts": len(f.get("ixps") or []), "ptts_detalhe": _ptts_da_instalacao(f), "n_carriers": len(f.get("carriers") or []),
           "campus_id": f.get("campus_id"), "criado": f.get("criado"), "atualizado": f.get("atualizado"),
           "cadastro": {"classe": c.get("classe"), "ultima_atualizacao": c.get("ultima_atualizacao"), "dias": c.get("dias"), "inferido": True,
                        "registro_atualizado": c.get("registro_atualizado"), "vinculo_atualizado": c.get("vinculo_atualizado")} if c else None}
    return {k: v for k, v in out.items() if v is not None}


def _ordenar(itens: list[dict], ordem: str) -> list[dict]:
    if ordem == "nome":
        return sorted(itens, key=lambda f: ((f.get("nome") or "").lower(), f["id"]))
    if ordem == "ptts":
        return sorted(itens, key=lambda f: (-len(f.get("ixps") or []), (f.get("nome") or "").lower(), f["id"]))
    if ordem == "atualizado":
        return sorted(itens, key=lambda f: ((f.get("cadastro") or {}).get("ultima_atualizacao") or "", f["id"]), reverse=True)
    return sorted(itens, key=lambda f: (-(f.get("n_redes") if f.get("n_redes") is not None else f.get("redes_declaradas") or 0), (f.get("nome") or "").lower(), f["id"]))


def lista(doc: dict, pais: Optional[str], uf: Optional[str], q: Optional[str], ptt: Optional[str], cadastro: Optional[str], com_ptt: bool, com_carrier: bool, ordem: str, limit: int, offset: int,
          ptts_do_site: Optional[dict[str, str]] = None) -> dict:
    """Instalações filtradas. `pais` padrão é BR; `todos` inclui as de PTTs externos de outros países. `ptts_do_site` (`{código: cidade}`) nomeia a cobertura (`cobertura_nomeada`)."""
    if ordem not in ORDENS:
        raise InstalacoesErro(400, f"ordem inválida: {ordem}. Use: {', '.join(ORDENS)}")
    if cadastro and cadastro not in CADASTRO:
        raise InstalacoesErro(400, f"cadastro inválido: {cadastro}. Use: {', '.join(CADASTRO)}")
    pais = (pais or "BR").upper()
    ptt = ptt.lower() if ptt else None
    q_ = (q or "").strip().lower()
    itens = []
    for f in doc["instalacoes"].values():
        if pais != "TODOS" and f.get("pais") != pais:
            continue
        if uf and (f.get("uf") or "").upper() != uf.upper():
            continue
        if q_ and q_ not in f"{f.get('nome') or ''} {f.get('aka') or ''} {f.get('org_nome') or ''} {f.get('cidade') or ''}".lower():
            continue
        if ptt and not any(x.get("code") == ptt for x in f.get("ixps") or []):
            continue
        if cadastro and (f.get("cadastro") or {}).get("classe") != cadastro:
            continue
        if com_ptt and not f.get("ixps"):
            continue
        if com_carrier and not f.get("carriers"):
            continue
        itens.append(f)
    itens = _ordenar(itens, ordem)
    return {**_meta(doc), "escopo": {"pais": pais}, "filtros": {"uf": uf, "q": q, "ptt": ptt, "cadastro": cadastro, "com_ptt": com_ptt, "com_carrier": com_carrier},
            "ordem": ORDENS[ordem], "cobertura": cobertura_nomeada(doc, ptts_do_site), "total": len(itens), "items": [resumo(f) for f in itens[offset:offset + limit]]}


def detalhe(doc: dict, vinc: Optional[dict], fid: int) -> Optional[dict]:
    f = doc["instalacoes"].get(str(fid))
    if f is None:
        return None
    campus = doc["campus"].get(str(f["campus_id"])) if f.get("campus_id") else None
    carriers = [{"id": c, **doc["carriers"].get(str(c), {})} for c in f.get("carriers") or []]
    redes = []
    nomes = (vinc or {}).get("redes") or {}
    for asn, criado, atualizado in (vinc or {}).get("por_instalacao", {}).get(str(fid), []):
        n = nomes.get(str(asn)) or {}
        redes.append({k: v for k, v in {"asn": asn, "nome": n.get("nome"), "is_br": n.get("is_br"), "no_vinculo_desde": criado, "vinculo_atualizado": atualizado}.items() if v is not None})
    redes.sort(key=lambda r: r["asn"])
    corpo = {k: v for k, v in f.items() if k not in ("carriers",)}
    return {**_meta(doc), **corpo, "carriers": carriers, "campus": campus, "redes": redes, "redes_total": len(redes),
            "redes_nota": "Vínculos de redes a instalações do Brasil, como cadastrados no PeeringDB; não indicam tráfego nem contrato." if f.get("escopo") == "brasil"
            else "Instalação fora do Brasil, listada por abrigar um PTT externo cadastrado; os vínculos de redes dela não foram coletados."}


def bloco_ixp(doc: Optional[dict], code: str) -> Optional[dict]:
    """Bloco `facilities` do perfil do PTT: instalações onde o PeeringDB diz que o PTT está. None se o produto não foi publicado ou o PTT não tem instalação cadastrada."""
    if not doc:
        return None
    fs = [f for f in doc["instalacoes"].values() if any(x.get("code") == code for x in f.get("ixps") or [])]
    if not fs:
        return None
    return {**_meta(doc), "ptt": code, "total": len(fs), "items": [resumo(f) for f in _ordenar(fs, "redes")]}


def bloco_asn(doc: Optional[dict], vinc: Optional[dict], asn: int) -> Optional[dict]:
    """Bloco `facilities` do perfil do ASN: instalações do Brasil onde a rede declara estar (`netfac`), com a data do vínculo."""
    if not doc or not vinc:
        return None
    ligacoes = vinc["por_asn"].get(str(asn))
    if not ligacoes:
        return None
    itens = []
    for fid, criado, atualizado in ligacoes:
        f = doc["instalacoes"].get(str(fid))
        if f:
            itens.append({**resumo(f), "no_vinculo_desde": criado, "vinculo_atualizado": atualizado, "ptts": [x.get("code") or f"pdb-ix-{x['ix_id']}" for x in f.get("ixps") or []]})
    itens.sort(key=lambda x: (-(x.get("n_redes") or 0), x["id"]))
    return {**_meta(doc), "asn": asn, "total": len(itens), "items": itens,
            "nota": "Instalações do Brasil em que a rede declara estar no PeeringDB; instalações no exterior não foram coletadas. "
                    "A coluna de PTTs lista os que o PeeringDB associa ao prédio, não o ponto em que a rede se conecta ao PTT."}


def bloco_peering(atrib: Optional[dict], portas: Optional[dict], vinc: Optional[dict], asn: int) -> Optional[dict]:
    """Bloco `peering` do perfil do ASN: atributos autodeclarados no PeeringDB e portas nos PTTs externos. None se a rede não tem registro."""
    if not atrib or str(asn) not in atrib["asns"]:
        return None
    a = atrib["asns"][str(asn)]
    p = ((portas or {}).get("por_asn") or {}).get(str(asn))
    out = {"snapshot_date": atrib["snapshot_date"], "coletado_em": atrib.get("coletado_em"), "fonte": atrib.get("fonte"), "limites": atrib.get("limites"), "asn": asn, **a,
           "instalacoes_br_observadas": len((vinc or {}).get("por_asn", {}).get(str(asn), []))}
    if p is not None:
        out["portas_externas"] = {"fonte": (portas or {}).get("fonte"), "limites": (portas or {}).get("limites"),
                                  "ptts": [{"ixp": c, "portas": len(v), "velocidades_mbps": v, "capacidade_mbps": sum(v)} for c, v in sorted(p.items())]}
    return out


def bloco_portas(portas: Optional[dict], code: str) -> Optional[dict]:
    """Portas (velocidade declarada) de um PTT externo; None se o PTT não é externo cadastrado ou o produto não foi publicado."""
    if not portas or code not in portas["ixps"]:
        return None
    return {"snapshot_date": portas["snapshot_date"], "coletado_em": (portas.get("fonte") or {}).get("coletado_em"), "fonte": portas.get("fonte"), "limites": portas.get("limites"), "ixp": code, **portas["ixps"][code]}


def linhas_facilities(doc: Optional[dict]) -> list[dict]:
    """Uma linha por instalação (coleção `facilities` do `/query`)."""
    if not doc:
        return []
    out = []
    for f in doc["instalacoes"].values():
        c = f.get("cadastro") or {}
        ln = {"id": f["id"], "nome": f.get("nome"), "org_nome": f.get("org_nome"), "cidade": f.get("cidade"), "uf": f.get("uf"), "pais": f.get("pais"), "lat": f.get("lat"), "lon": f.get("lon"),
              "escopo": f.get("escopo"), "n_redes": f.get("n_redes"), "n_redes_br": f.get("n_redes_br"), "redes_declaradas": f.get("redes_declaradas"),
              "ptts": [x.get("code") or f"pdb-ix-{x['ix_id']}" for x in f.get("ixps") or []], "n_carriers": len(f.get("carriers") or []), "campus_id": f.get("campus_id"),
              "criado": f.get("criado"), "atualizado": f.get("atualizado"), "cadastro_classe": c.get("classe"), "cadastro_dias": c.get("dias")}
        out.append({k: v for k, v in ln.items() if v is not None})
    out.sort(key=lambda r: r["id"])
    return out


def linhas_facilidades_rede(doc: Optional[dict], vinc: Optional[dict]) -> list[dict]:
    """Uma linha por vínculo rede × instalação do Brasil (coleção `facilidades_rede`)."""
    if not doc or not vinc:
        return []
    nomes = vinc.get("redes") or {}
    out = []
    for asn, ligs in vinc["por_asn"].items():
        for fid, criado, atualizado in ligs:
            f = doc["instalacoes"].get(str(fid))
            if f:
                out.append({k: v for k, v in {"asn": int(asn), "asn_nome": (nomes.get(asn) or {}).get("nome"), "facility_id": fid, "facility_nome": f.get("nome"), "cidade": f.get("cidade"),
                                              "uf": f.get("uf"), "org_nome": f.get("org_nome"), "no_vinculo_desde": criado, "vinculo_atualizado": atualizado}.items() if v is not None})
    out.sort(key=lambda r: (r["asn"], r["facility_id"]))
    return out


def linhas_redes_peering(atrib: Optional[dict], vinc: Optional[dict], portas: Optional[dict]) -> list[dict]:
    """Uma linha por rede do Brasil com registro no PeeringDB (coleção `redes_peering`): atributos de peering, instalações e portas em PTTs externos."""
    if not atrib:
        return []
    nomes = (vinc or {}).get("redes") or {}
    por_asn = (vinc or {}).get("por_asn") or {}
    pt = (portas or {}).get("por_asn") or {}
    out = []
    for a, r in atrib["asns"].items():
        c = r.get("cadastro") or {}
        v = [x for d in (pt.get(a) or {}).values() for x in d]
        ln = {"asn": int(a), "escopo": r.get("escopo"), "ipv6": r.get("ipv6"), "multicast": r.get("multicast"), "unicast": r.get("unicast"), "nunca_via_route_server": r.get("nunca_via_route_server"),
              "tem_looking_glass": "looking_glass" in r, "tem_route_server": "route_server" in r, "ixps_declarados": r.get("ixps_declarados"), "instalacoes_declaradas": r.get("instalacoes_declaradas"),
              "instalacoes_br": len(por_asn.get(a, [])), "portas_externas": len(v), "capacidade_externa_mbps": sum(v) if v else None,
              "criado": r.get("criado"), "atualizado": r.get("atualizado"), "cadastro_classe": c.get("classe"), "cadastro_dias": c.get("dias")}
        out.append({k: x for k, x in ln.items() if x is not None})
    out.sort(key=lambda r: r["asn"])
    return out


#: situação de uma rede no PTT do IX.br que está no prédio: `sessao_rs` (sessão com o route server vista no looking glass), `membro_sem_sessao_rs` (no cadastro e sem sessão),
#: `so_origina` (prefixo visto no PTT, fora do cadastro e sem sessão: INFERIDO, mesma leitura de `asn_interconexao`), `sem_presenca` (nenhum dos três) e `sem_coleta` (nenhuma família com coleta válida)
SITUACOES = {
    "sessao_rs": "sessão com o route server",
    "membro_sem_sessao_rs": "no cadastro, sem sessão com o route server",
    "so_origina": "só origina prefixos visíveis no PTT",
    "sem_presenca": "sem presença observada",
    "sem_coleta": "PTT sem coleta válida",
}
INFERIDAS = ("so_origina",)
NOTA_REDES_PERFIL = ("Conta, entre as redes que declaram estar nesta instalação no PeeringDB, quantas têm sessão no route server do PTT. A rede pode participar do PTT por outra instalação; "
                     "membro sem sessão pode trocar tráfego por sessão bilateral, que estas fontes não observam; 'só origina' é inferido da presença de prefixos e não prova presença física. "
                     "A coluna de originador cobre só ASNs brasileiros e o resumo, também. Nenhum rótulo diz que uma rede deveria estar no PTT.")


def situacao_no_ptt(asn: int, p: dict) -> str:
    """Situação de `asn` no PTT `p` (`{direto, membros, origem, coleta}`, com `coleta` por família): só famílias com coleta válida contam como medida."""
    if not any(c == "ok" for c in p["coleta"].values()):
        return "sem_coleta"
    if asn in p["direto"]:
        return "sessao_rs"
    if asn in p["membros"]:
        return "membro_sem_sessao_rs"
    if asn in p["origem"]:
        return "so_origina"
    return "sem_presenca"


def redes_perfil(det: dict, ptts: dict[str, dict], externos: list[dict], info: Callable[[int], dict]) -> dict:
    """Acrescenta ao detalhe da instalação o bloco `redes_perfil`: a situação de cada rede (do Brasil) em cada PTT do IX.br do prédio, com usuários APNIC e IPv6, e o resumo por PTT.
    `ptts` é `{código: {nome, direto, membros, origem, coleta}}` dos PTTs do IX.br com documento no snapshot; `externos` são os demais (sem dado de sessão); `info(asn)` devolve
    `{usuarios, ipv6}` do índice de ASNs. Só as redes do Brasil entram na contagem (a lista de originadores publicada é a dos brasileiros)."""
    redes = []
    for r in det.get("redes") or []:
        ln = {**r}
        if r.get("is_br"):
            i = info(r["asn"])
            ln["usuarios_apnic"] = i.get("usuarios")
            ln["ipv6"] = i.get("ipv6")
            ln["situacao"] = {c: situacao_no_ptt(r["asn"], p) for c, p in ptts.items()}
        redes.append(ln)
    resumo = []
    for c, p in ptts.items():
        cont = {k: 0 for k in SITUACOES}
        for ln in redes:
            if "situacao" in ln:
                cont[ln["situacao"][c]] += 1
        resumo.append({"ixp": c, "nome": p["nome"], "coleta": p["coleta"], "redes_do_brasil": sum(cont.values()), **cont})
    return {**det, "redes": redes, "redes_perfil": {"resumo": resumo, "ptts_sem_dado_de_sessao": externos, "situacoes": SITUACOES, "inferidas": list(INFERIDAS), "nota": NOTA_REDES_PERFIL}}
