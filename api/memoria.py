# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Teto de memória da API e do MCP: quantas datas ficam residentes e o que fazer perto do limite do contêiner.

Por quê (medido num ambiente de teste em 2026-11-18, teto de 6 GiB, snapshot de 2026-11-13): os caches do `Store` são dicionários por data sem
expurgo. O snapshot mais recente aquecido ocupa ~3,3 GB; consultar a fundo uma data antiga somou +1,7 GB, que nunca era devolvido.
Duas datas antigas bastavam para o OOM do contêiner (a API morre, volta fria e o site fica em 502 enquanto reaquece). O byte-cache
(`api/cache.py`) já tinha limite; o resto não.

Duas defesas, numa só tarefa de fundo. Nenhuma recusa consulta: a data antiga é sempre servida, só não fica em memória.

1. **Datas residentes.** Ficam em memória a data mais recente e as `API_DATAS_EXTRAS` (padrão 1) outras datas consultadas por
   último (começa com a anterior à mais recente). O que for de outra data é expurgado de todos os caches quando a consulta termina
   (enquanto uma consulta a usa, a data fica: ver `usando`). A próxima consulta a ela relê o disco: o histórico fica mais lento, a
   memória para de crescer. Com 0, só a data mais recente fica (o padrão do MCP no compose).
2. **Guarda.** A cada `API_MEMORIA_INTERVALO_S` lê a memória anônima do cgroup (o heap; o page cache é descartável e não conta).
   Acima de `API_MEMORIA_ALIVIO_PCT` (80) do teto, expurga tudo o que não é a data mais recente. Acima de `API_MEMORIA_CRITICO_PCT`
   (90), expurga tudo, inclusive a data mais recente, que volta a ser lida sob demanda: lentidão por alguns instantes em vez de OOM.
   (Até 2026-11-18 o crítico recusava datas antigas com 503; no MCP uma data inteira passa de 80% de um teto de 5 GiB, a memória não
   voltava abaixo do alívio e o histórico ficava recusado para sempre.)

Os caches são achados por introspecção, como em `api/diag.py`: todo mapeamento pendurado no `Store` (e nos serviços e repositórios
dele) e os mapeamentos com "cache" no nome nos módulos `api.*`. A data sai da chave: `'AAAA-MM-DD'`, `('AAAA-MM-DD', arquivo)`,
`'AAAA-MM-DD/sufixo'`, `(id, 'AAAA-MM-DD')`. Cache novo com chave nesses formatos entra sozinho; chave sem data nunca é tocada.

O objeto solto volta ao alocador por contagem de referências (dado de JSON não tem ciclo), mesmo congelado por `gc.freeze()`
(`api/heap.py`). O RSS nem sempre cai, mas a memória é reaproveitada pela data seguinte: o que importa é parar de crescer.

`API_MEMORIA=0` desliga tudo. No MCP as variáveis são as mesmas com o prefixo `MCP_` (`MCP_DATAS_EXTRAS`, `MCP_MEMORIA`…).
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
import threading
import time
from collections import Counter, OrderedDict
from contextlib import contextmanager
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

_log = logging.getLogger("arandurape")

_DATA = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)")
_DATA_EXATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _env_num(nome: str, padrao: float) -> float:
    try:
        return float(os.environ.get(nome, padrao))
    except ValueError:
        return padrao


def ligado(prefixo: str = "API") -> bool:
    """`API_MEMORIA=0` (ou `MCP_MEMORIA=0` no MCP) desliga a guarda daquele processo."""
    return os.environ.get(f"{prefixo}_MEMORIA", "1") != "0"


# ── data de uma chave de cache ───────────────────────────────────────────

def data_da_chave(chave: Any) -> Optional[str]:
    if isinstance(chave, str):
        m = _DATA.search(chave[:80])
        return m.group(1) if m else None
    if isinstance(chave, tuple):
        for parte in chave[:3]:
            if isinstance(parte, str):
                d = data_da_chave(parte)
                if d:
                    return d
    return None


# ── descoberta dos caches ────────────────────────────────────────────────

def _atributos(obj: Any) -> Iterable[tuple[str, Any]]:
    d = getattr(obj, "__dict__", None)
    if isinstance(d, dict):
        yield from list(d.items())
    for cls in type(obj).__mro__:
        for nome in getattr(cls, "__slots__", ()) or ():
            try:
                yield nome, getattr(obj, nome)
            except AttributeError:
                pass


def _e_componente(obj: Any) -> bool:
    """Serviço, repositório ou invólucro de cache do próprio código (não dado): vale descer nos atributos dele."""
    if isinstance(obj, (Mapping, list, tuple, set, frozenset, str, bytes, type)) or obj is None:
        return False
    mod = type(obj).__module__ or ""
    return mod.startswith(("api.", "core."))


class Cache:
    """Um mapeamento achado, com a trava do dono (se houver) e o nome do atributo (para as regras de proteção)."""

    __slots__ = ("nome", "mapa", "trava")

    def __init__(self, nome: str, mapa: MutableMapping, trava: Any = None):
        self.nome, self.mapa, self.trava = nome, mapa, trava


def caches_do_store(store: Any, profundidade: int = 3) -> list[Cache]:
    achados: list[Cache] = []
    vistos: set[int] = {id(store)}

    def visita(obj: Any, prefixo: str, nivel: int) -> None:
        trava = None
        attrs = list(_atributos(obj))
        for nome, v in attrs:
            if nome in ("_lock", "_trava") and hasattr(v, "acquire"):
                trava = v
        for nome, v in attrs:
            if id(v) in vistos:
                continue
            caminho = f"{prefixo}.{nome}"
            if isinstance(v, MutableMapping):
                vistos.add(id(v))
                componentes = [x for x in list(v.values())[:64] if _e_componente(x)]
                if componentes and nivel < profundidade:
                    # dicionário de serviços (ex.: `_outorgas` por sigla), não de dados: desce em cada um
                    for k, x in list(v.items()):
                        if _e_componente(x) and id(x) not in vistos:
                            vistos.add(id(x))
                            visita(x, f"{caminho}[{k!r}]", nivel + 1)
                else:
                    achados.append(Cache(caminho, v, trava))
            elif _e_componente(v) and nivel < profundidade:
                vistos.add(id(v))
                visita(v, caminho, nivel + 1)

    visita(store, "store", 0)
    return achados


def caches_de_modulo() -> list[Cache]:
    achados = []
    for nome_mod, mod in list(sys.modules.items()):
        if mod is None or not nome_mod.startswith("api."):
            continue
        for nome, v in list(vars(mod).items()):
            if "cache" in nome.lower() and isinstance(v, MutableMapping):
                achados.append(Cache(f"{nome_mod}.{nome}", v, None))
    return achados


# ── expurgo ──────────────────────────────────────────────────────────────

def expurgar(caches: Iterable[Cache], manter: set[str], protegidas: Optional[dict[str, set[str]]] = None) -> dict[str, int]:
    """Remove de cada cache as entradas de datas fora de `manter` (mais as `protegidas` daquele cache). Devolve {data: entradas}."""
    removidas: dict[str, int] = {}
    protegidas = protegidas or {}
    for c in caches:
        extra = next((v for k, v in protegidas.items() if c.nome.endswith(k)), set())
        try:
            if c.trava is not None:
                with c.trava:
                    _expurgar_um(c.mapa, manter | extra, removidas)
            else:
                _expurgar_um(c.mapa, manter | extra, removidas)
        except RuntimeError:     # mudou de tamanho durante a leitura (outra thread): fica para a próxima passada
            continue
    return removidas


def _expurgar_um(mapa: MutableMapping, manter: set[str], removidas: dict[str, int]) -> None:
    for k in list(mapa.keys()):
        d = data_da_chave(k)
        if d and d not in manter:
            mapa.pop(k, None)
            removidas[d] = removidas.get(d, 0) + 1


def datas_presentes(caches: Iterable[Cache]) -> set[str]:
    out: set[str] = set()
    for c in caches:
        try:
            for k in list(c.mapa.keys()):
                d = data_da_chave(k)
                if d:
                    out.add(d)
        except RuntimeError:
            continue
    return out


# ── uso de memória do contêiner ──────────────────────────────────────────

_CG2 = Path("/sys/fs/cgroup")
_CG1 = Path("/sys/fs/cgroup/memory")


def _ler_int(p: Path) -> Optional[int]:
    try:
        t = p.read_text().strip()
    except OSError:
        return None
    return int(t) if t.isdigit() else None


def _stat(p: Path, campo: str) -> Optional[int]:
    try:
        for linha in p.read_text().splitlines():
            k, _, v = linha.partition(" ")
            if k == campo and v.strip().isdigit():
                return int(v)
    except OSError:
        pass
    return None


def uso_memoria() -> tuple[Optional[int], Optional[int]]:
    """(memória anônima do contêiner, teto) em bytes. Anônima = heap, o que o kernel não pode descartar: é ela que leva ao OOM.
    Sem cgroup legível, o RSS do processo e teto desconhecido. `API_MEMORIA_LIMITE` (bytes) força o teto (testes, host sem cgroup)."""
    forcado = os.environ.get("API_MEMORIA_LIMITE")
    teto = int(forcado) if forcado and forcado.isdigit() else None
    if (_CG2 / "memory.max").exists():
        anon = _stat(_CG2 / "memory.stat", "anon")
        return anon, teto or _ler_int(_CG2 / "memory.max")
    if (_CG1 / "memory.limit_in_bytes").exists():
        anon = _stat(_CG1 / "memory.stat", "total_rss") or _stat(_CG1 / "memory.stat", "rss")
        lim = _ler_int(_CG1 / "memory.limit_in_bytes")
        return anon, teto or (lim if lim and lim < (1 << 60) else None)
    rss = None
    try:
        for linha in Path("/proc/self/status").read_text().splitlines():
            if linha.startswith("VmRSS:"):
                rss = int(linha.split()[1]) * 1024
    except OSError:
        pass
    return rss, teto


# ── a guarda ─────────────────────────────────────────────────────────────

class GuardaMemoria:
    def __init__(self, store: Any, latest: Callable[[], Optional[str]], *, leitor: Callable[[], tuple] = uso_memoria,
                 prefixo: str = "API"):
        # prefixo das variáveis de ambiente: API_* na API, MCP_* no servidor MCP (o mesmo Store, em outro contêiner e com outro teto)
        self.prefixo = prefixo
        self.store = store
        self._latest = latest
        self._ler = leitor
        self.extras = int(_env_num(f"{prefixo}_DATAS_EXTRAS", 1))
        self.alivio = _env_num(f"{prefixo}_MEMORIA_ALIVIO_PCT", 80) / 100
        self.critico_pct = _env_num(f"{prefixo}_MEMORIA_CRITICO_PCT", 90) / 100
        self.intervalo = _env_num(f"{prefixo}_MEMORIA_INTERVALO_S", 5)
        self.critico = False                       # a última passada expurgou tudo (informativo: nada é recusado)
        self.expurgos_totais = 0
        self._em_uso: Counter = Counter()           # datas com consulta em andamento: não são expurgadas no meio dela
        self._acessos: "OrderedDict[str, float]" = OrderedDict()   # datas não-latest, da menos para a mais recente
        self._trava = threading.Lock()
        self._evento: Optional[asyncio.Event] = None
        self._evento_t: Optional[threading.Event] = None
        self.ultimo: dict[str, Any] = {}
        self._visto_latest = latest()
        anteriores = [d for d in self._snapshots() if d != self._visto_latest]
        if anteriores and self.extras > 0:
            self._acessos[anteriores[-1]] = 0.0           # a anterior começa residente (comparações e "mudanças")

    def _snapshots(self) -> list[str]:
        try:
            return list(self.store.list_snapshots())
        except Exception:  # noqa: BLE001
            return []

    # ── chamado pelo middleware ──
    @contextmanager
    def usando(self, data: Optional[str]):
        """Envolve uma consulta: a data fica protegida do expurgo enquanto ela roda e, ao fim, é registrada (o que acorda a guarda)."""
        if not _DATA_EXATA.match(data or "") or data == self._latest():
            yield
            return
        with self._trava:
            self._em_uso[data] += 1
        try:
            yield
        finally:
            with self._trava:
                self._em_uso[data] -= 1
                if self._em_uso[data] <= 0:
                    del self._em_uso[data]
            self.registrar(data)

    def registrar(self, data: str) -> None:
        """Requisição com `?date=`: atualiza a ordem de uso e, se a data não é residente, pede um expurgo depois dela."""
        if not _DATA_EXATA.match(data or "") or data == self._latest():
            return
        with self._trava:
            self._acessos[data] = time.monotonic()
            self._acessos.move_to_end(data)
            while len(self._acessos) > max(self.extras, 0) + 8:
                self._acessos.popitem(last=False)
        self.acordar()

    def acordar(self) -> None:
        if self._evento is not None:
            self._evento.set()
        if self._evento_t is not None:
            self._evento_t.set()

    # ── política ──
    def residentes(self, so_latest: bool = False) -> set[str]:
        latest = self._latest()
        manter = {latest} if latest else set()
        with self._trava:
            if not so_latest and self.extras > 0:
                manter.update(list(self._acessos)[-self.extras:])
            manter.update(self._em_uso)
        return manter

    def protegidas(self, residentes: set[str]) -> dict[str, set[str]]:
        """Datas que um cache específico guarda para as residentes: as semanas da série de estabilidade BGP de cada uma. Sem isto a
        semana anterior de uma data residente era expurgada e relida a cada passada (visto num ambiente de teste em 2026-11-18)."""
        semanas: set[str] = set()
        bgp = getattr(self.store, "_bgp", None)
        if bgp is not None and hasattr(bgp, "bgp_stability_datas_semanais"):
            for d in residentes:
                try:
                    semanas.update(bgp.bgp_stability_datas_semanais(d, 6))
                except Exception:  # noqa: BLE001
                    pass
        return {"_bgp_horaria_cache": semanas}

    def passada(self) -> dict[str, Any]:
        """Uma verificação: mede, expurga o que estiver fora da política e atualiza o modo crítico. Bloqueante (rode em thread)."""
        t0 = time.perf_counter()
        latest = self._latest()
        if latest and self._visto_latest and latest != self._visto_latest:
            # snapshot novo publicado: o que era o mais recente vira o "anterior" e continua residente
            with self._trava:
                self._acessos[self._visto_latest] = time.monotonic()
                self._acessos.move_to_end(self._visto_latest)
        self._visto_latest = latest or self._visto_latest
        uso, teto = self._ler()
        frac = (uso / teto) if (uso and teto) else None
        so_latest = frac is not None and frac >= self.alivio
        tudo = frac is not None and frac >= self.critico_pct
        caches = caches_do_store(self.store) + caches_de_modulo()
        manter = set() if tudo else self.residentes(so_latest)
        removidas = expurgar(caches, manter, {} if tudo else self.protegidas(manter)) if (manter or tudo) else {}
        self.critico = tudo
        if tudo:
            self.expurgos_totais += 1
            _log.warning("memoria (%s): %.0f%% do teto: tudo expurgado, inclusive a data mais recente (relida sob demanda)",
                         self.prefixo, frac * 100)
        if removidas:
            uso2, _ = self._ler()
            _log.info("memoria (%s): expurgo de %s (%s entradas), uso %s → %s MiB de %s MiB, %.2f s%s",
                      self.prefixo, sorted(removidas), sum(removidas.values()), _mib(uso), _mib(uso2), _mib(teto),
                      time.perf_counter() - t0,
                      " (crítico: nenhuma data)" if tudo else " (alívio: só a data mais recente)" if so_latest else "")
            uso = uso2
            frac = (uso / teto) if (uso and teto) else None
        self.ultimo = {"uso_bytes": uso, "teto_bytes": teto, "fracao": round(frac, 3) if frac is not None else None,
                       "critico": self.critico, "residentes": sorted(manter), "expurgadas": removidas,
                       "segundos": round(time.perf_counter() - t0, 3)}
        return self.ultimo

    def estado(self) -> dict[str, Any]:
        return {"ligado": ligado(self.prefixo), "extras": self.extras, "alivio_pct": self.alivio * 100,
                "critico_pct": self.critico_pct * 100, "critico": self.critico, "expurgos_totais": self.expurgos_totais,
                "em_uso": sorted(self._em_uso),
                "acessos": list(self._acessos), "ultima_passada": self.ultimo}

    async def laco(self) -> None:
        self._evento = asyncio.Event()
        while ligado(self.prefixo):
            try:
                await asyncio.wait_for(self._evento.wait(), timeout=self.intervalo)
            except asyncio.TimeoutError:
                pass
            self._evento.clear()
            try:
                await asyncio.to_thread(self.passada)
            except Exception as exc:  # noqa: BLE001 — a guarda nunca derruba a API
                _log.warning("memoria: passada falhou: %s", exc)

    def iniciar_thread(self) -> threading.Thread:
        """O mesmo laço numa thread: para o servidor MCP, cujas tools chamam `registrar` de fora do laço de eventos
        (um `asyncio.Event` não pode ser acionado de outra thread)."""
        self._evento_t = threading.Event()

        def laco() -> None:
            while ligado(self.prefixo):
                self._evento_t.wait(self.intervalo)
                self._evento_t.clear()
                try:
                    self.passada()
                except Exception as exc:  # noqa: BLE001 — a guarda nunca derruba o serviço
                    _log.warning("memoria (%s): passada falhou: %s", self.prefixo, exc)

        t = threading.Thread(target=laco, name=f"guarda-memoria-{self.prefixo.lower()}", daemon=True)
        t.start()
        return t


def _mib(x: Optional[int]) -> Optional[int]:
    return None if x is None else x >> 20
