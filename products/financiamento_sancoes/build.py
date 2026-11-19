# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Crédito público (BNDES) e sanções (CGU: CEIS e CNEP) por operadora.

Publica `financiamento/operadoras.json.gz`: por raiz de CNPJ, as operações de financiamento do BNDES (total contratado e desembolsado, por ano e por UF, e as últimas operações) e as
sanções (vigentes e encerradas na data do snapshot), mais um resumo do conjunto. As duas partes são independentes: sem a fonte de um lado, o outro é publicado.

Honestidade semântica: o BNDES registra o que foi contratado e desembolsado, em valores nominais da data; a sanção é o registro do órgão sancionador na data do arquivo da CGU. O produto não
julga, não ordena operadoras por "risco" e não liga uma coisa à outra. Sanção sem prazo (a fonte usa 2099-12-31) aparece como `sem_prazo`.

Entrada:  normalized/{date}/summary/bndes_operacoes.json.gz e cgu_ceis_cnep.json.gz
Saída:    published/{date}/financiamento/operadoras.json.gz
Uso:
    python -m products.financiamento_sancoes.build --date 2026-11-08
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

from core.common import configure_logging, data_dir, normalized_path, now_iso, published_path, today_str
from core.jsonio import carregar_json_gz, gravar_json_gz

MAX_OPERACOES = 50
SEM_PRAZO = "2099-12-31"
LIMITES = ("Operações do BNDES: só as diretas e não automáticas (as indiretas têm o CNPJ mascarado); valores nominais da data da contratação; a operadora entra se o CNPJ básico está no universo de telecom. "
           "Sanções: registro do órgão sancionador na data do arquivo da CGU, sem julgamento; pode já ter sido suspensa, anulada ou cumprida sem refletir no arquivo; sanção a uma filial aparece na raiz com o CNPJ da filial. "
           "Duas fontes que não se ligam entre si: crédito público e sanção não têm relação de causa e efeito neste produto.")


def situacao(s: dict, hoje: str) -> str:
    """vigente | encerrada | futura, pela data do snapshot; fim ausente ou 2099-12-31 = sem prazo (vigente)."""
    ini, fim = s.get("inicio"), s.get("fim")
    if ini and ini > hoje:
        return "futura"
    if fim and fim != SEM_PRAZO and fim < hoje:
        return "encerrada"
    return "vigente"


def _financiamento(ops: list[dict]) -> dict:
    por_ano: dict[str, list[float]] = defaultdict(lambda: [0, 0.0, 0.0])
    por_uf: dict[str, list[float]] = defaultdict(lambda: [0, 0.0, 0.0])
    for o in ops:
        for chave, acc in (((o.get("data") or "")[:4] or "s/d", por_ano), (o.get("uf") or "s/d", por_uf)):
            acc[chave][0] += 1
            acc[chave][1] += o.get("contratado") or 0.0
            acc[chave][2] += o.get("desembolsado") or 0.0
    fmt = lambda k, v, nome: {nome: k, "operacoes": v[0], "contratado": round(v[1], 2), "desembolsado": round(v[2], 2)}      # noqa: E731
    recentes = sorted(ops, key=lambda o: (o.get("data") or "", o.get("contrato") or ""), reverse=True)[:MAX_OPERACOES]
    return {"operacoes_total": len(ops), "contratado_total": round(sum(o.get("contratado") or 0.0 for o in ops), 2),
            "desembolsado_total": round(sum(o.get("desembolsado") or 0.0 for o in ops), 2),
            "primeira": min((o["data"] for o in ops if o.get("data")), default=None), "ultima": max((o["data"] for o in ops if o.get("data")), default=None),
            "por_ano": [fmt(k, por_ano[k], "ano") for k in sorted(por_ano)], "por_uf": [fmt(k, v, "uf") for k, v in sorted(por_uf.items(), key=lambda kv: -kv[1][1])],
            "operacoes": recentes, "operacoes_omitidas": max(0, len(ops) - MAX_OPERACOES)}


def _sancoes(lista: list[dict], hoje: str) -> dict:
    marcadas = [{**s, "situacao": situacao(s, hoje), "sem_prazo": s.get("fim") == SEM_PRAZO, "sem_fim_informado": s.get("fim") is None} for s in lista]
    for s in marcadas:
        if s["sem_prazo"]:
            s["fim"] = None
        s["sem_fim_informado"] = s["fim"] is None          # inclui o 2099-12-31 da fonte e as sanções sem data final (multa do CNEP, publicação): "vigente" aqui é "consta sem fim", não "em curso comprovado"
    chave = lambda s: (s.get("inicio") or "", s.get("codigo") or "")      # noqa: E731
    por = lambda sit: sorted((s for s in marcadas if s["situacao"] == sit), key=chave, reverse=True)      # noqa: E731
    return {"vigentes": por("vigente"), "futuras": por("futura"), "encerradas": por("encerrada"), "total": len(marcadas)}


def calcular(bndes: Optional[dict], cgu: Optional[dict], snapshot_date: str) -> tuple[dict, dict[str, dict]]:
    ops_por_raiz: dict[str, list[dict]] = defaultdict(list)
    for cnpj, ops in ((bndes or {}).get("operacoes") or {}).items():
        ops_por_raiz[cnpj[:8]].extend({**o, "cnpj": cnpj} for o in ops)
    san_por_raiz: dict[str, list[dict]] = defaultdict(list)
    for cnpj, lista in ((cgu or {}).get("sancoes") or {}).items():
        san_por_raiz[cnpj[:8]].extend({**s, "cnpj": cnpj} for s in lista)
    docs: dict[str, dict] = {}
    for raiz in sorted(set(ops_por_raiz) | set(san_por_raiz)):
        d: dict = {}
        if raiz in ops_por_raiz:
            d["financiamento"] = _financiamento(ops_por_raiz[raiz])
        if raiz in san_por_raiz:
            d["sancoes"] = _sancoes(san_por_raiz[raiz], snapshot_date)
        docs[raiz] = d
    vigentes = sum(1 for d in docs.values() if (d.get("sancoes") or {}).get("vigentes"))
    resumo = {"operadoras_com_financiamento": len(ops_por_raiz), "operacoes": sum(len(v) for v in ops_por_raiz.values()),
              "contratado_total": round(sum(o.get("contratado") or 0.0 for v in ops_por_raiz.values() for o in v), 2),
              "operadoras_com_sancao": len(san_por_raiz), "operadoras_com_sancao_vigente": vigentes, "sancoes": sum(len(v) for v in san_por_raiz.values()),
              "bndes_presente": bool(bndes), "cgu_presente": bool(cgu)}
    return {"resumo": resumo}, docs


def publicar_financiamento_sancoes(base: Path, date_str: str, log) -> dict:
    norm = normalized_path(base, date_str, "summary")
    bndes = carregar_json_gz(norm / "bndes_operacoes.json.gz")
    cgu = carregar_json_gz(norm / "cgu_ceis_cnep.json.gz")
    if not bndes and not cgu:
        log.info("bndes_operacoes e cgu_ceis_cnep ausentes: financiamento e sanções não gerados")
        return {}
    geral, docs = calcular(bndes, cgu, date_str)
    meta = {"snapshot_date": date_str, "generated_at": now_iso(), "natureza": "registro_de_fonte_oficial",
            "fontes": {"bndes": {"fonte": "BNDES, dados abertos (operações não automáticas)", "licenca": "ODbL", "dump_reference": (bndes or {}).get("dump_reference")},
                       "cgu": {"fonte": "CGU, Portal da Transparência (CEIS e CNEP)", "arquivos": (cgu or {}).get("arquivos")}}}
    destino = published_path(base, date_str) / "financiamento"
    destino.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "operadoras.json.gz", {**meta, "limites": LIMITES, **geral, "operadoras": docs})
    log.info("financiamento/operadoras written", operadoras=len(docs), **geral["resumo"])
    return geral["resumo"]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Crédito público e sanções por operadora")
    p.add_argument("--date", default=today_str())
    a = p.parse_args(argv)
    publicar_financiamento_sancoes(data_dir(), a.date, configure_logging())
    return 0


if __name__ == "__main__":
    sys.exit(main())
