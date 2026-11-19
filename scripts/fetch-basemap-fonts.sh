#!/usr/bin/env bash
# Baixa as fontes do basemap (glifos em PBF do "Noto Sans Regular") para data/tiles/_assets/fonts/.
# O style do mapa (frontend/src/components/maps/mapTheme.ts) pede /tiles/_assets/fonts/{fontstack}/{range}.pbf; sem esses arquivos
# os rótulos não aparecem e o navegador registra 404 a cada carga de mapa. Eles não estão no git (data/ é ignorado) e não são
# gerados por build-basemap-tiles.sh: este script os provisiona em qualquer máquina (idempotente).
# Origem: https://github.com/openmaptiles/fonts (release v2.0, noto-sans.zip). Noto Sans: SIL Open Font License 1.1.
# Uso: bash scripts/fetch-basemap-fonts.sh [DIRETORIO_DATA]   (padrão: ./data)
set -euo pipefail
DATA="${1:-data}"
DEST="$DATA/tiles/_assets/fonts"
FONTE="Noto Sans Regular"
URL="https://github.com/openmaptiles/fonts/releases/download/v2.0/noto-sans.zip"
if [[ -f "$DEST/$FONTE/0-255.pbf" && "$(ls "$DEST/$FONTE" | wc -l)" -ge 256 ]]; then
  echo "fontes já presentes em $DEST/$FONTE"
  exit 0
fi
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fsSL -A "arandurape/1.0" -o "$TMP/noto-sans.zip" "$URL"
python3 - "$TMP/noto-sans.zip" "$DEST" "$FONTE" <<'PY'
import sys, zipfile
from pathlib import Path
zf, dest, fonte = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
n = 0
with zipfile.ZipFile(zf) as z:
    for nome in z.namelist():
        partes = Path(nome).parts
        if len(partes) >= 2 and partes[-2] == fonte and nome.endswith(".pbf"):
            alvo = dest / fonte / partes[-1]
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_bytes(z.read(nome))
            n += 1
if n < 256:
    sys.exit(f"esperava 256 faixas de glifos, extraí {n}: a estrutura do zip mudou?")
print(f"{n} faixas de glifos em {dest / fonte}")
PY
