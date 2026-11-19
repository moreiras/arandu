# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Peças comuns da coleta em rodízio: fontes que não cabem num único run e cobrem o universo ao longo dos dias.

Cada rodada consulta no máximo N itens (os sem leitura primeiro, depois os de leitura mais antiga), no ritmo que a fonte tolera,
herda do documento da rodada anterior o que não renovou e carrega a data de cada leitura. Usado por `cloudflare_radar` e pelas
fontes de varredura longa seguintes (Alice por vizinho, RDAP de contatos, SIASG). A lógica que depende da fonte (o que é um item, o que
é uma resposta completa) fica no coletor; aqui só há o que não muda.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Hashable, Iterable, Optional, Sequence

from core.common import read_json_gz


def anterior_normalizado(base: Path, date_str: str, arquivo: str, *, incluir_data: bool = False) -> dict:
    """Documento `normalized/{data}/summary/{arquivo}` da rodada mais recente anterior a `date_str` ({} se não houver).

    `incluir_data=True` aceita também a própria data (repetir a rodada com --force continua de onde ela estava)."""
    raiz = base / "normalized"
    if not raiz.is_dir():
        return {}
    for d in sorted((p.name for p in raiz.iterdir() if p.is_dir() and (p.name <= date_str if incluir_data else p.name < date_str)), reverse=True):
        arq = raiz / d / "summary" / arquivo
        if arq.is_file():
            return read_json_gz(arq)
    return {}


def escolher_por_idade(itens: Iterable[Any], lida_em: Callable[[Any], Optional[str]], limite: int) -> list:
    """Até `limite` itens: sem leitura primeiro, depois a mais antiga; empate pela ordem do próprio item (estável entre execuções).

    `lida_em(item)` devolve a data/hora ISO da última leitura ou None/"" se nunca foi lido. `limite <= 0` devolve todos na mesma ordem."""
    ordenados = sorted(itens, key=lambda i: (lida_em(i) or "", i))
    return ordenados[:limite] if limite and limite > 0 else ordenados


class Limitador:
    """Intervalo mínimo entre duas requisições (o `Crawl-delay`, o ritmo medido da fonte). `esperar()` antes de cada requisição."""

    def __init__(self, intervalo_s: float, relogio: Callable[[], float] = time.monotonic, dormir: Callable[[float], None] = time.sleep):
        self.intervalo_s, self.relogio, self.dormir = float(intervalo_s), relogio, dormir
        self._ultima: Optional[float] = None

    def continuar_de(self, outro: "Limitador") -> "Limitador":
        """Conta o intervalo a partir da última requisição de `outro` (troca de ritmo no meio da rodada sem requisição colada na anterior)."""
        self._ultima = outro._ultima
        return self

    def esperar(self) -> float:
        """Dorme o que falta para completar o intervalo desde a requisição anterior; devolve o que dormiu."""
        agora = self.relogio()
        falta = 0.0 if self._ultima is None else max(0.0, self.intervalo_s - (agora - self._ultima))
        if falta > 0:
            self.dormir(falta)
        self._ultima = self.relogio() if falta == 0 else agora + falta
        return falta


class Orcamento:
    """Limites de uma rodada: requisições, tempo de relógio e falhas seguidas. `motivo_parada()` diz por que parar (None = pode seguir)."""

    def __init__(self, requisicoes: int = 0, tempo_max_s: float = 0, falhas_seguidas_max: int = 0, relogio: Callable[[], float] = time.monotonic):
        self.requisicoes, self.tempo_max_s, self.falhas_seguidas_max, self.relogio = requisicoes, tempo_max_s, falhas_seguidas_max, relogio
        self.gastas = 0
        self.falhas = 0
        self.falhas_seguidas = 0
        self.t0 = relogio()

    def gastar(self, n: int = 1) -> None:
        self.gastas += n

    def sucesso(self) -> None:
        self.falhas_seguidas = 0

    def falha(self) -> None:
        self.falhas += 1
        self.falhas_seguidas += 1

    def motivo_parada(self) -> Optional[str]:
        if self.requisicoes and self.gastas >= self.requisicoes:
            return f"orçamento de {self.requisicoes} requisições esgotado"
        if self.tempo_max_s and self.relogio() - self.t0 > self.tempo_max_s:
            return f"tempo máximo de {self.tempo_max_s:g} s da rodada esgotado"
        if self.falhas_seguidas_max and self.falhas_seguidas >= self.falhas_seguidas_max:
            return f"{self.falhas_seguidas} falhas seguidas"
        return None

    def resumo(self) -> dict:
        return {"requisicoes_gastas": self.gastas, "falhas": self.falhas, "segundos": round(self.relogio() - self.t0, 1)}


def herdar(anterior: dict[Hashable, dict], novos: dict[Hashable, dict], vivos: Optional[set] = None, max_idade_dias: Optional[int] = None,
           data: Optional[str] = None, lida_em: str = "em") -> dict[Hashable, dict]:
    """Registros desta rodada mais o que a anterior tinha e esta não renovou (marcado `herdado: true`, com a data original).

    `vivos` limita ao universo atual (item que sumiu não é herdado). `max_idade_dias` + `data` descartam o herdado velho demais."""
    import datetime as _dt

    saida = dict(novos)
    for chave, v in anterior.items():
        if chave in saida or (vivos is not None and chave not in vivos):
            continue
        if max_idade_dias is not None and data and v.get(lida_em):
            if (_dt.date.fromisoformat(data) - _dt.date.fromisoformat(str(v[lida_em])[:10])).days > max_idade_dias:
                continue
        saida[chave] = {**v, "herdado": True}
    return saida
