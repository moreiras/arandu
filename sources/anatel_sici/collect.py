# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`anatel_sici` — Acessos de banda larga fixa declarados ao SICI (Anatel).

O SICI (Sistema de Coleta de Informações) é a declaração mensal obrigatória de toda
prestadora de telecomunicações à Anatel. Este módulo ingere a base pública de acessos
de banda larga fixa: quantos acessos em serviço cada CNPJ tem, em que município, com
que velocidade contratada, tecnologia, meio de acesso e tipo de cliente (PF/PJ).

Fonte: https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/
       acessos_banda_larga_fixa.zip   (~1 GB, atualizado mensalmente)

ESTRATÉGIA INCREMENTAL
----------------------
O servidor aceita HTTP Range, então nunca baixamos o ZIP inteiro:

  1. Lê o fim do arquivo → diretório central do ZIP → offsets de cada membro.
  2. Baixa e infla `Acessos_Banda_Larga_Fixa_Total.csv` (3,5 KB) para descobrir o
     último mês publicado. Custo: ~1 MB de tráfego.
  3. Se não há mês novo, encerra sem processar nada (caso comum: pipeline é semanal,
     o dado é mensal).
  4. Se há, baixa apenas o membro do ANO CORRENTE (~80 MB) e reprocessa esse ano.
  5. Meses de anos fechados são processados uma única vez (bootstrap ou virada de ano)
     e ficam congelados no cache.

Cache persistente (fora dos snapshots imutáveis, como geo_cache/):
  data/normalized/sici_cache/state.json          — controle de atualização
  data/normalized/sici_cache/months/{YYYY-MM}.json.gz — agregado imutável de um mês

Saída por snapshot:
  data/normalized/{date}/summary/sici_acessos.json.gz

Uso:
    python -m sources.anatel_sici.collect
    python -m sources.anatel_sici.collect --date 2026-06-28
    python -m sources.anatel_sici.collect --bootstrap      # processa todo o histórico
    python -m sources.anatel_sici.collect --force-full     # ignora o cache e refaz o ano
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import re
import struct
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

import httpx

from core.common import (
    configure_logging,
    data_dir,
    normalized_path,
    now_iso,
    today_str,
    write_json_gz,
)

ANATEL_URL = (
    "https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/"
    "acessos_banda_larga_fixa.zip"
)

# Membro sentinela: 3,5 KB com uma linha por mês (Ano;Mês;Acessos). Descobrir o último
# mês publicado custa ~1 MB de tráfego em vez de 1 GB.
SENTINEL_MEMBER = "Acessos_Banda_Larga_Fixa_Total.csv"

# Bytes lidos do fim do arquivo para localizar o diretório central do ZIP.
# O diretório tem 27 membros; 2 MB cobrem com folga.
TAIL_BYTES = 2 * 1024 * 1024

# Só os 12 meses mais recentes guardam detalhe por município; meses anteriores ficam
# apenas com os totais por CNPJ. Mantém a série de 2007 em diante sem explodir tamanho.
MUNICIPIO_DETAIL_MONTHS = 12

# Tipo de Produto que representa acesso de banda larga propriamente dito. Os demais
# (LINHA_DEDICADA, OUTROS, M2M) somam <1% dos acessos mas contêm links de backbone
# declarados como acesso — há médias de 47 Tbps/acesso neles.
PRODUTO_INTERNET = "INTERNET"

# Nome do membro por ano/período. O ZIP mistura períodos multi-ano (2007-2010) com
# anos isolados (2021+), e ainda alterna "-" e "_" no membro _Colunas.
_MEMBER_RE = re.compile(r"^Acessos_Banda_Larga_Fixa_(\d{4}(?:-\d{4})?)\.csv$")


# ---------------------------------------------------------------------------
# Leitura remota do ZIP via HTTP Range
# ---------------------------------------------------------------------------

class RemoteZip:
    """Acesso a membros individuais de um ZIP remoto via HTTP Range.

    Evita baixar 1 GB para ler um membro de 3,5 KB. Requer que o servidor responda
    206 Partial Content — o da Anatel responde.
    """

    def __init__(self, url: str, client: httpx.Client, log):
        self.url = url
        self.client = client
        self.log = log
        self.total_size = 0
        self.last_modified = ""
        self.etag = ""
        self.members: dict[str, tuple[int, int, int]] = {}  # nome → (offset, csize, usize)

    def open(self) -> None:
        head = self.client.head(self.url)
        head.raise_for_status()
        self.total_size = int(head.headers.get("content-length", 0))
        self.last_modified = head.headers.get("last-modified", "")
        self.etag = head.headers.get("etag", "")
        if not self.total_size:
            raise RuntimeError("servidor não informou content-length")

        start = max(0, self.total_size - TAIL_BYTES)
        tail = self._range(start, self.total_size - 1)
        self._parse_central_directory(tail)
        self.log.info("remote zip opened", size_mb=round(self.total_size / 1_048_576, 1),
                      members=len(self.members), last_modified=self.last_modified)

    def _range(self, start: int, end: int) -> bytes:
        resp = self.client.get(self.url, headers={"Range": f"bytes={start}-{end}"})
        if resp.status_code not in (200, 206):
            resp.raise_for_status()
        if resp.status_code == 200:
            # Servidor ignorou o Range e mandou tudo — fatia localmente.
            return resp.content[start : end + 1]
        return resp.content

    def _parse_central_directory(self, tail: bytes) -> None:
        """Extrai nome, offset e tamanhos de cada membro do diretório central."""
        for m in re.finditer(b"PK\x01\x02", tail):
            o = m.start()
            if o + 46 > len(tail):
                continue
            try:
                method, = struct.unpack("<H", tail[o + 10 : o + 12])
                csize, usize = struct.unpack("<II", tail[o + 20 : o + 28])
                name_len, extra_len, comment_len = struct.unpack("<HHH", tail[o + 28 : o + 34])
                offset, = struct.unpack("<I", tail[o + 42 : o + 46])
                name = tail[o + 46 : o + 46 + name_len].decode("latin-1")
            except (struct.error, UnicodeDecodeError):
                continue
            if not name or method not in (0, 8):
                continue
            self.members[name] = (offset, csize, usize)

    def iter_lines(self, name: str) -> Iterator[bytes]:
        """Itera as linhas de um membro, inflando em stream (memória constante)."""
        if name not in self.members:
            raise KeyError(f"membro '{name}' não está no ZIP")
        offset, csize, _ = self.members[name]

        # Cabeçalho local: 30 bytes fixos + nome + extra (podem diferir do central).
        header = self._range(offset, offset + 29)
        name_len, extra_len = struct.unpack("<HH", header[26:30])
        data_start = offset + 30 + name_len + extra_len
        raw = self._range(data_start, data_start + csize - 1)

        decomp = zlib.decompressobj(-15)
        tail = b""
        for i in range(0, len(raw), 1 << 20):
            chunk = decomp.decompress(raw[i : i + (1 << 20)])
            if not chunk:
                continue
            lines = (tail + chunk).split(b"\n")
            tail = lines.pop()
            yield from lines
        rest = decomp.flush()
        if rest:
            lines = (tail + rest).split(b"\n")
            tail = lines.pop()
            yield from lines
        if tail:
            yield tail


# ---------------------------------------------------------------------------
# Parsing e agregação
# ---------------------------------------------------------------------------

def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="replace")


def latest_published_month(rz: RemoteZip) -> Optional[str]:
    """Último mês publicado, lendo o membro sentinela de 3,5 KB. 'YYYY-MM' ou None."""
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


# Cabeçalho atual do CSV anual. Mapeamento tolerante como em anatel_scm.py: a Anatel
# já mudou nomes de coluna antes e voltará a mudar.
_COL_MAP: dict[str, str] = {
    "ano": "ano", "ms": "mes", "mes": "mes",
    "grupoeconmico": "grupo", "grupoeconomico": "grupo",
    "empresa": "empresa", "cnpj": "cnpj",
    "portedaprestadora": "porte",
    "uf": "uf", "municipio": "municipio", "municpio": "municipio",
    "cdigoibgemunicipio": "ibge", "codigoibgemunicipio": "ibge",
    "cdigoibgemunicpio": "ibge",
    "faixadevelocidade": "faixa", "velocidade": "velocidade",
    "tecnologia": "tecnologia", "meiodeacesso": "meio",
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
        "acessos": 0, "pf": 0, "pj": 0,
        "acessos_internet": 0, "capacidade_mbps": 0.0, "capacidade_internet_mbps": 0.0,
        "por_tecnologia": {}, "por_meio": {}, "por_faixa": {}, "por_produto": {},
        "por_municipio": {},
        "_vel": [],   # amostra para mediana; removido antes de serializar
    }


def aggregate_year(rz: RemoteZip, member: str, log,
                   detail_months: set[str]) -> dict[str, dict]:
    """Agrega um membro anual do CSV em {mes: {"cnpjs": {cnpj: agregado}, "distrib_velocidade": {...}}}.

    `detail_months` são os meses que guardam detalhe por município; os demais ficam
    só com totais. `distrib_velocidade` é uma matriz nacional UF × tipo (pf/pj) × faixa
    de velocidade — pequena (algumas centenas de células), guardada para TODOS os
    meses processados, não só os de `detail_months`.
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

        mes_data = months.setdefault(mes_key, {"cnpjs": {}, "distrib_velocidade": {}})
        bucket = mes_data["cnpjs"]
        agg = bucket.get(cnpj)
        if agg is None:
            agg = bucket[cnpj] = _empty_cnpj_agg()
            agg["empresa"] = r[ix["empresa"]].strip() if "empresa" in ix else ""
            agg["grupo"] = r[ix["grupo"]].strip() if "grupo" in ix else ""
            agg["porte"] = r[ix["porte"]].strip() if "porte" in ix else ""
            agg["uf"] = r[ix["uf"]].strip() if "uf" in ix else ""

        try:
            vel = float(r[ix["velocidade"]].replace(",", ".")) if "velocidade" in ix else 0.0
        except ValueError:
            vel = 0.0
        produto = r[ix["produto"]].strip() if "produto" in ix else ""
        tipo_pessoa = r[ix["tipo_pessoa"]].strip() if "tipo_pessoa" in ix else ""
        is_pf = tipo_pessoa.startswith("Pessoa F")
        is_internet = produto == PRODUTO_INTERNET

        agg["acessos"] += acessos
        if is_pf:
            agg["pf"] += acessos
        else:
            agg["pj"] += acessos
        cap = vel * acessos
        agg["capacidade_mbps"] += cap
        if is_internet:
            agg["acessos_internet"] += acessos
            agg["capacidade_internet_mbps"] += cap
            if vel > 0 and len(agg["_vel"]) < 20000:
                agg["_vel"].append((vel, acessos))

        for key, field in (("tecnologia", "por_tecnologia"), ("meio", "por_meio"),
                           ("faixa", "por_faixa"), ("produto", "por_produto")):
            if key in ix:
                v = r[ix[key]].strip() or "N/I"
                agg[field][v] = agg[field].get(v, 0) + acessos

        if is_internet and "faixa" in ix:
            uf_key = r[ix["uf"]].strip() if "uf" in ix else "??"
            faixa_v = r[ix["faixa"]].strip() or "N/I"
            dv = mes_data["distrib_velocidade"].setdefault(uf_key, {"pf": {}, "pj": {}})
            tipo_key = "pf" if is_pf else "pj"
            dv[tipo_key][faixa_v] = dv[tipo_key].get(faixa_v, 0) + acessos

        if mes_key in detail_months:
            ibge = r[ix["ibge"]].strip()
            if ibge.isdigit():
                mun = agg["por_municipio"].get(ibge)
                if mun is None:
                    mun = agg["por_municipio"][ibge] = {
                        "uf": r[ix["uf"]].strip() if "uf" in ix else "",
                        "nome": r[ix["municipio"]].strip() if "municipio" in ix else "",
                        "acessos": 0, "pf": 0, "pj": 0, "capacidade_mbps": 0.0, "fibra": 0,
                    }
                mun["acessos"] += acessos
                # Fibra = meio de acesso "Fibra" (FTTH/FTTB); o % de fibra por município sai daqui.
                if "meio" in ix and r[ix["meio"]].strip() == "Fibra":
                    mun["fibra"] = mun.get("fibra", 0) + acessos
                if is_pf:
                    mun["pf"] += acessos
                else:
                    mun["pj"] += acessos
                mun["capacidade_mbps"] += cap

    log.info("year aggregated", member=member, rows=rows, skipped=skipped,
             months=sorted(months))
    return months


def _finalize_month(mes_data: dict, mes: str) -> dict:
    """Fecha um mês: calcula derivados e descarta estruturas de trabalho."""
    bucket = mes_data["cnpjs"]
    total = 0
    for cnpj, agg in bucket.items():
        vel = agg.pop("_vel", [])
        agg["velocidade_mediana_mbps"] = _weighted_median(vel)
        agg["municipios"] = len(agg["por_municipio"])
        base = agg["acessos_internet"] or agg["acessos"]
        agg["velocidade_media_mbps"] = round(
            (agg["capacidade_internet_mbps"] or agg["capacidade_mbps"]) / base, 2
        ) if base else 0.0
        agg["capacidade_mbps"] = round(agg["capacidade_mbps"], 2)
        agg["capacidade_internet_mbps"] = round(agg["capacidade_internet_mbps"], 2)
        for mun in agg["por_municipio"].values():
            mun["capacidade_mbps"] = round(mun["capacidade_mbps"], 2)
        agg["tecnologia_predominante"] = (
            max(agg["por_tecnologia"].items(), key=lambda kv: kv[1])[0]
            if agg["por_tecnologia"] else ""
        )
        agg["meio_predominante"] = (
            max(agg["por_meio"].items(), key=lambda kv: kv[1])[0]
            if agg["por_meio"] else ""
        )
        total += agg["acessos"]
    return {"mes": mes, "generated_at": now_iso(), "cnpjs": bucket,
            "distrib_velocidade": mes_data.get("distrib_velocidade", {}),
            "total_acessos": total, "total_cnpjs": len(bucket)}


def _weighted_median(pairs: list[tuple[float, int]]) -> float:
    """Mediana da velocidade ponderada pelo número de acessos."""
    if not pairs:
        return 0.0
    pairs = sorted(pairs)
    half = sum(w for _, w in pairs) / 2
    acc = 0.0
    for vel, w in pairs:
        acc += w
        if acc >= half:
            return round(vel, 2)
    return round(pairs[-1][0], 2)


# ---------------------------------------------------------------------------
# Cache persistente
# ---------------------------------------------------------------------------

class SiciCache:
    def __init__(self, base: Path):
        self.dir = base / "normalized" / "sici_cache"
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

def _member_for_year(rz: RemoteZip, year: int) -> Optional[str]:
    """Membro anual que contém um ano — cobre períodos multi-ano como 2007-2010."""
    for name in rz.members:
        m = _MEMBER_RE.match(name)
        if not m:
            continue
        span = m.group(1)
        if "-" in span:
            ini, fim = (int(x) for x in span.split("-"))
            if ini <= year <= fim:
                return name
        elif int(span) == year:
            return name
    return None


def _all_year_members(rz: RemoteZip) -> list[str]:
    return sorted(n for n in rz.members if _MEMBER_RE.match(n))


def _detail_window(ultimo_mes: str) -> set[str]:
    """Os MUNICIPIO_DETAIL_MONTHS meses que guardam detalhe municipal."""
    ano, mes = (int(x) for x in ultimo_mes.split("-"))
    out = set()
    for _ in range(MUNICIPIO_DETAIL_MONTHS):
        out.add(f"{ano:04d}-{mes:02d}")
        mes -= 1
        if mes == 0:
            ano, mes = ano - 1, 12
    return out


def build_snapshot_output(cache: SiciCache, ultimo_mes: str, log) -> dict:
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
        "distrib_velocidade": atual.get("distrib_velocidade", {}),
        "serie_por_cnpj": serie,
        "serie_total": totais,
    }


def run(date_str: str, base: Path, log, bootstrap: bool = False,
        force_full: bool = False) -> dict:
    cache = SiciCache(base)
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

        detail = _detail_window(ultimo_mes)

        if bootstrap:
            members = _all_year_members(rz)
            log.info("bootstrap: processing all year members", members=len(members))
        elif force_full or not cache.has_month(ultimo_mes):
            year = int(ultimo_mes[:4])
            member = _member_for_year(rz, year)
            if not member:
                raise RuntimeError(f"membro do ano {year} não encontrado no ZIP")
            members = [member]
            # Virada de ano: se o ano anterior não está no cache, processa junto.
            prev = _member_for_year(rz, year - 1)
            if prev and not cache.has_month(f"{year - 1}-12"):
                members.append(prev)
                log.info("year rollover: also processing previous year", member=prev)
        else:
            members = []
            log.info("no new month — skipping download", mes=ultimo_mes)

        for member in members:
            months = aggregate_year(rz, member, log, detail)
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
    out_path = norm_dir / "sici_acessos.json.gz"
    write_json_gz(out_path, output)
    log.info("sici_acessos saved", path=str(out_path), mes=ultimo_mes,
             cnpjs=output["total_cnpjs"], acessos=output["total_acessos"],
             meses=len(output["meses_disponiveis"]))
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="`anatel_sici` — acessos de banda larga fixa (Anatel/SICI)")
    parser.add_argument("--date", default=today_str(),
                        help="Data do snapshot (YYYY-MM-DD); padrão: hoje")
    parser.add_argument("--bootstrap", action="store_true",
                        help="Processa todo o histórico (2007→hoje). Use na 1ª execução.")
    parser.add_argument("--force-full", action="store_true",
                        help="Ignora o cache e reprocessa o ano corrente")
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
