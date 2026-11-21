# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Máscara do CPF embutido em nomes empresariais (CPF de pessoa física sai mascarado).

A Receita e a Anatel publicam a razão social de empresário individual e de MEI como "NOME DA PESSOA 12345678901": o CPF inteiro, com dígito
verificador válido. Aqui ele vira `***456789**`, o mesmo formato que a Receita usa para o CPF de sócio pessoa física.

Só mexe em sequências de exatamente 11 dígitos (não encostadas em outro dígito, então CNPJ e telefone com DDD+9 de outra largura não casam) que
passam na conta dos dígitos verificadores, e só nos campos de nome (`e_campo_de_nome`). O resto do documento não é tocado: o número Fistel
e outros identificadores também têm 11 dígitos e servem de chave de junção.

O campo de nome é reconhecido pelo **padrão** da chave, não por uma lista fechada: uma lista fechada deixa passar campos como `sici_empresa`. Chaves de identificador (`cnpj`, `cpf`, `fistel`, `_id`, `codigo`…) ficam de fora mesmo que contenham
um termo de nome; listas de texto sob uma chave de nome (`nomes`, `marcas`) também são mascaradas.
"""
from __future__ import annotations

import gzip
import io
import json
import os
import re
import zipfile
from pathlib import Path
from typing import Any, Optional

CAMPOS_DE_NOME = frozenset({"razao_social", "nome_fantasia", "nome", "name", "empresa", "nome_empresarial", "prestadora", "titular", "operadora",
                            "razao", "nome_empresa", "marca"})        # casos conhecidos; o critério é `e_campo_de_nome`
_TERMO_DE_NOME = re.compile(r"razao|nome|name|empresa|titular|prestadora|operadora|owner|holder|organizacao|organization|fantasia|marca|"
                            r"responsavel|socio|^org$|^org_")
_TERMO_DE_IDENTIFICADOR = re.compile(r"cnpj|cpf|fistel|identificador|(^|_)ids?($|_)|codigo|^cod_|^n_|^num|^qtd|^total|^data|^dt_|cep|ibge|telefone|fone|email")
_CACHE_CHAVES: dict[str, bool] = {}


_LETRA = re.compile(r"[A-Za-zÀ-ÿ]")


def e_campo_de_nome(chave: str) -> bool:
    """Chave cujo valor é nome de pessoa ou de empresa (onde a Receita e a Anatel embutem o CPF de EI/MEI)."""
    r = _CACHE_CHAVES.get(chave)
    if r is None:
        k = chave.lower()
        r = k in CAMPOS_DE_NOME or (_TERMO_DE_NOME.search(k) is not None and _TERMO_DE_IDENTIFICADOR.search(k) is None)
        if len(_CACHE_CHAVES) < 10_000:
            _CACHE_CHAVES[chave] = r
    return r


def _e_nome(chave, valor: str) -> bool:
    """Campo de nome, ou mapa por número (`asns/names.json`: {"266187": "NOME 12345678909"}) com texto que tem letra (prefixo e IP não têm)."""
    if not isinstance(chave, str):
        return False
    if chave.isdigit():
        return _LETRA.search(valor) is not None
    return e_campo_de_nome(chave)
_ONZE = re.compile(r"(?<![0-9])([0-9]{3})[.\s]?([0-9]{3})[.\s]?([0-9]{3})[-\s]?([0-9]{2})(?![0-9])")


_ONZE_BYTES = re.compile(rb"(?<![0-9])[0-9]{3}[.\s]?[0-9]{3}[.\s]?[0-9]{3}[-\s]?[0-9]{2}(?![0-9])")


def pode_ter_cpf(dados: bytes) -> bool:
    """Pré-filtro barato sobre o JSON bruto: sem nenhuma sequência com cara de CPF, o documento nem é percorrido."""
    return _ONZE_BYTES.search(dados) is not None


def cpf_valido(d: str) -> bool:
    """11 dígitos com os dois verificadores corretos (sequências repetidas como 11111111111 não contam)."""
    if len(d) != 11 or not d.isdigit() or d == d[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        if (soma * 10 % 11) % 10 != int(d[n]):
            return False
    return True


def mascarar_cpf(texto: Any) -> Any:
    """`texto` com cada CPF válido trocado por `***XXXXXX**` (os 6 dígitos do meio, como a Receita faz com sócio PF). Não-texto passa como está."""
    if not isinstance(texto, str) or len(texto) < 11:
        return texto

    def troca(m: re.Match) -> str:
        d = "".join(m.groups())
        return f"***{d[3:9]}**" if cpf_valido(d) else m.group(0)

    return _ONZE.sub(troca, texto)


def mascarar_cpf_em(doc: Any, contador: Optional[list] = None) -> Any:
    """Aplica `mascarar_cpf` aos campos de nome em qualquer profundidade, **no próprio objeto** (dicionários e listas); devolve o mesmo objeto.
    Com `contador` (lista), acrescenta 1 a `contador[0]` por valor trocado.

    No lugar, e não cópia, porque roda em documentos de dezenas de MB (na publicação: `mascarar_snapshot`)."""
    if contador is not None and not contador:
        contador.append(0)
    pilha = [doc]
    while pilha:
        x = pilha.pop()
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, str):
                    if _e_nome(k, v):
                        novo = mascarar_cpf(v)
                        if novo != v:
                            x[k] = novo
                            if contador is not None:
                                contador[0] += 1
                elif isinstance(v, list) and v and isinstance(k, str) and e_campo_de_nome(k):
                    for i, e in enumerate(v):
                        if isinstance(e, str):
                            novo = mascarar_cpf(e)
                            if novo != e:
                                v[i] = novo
                                if contador is not None:
                                    contador[0] += 1
                        elif isinstance(e, (dict, list)):
                            pilha.append(e)
                elif isinstance(v, (dict, list)):
                    pilha.append(v)
        elif isinstance(x, list):
            for v in x:
                if isinstance(v, (dict, list)):
                    pilha.append(v)
    return doc


def sem_socios_pessoa_fisica(doc: Any) -> Any:
    """Tira dos grupos societários (`grupos_societarios.json`) o nome e o documento de todo sócio que não é pessoa jurídica, e deixa em
    `nomes_em_comum` só nomes de sócios pessoa jurídica; **no próprio objeto**, como `mascarar_cpf_em`.

    Dado de pessoa física não vai para rota pública nem para o MCP (AGENTS.md). Fica o que não identifica a
    pessoa: o tipo e a qualificação de cada sócio (a contagem do quadro continua certa) e `socios_em_comum`. Sócio estrangeiro também sai
    sem nome: a Receita não diz se é pessoa física ou jurídica. Roda no pipeline (snapshots novos) e na leitura (os já publicados)."""
    by_cnpj = (doc or {}).get("by_cnpj") if isinstance(doc, dict) else None
    if not isinstance(by_cnpj, dict):
        return doc
    pj = {s.get("nome") for r in by_cnpj.values() for s in r.get("socios") or [] if s.get("tipo") == "juridica" and s.get("nome")}
    for r in by_cnpj.values():
        if r.get("socios"):
            r["socios"] = [s if s.get("tipo") == "juridica" else {k: v for k, v in s.items() if k not in ("nome", "documento")}
                           for s in r["socios"]]
        for rel in r.get("relacionadas_parcial") or []:
            if "nomes_em_comum" in rel:
                rel["nomes_em_comum"] = [n for n in rel["nomes_em_comum"] or [] if n in pj]
    return doc


# ── na publicação ────────────────────────────────────────────────────────

_NAO_TOCAR = frozenset({"manifest.json"})


def _estilo(texto: str) -> dict:
    """Formato do JSON gravado, deduzido do texto (sem serializar o documento de novo, que em arquivos de dezenas de MB custaria caro): o
    arquivo regravado sai igual ao resto do snapshot. É cosmético; o checksum é recalculado depois."""
    inicio = texto[:400]
    kw: dict = {"ensure_ascii": texto.isascii()}       # caractere acentuado cru: gravado com ensure_ascii=False
    if "\n" in inicio.strip():
        linha = inicio.split("\n", 2)[1] if inicio.count("\n") >= 1 else ""
        kw["indent"] = max(1, len(linha) - len(linha.lstrip(" ")))
    elif '": ' not in inicio and '", "' not in inicio:
        kw["separators"] = (",", ":")
    return kw


def _mascarar_bytes(dados: bytes) -> Optional[bytes]:
    """JSON em bytes com o CPF dos campos de nome mascarado, no mesmo estilo; None se nada mudou."""
    if not pode_ter_cpf(dados):
        return None
    try:
        texto = dados.decode("utf-8")
        doc = json.loads(texto)
    except (UnicodeDecodeError, ValueError):
        return None
    n: list = []
    mascarar_cpf_em(doc, n)
    if not n[0]:
        return None
    return (json.dumps(doc, **_estilo(texto)) + ("\n" if texto.endswith("\n") else "")).encode("utf-8")


def _gravar(caminho: Path, dados: bytes, copia_em: Optional[Path], rel: str) -> None:
    if copia_em is not None:                        # guarda o original antes de regravar (correção de snapshot já publicado)
        destino = copia_em / rel
        if not destino.exists():
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(caminho.read_bytes())
    tmp = caminho.with_name(caminho.name + ".tmp-cpf")
    tmp.write_bytes(dados)
    os.chmod(tmp, caminho.stat().st_mode & 0o777)
    os.replace(tmp, caminho)


def _sha(dados: bytes) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(dados).hexdigest()


def mascarar_snapshot(diretorio: Path, *, gravar: bool = True, copia_em: Optional[Path] = None) -> dict[str, str]:
    """Mascara o CPF embutido nos campos de nome de todos os artefatos de `published/<data>/` (JSON, GeoJSON, `.json.gz` e as entradas do
    `asns.zip` do formato compactado), regravando de forma atômica só o que muda. Devolve {caminho como no manifesto: novo checksum}
    (as entradas do ZIP aparecem como `asns/<arquivo>`, como nos checksums). Roda no fechamento do snapshot
    (`publish.coleta_checks.refresh_manifest`, antes dos checksums): a API serve o que está publicado, sem mascarar na leitura.
    `gravar=False` só conta; `copia_em` guarda os originais. Idempotente: o CPF mascarado (`***456789**`) não casa de novo."""
    alterados: dict[str, str] = {}
    for caminho in sorted(diretorio.rglob("*")):
        if not caminho.is_file() or caminho.name in _NAO_TOCAR or caminho.name.endswith((".tmp", ".tmp-cpf")):
            continue
        rel = str(caminho.relative_to(diretorio))
        nome = caminho.name
        novo = None
        if nome.endswith((".json", ".geojson")):
            novo = _mascarar_bytes(caminho.read_bytes())
        elif nome.endswith((".json.gz", ".geojson.gz")):
            try:
                cru = gzip.decompress(caminho.read_bytes())
            except (OSError, EOFError):
                continue
            m = _mascarar_bytes(cru)
            novo = gzip.compress(m, compresslevel=6, mtime=0) if m is not None else None
        elif nome.endswith(".zip"):
            alterados.update(_mascarar_zip(caminho, rel, gravar, copia_em))
            continue
        if novo is not None:
            if gravar:
                _gravar(caminho, novo, copia_em, rel)
            alterados[rel] = _sha(novo)
    return alterados


def _mascarar_zip(caminho: Path, rel: str, gravar: bool, copia_em: Optional[Path]) -> dict[str, str]:
    """`asns.zip` (formato compactado, core/layout.py): regrava o ZIP inteiro se alguma entrada mudar. Devolve {`asns/<entrada>`: checksum}."""
    try:
        with zipfile.ZipFile(caminho) as z:
            entradas = [(i, z.read(i.filename)) for i in z.infolist()]
    except (OSError, zipfile.BadZipFile):
        return {}
    prefixo = rel[:-len(".zip")]
    mudou, saida = {}, []
    for info, dados in entradas:
        novo = _mascarar_bytes(dados) if info.filename.endswith(".json") else None
        if novo is not None:
            mudou[f"{prefixo}/{info.filename}"] = _sha(novo)
        saida.append((info, novo if novo is not None else dados))
    if mudou and gravar:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for info, dados in saida:
                z.writestr(info, dados, compress_type=info.compress_type)
        _gravar(caminho, buf.getvalue(), copia_em, rel)
    return mudou
