# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`socios_grupos` — Cruzamento de quadro societário: sócios em comum e cadeias de
propriedade entre as operadoras já cadastradas na base.

Entrada: normalized/{date}/summary/receita_socios.json.gz (`receita_socios`) +
         normalized/{date}/summary/anatel_{scm,smp,stfc,seac}.json.gz
Saída:   normalized/{date}/summary/grupos_societarios.json.gz

Duas fontes de relação entre CNPJs da base:
  1. Propriedade direta: o sócio de uma empresa é o próprio CNPJ básico de
     outra empresa da base. IMPORTANTE: o campo "CNPJ/CPF do sócio" da
     Receita, para sócio Pessoa Jurídica, traz SEMPRE só os 8 dígitos do
     CNPJ básico do sócio (confirmado empiricamente em 100% dos casos
     observados) — nunca o CNPJ completo de 14 dígitos, apesar do layout
     oficial sugerir o contrário. O casamento é feito diretamente por CNPJ
     básico.
  2. Sócio em comum: duas empresas compartilham o mesmo sócio pessoa física
     (casado por nome normalizado + CPF, parcialmente mascarado pela
     Receita: 3 primeiros dígitos e 2 dígitos verificadores ocultos) ou a
     mesma holding PJ. CAVEAT: nomes comuns podem colidir nos dígitos
     visíveis do CPF e gerar falso positivo.

Cada relação direta é classificada em TOTAL ou PARCIAL, nunca inferida por
transitividade dentro do grupo (A e C no mesmo grupo só porque ambos se
ligam a B não implica relação A↔C):
  - TOTAL ("mesmo_grupo"): o quadro de sócios das duas empresas é IDÊNTICO
    (mesmo conjunto, não só interseção não vazia), ou uma delas tem a outra
    como ÚNICA sócia (controle exclusivo, sem nenhum outro sócio junto).
  - PARCIAL ("relacionadas_parcial"): há sócio(s) em comum mas o quadro não
    é idêntico, ou a propriedade não é exclusiva (a controladora é uma entre
    vários sócios da controlada). Vem com a contagem de sócios em comum e
    os nomes.

Sócios pessoa jurídica que são holdings EXTERNAS à base (não são elas mesmas
operadoras SCM/SMP/STFC/SeAC) têm seus dados cadastrais resolvidos via
BrasilAPI, pela matriz (CNPJ básico + "0001" + dígitos verificadores
calculados pelo algoritmo padrão módulo 11 — a Receita não informa os
dígitos verificadores do sócio, então precisam ser recalculados; a matriz
pode não existir/ter sido baixada, caso em que os dados ficam vazios).
Poucas chamadas pontuais, nunca o dump inteiro, com cache próprio
persistente em normalized/holdings_cache/nomes.json.gz.

Só sócio COM participação societária gera relação (decisão D5): administrador, conselheiro,
diretor, presidente e demais cargos sem participação (`qualificacoes.py`) não ligam empresas.
Cada relação guarda a classe e os códigos de qualificação que a sustentam, sem nomes.

Sociedade anônima (natureza jurídica da Receita, `core/sociedade_anonima.py`, decisão P8): o quadro de S.A. traz gestão, não acionistas; ele não gera aresta. A relação que
nasce do quadro de outra empresa em que a S.A. é sócia PJ com participação continua. A S.A. sai marcada com `grupo_inferivel: false` (sem nomes).

Componentes conectados (sócio em comum OU propriedade direta, total ou
parcial) definem os "grupos societários" (`grupo_id`) — um agrupamento mais
amplo e transitivo, útil para navegação, mas que não deve ser confundido com
as relações diretas TOTAL/PARCIAL entre um par específico de empresas.
O `grupo_id` é `grp_` + o menor CNPJ básico do componente: o mesmo conjunto tem o mesmo id
em snapshots diferentes; `equivalencia_grupo_id` leva o id de cada membro ao id do grupo.

Uso:
    python -m sources.socios_grupos.enrich --date 2026-09-27
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import unicodedata
from pathlib import Path

import httpx

from core.common import (
    configure_logging,
    data_dir,
    normalized_path,
    now_iso,
    read_json_gz,
    today_str,
    write_json_gz,
)
from core.site import USER_AGENT
from core.cpf import sem_socios_pessoa_fisica
from core import sociedade_anonima as sa
from sources.socios_grupos.qualificacoes import classe_da_qualificacao, liga_empresas, regra_publicada

BRASILAPI_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
BRASILAPI_DELAY = 0.35  # segundos entre requisições — evita 429 em lotes de centenas de holdings

_BASE_SOURCES = ("anatel_scm.json.gz", "anatel_smp.json.gz",
                  "anatel_stfc.json.gz", "anatel_seac.json.gz")

_ENDERECO_FIELDS = ("logradouro", "numero", "complemento", "bairro",
                     "municipio", "uf", "cep", "codigo_ibge")


def _normalize_name(name: str) -> str:
    """Maiúsculas, sem acento, espaços colapsados — chave de casamento de nome."""
    nfkd = unicodedata.normalize("NFKD", name or "")
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_only.upper()).strip()


def _cnpj_check_digits(base12: str) -> str:
    """Calcula os 2 dígitos verificadores de um CNPJ a partir dos 12 primeiros
    dígitos (8 do básico + 4 da ordem), pelo algoritmo padrão módulo 11."""
    def _digit(digits: str, weights: list[int]) -> str:
        total = sum(int(d) * w for d, w in zip(digits, weights))
        r = total % 11
        return "0" if r < 2 else str(11 - r)

    d1 = _digit(base12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = _digit(base12 + d1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return d1 + d2


def _matriz_cnpj(cnpj_basico: str) -> str:
    """CNPJ da matriz (ordem 0001) a partir do CNPJ básico, com DV calculado."""
    base12 = cnpj_basico + "0001"
    return base12 + _cnpj_check_digits(base12)


def _load_base_cnpjs(
    base: Path, date_str: str, log
) -> tuple[set[str], dict[str, set[str]], dict[str, dict]]:
    """Retorna (todos os CNPJs da base, mapa cnpj_basico -> {CNPJs completos},
    mapa CNPJ -> endereço da outorga Anatel — a mesma fonte que alimenta as
    collections `scms`/`smps`/`stfcs`/`seacs`)."""
    all_cnpjs: set[str] = set()
    endereco_by_cnpj: dict[str, dict] = {}
    for name in _BASE_SOURCES:
        path = normalized_path(base, date_str, "summary", name)
        if not path.exists():
            continue
        data = read_json_gz(path)
        by_cnpj = (data or {}).get("by_cnpj", {})
        all_cnpjs.update(by_cnpj.keys())
        for cnpj, recs in by_cnpj.items():
            if cnpj in endereco_by_cnpj or not recs:
                continue
            rec = recs[0]
            end = {f: rec.get(f, "") for f in _ENDERECO_FIELDS}
            if end.get("logradouro") or end.get("municipio"):
                endereco_by_cnpj[cnpj] = end

    basico_to_full: dict[str, set[str]] = {}
    for cnpj in all_cnpjs:
        if len(cnpj) == 14:
            basico_to_full.setdefault(cnpj[:8], set()).add(cnpj)
    return all_cnpjs, basico_to_full, endereco_by_cnpj


class _UnionFind:
    def __init__(self, items: list[str]):
        self.parent = {i: i for i in items}

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def _fetch_cartao_cnpj(cnpj: str, client: httpx.Client) -> dict:
    """Busca o cadastro completo na BrasilAPI, com um retry após 429.

    A quantidade de holdings externas resolvidas por execução pode passar de
    mil — sem pausa entre chamadas, a BrasilAPI passa a responder 429 em
    sequência (observado empiricamente); o delay entre chamadas é aplicado
    pelo chamador.
    """
    empty = {
        "razao_social": "", "nome_fantasia": "", "situacao_cadastral": "",
        "natureza_juridica": "", "porte": "", "capital_social": None,
        "data_inicio_atividade": "", "cnae_fiscal_descricao": "",
        "logradouro": "", "numero": "", "complemento": "", "bairro": "",
        "municipio": "", "uf": "", "cep": "",
    }
    for attempt in range(2):
        try:
            r = client.get(BRASILAPI_URL.format(cnpj=cnpj), timeout=15)
            if r.status_code == 429:
                time.sleep(BRASILAPI_DELAY * 5)
                continue
            if r.status_code != 200:
                return empty
            d = r.json()
            return {
                "razao_social": d.get("razao_social") or "",
                "nome_fantasia": d.get("nome_fantasia") or "",
                "situacao_cadastral": d.get("descricao_situacao_cadastral") or "",
                "natureza_juridica": d.get("natureza_juridica") or "",
                "porte": d.get("porte") or "",
                "capital_social": d.get("capital_social"),
                "data_inicio_atividade": d.get("data_inicio_atividade") or "",
                "cnae_fiscal_descricao": d.get("cnae_fiscal_descricao") or "",
                "logradouro": d.get("logradouro") or "",
                "numero": d.get("numero") or "",
                "complemento": d.get("complemento") or "",
                "bairro": d.get("bairro") or "",
                "municipio": d.get("municipio") or "",
                "uf": d.get("uf") or "",
                "cep": d.get("cep") or "",
            }
        except Exception:
            return empty
    return empty


def _holdings_cache_path(base: Path) -> Path:
    return base / "normalized" / "holdings_cache" / "cartoes.json.gz"


def _socio_chave(s: dict) -> str | None:
    ident = s.get("identificador_socio", "")
    doc = (s.get("cnpj_cpf_socio") or "").strip()
    nome = s.get("nome_socio", "")
    if ident == "1" and len(doc) in (8, 14):
        return f"cnpj:{doc[:8]}"
    if ident == "2" and nome.strip() and doc:
        return f"pf:{_normalize_name(nome)}|{doc}"
    return None


def _socio_qualificacoes(socios_raw: list[dict], so_participacao: bool = False) -> dict[str, set[str]]:
    """Chave de identidade -> códigos de qualificação com que o sócio consta no quadro. Com `so_participacao`, só os registros de quem tem
    participação societária (a regra que liga empresas); sem ele, todos (para contar o que a regra deixou de ligar)."""
    out: dict[str, set[str]] = {}
    for s in socios_raw:
        key = _socio_chave(s)
        if key is None:
            continue
        q = str(s.get("qualificacao_socio") or "").strip()
        if so_participacao and not liga_empresas(q):
            continue
        out.setdefault(key, set()).add(q)
    return out


def _socio_identity_keys(socios_raw: list[dict]) -> set[str]:
    """Chaves de identidade dos sócios COM participação societária de uma empresa: 'pf:nome|cpf' para pessoa física, 'cnpj:basico' para
    pessoa jurídica. Administrador, diretor e presidente sem participação (qualificações da classe `administracao` e `representacao`) ficam
    de fora, assim como sócio estrangeiro (sem CPF/CNPJ não há chave confiável): nunca contam para igualdade/interseção de quadro societário."""
    return set(_socio_qualificacoes(socios_raw, so_participacao=True))


def _classes(codigos: set[str]) -> list[str]:
    return sorted({classe_da_qualificacao(c) for c in codigos})


def _sa_basicos(base: Path, date_str: str, alvo: set[str], log) -> tuple[set[str], bool]:
    """(raízes do universo que são S.A. pela natureza jurídica da Receita, e se a natureza estava disponível)."""
    path = normalized_path(base, date_str, "summary", "receita_cnpj.json.gz")
    if not path.exists():
        log.warning("receita_cnpj ausente: sem natureza jurídica, S.A. não é identificada no agrupamento", data=date_str)
        return set(), False
    empresas = (read_json_gz(path) or {}).get("empresa") or {}
    return {b for b in alvo if sa.e_sociedade_anonima((empresas.get(b) or {}).get("nat"))}, True


def run(date_str: str, base: Path, log) -> dict:
    socios_path = normalized_path(base, date_str, "summary", "receita_socios.json.gz")
    if not socios_path.exists():
        raise FileNotFoundError(
            f"receita_socios.json.gz não encontrado: {socios_path}. Rode a coleta receita_socios primeiro."
        )
    socios_data = read_json_gz(socios_path)
    by_cnpj_basico: dict[str, list[dict]] = (socios_data or {}).get("by_cnpj_basico", {})

    _, basico_to_full, endereco_by_cnpj = _load_base_cnpjs(base, date_str, log)
    target_basicos = set(basico_to_full.keys())
    sa_basicos, natureza_disponivel = _sa_basicos(base, date_str, target_basicos, log)

    # Nome legível de cada chave de identidade, para exibir "sócios em comum".
    identity_name: dict[str, str] = {}
    socio_sets: dict[str, set[str]] = {}
    # cnpj_basico -> {chave -> códigos de qualificação} só de quem tem participação (a regra que liga)
    socio_quals: dict[str, dict[str, set[str]]] = {}
    uf = _UnionFind(sorted(target_basicos))   # ordem fixa; o `grupo_id` vem do menor CNPJ básico do componente, não da raiz da union-find
    uf_antes = _UnionFind(sorted(target_basicos))   # a regra anterior (todo registro do quadro liga), só para medir o efeito da decisão
    # socio_key -> {cnpj_basico que têm esse sócio com participação}
    socio_index: dict[str, set[str]] = {}
    socio_index_antes: dict[str, set[str]] = {}
    # cnpj_basico -> {outro_cnpj_basico -> {"tipo", "confianca"}} — só arestas com
    # EVIDÊNCIA DIRETA (nunca inferidas por transitividade dentro do grupo).
    edges: dict[str, dict[str, dict]] = {}
    # cnpj_basico de holdings PJ externas à base -> conjunto de cnpj_basico relacionados
    external_holdings: dict[str, set[str]] = {}

    def _add_edge(a: str, b: str, tipo: str, confianca: str, **extra) -> None:
        edges.setdefault(a, {})[b] = {"tipo": tipo, "confianca": confianca, **extra}

    for cnpj_basico, socios in by_cnpj_basico.items():
        if cnpj_basico not in target_basicos:
            continue
        socio_quals[cnpj_basico] = _socio_qualificacoes(socios, so_participacao=True)
        if cnpj_basico in sa_basicos:
            socio_quals[cnpj_basico] = {}
        socio_sets[cnpj_basico] = set(socio_quals[cnpj_basico])
        for s in socios:
            key = _socio_chave(s)
            if key is None:
                continue          # ident == "3" (estrangeiro sem CPF/CNPJ): sem chave confiável de casamento
            identity_name[key] = s.get("nome_socio", "")
            socio_index_antes.setdefault(key, set()).add(cnpj_basico)
            if cnpj_basico in sa_basicos or not liga_empresas(s.get("qualificacao_socio")):
                continue          # o quadro de S.A. não liga (P8): traz gestão, não acionistas
            socio_index.setdefault(key, set()).add(cnpj_basico)
            if key.startswith("cnpj:") and key[5:] not in target_basicos:
                # A Receita traz só o CNPJ básico (8 dígitos) do sócio PJ, mas trata com tolerância o CNPJ completo (14).
                external_holdings.setdefault(key[5:], set()).add(cnpj_basico)

    def _liga_antes(index: dict[str, set[str]], um: _UnionFind) -> None:
        for membros in index.values():
            m = sorted(membros)
            for x in m[1:]:
                um.union(m[0], x)

    _liga_antes(socio_index_antes, uf_antes)
    pares_antes: set[tuple[str, str]] = set()
    for membros in socio_index_antes.values():
        m = sorted(membros)
        pares_antes.update((m[i], m[j]) for i in range(len(m)) for j in range(i + 1, len(m)))

    # --- Propriedade direta: cnpj_basico controlado por socio_basico (ambos na base) ---
    for cnpj_basico, socios in by_cnpj_basico.items():
        if cnpj_basico not in target_basicos:
            continue
        for s in socios:
            if s.get("identificador_socio") != "1":
                continue
            doc = (s.get("cnpj_cpf_socio") or "").strip()
            if len(doc) not in (8, 14):
                continue
            socio_basico = doc[:8]
            if socio_basico not in target_basicos or socio_basico == cnpj_basico:
                continue
            uf_antes.union(cnpj_basico, socio_basico)
            pares_antes.add(tuple(sorted((cnpj_basico, socio_basico))))
            q = s.get("qualificacao_socio")
            if cnpj_basico in sa_basicos or not liga_empresas(q):
                continue
            uf.union(cnpj_basico, socio_basico)
            ev = {"classes_qualificacao": _classes({str(q or "").strip()}), "qualificacoes_em_comum": [str(q or "").strip()]}
            # Exclusivo: cnpj_basico não tem NENHUM outro sócio além de socio_basico.
            exclusivo = len(socios) == 1
            if exclusivo:
                _add_edge(cnpj_basico, socio_basico, "controle_exclusivo_recebido", "alta", **ev)
                _add_edge(socio_basico, cnpj_basico, "controle_exclusivo_exercido", "alta", **ev)
            else:
                _add_edge(cnpj_basico, socio_basico, "controle_parcial_recebido", "alta",
                          total_socios=len(socios), **ev)
                _add_edge(socio_basico, cnpj_basico, "controle_parcial_exercido", "alta",
                          total_socios=len(socios), **ev)

    # --- Sócio em comum: casa só pares que de fato compartilham aquele sócio COM participação nas duas empresas,
    # nunca todo o resto do componente conectado (isso seria transitividade sem
    # evidência: A e C podem estar no mesmo grupo só porque ambos se ligam a B,
    # sem nenhum sócio em comum direto entre A e C). Classifica em total
    # (quadro idêntico) ou parcial (com a contagem e os nomes em comum). ---
    pares_liga: set[tuple[str, str]] = set()
    for cnpj_set in socio_index.values():
        members = sorted(cnpj_set)
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                if b in edges.get(a, {}):
                    continue  # já tem aresta de propriedade direta entre esse par
                uf.union(a, b)
                comuns = socio_sets.get(a, set()) & socio_sets.get(b, set())
                quals = sorted({q for k in comuns for q in socio_quals[a].get(k, set()) | socio_quals[b].get(k, set())})
                ev = {"classes_qualificacao": _classes(set(quals)), "qualificacoes_em_comum": quals}
                if socio_sets.get(a) and socio_sets.get(a) == socio_sets.get(b):
                    _add_edge(a, b, "quadro_identico", "media", socios_em_comum=len(comuns), **ev)
                    _add_edge(b, a, "quadro_identico", "media", socios_em_comum=len(comuns), **ev)
                else:
                    nomes = sorted({identity_name.get(k, k) for k in comuns})
                    _add_edge(a, b, "socios_em_comum", "media",
                              socios_em_comum=len(comuns), nomes_em_comum=nomes, **ev)
                    _add_edge(b, a, "socios_em_comum", "media",
                              socios_em_comum=len(comuns), nomes_em_comum=nomes, **ev)
                pares_liga.add((a, b))
    pares_ligados = pares_liga | {tuple(sorted((a, b))) for a, viz in edges.items() for b in viz}
    comp_antes: dict[str, list[str]] = {}
    for c in sorted(target_basicos):
        comp_antes.setdefault(uf_antes.find(c), []).append(c)
    grandes_antes = [m for m in comp_antes.values() if len(m) >= 2]

    # Resolve cadastro completo das holdings externas pela matriz (poucas
    # chamadas, com cache). Chave do cache é o CNPJ básico (8 dígitos) — o
    # único dado que a Receita dá do sócio.
    cache_path = _holdings_cache_path(base)
    holdings_cache: dict[str, dict] = read_json_gz(cache_path) if cache_path.exists() else {}
    missing = [basico for basico in external_holdings if basico not in holdings_cache]
    if missing:
        with httpx.Client(headers={"User-Agent": USER_AGENT},
                           follow_redirects=True) as client:
            for i, basico in enumerate(missing, 1):
                holdings_cache[basico] = _fetch_cartao_cnpj(_matriz_cnpj(basico), client)
                time.sleep(BRASILAPI_DELAY)
                if i % 100 == 0:
                    log.info("holdings: progresso", feitos=i, total=len(missing))
                    write_json_gz(cache_path, holdings_cache)  # checkpoint incremental
        write_json_gz(cache_path, holdings_cache)
        log.info("holdings externas resolvidas", total=len(missing))

    _TOTAL_TIPOS = {"controle_exclusivo_recebido", "controle_exclusivo_exercido",
                     "quadro_identico"}

    # Monta grupos (componentes com mais de um membro) — agrupamento amplo e
    # transitivo, distinto das relações diretas total/parcial abaixo.
    components: dict[str, list[str]] = {}
    for cnpj_basico in sorted(target_basicos):
        root = uf.find(cnpj_basico)
        components.setdefault(root, []).append(cnpj_basico)

    grupos = []
    grupo_id_by_basico: dict[str, str] = {}
    for root, members in components.items():
        if len(members) < 2:
            continue
        grupo_id = f"grp_{min(members)}"      # estável: depende do conjunto, não da ordem de ligação (GRUPO-E14)
        for m in members:
            grupo_id_by_basico[m] = grupo_id

        # Classificação do CLUSTER inteiro (distinta da classificação de cada
        # aresta): "total" se toda relação DIRETA entre membros for TOTAL,
        # "parcial" se toda relação for PARCIAL, "misto" se houver as duas.
        # Membros conectados só transitivamente (sem aresta direta entre si)
        # não contam aqui — só o que de fato tem evidência direta.
        members_set = set(members)
        tem_total = tem_parcial = False
        for m in members:
            for outro, rel in edges.get(m, {}).items():
                if outro not in members_set:
                    continue
                if rel["tipo"] in _TOTAL_TIPOS:
                    tem_total = True
                else:
                    tem_parcial = True
        if tem_total and tem_parcial:
            classificacao = "misto"
        elif tem_total:
            classificacao = "total"
        else:
            classificacao = "parcial"

        grupos.append({
            "grupo_id": grupo_id,
            "cnpj_basicos": sorted(members),
            "cnpjs": sorted({c for m in members for c in basico_to_full.get(m, set())}),
            "tamanho": len(members),
            "classificacao": classificacao,
        })

    by_cnpj: dict[str, dict] = {}
    for cnpj_basico, full_cnpjs in basico_to_full.items():
        grupo_id = grupo_id_by_basico.get(cnpj_basico)
        socios_raw = by_cnpj_basico.get(cnpj_basico, [])
        socios_out = [{
            "tipo": {"1": "juridica", "2": "fisica", "3": "estrangeiro"}.get(
                s.get("identificador_socio", ""), "desconhecido"),
            "nome": s.get("nome_socio", ""),
            "documento": s.get("cnpj_cpf_socio", ""),
            "qualificacao": s.get("qualificacao_socio", ""),
        } for s in socios_raw]

        mesmo_grupo: list[dict] = []
        relacionadas_parcial: list[dict] = []
        group_basicos: list[str] = []
        if grupo_id:
            group_basicos = next(g["cnpj_basicos"] for g in grupos if g["grupo_id"] == grupo_id)
            for outro_basico, rel in edges.get(cnpj_basico, {}).items():
                for outro_cnpj in sorted(basico_to_full.get(outro_basico, set())):
                    ev = {k: rel[k] for k in ("classes_qualificacao", "qualificacoes_em_comum") if k in rel}
                    if rel["tipo"] in _TOTAL_TIPOS:
                        mesmo_grupo.append({"cnpj": outro_cnpj, "tipo_relacao": rel["tipo"], **ev})
                    else:
                        entry = {"cnpj": outro_cnpj, "tipo_relacao": rel["tipo"], **ev}
                        if "socios_em_comum" in rel:
                            entry["socios_em_comum"] = rel["socios_em_comum"]
                        if "nomes_em_comum" in rel:
                            entry["nomes_em_comum"] = rel["nomes_em_comum"]
                        if "total_socios" in rel:
                            entry["total_socios_da_controlada"] = rel["total_socios"]
                        relacionadas_parcial.append(entry)

        holdings_out = [
            {"cnpj_basico": basico, **holdings_cache.get(basico, {})}
            for basico, basicos in external_holdings.items()
            if cnpj_basico in basicos
        ]

        entry = {
            **({"grupo_inferivel": False, "motivo": sa.MOTIVO} if cnpj_basico in sa_basicos else {}),
            "grupo_id": grupo_id,
            "tamanho_grupo": len(group_basicos) if grupo_id else 1,
            "socios": socios_out,
            "mesmo_grupo": mesmo_grupo,
            "relacionadas_parcial": relacionadas_parcial,
            "holdings_externas": holdings_out,
            "endereco_sede": endereco_by_cnpj.get(next(iter(full_cnpjs), ""), None),
            "receita_dump_reference": (socios_data or {}).get("dump_reference", ""),
        }
        for cnpj in full_cnpjs:
            by_cnpj[cnpj] = {
                "cnpj": cnpj,
                **entry,
                "endereco_sede": endereco_by_cnpj.get(cnpj) or entry["endereco_sede"],
            }

    tamanho_por_grupo = {g["grupo_id"]: g["tamanho"] for g in grupos}

    def _intacto(m: list[str]) -> bool:
        """O grupo da regra anterior continua o mesmo conjunto (mesmos membros, nenhum a mais)."""
        gids = {grupo_id_by_basico.get(c) for c in m}
        return len(gids) == 1 and None not in gids and tamanho_por_grupo[next(iter(gids))] == len(m)

    output = {
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "receita_socios_generated_at": (socios_data or {}).get("generated_at", ""),
        "receita_dump_reference": (socios_data or {}).get("dump_reference", ""),
        "total_grupos": len(grupos),
        "total_cnpjs_em_grupo": sum(g["tamanho"] for g in grupos),
        "regra_qualificacao": regra_publicada(),
        "efeito_da_regra": {
            "pares_ligados_so_por_cargo_sem_participacao": len(pares_antes - pares_ligados),
            "grupos_pela_regra_anterior": len(grandes_antes),
            "cnpjs_basicos_em_grupo_pela_regra_anterior": sum(len(m) for m in grandes_antes),
            "grupos": len(grupos),
            "cnpjs_basicos_em_grupo": sum(g["tamanho"] for g in grupos),
            "grupos_desfeitos_ou_reduzidos": sum(1 for m in grandes_antes if not _intacto(m)),
            "sociedades_anonimas_sem_inferencia": len(sa_basicos),
            "natureza_juridica_disponivel": natureza_disponivel,
        },
        "regra_sociedade_anonima": sa.regra_publicada(),
        "equivalencia_grupo_id": {f"grp_{m}": g["grupo_id"] for g in grupos for m in g["cnpj_basicos"] if f"grp_{m}" != g["grupo_id"]},
        "grupos": grupos,
        "by_cnpj": by_cnpj,
    }

    dst = normalized_path(base, date_str, "summary", "grupos_societarios.json.gz")
    write_json_gz(dst, sem_socios_pessoa_fisica(output))      # nome de sócio pessoa física não é gravado (só tipo e qualificação)
    log.info("grupos_societarios saved", path=str(dst),
             total_grupos=len(grupos), total_cnpjs=len(by_cnpj))
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="`socios_grupos` — cruzamento de quadro societário entre operadoras")
    parser.add_argument("--date", default=today_str())
    args = parser.parse_args(argv)

    log = configure_logging()
    base = data_dir()

    try:
        run(date_str=args.date, base=base, log=log)
    except FileNotFoundError as e:
        log.error("input not found", error=str(e))
        return 1
    except Exception:
        log.exception("unexpected error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
