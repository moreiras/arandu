# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""RDAP do Registro.br: contatos administrativo e de abuso dos ASNs do Brasil, em rodízio lento.

`GET https://rdap.registro.br/autnum/{asn}`. Medido: sob ritmo alto a resposta vem INCOMPLETA, sem aviso e com
HTTP 200 (sem os e-mails, ~150 B menor); em rajada o servidor fecha a conexão. Por isso este coletor:

- consulta um ASN por vez, no ritmo medido (`RDAP_INTERVALO_S`), nunca em paralelo;
- confere a completude de CADA resposta (`administrative` e `abuse` com e-mail). Incompleta não conta como leitura válida: guarda-se a tentativa e a
  leitura válida anterior (se houver) continua valendo; a reconsulta fica para depois dos ASNs nunca lidos e dos de leitura mais antiga;
- detecta degradação pela janela das últimas respostas (metade ou mais incompletas) e recua (dobra o intervalo); persistindo, encerra a rodada;
- conexão derrubada, 429/403 ou falhas seguidas encerram a rodada (nada de contornar bloqueio). Em 404 o ASN não tem registro (leitura válida, sem contatos);
- sem e-mail confirmado: um ASN que vem incompleto duas vezes com a fonte "saudável" (janela sem degradação) passa a `parcial_confirmado`.

Guarda o mínimo: papel, e-mail e `handle` do contato. Sem nome, endereço, telefone nem `legalRepresentative`.

DADO DE CONTATO: o arquivo fica em `normalized/` (nunca copiado para `published/`) e só é servido ao usuário logado (`/asns/{asn}/contacts`);
nunca em rota pública nem no MCP. Nenhum e-mail vai para log.

Universo: ASNs de `normalized/{data}/summary/orgs.json.gz` (Registro.br). Estado do rodízio: o `rdap_contatos.json.gz` da rodada anterior.
Normalizado: data/normalized/{date}/summary/rdap_contatos.json.gz

Uso:
    python -m sources.rdap_contatos.collect --date 2026-11-10 [--asns 700] [--intervalo 12]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import deque
from pathlib import Path
from typing import Callable, Optional

import httpx

from core import rodizio
from core.common import configure_logging, data_dir, normalized_path, now_iso, read_json_gz, today_str, write_json_gz
from core.site import USER_AGENT

BASE_URL = "https://rdap.registro.br/autnum/"
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/rdap+json"}
PAPEIS = ("administrative", "abuse")
INTERVALO_S = 12.0                 # medido: 10 s deu 100% completas; 12 s por segurança; sobrescreve com RDAP_INTERVALO_S
ASNS_POR_EXECUCAO = 700
TEMPO_MAX_S = 3 * 3600
JANELA = 10                        # respostas recentes que decidem se a fonte está degradando
JANELA_MIN = 5
DEGRADA_FRACAO = 0.5
RECUOS_MAX = 2                     # dobra o intervalo até 2 vezes (4x); depois encerra
CONFIRMA_PARCIAL = 2               # incompletas "saudáveis" para aceitar que o ASN não tem e-mail
CHECKPOINT_A_CADA = 50
ARQUIVO = "rdap_contatos.json.gz"


class Bloqueio(RuntimeError):
    """429/403 do servidor: parar e não insistir."""


def _emails(entidade: dict) -> list[str]:
    vcard = entidade.get("vcardArray")
    props = vcard[1] if isinstance(vcard, list) and len(vcard) > 1 and isinstance(vcard[1], list) else []
    saida: list[str] = []
    for p in props:
        if isinstance(p, list) and len(p) >= 4 and p[0] == "email" and isinstance(p[3], str) and "@" in p[3]:
            saida.append(p[3].strip().lower())
    return saida


def _percorre(entidades: list, achados: dict) -> None:
    for e in entidades or []:
        if not isinstance(e, dict):
            continue
        for papel in e.get("roles") or []:
            if papel in PAPEIS:
                achados.setdefault(papel, []).append(e)
        _percorre(e.get("entities") or [], achados)


def extrair(resposta: object) -> Optional[dict]:
    """Reduz a resposta RDAP de `autnum` ao recorte mínimo: {"contatos": [{papel, email, handle}], "completo": bool}.

    None se o JSON não é um `autnum` RDAP (erro, página de manutenção). Entidade aninhada (o administrativo costuma vir dentro do `registrant`) conta.
    Completo = os dois papéis (`administrative`, `abuse`) com ao menos um e-mail."""
    if not isinstance(resposta, dict) or resposta.get("objectClassName") != "autnum":
        return None
    achados: dict[str, list[dict]] = {}
    _percorre(resposta.get("entities") or [], achados)
    contatos: list[dict] = []
    for papel in PAPEIS:
        vistos: set[str] = set()
        for e in achados.get(papel, []):
            for mail in _emails(e):
                if mail not in vistos:
                    vistos.add(mail)
                    contatos.append({"papel": papel, "email": mail, "handle": e.get("handle") or None})
    completo = all(any(c["papel"] == p for c in contatos) for p in PAPEIS)
    return {"contatos": contatos, "completo": completo}


class Saude:
    """Janela das últimas respostas: a fonte está degradando quando metade ou mais veio incompleta."""

    def __init__(self, tamanho: int = JANELA, minimo: int = JANELA_MIN, fracao: float = DEGRADA_FRACAO):
        self.janela: deque[bool] = deque(maxlen=tamanho)
        self.minimo, self.fracao = minimo, fracao

    def registra(self, completa: bool) -> None:
        self.janela.append(completa)

    def degradada(self) -> bool:
        return len(self.janela) >= self.minimo and sum(1 for c in self.janela if not c) / len(self.janela) >= self.fracao

    def saudavel(self) -> bool:
        """Há evidência de que a fonte responde bem: janela cheia o bastante e quase toda completa (≥ 80 %). Sem evidência, não é saudável."""
        return len(self.janela) >= self.minimo and sum(1 for c in self.janela if not c) / len(self.janela) <= 0.2

    def limpa(self) -> None:
        self.janela.clear()


def _salva_atomico(destino: Path, doc: dict) -> None:
    tmp = destino.with_name(destino.name + ".tmp")
    write_json_gz(tmp, doc)
    os.replace(tmp, destino)


def _anterior(base: Path, date_str: str) -> dict:
    return rodizio.anterior_normalizado(base, date_str, ARQUIVO, incluir_data=True)


def _universo(base: Path, date_str: str) -> list[int]:
    """ASNs do Registro.br: o `orgs.json.gz` mais recente até a data."""
    raiz = base / "normalized"
    if not raiz.is_dir():
        return []
    for d in sorted((p.name for p in raiz.iterdir() if p.is_dir() and p.name <= date_str), reverse=True):
        arq = raiz / d / "summary" / "orgs.json.gz"
        if arq.is_file():
            return sorted(int(a) for a in read_json_gz(arq).get("orgs", {}))
    return []


def vez_do_rodizio(asns: list[int], lidos: dict, limite: int) -> list[int]:
    """Nunca consultados primeiro; depois pela data da última tentativa ou leitura (a mais antiga). Incompleto fica atrás dos nunca vistos."""
    def idade(a: int) -> Optional[str]:
        v = lidos.get(str(a)) or {}
        return max(v.get("em") or "", v.get("tentou_em") or "") or None
    return rodizio.escolher_por_idade(asns, idade, limite)


def consulta(client: httpx.Client, asn: int) -> tuple[str, Optional[dict]]:
    """Uma consulta. Devolve (situação, recorte): 'ok' (recorte), 'nao_encontrado' (404), 'invalida' (200 sem autnum RDAP).
    Levanta `Bloqueio` em 429/403 e `httpx.HTTPError` em falha de rede (inclui conexão fechada sem resposta)."""
    r = client.get(BASE_URL + str(asn))
    if r.status_code in (403, 429):
        raise Bloqueio(f"HTTP {r.status_code} em autnum")
    if r.status_code == 404:
        return "nao_encontrado", None
    r.raise_for_status()
    try:
        recorte = extrair(r.json())
    except json.JSONDecodeError:
        recorte = None
    return ("ok", recorte) if recorte is not None else ("invalida", None)


def run(date_str: str, base: Path, log, asns_por_execucao: Optional[int] = None, intervalo_s: Optional[float] = None, tempo_max_s: Optional[float] = None,
        client: Optional[httpx.Client] = None, relogio: Callable[[], float] = time.monotonic, dormir: Callable[[float], None] = time.sleep) -> dict:
    limite = asns_por_execucao or int(os.environ.get("RDAP_ASNS_POR_EXECUCAO") or ASNS_POR_EXECUCAO)
    intervalo = float(intervalo_s if intervalo_s is not None else (os.environ.get("RDAP_INTERVALO_S") or INTERVALO_S))
    tempo_max = float(tempo_max_s if tempo_max_s is not None else (os.environ.get("RDAP_TEMPO_MAX_S") or TEMPO_MAX_S))
    asns = _universo(base, date_str)
    if not asns:
        raise RuntimeError("rdap_contatos: sem orgs.json.gz (universo de ASNs do Registro.br)")
    antes = _anterior(base, date_str)
    vivos = set(asns)
    lidos: dict[str, dict] = {k: v for k, v in (antes.get("contatos") or {}).items() if int(k) in vivos}
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    arquivo = destino / ARQUIVO
    lim = rodizio.Limitador(intervalo, relogio=relogio, dormir=dormir)
    orc = rodizio.Orcamento(requisicoes=limite, tempo_max_s=tempo_max, falhas_seguidas_max=3, relogio=relogio)
    saude = Saude()
    recuos = 0
    motivo: Optional[str] = None
    proprio = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(30, read=60), headers=HEADERS, follow_redirects=False)
    cont = {"validas": 0, "incompletas": 0, "nao_encontrado": 0, "invalidas": 0, "confirmadas_sem_email": 0}

    def grava(parcial: bool) -> None:
        _salva_atomico(arquivo, _documento(date_str, asns, lidos, {**cont, **orc.resumo(), "intervalo_s": lim.intervalo_s, "recuos": recuos, "parou": motivo, "parcial": parcial}))

    try:
        for asn in vez_do_rodizio(asns, lidos, limite):
            motivo = orc.motivo_parada()
            if motivo:
                break
            lim.esperar()
            orc.gastar()
            chave = str(asn)
            try:
                situacao, rec = consulta(client, asn)
            except Bloqueio as exc:
                motivo = f"sinal de bloqueio: {exc}"
                break
            except httpx.HTTPError as exc:
                orc.falha()
                saude.registra(False)
                log.warning("rdap_contatos: falha de rede", erro=type(exc).__name__, falhas_seguidas=orc.falhas_seguidas)
                if recuos < RECUOS_MAX:                     # conexão derrubada sob ritmo alto: recua antes do próximo
                    recuos += 1
                    lim.intervalo_s *= 2
                    log.warning("rdap_contatos: recuo", intervalo_s=lim.intervalo_s)
                continue
            orc.sucesso()
            ant = lidos.get(chave) or {}
            if situacao == "nao_encontrado":
                lidos[chave] = {"em": date_str, "tentou_em": date_str, "status": "nao_encontrado", "contatos": [], "incompletas": 0}
                cont["nao_encontrado"] += 1
            elif situacao == "invalida":
                cont["invalidas"] += 1
                saude.registra(False)
                lidos[chave] = {"em": ant.get("em"), "tentou_em": date_str, "status": ant.get("status") or "incompleto", "contatos": ant.get("contatos") or [],
                                "incompletas": ant.get("incompletas", 0)}
            elif rec["completo"]:
                saude.registra(True)
                lidos[chave] = {"em": date_str, "tentou_em": date_str, "status": "completo", "contatos": rec["contatos"], "incompletas": 0}
                cont["validas"] += 1
            else:
                saudavel = saude.saudavel()
                saude.registra(False)
                cont["incompletas"] += 1
                n = ant.get("incompletas", 0) + (1 if saudavel else 0)
                if saudavel and n >= CONFIRMA_PARCIAL:
                    # a fonte respondia bem e o ASN continua sem os dois e-mails: ausência real, não degradação
                    lidos[chave] = {"em": date_str, "tentou_em": date_str, "status": "parcial_confirmado", "contatos": rec["contatos"], "incompletas": n}
                    cont["confirmadas_sem_email"] += 1
                else:
                    # NÃO é leitura válida: mantém a anterior (com a data dela) e só anota a tentativa
                    lidos[chave] = {"em": ant.get("em"), "tentou_em": date_str, "status": ant.get("status") or "incompleto", "contatos": ant.get("contatos") or [], "incompletas": n}
            if saude.degradada():
                if recuos >= RECUOS_MAX:
                    motivo = f"degradação persistente mesmo a {lim.intervalo_s:g} s entre consultas"
                    break
                recuos += 1
                lim.intervalo_s *= 2
                saude.limpa()
                log.warning("rdap_contatos: degradação, recuo", intervalo_s=lim.intervalo_s)
            if orc.gastas % CHECKPOINT_A_CADA == 0:
                grava(True)
    finally:
        if proprio:
            client.close()
    grava(False)
    medicao = {**cont, **orc.resumo(), "limite": limite, "intervalo_s": lim.intervalo_s, "recuos": recuos, "parou": motivo, "asns_no_universo": len(asns),
               "com_leitura_valida": sum(1 for v in lidos.values() if v.get("em"))}
    log.info("rdap_contatos written", **medicao)
    return medicao


def _documento(date_str: str, asns: list[int], lidos: dict, execucao: dict) -> dict:
    validos = [v for v in lidos.values() if v.get("em")]
    datas = sorted(v["em"] for v in validos)
    return {
        "snapshot_date": date_str, "fetched_at": now_iso(), "fonte": BASE_URL, "dado_de_contato": True,
        "aviso": "DADO DE CONTATO: só para usuário logado; nunca em rota pública nem no MCP; não copiar para published/.",
        "cobertura": {"asns_no_universo": len(asns), "com_leitura_valida": len(validos), "completos": sum(1 for v in validos if v.get("status") == "completo"),
                      "parcial_confirmado": sum(1 for v in validos if v.get("status") == "parcial_confirmado"),
                      "nao_encontrado": sum(1 for v in validos if v.get("status") == "nao_encontrado"),
                      "so_incompletos": sum(1 for v in lidos.values() if not v.get("em")),
                      "leitura_mais_antiga": datas[0] if datas else None, "leitura_mais_recente": datas[-1] if datas else None},
        "contatos": dict(sorted(lidos.items(), key=lambda kv: int(kv[0]))), "ultima_execucao": execucao,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="RDAP do Registro.br: contatos dos ASNs do Brasil (rodízio lento, verifica a completude de cada resposta)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre incremental")
    p.add_argument("--asns", type=int, default=None, help="consultas nesta execução (padrão: RDAP_ASNS_POR_EXECUCAO ou %d)" % ASNS_POR_EXECUCAO)
    p.add_argument("--intervalo", type=float, default=None, help="segundos entre consultas (padrão: RDAP_INTERVALO_S ou %g)" % INTERVALO_S)
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        print(run(a.date, data_dir(), log, asns_por_execucao=a.asns, intervalo_s=a.intervalo))
    except Exception:
        log.exception("falha na coleta de rdap_contatos")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
