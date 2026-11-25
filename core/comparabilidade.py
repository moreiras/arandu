# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Regra única de comparabilidade entre dois pontos de uma série (PT-28).

Dois pontos só têm variação calculada quando são comparáveis. Esta é a única definição no código: a API (`/snapshots/diff`, `/history/*`,
`/history/brasil/series`, `/changes/summary`, `/cdns/mudancas`) a aplica e devolve o resultado com o texto do "Como ler"; o frontend só desenha o
que a API entrega, sem recalcular nem reescrever a regra.

Um ponto é `{"date": AAAA-MM-DD, "valor": número ou None, "meta": {...}}`, com `meta` opcional:
  base      identificador da população ou da fonte do número (outra base = outro número, não variação);
  metodo    identificador do método ou da regra de cálculo (hash das regras, definição de "rota brasileira"...);
  cobertura {nome: número} do que sustenta o ponto (ASNs medidos, PTTs coletados...);
  coleta_ok falso quando a coleta do ponto foi parcial ou falhou.

Motivos que impedem a variação: `ausente`, `base_diferente`, `metodo_mudou`, `cobertura_mudou`, `data_atipica`. `lacuna` (semanas sem snapshot entre os
pontos) só avisa. A variação nunca vira zero por falta de dado, e a regra não atribui causa: diz que os pontos não são comparáveis e por quê."""
from __future__ import annotations

import datetime as dt
from typing import Any, Optional

VERSAO_REGRA = 1

# Variação relativa de uma medida de cobertura (ASNs medidos, PTTs coletados) a partir da qual os dois pontos deixam de ser comparáveis. Na
# primeira medição do índice de prontidão a cobertura de Filtragem triplicou entre duas semanas: 25% é limiar de projeto, não derivado de dado.
LIMIAR_COBERTURA = 0.25
# Pontos comparáveis seguidos para desenhar uma linha (e não só pontos): com menos, a série não sustenta leitura de tendência.
MIN_PONTOS_LINHA = 4
# Intervalo normal entre snapshots semanais, com folga; acima disso há semanas sem snapshot entre os pontos.
DIAS_ENTRE_SNAPSHOTS = 10

MOTIVOS: dict[str, str] = {
    "ausente": "falta a medida em um dos pontos",
    "base_diferente": "a base (população ou fonte) do número é outra nos dois pontos",
    "metodo_mudou": "o método ou a regra de cálculo mudou entre os pontos",
    "cobertura_mudou": "a cobertura da coleta ou da medição mudou muito entre os pontos",
    "data_atipica": "um dos pontos está numa data atípica marcada",
    "lacuna": "há semanas sem snapshot entre os dois pontos",
}
BLOQUEIAM = ("ausente", "base_diferente", "metodo_mudou", "cobertura_mudou", "data_atipica")

# D7: pico de 2026-07-05. O campo-fonte de ROA, ASPA e RPKI dos ASNs estrangeiros deixou de vir nessa data e a ausência era contada como zero
# (a regra 2 dos eventos corrigiu isso, mas a data fica marcada, não apagada). A causa do campo ausente é hipótese a confirmar.
DATAS_ATIPICAS: dict[str, dict[str, Any]] = {
    "2026-07-05": {
        "motivo": "o campo de ROA, ASPA e RPKI dos ASNs estrangeiros deixou de vir nesta data (causa a confirmar); eventos de perda dessas "
                  "famílias foram regenerados com a regra 2, e a data fica marcada",
        "tipos_evento": ("roa_perdido", "aspa_perdido", "rpki_invalido_resolvido"),
        "metricas": ("n_roa", "n_aspa", "rpki_valid", "rpki_invalid", "rpki_not_found"),
        "so_estrangeiro": True,
    },
}

REGRA_COMO_LER = (
    "Variação só entre pontos comparáveis. Dois pontos não são comparáveis quando a medida falta em um deles, quando a base (população ou fonte) "
    "ou o método de cálculo mudou, quando a cobertura da coleta variou 25% ou mais, ou quando um deles está numa data atípica marcada. Nesses casos a "
    "variação não é calculada, e a série mostra o corte e o motivo, sem atribuir causa.",
    "Semanas sem snapshot entre dois pontos comparáveis aparecem como aviso. A linha só é desenhada com pelo menos 4 pontos comparáveis seguidos; "
    "com menos, a série aparece como pontos e na tabela.",
)


def regra() -> dict:
    """A regra em forma publicável (vai nas respostas das séries, para o "Como ler" da tela)."""
    return {"versao": VERSAO_REGRA, "limiar_cobertura": LIMIAR_COBERTURA, "min_pontos_linha": MIN_PONTOS_LINHA, "motivos": dict(MOTIVOS),
            "datas_atipicas": {d: {"motivo": v["motivo"], "tipos_evento": list(v["tipos_evento"]), "metricas": list(v["metricas"])} for d, v in DATAS_ATIPICAS.items()},
            "texto": list(REGRA_COMO_LER)}


def _motivo(codigo: str, detalhe: Optional[str] = None) -> dict:
    out = {"codigo": codigo, "texto": MOTIVOS[codigo]}
    if detalhe:
        out["detalhe"] = detalhe
    return out


def atipica(data: str, metrica: Optional[str] = None, estrangeiro: bool = False) -> Optional[str]:
    """Texto do motivo se `data` é atípica para a métrica. Com `so_estrangeiro`, só vale para escopo estrangeiro (os totais brasileiros não sofrem)."""
    a = DATAS_ATIPICAS.get(data)
    if not a or (a.get("so_estrangeiro") and not estrangeiro):
        return None
    if metrica is not None and metrica not in a["metricas"]:
        return None
    return a["motivo"]


def atipica_evento(data: str, tipo: str) -> Optional[str]:
    """Texto do motivo se os eventos do `tipo` na `data` são de data atípica (D7)."""
    a = DATAS_ATIPICAS.get(data)
    return a["motivo"] if a and tipo in a["tipos_evento"] else None


def _cobertura_mudou(ma: dict, mb: dict) -> Optional[str]:
    ca, cb = ma.get("cobertura") or {}, mb.get("cobertura") or {}
    for nome in sorted(set(ca) & set(cb)):
        x, y = ca[nome], cb[nome]
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            continue
        if x == 0 and y == 0:
            continue
        base = max(abs(x), abs(y))
        if abs(y - x) / base >= LIMIAR_COBERTURA:
            return f"{nome}: {x:g} para {y:g}"
    if ma.get("coleta_ok") is not None and mb.get("coleta_ok") is not None and ma["coleta_ok"] != mb["coleta_ok"]:
        return "coleta parcial ou ausente em um dos pontos"
    return None


def avaliar(a: dict, b: dict, metrica: Optional[str] = None, estrangeiro: bool = False) -> dict:
    """Compara dois pontos. `{"comparavel": bool, "motivos": [...], "avisos": [...]}`; `motivos` bloqueiam a variação, `avisos` não."""
    ma, mb = a.get("meta") or {}, b.get("meta") or {}
    motivos: list[dict] = []
    if a.get("valor") is None or b.get("valor") is None:
        motivos.append(_motivo("ausente"))           # sem medida não há o que comparar: base, método e cobertura do ponto vazio não entram
    else:
        if ma.get("base") != mb.get("base"):
            motivos.append(_motivo("base_diferente", f"{ma.get('base')} e {mb.get('base')}"))
        if ma.get("metodo") != mb.get("metodo"):
            motivos.append(_motivo("metodo_mudou", f"{ma.get('metodo')} e {mb.get('metodo')}"))
        det = _cobertura_mudou(ma, mb)
        if det:
            motivos.append(_motivo("cobertura_mudou", det))
    for p in (a, b):
        t = atipica(p["date"], metrica, estrangeiro)
        if t:
            motivos.append(_motivo("data_atipica", p["date"]))
    avisos = []
    try:
        dias = abs((dt.date.fromisoformat(b["date"]) - dt.date.fromisoformat(a["date"])).days)
        if dias > DIAS_ENTRE_SNAPSHOTS:
            avisos.append(_motivo("lacuna", f"{dias} dias entre {min(a['date'], b['date'])} e {max(a['date'], b['date'])}"))
    except (KeyError, ValueError):
        pass
    return {"comparavel": not motivos, "motivos": motivos, "avisos": avisos}


def variacao(a: dict, b: dict, metrica: Optional[str] = None, unidade: str = "absoluta", estrangeiro: bool = False) -> dict:
    """Variação de `a` para `b`. Sem comparabilidade, `calculada` é falso, nada de número e os `motivos` dizem por quê.
    `unidade="pp"` para valores já em percentual: a variação é em pontos percentuais e `pct` não é calculado."""
    av = avaliar(a, b, metrica, estrangeiro)
    out: dict = {"de": a["date"], "para": b["date"], "calculada": av["comparavel"], "motivos": av["motivos"], "avisos": av["avisos"]}
    if av["comparavel"]:
        d = b["valor"] - a["valor"]
        out["absoluta"] = round(d, 4) if isinstance(d, float) else d
        out["unidade"] = unidade
        out["pct"] = None if unidade == "pp" or not a["valor"] else round(100 * d / a["valor"], 2)
    return out


def anotar_serie(pontos: list[dict], metrica: Optional[str] = None, estrangeiro: bool = False, unidade: str = "absoluta") -> dict:
    """Marca cada ponto com `comparavel_com_anterior` (None no primeiro) e `motivos`, divide a série em segmentos de pontos comparáveis seguidos e
    calcula a variação do último segmento. `desenhar_linha` só é verdadeiro com `MIN_PONTOS_LINHA` ou mais pontos no último segmento."""
    marcados: list[dict] = []
    segmentos: list[list[int]] = []
    for i, p in enumerate(pontos):
        if i == 0:
            marcados.append({**p, "comparavel_com_anterior": None, "motivos": [], "avisos": []})
            segmentos.append([0] if p.get("valor") is not None else [])
            continue
        av = avaliar(pontos[i - 1], p, metrica, estrangeiro)
        marcados.append({**p, "comparavel_com_anterior": av["comparavel"], "motivos": [m["codigo"] for m in av["motivos"]],
                         "detalhes": av["motivos"], "avisos": [m["codigo"] for m in av["avisos"]]})
        if av["comparavel"]:
            segmentos[-1].append(i)
        else:
            segmentos.append([i] if p.get("valor") is not None else [])
    segmentos = [s for s in segmentos if s]
    ultimo = segmentos[-1] if segmentos else []
    out: dict = {"pontos": marcados, "segmentos": segmentos, "desenhar_linha": len(ultimo) >= MIN_PONTOS_LINHA}
    if len(ultimo) >= 2:
        out["variacao"] = variacao(pontos[ultimo[0]], pontos[ultimo[-1]], metrica, unidade, estrangeiro)
    elif len(pontos) >= 2:
        out["variacao"] = variacao(pontos[-2], pontos[-1], metrica, unidade, estrangeiro)
    cortes = [p for p in marcados[1:] if p["comparavel_com_anterior"] is False]
    if cortes:
        out["nota"] = "Série cortada onde os pontos não são comparáveis: " + "; ".join(
            f"{p['date']} ({', '.join(m['texto'] + (' [' + m['detalhe'] + ']' if m.get('detalhe') else '') for m in p['detalhes'])})" for p in cortes) + "."
    return out
