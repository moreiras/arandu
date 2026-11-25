# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Ligação marca → raiz do CNPJ (usada pela qualidade e pelo Consumidor.gov.br).

O RQUAL e as reclamações da Anatel só trazem o NOME da empresa. Duas regras, nesta ordem, e o resultado sempre diz qual valeu:

  1. **curada**: `config/curada_marcas_operadoras.yaml`, feita à mão com a razão social das outorgas e os grupos do SICI;
  2. **automática**: o nome da marca, sem acento e pontuação, é IGUAL ao nome fantasia de outorgas de UMA só raiz de CNPJ (se duas raízes usam o mesmo nome fantasia, não casa). Nome igual não
     prova identidade (a "Starlink" das reclamações não é a Star Link, provedor de Santo André): o chamador só aceita o casamento automático se as reclamações da marca se concentrarem nas UFs
     onde a raiz tem outorga (`products/qualidade/build.py`).

Marca genérica ("Outros", "Não localizei a minha empresa") e nome com menos de 4 caracteres nunca casam sozinhos. Sem casamento, a marca fica sem CNPJ: não se adivinha.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Iterable

import yaml

CAMINHO_CURADA = Path(__file__).resolve().parent.parent / "config" / "curada_marcas_operadoras.yaml"
GENERICAS = {"OUTROS", "OUTRAS", "NAOLOCALIZEIMINHAEMPRESA", "NI", "NAOINFORMADO", ""}


def normalizar(s: str | None) -> str:
    """Maiúsculas, sem acento e só letras, dígitos e `+` (para `GIGA+`)."""
    t = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9+]", "", t)


def carregar_curada(caminho: Path | None = None) -> dict:
    """`{"versao", "curada_em", "fonte_da_curadoria", "marcas": {normalizada: {"marca", "raizes", "base", "data"}}, "aliases_consumidor_gov", "asns_estrangeiros"}`.

    `asns_estrangeiros` liga a raiz de uma operadora brasileira a ASNs de fora do Brasil da mesma marca (Starlink → AS14593): o vínculo
    `estrangeiro` do índice ASN ↔ CNPJ (`api/services/operadoras.py`). Fica fora de `marcas` porque não liga nome de marca a raiz (não
    mexe no RQUAL nem no Consumidor.gov.br). Falha alto em raiz mal formada e em entrada sem base ou data."""
    doc = yaml.safe_load((caminho or CAMINHO_CURADA).read_text(encoding="utf-8"))
    marcas = {}
    for m in doc["marcas"]:
        raizes = [str(r) for r in m["raizes"]]
        if not raizes or any(not re.fullmatch(r"\d{8}", r) for r in raizes):
            raise ValueError(f"curada_marcas_operadoras: raiz inválida em {m['marca']}: {raizes}")
        marcas[normalizar(m["marca"])] = {"marca": m["marca"], "raizes": raizes, "base": m["base"], "data": str(m.get("data") or doc["curada_em"])}
    aliases = {}
    for a in doc.get("aliases_consumidor_gov") or []:
        alvo = normalizar(a["marca"])
        if alvo not in marcas:
            raise ValueError(f"curada_marcas_operadoras: o alias {a['nome']!r} aponta para a marca {a['marca']!r}, que não está na tabela")
        aliases[normalizar(a["nome"])] = {"nome": a["nome"], "alvo": alvo, "base": a["base"]}
    estrangeiros = []
    for e in doc.get("asns_estrangeiros") or []:
        raizes = [str(r) for r in e["raizes"]]
        asns = [int(a) for a in e["asns"]]
        if not raizes or any(not re.fullmatch(r"\d{8}", r) for r in raizes) or not asns or not e.get("base") or not e.get("data"):
            raise ValueError(f"curada_marcas_operadoras: entrada de AS estrangeiro incompleta em {e.get('marca')}: raízes, ASNs, base e data são obrigatórios")
        estrangeiros.append({"marca": e["marca"], "raizes": raizes, "asns": asns, "base": e["base"], "data": str(e["data"])})
    return {"versao": doc["versao"], "curada_em": str(doc["curada_em"]), "fonte_da_curadoria": doc["fonte_da_curadoria"], "marcas": marcas, "aliases_consumidor_gov": aliases,
            "asns_estrangeiros": estrangeiros}


def indice_fantasia(outorgas: Iterable[dict]) -> dict[str, set[str]]:
    """Nome fantasia normalizado → raízes de CNPJ que o usam, a partir das linhas das outorgas (`cnpj`, `nome_fantasia`)."""
    idx: dict[str, set[str]] = {}
    for o in outorgas:
        n = normalizar(o.get("nome_fantasia"))
        if len(n) >= 4 and n != "NI":
            idx.setdefault(n, set()).add((o.get("cnpj") or "")[:8])
    return idx


def casar(marca: str, curada: dict, fantasia: dict[str, set[str]], automatico: bool = True) -> dict | None:
    """`{"raizes": [...], "metodo": "curada"|"automatico", "base": str}` ou `None`. `automatico=False` só aceita a tabela curada; quem usa a regra automática deve validá-la (ver `products/qualidade`)."""
    n = normalizar(marca)
    if n in GENERICAS:
        return None
    c = curada["marcas"].get(n)
    if c:
        return {"raizes": c["raizes"], "metodo": "curada", "base": c["base"]}
    if automatico and len(n) >= 4 and len(fantasia.get(n, ())) == 1:
        raiz = next(iter(fantasia[n]))
        return {"raizes": [raiz], "metodo": "automatico", "base": "nome da marca igual ao nome fantasia de outorgas dessa raiz de CNPJ (e de nenhuma outra)"}
    return None


def casar_consumidor(nome_fantasia: str, curada: dict, fantasia: dict[str, set[str]]) -> dict | None:
    """Como `casar`, para o "Nome Fantasia" do Consumidor.gov.br: primeiro os apelidos da seção `aliases_consumidor_gov` da tabela curada ("Vivo - Telefônica" → VIVO), que herdam as
    raízes da marca de destino e dizem isso na base; sem apelido, a mesma regra de `casar`. O resultado é `curada` quando vem de apelido ou da tabela; `automatico` precisa da validação por UF do chamador."""
    a = (curada.get("aliases_consumidor_gov") or {}).get(normalizar(nome_fantasia))
    if a:
        alvo = curada["marcas"][a["alvo"]]
        return {"raizes": alvo["raizes"], "metodo": "curada", "base": f"apelido do Consumidor.gov.br para {alvo['marca']}: {a['base']}"}
    return casar(nome_fantasia, curada, fantasia)
