# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Shodan, exposição de serviços por ASN: só CONTAGENS, em rodízio.

`GET https://api.shodan.io/shodan/host/count?key=...&query=...&facets=...`: segundo a documentação (developer.shodan.io/api, lida em 2026-11-10), devolve só contagens (sem listar hosts) e "não consome créditos de consulta";
a página NÃO informa o limite de taxa nem quais filtros/facetas exigem plano pago, e diz que o método "se comporta como" a busca (que gasta 1 crédito com filtro). Por isso a rodada confere `/api-info` antes e depois das 10 primeiras
leituras e PARA se os créditos de consulta caírem.
Por ASN do Brasil, até três consultas:
  A. `asn:AS<N>` com a faceta `port:20`: total de serviços observados e as portas mais vistas;
  B. `asn:AS<N> port:<portas de risco>` com a faceta `port`: contagem EXATA de cada porta de risco (a faceta da consulta A só traz o topo e perderia as raras); só se A > 0;
  C. `asn:AS<N>` com a faceta `vuln:20` (CVEs): só se o plano da conta permitir. A indisponibilidade é registrada ("não disponível no plano") e a faceta só é reexperimentada depois de 30 dias.

NUNCA lista de IPs nem host individual. Ausência não é zero: ASN sem leitura é "não consultado"; total 0 é "o Shodan não observou serviço", não "não tem serviço".

Chave só do ambiente (`SHODAN_API_KEY`, que o compose preenche com `SHODAN`); a API do Shodan a exige na querystring, então NENHUMA URL, exceção ou resposta é logada (o log do `httpx` é calado) e
o arquivo gravado não a contém. Uma consulta por vez, intervalo de `SHODAN_INTERVALO_S` (padrão 1,1 s: 1 requisição/s é a prática conhecida da API, a confirmar na sondagem), recuo em 429, para em 401.

`--sondar` mede, na conta real, o que o plano permite (facetas e filtros), os créditos (`/api-info` antes e depois), o tempo por consulta e quantos ASNs têm contagem. Imprime só números.

Estado do rodízio: o `shodan_exposicao.json.gz` da rodada anterior. Normalizado: data/normalized/{date}/summary/shodan_exposicao.json.gz

Uso:
    python -m sources.shodan_exposicao.collect --date 2026-11-10 [--asns 1500] [--intervalo 1.1]
    python -m sources.shodan_exposicao.collect --sondar [--amostra 60] [--saida sondagem.json]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
import time
from datetime import date as _date
from pathlib import Path
from typing import Callable, Optional

import httpx

from core import rodizio, shodan
from core.common import configure_logging, data_dir, normalized_path, now_iso, read_json_gz, today_str, write_json_gz
from core.site import USER_AGENT

HEADERS = {"User-Agent": USER_AGENT}
INTERVALO_S = 1.1
CONFERE_CREDITOS_APOS = 10       # leituras de ASN até reler `/api-info`; créditos de consulta menores que no início = a consulta custa, parar
ASNS_POR_EXECUCAO = 1500
TEMPO_MAX_S = 2 * 3600
VULN_REEXPERIMENTA_DIAS = 30
CHECKPOINT_A_CADA = 100
ARQUIVO = "shodan_exposicao.json.gz"
UA_SONDAGEM = {"User-Agent": f"{USER_AGENT} medicao-pesquisa"}     # a sondagem também identifica a instância

logging.getLogger("httpx").setLevel(logging.WARNING)       # o httpx loga a URL da requisição, e a URL do Shodan carrega a chave
logging.getLogger("httpcore").setLevel(logging.WARNING)


class ChaveInvalida(RuntimeError):
    """401 da API na consulta principal: chave ausente, inválida ou revogada. Não adianta continuar."""


class PlanoNaoPermite(RuntimeError):
    """A consulta/faceta exige plano pago (4xx com `error`): não é falha da rodada."""


class Limite(RuntimeError):
    """429 persistente: parar a rodada."""


def _get(client: httpx.Client, caminho: str, params: dict, chave: str, espera_429_s: float = 5.0, dormir: Callable[[float], None] = time.sleep, limitador: Optional[rodizio.Limitador] = None) -> dict:
    """GET com a chave na querystring. Devolve o JSON. 401 → `ChaveInvalida`; outro 4xx → `PlanoNaoPermite` (a mensagem do Shodan, sem URL); 429 → 2 tentativas, depois `Limite`;
    5xx e erro de rede → `httpx.HTTPError` (a mensagem das exceções do httpx traz a URL: quem captura NUNCA a registra)."""
    for tentativa in range(3):
        if limitador is not None:      # intervalo mínimo em CADA requisição (só entre ASNs, as 3 consultas de um ASN sairiam em rajada e dariam 429)
            limitador.esperar()
        r = client.get(shodan.BASE_URL + caminho, params={**params, "key": chave})
        if r.status_code == 429:
            if tentativa == 2:
                raise Limite("HTTP 429 persistente")
            dormir(min(float(r.headers.get("Retry-After", espera_429_s) or espera_429_s), 60) * (tentativa + 1))
            continue
        if r.status_code >= 500:
            raise httpx.HTTPError(f"HTTP {r.status_code}")
        try:
            corpo = r.json()
        except json.JSONDecodeError:
            corpo = {}
        if r.status_code == 401:
            raise ChaveInvalida(str((corpo or {}).get("error") or "HTTP 401")[:200])
        if r.status_code >= 400:
            raise PlanoNaoPermite(f"HTTP {r.status_code}: {str((corpo or {}).get('error') or '')[:200]}")
        return corpo if isinstance(corpo, dict) else {}
    raise Limite("HTTP 429 persistente")


def contar(client: httpx.Client, consulta: str, facetas: Optional[str], chave: str, **kw) -> dict:
    p = {"query": consulta}
    if facetas:
        p["facets"] = facetas
    return _get(client, "/shodan/host/count", p, chave, **kw)


def leitura_do_asn(client: httpx.Client, asn: int, chave: str, vuln: str, cont: Optional[dict] = None, **kw) -> tuple[dict, str]:
    """Consultas A, B e C de um ASN. Devolve (leitura sem a data, situação da faceta `vuln`: 'ok', 'indisponivel' ou a recebida se C não foi tentada)."""
    def n(k: str = "requisicoes") -> None:
        if cont is not None:
            cont[k] = cont.get(k, 0) + 1
    n()
    a = contar(client, shodan.CONSULTA_GERAL.format(asn=asn), f"port:{shodan.TOP_PORTAS}", chave, **kw)
    total = shodan.numero(a.get("total")) or 0
    leitura: dict = {"total": total, "portas": [[shodan.numero(x["value"]), shodan.numero(x["count"])] for x in shodan.faceta(a, "port")[: shodan.TOP_PORTAS]
                                                  if shodan.numero(x.get("value")) is not None], "risco": {}, "risco_total": 0, "vulns": None}
    if total <= 0:
        return leitura, vuln
    n()
    b = contar(client, shodan.CONSULTA_RISCO.format(asn=asn), f"port:{len(shodan.PORTAS_DE_RISCO)}", chave, **kw)
    leitura["risco_total"] = shodan.numero(b.get("total")) or 0
    leitura["risco"] = {str(p): c for p, c in ((shodan.numero(x.get("value")), shodan.numero(x.get("count"))) for x in shodan.faceta(b, "port"))
                        if p in shodan.PORTAS_DE_RISCO and c}
    if vuln != "indisponivel":
        n()
        try:
            c = contar(client, shodan.CONSULTA_GERAL.format(asn=asn), f"vuln:{shodan.TOP_VULNS}", chave, **kw)
            leitura["vulns"] = [[str(x["value"]), shodan.numero(x["count"])] for x in shodan.faceta(c, "vuln")[: shodan.TOP_VULNS]]
            vuln = "ok"
        except PlanoNaoPermite:
            vuln = "indisponivel"
    return leitura, vuln


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


def _salva_atomico(destino: Path, doc: dict) -> None:
    tmp = destino.with_name(destino.name + ".tmp")
    write_json_gz(tmp, doc)
    os.replace(tmp, destino)


def _documento(date_str: str, asns: list[int], lidos: dict, plano: dict, execucao: dict) -> dict:
    datas = sorted(v["em"] for v in lidos.values() if v.get("em"))
    return {"snapshot_date": date_str, "fetched_at": now_iso(), "fonte": shodan.BASE_URL + "/shodan/host/count", "licenca": shodan.LICENCA, "atribuicao": shodan.ATRIBUICAO,
            "plano": plano, "consultas": {"geral": shodan.CONSULTA_GERAL, "risco": shodan.CONSULTA_RISCO}, "asns_no_universo": len(asns),
            "cobertura": {"com_leitura": len(lidos), "com_servicos": sum(1 for v in lidos.values() if v.get("total")), "leitura_mais_antiga": datas[0] if datas else None,
                          "leitura_mais_recente": datas[-1] if datas else None},
            "asns": dict(sorted(lidos.items(), key=lambda kv: int(kv[0]))), "ultima_execucao": execucao}


def run(date_str: str, base: Path, log, asns_por_execucao: Optional[int] = None, intervalo_s: Optional[float] = None, tempo_max_s: Optional[float] = None,
        chave: Optional[str] = None, client: Optional[httpx.Client] = None, relogio: Callable[[], float] = time.monotonic, dormir: Callable[[float], None] = time.sleep) -> dict:
    chave = chave if chave is not None else os.environ.get("SHODAN_API_KEY", "")
    if not chave:
        raise ChaveInvalida("SHODAN_API_KEY ausente do ambiente")
    limite = asns_por_execucao or int(os.environ.get("SHODAN_ASNS_POR_EXECUCAO") or ASNS_POR_EXECUCAO)
    intervalo = float(intervalo_s if intervalo_s is not None else (os.environ.get("SHODAN_INTERVALO_S") or INTERVALO_S))
    tempo_max = float(tempo_max_s if tempo_max_s is not None else (os.environ.get("SHODAN_TEMPO_MAX_S") or TEMPO_MAX_S))
    asns = _universo(base, date_str)
    if not asns:
        raise RuntimeError("shodan_exposicao: sem orgs.json.gz (universo de ASNs do Registro.br)")
    antes = rodizio.anterior_normalizado(base, date_str, ARQUIVO, incluir_data=True)
    lidos: dict[str, dict] = {k: v for k, v in (antes.get("asns") or {}).items() if int(k) in set(asns)}
    plano = dict((antes.get("plano") or {}).get("facetas") or {})
    vuln = plano.get("vuln") or "nao_testada"
    if vuln == "indisponivel" and plano.get("vuln_testada_em") and (_date.fromisoformat(date_str) - _date.fromisoformat(plano["vuln_testada_em"])).days >= VULN_REEXPERIMENTA_DIAS:
        vuln = "nao_testada"
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    arquivo = destino / ARQUIVO
    lim = rodizio.Limitador(intervalo, relogio=relogio, dormir=dormir)
    creditos0 = None
    orc = rodizio.Orcamento(requisicoes=limite * 3, tempo_max_s=tempo_max, falhas_seguidas_max=3, relogio=relogio)
    cont: dict = {"requisicoes": 0}
    motivo: Optional[str] = None
    lidos_agora = 0
    proprio = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(30, read=60), headers=HEADERS)

    def estado_plano() -> dict:
        return {"facetas": {"port": "ok", "vuln": vuln, **({"vuln_testada_em": plano.get("vuln_testada_em")} if plano.get("vuln_testada_em") else {})}}

    def grava(parcial: bool) -> None:
        _salva_atomico(arquivo, _documento(date_str, asns, lidos, estado_plano(), {**cont, **orc.resumo(), "asns_lidos": lidos_agora, "limite": limite, "intervalo_s": intervalo,
                                                                                    "parou": motivo, "parcial": parcial}))

    try:
        creditos0 = _api_info(client, chave, limitador=lim).get("query_credits")
        for asn in rodizio.escolher_por_idade(asns, lambda a: (lidos.get(str(a)) or {}).get("em"), limite):
            motivo = orc.motivo_parada()
            if motivo:
                break
            if lidos_agora == CONFERE_CREDITOS_APOS and creditos0 is not None:
                c1 = _api_info(client, chave, limitador=lim).get("query_credits")
                if c1 is not None and c1 < creditos0:
                    motivo = f"a consulta gasta créditos de consulta ({creditos0} -> {c1} em {lidos_agora} ASNs): parado"
                    break
                creditos0 = None
            vuln_antes = vuln
            try:
                gasto = {"requisicoes": 0}
                leitura, vuln = leitura_do_asn(client, asn, chave, vuln, gasto, dormir=dormir, limitador=lim)
            except ChaveInvalida as exc:
                motivo = f"chave recusada pelo Shodan: {exc}"
                break
            except Limite as exc:
                motivo = f"limite de taxa: {exc}"
                break
            except PlanoNaoPermite as exc:
                # A/B recusadas por plano: a rodada não tem como seguir; registra e para (não é falha de rede)
                motivo = f"o plano da conta não permite a consulta: {exc}"
                break
            except httpx.HTTPError as exc:
                orc.gastar(1)
                orc.falha()
                log.warning("shodan_exposicao: falha de rede", erro=type(exc).__name__, falhas_seguidas=orc.falhas_seguidas)    # nunca str(exc): a URL leva a chave
                continue
            orc.gastar(gasto["requisicoes"])
            cont["requisicoes"] += gasto["requisicoes"]
            orc.sucesso()
            if vuln == "indisponivel" and vuln_antes != "indisponivel":
                plano["vuln_testada_em"] = date_str
                log.info("shodan_exposicao: faceta vuln indisponível no plano; só será reexperimentada depois de %d dias" % VULN_REEXPERIMENTA_DIAS)
            lidos[str(asn)] = {**leitura, "em": date_str}
            lidos_agora += 1
            if lidos_agora % CHECKPOINT_A_CADA == 0:
                grava(True)
    finally:
        if proprio:
            client.close()
    grava(False)
    medicao = {"asns_lidos": lidos_agora, "limite": limite, "requisicoes": cont["requisicoes"], "falhas": orc.falhas, "segundos": orc.resumo()["segundos"], "intervalo_s": intervalo,
               "parou": motivo, "asns_no_universo": len(asns), "asns_com_leitura": len(lidos), "asns_com_servicos": sum(1 for v in lidos.values() if v.get("total")),
               "vuln": vuln, "dias_ate_cobrir": -(-len(asns) // limite) if limite else None}
    log.info("shodan_exposicao written", **medicao)
    return medicao


# ── sondagem (para rodar onde a chave existe) ──────────────────────────────────────────────────────────────────────────

FACETAS_SONDADAS = ("port", "product", "vuln", "org", "os", "country", "state", "city", "isp", "tag", "has_vuln")
FILTROS_SONDADOS = ("country:BR", "has_vuln:true", "vuln:CVE-2021-44228", "port:23", "state:SP")


def _tempo(f: Callable[[], dict]) -> tuple[Optional[dict], int, Optional[str]]:
    t0 = time.monotonic()
    erro = None
    r = None
    try:
        r = f()
    except (ChaveInvalida, PlanoNaoPermite, Limite) as exc:
        erro = f"{type(exc).__name__}: {exc}"
    except httpx.HTTPError as exc:
        erro = type(exc).__name__
    return r, round((time.monotonic() - t0) * 1000), erro


def _api_info(client: httpx.Client, chave: str, limitador: Optional[rodizio.Limitador] = None) -> dict:
    try:
        i = _get(client, "/api-info", {}, chave, limitador=limitador)
    except (ChaveInvalida, PlanoNaoPermite, Limite, httpx.HTTPError) as exc:
        return {"erro": type(exc).__name__}
    return {k: i.get(k) for k in ("plan", "query_credits", "scan_credits", "monitored_ips", "usage_limits") if k in i}


def sondar(base: Path, amostra: int, chave: str, intervalo: float = INTERVALO_S, seed: int = 20261110, saida: Optional[Path] = None, log=None) -> dict:
    """Mede (a) facetas e filtros que o plano aceita, (b) créditos e limites, (c) quantos ASNs do Brasil têm contagem, (d) tempo por consulta. Só números, sem valores de host."""
    universo = _universo(base, today_str())
    if not universo:
        raise RuntimeError("sondagem: sem orgs.json.gz em normalized/ (universo de ASNs)")
    sorteio = random.Random(seed).sample(universo, min(amostra, len(universo)))
    lim = rodizio.Limitador(intervalo)
    rel: dict = {"em": now_iso(), "intervalo_s": intervalo, "amostra": len(sorteio), "universo": len(universo)}
    with httpx.Client(timeout=httpx.Timeout(30, read=60), headers=UA_SONDAGEM) as client:
        rel["api_info_antes"] = _api_info(client, chave)
        # (a) facetas e filtros, num ASN com serviços (o primeiro da amostra que tiver)
        alvo = None
        t_a: list[int] = []
        for asn in sorteio:
            lim.esperar()
            r, ms, erro = _tempo(lambda: contar(client, shodan.CONSULTA_GERAL.format(asn=asn), "port:5", chave))
            t_a.append(ms)
            if erro and erro.startswith("ChaveInvalida"):
                rel["erro_fatal"] = erro
                break
            if r and (shodan.numero(r.get("total")) or 0) > 0:
                alvo = asn
                break
        rel["asn_para_facetas"] = alvo
        rel["facetas"] = {}
        rel["filtros"] = {}
        if alvo:
            for f in FACETAS_SONDADAS:
                lim.esperar()
                r, ms, erro = _tempo(lambda: contar(client, shodan.CONSULTA_GERAL.format(asn=alvo), f"{f}:5", chave))
                rel["facetas"][f] = {"ok": erro is None, "itens": len(shodan.faceta(r, f)), "ms": ms, "erro": erro}
            for filtro in FILTROS_SONDADOS:
                lim.esperar()
                r, ms, erro = _tempo(lambda: contar(client, f"asn:AS{alvo} {filtro}", None, chave))
                rel["filtros"][filtro] = {"ok": erro is None, "total": (r or {}).get("total"), "ms": ms, "erro": erro}
        # (c) e (d): o que o coletor faria por ASN (A, B e, se existir, C)
        vuln = "ok" if (rel["facetas"].get("vuln") or {}).get("ok") else "indisponivel"
        com_servicos = com_risco = 0
        ms_asn: list[int] = []
        totais: list[int] = []
        falhas = 0
        for asn in sorteio:
            t0 = time.monotonic()
            try:
                leitura, _ = leitura_do_asn(client, asn, chave, vuln, limitador=lim)
            except Limite:                      # 429 persistente: parar, sem insistir na API
                falhas += 1
                rel["parou"] = "limite de taxa (HTTP 429 persistente)"
                break
            except (ChaveInvalida, PlanoNaoPermite, httpx.HTTPError):
                falhas += 1
                continue
            ms_asn.append(round((time.monotonic() - t0) * 1000))
            totais.append(leitura["total"])
            com_servicos += 1 if leitura["total"] else 0
            com_risco += 1 if leitura["risco_total"] else 0
        ms_asn.sort()
        totais.sort()
        rel["cobertura"] = {"consultados": len(totais), "falhas": falhas, "com_servicos": com_servicos, "com_algum_servico_de_risco": com_risco,
                            "pct_com_servicos": round(100 * com_servicos / len(totais), 1) if totais else None,
                            "total_mediano": totais[len(totais) // 2] if totais else None, "total_maximo": totais[-1] if totais else None}
        rel["tempo_por_asn_ms"] = {"mediana": ms_asn[len(ms_asn) // 2] if ms_asn else None, "maximo": ms_asn[-1] if ms_asn else None,
                                   "estimativa_para_o_universo_horas": round(len(universo) * (sum(ms_asn) / max(1, len(ms_asn)) / 1000) / 3600, 1) if ms_asn else None}      # já inclui as pausas entre as consultas de cada ASN
        rel["api_info_depois"] = _api_info(client, chave, limitador=lim)
    if saida:
        saida.write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding="utf-8")
    if log:
        log.info("shodan sondagem pronta", cobertura=rel.get("cobertura"))
    return rel


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Shodan: contagens por ASN (rodízio) — exposição de serviços")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre incremental")
    p.add_argument("--asns", type=int, default=None, help="ASNs nesta execução (padrão: SHODAN_ASNS_POR_EXECUCAO ou %d)" % ASNS_POR_EXECUCAO)
    p.add_argument("--intervalo", type=float, default=None, help="segundos entre consultas (padrão: SHODAN_INTERVALO_S ou %g)" % INTERVALO_S)
    p.add_argument("--sondar", action="store_true", help="mede facetas, filtros, créditos, tempo e cobertura na conta real e imprime os números")
    p.add_argument("--amostra", type=int, default=60, help="ASNs sorteados na sondagem")
    p.add_argument("--saida", type=Path, default=None, help="arquivo JSON da sondagem")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        if a.sondar:
            chave = os.environ.get("SHODAN_API_KEY", "")
            if not chave:
                log.error("shodan_exposicao: SHODAN_API_KEY ausente do ambiente")
                return 1
            print(json.dumps(sondar(data_dir(), a.amostra, chave, a.intervalo or INTERVALO_S, saida=a.saida, log=log), ensure_ascii=False, indent=1))
        else:
            print(run(a.date, data_dir(), log, asns_por_execucao=a.asns, intervalo_s=a.intervalo))
    except ChaveInvalida as exc:
        log.error("shodan_exposicao: chave", erro=str(exc))
        return 1
    except httpx.HTTPError as exc:
        log.error("falha de rede na coleta de shodan_exposicao", erro=type(exc).__name__)      # nunca str(exc) nem traceback de httpx: a URL leva a chave
        return 1
    except Exception as exc:
        log.error("falha na coleta de shodan_exposicao", erro=type(exc).__name__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
