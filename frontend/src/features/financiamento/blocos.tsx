// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { BlocoProps } from '../entidade/registry'
import type { OperadoraCtx } from '../operadora/contexto'
import type { FinanciamentoOperadora, SancaoRegistro } from '../../types/api'

const reais = (v?: number | null) => (v == null ? '—' : `R$ ${v.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}`)
const dataBr = (d?: string | null) => (d ? d.split('-').reverse().join('/') : '—')
const LINHAS = 10

function Rodape({ f, fonte }: { f: FinanciamentoOperadora; fonte: 'bndes' | 'cgu' }) {
  const ref = fonte === 'bndes' ? `BNDES, dados abertos (ODbL), conjunto de ${f.fontes.bndes.dump_reference ?? 's/d'}` : `CGU, Portal da Transparência (CEIS e CNEP), arquivos de ${Object.values(f.fontes.cgu.arquivos ?? {}).join(' e ') || 's/d'}`
  return <p className="text-xs text-gray-500">{ref}; snapshot {f.snapshot_date}. {f.limites}</p>
}

/** Operações do BNDES da operadora: totais em R$ nominais da data da contratação, série por ano e as mais recentes. Só operações diretas; ausência não é prova de que nunca houve crédito. */
export function CreditoPublicoBloco({ dados }: BlocoProps<OperadoraCtx>) {
  const f = dados.financiamento
  const b = f?.financiamento
  if (!f || !b) return null
  return (
    <div className="space-y-3 text-sm" data-testid="credito-publico">
      <p data-testid="credito-resumo">
        <span className="tabular-nums">{b.operacoes_total}</span> operação(ões) direta(s) com o BNDES entre {dataBr(b.primeira)} e {dataBr(b.ultima)}: <span className="tabular-nums">{reais(b.contratado_total)}</span> contratados e{' '}
        <span className="tabular-nums">{reais(b.desembolsado_total)}</span> desembolsados (valores nominais, sem correção).
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead><tr className="text-left text-gray-500"><th className="py-1 pr-3">Ano</th><th className="pr-3 text-right">Operações</th><th className="pr-3 text-right">Contratado</th><th className="text-right">Desembolsado</th></tr></thead>
          <tbody>
            {b.por_ano.map((a) => (
              <tr key={a.ano} className="border-t border-gray-100"><td className="py-1 pr-3">{a.ano}</td><td className="pr-3 text-right tabular-nums">{a.operacoes}</td><td className="pr-3 text-right tabular-nums">{reais(a.contratado)}</td><td className="text-right tabular-nums">{reais(a.desembolsado)}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <details>
        <summary className="cursor-pointer text-xs text-primario-600">Operações mais recentes ({Math.min(b.operacoes.length, LINHAS)} de {b.operacoes_total})</summary>
        <ul className="mt-2 space-y-1 text-xs">
          {b.operacoes.slice(0, LINHAS).map((o) => (
            <li key={`${o.cnpj}-${o.contrato}`}>{dataBr(o.data)} · {o.produto}{o.instrumento ? ` / ${o.instrumento}` : ''} · {o.uf} · <span className="tabular-nums">{reais(o.contratado)}</span>{o.projeto ? ` · ${o.projeto}` : ''}</li>
          ))}
        </ul>
      </details>
      <Rodape f={f} fonte="bndes" />
    </div>
  )
}

function Sancao({ s }: { s: SancaoRegistro }) {
  const periodo = s.sem_prazo || s.sem_fim_informado || !s.fim ? `desde ${dataBr(s.inicio)}, sem data final informada` : `${dataBr(s.inicio)} a ${dataBr(s.fim)}`
  return (
    <li className="text-xs" data-testid="sancao-item">
      <span className="font-medium">{s.cadastro}</span> · {s.categoria} · {periodo} · {s.orgao}{s.uf_orgao && !s.orgao.includes(`(${s.uf_orgao})`) ? `/${s.uf_orgao}` : ''} ({s.esfera.toLowerCase()})
      {s.multa != null ? <> · multa <span className="tabular-nums">{reais(s.multa)}</span></> : null}
      {s.fundamento ? <span className="block text-gray-500">{s.fundamento}</span> : null}
      {s.cnpj.slice(8, 12) !== '0001' ? <span className="block text-gray-500">CNPJ {s.cnpj} (estabelecimento não matriz)</span> : null}
    </li>
  )
}

/** Sanções do CEIS e do CNEP: registro do órgão sancionador na data do arquivo da CGU, sem adjetivo; vigentes, futuras e encerradas separadas. */
export function SancoesBloco({ dados }: BlocoProps<OperadoraCtx>) {
  const f = dados.financiamento
  const s = f?.sancoes
  if (!f || !s) return null
  const grupos: Array<[string, SancaoRegistro[]]> = [['Constam no cadastro (sem fim informado ou fim futuro)', s.vigentes], ['Com início futuro', s.futuras], ['Encerradas', s.encerradas]]
  return (
    <div className="space-y-3 text-sm" data-testid="sancoes">
      <p data-testid="sancoes-resumo">Há <span className="tabular-nums">{s.total}</span> registro(s) no CEIS/CNEP para esta empresa: <span className="tabular-nums">{s.vigentes.length}</span> constando sem fim ou com fim futuro, <span className="tabular-nums">{s.encerradas.length}</span> encerrada(s){s.futuras.length ? `, ${s.futuras.length} com início futuro` : ''}.</p>
      {grupos.filter(([, l]) => l.length > 0).map(([titulo, lista]) => (
        <div key={titulo}>
          <h4 className="text-xs font-semibold text-gray-600">{titulo}</h4>
          <ul className="mt-1 space-y-2">{lista.map((x) => <Sancao key={`${x.cadastro}-${x.codigo}`} s={x} />)}</ul>
        </div>
      ))}
      <Rodape f={f} fonte="cgu" />
    </div>
  )
}
