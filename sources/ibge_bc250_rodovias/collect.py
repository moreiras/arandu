# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`ibge_bc250_rodovias` — Coleta da malha rodoviária nacional da Base Cartográfica Contínua do
IBGE (BC250).

Relevância para o Arandurape: faixas de domínio de rodovias frequentemente
carregam cabos OPGW ou dutos de fibra óptica lançados por concessionárias ou
por terceiros para telecom de longa distância — mesmo espírito das camadas de
linhas de transmissão (`aneel_sigel_transmission`, `sources/aneel_sigel_transmission`). O IBGE não
indica quais trechos têm fibra; este coletor publica só a malha viária em si.

Fonte:       https://geoftp.ibge.gov.br/cartas_e_mapas/bases_cartograficas_continuas/bc250/versao2025/shapefiles/bc_250_shapefiles_2026_03_03.zip
Camada:      rod_trecho_rodoviario_l (shapefile dentro do zip), 124.687 feições
Normalizado: data/normalized/{date}/summary/ibge_rodovias.json.gz

Uso:
    python -m sources.ibge_bc250_rodovias.collect
    python -m sources.ibge_bc250_rodovias.collect --date 2026-09-26

Pegadinhas confirmadas em levantamento manual (2026-09-26):
  - O zip do BC250 cobre TODOS os temas do Brasil inteiro (761 MB) — baixá-lo
    inteiro toda semana seria desperdício para um dado que muda a cada ~2 anos
    (última mudança de versão: 2023 → 2025, ~15 meses). O servidor do IBGE
    aceita HTTP Range (`Accept-Ranges: bytes`), então este coletor lê só o
    diretório central do zip (últimos ~8 MB) e depois baixa por Range só os 4
    membros do shapefile de interesse (~47,5 MB comprimidos, não 761 MB).
  - Sem bibliotecas de shapefile/GIS no worker (`pyshp`/`fiona`/GDAL não estão
    instalados) — este coletor faz parsing binário nativo de `.shp` (formato
    Esri Shapefile, shape type 3 = PolyLine, sem Z/M) e `.dbf` (dBASE III,
    campos de largura fixa), sem dependências externas além de stdlib+httpx.
  - Geometria em `GCS_SIRGAS_2000` (graus) — compatível com WGS84 para fins de
    visualização web, sem reprojeção necessária.
  - Existe uma segunda camada quase idêntica no mesmo zip,
    `rod_via_deslocamento_l` (124.688 feições) — não usada aqui;
    `rod_trecho_rodoviario_l` é a camada temática com `sigla` de rodovia
    (ex.: "BR-101"), mais útil para filtros e popups.
  - `jurisdicao`/`revestimen` têm proporção alta de "Desconhecida"/valores
    vazios (49% e <0,1% respectivamente) — limitação do dado fonte do IBGE,
    não um problema de parsing deste coletor.
"""

from __future__ import annotations

import argparse
import struct
import sys
import zlib

import httpx

from core.common import (
    configure_logging,
    data_dir,
    normalized_path,
    now_iso,
    today_str,
    write_json_gz,
)
from core.site import USER_AGENT

ZIP_URL = (
    "https://geoftp.ibge.gov.br/cartas_e_mapas/bases_cartograficas_continuas/"
    "bc250/versao2025/shapefiles/bc_250_shapefiles_2026_03_03.zip"
)
SOURCE = "IBGE — Base Cartográfica Contínua 1:250.000 (BC250 versão 2025), camada rod_trecho_rodoviario_l"

LAYER_BASENAME = "rod_trecho_rodoviario_l"
MEMBERS = [f"{LAYER_BASENAME}.{ext}" for ext in ("shp", "shx", "dbf")]

# Diretório central do zip fica no fim do arquivo; 355 membros no total no zip
# atual do BC250 cabem folgadamente nos últimos 8 MB.
CENTRAL_DIR_TAIL_BYTES = 8 * 1024 * 1024

# Campos do .dbf mapeados para nomes estáveis no GeoJSON publicado (o IBGE já
# truncou os nomes originais em 10 caracteres, formato dBASE).
_DBF_FIELD_MAP = {
    "tipovia": "tipo_via",
    "jurisdicao": "jurisdicao",
    "administra": "administracao",
    "concession": "concessionaria",
    "revestimen": "revestimento",
    "operaciona": "operacional",
    "situacaofi": "situacao",
    "trafego": "trafego",
    "sigla": "sigla",
    "codtrechor": "codigo_trecho",
    "nrpistas": "nr_pistas",
    "nrfaixas": "nr_faixas",
    "limitevelo": "limite_velocidade_kmh",
}

_PAVIMENTADA_TRUE = ("pavimentado",)
_PAVIMENTADA_FALSE = ("sem revestimento", "leito natural", "primário (solto)", "primario (solto)")


def _make_client() -> httpx.Client:
    headers = {"User-Agent": USER_AGENT}
    return httpx.Client(headers=headers, timeout=120, follow_redirects=True)


# ---------------------------------------------------------------------------
# Acesso a membros individuais de um zip remoto via HTTP Range
# ---------------------------------------------------------------------------

class RemoteZip:
    """Lê membros específicos de um zip remoto via HTTP Range, sem baixá-lo
    inteiro. Assume que os membros de interesse cabem em memória inflados
    (ao contrário de `sources/anatel_sici/collect.py`, que faz streaming para
    membros de ~GB — aqui os maiores membros são dezenas de MB)."""

    def __init__(self, url: str, client: httpx.Client, log):
        self.url = url
        self.client = client
        self.log = log
        self.total_size = 0
        self.members: dict[str, tuple[int, int, int, int]] = {}  # nome -> (offset, csize, usize, method)

    def open(self) -> None:
        head = self.client.head(self.url)
        head.raise_for_status()
        self.total_size = int(head.headers.get("content-length", 0))
        if not self.total_size:
            raise RuntimeError("servidor não informou content-length")

        start = max(0, self.total_size - CENTRAL_DIR_TAIL_BYTES)
        tail = self._range(start, self.total_size - 1)
        self._parse_central_directory(tail)
        self.log.info("remote zip opened", size_mb=round(self.total_size / 1_048_576, 1),
                      members=len(self.members))

    def _range(self, start: int, end: int) -> bytes:
        resp = self.client.get(self.url, headers={"Range": f"bytes={start}-{end}"})
        if resp.status_code not in (200, 206):
            resp.raise_for_status()
        if resp.status_code == 200:
            return resp.content[start : end + 1]
        return resp.content

    def _parse_central_directory(self, tail: bytes) -> None:
        for m_start in _find_all(tail, b"PK\x01\x02"):
            o = m_start
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
            self.members[name] = (offset, csize, usize, method)

    def read_member(self, name: str) -> bytes:
        """Baixa e infla um membro inteiro (assume que cabe em memória)."""
        if name not in self.members:
            raise KeyError(f"membro '{name}' não está no diretório central do zip")
        offset, csize, usize, method = self.members[name]

        header = self._range(offset, offset + 29)
        name_len, extra_len = struct.unpack("<HH", header[26:30])
        data_start = offset + 30 + name_len + extra_len
        raw = self._range(data_start, data_start + csize - 1)
        data = zlib.decompress(raw, -15) if method == 8 else raw
        if len(data) != usize:
            raise RuntimeError(
                f"membro '{name}': tamanho inflado {len(data)} != esperado {usize}"
            )
        return data


def _find_all(haystack: bytes, needle: bytes):
    start = 0
    while True:
        idx = haystack.find(needle, start)
        if idx == -1:
            return
        yield idx
        start = idx + 1


# ---------------------------------------------------------------------------
# Parsing binário do .dbf (dBASE III, campos de largura fixa)
# ---------------------------------------------------------------------------

def _parse_dbf(data: bytes) -> list[dict]:
    n_records, = struct.unpack("<I", data[4:8])
    header_len, record_len = struct.unpack("<HH", data[8:12])

    fields: list[tuple[str, int]] = []
    pos = 32
    while data[pos] != 0x0D:
        name = data[pos : pos + 11].rstrip(b"\x00").decode("latin-1")
        flen = data[pos + 16]
        fields.append((name, flen))
        pos += 32

    records = []
    rec_start = header_len
    for _ in range(n_records):
        rec = data[rec_start : rec_start + record_len]
        rec_start += record_len
        vals: dict[str, str] = {}
        p = 1  # byte 0 é a flag de exclusão lógica
        for name, flen in fields:
            raw_v = rec[p : p + flen]
            try:
                vals[name] = raw_v.decode("utf-8").strip()
            except UnicodeDecodeError:
                vals[name] = raw_v.decode("latin-1", errors="replace").strip()
            p += flen
        records.append(vals)
    return records


# ---------------------------------------------------------------------------
# Parsing binário do .shp (Esri Shapefile, shape type 3 = PolyLine)
# ---------------------------------------------------------------------------

def _parse_shp(data: bytes, log) -> list[dict | None]:
    file_length_words, = struct.unpack(">I", data[24:28])
    shape_type, = struct.unpack("<I", data[32:36])
    if shape_type != 3:
        raise RuntimeError(f"tipo de geometria inesperado no .shp: {shape_type} (esperado 3 = PolyLine)")

    geometries: list[dict | None] = []
    pos = 100  # fim do header fixo
    end = file_length_words * 2
    suspect_dup = 0
    while pos < end:
        record_number, content_length_words = struct.unpack(">II", data[pos : pos + 8])
        content_start = pos + 8
        content_len = content_length_words * 2
        rec_shape_type, = struct.unpack("<I", data[content_start : content_start + 4])

        if rec_shape_type == 0:  # null shape
            geometries.append(None)
        else:
            num_parts, num_points = struct.unpack("<ii", data[content_start + 36 : content_start + 44])
            parts_start = content_start + 44
            parts = list(struct.unpack(f"<{num_parts}i", data[parts_start : parts_start + 4 * num_parts]))
            points_start = parts_start + 4 * num_parts
            coords = struct.unpack(f"<{num_points * 2}d", data[points_start : points_start + 16 * num_points])
            xy = [[round(coords[i * 2], 5), round(coords[i * 2 + 1], 5)] for i in range(num_points)]

            bounds = parts + [num_points]
            paths = [xy[bounds[i] : bounds[i + 1]] for i in range(num_parts)]
            paths = [p for p in paths if len(p) >= 2]
            if any(len(set(map(tuple, p))) < max(2, len(p) // 3) for p in paths):
                suspect_dup += 1

            if not paths:
                geometries.append(None)
            elif len(paths) == 1:
                geometries.append({"type": "LineString", "coordinates": paths[0]})
            else:
                geometries.append({"type": "MultiLineString", "coordinates": paths})

        pos = content_start + content_len

    if suspect_dup:
        log.warning("shp com partes suspeitas de vértices duplicados", count=suspect_dup)
    return geometries


# ---------------------------------------------------------------------------
# Normalização
# ---------------------------------------------------------------------------

def _to_number(raw: str) -> float | int | None:
    raw = raw.strip().strip("*")
    if not raw:
        return None
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        return None


def _pavimentada(revestimento: str) -> bool | None:
    low = revestimento.lower()
    if any(tok in low for tok in _PAVIMENTADA_TRUE):
        return True
    if any(tok in low for tok in _PAVIMENTADA_FALSE):
        return False
    return None


def _normalize_record(geometry: dict | None, attrs: dict) -> dict | None:
    if geometry is None:
        return None

    props = {}
    for dbf_name, out_name in _DBF_FIELD_MAP.items():
        raw = attrs.get(dbf_name, "")
        if out_name in ("nr_pistas", "nr_faixas", "limite_velocidade_kmh"):
            props[out_name] = _to_number(raw)
        else:
            props[out_name] = raw or None
    props["pavimentada"] = _pavimentada(attrs.get("revestimen", ""))

    return {"type": "Feature", "geometry": geometry, "properties": props}


def run(date_str: str, base, log) -> dict:
    """Coleta a malha rodoviária nacional (camada rod_trecho_rodoviario_l do
    BC250), baixando só os membros do shapefile de interesse via HTTP Range.

    Returns:
        O dict normalizado gravado em disco: features GeoJSON e total.
    """
    norm_dir = normalized_path(base, date_str, "summary")
    norm_dir.mkdir(parents=True, exist_ok=True)

    with _make_client() as client:
        rz = RemoteZip(ZIP_URL, client, log)
        rz.open()

        missing = [m for m in MEMBERS if m not in rz.members]
        if missing:
            raise RuntimeError(f"membros do shapefile não encontrados no zip: {missing}")

        dbf_bytes = rz.read_member(f"{LAYER_BASENAME}.dbf")
        shp_bytes = rz.read_member(f"{LAYER_BASENAME}.shp")

    log.info("membros baixados", dbf_mb=round(len(dbf_bytes) / 1_048_576, 1),
              shp_mb=round(len(shp_bytes) / 1_048_576, 1))

    attrs_list = _parse_dbf(dbf_bytes)
    geometries = _parse_shp(shp_bytes, log)

    if len(attrs_list) != len(geometries):
        raise RuntimeError(
            f".dbf tem {len(attrs_list)} registros mas .shp tem {len(geometries)} "
            "— formato inesperado, abortando em vez de casar dados errados"
        )

    features = []
    for geometry, attrs in zip(geometries, attrs_list):
        norm = _normalize_record(geometry, attrs)
        if norm is not None:
            features.append(norm)

    normalized = {
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "source": SOURCE,
        "total": len(features),
        "features": features,
    }
    norm_file = norm_dir / "ibge_rodovias.json.gz"
    write_json_gz(norm_file, normalized)

    log.info("ibge_bc250_rodovias done", total=len(features))
    return normalized


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="`ibge_bc250_rodovias` — coleta da malha rodoviária nacional do IBGE (BC250)"
    )
    parser.add_argument("--date", default=today_str(),
                        help="Data do snapshot (YYYY-MM-DD); padrão: hoje")
    args = parser.parse_args(argv)

    log = configure_logging()
    base = data_dir()

    try:
        run(date_str=args.date, base=base, log=log)
    except httpx.HTTPStatusError as exc:
        log.error("http error", status=exc.response.status_code, url=str(exc.request.url))
        return 1
    except httpx.RequestError as exc:
        log.error("connection error", error=str(exc))
        return 1
    except Exception:
        log.exception("unexpected error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
