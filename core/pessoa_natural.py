# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Privacidade de pessoa natural (decisão D1 do mantenedor, 2026-11-24): empresário individual (EI) e MEI.

O nome empresarial de EI e de MEI é o nome civil da pessoa. O critério é a **natureza jurídica da Receita** (`receita_cnpj`: natureza 213-5
"Empresário (Individual)"; o MEI é uma opção do empresário individual no Simples, `simples.mei`; e `codigo_natureza_juridica` do cadastro por ASN em
`geo_orgs`). Para esses titulares:

- **Nome**: o nome fantasia; sem nome fantasia, o rótulo "Empresário individual" com o ASN e o CNPJ mascarado (`**.***.678/0001-**`). Vale para a razão
  social, o nome fantasia e o nome do AS (Registro.br) onde quer que apareçam;
- **Posição**: o ponto exato da sede vira o centróide do município IBGE (o projeto não tem base de centróide de CEP e não a inventa: ver
  `POSICAO_REDUZIDA_A`); o endereço textual sai;
- **Sócios** (`socios`, `holdings_externas`): sem mudança (D1); o percurso não entra nessas chaves.

O módulo tem três partes: o critério e o rótulo (`e_empresario_individual`, `rotulo`); o `Indice` dos titulares de um snapshot, montado do
cadastro da Receita, do cadastro por ASN e das outorgas da Anatel (`indice_do_snapshot`); e o percurso `aplicar`, que troca nome e posição
em qualquer documento sem alterar o original (o `Store` guarda os documentos em memória). O mesmo percurso roda na **publicação**
(`core.cpf.mascarar_snapshot`), na **leitura** do que ainda é cru (cadastro por ASN, outorgas, snapshots anteriores a esta regra) e na **saída**
da API e do MCP.

O reconhecimento do titular num registro é por identificador, não por heurística de nome: a chave `cnpj` (ou `cnpj_root`, `raiz`...), a chave `asn`,
ou a chave do dicionário pai (mapa por CNPJ ou por ASN). O nome civil conhecido (de qualquer fonte do mesmo titular) também é trocado onde aparece
num campo de nome sem identificador ao lado (`asns/names.json`, listas de vizinhos).
"""
from __future__ import annotations

import gzip
import json
import re
import threading
from pathlib import Path
from typing import Any, Iterable, Optional

from core.cpf import e_campo_de_nome

#: versão da regra, gravada no manifesto de cada snapshot que a recebeu (`manifest.privacidade.pessoa_natural`); sem ela o leitor mascara na leitura
VERSAO = 1
ROTULO = "Empresário individual"
NATUREZA_EI = "2135"
#: a posição de EI/MEI vai ao centróide do município IBGE: não há base de centróide de CEP no projeto (pendência registrada no plano PT-11)
POSICAO_REDUZIDA_A = "municipio"

_SO_DIGITOS = re.compile(r"\D")
_TEXTO_EI = re.compile(r"empres[aá]rio\s*\(?\s*individual", re.I)
# chaves cujo valor é o nome do titular (razão social, fantasia, nome do AS). Mais estreito que `core.cpf.e_campo_de_nome`: dentro de um registro
# de EI só estas chaves recebem o nome público, para não trocar `municipio_nome` ou `ixp_nome`.
_CHAVE_NOME = re.compile(r"^(razao_social|razao|nome_fantasia|fantasia|nome_empresarial|nome_empresa|empresa|sici_empresa|operadora|prestadora|titular|"
                         r"name|nome|org|org_name|as_name|asn_name|marca|holder|owner|empresa_nome|nome_titular)$")
# `entidade` só é nome onde o produto o diz: nos registros de multas (`raiz`, `cnpjs` ou `cnpj_matriz`) e de ERBs (`marca`) ela traz a razão social da Anatel,
# mas nos eventos do histórico é um rótulo de tipo ("asn") ao lado de `asn`: por isso fica fora de `_CHAVE_NOME` e é reconhecida pela forma do registro.
_CHAVE_ENTIDADE = "entidade"
_MARCAS_DE_REGISTRO_DE_EMPRESA = frozenset({"marca", "cnpjs", "cnpj_matriz"})
_LISTA_DE_NOMES = re.compile(r"^(alt_names|nomes|marcas|nomes_alternativos)$")
_CHAVE_CNPJ = frozenset({"cnpj", "cnpj_14", "cnpj14", "cnpj_basico", "cnpj_raiz", "cnpj_root", "raiz", "raiz_cnpj", "cnpj_matriz"})
_CHAVE_ASN = frozenset({"asn", "as_number", "origin_asn", "asn_titular"})
_CHAVE_LAT = frozenset({"lat", "latitude"})
_CHAVE_LON = frozenset({"lon", "lng", "longitude"})
_CHAVE_IBGE = ("codigo_ibge", "codigo_municipio_ibge", "ibge", "cod_ibge", "municipio_ibge")
_CHAVE_ENDERECO = frozenset({"descricao_tipo_de_logradouro", "tipo_logradouro", "logradouro", "numero", "complemento", "bairro", "cep", "address",
                             "endereco"})
#: o que D1 manda deixar como está
_NAO_PERCORRER = frozenset({"socios", "holdings_externas"})
_CPF_NO_NOME = re.compile(r"(\s|^)(\*{3}[0-9]{6}\*{2}|[0-9]{3}\.?[0-9]{3}\.?[0-9]{3}-?[0-9]{2})(?![0-9])")
_SUFIXO_PAIS = re.compile(r"^(.*?)(,\s*[A-Z]{2})$")


def e_empresario_individual(codigo: Any = None, texto: Any = None, mei: bool = False) -> bool:
    """Natureza jurídica de pessoa natural: código 213-5 (com ou sem hífen), texto "Empresário (Individual)" ou opção pelo MEI."""
    if mei:
        return True
    cod = _SO_DIGITOS.sub("", str(codigo)) if codigo not in (None, "") else ""
    if cod == NATUREZA_EI:
        return True
    return isinstance(texto, str) and _TEXTO_EI.search(texto) is not None


def cnpj_mascarado(cnpj: str) -> str:
    """`12345678000190` → `**.***.678/0001-**` (só os três últimos dígitos da raiz e a ordem do estabelecimento)."""
    d = _SO_DIGITOS.sub("", cnpj or "")
    if len(d) == 14:
        return f"**.***.{d[5:8]}/{d[8:12]}-**"
    if len(d) == 8:
        return f"**.***.{d[5:8]}/****-**"
    return "**.***.***/****-**"


def rotulo(asn: Optional[int] = None, cnpj: Optional[str] = None) -> str:
    """"Empresário individual" com o ASN e o CNPJ mascarado, quando conhecidos."""
    partes = ([f"AS{asn}"] if asn else []) + ([f"CNPJ {cnpj_mascarado(cnpj)}"] if cnpj else [])
    return f"{ROTULO} ({', '.join(partes)})" if partes else ROTULO


def _normaliza(s: str) -> str:
    from core.geoip import normaliza

    return normaliza(s)


def chave_de_nome(nome: Any) -> Optional[str]:
    """Chave de comparação do nome civil: sem CPF (inteiro ou mascarado), sem o sufixo ", BR" do Registro.br, sem acento nem pontuação.
    None para texto curto demais ou sem letra."""
    if not isinstance(nome, str) or len(nome) < 5:
        return None
    base = _CPF_NO_NOME.sub(" ", nome)
    c = _normaliza(base)
    return c if len(c) >= 5 and any(ch.isalpha() for ch in c) else None


def _chaves_do_nome(nome: Any) -> tuple[list[str], str]:
    """(chaves a procurar, sufixo ", XX" a devolver). O nome do AS vem com o país depois da vírgula."""
    sufixo = ""
    base = nome
    m = _SUFIXO_PAIS.match(nome.strip()) if isinstance(nome, str) else None
    if m:
        base, sufixo = m.group(1), m.group(2)
    ks = [k for k in (chave_de_nome(nome), chave_de_nome(base)) if k]
    return list(dict.fromkeys(ks)), sufixo


class Indice:
    """Titulares de pessoa natural de um snapshot: raiz de CNPJ → nome fantasia (ou None), ASN → CNPJ, e as chaves dos nomes civis conhecidos."""

    def __init__(self) -> None:
        self.raizes: dict[str, Optional[str]] = {}      # raiz (8 dígitos) → nome fantasia público (ou None)
        self.asn_cnpj: dict[int, str] = {}              # ASN de titular EI/MEI → CNPJ (14 dígitos)
        self.nomes: dict[str, str] = {}                 # chave do nome civil → raiz
        self.civis: dict[str, set] = {}                 # raiz → chaves dos nomes civis (para validar o nome fantasia)
        self.cnpjs: dict[str, str] = {}                 # raiz → CNPJ de 14 dígitos conhecido (para o rótulo)

    def __bool__(self) -> bool:
        return bool(self.raizes or self.asn_cnpj)

    # ── construção ──
    def _fantasia(self, raiz: str, fantasia: Any) -> None:
        f = (fantasia or "").strip() if isinstance(fantasia, str) else ""
        if f and self.raizes.get(raiz) is None:
            self.raizes[raiz] = f

    def adicionar(self, raiz: str, asn: Optional[int] = None, cnpj: Optional[str] = None, fantasia: Any = None, nomes: Iterable[Any] = ()) -> None:
        self.raizes.setdefault(raiz, None)
        self._fantasia(raiz, fantasia)
        if cnpj and len(cnpj) == 14:
            self.cnpjs.setdefault(raiz, cnpj)
        if asn:
            self.asn_cnpj[int(asn)] = cnpj if cnpj and len(cnpj) == 14 else self.cnpjs.get(raiz) or raiz + "0001"
        for n in nomes:
            self.nome_civil(raiz, n)

    def nome_civil(self, raiz: str, nome: Any) -> None:
        ks, _ = _chaves_do_nome(nome)
        for k in ks:
            self.nomes.setdefault(k, raiz)
            self.civis.setdefault(raiz, set()).add(k)

    # ── consulta ──
    def e_titular(self, cnpj: Any = None, asn: Any = None) -> Optional[tuple[str, Optional[int], Optional[str]]]:
        """(raiz, asn, cnpj) do titular EI/MEI identificado por CNPJ ou ASN; None se não é."""
        raiz = None
        c14 = None
        if cnpj not in (None, ""):
            d = _SO_DIGITOS.sub("", str(cnpj))
            if len(d) >= 8 and d[:8] in self.raizes:
                raiz = d[:8]
                c14 = d if len(d) == 14 else None
        a = None
        if asn not in (None, "", True, False):
            try:
                a = int(asn)
            except (TypeError, ValueError):
                a = None
            if a in self.asn_cnpj:
                raiz = raiz or self.asn_cnpj[a][:8]
                c14 = c14 or self.asn_cnpj[a]
            else:
                a = None
        if raiz is None:
            return None
        if a is None:
            a = next((x for x, c in self.asn_cnpj.items() if c[:8] == raiz and (c14 is None or c == c14)), None)
        return raiz, a, c14 or next((c for c in self.asn_cnpj.values() if c[:8] == raiz), None)

    def nome_publico(self, raiz: str, asn: Optional[int] = None, cnpj: Optional[str] = None) -> str:
        """Nome fantasia do titular se houver (e não for o próprio nome civil); senão o rótulo com ASN e CNPJ mascarado."""
        f = self.raizes.get(raiz)
        if f:
            k = chave_de_nome(f)
            if k is None or k not in self.civis.get(raiz, ()):
                return f
        return rotulo(asn, cnpj or self.cnpjs.get(raiz) or raiz)

    def raiz_do_nome(self, nome: Any) -> Optional[tuple[str, str]]:
        """(raiz, sufixo) se `nome` é o nome civil de um titular conhecido; None se não é."""
        if not self.nomes:
            return None
        ks, sufixo = _chaves_do_nome(nome)
        for k in ks:
            if k in self.nomes:
                return self.nomes[k], sufixo
        return None


# ── montagem a partir do snapshot ────────────────────────────────────────────────────────────

_OUTORGAS = ("anatel_scm.json.gz", "anatel_smp.json.gz", "anatel_stfc.json.gz", "anatel_seac.json.gz")


def _ler(caminho: Path) -> Any:
    try:
        if caminho.name.endswith(".gz"):
            with gzip.open(caminho, "rt", encoding="utf-8") as f:
                return json.load(f)
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError, EOFError):
        return None


def indice_do_snapshot(base: Path, date_str: str) -> Indice:
    """Índice dos titulares EI/MEI de `normalized/{date}/summary/` (Receita, cadastro por ASN e outorgas). Fonte ausente não é erro: o índice sai
    com o que há (sem `receita_cnpj` e sem `geo_orgs`, vazio)."""
    resumo = Path(base) / "normalized" / date_str / "summary"
    idx = Indice()
    nomes_por_raiz: dict[str, list] = {}
    fantasia_por_raiz: dict[str, Any] = {}

    rf = _ler(resumo / "receita_cnpj.json.gz") or {}
    simples = rf.get("simples") or {}
    for raiz, emp in (rf.get("empresa") or {}).items():
        if e_empresario_individual(emp.get("nat"), None, bool((simples.get(raiz) or {}).get("mei"))):
            idx.adicionar(raiz)
            ests = (rf.get("estabelecimentos") or {}).get(raiz) or []
            for e in sorted(ests, key=lambda e: e.get("m", 2)):          # matriz primeiro
                if e.get("n"):
                    idx._fantasia(raiz, e["n"])
    for raiz, s in simples.items():
        if s.get("mei") and raiz not in idx.raizes:
            idx.adicionar(raiz)

    geo = (_ler(resumo / "geo_orgs.json.gz") or {}).get("orgs") or {}
    for chave, org in geo.items():
        cnpj = _SO_DIGITOS.sub("", str(org.get("cnpj") or ""))
        raiz = cnpj[:8] if len(cnpj) >= 8 else None
        if raiz and (raiz in idx.raizes
                     or e_empresario_individual(org.get("codigo_natureza_juridica"), org.get("natureza_juridica"))):
            try:
                asn = int(chave)
            except (TypeError, ValueError):
                asn = None
            idx.adicionar(raiz, asn, cnpj if len(cnpj) == 14 else None, org.get("nome_fantasia"))
            nomes_por_raiz.setdefault(raiz, []).extend([org.get("razao_social"), org.get("name")])
    for arq in _OUTORGAS:
        doc = _ler(resumo / arq) or {}
        for cnpj, recs in (doc.get("by_cnpj") or {}).items():
            raiz = cnpj[:8]
            if raiz in idx.raizes:
                for r in recs:
                    nomes_por_raiz.setdefault(raiz, []).append(r.get("razao_social"))
                    fantasia_por_raiz.setdefault(raiz, r.get("nome_fantasia"))
    nomes_asn = _ler(resumo / "asn_names.json.gz") or {}
    if isinstance(nomes_asn, dict) and idx.asn_cnpj:
        for a, c in idx.asn_cnpj.items():
            if str(a) in nomes_asn:
                nomes_por_raiz.setdefault(c[:8], []).append(nomes_asn[str(a)])
    for raiz, nomes in nomes_por_raiz.items():
        for n in nomes:
            idx.nome_civil(raiz, n)
    for raiz, f in fantasia_por_raiz.items():
        idx._fantasia(raiz, f)
    return idx


# ── posição ──────────────────────────────────────────────────────────────────────────────────

def _centroide(d: dict) -> Optional[tuple[float, float]]:
    """Centróide do município do registro (código IBGE, ou nome e UF); None se não resolve."""
    cen = _centroides()
    for k in _CHAVE_IBGE:
        v = d.get(k)
        if v not in (None, ""):
            achou = cen.get(str(v).strip()[:7])
            if achou:
                return achou
    nome = next((d[k] for k in ("municipio", "city", "cidade") if isinstance(d.get(k), str) and d.get(k)), None)
    if nome:
        from core.geoip import centroide_municipio

        achou = centroide_municipio(nome, d.get("uf") if isinstance(d.get("uf"), str) else None)
        if achou:
            return achou[0], achou[1]
    return None


_CENTROIDES: dict[str, tuple[float, float]] = {}
_CENTROIDES_LOCK = threading.Lock()


def _centroides() -> dict[str, tuple[float, float]]:
    """{código IBGE: (lat, lon)} de `config/municipios-centroides.json` (o arquivo guarda [lon, lat])."""
    if not _CENTROIDES:
        with _CENTROIDES_LOCK:
            if not _CENTROIDES:
                try:
                    bruto = json.loads((Path(__file__).resolve().parent.parent / "config" / "municipios-centroides.json").read_text(encoding="utf-8"))
                    _CENTROIDES.update({str(k): (v[1], v[0]) for k, v in bruto.items()})
                except (OSError, ValueError):
                    _CENTROIDES["_"] = (0.0, 0.0)
    return _CENTROIDES


def posicao_reduzida(d: dict) -> Optional[tuple[float, float]]:
    """Posição pública de um titular EI/MEI: o centróide do município do registro, ou None (o ponto some, nunca fica o exato)."""
    return _centroide(d)


# ── percurso ─────────────────────────────────────────────────────────────────────────────────

class _Contexto:
    __slots__ = ("idx", "pontos")

    def __init__(self, idx: Indice, pontos: bool) -> None:
        self.idx, self.pontos = idx, pontos


def _nome_de_titular(valor: Any, ti: tuple[str, Optional[int], Optional[str]], ctx: _Contexto) -> Any:
    if not isinstance(valor, str) or not valor.strip():
        return valor
    raiz, asn, cnpj = ti
    publico = ctx.idx.nome_publico(raiz, asn, cnpj)
    achou = ctx.idx.raiz_do_nome(valor)
    return publico + (achou[1] if achou and achou[0] == raiz else _sufixo(valor))


def _sufixo(valor: str) -> str:
    m = _SUFIXO_PAIS.match(valor.strip())
    return m.group(2) if m else ""


def _titular_do_dict(d: dict, chave_pai: Any, ctx: _Contexto) -> Optional[tuple[str, Optional[int], Optional[str]]]:
    cnpj = asn = None
    for k, v in d.items():
        if not isinstance(k, str):
            continue
        kl = k.lower()
        if kl in _CHAVE_CNPJ and isinstance(v, (str, int)) and cnpj is None:
            cnpj = v
        elif kl in _CHAVE_ASN and isinstance(v, (str, int)) and asn is None:
            asn = v
    if cnpj is None and asn is None and isinstance(chave_pai, str) and chave_pai.isdigit():
        if len(chave_pai) in (8, 14):
            cnpj = chave_pai
        else:
            asn = chave_pai
    if cnpj is None and asn is None:
        return None
    return ctx.idx.e_titular(cnpj, asn)


def _reduzir_ponto(d: dict, novo: dict) -> None:
    ponto = posicao_reduzida(d)
    for k in d:
        kl = k.lower() if isinstance(k, str) else ""
        if kl in _CHAVE_LAT:
            novo[k] = ponto[0] if ponto else None
        elif kl in _CHAVE_LON:
            novo[k] = ponto[1] if ponto else None
    if "geo_confidence" in d:
        novo["geo_confidence"] = "city_centroid" if ponto else "unknown"


_LETRA = re.compile(r"[A-Za-zÀ-ÿ]")


def _titular_da_chave(chave: str, ctx: _Contexto) -> Optional[tuple[str, Optional[int], Optional[str]]]:
    return ctx.idx.e_titular(chave, None) if len(chave) in (8, 14) else ctx.idx.e_titular(None, chave)


def _nome_sem_titular(v: str, ctx: _Contexto) -> Optional[str]:
    """Nome civil conhecido num campo de nome sem identificador ao lado (`asns/names.json`, lista de vizinhos): o nome público do titular."""
    achou = ctx.idx.raiz_do_nome(v)
    if not achou:
        return None
    raiz, sufixo = achou
    asn = next((a for a, c in ctx.idx.asn_cnpj.items() if c[:8] == raiz), None)
    return ctx.idx.nome_publico(raiz, asn, None) + sufixo


def _dict(d: dict, chave_pai: Any, ctx: _Contexto, herdado: Any = None) -> Any:
    """`herdado`: o titular do registro pai, para os itens de uma lista de nomes do próprio titular (`alt_names`: [{name, source}])."""
    props = d.get("properties") if d.get("type") == "Feature" else None
    ti = _titular_do_dict(props if isinstance(props, dict) else d, chave_pai, ctx) or herdado
    entidade_e_nome = _CHAVE_ENTIDADE in d and not _MARCAS_DE_REGISTRO_DE_EMPRESA.isdisjoint(d)
    novo: Optional[dict] = None

    def troca(k, v):
        nonlocal novo
        if novo is None:
            novo = dict(d)
        novo[k] = v

    for k, v in d.items():
        if isinstance(k, str) and k in _NAO_PERCORRER:
            continue
        ks = k if isinstance(k, str) else ""
        if ti is not None and ctx.pontos and ks in _CHAVE_ENDERECO:
            if novo is None:
                novo = dict(d)
            novo.pop(k, None)
            continue
        if isinstance(v, str):
            e_nome = _CHAVE_NOME.match(ks) is not None or (entidade_e_nome and ks == _CHAVE_ENTIDADE)
            if ti is not None and e_nome:
                n = _nome_de_titular(v, ti, ctx)
            elif ti is None and ks.isdigit() and (tk := _titular_da_chave(ks, ctx)) is not None and _LETRA.search(v):
                n = _nome_de_titular(v, tk, ctx)                  # mapa por ASN (`asns/names.json`): a chave é o titular
            elif ti is None and ctx.idx.nomes and (e_nome or e_campo_de_nome(ks) or ks.isdigit()):
                n = _nome_sem_titular(v, ctx) or v
            else:
                continue
            if n != v:
                troca(k, n)
        elif isinstance(v, dict):
            n = _dict(v, k, ctx)
            if ti is not None and ctx.pontos and ks.startswith(("endereco", "address")):        # `endereco_sede` do titular: só município e UF ficam
                n = {a: b for a, b in n.items() if a not in _CHAVE_ENDERECO and a.lower() not in _CHAVE_LAT | _CHAVE_LON}
            if n is not v:
                troca(k, n)
        elif isinstance(v, list):
            n = _lista(v, k, ctx, ti if ti is not None and _LISTA_DE_NOMES.match(ks) else None)
            if n is not v and n != v:
                troca(k, n)
    if ti is not None and ctx.pontos:
        base = novo if novo is not None else dict(d)
        if props is not None:                           # feição GeoJSON: o ponto está na geometria; o centróide sai do registro das propriedades
            geom = d.get("geometry")
            if isinstance(geom, dict) and geom.get("type") == "Point":
                ponto = posicao_reduzida(props)
                base["geometry"] = {"type": "Point", "coordinates": [ponto[1], ponto[0]]} if ponto else None
                novo = base
        if any(isinstance(k, str) and k.lower() in (_CHAVE_LAT | _CHAVE_LON) for k in d):
            _reduzir_ponto(d, base)
            novo = base
    return d if novo is None else novo


def _lista(lst: list, chave_pai: Any, ctx: _Contexto, ti: Any = None) -> Any:
    """`ti`: titular dono de uma lista de nomes dele (`alt_names`, `nomes`): os textos e os itens `{name, source}` levam o nome público."""
    novo: Optional[list] = None
    nome = ctx.idx.nomes and isinstance(chave_pai, str) and e_campo_de_nome(chave_pai)
    for i, v in enumerate(lst):
        n = v
        if isinstance(v, dict):                          # registros de um mapa por CNPJ ou ASN (`by_cnpj: {cnpj: [registro]}`): a chave do pai vale
            n = _dict(v, chave_pai if isinstance(chave_pai, str) and chave_pai.isdigit() else None, ctx, herdado=ti)
        elif isinstance(v, list):
            n = _lista(v, None, ctx, ti)
        elif isinstance(v, str):
            if ti is not None:
                n = _nome_de_titular(v, ti, ctx)
            elif nome:
                n = _nome_sem_titular(v, ctx) or v
        if n is not v and n != v:
            if novo is None:
                novo = list(lst)
            novo[i] = n
    return lst if novo is None else novo


def aplicar(doc: Any, idx: Optional[Indice], pontos: bool = True) -> Any:
    """`doc` com o nome e a posição dos titulares EI/MEI no padrão público (D1). **Não altera o original**: devolve o mesmo objeto se nada
    muda e uma cópia rasa dos ramos que mudam. Sem índice (ou vazio), devolve `doc`."""
    if not idx:
        return doc
    ctx = _Contexto(idx, pontos)
    if isinstance(doc, dict):
        return _dict(doc, None, ctx)
    if isinstance(doc, list):
        return _lista(doc, None, ctx)
    return doc


def posicao_de_linha(linha: dict, idx: Optional[Indice]) -> dict:
    """Linha de tabela (`query`) de titular EI/MEI com a posição reduzida ao centróide do município; o resto passa como está."""
    if not idx:
        return linha
    ti = _titular_do_dict(linha, None, _Contexto(idx, True))
    if ti is None:
        return linha
    nova = dict(linha)
    _reduzir_ponto(linha, nova)
    return nova


def aplicar_em_texto_json(texto: str, idx: Optional[Indice]) -> str:
    """O mesmo sobre um JSON serializado (resource do MCP: texto). Texto que não é JSON, ou sem titular, volta como veio."""
    if not idx or not isinstance(texto, str) or texto[:1] not in ("{", "["):
        return texto
    try:
        doc = json.loads(texto)
    except ValueError:
        return texto
    novo = aplicar(doc, idx)
    if novo is doc:
        return texto
    ini = texto[:400]
    kw: dict = {"ensure_ascii": texto.isascii()}
    if "\n" in ini.strip():
        linha = ini.split("\n", 2)[1] if ini.count("\n") >= 1 else ""
        kw["indent"] = max(1, len(linha) - len(linha.lstrip(" ")))
    return json.dumps(novo, **kw)


def na_saida(valor: Any, idx: Optional[Indice]) -> Any:
    """Resultado de uma tool ou resource do MCP: objeto (percurso) ou texto JSON."""
    if isinstance(valor, str):
        return aplicar_em_texto_json(valor, idx)
    return aplicar(valor, idx)
