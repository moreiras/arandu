# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Monta a prévia social do repositório (1280×640, a proporção que o GitHub pede em Settings → Social preview) com o símbolo à
esquerda e o nome à direita, a partir dos dois SVGs desta pasta, e a rasteriza com o rsvg-convert.

    python3 marca/gerar_previa_social.py      # grava marca/arandurape-previa-social.png (e o .svg intermediário)
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
LARGURA, ALTURA = 1280, 640


def _miolo(svg: str) -> str:
    """O conteúdo depois do <defs> e antes do </svg>."""
    return svg.split("</defs>", 1)[1].rsplit("</svg>", 1)[0]


def montar() -> str:
    simbolo = _miolo((AQUI / "arandurape-simbolo.svg").read_text(encoding="utf-8"))
    logo = _miolo((AQUI / "arandurape-logo.svg").read_text(encoding="utf-8"))
    # No logo, o nome (texto em contorno) vem depois do anel do globo.
    anel = re.search(r'<circle cx="400" cy="400" r="340" fill="none"[^>]*/>', logo)
    if not anel:
        sys.exit("anel do globo não encontrado em arandurape-logo.svg")
    nome = logo[anel.end():]
    # Símbolo: o globo (60..740 no viewBox 800) com 560 px de diâmetro, centrado na altura.
    e = 560 / 680
    sx, sy = 60 - 60 * e, (ALTURA - 560) / 2 - 60 * e
    # Nome: ocupa x 62..733 e y 765..882 no viewBox do logo (linha de base em 860).
    en = 560 / 671
    nx, ny = 660 - 62 * en, ALTURA / 2 - (765 + 860) / 2 * en
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {LARGURA} {ALTURA}" width="{LARGURA}" height="{ALTURA}">\n'
            '<defs><clipPath id="globe"><circle cx="400" cy="400" r="340"/></clipPath></defs>\n'
            f'<rect width="{LARGURA}" height="{ALTURA}" fill="#FFFFFF"/>\n'
            f'<g transform="translate({sx:.2f},{sy:.2f}) scale({e:.5f})">{simbolo}</g>\n'
            f'<g transform="translate({nx:.2f},{ny:.2f}) scale({en:.5f})">{nome}</g>\n'
            '</svg>\n')


def main() -> int:
    svg = AQUI / "arandurape-previa-social.svg"
    png = AQUI / "arandurape-previa-social.png"
    svg.write_text(montar(), encoding="utf-8")
    if not shutil.which("rsvg-convert"):
        sys.exit("rsvg-convert não encontrado (librsvg)")
    subprocess.run(["rsvg-convert", "-w", str(LARGURA), "-h", str(ALTURA), "-o", str(png), str(svg)], check=True)
    svg.unlink()
    print(f"{png} ({png.stat().st_size // 1024} KiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
