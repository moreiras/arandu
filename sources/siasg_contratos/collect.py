# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Contratos públicos: resultados de itens da Lei 14.133 publicados no PNCP, por CNPJ de fornecedor de telecom, em rodízio.

Fonte: API aberta e sem chave `dadosabertos.compras.gov.br` (espelho do PNCP). Uma consulta por CNPJ de matriz (`niFornecedor` aceita só o CNPJ de 14 dígitos: a filial é outro fornecedor e
não entra) e período (`dataResultadoPncpInicial/Final`, obrigatórias), páginas de 500 itens. O universo é o de `core.universo_telecom` em duas faixas: "A" = raiz que declara acessos
no SICI (fixo ou móvel) no mês de referência, relida a cada `SIASG_INTERVALO_A_DIAS` (7); "B" = o resto do universo (outorga ou CNAE 61 sem acessos declarados), a cada `SIASG_INTERVALO_B_DIAS` (56).

Rodízio (`core.rodizio`): em cada execução, até `SIASG_FORNECEDORES_POR_EXECUCAO` raízes devidas (sem leitura primeiro, depois a mais antiga; faixa A antes da B), dentro de um orçamento de
requisições, de tempo e de falhas seguidas; a leitura nova de uma raiz usa a janela incremental (última leitura menos `SOBREPOSICAO_DIAS`), então o histórico (a partir de 2021-04-01) é lido
uma vez só. O que a execução não renova é herdado do estado anterior com a data da leitura de cada raiz. Depois dos itens, enriquece-se cada contratação (órgão, esfera, município, modalidade,
objeto resumido) em ordem de valor, também em rodízio e com orçamento, e renova-se a cada 30 dias a tabela de unidades (UASG: município do órgão, 45 páginas).

Parada: HTTP 403, 429 repetido ou resposta que não é JSON encerra a rodada na hora (sem contornar), grava o que já foi lido e sai com código 3.

Normalizado: data/normalized/{date}/summary/siasg_contratos.json.gz (carrega o estado da execução anterior).

Uso:
    python -m sources.siasg_contratos.collect --date 2026-11-10 [--fornecedores 1500] [--force]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date as _date, timedelta
from pathlib import Path
from typing import Optional

import httpx

from core import rodizio, siasg
from core.common import configure_logging, data_dir, normalized_path, now_iso, read_json_gz, today_str, write_json_gz
from core.universo_telecom import basicos as universo_telecom, cnae_principal_ativa
from core.site import USER_AGENT

HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}
ESPERA_S = 1.1
FORNECEDORES_POR_EXECUCAO = 3000
COMPRAS_POR_EXECUCAO = 800
ORCAMENTO_REQUISICOES = 4000
TEMPO_MAX_S = 7200
FALHAS_SEGUIDAS_MAX = 8
INTERVALO_A_DIAS = 7
INTERVALO_B_DIAS = 56
INTERVALO_C_DIAS = 112
ORDEM_FAIXA = {"A": 0, "B": 1, "C": 2}
UASG_MAX_IDADE_DIAS = 30
MAX_PAGINAS_POR_FORNECEDOR = 40                      # 20 mil itens; acima disso a raiz fica marcada `incompleto`


class Bloqueio(RuntimeError):
    """403, 429 repetido ou resposta que não é JSON: sinal de bloqueio ou de desafio anti-bot. A rodada para; não se contorna."""


def _env_int(nome: str, padrao: int) -> int:
    try:
        return int(os.environ.get(nome) or padrao)
    except ValueError:
        return padrao


class Api:
    """GET com pausa mínima entre requisições, até 3 tentativas em erro transitório e contagem no orçamento."""

    def __init__(self, client: httpx.Client, limitador: rodizio.Limitador, orc: rodizio.Orcamento):
        self.client, self.limitador, self.orc = client, limitador, orc

    def get(self, caminho: str, params: dict) -> Optional[dict]:
        for tentativa in range(1, 4):
            self.limitador.esperar()
            self.orc.gastar()
            try:
                r = self.client.get(siasg.BASE_URL + caminho, params=params)
            except httpx.HTTPError:
                if tentativa == 3:
                    return None
                time.sleep(min(5 * tentativa, 30) if self.limitador.intervalo_s else 0)
                continue
            if r.status_code == 403:
                raise Bloqueio(f"HTTP 403 em {caminho}")
            if r.status_code == 429:
                if tentativa == 3:
                    raise Bloqueio(f"HTTP 429 repetido em {caminho}")
                time.sleep(min(float(r.headers.get("Retry-After", 10) or 10), 120) if self.limitador.intervalo_s else 0)
                continue
            if r.status_code >= 500:
                if tentativa == 3:
                    return None
                time.sleep(5 * tentativa if self.limitador.intervalo_s else 0)
                continue
            if r.status_code == 404:
                return {"resultado": [], "totalRegistros": 0, "totalPaginas": 0}
            if r.status_code >= 400:
                return None
            try:
                dados = r.json()
            except ValueError:
                raise Bloqueio(f"resposta de {caminho} não é JSON (desafio ou bloqueio?)")
            if not isinstance(dados, dict):
                raise Bloqueio(f"resposta de {caminho} com formato inesperado")
            return dados
        return None


def universo(base: Path, date_str: str, log=None) -> dict[str, str]:
    """{raiz: faixa}: "A" = declara acessos no SICI (fixo ou móvel) no mês de referência; "B" = o resto das outorgas e do SICI; "C" = CNAE 61 como atividade principal,
    estabelecimento ativo, sem outorga nem SICI (`SIASG_COM_CNAE_PRINCIPAL=0` desliga a faixa C)."""
    todos = universo_telecom(base, date_str, log, com_receita=False)
    sinal: set[str] = set()
    for nome in ("sici_acessos.json.gz", "sici_movel_acessos.json.gz"):
        p = normalized_path(base, date_str, "summary", nome)
        if p.exists():
            cn = (read_json_gz(p) or {}).get("cnpjs") or {}
            sinal.update(c[:8] for c, v in cn.items() if len(c) == 14 and ((v or {}).get("acessos") or 0) > 0)
    saida = {r: ("A" if r in sinal else "B") for r in sorted(todos | sinal)}
    if _env_int("SIASG_COM_CNAE_PRINCIPAL", 1):
        for r in sorted(cnae_principal_ativa(base, date_str) - set(saida)):
            saida[r] = "C"
    return saida


def devidas(faixas: dict[str, str], lidas: dict[str, dict], hoje: str, intervalos: dict[str, int]) -> dict[str, list[str]]:
    """Raízes devidas por faixa: nunca lidas ou com leitura mais antiga que o intervalo da faixa."""
    h = _date.fromisoformat(hoje)
    saida: dict[str, list[str]] = {"A": [], "B": [], "C": []}
    for raiz, faixa in faixas.items():
        em = (lidas.get(raiz) or {}).get("lida_em")
        if not em or (h - _date.fromisoformat(em[:10])).days >= intervalos[faixa]:
            saida[faixa].append(raiz)
    return saida


def _primeira_leitura(anterior: Optional[dict]) -> bool:
    return not anterior or not anterior.get("lida_em") or bool(anterior.get("incompleto"))


def _inicio(anterior: Optional[dict], hoje: str) -> str:
    """Primeira leitura: `JANELAS_INICIAIS` períodos para trás (a API recusa período > 365 dias). Seguintes: última leitura menos a sobreposição (resultado incluído com atraso)."""
    if _primeira_leitura(anterior):
        return siasg.inicio_primeira_leitura(hoje)
    ini = (_date.fromisoformat(anterior["lida_em"][:10]) - timedelta(days=siasg.SOBREPOSICAO_DIAS)).isoformat()
    return max(ini, siasg.JANELA_INICIO)


def ler_fornecedor(api: Api, raiz: str, anterior: Optional[dict], hoje: str) -> Optional[dict]:
    """Registro novo da raiz (itens mesclados) ou None se a consulta falhou (a raiz continua devida)."""
    cnpj = siasg.cnpj_matriz(raiz)
    inicio = _inicio(anterior, hoje)
    primeira = _primeira_leitura(anterior)
    itens = {} if primeira else {siasg.chave_item(i): i for i in (anterior or {}).get("itens") or []}
    total, incompleto = 0, False
    for ini, fim in siasg.janelas(inicio, hoje):          # a API só aceita períodos de até 365 dias
        for pagina in range(1, MAX_PAGINAS_POR_FORNECEDOR + 1):
            d = api.get(siasg.ENDPOINT_RESULTADOS, {"niFornecedor": cnpj, "dataResultadoPncpInicial": ini, "dataResultadoPncpFinal": fim, "tamanhoPagina": siasg.TAMANHO_PAGINA, "pagina": pagina})
            if d is None:
                return None
            for r in d.get("resultado") or []:
                it = siasg.item_compacto(r)
                if it:
                    itens[siasg.chave_item(it)] = it
            total += d.get("totalRegistros") or 0
            if pagina >= (d.get("totalPaginas") or 0):
                break
            if pagina == MAX_PAGINAS_POR_FORNECEDOR:
                incompleto = True
    ordenados = sorted(itens.values(), key=lambda i: (i.get("data") or "", i["id"], i["seq"]))
    return {"cnpj": cnpj, "lida_em": hoje, "desde": inicio if primeira else (anterior or {}).get("desde") or siasg.JANELA_INICIO, "itens": ordenados, "total_ultima_consulta": total, **({"incompleto": True} if incompleto else {})}


def candidatas_ao_aprofundamento(faixas: dict[str, str], regs: dict[str, dict]) -> list[str]:
    """Raízes já lidas cuja história ainda não chegou à Lei 14.133, da faixa A para a C e, em cada faixa, a aprofundada há mais tempo primeiro."""
    c = [r for r, f in faixas.items() if r in regs and (regs[r].get("desde") or siasg.JANELA_INICIO) > siasg.JANELA_INICIO and not regs[r].get("incompleto")]
    return sorted(c, key=lambda r: (ORDEM_FAIXA[faixas[r]], regs[r].get("aprofundada_em") or "", r))


def aprofundar_fornecedor(api: Api, raiz: str, reg: dict, hoje: str) -> Optional[dict]:
    """Lê a janela imediatamente anterior ao que a raiz já tem (`desde`) e a junta aos itens; None se a consulta falhou. `lida_em` não muda: é a data da leitura de atualização."""
    desde = reg.get("desde") or siasg.JANELA_INICIO
    fim = (_date.fromisoformat(desde) - timedelta(days=1)).isoformat()
    ini = max((_date.fromisoformat(fim) - timedelta(days=siasg.PERIODO_MAX_DIAS - 1)).isoformat(), siasg.JANELA_INICIO)
    itens = {siasg.chave_item(i): i for i in reg.get("itens") or []}
    incompleto = False
    for pagina in range(1, MAX_PAGINAS_POR_FORNECEDOR + 1):
        d = api.get(siasg.ENDPOINT_RESULTADOS, {"niFornecedor": reg["cnpj"], "dataResultadoPncpInicial": ini, "dataResultadoPncpFinal": fim, "tamanhoPagina": siasg.TAMANHO_PAGINA, "pagina": pagina})
        if d is None:
            return None
        for r in d.get("resultado") or []:
            it = siasg.item_compacto(r)
            if it:
                itens[siasg.chave_item(it)] = it
        if pagina >= (d.get("totalPaginas") or 0):
            break
        if pagina == MAX_PAGINAS_POR_FORNECEDOR:
            incompleto = True
    ordenados = sorted(itens.values(), key=lambda i: (i.get("data") or "", i["id"], i["seq"]))
    return {**reg, "itens": ordenados, "desde": ini, "aprofundada_em": hoje, **({"incompleto": True} if incompleto else {})}


def _lista_uasg(api: Api, paginas_max: int = 200) -> dict[str, dict]:
    """Tabela de unidades de compra ativas: código → nome, UF e município (IBGE) do órgão. None-safe: página que falha interrompe e devolve {}."""
    out: dict[str, dict] = {}
    for pagina in range(1, paginas_max + 1):
        d = api.get("/modulo-uasg/1_consultarUasg", {"statusUasg": "true", "pagina": pagina})
        if d is None:
            return {}
        for u in d.get("resultado") or []:
            if u.get("codigoUasg"):
                out[str(u["codigoUasg"])] = {"nome": u.get("nomeUasg"), "uf": u.get("siglaUf"), "ibge": str(u["codigoMunicipioIbge"]) if u.get("codigoMunicipioIbge") else None,
                                              "municipio": u.get("nomeMunicipioIbge"), "org": siasg.digitos(u.get("cnpjCpfOrgao")) or None}
        if pagina >= (d.get("totalPaginas") or 0):
            break
    return out


def pendentes_de_enriquecimento(fornecedores: dict[str, dict], compras: dict[str, dict]) -> list[str]:
    """Contratações com algum item não cancelado e sem detalhe, da de maior valor para a de menor (empate pelo número de controle)."""
    valor: dict[str, float] = {}
    for f in fornecedores.values():
        for it in f.get("itens") or []:
            if it.get("compra") and it["compra"] not in compras and it.get("sit") != siasg.CANCELADO:
                valor[it["compra"]] = valor.get(it["compra"], 0.0) + (it.get("valor") or 0.0)
    return sorted(valor, key=lambda c: (-valor[c], c))


def run(date_str: str, base: Path, log, client: Optional[httpx.Client] = None, fornecedores_por_execucao: Optional[int] = None, compras_por_execucao: Optional[int] = None,
        orcamento_requisicoes: Optional[int] = None, tempo_max_s: Optional[float] = None, espera_s: float = ESPERA_S, relogio=time.monotonic, dormir=time.sleep) -> dict:
    t0 = time.time()
    limite = fornecedores_por_execucao if fornecedores_por_execucao is not None else _env_int("SIASG_FORNECEDORES_POR_EXECUCAO", FORNECEDORES_POR_EXECUCAO)
    limite_compras = compras_por_execucao if compras_por_execucao is not None else _env_int("SIASG_COMPRAS_POR_EXECUCAO", COMPRAS_POR_EXECUCAO)
    intervalos = {"A": _env_int("SIASG_INTERVALO_A_DIAS", INTERVALO_A_DIAS), "B": _env_int("SIASG_INTERVALO_B_DIAS", INTERVALO_B_DIAS), "C": _env_int("SIASG_INTERVALO_C_DIAS", INTERVALO_C_DIAS)}
    antes = rodizio.anterior_normalizado(base, date_str, "siasg_contratos.json.gz", incluir_data=True)
    faixas = universo(base, date_str, log)
    if not faixas:
        raise RuntimeError("siasg_contratos: universo de telecom vazio (outorgas e SICI ausentes do normalizado)")
    orc = rodizio.Orcamento(requisicoes=orcamento_requisicoes if orcamento_requisicoes is not None else _env_int("SIASG_ORCAMENTO", ORCAMENTO_REQUISICOES),
                            tempo_max_s=tempo_max_s if tempo_max_s is not None else _env_int("SIASG_TEMPO_MAX_S", TEMPO_MAX_S), falhas_seguidas_max=FALHAS_SEGUIDAS_MAX, relogio=relogio)
    proprio = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(60, read=180), headers=HEADERS)
    api = Api(client, rodizio.Limitador(espera_s, relogio=relogio, dormir=dormir), orc)
    anteriores = antes.get("fornecedores") or {}
    compras = {k: v for k, v in (antes.get("compras") or {}).items()}
    uasg, uasg_em = antes.get("uasg") or {}, antes.get("uasg_em")
    novos: dict[str, dict] = {}
    parada, bloqueio = None, False
    lidos = lidos_a = enriquecidas = aprofundadas = 0
    try:
        h = _date.fromisoformat(date_str)
        if not uasg or not uasg_em or (h - _date.fromisoformat(uasg_em)).days >= UASG_MAX_IDADE_DIAS:
            nova = _lista_uasg(api)
            if nova:
                uasg, uasg_em = nova, date_str
            elif not uasg:
                log.warning("siasg_contratos: tabela de unidades indisponível; município do órgão só pelo detalhe da contratação")
        dev = devidas(faixas, {**anteriores}, date_str, intervalos)
        vez: list[str] = []
        for faixa in ("A", "B", "C"):                                # a faixa seguinte só ocupa o que a anterior não usou
            if limite and len(vez) >= limite:
                break
            vez += rodizio.escolher_por_idade(dev[faixa], lambda r: (anteriores.get(r) or {}).get("lida_em"), (limite - len(vez)) if limite else 0)
        for raiz in vez:
            parada = orc.motivo_parada()
            if parada:
                break
            reg = ler_fornecedor(api, raiz, anteriores.get(raiz), date_str)
            if reg is None:
                orc.falha()
                continue
            orc.sucesso()
            novos[raiz] = reg
            lidos += 1
            lidos_a += 1 if faixas.get(raiz) == "A" else 0
        if not parada:
            atuais = rodizio.herdar(anteriores, novos, vivos=set(faixas), data=date_str, lida_em="lida_em")
            for numero in pendentes_de_enriquecimento(atuais, compras)[: max(limite_compras, 0)]:
                parada = orc.motivo_parada()
                if parada:
                    break
                d = api.get(siasg.ENDPOINT_COMPRA, {"tipo": "numeroControlePNCPCompra", "codigo": numero})
                res = (d or {}).get("resultado") or []
                if not res:
                    orc.falha()
                    continue
                orc.sucesso()
                compras[numero] = siasg.compra_compacta(res[0], date_str)
                enriquecidas += 1
        if not parada and _env_int("SIASG_APROFUNDAR", 1):            # com o orçamento que sobrou: uma janela mais antiga por raiz, da faixa A para a C
            base_reg = {**anteriores, **novos}
            for raiz in candidatas_ao_aprofundamento(faixas, base_reg):
                parada = orc.motivo_parada()
                if parada:
                    break
                reg2 = aprofundar_fornecedor(api, raiz, base_reg[raiz], date_str)
                if reg2 is None:
                    orc.falha()
                    continue
                orc.sucesso()
                novos[raiz] = reg2
                aprofundadas += 1
    except Bloqueio as exc:
        bloqueio, parada = True, str(exc)
        log.error("siasg_contratos: sinal de bloqueio; rodada encerrada", motivo=parada)
    finally:
        if proprio:
            client.close()
    fornecedores = rodizio.herdar(anteriores, novos, vivos=set(faixas), data=date_str, lida_em="lida_em")
    usadas = {it["compra"] for f in fornecedores.values() for it in f.get("itens") or [] if it.get("compra")}
    compras = {k: v for k, v in compras.items() if k in usadas}
    sem_leitura = sum(1 for r in faixas if r not in fornecedores)
    abortada = bool(parada) and "falhas seguidas" in parada
    medicao = {"fornecedores_lidos": lidos, "fornecedores_lidos_faixa_a": lidos_a, "limite": limite, "contratacoes_enriquecidas": enriquecidas, "raizes_aprofundadas": aprofundadas, **orc.resumo(), "parada": parada, "bloqueio": bloqueio, "abortada_por_falhas": abortada,
               "universo": len(faixas), "faixa_a": sum(1 for v in faixas.values() if v == "A"), "raizes_com_leitura": len(fornecedores), "raizes_sem_leitura": sem_leitura,
               "raizes_com_contrato": sum(1 for f in fornecedores.values() if f.get("itens")), "itens": sum(len(f.get("itens") or []) for f in fornecedores.values()),
               "contratacoes_com_detalhe": len(compras), "contratacoes_sem_detalhe": len(pendentes_de_enriquecimento(fornecedores, compras)), "unidades_na_tabela": len(uasg),
               "segundos_totais": round(time.time() - t0, 1)}
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / "siasg_contratos.json.gz", {
        "snapshot_date": date_str, "fetched_at": now_iso(), "fonte": siasg.FONTE_URL, "api": siasg.BASE_URL + siasg.ENDPOINT_RESULTADOS, "licenca": siasg.LICENCA,
        "janela_inicio": siasg.inicio_primeira_leitura(date_str), "periodo_max_dias": siasg.PERIODO_MAX_DIAS, "intervalos_dias": intervalos, "faixas": {r: f for r, f in faixas.items()},
        "fornecedores": dict(sorted(fornecedores.items())), "compras": dict(sorted(compras.items())), "uasg": uasg, "uasg_em": uasg_em, "ultima_execucao": medicao})
    log.info("siasg_contratos written", **{k: v for k, v in medicao.items() if k != "parada"}, parada=parada)
    return medicao


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Contratos públicos (Compras.gov.br / PNCP, Lei 14.133) por fornecedor de telecom, em rodízio")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre incremental (repetir continua de onde parou)")
    p.add_argument("--fornecedores", type=int, default=None, help="raízes de CNPJ a ler nesta execução (padrão: SIASG_FORNECEDORES_POR_EXECUCAO ou 1500)")
    p.add_argument("--compras", type=int, default=None, help="contratações a enriquecer nesta execução (padrão: SIASG_COMPRAS_POR_EXECUCAO ou 800)")
    p.add_argument("--requisicoes", type=int, default=None, help="orçamento de requisições da rodada (padrão: SIASG_ORCAMENTO ou 2500)")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        m = run(a.date, data_dir(), log, fornecedores_por_execucao=a.fornecedores, compras_por_execucao=a.compras, orcamento_requisicoes=a.requisicoes)
        print(m)
    except Exception:
        log.exception("falha na coleta de siasg_contratos")
        return 1
    return 3 if (m.get("bloqueio") or m.get("abortada_por_falhas")) else 0


if __name__ == "__main__":
    sys.exit(main())
