# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`anatel_sici_movel` — Acessos de telefonia móvel (SMP) declarados ao SICI (Anatel).

Mesma fonte/mecânica de sources/anatel_sici/collect.py (`anatel_sici`), mas para o zip de telefonia
móvel: quantos acessos móveis cada CNPJ tem, em que município, com que modalidade de
cobrança (pré/pós-pago), tecnologia (geração 2G-5G) e tipo de cliente (PF/PJ).

Fonte: https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/
       acessos_telefonia_movel.zip   (~3 GB, atualizado mensalmente)

DIFERENÇAS PARA A BASE DE BANDA LARGA FIXA (`anatel_sici`)
-------------------------------------------------
- Os membros do ZIP são SEMESTRAIS (`Acessos_Telefonia_Movel_2026_2S.csv`), não anuais,
  e maiores (~100–250 MB comprimidos cada, vs. ~80 MB dos anuais da base fixa).
- Não há "velocidade contratada" — em vez disso, há Modalidade de Cobrança (pré/pós-pago)
  e Tecnologia Geração (2G/3G/4G/5G).
- `Tipo de Produto` inclui M2M (chips embarcados em máquinas) e PONTO_DE_SERVICO
  (infraestrutura da prestadora). Nenhum dos dois entra no total `acessos` — só voz/
  dados de linha pessoal contam, batendo com o total oficial da Anatel (conferido
  contra o sentinela). Ficam contados à parte em `acessos_m2m`/`acessos_outros`.
- Escopo do histórico: só os membros semestrais no formato unificado (2019 em diante).
  Períodos anteriores a 2019 vêm em arquivos separados por dimensão (Modalidade vs.
  Tecnologia, colunas diferentes) e ficam fora de escopo desta primeira versão.

Cache persistente (fora dos snapshots imutáveis, como geo_cache/):
  data/normalized/sici_movel_cache/state.json                — controle de atualização
  data/normalized/sici_movel_cache/months/{YYYY-MM}.json.gz  — agregado imutável de um mês

Saída por snapshot:
  data/normalized/{date}/summary/sici_movel_acessos.json.gz

Uso:
    python -m sources.anatel_sici_movel.collect
    python -m sources.anatel_sici_movel.collect --date 2026-06-28
    python -m sources.anatel_sici_movel.collect --bootstrap      # processa todo o histórico (2019+)
    python -m sources.anatel_sici_movel.collect --force-full     # ignora o cache e refaz o semestre
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from pathlib import Path
from typing import Optional

import httpx

from core.common import (
    configure_logging,
    data_dir,
    normalized_path,
    now_iso,
    today_str,
    write_json_gz,
)
from sources.anatel_sici.collect import RemoteZip, _decode

ANATEL_URL = (
    "https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/"
    "acessos_telefonia_movel.zip"
)

# Membro sentinela: mesma forma "Ano;Mês;Acessos" do `anatel_sici`, custa ~1 MB de tráfego
# para descobrir o último mês publicado em vez dos ~3 GB do zip inteiro.
SENTINEL_MEMBER = "Acessos_Telefonia_Movel_Total.csv"

# Só os 12 meses mais recentes guardam detalhe por município — mesma janela do `anatel_sici`.
MUNICIPIO_DETAIL_MONTHS = 12

# Membro semestral no formato unificado, ex.: "Acessos_Telefonia_Movel_2026_2S.csv".
# Não casa com as variantes "_Colunas.csv" (metadado, não dado) nem com os arquivos
# pré-2019 ("_2005-2018_Modalidade.csv" etc.), que têm outro layout de colunas.
_MEMBER_RE = re.compile(r"^Acessos_Telefonia_Movel_(\d{4})_([12]S)\.csv$")

# Tipo de Produto que conta como acesso de telefonia móvel "padrão" (voz e/ou dados
# de linha pessoal). Os demais — M2M (chip embarcado em máquina) e PONTO_DE_SERVICO
# (infraestrutura da prestadora, não linha de cliente) — juntos batem ~59M acessos em
# 2026-07 e NÃO entram no total oficial da Anatel (conferido contra o sentinela
# Acessos_Telefonia_Movel_Total.csv: soma de VOZ+DADOS/VOZ/DADOS bate com o total
# publicado; incluir M2M/PONTO_DE_SERVICO infla o total em ~27%). Mesmo espírito do
# filtro PRODUTO_INTERNET no `anatel_sici` (banda larga fixa), que isola link dedicado/backbone
# do acesso de fato.
PRODUTOS_ACESSO_PADRAO = {"VOZ+DADOS", "VOZ", "DADOS"}
PRODUTO_M2M = "M2M"


# ---------------------------------------------------------------------------
# Parsing e agregação
# ---------------------------------------------------------------------------

def latest_published_month(rz: RemoteZip) -> Optional[str]:
    """Último mês publicado, lendo o membro sentinela. 'YYYY-MM' ou None."""
    best: Optional[tuple[int, int]] = None
    for i, raw in enumerate(rz.iter_lines(SENTINEL_MEMBER)):
        if i == 0:
            continue
        parts = _decode(raw).strip().split(";")
        if len(parts) < 2:
            continue
        try:
            ano, mes = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        if best is None or (ano, mes) > best:
            best = (ano, mes)
    return f"{best[0]:04d}-{best[1]:02d}" if best else None


def _norm_key(col: str) -> str:
    return re.sub(r"[^a-z0-9]", "", col.lower())


# Cabeçalho do CSV semestral (formato 2019+). Mapeamento tolerante como em
# anatel_sici.py: a Anatel já mudou nomes de coluna antes e voltará a mudar.
_COL_MAP: dict[str, str] = {
    "ano": "ano", "ms": "mes", "mes": "mes",
    "grupoeconmico": "grupo", "grupoeconomico": "grupo",
    "empresa": "empresa", "cnpj": "cnpj",
    "portedaprestadora": "porte",
    "uf": "uf", "municipio": "municipio", "municpio": "municipio",
    "cdigoibgemunicipio": "ibge", "codigoibgemunicipio": "ibge",
    "cdigoibgemunicpio": "ibge",
    "cdigonacional": "ddd", "codigonacional": "ddd",
    "modalidadedecobrana": "modalidade", "modalidadedecobranca": "modalidade",
    "tecnologia": "tecnologia",
    "tecnologiagerao": "geracao", "tecnologiageracao": "geracao",
    "tipodepessoa": "tipo_pessoa", "tipodeproduto": "produto",
    "acessos": "acessos",
}

_REQUIRED = {"ano", "mes", "cnpj", "ibge", "acessos"}


def _build_index(header: list[str]) -> dict[str, int]:
    index: dict[str, int] = {}
    for i, col in enumerate(header):
        field = _COL_MAP.get(_norm_key(col))
        if field and field not in index:
            index[field] = i
    missing = _REQUIRED - set(index)
    if missing:
        raise RuntimeError(f"colunas obrigatórias ausentes no CSV: {sorted(missing)}")
    return index


def _empty_cnpj_agg() -> dict:
    return {
        "empresa": "", "grupo": "", "porte": "", "uf": "",
        "acessos": 0, "pf": 0, "pj": 0, "acessos_m2m": 0, "acessos_outros": 0,
        "por_geracao": {}, "por_modalidade": {}, "por_produto": {},
        "por_municipio": {},
    }


def aggregate_period(rz: RemoteZip, member: str, log,
                     detail_months: set[str]) -> dict[str, dict]:
    """Agrega um membro semestral do CSV em {mes: {"cnpjs": {...}, "distrib_modalidade": {...}}}.

    `distrib_modalidade` é uma matriz nacional UF × tipo (pf/pj) × modalidade de
    cobrança — pequena, guardada para TODOS os meses processados, não só os de
    `detail_months` (mesmo espírito de `distrib_velocidade` no `anatel_sici`).
    """
    months: dict[str, dict] = {}
    lines = rz.iter_lines(member)
    header = _decode(next(lines)).lstrip("﻿").strip().split(";")
    ix = _build_index(header)
    n_cols = len(header)
    rows = skipped = 0

    for raw in lines:
        line = _decode(raw).rstrip("\r\n")
        if not line:
            continue
        r = line.split(";")
        if len(r) < n_cols:
            skipped += 1
            continue
        rows += 1

        cnpj = re.sub(r"\D", "", r[ix["cnpj"]])
        if len(cnpj) != 14:
            skipped += 1
            continue
        try:
            mes_key = f"{int(r[ix['ano']]):04d}-{int(r[ix['mes']]):02d}"
            acessos = int(r[ix["acessos"]] or 0)
        except ValueError:
            skipped += 1
            continue
        if acessos <= 0:
            continue

        mes_data = months.setdefault(mes_key, {"cnpjs": {}, "distrib_modalidade": {}})
        bucket = mes_data["cnpjs"]
        agg = bucket.get(cnpj)
        if agg is None:
            agg = bucket[cnpj] = _empty_cnpj_agg()
            agg["empresa"] = r[ix["empresa"]].strip() if "empresa" in ix else ""
            agg["grupo"] = r[ix["grupo"]].strip() if "grupo" in ix else ""
            agg["porte"] = r[ix["porte"]].strip() if "porte" in ix else ""
            agg["uf"] = r[ix["uf"]].strip() if "uf" in ix else ""

        produto = r[ix["produto"]].strip() if "produto" in ix else ""
        tipo_pessoa = r[ix["tipo_pessoa"]].strip() if "tipo_pessoa" in ix else ""
        is_pf = tipo_pessoa.startswith("Pessoa F")
        is_padrao = produto in PRODUTOS_ACESSO_PADRAO

        # `acessos`/`pf`/`pj`/`distrib_modalidade` só contam acesso padrão (voz/dados de
        # linha pessoal) — ver comentário de PRODUTOS_ACESSO_PADRAO. M2M e
        # PONTO_DE_SERVICO ficam só em `por_produto` e nos contadores dedicados abaixo.
        if is_padrao:
            agg["acessos"] += acessos
            if is_pf:
                agg["pf"] += acessos
            else:
                agg["pj"] += acessos
        elif produto == PRODUTO_M2M:
            agg["acessos_m2m"] += acessos
        else:
            agg["acessos_outros"] += acessos

        for key, field in (("geracao", "por_geracao"), ("modalidade", "por_modalidade"),
                           ("produto", "por_produto")):
            if key in ix:
                v = r[ix[key]].strip() or "N/I"
                agg[field][v] = agg[field].get(v, 0) + acessos

        if is_padrao and "modalidade" in ix:
            uf_key = r[ix["uf"]].strip() if "uf" in ix else "??"
            modalidade_v = r[ix["modalidade"]].strip() or "N/I"
            dm = mes_data["distrib_modalidade"].setdefault(uf_key, {"pf": {}, "pj": {}})
            tipo_key = "pf" if is_pf else "pj"
            dm[tipo_key][modalidade_v] = dm[tipo_key].get(modalidade_v, 0) + acessos

        if is_padrao and mes_key in detail_months:
            ibge = r[ix["ibge"]].strip()
            if ibge.isdigit():
                mun = agg["por_municipio"].get(ibge)
                if mun is None:
                    mun = agg["por_municipio"][ibge] = {
                        "uf": r[ix["uf"]].strip() if "uf" in ix else "",
                        "nome": r[ix["municipio"]].strip() if "municipio" in ix else "",
                        "acessos": 0, "pf": 0, "pj": 0,
                    }
                mun["acessos"] += acessos
                if is_pf:
                    mun["pf"] += acessos
                else:
                    mun["pj"] += acessos

    log.info("period aggregated", member=member, rows=rows, skipped=skipped,
             months=sorted(months))
    return months


def _finalize_month(mes_data: dict, mes: str) -> dict:
    """Fecha um mês: calcula derivados e descarta estruturas de trabalho."""
    bucket = mes_data["cnpjs"]
    total = 0
    for cnpj, agg in bucket.items():
        agg["municipios"] = len(agg["por_municipio"])
        agg["geracao_predominante"] = (
            max(agg["por_geracao"].items(), key=lambda kv: kv[1])[0]
            if agg["por_geracao"] else ""
        )
        total += agg["acessos"]
    return {"mes": mes, "generated_at": now_iso(), "cnpjs": bucket,
            "distrib_modalidade": mes_data.get("distrib_modalidade", {}),
            "total_acessos": total, "total_cnpjs": len(bucket)}


# ---------------------------------------------------------------------------
# Cache persistente
# ---------------------------------------------------------------------------

class SiciMovelCache:
    def __init__(self, base: Path):
        self.dir = base / "normalized" / "sici_movel_cache"
        self.months_dir = self.dir / "months"
        self.months_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.dir / "state.json"
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {"last_modified": "", "etag": "", "ultimo_mes": "", "membros": {}}

    def save_state(self) -> None:
        self.state["updated_at"] = now_iso()
        self.state_path.write_text(json.dumps(self.state, indent=2, ensure_ascii=False))

    def has_month(self, mes: str) -> bool:
        return (self.months_dir / f"{mes}.json.gz").exists()

    def write_month(self, mes: str, payload: dict) -> None:
        write_json_gz(self.months_dir / f"{mes}.json.gz", payload)

    def read_month(self, mes: str) -> Optional[dict]:
        path = self.months_dir / f"{mes}.json.gz"
        if not path.exists():
            return None
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)

    def months(self) -> list[str]:
        return sorted(p.stem.replace(".json", "")
                      for p in self.months_dir.glob("*.json.gz"))


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------

def _period_for_month(mes: str) -> tuple[int, str]:
    ano, m = (int(x) for x in mes.split("-"))
    return ano, ("1S" if m <= 6 else "2S")


def _prev_period(ano: int, sem: str) -> tuple[int, str]:
    return (ano - 1, "2S") if sem == "1S" else (ano, "1S")


def _last_month_of_period(ano: int, sem: str) -> str:
    return f"{ano:04d}-06" if sem == "1S" else f"{ano:04d}-12"


def _member_for_period(rz: RemoteZip, ano: int, sem: str) -> Optional[str]:
    name = f"Acessos_Telefonia_Movel_{ano}_{sem}.csv"
    return name if name in rz.members else None


def _all_period_members(rz: RemoteZip) -> list[str]:
    """Todos os membros semestrais no formato unificado (2019 em diante)."""
    return sorted(n for n in rz.members if _MEMBER_RE.match(n))


def build_snapshot_output(cache: SiciMovelCache, ultimo_mes: str, log) -> dict:
    """Monta o normalizado do snapshot: mês de referência completo + série histórica."""
    atual = cache.read_month(ultimo_mes)
    if not atual:
        raise RuntimeError(f"mês de referência {ultimo_mes} ausente do cache")

    serie: dict[str, list[list]] = {}
    totais: list[dict] = []
    for mes in cache.months():
        payload = cache.read_month(mes)
        if not payload:
            continue
        totais.append({"mes": mes, "acessos": payload.get("total_acessos", 0),
                       "cnpjs": payload.get("total_cnpjs", 0)})
        for cnpj, agg in payload.get("cnpjs", {}).items():
            serie.setdefault(cnpj, []).append(
                [mes, agg["acessos"], agg["pf"], agg["pj"]]
            )
    for v in serie.values():
        v.sort()

    return {
        "generated_at": now_iso(),
        "fonte": ANATEL_URL,
        "mes_referencia": ultimo_mes,
        "meses_disponiveis": cache.months(),
        "total_acessos": atual.get("total_acessos", 0),
        "total_cnpjs": atual.get("total_cnpjs", 0),
        "cnpjs": atual.get("cnpjs", {}),
        "distrib_modalidade": atual.get("distrib_modalidade", {}),
        "serie_por_cnpj": serie,
        "serie_total": totais,
    }


def run(date_str: str, base: Path, log, bootstrap: bool = False,
        force_full: bool = False) -> dict:
    cache = SiciMovelCache(base)
    norm_dir = normalized_path(base, date_str, "summary")
    norm_dir.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=300, follow_redirects=True) as client:
        rz = RemoteZip(ANATEL_URL, client, log)
        rz.open()

        ultimo_mes = latest_published_month(rz)
        if not ultimo_mes:
            raise RuntimeError("não foi possível determinar o último mês publicado")
        log.info("latest published month", mes=ultimo_mes,
                 cached=cache.state.get("ultimo_mes"))

        detail = set()
        ano_ref, mes_ref = (int(x) for x in ultimo_mes.split("-"))
        for _ in range(MUNICIPIO_DETAIL_MONTHS):
            detail.add(f"{ano_ref:04d}-{mes_ref:02d}")
            mes_ref -= 1
            if mes_ref == 0:
                ano_ref, mes_ref = ano_ref - 1, 12

        if bootstrap:
            members = _all_period_members(rz)
            log.info("bootstrap: processing all period members", members=len(members))
        elif force_full or not cache.has_month(ultimo_mes):
            ano, sem = _period_for_month(ultimo_mes)
            member = _member_for_period(rz, ano, sem)
            if not member:
                raise RuntimeError(f"membro do período {ano}_{sem} não encontrado no ZIP")
            members = [member]
            # Virada de semestre: se o semestre anterior não está completo no cache,
            # processa junto (mesmo espírito do rollover de ano no `anatel_sici`).
            prev_ano, prev_sem = _prev_period(ano, sem)
            prev_member = _member_for_period(rz, prev_ano, prev_sem)
            if prev_member and not cache.has_month(_last_month_of_period(prev_ano, prev_sem)):
                members.append(prev_member)
                log.info("period rollover: also processing previous period", member=prev_member)
        else:
            members = []
            log.info("no new month — skipping download", mes=ultimo_mes)

        for member in members:
            months = aggregate_period(rz, member, log, detail)
            for mes, mes_data in months.items():
                # Mês já congelado e fora da janela de detalhe não é reescrito.
                if not force_full and cache.has_month(mes) and mes not in detail:
                    continue
                cache.write_month(mes, _finalize_month(mes_data, mes))
            cache.state.setdefault("membros", {})[member] = {
                "processed_at": now_iso(), "meses": sorted(months),
            }

        cache.state["last_modified"] = rz.last_modified
        cache.state["etag"] = rz.etag
        cache.state["ultimo_mes"] = ultimo_mes
        cache.save_state()

    output = build_snapshot_output(cache, ultimo_mes, log)
    out_path = norm_dir / "sici_movel_acessos.json.gz"
    write_json_gz(out_path, output)
    log.info("sici_movel_acessos saved", path=str(out_path), mes=ultimo_mes,
             cnpjs=output["total_cnpjs"], acessos=output["total_acessos"],
             meses=len(output["meses_disponiveis"]))
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="`anatel_sici_movel` — acessos de telefonia móvel/SMP (Anatel/SICI)")
    parser.add_argument("--date", default=today_str(),
                        help="Data do snapshot (YYYY-MM-DD); padrão: hoje")
    parser.add_argument("--bootstrap", action="store_true",
                        help="Processa todo o histórico unificado (2019→hoje). Use na 1ª execução.")
    parser.add_argument("--force-full", action="store_true",
                        help="Ignora o cache e reprocessa o semestre corrente")
    args = parser.parse_args(argv)

    log = configure_logging()
    base = data_dir()

    try:
        run(date_str=args.date, base=base, log=log,
            bootstrap=args.bootstrap, force_full=args.force_full)
    except httpx.HTTPStatusError as exc:
        log.error("http error", status=exc.response.status_code, url=str(exc.request.url))
        return 1
    except Exception:
        log.exception("unexpected error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
