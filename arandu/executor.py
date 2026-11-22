# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Executor do pipeline: ordem calculada, política de falha, relatório por execução, lock e retomada."""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional

from arandu import publicacao
from arandu.lockfile import LockOcupado, lock  # noqa: F401
from core.catalog.loader import Catalog, dependencias_de_etapas, id_de_etapa, ordem_de_execucao
from arandu.runner import Resultado
from core.catalog.schema import Step

OK, FALHA, PULADA, DELEGADA, RETOMADA, NAO_EXECUTADA, PLANEJADA = (
    "ok", "falha", "pulada", "delegada_ao_host", "retomada", "nao_executada", "planejada")


# `LockOcupado` e `lock` vêm de `arandu.lockfile` (flock, não pid): re-exportados aqui por compatibilidade


def agora() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def hoje() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")


def _escreve_atomico(path: Path, texto: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(texto)
        os.chmod(tmp, 0o644)           # mkstemp cria 0600; o worker roda como root e o painel/diagnóstico lê como usuário comum
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def idade_dias(marcador: Path, campo: str, em: str) -> Optional[int]:
    """Dias entre a data do marcador e `em`; None se o marcador não existe ou é ilegível."""
    try:
        d = json.loads(marcador.read_text(encoding="utf-8")).get(campo, "")
        return (dt.date.fromisoformat(em) - dt.date.fromisoformat(d)).days
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def vencida(step: Step, data_dir: Path, date: str, env: Optional[dict] = None) -> tuple[bool, str]:
    """A etapa com `executar_se` está devida? (sem marcador legível = devida)."""
    e = step.executar_se
    if e is None:
        return True, ""
    env = os.environ if env is None else env
    limite = e.max_idade_dias
    if e.env_max_idade and str(env.get(e.env_max_idade, "")).isdigit():
        limite = int(env[e.env_max_idade])
    idade = idade_dias(data_dir / e.marcador, e.campo, date)
    if idade is None or idade < 0:
        return True, "sem marcador válido"
    if idade >= limite:
        return True, f"última execução há {idade} dia(s) (limite {limite})"
    return False, f"última execução há {idade} dia(s), dentro do limite de {limite}"


PERIODO_DIAS = {"diaria": 1, "diaria_se_novo_mes": 1, "semanal": 7, "mensal": 30}


def bloqueada_por_disco(step: Step, data_dir: Path) -> Optional[str]:
    """Coleta `pesada` não começa com o disco acima do limite de bloqueio (85%): melhor falhar cedo do que encher o volume.

    Devolve o motivo, ou None se pode rodar. A etapa segue a `politica_falha` como qualquer falha."""
    if not step.pesada:
        return None
    from arandu.ops import BLOQUEIO_DISCO_PCT

    try:
        du = shutil.disk_usage(data_dir)
    except OSError:
        return None
    limite = float(os.environ.get("ARANDU_BLOQUEIO_DISCO_PCT", BLOQUEIO_DISCO_PCT))
    pct = round(100 * du.used / du.total, 1)
    if pct >= limite:
        return f"disco com {pct}% de uso (limite {limite:g}%): coleta pesada bloqueada; libere espaço (arandu gc --dry-run)"
    return None


def versao_incompleta(cat: Catalog, data_dir: Path, fonte: str) -> Optional[str]:
    """Padrão declarado em `armazem.incluir` que a última versão da fonte não contém (None se completa ou sem declaração).

    Versões registradas antes de o bruto entrar no armazém (ex.: lg_ixbr) não servem para restaurar o que as
    etapas seguintes leem: a fonte é coletada de novo."""
    import fnmatch
    from core.store import listar
    from core.store.fontes import padroes_da_fonte

    s = cat.sources.get(fonte)
    if not (s and s.armazem and s.armazem.incluir):
        return None
    vs = listar(data_dir, fonte)
    if not vs:
        return None
    for tipo, pad in padroes_da_fonte(cat, fonte):
        glob = f"{tipo}/" + re.sub(r"\{[^}]+\}", "*", pad)
        if not any(fnmatch.fnmatch(a, glob) for a in vs[-1].arquivos):
            return pad
    return None


def devida_por_cadencia(cat: Catalog, step: Step, data_dir: Path, date: str, env: Optional[dict] = None) -> tuple[bool, str]:
    """A etapa está devida segundo a cadência da fonte que ela produz e a última coleta registrada no armazém?

    Etapas sem fonte (análises, produtos) estão sempre devidas. Sem registro no armazém, vale o marcador antigo
    (`executar_se`) ou, na falta dele, a etapa roda. `sob_demanda` e `manual` só rodam com `--only`."""
    from core.store import ultima_verificacao

    fontes = [f for f in step.fontes if f in cat.sources and cat.sources[f].tipo != "curada"]
    if not fontes:
        return True, "etapa sem fonte"
    fid = fontes[0]
    if any(cat.sources[f].armazem and cat.sources[f].armazem.sempre_coletar for f in fontes):
        return True, "o bruto que as etapas seguintes leem não é versionado (até o passo 1.2.4): sempre coleta"
    coleta = cat.sources[fid].cadencia.coleta_atual
    if coleta not in PERIODO_DIAS:
        return False, f"coleta '{coleta}': só sob demanda"
    for f in fontes:
        falta = versao_incompleta(cat, data_dir, f)
        if falta:
            return True, f"a última versão de {f} no armazém não tem {falta} (registrada antes do bruto versionado): coleta"
    ult = ultima_verificacao(data_dir, fid)
    if ult is None:
        if step.executar_se:
            return vencida(step, data_dir, date, env)
        return True, "sem versão registrada no armazém"
    try:
        dias = (dt.date.fromisoformat(date) - dt.date.fromisoformat(ult[:10])).days
    except ValueError:
        return True, "data inválida no registro do armazém"
    if dias < 0:
        return True, f"reprocessamento de uma data anterior à última coleta ({ult[:10]})"
    periodo = PERIODO_DIAS[coleta]
    if dias >= periodo:
        return True, f"última coleta há {dias} dia(s) (cadência {coleta}: {periodo})"
    return False, f"última coleta há {dias} dia(s), dentro da cadência {coleta} ({periodo})"


def restaurar_pins(cat: Catalog, step: Step, data_dir: Path, date: str) -> list[dict]:
    """`--pin-sources`: restaura as versões que o manifesto de `date` registrou, em vez de coletar de novo.

    Fonte `legado` (snapshot anterior ao armazém) mantém os arquivos que já estão nos caminhos antigos."""
    from core.store import listar, materializar

    try:
        manifesto = json.loads((data_dir / "published" / date / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifesto = {}
    pins = {s["id"]: s for s in manifesto.get("sources") or []}
    saida = []
    for fid in step.fontes:
        p = pins.get(fid)
        if not p or not p.get("versao"):
            continue
        v = next((x for x in listar(data_dir, fid) if x.nome == p["versao"]), None)
        if v is None:
            raise FileNotFoundError(f"versão {p['versao']} de {fid} (fixada pelo manifesto de {date}) não está no armazém")
        materializar(data_dir, v, date, sobrescrever=True)
        saida.append({"fonte": fid, "versao": v.nome, "as_of": v.as_of})
    return saida


def reutilizar_versao(cat: Catalog, step: Step, data_dir: Path, date: str) -> list[dict]:
    """Restaura nos caminhos de sempre a melhor versão disponível das fontes da etapa (compõe o snapshot)."""
    from core.store import materializar, resolver

    saida = []
    for fid in step.fontes:
        v = resolver(data_dir, fid, date)
        if v is None:
            continue
        materializar(data_dir, v, date)
        saida.append({"fonte": fid, "versao": v.nome, "as_of": v.as_of})
    return saida


def reaproveitar(step: Step, data_dir: Path, date: str) -> tuple[bool, str]:
    """Copia o arquivo da última coleta válida para a data (política usar_ultima_valida)."""
    rel = step.reaproveita.replace("{date}", date) if step.reaproveita else None
    if not rel:
        return False, "sem 'reaproveita'"
    destino = data_dir / rel
    if destino.exists():
        return True, "já existe para a data"
    candidatos: list[str] = []
    e = step.executar_se or None
    marc = data_dir / (step.gravar_marcador or (e.marcador if e else "")) if (step.gravar_marcador or e) else None
    if marc and marc.is_file():
        try:
            candidatos.append(json.loads(marc.read_text(encoding="utf-8")).get("date", ""))
        except (OSError, ValueError):
            pass
    modelo = step.reaproveita.replace("{date}", "@@")
    raiz = data_dir / modelo.split("@@")[0].rstrip("/")
    if raiz.is_dir():
        candidatos += sorted((p.name for p in raiz.iterdir() if p.is_dir() and p.name < date), reverse=True)
    for d in candidatos:
        if not d or d == date:
            continue
        origem = data_dir / modelo.replace("@@", d)
        if origem.is_file():
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origem, destino)
            return True, f"reaproveitado de {d}"
    return False, "nenhuma coleta anterior encontrada"


@dataclass
class EtapaRelatorio:
    id: str
    status: str
    politica: str
    inicio: Optional[str] = None
    fim: Optional[str] = None
    duracao_s: Optional[float] = None
    exit: Optional[int] = None
    motivo: Optional[str] = None
    tentativas: Optional[int] = None          # só quando a etapa foi tentada mais de uma vez
    publicados: Optional[list] = None         # arquivos copiados para published/ por `publicar:` da fonte
    versoes: Optional[list] = None            # versões de fonte registradas no armazém por esta etapa
    reutilizadas: Optional[list] = None       # versões do armazém restauradas no lugar da coleta (cadência)
    pico_mem_mb: Optional[int] = None         # maior RSS do processo da etapa entre as tentativas (base do `memoria_mb` do catálogo)


@dataclass
class Relatorio:
    date: str
    versao: str
    inicio: str
    fim: Optional[str] = None
    duracao_s: Optional[float] = None
    ok: Optional[bool] = None
    abortada_em: Optional[str] = None
    etapas: list[EtapaRelatorio] = field(default_factory=list)

    def para_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "etapas"}
        d["etapas"] = [{k: v for k, v in e.__dict__.items() if v is not None} for e in self.etapas]
        d["falhas_criticas"] = [e.id for e in self.etapas if e.status == FALHA and e.politica == "critica"]
        d["avisos"] = [e.id for e in self.etapas if e.status == FALHA and e.politica != "critica"]
        return d


def caminho_relatorio(data_dir: Path, date: str, continuo: bool = False) -> Path:
    """Relatório do dia; a trilha contínua (`arandu continuo`) grava o dela à parte, para não se misturar à retomada do pipeline."""
    return data_dir / "ops" / "runs" / ("continuo" if continuo else "") / f"{date}.json"


def ler_relatorio(data_dir: Path, date: str, continuo: bool = False) -> Optional[dict]:
    try:
        return json.loads(caminho_relatorio(data_dir, date, continuo).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def caminho_lock(data_dir: Path, continuo: bool = False) -> Path:
    """Lock do pipeline e, separado, o da trilha contínua: uma não espera a outra; duas instâncias da mesma trilha, nunca."""
    return data_dir / "ops" / ("arandu-continuo.lock" if continuo else "arandu.lock")


def restaurar_continua(cat: Catalog, step: Step, data_dir: Path, date: str) -> tuple[Optional[list], str]:
    """No pipeline, a etapa contínua não coleta: restaura na data a última versão que a trilha contínua registrou no armazém."""
    reus = reutilizar_versao(cat, step, data_dir, date)
    if reus:
        quando = ", ".join(sorted({r["as_of"][:10] for r in reus if r.get("as_of")}))
        return reus, f"coleta contínua (arandu continuo): restaurada a versão do armazém de {quando or '?'}"
    return None, "coleta contínua (arandu continuo): nenhuma versão no armazém; a etapa fica sem dado nesta data"


def publicar_fontes(cat: Catalog, step: Step, data_dir: Path, date: str, log: Callable[[str], None] = print) -> tuple[Optional[list], Optional[str]]:
    """`publicar:` das fontes da etapa: copia o normalizado para published/<data>/, de forma atômica. Devolve (arquivos, erro)."""
    saida = []
    for fid in step.fontes:
        src = cat.sources.get(fid)
        if not (src and src.publicar):
            continue
        de = data_dir / "normalized" / date / src.publicar.de
        para = data_dir / "published" / date / src.publicar.para
        if not de.is_file():
            return None, f"{fid}: {src.publicar.de} não foi gerado; nada a publicar"
        para.parent.mkdir(parents=True, exist_ok=True)
        tmp = para.with_name(para.name + ".tmp")
        shutil.copyfile(de, tmp)
        tmp.replace(para)
        saida.append(src.publicar.para)
        log(f"[{step.id}] publicado: {src.publicar.para}")
    return (saida or None), None


def registrar_versoes(cat: Catalog, step: Step, data_dir: Path, date: str, pipeline_version: str,
                      log: Callable[[str], None] = print) -> list[dict]:
    """Gravação dupla: depois que a coleta terminou, a versão da fonte entra no armazém. Falha aqui é aviso."""
    from core.store import registrar_da_fonte

    saida = []
    for fid in step.fontes:
        try:
            r = registrar_da_fonte(cat, data_dir, fid, date, pipeline_version=pipeline_version)
        except Exception as exc:  # noqa: BLE001 — o armazém é aditivo: não derruba a execução
            log(f"[{step.id}] AVISO: não registrou a versão de {fid} no armazém: {exc}")
            continue
        if r is not None:
            v, evento = r
            saida.append({"fonte": fid, "as_of": v.as_of, "versao": v.nome, "evento": evento})
    return saida


def planejar(cat: Catalog, only: Optional[Iterable[str]] = None) -> list[Step]:
    ordem = ordem_de_execucao(cat)
    sel = {id_de_etapa(x) for x in only} if only else None
    if sel:
        ruins = sel - set(cat.steps)
        if ruins:
            raise KeyError(f"etapa(s) inexistente(s): {', '.join(sorted(ruins))}")
    return [cat.steps[k] for k in ordem if sel is None or k in sel]


def etapas_de(cat: Catalog, alvo: str) -> list[str]:
    """Etapas que produzem uma fonte ou produto (para `arandu collect/build`)."""
    alvo = id_de_etapa(alvo)
    return [s.id for s in cat.steps.values() if alvo in s.fontes or alvo in s.produtos or alvo == s.id]


def etapa_sem_fonte(cat: Catalog, step: Step) -> bool:
    """Etapa que não coleta fonte (análise, produto, manifesto, histórico): a cadência por fonte não a gradua."""
    return not [f for f in step.fontes if f in cat.sources and cat.sources[f].tipo != "curada"]


def etapa_de_publicacao(cat: Catalog, step: Step, deps: dict[str, set[str]]) -> bool:
    """Etapa presa à janela de publicação: sem fonte, ou fonte derivada que lê a saída de uma etapa sem fonte
    (por exemplo `global_prefix_geo`, que depende de `bgp_ixp`). Fora da janela essa entrada não existe na data."""
    if etapa_sem_fonte(cat, step):
        return True
    # fonte bruta que grava direto em published/<data>/ (rpki_collector): fora da janela criaria uma pasta sem manifesto
    if any(f in cat.sources and cat.sources[f].tipo == "bruta" and cat.sources[f].saidas.publicado for f in step.fontes):
        return True
    return any(d in cat.steps and etapa_sem_fonte(cat, cat.steps[d]) for d in deps.get(step.id, set()))


# ── destinos, memória e paralelismo das coletas ─────────────────────────────────────────────────────────────────────────────────
# Cortesia por destino (regra do mantenedor): nunca duas consultas ao mesmo host ao mesmo tempo, nem entre o pipeline e a trilha
# contínua. Hosts diferentes podem ser consultados em paralelo, dentro do orçamento de memória do worker.

def destinos_da_etapa(cat: Catalog, step: Step) -> set[str]:
    """Hosts que a etapa consulta: os declarados em `destinos` mais o host do `origem.url` de cada fonte que ela produz.

    URL com molde (`telnet://lg.{ixp}.ix.br`) vira um destino só, com o molde no nome: conservador, nenhum par de PTTs em paralelo."""
    from urllib.parse import urlsplit

    hosts = {h.strip().lower() for h in step.destinos if h.strip()}
    for fid in step.fontes:
        src = cat.sources.get(fid)
        url = ((src.origem.url if src and src.origem else None) or "").strip()
        primeiro = url.split()[0] if url else ""
        if "://" not in primeiro:
            continue
        try:
            netloc = urlsplit(primeiro).netloc
        except ValueError:
            continue
        host = netloc.rsplit("@", 1)[-1].split(":")[0].strip().lower()
        if host:
            hosts.add(host)
    return hosts


def paralelizavel(cat: Catalog, step: Step, orcamento_mb: int) -> bool:
    """Pode rodar ao lado de outras: coleta pura (só fontes `bruta`, que declaram o que leem em `entradas`) do worker, com destino
    conhecido e pico de memória medido que cabe no orçamento. Derivadas e produtos ficam em série, na ordem do plano (o desempate da
    ordem cobre dependências que o catálogo não declara)."""
    fontes = [cat.sources.get(f) for f in step.fontes]
    return (step.runner == "worker" and step.memoria_mb is not None and step.memoria_mb <= orcamento_mb
            and bool(fontes) and all(f is not None and f.tipo == "bruta" for f in fontes)
            and bool(destinos_da_etapa(cat, step)))


def orcamento_memoria_mb(env: Optional[dict] = None) -> Optional[int]:
    """Memória para as etapas em paralelo: ARANDU_MEM_ORCAMENTO_MB ou 80% do teto do cgroup do contêiner; None se não se sabe."""
    env = os.environ if env is None else env
    v = str(env.get("ARANDU_MEM_ORCAMENTO_MB") or "").strip()
    if v.isdigit() and int(v) > 0:
        return int(v)
    for arq in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            txt = Path(arq).read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if txt.isdigit() and int(txt) < 1 << 50:            # "max" ou número astronômico = sem teto
            return int(int(txt) / 2**20 * 0.8)
    return None


def paralelo_do_ambiente(env: Optional[dict] = None) -> int:
    v = str((os.environ if env is None else env).get("ARANDU_PARALELO") or "").strip()
    return max(1, int(v)) if v.isdigit() else 1


@contextmanager
def travas_de_destino(data_dir: Path, hosts: set[str], sid: str, log: Callable[[str], None] = print):
    """flock por host em data/ops/destinos/: vale entre processos (pipeline e trilha contínua). Ordem fixa: sem impasse."""
    import fcntl

    abertos = []
    try:
        for h in sorted(hosts):
            arq = data_dir / "ops" / "destinos" / (re.sub(r"[^a-z0-9._-]", "_", h) + ".lock")
            arq.parent.mkdir(parents=True, exist_ok=True)
            f = open(arq, "a+")
            abertos.append(f)
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                log(f"[{sid}] aguardando o destino {h} (em uso por outra execução)")
                fcntl.flock(f, fcntl.LOCK_EX)
        yield
    finally:
        for f in abertos:
            try:
                fcntl.flock(f, fcntl.LOCK_UN)
            finally:
                f.close()


def em_paralelo(plano: list[Step], preparar, rodar, concluir, rel: "Relatorio", deps: dict[str, set[str]], elegivel, destinos,
                paralelo: int, orcamento_mb: int, estado: dict) -> None:
    """Agenda o plano com até `paralelo` etapas ao mesmo tempo.

    As etapas que não são `elegivel` rodam sozinhas, na ordem do plano, sempre que nada está rodando e uma delas está pronta. As
    `elegivel` (coleta pura, destino conhecido, memória medida) começam juntas quando não há dessas prontas: uma por destino, e a soma dos
    `memoria_mb` em curso nunca passa do orçamento. Toda etapa espera as dependências terminarem. As decisões (`preparar`, `concluir`) ficam na thread principal; só `rodar`
    vai para as threads. O relatório mantém a ordem do plano."""
    from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

    entradas = {s.id: EtapaRelatorio(id=s.id, status=PLANEJADA, politica=s.politica_falha) for s in plano}
    rel.etapas.extend(entradas[s.id] for s in plano)
    ids = {s.id for s in plano}
    dep = {s.id: deps.get(s.id, set()) & ids for s in plano}
    pendentes = list(plano)
    feitas: set[str] = set()
    rodando: dict = {}
    ocupados: set[str] = set()
    em_uso = 0

    def pronta(s: Step) -> bool:
        return dep[s.id] <= feitas

    def sozinha(s: Step) -> None:
        pendentes.remove(s)
        if preparar(s, entradas[s.id]):
            concluir(s, entradas[s.id], *rodar(s))
        feitas.add(s.id)

    def esperar() -> None:
        nonlocal em_uso
        prontos, _ = wait(list(rodando), return_when=FIRST_COMPLETED)
        for fut in prontos:
            s, mb, hs = rodando.pop(fut)
            em_uso -= mb
            ocupados.difference_update(hs)
            concluir(s, entradas[s.id], *fut.result())
            feitas.add(s.id)

    with ThreadPoolExecutor(max_workers=paralelo, thread_name_prefix="etapa") as pool:
        while pendentes or rodando:
            if estado["abortada"]:                      # nada novo começa; o que está rodando termina
                if rodando:
                    esperar()
                    continue
                for s in list(pendentes):
                    sozinha(s)                           # preparar marca como não executada
                continue
            if not rodando:                              # as que não podem ter companhia vão primeiro, enquanto nada roda
                excl = next((s for s in pendentes if not elegivel(s) and pronta(s)), None)
                if excl is not None:
                    sozinha(excl)
                    continue
            lancou = False
            for s in list(pendentes):
                if estado["abortada"] or len(rodando) >= paralelo:
                    break
                if not (elegivel(s) and pronta(s)):
                    continue
                hs, mb = destinos(s), int(s.memoria_mb or 0)
                if hs & ocupados or em_uso + mb > orcamento_mb:
                    continue
                pendentes.remove(s)
                lancou = True
                if not preparar(s, entradas[s.id]):
                    feitas.add(s.id)
                    continue
                ocupados.update(hs)
                em_uso += mb
                rodando[pool.submit(rodar, s)] = (s, mb, hs)
            if lancou:
                continue
            if rodando:
                esperar()
                continue
            alvo = next((s for s in pendentes if pronta(s)), None)
            if alvo is None:                             # não acontece num plano em ordem topológica; melhor falhar alto que travar
                raise RuntimeError("agendamento sem progresso: " + ", ".join(s.id for s in pendentes))
            sozinha(alvo)


def executar(cat: Catalog, date: str, data_dir: Path, runner, *, only: Optional[Iterable[str]] = None,
             due: bool = False, retomar: bool = False, pin_sources: bool = False, dry_run: bool = False, force: bool = False, versao: str = "desconhecida",
             publicar: bool = False, continuo: bool = False, paralelo: int = 1, orcamento_mem_mb: Optional[int] = None,
             log: Callable[[str], None] = print, env: Optional[dict] = None, usar_lock: bool = True,
             gravar_relatorio: bool = True, sleep: Callable[[float], None] = time.sleep) -> Relatorio:
    plano = planejar(cat, only)
    if continuo:                       # trilha contínua: só as etapas `continua`, sempre (o rodízio de cada uma decide o que ler)
        plano = [s for s in plano if s.continua]
    explicito = bool(only) or continuo
    rel = Relatorio(date=date, versao=versao, inicio=agora())
    anterior = ler_relatorio(data_dir, date, continuo) if (retomar and not force) else None
    ok_antes = {id_de_etapa(e["id"]) for e in (anterior or {}).get("etapas", []) if e.get("status") in (OK, RETOMADA)}
    executadas: set[str] = set()
    refeitas: set[str] = set()         # etapas executadas nesta rodada: tudo que depende delas precisa ser refeito
    deps = dependencias_de_etapas(cat)
    path = caminho_relatorio(data_dir, date, continuo)
    t0 = time.time()

    def salvar():
        if gravar_relatorio and not dry_run:
            _escreve_atomico(path, json.dumps(rel.para_dict(), ensure_ascii=False, indent=2) + "\n")

    estado = {"abortada": False}

    def abortar(s: Step) -> None:
        estado["abortada"] = True
        rel.abortada_em = s.id

    def preparar(s: Step, e: EtapaRelatorio) -> bool:
        """Decide a etapa sem rodá-la (pular, restaurar, retomar, dry-run). True = tem de rodar. Só na thread principal."""
        if estado["abortada"]:
            e.status, e.motivo = NAO_EXECUTADA, f"execução abortada em {rel.abortada_em}"
            return False
        if s.runner == "host":
            e.status, e.motivo = DELEGADA, "etapa de host (compose/shell): roda em scripts/host-steps.sh"
            return False
        if s.continua and not explicito:
            reus, porque = (None, "coleta contínua: roda em arandu continuo") if dry_run else restaurar_continua(cat, s, data_dir, date)
            e.status, e.motivo, e.reutilizadas = PULADA, porque, reus
            if not dry_run:
                log(f"[{s.id}] {porque}")
                salvar()
            return False
        if s.so_com_only and not explicito:
            e.status, e.motivo = PULADA, "etapa manual: só roda com --only"
            return False
        if s.somente_se_executou and not explicito and not all(x in executadas for x in s.somente_se_executou):
            e.status, e.motivo = PULADA, "etapa de que depende não rodou nesta execução"
            return False
        if retomar and s.id in ok_antes and not explicito:
            refez = sorted(deps.get(s.id, set()) & refeitas)
            if not refez:
                e.status, e.motivo = RETOMADA, "já concluída neste dia"
                executadas.add(s.id)
                return False
            e.motivo = f"concluída antes, mas refeita porque {', '.join(refez)} foi(ram) executada(s) de novo"
        if pin_sources and s.fontes and not explicito:
            try:
                e.reutilizadas = restaurar_pins(cat, s, data_dir, date) or None
            except FileNotFoundError as exc:
                e.status, e.motivo, e.exit = FALHA, str(exc), 1
                if s.politica_falha == "critica":
                    abortar(s)
                return False
            e.status, e.motivo = PULADA, "versão fixada pelo manifesto (--pin-sources)"
            return False
        if due and not explicito and not publicar and etapa_de_publicacao(cat, s, deps):
            aberta, porque = publicacao.janela_aberta(data_dir, date, env)
            if not aberta:       # coleta por fonte todo dia, snapshot só a cada N dias
                e.status, e.motivo = PULADA, porque
                return False
        if due and not explicito:
            devida, porque = devida_por_cadencia(cat, s, data_dir, date, env)
            if not devida:
                reus = [] if dry_run else reutilizar_versao(cat, s, data_dir, date)
                if reus or dry_run or not s.fontes:
                    e.status, e.motivo = PULADA, porque
                    e.reutilizadas = reus or None
                    if reus and not dry_run:
                        salvar()
                    return False
                # nada no armazém para reutilizar: a etapa roda mesmo fora da cadência
                e.motivo = f"{porque}; sem versão para reutilizar — executada"
        if not explicito and not due:
            devida, porque = vencida(s, data_dir, date, env)
            if not devida:
                e.status, e.motivo = PULADA, porque
                if s.reaproveita and not dry_run:
                    feito, msg = reaproveitar(s, data_dir, date)
                    e.motivo = f"{porque}; {msg}"
                return False
        if dry_run:
            e.status, e.motivo = PLANEJADA, "dry-run"
            return False
        log(f"[{s.id}] {s.nome}...")
        e.inicio = agora()
        return True

    def rodar(s: Step) -> tuple:
        """Roda a etapa com as tentativas, sob o lock dos destinos dela. Pode ir para uma thread: não mexe no relatório."""
        t = time.time()
        with travas_de_destino(data_dir, destinos_da_etapa(cat, s), s.id, log):
            bloqueio = bloqueada_por_disco(s, data_dir)
            r = Resultado(75, bloqueio) if bloqueio else runner.run(s, date)
            picos = [r.pico_mem_mb]
            n = 1
            while r.rc != 0 and not bloqueio and n < s.tentativas:      # disco cheio não melhora esperando
                log(f"[{s.id}] tentativa {n}/{s.tentativas} falhou ({r.motivo}); nova tentativa em {s.espera_s} s")
                sleep(s.espera_s)
                n += 1
                r = runner.run(s, date)
                picos.append(r.pico_mem_mb)
        return r, n, picos, round(time.time() - t, 1)

    def concluir(s: Step, e: EtapaRelatorio, r: Resultado, n: int, picos: list, duracao: float) -> None:
        """Status, publicação, armazém e política de falha. Só na thread principal."""
        if n > 1:
            e.tentativas = n
        e.pico_mem_mb = max((p for p in picos if p is not None), default=None)
        e.fim, e.duracao_s, e.exit = agora(), duracao, r.rc
        if r.rc == 0:
            e.status = OK
            executadas.add(s.id)
            refeitas.add(s.id)
            e.publicados, erro_pub = publicar_fontes(cat, s, data_dir, date, log)
            if erro_pub:
                e.status, e.motivo = FALHA, erro_pub
                if s.politica_falha == "critica":
                    abortar(s)
                salvar()
                return
            e.versoes = registrar_versoes(cat, s, data_dir, date, versao, log) or None
            if s.gravar_marcador:
                _escreve_atomico(data_dir / s.gravar_marcador, json.dumps({"date": date}))
        else:
            e.status, e.motivo = FALHA, r.motivo
            if s.politica_falha == "usar_ultima_valida":
                feito, msg = reaproveitar(s, data_dir, date)
                e.motivo = f"{r.motivo}; {msg}"
                log(f"[{s.id}] AVISO: falhou; {msg}")
            elif s.politica_falha == "critica":
                abortar(s)
                log(f"[{s.id}] ERRO: etapa crítica falhou — execução abortada")
            else:
                log(f"[{s.id}] AVISO: falhou ({r.motivo}) — etapa opcional, segue")
            if s.politica_falha == "opcional" and not dry_run:
                # o manifesto declara a última versão boa do armazém para esta fonte: o arquivo tem de estar na data
                # (sem isso, cabos e linhas de transmissão somem do snapshot)
                reus = reutilizar_versao(cat, s, data_dir, date)
                if reus:
                    e.reutilizadas = reus
                    log(f"[{s.id}] AVISO: usando a versão do armazém de {reus[0]['as_of']}")
        salvar()

    def sequencial():
        for s in plano:
            e = EtapaRelatorio(id=s.id, status=PLANEJADA, politica=s.politica_falha)
            rel.etapas.append(e)
            if preparar(s, e):
                concluir(s, e, *rodar(s))

    def corpo():
        orc = orcamento_mem_mb if orcamento_mem_mb is not None else orcamento_memoria_mb(env)
        if paralelo > 1 and not dry_run and orc:
            log(f"[arandu] coletas em paralelo: até {paralelo} ao mesmo tempo, orçamento de memória {orc} MB, uma por destino")
            em_paralelo(plano, preparar, rodar, concluir, rel, deps, lambda s: paralelizavel(cat, s, orc),
                        lambda s: destinos_da_etapa(cat, s), paralelo, orc, estado)
        else:
            if paralelo > 1 and not dry_run:
                log("[arandu] paralelo pedido, mas sem orçamento de memória (ARANDU_MEM_ORCAMENTO_MB ou teto do cgroup): roda em série")
            sequencial()
        return None

    if usar_lock and not dry_run:
        with lock(caminho_lock(data_dir, continuo)):
            corpo()
    else:
        corpo()
    rel.fim = agora()
    rel.duracao_s = round(time.time() - t0, 1)
    rel.ok = rel.abortada_em is None
    salvar()
    if gravar_relatorio and not dry_run:      # o relatório do dia é sobrescrito a cada execução: guarda também o histórico
        hist = path.parent / "history" / f"{date}T{rel.inicio[11:19].replace(':', '')}.json"
        _escreve_atomico(hist, json.dumps(rel.para_dict(), ensure_ascii=False, indent=2) + "\n")
        os.chmod(hist, 0o644)
    return rel
