# SPDX-License-Identifier: AGPL-3.0-or-later
"""T1 — fixtures dos testes de coletor/normalizador: formato original → normalizado, sem rede."""
import gzip
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "raw"
DATE = "2026-09-20"


@pytest.fixture()
def fx():
    """Caminho de uma amostra real: fx("registro_br", "nicbr-asn-blk.sample.txt")."""
    def _fx(*parts: str) -> Path:
        p = FIXTURES.joinpath(*parts)
        assert p.exists(), f"amostra ausente: {p}"
        return p
    return _fx


@pytest.fixture()
def base(tmp_path):
    """DATA_DIR temporário (raiz de raw/ normalized/ published/)."""
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture()
def log():
    from core.common import configure_logging
    return configure_logging()


@pytest.fixture()
def date_str():
    return DATE


def read_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def write_gz(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def volatile(d, keys=("generated_at", "fetched_at")):
    """Remove campos voláteis (timestamps) para comparar execuções."""
    if isinstance(d, dict):
        return {k: volatile(v, keys) for k, v in d.items() if k not in keys}
    if isinstance(d, list):
        return [volatile(x, keys) for x in d]
    return d


def make_zip(member: str, content: bytes) -> bytes:
    """ZIP em memória com um único membro — como a Anatel entrega os CSVs."""
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(member, content)
    return buf.getvalue()


def mount_range_zip(respx_mock, url: str, members: dict[str, bytes], last_modified="Tue, 07 Jul 2026 10:00:00 GMT", etag='"v1"'):
    """Serve um ZIP com HEAD e GET com `Range` (206), como o servidor da Anatel. Devolve o log de requisições."""
    import io
    import re
    import zipfile

    import httpx

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in members.items():
            z.writestr(name, content)
    blob = buf.getvalue()
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        rng = request.headers.get("Range")
        calls.append((request.method, rng or ""))
        headers = {"content-length": str(len(blob)), "last-modified": last_modified, "etag": etag}
        if request.method == "HEAD":
            return httpx.Response(200, headers=headers)
        if rng:
            m = re.match(r"bytes=(\d+)-(\d+)", rng)
            a, b = int(m.group(1)), min(int(m.group(2)), len(blob) - 1)
            return httpx.Response(206, content=blob[a:b + 1], headers=headers)
        return httpx.Response(200, content=blob, headers=headers)

    respx_mock.route(url=url).mock(side_effect=handler)
    return calls
