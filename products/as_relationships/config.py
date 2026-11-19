# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Parâmetros do algoritmo (config/as_relationships.yaml). Valores padrão idênticos ao arquivo: o teste confere."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

ARQUIVO = Path(__file__).resolve().parents[2] / "config" / "as_relationships.yaml"


@dataclass(frozen=True)
class Pesos:
    prior_par: float = 0.3
    aspa_positivo: float = 7.0
    aspa_negativo: float = 1.0
    rs_max: float = 3.2
    rs_bonus_ptt: float = 0.4
    colecao_max: float = 2.6
    caida_p2c: float = 1.5
    caida_p2p: float = 1.2
    clique_par: float = 8.0
    clique_borda: float = 2.2
    irmaos: float = 2.5


@dataclass(frozen=True)
class Estratos:
    """Estratos de evidência independente: o elo p2c é `ambos` (CAIDA e tripla confirmam), `so_caida`, `so_tripla`, `conflito` ou `sem_evidencia`.
    `rebaixar`: estratos cujo p2c "provável" passa a "possível" (acerto de 2% a 22% no ASPA, medido na régua). `p_calibrada`: taxa de acerto observada
    no ASPA (sem o ASPA como entrada) por estrato e família; só vale para elos com `vps` > 0. Estrato fora da tabela não recebe `p_calibrada`."""
    ativo: bool = True
    rebaixar: tuple[str, ...] = ("conflito", "sem_evidencia")
    p_calibrada: tuple[tuple[str, str, float], ...] = (("ambos", "v4", 0.9241), ("ambos", "v6", 0.9509), ("so_caida", "v4", 0.9058), ("so_caida", "v6", 0.9527))
    medido_em: str = "2026-11-06"


@dataclass(frozen=True)
class Refino:
    """ARC v2: Naive Bayes iterativo sobre o veredito da v1 (bootstrap), restrições, histerese."""
    ativo: bool = True
    iteracoes: int = 3
    p_treino: float = 0.7                 # só vereditos da v1 com ao menos este p (e nível ≥ provável) treinam a primeira rodada
    p_ancora: float = 0.9                 # posterior mínimo para o elo virar âncora de propagação na rodada seguinte
    suavizacao: float = 1.0               # Laplace
    cap_v1: bool = True                   # o nível da v2 não passa do da v1 (o NB não promove; ver a régua em products/as_relationships/regua.py)
    peso_fraco: float = 0.3               # peso dos rótulos de nível possível da v1 no treino (os firmes pesam 1)
    abstencao: float = 0.5                # abaixo disto o elo fica sem classificação (abstenção)
    temperatura: tuple[tuple[str, float], ...] = (("v4", 1.0), ("v6", 1.0))   # calibração por família (régua sem ASPA; 1,0 = sem ajuste)
    ece_max: float = 0.10                 # acima disto a probabilidade é publicada como não calibrada
    complexa_p_min: float = 0.8           # v4 e v6 divergem "com força" quando os dois têm ao menos este p e nível ≥ provável
    persistencia: int = 2                 # snapshots consecutivos com a mesma proposta para a relação mudar de estado (E6)
    cone_max_asns: int = 5000             # teto de ASNs listados no cone (produto `transito`)
    ece: tuple[tuple[str, float], ...] = (("v4", 0.3776), ("v6", 0.4154))   # ECE (p ≥ 0,5) de validação cruzada da régua sem ASPA; acima de ece_max = p não calibrada
    calibrado_em: str = "2026-11-05"      # data do snapshot em que a régua mediu o ECE
    estratos: Estratos = field(default_factory=Estratos)
    irr: bool = False                     # `lg_ixbr`: a política do IRR (import/export dos aut-num) entra como característica do NB; desligada até a régua medir


@dataclass(frozen=True)
class Config:
    versao: int = 2
    asns_ixp: frozenset[int] = frozenset({26162})
    descartar_asn: tuple[tuple[int, int], ...] = ((0, 0), (23456, 23456), (64512, 65535), (4200000000, 4294967295))
    clique_candidatos: int = 60
    clique_tamanho_minimo: int = 3
    rodadas: int = 3
    visibilidade_min_vps: int = 3
    visibilidade_min_ptt: int = 2
    votos_para_ancora: int = 8
    razao_para_ancora: float = 0.9
    pesos: Pesos = field(default_factory=Pesos)
    # nível → (p mínimo, fontes independentes mínimas), do mais forte ao mais fraco
    niveis: tuple[tuple[str, float, int], ...] = (("confirmado", 0.95, 2), ("provavel", 0.70, 1), ("possivel", 0.50, 0))
    refino: Refino = field(default_factory=Refino)


def carregar(caminho: Path = ARQUIVO) -> Config:
    d = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
    c, p, n = d.get("clique", {}), d.get("propagacao", {}), d.get("niveis", {})
    base = Config()
    r = d.get("refino") or {}
    rb = base.refino
    e = r.get("estratos") or {}
    eb = rb.estratos
    estratos = Estratos(
        ativo=bool(e.get("ativo", eb.ativo)), rebaixar=tuple(str(x) for x in e.get("rebaixar", eb.rebaixar)),
        p_calibrada=tuple((str(k), str(a), float(v)) for k, por_afi in (e.get("p_calibrada") or {}).items() for a, v in por_afi.items()) if "p_calibrada" in e else eb.p_calibrada,
        medido_em=str(e.get("medido_em", eb.medido_em)))
    refino = Refino(
        ativo=bool(r.get("ativo", rb.ativo)), iteracoes=int(r.get("iteracoes", rb.iteracoes)), p_treino=float(r.get("p_treino", rb.p_treino)),
        p_ancora=float(r.get("p_ancora", rb.p_ancora)), suavizacao=float(r.get("suavizacao", rb.suavizacao)), peso_fraco=float(r.get("peso_fraco", rb.peso_fraco)), cap_v1=bool(r.get("cap_v1", rb.cap_v1)),
        abstencao=float(r.get("abstencao", rb.abstencao)),
        temperatura=tuple((str(k), float(v)) for k, v in (r.get("temperatura") or dict(rb.temperatura)).items()),
        ece_max=float(r.get("ece_max", rb.ece_max)), complexa_p_min=float(r.get("complexa_p_min", rb.complexa_p_min)),
        persistencia=int(r.get("persistencia", rb.persistencia)), cone_max_asns=int(r.get("cone_max_asns", rb.cone_max_asns)),
        ece=tuple((str(k), float(v)) for k, v in (r.get("ece") or {}).items() if v is not None), calibrado_em=str(r.get("calibrado_em", rb.calibrado_em) or ""),
        estratos=estratos, irr=bool(r.get("irr", rb.irr)))
    return Config(
        versao=int(d.get("versao", base.versao)),
        asns_ixp=frozenset(int(x) for x in d.get("asns_ixp", base.asns_ixp)),
        descartar_asn=tuple((int(a), int(b)) for a, b in d.get("descartar_asn", base.descartar_asn)),
        clique_candidatos=int(c.get("candidatos", base.clique_candidatos)),
        clique_tamanho_minimo=int(c.get("tamanho_minimo", base.clique_tamanho_minimo)),
        rodadas=int(p.get("rodadas", base.rodadas)),
        visibilidade_min_vps=int((d.get("visibilidade") or {}).get("min_vps", base.visibilidade_min_vps)),
        visibilidade_min_ptt=int((d.get("visibilidade") or {}).get("min_ptt", base.visibilidade_min_ptt)),
        votos_para_ancora=int(p.get("votos_para_ancora", base.votos_para_ancora)),
        razao_para_ancora=float(p.get("razao_para_ancora", base.razao_para_ancora)),
        pesos=Pesos(**{k: float(v) for k, v in (d.get("pesos") or {}).items()}),
        niveis=tuple((nome, float(v["p_min"]), int(v["fontes_independentes"])) for nome, v in n.items()) or base.niveis,
        refino=refino,
    )
