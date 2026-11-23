# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Leitura da camada de histórico (`data/history/`) para a API.

Os arquivos são derivados e reconstruíveis, e crescem por snapshot: `index.json` diz que datas existem; `weekly/{date}/*.jsonl.gz` traz as
linhas por ASN, PTT, operadora e UF; `events/{date}.jsonl.gz` traz os eventos. O acesso é por série (uma entidade em várias datas), então:

  * as linhas de ASN **brasileiro** (~9 mil por data) ficam em cache por data, com a chave do `sha256` do índice (reconstruir invalida);
    ASN estrangeiro não é cacheado (caminho lento, raro): varre o arquivo, que está em ordem numérica;
  * PTT, operadora e UF (arquivos pequenos) e eventos ficam em cache por data e mtime.
Tudo é leitura: a API nunca escreve em `data/history/`.
"""
from __future__ import annotations

import gzip
import json
import threading
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Iterator, Optional

_MAX_DATAS_ASN = 60               # ~9 mil linhas por data: limite de memória das linhas de ASN BR em cache


def _linhas(caminho: Path) -> Iterator[str]:
    with gzip.open(caminho, "rt", encoding="utf-8") as f:
        for ln in f:
            if ln.strip():
                yield ln


class HistoricoRepo:
    def __init__(self, base: Path):
        self.raiz = Path(base) / "history"
        self._indice: Optional[dict] = None
        self._mtime: Optional[float] = None
        self._br: "OrderedDict[tuple, dict[int, dict]]" = OrderedDict()
        self._pequenos: dict[tuple, dict] = {}
        self._eventos: dict[tuple, list[dict]] = {}
        # todos os eventos ordenados e o índice por entidade, refeitos só quando muda a lista de datas ou um arquivo de eventos
        self._todos: Optional[tuple] = None
        self._trava_todos = threading.Lock()

    # ── índice ───────────────────────────────────────────────────────────────
    def indice(self) -> dict:
        p = self.raiz / "index.json"
        if not p.exists():
            return {"snapshots": []}
        m = p.stat().st_mtime
        if self._indice is None or m != self._mtime:
            self._indice = json.loads(p.read_text(encoding="utf-8"))
            self._mtime = m
        return self._indice

    def entradas(self) -> dict[str, dict]:
        return {s["date"]: s for s in self.indice().get("snapshots", [])}

    def datas(self) -> list[str]:
        return sorted(self.entradas())

    # ── séries por entidade ──────────────────────────────────────────────────
    def _asn_br(self, date: str) -> dict[int, dict]:
        chave = (date, (self.entradas().get(date) or {}).get("asn_sha256"))
        if chave in self._br:
            self._br.move_to_end(chave)
            return self._br[chave]
        caminho = self.raiz / "weekly" / date / "asn.jsonl.gz"
        linhas: dict[int, dict] = {}
        if caminho.exists():
            for ln in _linhas(caminho):
                if '"is_br":true' in ln:                 # só decodifica o recorte BR
                    d = json.loads(ln)
                    linhas[d["asn"]] = d
        self._br[chave] = linhas
        while len(self._br) > _MAX_DATAS_ASN:
            self._br.popitem(last=False)
        return linhas

    def linha_asn(self, date: str, asn: int) -> Optional[dict]:
        br = self._asn_br(date).get(asn)
        if br is not None:
            return br
        caminho = self.raiz / "weekly" / date / "asn.jsonl.gz"
        if not caminho.exists():
            return None
        alvo = f'{{"asn":{asn},'
        for ln in _linhas(caminho):
            if ln.startswith(alvo):
                return json.loads(ln)
            if ln.startswith('{"asn":') and int(ln[7:ln.index(",")]) > asn:
                return None                               # em ordem numérica: passou do ASN
        return None

    def asns_do_cnpj(self, date: str, cnpj: str) -> list[int]:
        """ASNs brasileiros do CNPJ na data (linhas de ASN BR em cache)."""
        return sorted(a for a, ln in self._asn_br(date).items() if ln.get("cnpj") == cnpj)

    def _pequeno(self, date: str, nome: str, campo: str) -> dict[str, dict]:
        caminho = self.raiz / "weekly" / date / f"{nome}.jsonl.gz"
        if not caminho.exists():
            return {}
        chave = (date, nome, caminho.stat().st_mtime)
        if chave not in self._pequenos:
            self._pequenos = {k: v for k, v in self._pequenos.items() if k[:2] != chave[:2]}
            self._pequenos[chave] = {str(d[campo]): d for d in map(json.loads, _linhas(caminho))}
        return self._pequenos[chave]

    def linha_ixp(self, date: str, code: str) -> Optional[dict]:
        return self._pequeno(date, "ixp", "ixp").get(code)

    def linha_operadora(self, date: str, cnpj: str) -> Optional[dict]:
        return self._pequeno(date, "operadora", "cnpj").get(cnpj)

    def linha_uf(self, date: str, uf: str) -> Optional[dict]:
        return self._pequeno(date, "uf", "uf").get(uf)

    def linhas_uf(self, date: str) -> list[dict]:
        return list(self._pequeno(date, "uf", "uf").values())

    def linhas_ixp(self, date: str) -> list[dict]:
        return list(self._pequeno(date, "ixp", "ixp").values())

    def series_asn_br(self, ultimas: int) -> list[dict]:
        """Linhas de ASN brasileiro das `ultimas` datas com histórico, com a coluna `data` (tabela da coleção `series_asn` do `/query`)."""
        datas = self.datas()[-ultimas:]
        chave = (tuple(datas), self._mtime, tuple((self.entradas().get(d) or {}).get("asn_sha256") for d in datas))
        if getattr(self, "_series_chave", None) != chave:
            linhas = []
            for d in datas:
                for asn, ln in sorted(self._asn_br(d).items()):
                    linhas.append({"data": d, **{k: v for k, v in ln.items() if not k.startswith("hash_") and k != "is_br"}})
            self._series_chave, self._series_linhas = chave, linhas
        return self._series_linhas

    # ── eventos ──────────────────────────────────────────────────────────────
    def _chave_eventos(self) -> tuple:
        partes = []
        for d in self.datas():
            try:
                partes.append((d, (self.raiz / "events" / f"{d}.jsonl.gz").stat().st_mtime))
            except OSError:
                partes.append((d, None))
        return tuple(partes)

    def _montar_todos(self) -> tuple:
        """(lista ordenada, índice). Montar custa juntar e ordenar dezenas de milhares de eventos: no teste de carga de 2026-11-23 isso,
        refeito a cada perfil, era metade do tempo em que a API segurava o GIL. Agora só quando a chave muda, e sob trava (uma montagem só
        quando vários pedidos chegam juntos)."""
        chave = self._chave_eventos()
        atual = self._todos
        if atual is not None and atual[0] == chave:
            return atual
        with self._trava_todos:
            atual = self._todos
            if atual is not None and atual[0] == chave:
                return atual
            out = [e for d, _ in chave for e in self.eventos(d)]
            out.sort(key=lambda e: (e["data"], e["tipo"], e["entidade"], e["chave"]), reverse=True)
            idx: dict[str, dict] = {"asn": defaultdict(list), "ixp": defaultdict(list), "uf": defaultdict(list), "entidade": defaultdict(list)}
            for e in out:                                   # na ordem da lista: cada recorte já sai ordenado
                if e.get("asn") is not None:
                    idx["asn"][e["asn"]].append(e)
                if e["tipo"].startswith("ixp_"):
                    idx["ixp"][e["chave"]].append(e)
                if e.get("uf") is not None:
                    idx["uf"][e["uf"]].append(e)
                idx["entidade"][e["entidade"]].append(e)
            self._todos = (chave, out, {k: dict(v) for k, v in idx.items()}, {id(e): i for i, e in enumerate(out)})
            return self._todos

    def todos_eventos(self) -> list[dict]:
        """Todos os eventos de todas as datas com histórico (tabela da coleção `eventos` do `/query`), do mais recente ao mais antigo.
        A lista é compartilhada entre pedidos: só leitura."""
        return self._montar_todos()[1]

    def posicao(self, evento: dict) -> int:
        """Posição do evento em `todos_eventos` (para juntar recortes do índice sem perder a ordem entre empates da chave de ordenação)."""
        return self._montar_todos()[3][id(evento)]

    def eventos_de(self, campo: str, valor) -> list[dict]:
        """Os eventos com `campo` (`asn`, `ixp`, `uf` ou `entidade`) igual a `valor`, na ordem de `todos_eventos` (só leitura)."""
        return self._montar_todos()[2][campo].get(valor, [])

    def eventos(self, date: str) -> list[dict]:
        caminho = self.raiz / "events" / f"{date}.jsonl.gz"
        if not caminho.exists():
            return []
        chave = (date, caminho.stat().st_mtime)          # o arquivo é regravado quando um pendente é decidido
        if chave not in self._eventos:
            self._eventos = {k: v for k, v in self._eventos.items() if k[0] != date}
            self._eventos[chave] = [json.loads(x) for x in _linhas(caminho)]
        return self._eventos[chave]
