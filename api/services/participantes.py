# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tabela única de participantes de um PTT do IX.br (PT-24 / IXP-E5.5): uma linha por ASN, com as colunas que a página espalhava em quatro blocos.

Só junta dado que o snapshot já publica, sem coleta nova: o cadastro de participantes (`membro`), o `asn_direct` do looking glass por família (`direto`), os ASNs com
prefixo visto no PTT (`originador`, só dos brasileiros: é o que o documento do PTT guarda), as sessões e os contadores de rotas dos route servers (Alice-LG, nível 1),
o detalhe das rotas rejeitadas (nível 2) e os CDNs da lista curada. Funções puras: quem monta as entradas é a rota.

Leituras que a tela não pode confundir (política editorial: dado e comparação, sem causa nem veredito):
  * `membro` (cadastro do IX.br) é diferente de `sessao_rs` (sessão BGP com o route server): o cadastrado sem sessão pode trocar tráfego por sessão bilateral;
  * `direto` vem do looking glass e `sessao_rs` do Alice-LG; as duas fontes se contam à parte e podem divergir;
  * família sem coleta válida (`coleta` diferente de `ok`) vem como `None` na linha e fica fora dos filtros: nunca vira "não tem";
  * a rejeição é `filtradas ÷ recebidas` nas sessões up, os dois contadores do mesmo instante (route server); o detalhe por motivo é de outra coleta e traz a própria idade.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Callable, Optional

FILTROS = {
    "todos": "todos os participantes",
    "sem-v6": "sem sessão direta IPv6 no looking glass (só famílias com coleta válida)",
    "sem-v4": "sem sessão direta IPv4 no looking glass (só famílias com coleta válida)",
    "sem-direto": "sem sessão direta em nenhuma das famílias com coleta válida",
    "membro-sem-sessao-rs": "no cadastro do IX.br e sem sessão com o route server (pode haver peering bilateral)",
    "sessao-sem-cadastro": "com sessão no route server e fora do cadastro de participantes",
    "com-cdn": "ASN de CDN da lista curada",
    "com-rejeicao": "com ao menos uma rota filtrada pelo route server nas sessões up",
}
ORDENS = {
    "asn": "ASN, crescente (ordem neutra)",
    "nome": "nome, A–Z",
    "uf": "UF da sede, A–Z",
    "sessoes_rs": "número de sessões com o route server",
    "rejeicao": "rotas filtradas ÷ recebidas nas sessões up",
    "assinantes": "acessos de banda larga fixa declarados ao SICI (Anatel) pelo CNPJ do ASN",
    "usuarios_apnic": "usuários estimados pela APNIC para o ASN inteiro (só ASN brasileiro)",
    "usuarios_ptt": "estimativa de usuários do ASN via os prefixos IPv4 vistos no PTT",
}
LIMITES = ("Cada linha é um ASN visto no cadastro do IX.br, no looking glass ou nos route servers do PTT. 'Direto' é a sessão com o route server vista no looking glass; 'membro' é o cadastro do IX.br; "
           "as duas coisas são diferentes, e membro sem sessão pode trocar tráfego por sessão bilateral, que estas fontes não observam. Família sem coleta válida aparece como 'sem coleta', nunca como ausência. "
           "'Originador' vale só para ASN brasileiro (a lista publicada). A rejeição é o contador de rotas filtradas dividido pelo de rotas recebidas nas sessões up do route server, do mesmo instante; "
           "o número de rotas por motivo vem de outra coleta, com a idade dela. 'Assinantes' são os acessos de banda larga fixa que o CNPJ do ASN declarou ao SICI da Anatel no mês de referência "
           "(data diferente da do snapshot); vale só para ASN com CNPJ vinculado e, quando o CNPJ tem mais de um ASN, o mesmo total aparece em cada um (não some). Não é ranking nem diz quem tem razão. "
           "'Empresa' é o nome comercial do CNPJ vinculado ao ASN (Anatel); sem nome nas fontes, a coluna fica em branco e o CNPJ não é usado como nome. 'Política de peering' é o que a própria rede declarou no PeeringDB, sem verificação.")
LIMITES_USUARIOS = ("Usuários APNIC (total do AS): a APNIC estima usuários por AS por amostragem de anúncios, não por prefixo; só ASN brasileiro (os demais ficam em branco). "
                    "Dos quais via prefixos vistos no PTT (estimado): usuários APNIC do AS multiplicados pela parte do espaço IPv4 anunciado pelo AS que aparece neste PTT (prefixos até /24, sem contar blocos aninhados duas vezes). "
                    "A conta supõe usuários distribuídos de modo uniforme pelo espaço IPv4 do AS; não vale bem com CGNAT, blocos de servidor nem para IPv6. É só IPv4, só ASN brasileiro e só prefixos até /24. "
                    "'Visto no PTT' inclui prefixos anunciados por terceiros, então pode haver valor para um ASN sem sessão. Somar o valor entre PTTs conta o mesmo usuário mais de uma vez. "
                    "A soma da coluna, mais a de ASNs que anunciam prefixos no PTT sem constar como participantes, é a estimativa de usuários do PTT; os valores exibidos são arredondados.")


class ParticipantesErro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status, self.mensagem = status, mensagem


def _dias(ref: Optional[str], iso: Optional[str]) -> Optional[int]:
    """Dias inteiros entre a data do snapshot e um instante ISO; None se algum não lê."""
    if not ref or not iso:
        return None
    try:
        a = date.fromisoformat(ref[:10])
        b = datetime.fromisoformat(str(iso).replace("Z", "+00:00")).date()
    except ValueError:
        return None
    return max(0, (a - b).days)


def _familia(doc: dict, afi: str) -> dict:
    v = doc.get(afi)
    v = v if isinstance(v, dict) else {}
    ok = v.get("coleta") == "ok"
    return {"coleta": v.get("coleta") or "missing", "ok": ok, "direto": set(v.get("asn_direct") or []) if ok else set(), "origem": set(v.get("br_asns_origin") or []) if ok else set()}


def _rejeicao(lista: list[dict]) -> Optional[dict]:
    up = [s for s in lista if s.get("estado") == "up" and s.get("recebidas") is not None and s.get("filtradas") is not None]
    if not up:
        return None
    rec, fil = sum(s["recebidas"] for s in up), sum(s["filtradas"] for s in up)
    return {"filtradas": fil, "recebidas": rec, "pct": round(100 * fil / rec, 2) if rec else None, "sessoes_up": len(up)}


def montar(date_str: str, code: str, ixp: dict, membros: set[int], rs_ixp: Optional[dict], rs_asns: Optional[dict], pol_asns: Optional[dict], cdns: Optional[dict],
           nomes_de: Callable[[list[int]], dict], br_de: Callable[[int], Optional[bool]], sici_de: Optional[Callable[[int], Optional[dict]]] = None,
           empresa_de: Optional[Callable[[int], Optional[dict]]] = None, usuarios_de: Optional[Callable[[int], Optional[dict]]] = None,
           prefixos: Optional[dict[str, dict]] = None, pdb_de: Optional[Callable[[int], Optional[dict]]] = None,
           alcancado: Optional[dict[str, dict]] = None) -> dict:
    """Todas as linhas do PTT (sem filtro nem página) e os metadados. `nomes_de(asns)` devolve `{str(asn): {name, uf}}`; `br_de(asn)` diz se o ASN é brasileiro (LACNIC);
    `sici_de(asn)` devolve `{acessos, compartilhado}` do CNPJ do ASN no SICI, ou None quando não há vínculo ASN→CNPJ ou o CNPJ não declarou.
    `empresa_de(asn)` devolve `{cnpj, nome}` (nome None sem nome nas fontes); `usuarios_de(asn)` devolve `{apnic, ptt}` (cada um None quando não se aplica);
    `prefixos` é `{afi: {str(asn): estatísticas de prefixos do peer}}` (de `/ixps/{code}/peers`); `pdb_de(asn)` devolve `{portas_mbps, instalacoes}` do PeeringDB;
    `alcancado` é `{afi: {str(asn): assinantes SICI alcançados pelo peer}}`."""
    fam = {"v6": _familia(ixp, "v6"), "v4": _familia(ixp, "v4")}
    rs_membros = {m["asn"]: m for m in ((rs_ixp or {}).get("membros") or [])}
    rs_medido = bool(rs_ixp) and ((rs_ixp.get("resumo") or {}).get("rs_consultados") or 0) > 0
    por_asn_cdn: dict[int, list[str]] = {}
    for c in (cdns or {}).get("cdns") or []:
        if code in (c.get("ixbr") or []):
            for a in c.get("asns") or []:
                if a in membros:
                    por_asn_cdn.setdefault(a, []).append(c["name"])
    todos = set(membros) | fam["v6"]["direto"] | fam["v4"]["direto"] | {a for a, m in rs_membros.items() if m.get("sessoes")}
    nomes = nomes_de(sorted(todos))
    linhas = []
    for asn in sorted(todos):
        m = rs_membros.get(asn) or {}
        n = nomes.get(str(asn)) or {}
        nome = (m.get("nome") or "").strip() or n.get("name") or None            # o cadastro do route server vem às vezes com nome vazio (fec): cai para o nome do ASN
        br = br_de(asn)
        sessoes = ({"sessoes": m["sessoes"], "up": m["up"], "down": m["down"], "incertas": m.get("rs_incerto", 0)} if m.get("sessoes") else
                   ({"sessoes": 0, "up": 0, "down": 0, "incertas": 0} if rs_medido and asn in membros else None))
        lista = (((rs_asns or {}).get("asns") or {}).get(str(asn)) or {}).get("ixps", {}).get(code, {}).get("lista") or []
        det = ((((pol_asns or {}).get("asns") or {}).get(str(asn)) or {}).get("ixps", {}).get(code) or {}).get("rejeicoes")
        detalhe = ({"rotas": det["rotas"], "coletado_ate": det.get("coletado_ate"), "idade_dias": _dias(date_str, det.get("coletado_ate")), "herdado": bool(det.get("herdado")),
                    "contagem": det.get("contagem")} if det else None)
        linhas.append({
            "asn": asn, "nome": nome, "uf": n.get("uf"), "is_br": br,
            "membro": asn in membros,
            "direto": {a: (asn in f["direto"] if f["ok"] else None) for a, f in fam.items()},
            "originador": {a: ((asn in f["origem"]) if (f["ok"] and br) else None) for a, f in fam.items()},
            "sessao_rs": sessoes,
            "cadastrado_sem_sessao_rs": bool(m.get("cadastrado_sem_sessao")),
            "sessao_rs_sem_cadastro": bool(m.get("sessoes")) and asn not in membros,
            "rejeicao": _rejeicao(lista),
            "rejeicao_detalhe": detalhe,
            "cdns": sorted(por_asn_cdn.get(asn, [])),
            "sici": sici_de(asn) if sici_de else None,
            "empresa": empresa_de(asn) if empresa_de else None,
            "usuarios_apnic": (usuarios_de(asn) or {}).get("apnic") if usuarios_de else None,
            "usuarios_ptt": (usuarios_de(asn) or {}).get("ptt") if usuarios_de else None,
            "prefixos": {a: ((prefixos or {}).get(a) or {}).get(str(asn)) for a in ("v6", "v4")},
            "peeringdb": pdb_de(asn) if pdb_de else None,
            "sici_alcancado": {a: ((alcancado or {}).get(a) or {}).get(str(asn)) for a in ("v6", "v4")},
        })
    return {"linhas": linhas, "familias": {a: f["coleta"] for a, f in fam.items()}, "route_servers_medido": rs_medido}


def _sem(l: dict, a: str) -> bool:
    return l["direto"][a] is False


def _passa(l: dict, filtro: str, fam_ok: dict[str, bool]) -> bool:
    if filtro == "todos":
        return True
    if filtro == "sem-v6":
        return _sem(l, "v6")
    if filtro == "sem-v4":
        return _sem(l, "v4")
    if filtro == "sem-direto":
        medidas = [a for a in ("v6", "v4") if fam_ok[a]]
        return bool(medidas) and all(l["direto"][a] is False for a in medidas)
    if filtro == "membro-sem-sessao-rs":
        return l["cadastrado_sem_sessao_rs"]
    if filtro == "sessao-sem-cadastro":
        return l["sessao_rs_sem_cadastro"]
    if filtro == "com-cdn":
        return bool(l["cdns"])
    if filtro == "com-rejeicao":
        return bool(l["rejeicao"] and l["rejeicao"]["filtradas"])
    return True


def contagens(linhas: list[dict], familias: dict[str, str]) -> dict[str, int]:
    fam_ok = {a: c == "ok" for a, c in familias.items()}
    return {f: sum(1 for l in linhas if _passa(l, f, fam_ok)) for f in FILTROS}


def _chave(ordem: str):
    if ordem == "nome":
        return lambda l: ((l["nome"] or "").lower() or "￿", l["asn"])
    if ordem == "uf":
        return lambda l: (l["uf"] or "￿", l["asn"])
    if ordem == "sessoes_rs":
        return lambda l: (l["sessao_rs"]["sessoes"] if l["sessao_rs"] else -1, l["asn"])
    if ordem == "rejeicao":
        return lambda l: ((l["rejeicao"] or {}).get("pct") if (l["rejeicao"] or {}).get("pct") is not None else -1, l["asn"])
    if ordem == "assinantes":
        return lambda l: ((l["sici"] or {}).get("acessos", -1), l["asn"])
    if ordem in ("usuarios_apnic", "usuarios_ptt"):
        return lambda l: (l[ordem] if l[ordem] is not None else -1, l["asn"])
    return lambda l: l["asn"]


def pagina(base: dict, q: Optional[str], filtro: str, uf: Optional[str], ordem: str, desc: bool, limit: int, offset: int) -> dict:
    """Filtra, ordena e corta as linhas de `montar`. Os contadores dos filtros valem para o PTT inteiro (não mudam com `q` nem `uf`)."""
    if filtro not in FILTROS:
        raise ParticipantesErro(400, f"filtro inválido: {filtro}. Use: {', '.join(FILTROS)}")
    if ordem not in ORDENS:
        raise ParticipantesErro(400, f"ordem inválida: {ordem}. Use: {', '.join(ORDENS)}")
    linhas, fams = base["linhas"], base["familias"]
    fam_ok = {a: c == "ok" for a, c in fams.items()}
    nq = (q or "").strip().lower()
    num = nq[2:] if nq.startswith("as") and nq[2:].isdigit() else nq          # "AS64500" acha pelo número
    sel = []
    for l in linhas:
        if uf and (l["uf"] or "").upper() != uf.upper():
            continue
        if nq and not (num in str(l["asn"]) or nq in (l["nome"] or "").lower()):
            continue
        if _passa(l, filtro, fam_ok):
            sel.append(l)
    sel.sort(key=_chave(ordem), reverse=desc)
    return {"total": len(sel), "items": sel[offset:offset + limit], "contagens": contagens(linhas, fams), "total_participantes": len(linhas),
            "ufs": sorted({l["uf"] for l in linhas if l["uf"]})}
