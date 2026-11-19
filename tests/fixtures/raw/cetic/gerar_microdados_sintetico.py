"""Gera `tic_domicilios_microdados_sintetico.csv.gz`: base SINTÉTICA no layout da base real da TIC Domicílios (Latin-1, `;`, vírgula decimal, 200 réplicas).

    python tests/fixtures/raw/cetic/gerar_microdados_sintetico.py
Semente fixa; nenhum domicílio real. AP (UF 16) fica com 12 domicílios para exercitar a supressão; as demais UFs têm 36.
"""
import csv
import gzip
import io
import random
from pathlib import Path

REGIAO = {"11": "4", "12": "4", "13": "4", "14": "4", "15": "4", "16": "4", "17": "4", "21": "2", "22": "2", "23": "2", "24": "2", "25": "2", "26": "2", "27": "2",
          "28": "2", "29": "2", "31": "1", "32": "1", "33": "1", "35": "1", "41": "3", "42": "3", "43": "3", "50": "5", "51": "5", "52": "5", "53": "5"}
rng = random.Random(20260102)
cab = ["QUEST", "ID_DOMICILIO", "COD_UF", "AREA", "COD_REGIAO_2", "A1_AGREG", "A4", "A7_AGREG", "PESO"] + [f"REP{i}" for i in range(1, 201)]
saida = io.StringIO()
w = csv.writer(saida, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\n")
w.writerow(cab)
q = 100000
for uf, reg in REGIAO.items():
    for k in range(12 if uf == "16" else 36):
        q += 1
        internet = rng.random() < 0.85
        peso = round(rng.uniform(300, 1800), 2)
        reps = [round(peso * rng.choice((0, 0.5, 1, 1, 1.5, 2)), 2) for _ in range(200)]
        w.writerow([q, k + 1, uf, rng.choice("12"), reg, int(rng.random() < 0.3), 1 if internet else 0, 1 if internet and rng.random() < 0.75 else 99, str(peso).replace(".", ",")]
                   + [str(x).replace(".", ",") for x in reps])
with open(Path(__file__).with_name("tic_domicilios_microdados_sintetico.csv.gz"), "wb") as bruto, gzip.GzipFile(fileobj=bruto, mode="wb", mtime=0) as f:
    f.write(saida.getvalue().encode("latin-1"))
