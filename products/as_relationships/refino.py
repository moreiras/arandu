# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""ARC v2: refinamento probabilístico no estilo do ProbLink (Jin et al., NSDI 2019).

A v1 (arc.py/decisao.py) soma pesos de evidência por elo. A v2 usa o veredito da v1 como *bootstrap* de um Naive Bayes sobre
características discretas do elo e o itera: os elos com posterior alto viram âncora da propagação *valley-free* seguinte, que
recalcula a característica de "tripla" (o que os vizinhos do elo, nos caminhos, implicam sobre ele) sem usar o rótulo do próprio elo.

Classes por elo {a, b} (a < b): `ab` (a provedor de b), `ba` e `pp` (par). Irmãos não competem no NB: saem da organização (restricoes.py).
Características (todas orientadas: vistas do candidato a provedor; o treino inclui o espelho para a simetria): tripla, distância ao
clique, razão de grau de trânsito, nº de VPs, PTTs em comum, apoio da rampa dos route servers, estado do ASPA, rótulo do CAIDA (o
"modelo de erro" é aprendido: P(rótulo do CAIDA | classe)), perfil de política no IX.br e restrição declarada ("não exporto para").
O NB supõe independência e as características são correlacionadas, então a posterior bruta é pouco confiável; a **temperatura**
(config, medida pela régua sem ASPA) a recalibra, e o `ece` de validação cruzada decide se `p` sai marcada como calibrada.

Os elos cuja posterior fica abaixo de `abstencao` não são classificados."""
from __future__ import annotations

import math
from collections import Counter, defaultdict, deque
from typing import Callable, Iterable, Optional

from products.as_relationships.config import Config
from products.as_relationships import irr_relacao
from products.as_relationships.decisao import Veredito
from products.as_relationships.evidencias import Evidencias, Par

CLASSES = ("ab", "ba", "pp")
CARACTERISTICAS = ("tripla", "dist_clique", "grau", "vps", "coloc", "rs", "aspa", "caida", "politica", "restricao", "irr")
NIVEL_FIRME = ("declarado", "confirmado", "provavel")
ORDEM_NIVEL = {"declarado": 4, "confirmado": 3, "provavel": 2, "possivel": 1, "sem_classificacao": 0}


# ── propagação com voto em todos os elos ─────────────────────────────────────────────────────────────────────────
def votar_todos(caminho: tuple[int, ...], vp0: bool, rotulo: Callable[[int, int], Optional[str]]) -> Optional[list[Par]]:
    """Votos `(provedor, cliente)` de **todos** os elos do caminho, cada um pelo que os *outros* elos rotulados implicam (padrão U* P? D*).
    Diferente de `propagacao.votar_caminho`, o elo que já tem rótulo também vota: o voto independe do próprio rótulo, e é isso que
    faz da "tripla" uma característica (não uma cópia do veredito). None se os rótulos violam *valley-free*."""
    n = len(caminho) - 1
    r = [rotulo(caminho[i], caminho[i + 1]) for i in range(n)]
    desceu = False
    for x in r:
        if x == "U":
            if desceu:
                return None
        elif x == "P":
            if desceu:
                return None
            desceu = True
        elif x == "D":
            desceu = True
    if not any(r):
        return []
    tem_desc, vistos = [False] * n, False                   # existe 'D' ou 'P' antes do elo i
    for i in range(n):
        tem_desc[i] = vistos
        if r[i] in ("D", "P"):
            vistos = True
    tem_sub, vistos = [False] * n, False                    # existe 'U' ou 'P' depois do elo i
    for i in range(n - 1, -1, -1):
        tem_sub[i] = vistos
        if r[i] in ("U", "P"):
            vistos = True
    out: list[Par] = []
    for i in range(n):
        if i == 0 and vp0:
            continue
        if tem_sub[i] and not tem_desc[i]:
            out.append((caminho[i + 1], caminho[i]))
        elif tem_desc[i] and not tem_sub[i]:
            out.append((caminho[i], caminho[i + 1]))
    return out


def contar_votos(caminhos: Iterable[tuple[tuple[int, ...], int, bool]], rotulo: Callable[[int, int], Optional[str]]) -> dict[Par, list[int]]:
    votos: dict[Par, list[int]] = {}
    for caminho, n_vps, vp0 in caminhos:
        r = votar_todos(caminho, vp0, rotulo)
        for par in r or ():
            v = votos.get(par)
            if v is None:
                votos[par] = [1, n_vps]
            else:
                v[0] += 1
                if n_vps > v[1]:
                    v[1] = n_vps
    return votos


# ── características ──────────────────────────────────────────────────────────────────────────────────────────────
def distancias_ao_clique(adj: dict[int, set[int]], clique: Iterable[int]) -> dict[int, int]:
    dist = {c: 0 for c in clique}
    fila = deque(dist)
    while fila:
        x = fila.popleft()
        for y in adj.get(x, ()):
            if y not in dist:
                dist[y] = dist[x] + 1
                fila.append(y)
    return dist


def _bucket_vps(n: int) -> str:
    return "0" if n <= 0 else "1" if n == 1 else "2" if n == 2 else "3-5" if n <= 5 else "6+"


def _ln1(x: int) -> float:
    return math.log2(x + 1)


class Contexto:
    """Tudo que as características precisam, pré-calculado uma vez por família de endereço."""

    def __init__(self, ev: Evidencias, adj: dict[int, set[int]], grau: dict[int, int], politica: Optional[dict[int, str]] = None,
                 restricoes: Optional[dict[tuple[int, int], str]] = None, irr: Optional[dict[tuple[int, int], dict]] = None) -> None:
        self.ev = ev
        self.grau = grau
        self.dist = distancias_ao_clique(adj, ev.clique) if ev.clique else {}
        self.politica = politica or {}
        self.restricoes = restricoes or {}              # (quem restringe, alvo) → "nao" | "so"
        self.irr = irr                                  # `irr_relacao.relacoes` ou None: sem ele a característica é sempre "0", neutra no NB

    def caracteristicas(self, a: int, b: int, votos: dict[Par, list[int]], usar_aspa: bool = True) -> dict[str, str]:
        """Características do elo vistas de `a` como candidato a provedor de `b`."""
        ev = self.ev
        v_ab, v_ba = votos.get((a, b), (0,))[0], votos.get((b, a), (0,))[0]
        tot = v_ab + v_ba
        if tot == 0:
            tripla = "0"
        else:
            f = v_ab / tot
            forte = tot >= 8
            tripla = ("ab+" if forte else "ab") if f >= 0.9 else ("ba+" if forte else "ba") if f <= 0.1 else "misto"
        da, db = min(self.dist.get(a, 9), 4), min(self.dist.get(b, 9), 4)
        dist = "?" if not self.dist else f"{'<' if da < db else '=' if da == db else '>'}{min(da, db)}"
        grau = str(max(-4, min(4, round(_ln1(self.grau.get(a, 0)) - _ln1(self.grau.get(b, 0))))))
        k = (min(a, b), max(a, b))
        vps = _bucket_vps(ev.n_vps_elo.get(k, 0))
        coloc = str(min(2, len(ev.ptts_do_asn.get(a, set()) & ev.ptts_do_asn.get(b, set()))))
        m_ab, m_ba = len(ev.rs_membros.get((a, b), ())), len(ev.rs_membros.get((b, a), ()))
        rs = "0" if not (m_ab or m_ba) else "ambos" if (m_ab and m_ba) else ("ab+" if ev.rs_forte((a, b)) else "ab") if m_ab else ("ba+" if ev.rs_forte((b, a)) else "ba")
        if not usar_aspa:
            aspa = "0"
        elif (a, b) in ev.aspa_pos or (b, a) in ev.aspa_pos:
            aspa = "ab" if (a, b) in ev.aspa_pos and (b, a) not in ev.aspa_pos else "ba" if (b, a) in ev.aspa_pos and (a, b) not in ev.aspa_pos else "ambos"
        else:
            n1, n2 = ev.aspa_nega((a, b)), ev.aspa_nega((b, a))
            aspa = "neg_ambos" if (n1 and n2) else "neg_ab" if n1 else "neg_ba" if n2 else "0"
        caida = "ab" if (a, b) in ev.caida_p2c else "ba" if (b, a) in ev.caida_p2c else "pp" if k in ev.caida_p2p else "0"
        politica = f"{self.politica.get(a, '-')}/{self.politica.get(b, '-')}"
        ra, rb = self.restricoes.get((a, b)), self.restricoes.get((b, a))
        restricao = "0" if not (ra or rb) else f"{ra or '-'}/{rb or '-'}"
        return {"tripla": tripla, "dist_clique": dist, "grau": grau, "vps": vps, "coloc": coloc, "rs": rs, "aspa": aspa,
                "caida": caida, "politica": politica, "restricao": restricao, "irr": irr_relacao.valor(self.irr, a, b) if self.irr else "0"}


# ── Naive Bayes ──────────────────────────────────────────────────────────────────────────────────────────────────
class NaiveBayes:
    def __init__(self, suavizacao: float = 1.0, sem: Iterable[str] = ()) -> None:
        self.s = suavizacao
        self.sem = set(sem)
        self.n = {c: 0.0 for c in CLASSES}
        self.cont: dict[str, dict[str, dict[str, float]]] = {f: {c: defaultdict(float) for c in CLASSES} for f in CARACTERISTICAS}
        self.vocab: dict[str, set[str]] = {f: set() for f in CARACTERISTICAS}

    def treinar(self, amostras: Iterable[tuple[dict[str, str], dict[str, str], str]]) -> None:
        """`(características de a→b, características de b→a, classe)`: cada amostra entra com o espelho (b→a, classe invertida)."""
        for am in amostras:
            fa, fb, c = am[:3]
            w = am[3] if len(am) > 3 else 1.0                      # peso: o rótulo fraco da v1 conta menos que o firme
            for f, cl in ((fa, c), (fb, {"ab": "ba", "ba": "ab", "pp": "pp"}[c])):
                self.n[cl] += w
                for nome in CARACTERISTICAS:
                    if nome in self.sem:
                        continue
                    self.cont[nome][cl][f[nome]] += w
                    self.vocab[nome].add(f[nome])

    def escores(self, f: dict[str, str]) -> dict[str, float]:
        """log P(classe) + Σ log P(característica | classe), com Laplace."""
        total = sum(self.n.values()) or 1.0
        out = {}
        for c in CLASSES:
            s = math.log((self.n[c] + self.s) / (total + self.s * len(CLASSES)))
            for nome in CARACTERISTICAS:
                if nome in self.sem:
                    continue
                v = len(self.vocab[nome] | {f[nome]})
                s += math.log((self.cont[nome][c].get(f[nome], 0.0) + self.s) / (self.n[c] + self.s * v))
            out[c] = s
        return out


def posterior(escores: dict[str, float], temperatura: float = 1.0) -> dict[str, float]:
    t = max(temperatura, 1e-6)
    mx = max(escores.values())
    e = {c: math.exp((s - mx) / t) for c, s in escores.items()}
    z = sum(e.values())
    return {c: x / z for c, x in e.items()}


# ── rotinas de rótulo ────────────────────────────────────────────────────────────────────────────────────────────
def classe_do_veredito(v: Veredito) -> Optional[str]:
    lo = min(v.a, v.b)
    if v.tipo == "p2c":
        return "ab" if v.a == lo else "ba"
    if v.tipo == "p2p":
        return "pp"
    return None


def classe_estrato(f: dict) -> str:
    """Estrato de evidência independente de um elo, nas características vistas do provedor inferido: CAIDA concorda (`caida=ab`) e/ou
    tripla confirmada (`tripla=ab+`); se um confirma e o outro contradiz (CAIDA `ba`/`pp` contra `ab+`; tripla `ba`/`ba+` contra `caida=ab`), `conflito`."""
    caida, tripla = f.get("caida"), f.get("tripla") or ""
    c_ok, t_ok = caida == "ab", tripla == "ab+"
    if (c_ok and tripla.startswith("ba")) or (t_ok and caida in ("ba", "pp")):
        return "conflito"
    if c_ok and t_ok:
        return "ambos"
    return "so_caida" if c_ok else "so_tripla" if t_ok else "sem_evidencia"


def _ancoras(classes: dict[tuple[int, int], str]) -> dict[Par, str]:
    """Âncoras de propagação `(x, y) → U|D|P` lidas da esquerda para a direita."""
    extra: dict[Par, str] = {}
    for (lo, hi), c in classes.items():
        if c == "ab":                                   # lo é provedor de hi: lo→hi desce, hi→lo sobe
            extra[(lo, hi)], extra[(hi, lo)] = "D", "U"
        elif c == "ba":
            extra[(hi, lo)], extra[(lo, hi)] = "D", "U"
        else:
            extra[(lo, hi)] = extra[(hi, lo)] = "P"
    return extra


def temperatura_da_afi(cfg: Config, afi: str) -> float:
    return dict(cfg.refino.temperatura).get(afi, 1.0)


def refinar(vereditos: list[Veredito], contexto: dict, cfg: Config, afi: str, politica: Optional[dict[int, str]] = None,
            restricoes: Optional[dict[tuple[int, int], str]] = None, usar_aspa: bool = True, log=None, irr: Optional[dict[tuple[int, int], dict]] = None) -> tuple[list[Veredito], dict]:
    """Devolve `(vereditos refinados, diagnóstico)`. `contexto` é o dict preenchido por `arc.inferir(..., contexto=...)`.
    O diagnóstico traz `escores` ({(lo, hi): {classe: log-escore}} da última iteração) para a calibração da régua."""
    rf = cfg.refino
    ev: Evidencias = contexto["ev"]
    limpos = contexto.get("limpos")
    ctx = Contexto(ev, contexto["adj"], contexto["grau_transito"], politica, restricoes, irr if rf.irr else None)
    votos_v1: dict[Par, list[int]] = contexto["votos"]
    elos = sorted({(min(v.a, v.b), max(v.a, v.b)) for v in vereditos})
    por_elo = {(min(v.a, v.b), max(v.a, v.b)): v for v in vereditos}

    base = {k: classe_do_veredito(v) for k, v in por_elo.items()}
    treino = {k: c for k, c in base.items() if c and por_elo[k].nivel in NIVEL_FIRME and por_elo[k].p >= rf.p_treino}
    ancoras_iniciais = {k: c for k, c in treino.items() if por_elo[k].p >= rf.p_ancora}
    # rótulos fracos da v1 (nível possível): sem eles o NB só vê "par" com evidência forte (raro) e passa a chamar de p2c todo elo sem sinal
    fracos = {k: c for k, c in base.items() if c and k not in treino and por_elo[k].nivel == "possivel"}
    votos = votos_v1
    classes_atuais = dict(ancoras_iniciais)
    escores: dict[tuple[int, int], dict[str, float]] = {}
    hist = []
    nb: Optional[NaiveBayes] = None
    carac: dict[tuple[int, int], dict[str, str]] = {}
    carac_esp: dict[tuple[int, int], dict[str, str]] = {}
    for it in range(max(1, rf.iteracoes)):
        if limpos is not None:
            extra = _ancoras(classes_atuais)
            rot = lambda x, y: ev.rotulo_ancora(x, y, extra)                     # noqa: E731
            votos = contar_votos(limpos(), rot)
        carac = {(a, b): ctx.caracteristicas(a, b, votos, usar_aspa) for a, b in elos}
        carac_esp = {(a, b): ctx.caracteristicas(b, a, votos, usar_aspa) for a, b in elos}
        nb = NaiveBayes(rf.suavizacao)
        nb.treinar([(carac[k], carac_esp[k], c, 1.0) for k, c in treino.items()] + [(carac[k], carac_esp[k], c, rf.peso_fraco) for k, c in fracos.items()])
        escores = {k: nb.escores(carac[k]) for k in elos}
        post = {k: posterior(s, temperatura_da_afi(cfg, afi)) for k, s in escores.items()}
        novos = {}
        for k, p in post.items():
            c = max(CLASSES, key=lambda x: p[x])
            if p[c] >= rf.p_ancora:
                novos[k] = c
        # a verdade do bootstrap (ASPA, confirmados) não é desfeita pelo NB: só se acrescentam âncoras
        mudou = sum(1 for k in set(novos) | set(classes_atuais) if novos.get(k) != classes_atuais.get(k))
        hist.append({"iteracao": it + 1, "ancoras": len(novos), "mudaram": mudou, "treino": len(treino), "fracos": len(fracos), "votos": len(votos)})
        if log is not None:
            log.info("refino iteration", afi=afi, **hist[-1])
        classes_atuais = {**novos, **{k: c for k, c in ancoras_iniciais.items() if k not in novos}}
        if mudou == 0 and it > 0:
            break

    t = temperatura_da_afi(cfg, afi)
    saida: list[Veredito] = []
    for v in vereditos:
        k = (min(v.a, v.b), max(v.a, v.b))
        p = posterior(escores[k], t)
        c = max(CLASSES, key=lambda x: p[x])
        saida.append(_veredito(v, k, c, p, ev, votos_v1, cfg, carac[k], base[k], carac_esp[k], afi))
    diag = {"iteracoes": hist, "treino": len(treino), "elos": len(elos), "temperatura": t,
            "abstencoes": sum(1 for v in saida if v.evid.get("refino", {}).get("abstencao")),
            "rebaixados_por_estrato": dict(Counter(v.evid["refino"]["rebaixado_por_estrato"] for v in saida if v.evid.get("refino", {}).get("rebaixado_por_estrato"))),
            "escores": escores, "caracteristicas": carac, "caracteristicas_espelho": carac_esp, "treinados": treino, "fracos": fracos, "nb": nb, "votos": votos}
    return saida, diag


def fontes_independentes(c: str, a: int, b: int, ev: Evidencias, votos: dict[Par, list[int]]) -> set[str]:
    """Fontes independentes (aspa, rs, colecao, clique) que sustentam a classe `c` do elo (a < b)."""
    f: set[str] = set()
    pares = {"ab": [(a, b)], "ba": [(b, a)], "pp": []}[c]
    for par in pares:
        if par in ev.aspa_pos:
            f.add("aspa")
        if ev.rs_membros.get(par):
            f.add("rs")
        if votos.get(par):
            f.add("colecao")
    if c == "pp" and ev.no_clique(a, b):
        f.add("clique")
    if c in ("ab", "ba") and (a in ev.clique) != (b in ev.clique) and ((a in ev.clique) == (c == "ab")):
        f.add("clique")
    return f


def _veredito(v: Veredito, k: tuple[int, int], c: str, p: dict[str, float], ev: Evidencias, votos_v1: dict, cfg: Config,
              carac: dict[str, str], classe_v1: Optional[str], carac_esp: Optional[dict[str, str]] = None, afi: str = "") -> Veredito:
    a, b = k
    pc = p[c]
    fontes = fontes_independentes(c, a, b, ev, votos_v1)
    refino = {"p_v1": v.p, "tipo_v1": v.tipo, "tripla": carac["tripla"]}
    abst = pc < cfg.refino.abstencao
    declarado = c in ("ab", "ba") and "aspa" in fontes
    nivel = "sem_classificacao"
    if declarado:
        nivel = "declarado"
    elif not abst:
        for nome, p_min, n_min in cfg.niveis:
            if pc >= p_min and len(fontes) >= n_min:
                nivel = nome
                break
    # medido na régua: o NB sozinho PROMOVE elos com precisão pior que a da v1; por isso o nível da v2 nunca passa do nível da v1
    # (o refino pode abster e rebaixar, não promover). `cap_v1` desliga o limite quando a régua mostrar ganho.
    if cfg.refino.cap_v1 and ORDEM_NIVEL[nivel] > ORDEM_NIVEL[v.nivel] and nivel != "declarado":
        refino["limitado_pela_v1"] = nivel
        nivel = v.nivel
    if abst and not declarado:
        refino["abstencao"] = True
        nivel = "sem_classificacao"
    if not (set(v.evid) - {"fontes", "refino", "contra"}) and nivel != "declarado":         # sem nenhuma evidência além das características
        nivel = "sem_classificacao"
    tipo = "sem_classificacao" if nivel == "sem_classificacao" else ("p2p" if c == "pp" else "p2c")
    prov, cli = (a, b) if c == "ab" else (b, a)
    estrato = None
    es = cfg.refino.estratos
    if tipo == "p2c" and carac_esp is not None:                       # estrato visto do provedor inferido (a = menor ASN: `carac`; b: o espelho)
        vista = carac if c == "ab" else carac_esp
        estrato = {"classe": classe_estrato(vista)}
        if es.ativo and nivel == "provavel" and estrato["classe"] in es.rebaixar:     # sem evidência independente (ou em conflito) não é "provável"
            refino["rebaixado_por_estrato"] = estrato["classe"]
            nivel = "possivel"
        taxa = {(e_, a_): x for e_, a_, x in es.p_calibrada}.get((estrato["classe"], afi))
        estrato["p_calibrada"] = taxa if (es.ativo and taxa is not None and vista.get("vps") != "0") else None
    evid = {**v.evid, "fontes": sorted(fontes), "refino": refino}
    if estrato is not None:
        evid["estrato"] = estrato
    contra = [h for h in CLASSES if h != c and p[h] >= 0.2]
    if contra and tipo != "sem_classificacao":
        h = max(contra, key=lambda x: p[x])
        alt = {"ab": {"tipo": "p2c", "a": a, "b": b}, "ba": {"tipo": "p2c", "a": b, "b": a}, "pp": {"tipo": "p2p"}}[h]
        evid["contra"] = {**alt, "p": round(p[h], 3), "fontes": sorted(fontes_independentes(h, a, b, ev, votos_v1))}
    else:
        evid.pop("contra", None)
    return Veredito(a=prov if tipo == "p2c" else a, b=cli if tipo == "p2c" else b, tipo=tipo, p=round(pc, 4), nivel=nivel, evid=evid,
                    n_vps=v.n_vps, n_ptt=v.n_ptt)


def ablacao(diag: dict, aspa_verdade: Callable[[list[Veredito]], dict], vereditos: list[Veredito], cfg: Config, afi: str) -> dict:
    """Retira uma característica por vez e re-treina/prediz sobre as características já calculadas (a "tripla" fica a da última iteração)."""
    out = {}
    for f in CARACTERISTICAS:
        nb = NaiveBayes(cfg.refino.suavizacao, sem=(f,))
        carac = diag["caracteristicas"]
        nb.treinar([(carac[k], _espelho(carac, k, diag), c, 1.0) for k, c in diag["treinados"].items()]
                   + [(carac[k], _espelho(carac, k, diag), c, cfg.refino.peso_fraco) for k, c in diag.get("fracos", {}).items()])
        t = temperatura_da_afi(cfg, afi)
        novos = []
        for v in vereditos:
            k = (min(v.a, v.b), max(v.a, v.b))
            p = posterior(nb.escores(carac[k]), t)
            c = max(CLASSES, key=lambda x: p[x])
            novos.append(Veredito(a=k[0] if c != "ba" else k[1], b=k[1] if c != "ba" else k[0], tipo="p2p" if c == "pp" else "p2c", p=p[c],
                                  nivel="provavel" if p[c] >= 0.7 else "possivel" if p[c] >= 0.5 else "sem_classificacao"))
        out[f] = aspa_verdade(novos)
    return out


def _espelho(carac: dict, k: tuple[int, int], diag: dict) -> dict[str, str]:
    return diag["caracteristicas_espelho"][k]
