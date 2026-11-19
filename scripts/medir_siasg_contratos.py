#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Mede, numa amostra do universo de telecom, o custo real da coleta de contratos públicos e projeta a varredura completa.

NÃO grava no armazém de dados: só lê o universo (`normalized/{date}/summary`) e escreve o relatório no `--saida`. Consulta a API do Compras.gov.br com o mesmo coletor da fonte
(`sources.siasg_contratos.collect`: User-Agent identificado, 1,1 s entre requisições, parada em 403/429/resposta que não é JSON), uma raiz por vez, em janelas de até 360 dias (a API recusa mais de 365).

O que o relatório traz: requisições e segundos por raiz (média e percentis), fração de raízes com resultado, itens por raiz, contratações por item, custo do detalhe por contratação,
tamanho do estado em JSON comprimido por raiz e a projeção para o universo inteiro (requisições, horas, itens, contratações, MiB do estado diário). Sem nome de empresa nem de órgão.

Uso (no ambiente de teste, fora da janela do pipeline, ver `scripts/arandu-exclusivo.sh`):
    python scripts/medir_siasg_contratos.py --date 2026-11-10 --amostra 300 --compras 150 --saida /tmp/medida_siasg.json
"""
from __future__ import annotations

import argparse
import gzip
import json
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Optional

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import rodizio, siasg  # noqa: E402
from core.common import configure_logging, data_dir, today_str  # noqa: E402
from sources.siasg_contratos import collect as fonte  # noqa: E402


def _pct(v: list[float], p: float) -> Optional[float]:
    if not v:
        return None
    s = sorted(v)
    return round(s[min(len(s) - 1, int(round(p / 100 * (len(s) - 1))))], 2)


def medir(date_str: str, base: Path, amostra: int, compras: int, semente: int = 1, espera_s: float = fonte.ESPERA_S, client: Optional[httpx.Client] = None, log=None) -> dict:
    faixas = fonte.universo(base, date_str, log)
    if not faixas:
        raise SystemExit("universo vazio: faltam as outorgas e o SICI no normalizado dessa data")
    rnd = random.Random(semente)
    a = sorted(r for r, f in faixas.items() if f == "A")
    b = sorted(r for r, f in faixas.items() if f != "A")                 # B e C
    n_a = min(len(a), round(amostra * len(a) / len(faixas)))
    escolha = rnd.sample(a, n_a) + rnd.sample(b, min(len(b), amostra - n_a))
    proprio = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(60, read=180), headers=fonte.HEADERS)
    orc = rodizio.Orcamento(requisicoes=0, tempo_max_s=0, falhas_seguidas_max=fonte.FALHAS_SEGUIDAS_MAX)
    api = fonte.Api(client, rodizio.Limitador(espera_s), orc)
    por_raiz: list[dict] = []
    registros: dict[str, dict] = {}
    parada = None
    try:
        for raiz in escolha:
            t0, antes = time.monotonic(), orc.gastas
            try:
                reg = fonte.ler_fornecedor(api, raiz, None, date_str)
            except fonte.Bloqueio as exc:
                parada = str(exc)
                break
            if reg is None:
                orc.falha()
                por_raiz.append({"faixa": faixas[raiz], "ok": False, "requisicoes": orc.gastas - antes, "segundos": round(time.monotonic() - t0, 2), "itens": 0})
                if orc.motivo_parada():
                    parada = orc.motivo_parada()
                    break
                continue
            orc.sucesso()
            registros[raiz] = reg
            por_raiz.append({"faixa": faixas[raiz], "ok": True, "requisicoes": orc.gastas - antes, "segundos": round(time.monotonic() - t0, 2), "itens": len(reg["itens"])})
        # detalhe de contratações: as de maior valor entre as lidas
        pend = fonte.pendentes_de_enriquecimento(registros, {})
        total_compras = len(pend)
        tempos_compra: list[float] = []
        detalhes: dict[str, dict] = {}
        if not parada:
            for numero in rnd.sample(pend, min(compras, len(pend))):
                t0 = time.monotonic()
                d = api.get(siasg.ENDPOINT_COMPRA, {"tipo": "numeroControlePNCPCompra", "codigo": numero})
                tempos_compra.append(time.monotonic() - t0)
                res = (d or {}).get("resultado") or []
                if res:
                    detalhes[numero] = siasg.compra_compacta(res[0], date_str)
    except fonte.Bloqueio as exc:
        parada = str(exc)
    finally:
        if proprio:
            client.close()
    lidas = [x for x in por_raiz if x["ok"]]
    com = [x for x in lidas if x["itens"] > 0]
    itens_total = sum(x["itens"] for x in lidas)
    req = [x["requisicoes"] for x in lidas]
    seg = [x["segundos"] for x in lidas]
    tamanho = len(gzip.compress(json.dumps({"fornecedores": registros, "compras": detalhes}, ensure_ascii=False).encode())) if registros else 0
    u = len(faixas)
    escala = u / len(lidas) if lidas else None
    seg_medio = statistics.mean(seg) if seg else None
    s_compra = statistics.mean(tempos_compra) if tempos_compra else None
    compras_por_item = (total_compras / itens_total) if itens_total else None
    rel = {
        "data": date_str, "semente": semente, "universo": u, "faixa_a": len(a), "faixa_b": len(b), "amostra_pedida": amostra, "amostra_lida": len(lidas), "parada": parada,
        "por_raiz": {"requisicoes_media": round(statistics.mean(req), 3) if req else None, "segundos_media": round(seg_medio, 2) if seg_medio is not None else None, "segundos_p50": _pct(seg, 50), "segundos_p95": _pct(seg, 95),
                     "segundos_max": max(seg) if seg else None, "fracao_com_resultado": round(len(com) / len(lidas), 4) if lidas else None,
                     "itens_media_das_com_resultado": round(statistics.mean(x["itens"] for x in com), 1) if com else None, "itens_max": max((x["itens"] for x in lidas), default=None),
                     "falhas": sum(1 for x in por_raiz if not x["ok"])},
        "detalhe_contratacao": {"amostra": len(tempos_compra), "segundos_media": round(s_compra, 2) if s_compra is not None else None, "contratacoes_nas_raizes_lidas": total_compras, "contratacoes_por_item": round(compras_por_item, 3) if compras_por_item else None,
                                "com_esfera": sum(1 for d in detalhes.values() if d.get("esfera")), "com_municipio": sum(1 for d in detalhes.values() if d.get("ibge"))},
        "estado_comprimido_bytes_da_amostra": tamanho,
        "projecao_universo_inteiro": ({
            "requisicoes_itens": round(statistics.mean(req) * u) if req else None,
            "horas_so_itens_com_pausa_de_1_1s": round(u * (seg_medio or 0) / 3600, 2) if seg_medio is not None else None,
            "itens": round(itens_total * escala), "contratacoes": round(total_compras * escala), "horas_detalhe_de_todas_as_contratacoes": round(total_compras * escala * (s_compra or 0) / 3600, 2) if s_compra is not None else None,
            "estado_diario_mib_gz": round(tamanho * escala / 1024 / 1024, 1),
            "dias_do_rodizio_faixa_a_com_1500_por_dia": round(len(a) / 1500, 1)} if escala else None),
        "aviso": "projeção linear da amostra; raiz com muito contrato (grandes operadoras) pesa fora da média, então confirme o p95 e o máximo antes de fixar o orçamento por rodada",
    }
    return rel


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Mede o custo da coleta de contratos públicos numa amostra do universo e projeta a varredura")
    p.add_argument("--date", default=today_str())
    p.add_argument("--amostra", type=int, default=300, help="raízes de CNPJ (proporcional às faixas A e B)")
    p.add_argument("--compras", type=int, default=150, help="contratações a detalhar para medir o custo do detalhe")
    p.add_argument("--semente", type=int, default=1)
    p.add_argument("--saida", default="medida_siasg_contratos.json")
    a = p.parse_args(argv)
    rel = medir(a.date, data_dir(), a.amostra, a.compras, a.semente, log=configure_logging())
    Path(a.saida).write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(rel, ensure_ascii=False, indent=1))
    return 3 if rel["parada"] and "falhas" not in rel["parada"] else 0


if __name__ == "__main__":
    sys.exit(main())
