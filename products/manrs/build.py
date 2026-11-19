# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""MANRS agregado: quanto da Internet brasileira está em organizações participantes do programa de operadores do MANRS.

Entrada:  data/normalized/{date}/summary/manrs_participantes.json.gz (fonte `manrs_participantes`, nunca publicada) e published/{date}/prontidao/asns.json.gz (ASNs do Brasil com UF, porte e índice).
Saída:    published/{date}/manrs/resumo.json.gz — só agregados, com a atribuição exigida pelos termos.

Termos do MANRS (manrs.org/terms-of-service/, cláusula 2): dados de outras redes só podem ser divulgados de forma agregada e sem identificá-las; uso não comercial; atribuição obrigatória;
não sugerir endosso. Por isso: (a) nenhum registro por ASN ou organização sai daqui; (b) recorte com menos de `MINIMO_ASNS` ASNs participantes é suprimido (uma UF com 1 ou 2 participantes
os identificaria por exclusão); (c) a comparação de prontidão entre participantes e não participantes existe só no total e por porte, nunca por UF; (d) a prontidão por ASN
 não ganha marca de participação.

Uso:
    python -m products.manrs.build --date 2026-11-03
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from core.common import configure_logging, data_dir, normalized_path, now_iso, published_path, today_str
from core.jsonio import carregar_json_gz, gravar_json_gz
from products.prontidao.build import agregar

MINIMO_ASNS = 5
ATRIBUICAO = "Provided by the MANRS with support from the Global Cyber Alliance"
FONTE = "Tabela pública de participantes do programa de operadores de rede do MANRS (manrs.org/netops/participants/)"
LIMITES = (
    "Participar do MANRS é um compromisso declarado pela organização; a lista não prova que cada ASN da organização cumpre as ações. O cálculo considera os ASNs do Registro.br listados pelas organizações participantes; "
    "organização com ASNs fora do Brasil entra só pelos ASNs brasileiros. Recortes com menos de %d ASNs participantes são suprimidos para não identificar redes (os termos do MANRS só permitem divulgação agregada). "
    "A comparação de prontidão entre participantes e não participantes descreve associação, não causa. Não há lista de organizações nem de ASNs. %s. O MANRS e a GCA não endossam este uso." % (MINIMO_ASNS, ATRIBUICAO)
)


def _pct(parte: float, total: float) -> Optional[float]:
    return round(100 * parte / total, 1) if total else None


def _comparacao(asns: dict[str, dict], grupo: dict[str, str]) -> Optional[dict]:
    """Prontidão de participantes e não participantes; só se os dois grupos têm ao menos `MINIMO_ASNS` ASNs com índice."""
    ag = agregar(asns, grupo)
    p, n = ag.get("participantes"), ag.get("nao_participantes")
    if not p or not n or p["asns_com_indice"] < MINIMO_ASNS or n["asns_com_indice"] < MINIMO_ASNS:
        return None
    pega = lambda a: {k: a[k] for k in ("asns_com_indice", "media_ponderada_usuarios", "mediana", "classes")}
    return {"participantes": pega(p), "nao_participantes": pega(n)}


def _celula(asns: dict[str, dict], membros: set[str], participantes: set[str], com_comparacao: bool, suprimir: Optional[str] = None) -> dict:
    total_us = sum(asns[a]["usuarios"] for a in membros)
    part = membros & participantes
    out = {"asns": len(membros), "usuarios": total_us}
    if suprimir:
        return {**out, "suprimido": True, "motivo": suprimir}
    out.update(asns_participantes=len(part), pct_asns=_pct(len(part), len(membros)), usuarios_participantes=sum(asns[a]["usuarios"] for a in part))
    out["pct_usuarios"] = _pct(out["usuarios_participantes"], total_us)
    if com_comparacao:
        out["comparacao_prontidao"] = _comparacao({a: asns[a] for a in membros}, {a: ("participantes" if a in part else "nao_participantes") for a in membros})
    return out


def _particao(asns: dict[str, dict], grupos: dict[str, set[str]], participantes: set[str], com_comparacao: bool) -> dict[str, dict]:
    """Células de uma partição (UF ou porte). Além do recorte com menos de `MINIMO_ASNS` participantes, suprime o menor dos demais enquanto os suprimidos somarem menos que o mínimo:
    como o total do país é público, um único recorte suprimido sairia por diferença (total menos os outros)."""
    contagem = {g: len(m & participantes) for g, m in grupos.items()}
    ocultos = {g for g, n in contagem.items() if n < MINIMO_ASNS}
    motivo = {g: f"menos de {MINIMO_ASNS} ASNs participantes" for g in ocultos}
    while ocultos and sum(contagem[g] for g in ocultos) < MINIMO_ASNS and len(ocultos) < len(grupos):
        g = min((g for g in grupos if g not in ocultos), key=lambda g: (contagem[g], g))
        ocultos.add(g)
        motivo[g] = "suprimido também para que o recorte pequeno não saia por diferença do total"
    return {g: _celula(asns, grupos[g], participantes, com_comparacao, motivo.get(g)) for g in sorted(grupos)}


def calcular(prontidao: dict, doc_manrs: dict) -> dict:
    asns = prontidao["asns"]
    em_br = {int(a) for a in asns}
    orgs = [p for p in doc_manrs["participantes"] if em_br & set(p["asns"])]
    participantes = {str(a) for p in orgs for a in p["asns"] if a in em_br}
    todos = set(asns)
    por_uf: dict[str, set[str]] = {}
    por_porte: dict[str, set[str]] = {}
    for a, d in asns.items():
        if d.get("uf"):
            por_uf.setdefault(d["uf"], set()).add(a)
        if d.get("faixa_porte"):
            por_porte.setdefault(d["faixa_porte"], set()).add(a)
    brasil = _celula(asns, todos, participantes, True, f"menos de {MINIMO_ASNS} ASNs participantes" if len(todos & participantes) < MINIMO_ASNS else None)
    return {
        "brasil": {**brasil, "organizacoes_com_asn_br": len(orgs)} if not brasil.get("suprimido") else brasil,
        "por_uf": _particao(asns, por_uf, participantes, False),
        "por_faixa_porte": _particao(asns, por_porte, participantes, True),
    }


def publicar_manrs(base: Path, date_str: str, log) -> dict:
    pub = published_path(base, date_str)
    prontidao = carregar_json_gz(pub / "prontidao" / "asns.json.gz")
    doc = carregar_json_gz(normalized_path(base, date_str, "summary") / "manrs_participantes.json.gz")
    if not prontidao or not doc:
        log.info("manrs: prontidão ou lista de participantes ausente; resumo não gerado", prontidao=bool(prontidao), participantes=bool(doc))
        return {}
    r = calcular(prontidao, doc)
    destino = pub / "manrs"
    destino.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "resumo.json.gz", {
        "snapshot_date": date_str, "generated_at": now_iso(), "natureza": "agregado", "atribuicao": ATRIBUICAO, "fonte": {"descricao": FONTE, "url": doc["url"], "medido_em": doc.get("medido_em"),
                                                                                                                   "coletado_em": doc["snapshot_date"], "termos": "https://manrs.org/terms-of-service/"},
        "regras": {"minimo_asns_por_recorte": MINIMO_ASNS, "comparacao": "total e por porte (nunca por UF)"}, "limites": LIMITES, **r})
    log.info("manrs written", asns_participantes=r["brasil"].get("asns_participantes"), organizacoes=r["brasil"]["organizacoes_com_asn_br"])
    return r


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="MANRS agregado")
    p.add_argument("--date", default=today_str())
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        publicar_manrs(data_dir(), a.date, log)
    except Exception:
        log.exception("falha em products.manrs")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
