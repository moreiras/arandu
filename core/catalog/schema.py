# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Esquema do catálogo de fontes e produtos (`catalog/`).

Um `source.yaml` descreve algo que vem de fora (ou derivado só dele); um `product.yaml`, um
cruzamento que gera artefatos publicados. O catálogo é a fonte única da documentação gerada
(`scripts/gen_docs.py`). Valor desconhecido é escrito literalmente `nao_verificado` — nunca
chutado — e é contado pelo validador como tarefa aberta.
"""
from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

NAO_VERIFICADO = "nao_verificado"

ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
# Chaves de junção (seção 1.4); 'mes_referencia' é o mês da declaração na origem.
CHAVES = {"asn", "cnpj", "prefixo", "ibge", "uf", "ixp", "grupo", "mes", "mes_referencia",
          "pais", "ponto", "facilidade", "cabo", "rede", "ano"}

Cadencia = Literal["diaria", "semanal", "quinzenal", "mensal", "trimestral", "semestral", "anual",
                   "irregular", "continua", "estatica", "nao_verificado"]
Coleta = Literal["diaria", "semanal", "mensal", "sob_demanda", "diaria_se_novo_mes", "manual"]


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Origem(_Base):
    """`uso_comercial`: permitido = licença aberta que admite uso comercial (mesmo com atribuição);
    restrito = há condição que limita ou exige autorização (não comercial, share-alike, AUP, EULA);
    nao_verificado = termos não localizados/lidos. Regra: um eventual recurso pago não
    depende de fonte restrito ou nao_verificado."""
    url: Optional[str] = None
    formato: str
    licenca: str                                   # texto curto; 'nao_verificado' se desconhecida
    termos: Optional[str] = None                   # URL dos termos de uso
    uso_comercial: Literal["permitido", "restrito", "nao_verificado"]
    nota: Optional[str] = None                     # evidência da licença / ressalvas


class CadenciaFonte(_Base):
    fonte_atualiza: Cadencia                       # quando a origem publica
    coleta: Coleta                                 # alvo (plano)
    coleta_atual: Coleta                           # o que o pipeline faz hoje
    frescor_maximo: str                            # '45d', '8d', 'nao_verificado'
    janela_horaria: Optional[str] = None

    @field_validator("frescor_maximo")
    @classmethod
    def _frescor(cls, v: str) -> str:
        if v != NAO_VERIFICADO and not re.fullmatch(r"\d+[dhw]", v):
            raise ValueError("frescor_maximo deve ser '<n>d', '<n>h', '<n>w' ou nao_verificado")
        return v


class Saidas(_Base):
    bruto: list[str] = Field(default_factory=list)
    normalizado: list[str] = Field(default_factory=list)
    publicado: list[str] = Field(default_factory=list)   # só em produtos (e curadas lidas direto)
    fragmentos: list[str] = Field(default_factory=list)


class Campo(_Base):
    nome: str
    tipo: str
    significado: str                               # obrigatório: o que o campo quer dizer
    tratamento: Optional[str] = None               # como é transformado/agregado
    publicado_em: list[str] = Field(default_factory=list)
    sensivel: bool = False                         # dado de pessoa/contato (privacidade)


class Retencao(_Base):
    bruto: Optional[str] = None
    normalizado: Optional[str] = None
    publicado: Optional[str] = None


class Armazem(_Base):
    """O que entra na versão da fonte no armazém (padrão: normalized + published declarados, sem caches)."""
    incluir: list[str] = Field(default_factory=list)    # 'raw:padrão' | 'normalized:padrão' | 'published:padrão' (substitui o padrão)
    sempre_coletar: bool = False                         # a versão não traz o bruto que as etapas seguintes leem: `--due` nunca a pula
    manter_versoes: Optional[int] = Field(default=None, ge=2)   # histórico fino (RPKI, nicbr-asn-blk…): versões que o gc guarda, acima do perfil


class Publicar(_Base):
    """Publica o normalizado da fonte como está: `de` em normalized/<data>/, `para` em published/<data>/ — fonte simples sem produto próprio."""
    de: str
    para: str


class EtapaInline(_Base):
    """Etapa declarada na própria fonte: evita o arquivo em catalog/steps/ para a fonte simples."""
    args: list[str] = Field(default_factory=lambda: ["--date", "{date}"])
    tentativas: int = Field(default=3, ge=1, le=5)
    espera_s: int = Field(default=60, ge=0, le=900)
    politica_falha: Optional[Literal["critica", "opcional", "usar_ultima_valida"]] = None     # padrão: a da fonte
    memoria_mb: Optional[int] = Field(default=None, ge=1)    # ver Step.memoria_mb
    continua: bool = False                                    # ver Step.continua
    destinos: list[str] = Field(default_factory=list)         # ver Step.destinos
    aceita_force: bool = False                                # ver Step.aceita_force


class Source(_Base):
    id: str
    nome: str
    tipo: Literal["bruta", "derivada", "curada"]
    ativa: bool
    modulo: Optional[str] = None                   # módulo Python (bruta/derivada)
    arquivo: Optional[str] = None                  # arquivo em config/ (curada)
    publicavel: bool                               # False: nunca chega a published/, API ou MCP
    exposicao: Literal["aberta", "login", "nenhuma"] = "aberta"   # nível de acesso do que é servido; 'login' = só usuário logado
    decisao_exposicao: Optional[str] = None        # por que a exposição é a que é, quando é decisão do projeto (D9); só com exposicao=aberta
    atribuicao: Optional[str] = None               # a atribuição exigida pela fonte, como deve aparecer em quem a republica
    descricao: str
    origem: Optional[Origem] = None
    cadencia: CadenciaFonte
    politica_falha: Literal["critica", "opcional", "usar_ultima_valida"]
    entradas: list[str] = Field(default_factory=list)
    saidas: Saidas
    chaves: list[str] = Field(default_factory=list)
    campos: list[Campo] = Field(default_factory=list)
    limites: str
    retencao: Optional[Retencao] = None
    fixture: Optional[str] = None
    pendencias: list[str] = Field(default_factory=list)   # tarefas abertas (o que é nao_verificado e por quê)
    armazem: Optional[Armazem] = None                      # o que versionar no armazém; padrão: normalizado + publicado
    etapa: Optional[EtapaInline] = None                    # etapa do arandu declarada aqui; sem isso, a etapa fica em catalog/steps/
    publicar: Optional[Publicar] = None                    # publica o normalizado como está

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        if not ID_RE.match(v):
            raise ValueError("id deve casar [a-z][a-z0-9_]*")
        return v

    @field_validator("chaves")
    @classmethod
    def _chaves(cls, v: list[str]) -> list[str]:
        ruim = [c for c in v if c not in CHAVES]
        if ruim:
            raise ValueError(f"chaves fora do vocabulário: {ruim}")
        return v

    @model_validator(mode="after")
    def _coerencia(self) -> "Source":
        if self.tipo == "curada":
            if not self.arquivo:
                raise ValueError("fonte curada exige 'arquivo' (em config/)")
        else:
            if not self.modulo:
                raise ValueError("fonte bruta/derivada exige 'modulo'")
        if not self.publicavel and self.exposicao != "nenhuma":
            raise ValueError("publicavel=false exige exposicao=nenhuma")
        if self.publicavel and self.exposicao == "nenhuma":
            raise ValueError("exposicao=nenhuma exige publicavel=false")
        if self.decisao_exposicao and self.exposicao != "aberta":
            raise ValueError("'decisao_exposicao' só vale com exposicao=aberta")
        if self.tipo == "bruta" and self.origem is None:
            raise ValueError("fonte bruta exige 'origem'")
        if self.tipo == "derivada" and not self.entradas:
            raise ValueError("fonte derivada exige 'entradas'")
        if self.etapa and not self.modulo:
            raise ValueError("'etapa' inline exige 'modulo'")
        if self.publicar and not self.publicavel:
            raise ValueError("'publicar' exige publicavel=true")
        return self


class EntradaProduto(_Base):
    source: Optional[str] = None
    product: Optional[str] = None

    @model_validator(mode="after")
    def _um(self) -> "EntradaProduto":
        if bool(self.source) == bool(self.product):
            raise ValueError("entrada deve ter exatamente um de 'source' ou 'product'")
        return self


class Product(_Base):
    id: str
    nome: str
    descricao: str
    modulo: Optional[str] = None                   # onde é construído
    entradas: list[EntradaProduto]
    chaves_de_juncao: list[str] = Field(default_factory=list)
    saidas: Saidas
    campos: list[Campo] = Field(default_factory=list)
    cenarios_de_teste: list[str] = Field(default_factory=list)
    limites: Optional[str] = None
    pendencias: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        if not ID_RE.match(v):
            raise ValueError("id deve casar [a-z][a-z0-9_]*")
        return v

    @field_validator("chaves_de_juncao")
    @classmethod
    def _chaves(cls, v: list[str]) -> list[str]:
        ruim = [c for c in v if c not in CHAVES]
        if ruim:
            raise ValueError(f"chaves fora do vocabulário: {ruim}")
        return v


class ExecutarSe(_Base):
    """Janela de execução por marcador: a etapa só roda quando o marcador não existe ou é mais velho que o limite."""
    marcador: str                                  # arquivo JSON relativo à raiz do repositório
    campo: str = "date"                            # chave AAAA-MM-DD dentro do marcador
    max_idade_dias: int
    env_max_idade: Optional[str] = None            # variável de ambiente que sobrescreve o limite


class Step(_Base):
    """Etapa do pipeline: o que o executor `arandu` roda, em que ordem e com que política.

    A ordem é calculada: dependências vêm das `entradas` das fontes/produtos que a etapa produz mais
    `depois_de`; `ordem` é só o desempate estável entre etapas sem dependência entre si.
    """
    id: str
    nome: str
    ordem: int                                     # desempate da ordem calculada; única
    runner: Literal["worker", "host"] = "worker"   # host: delegada ao shell (docker compose no host)
    modulo: Optional[str] = None                   # python -m <modulo> (worker)
    args: list[str] = Field(default_factory=lambda: ["--date", "{date}"])
    comando: list[str] = Field(default_factory=list)   # argv literal (host); {date} é substituído
    fontes: list[str] = Field(default_factory=list)    # fontes que a etapa produz (derivam dependências)
    produtos: list[str] = Field(default_factory=list)  # produtos que a etapa completa (derivam dependências)
    parcial: list[str] = Field(default_factory=list)   # produtos a que a etapa só contribui (sem derivar dependências)
    refresca: list[str] = Field(default_factory=list)  # produtos já gerados que a etapa atualiza no lugar
    depois_de: list[str] = Field(default_factory=list)       # dependências explícitas (ids de etapa)
    somente_se_executou: list[str] = Field(default_factory=list)   # roda só se estas etapas rodaram nesta execução
    politica_falha: Literal["critica", "opcional", "usar_ultima_valida"]
    executar_se: Optional[ExecutarSe] = None
    gravar_marcador: Optional[str] = None          # arquivo JSON {date: ...} gravado após sucesso
    reaproveita: Optional[str] = None              # arquivo (com {date}) copiado do último snapshot se pulada ou falhou
    tentativas: int = Field(default=1, ge=1, le=5)     # execuções antes de dar a etapa por falha (erro transitório de rede)
    espera_s: int = Field(default=60, ge=0, le=900)    # pausa entre tentativas
    so_com_only: bool = False                      # etapa manual (backfill): só roda com `arandu run --only <id>`, nunca no pipeline normal
    pesada: bool = False                           # coleta que ocupa GBs: não roda com o disco acima do limite de bloqueio (arandu doctor)
    replay: bool = False                           # reexecutada por `arandu run --compare` (equivale aos estágios do replay)
    replay_se_publicado: Optional[str] = None      # só no compare se este arquivo existir no publicado original
    # Pico de memória da etapa, medido (`pico_mem_mb` nos relatórios; `arandu memoria` resume), com folga. Sem ele a etapa nunca roda
    # ao lado de outra: é a reserva que o paralelismo das coletas desconta do orçamento de memória do worker.
    memoria_mb: Optional[int] = Field(default=None, ge=1)
    # Coleta contínua (rodízio diário com orçamento): roda na trilha própria (`arandu continuo`, em horário próprio e com lock próprio),
    # nunca dentro do pipeline; no pipeline, a etapa só restaura do armazém a última versão coletada.
    continua: bool = False
    # Hosts que a etapa consulta além do `origem.url` das fontes dela (que entra sozinho). Cortesia por destino: nunca duas consultas
    # ao mesmo host ao mesmo tempo (lock por host em data/ops/destinos/, entre o pipeline e a trilha contínua).
    destinos: list[str] = Field(default_factory=list)
    # O módulo da etapa aceita `--force` (refazer o que já existe) e `arandu run --force` o repassa. Só declare se o argparse do módulo
    # tem a opção e ela vale para os `args` da etapa: tests/unit/test_arandu_force.py confere. Etapa sem ele já refaz tudo a cada execução.
    aceita_force: bool = False
    descricao: str = ""

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        if not ID_RE.match(v):
            raise ValueError("id deve casar [a-z][a-z0-9_]*")
        return v

    @model_validator(mode="after")
    def _coerencia(self) -> "Step":
        if self.runner == "worker" and not self.modulo:
            raise ValueError("etapa worker exige 'modulo'")
        if self.runner == "host" and not self.comando:
            raise ValueError("etapa host exige 'comando'")
        if self.runner == "host" and self.aceita_force:
            raise ValueError("etapa de host não recebe --force: 'aceita_force' só vale para etapa worker")
        if self.politica_falha == "usar_ultima_valida" and not self.reaproveita:
            raise ValueError("usar_ultima_valida exige 'reaproveita'")
        return self
