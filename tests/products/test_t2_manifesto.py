# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T2 — o manifesto cobre 100% dos arquivos publicados: os checksums saem no fim do pipeline, não no `snapshot_completo`."""
import json

from core.integridade import EXCLUIDOS, sha256_arquivo
from tests.synth.world import T1


def test_checksums_cobrem_todos_os_arquivos_publicados(pipeline):
    base, _ = pipeline
    pub = base / "published" / T1
    manifesto = json.loads((pub / "manifest.json").read_text(encoding="utf-8"))
    publicados = {str(p.relative_to(pub)) for p in pub.rglob("*") if p.is_file() and p.name not in EXCLUIDOS}
    assert set(manifesto["checksums"]) == publicados
    assert any(k.startswith("asns/") and k != "asns/index.json" for k in publicados)      # documentos de ASN (compose)


def test_checksum_confere_com_o_conteudo(pipeline):
    base, _ = pipeline
    pub = base / "published" / T1
    manifesto = json.loads((pub / "manifest.json").read_text(encoding="utf-8"))
    for rel in ("asns/index.json", "summary.json", "scm.json.gz"):
        if rel in manifesto["checksums"]:
            assert manifesto["checksums"][rel] == sha256_arquivo(pub / rel), rel
