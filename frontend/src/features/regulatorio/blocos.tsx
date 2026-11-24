// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from '../../components/layout/LinkDatado'
import { fetchFustMunicipios } from '../../services/api'
import { useActiveDate } from '../../hooks/useSnapshot'
import type { BlocoProps } from '../entidade/registry'
import type { MunicipioCtx } from '../municipio/contexto'
import type { OperadoraCtx } from '../operadora/contexto'
import type { UfCtx } from '../uf/contexto'
import type { FustMeta, FustTotais, RegMeta } from '../../types/api'
import { useOrdenacao } from '../../lib/ordenacao'
import { ThOrdenavel } from '../../components/ui/ThOrdenavel'

const inteiro = (v?: number | null) => (v == null ? '—' : Math.round(v).toLocaleString('pt-BR'))
const reais = (v?: number | null) => (v == null ? '—' : v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }))
const dec = (v?: number | null) => (v == null ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }))

/** O que o dado é e não é, sempre junto do número: cadastro da Anatel, sem executora e sem desembolso. */
function Nota({ m }: { m: FustMeta }) {
  return (
    <p className="text-xs text-gray-500">
      Compromissos do FUST registrados pela Anatel (arquivo de {m.data_arquivo ? new Date(m.data_arquivo).toLocaleDateString('pt-BR') : 'data não informada'}). {m.limites}
    </p>
  )
}

function Situacao({ t }: { t: FustTotais }) {
  return (
    <dl className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
      <div><dt className="inline text-gray-500">Atendidos </dt><dd className="inline font-medium tabular-nums">{inteiro(t.atendidos)}</dd></div>
      <div><dt className="inline text-gray-500">A vencer </dt><dd className="inline font-medium tabular-nums">{inteiro(t.a_vencer)}</dd></div>
      <div><dt className="inline text-gray-500">Em apuração </dt><dd className="inline font-medium tabular-nums">{inteiro(t.em_apuracao)}</dd></div>
    </dl>
  )
}

function Programas({ programas, nomes }: { programas: Record<string, number>; nomes: Record<string, string> }) {
  const itens = Object.entries(programas)
  if (itens.length === 0) return null
  return (
    <ul className="text-sm divide-y divide-gray-50">
      {itens.map(([cod, n]) => (
        <li key={cod} className="py-1 flex justify-between gap-4"><span>{cod} · {nomes[cod] ?? 'programa'}</span><span className="tabular-nums text-gray-600">{inteiro(n)}</span></li>
      ))}
    </ul>
  )
}

/** Compromissos do FUST no município: situação, programas e valor previsto. Município sem compromisso mostra zero. */
export function FustMunicipioBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const f = dados.fust
  if (!f) return null
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
        <div><span className="text-2xl font-semibold tabular-nums">{inteiro(f.compromissos)}</span> <span className="text-sm text-gray-500">compromissos</span></div>
        {f.compromissos > 0 && <div className="text-sm text-gray-600">{reais(f.investimento)} previstos</div>}
        {f.por_10mil_hab != null && <div className="text-sm text-gray-600"><span className="font-medium tabular-nums">{dec(f.por_10mil_hab)}</span> por 10 mil habitantes</div>}
        {f.comparacao_uf && <div className="text-sm text-gray-500">Na UF {f.uf}: {inteiro(f.comparacao_uf.municipios_com_compromisso)} de {inteiro(f.comparacao_uf.municipios)} municípios têm compromisso</div>}
      </div>
      {f.compromissos > 0 && <Situacao t={f} />}
      <Programas programas={f.programas} nomes={f.programas_nomes} />
      {f.compromissos === 0 && <p className="text-sm text-gray-600">Nenhum compromisso do FUST registrado para este município.</p>}
      <Nota m={f} />
    </div>
  )
}

/** Compromissos do FUST na UF e os municípios com mais compromissos, com filtro por programa. */
export function FustUfBloco({ dados }: BlocoProps<UfCtx>) {
  const f = dados.fust
  const [programa, setPrograma] = useState('')
  // A tabela traz só os 10 primeiros: a ordem vai ao servidor (`ordem`), que ordena do maior para o menor.
  const [campo, setCampo] = useState<'compromissos' | 'atendidos' | 'investimento'>('compromissos')
  const date = useActiveDate() ?? undefined
  const q = useQuery({
    queryKey: ['fust-municipios', date, dados.uf, programa, campo], enabled: !!f,
    queryFn: () => fetchFustMunicipios({ date, uf: dados.uf, programa: programa || undefined, limit: 10, ...(campo === 'compromissos' ? {} : { ordem: campo }) }), staleTime: 10 * 60 * 1000, retry: false,
  })
  const th = (c: typeof campo) => ({ campo: c, ordem: { campo, dir: 'desc' as const }, onOrdenar: () => setCampo(c) })
  if (!f) return null
  const r = f.resumo
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
        <div><span className="text-2xl font-semibold tabular-nums">{inteiro(r.compromissos)}</span> <span className="text-sm text-gray-500">compromissos · {reais(r.investimento)} previstos</span></div>
        <div className="text-sm text-gray-600">{inteiro(r.municipios_com_compromisso)} de {inteiro(r.municipios)} municípios têm compromisso</div>
      </div>
      <Situacao t={r} />
      <Programas programas={r.programas} nomes={f.programas_nomes} />
      <label className="text-sm text-gray-600 flex flex-col w-fit">Municípios com mais compromissos em
        <select value={programa} onChange={(ev) => setPrograma(ev.target.value)} className="border border-gray-300 rounded px-2 py-1.5 text-sm">
          <option value="">qualquer programa</option>
          {Object.keys(r.programas).map((c) => <option key={c} value={c}>{c} · {f.programas_nomes[c] ?? ''}</option>)}
        </select>
      </label>
      {q.data && (
        <table className="text-xs min-w-full">
          <thead className="text-gray-500"><tr><th scope="col" className="text-left px-2 py-1">Município</th><ThOrdenavel {...th('compromissos')} alinhar="right" className="text-right px-2 py-1">Compromissos</ThOrdenavel><ThOrdenavel {...th('atendidos')} alinhar="right" className="text-right px-2 py-1">Atendidos</ThOrdenavel><ThOrdenavel {...th('investimento')} alinhar="right" className="text-right px-2 py-1">Previsto</ThOrdenavel></tr></thead>
          <tbody>
            {q.data.items.map((m) => (
              <tr key={m.ibge} className="border-t border-gray-100">
                <td className="px-2 py-1"><Link to={`/municipio/${m.ibge}`} className="text-primario-600 hover:underline">{m.nome ?? m.ibge}</Link></td>
                <td className="px-2 py-1 text-right tabular-nums">{inteiro(m.compromissos)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{inteiro(m.atendidos)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{reais(m.investimento)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <Nota m={f} />
    </div>
  )
}

/** Multas constituídas contra a empresa (raiz do CNPJ) por serviço. Sempre com o aviso de que multa constituída não é condenação definitiva. */
export function MultasOperadoraBloco({ dados }: BlocoProps<OperadoraCtx>) {
  const m = dados.multas
  const { ordenados, props } = useOrdenacao(m?.por_grupo, {
    servico: (g) => g.grupo,
    multas: (g) => g.multas,
    quitadas: (g) => g.situacoes.Quitado ?? 0,
    devedor: (g) => (g.situacoes.Devedor ?? 0) + (g.situacoes.Parcial ?? 0),
    saldo: (g) => g.saldo,
    anos: { valor: (g) => g.primeiro_ano, primeiro: 'asc' },
  })
  if (!m) return null
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
        <div><span className="text-2xl font-semibold tabular-nums">{inteiro(m.multas)}</span> <span className="text-sm text-gray-500">multas constituídas</span></div>
        <div className="text-sm text-gray-600">saldo devedor atualizado {reais(m.saldo)} · valor original {reais(m.original)} · pago {reais(m.pago)}</div>
      </div>
      <table className="text-xs min-w-full">
        <thead className="text-gray-500"><tr><ThOrdenavel {...props('servico')} className="text-left px-2 py-1">Serviço</ThOrdenavel><ThOrdenavel {...props('multas')} alinhar="right" className="text-right px-2 py-1">Multas</ThOrdenavel><ThOrdenavel {...props('quitadas')} alinhar="right" className="text-right px-2 py-1">Quitadas</ThOrdenavel><ThOrdenavel {...props('devedor')} alinhar="right" className="text-right px-2 py-1">Devedor</ThOrdenavel>
          <ThOrdenavel {...props('saldo')} alinhar="right" className="text-right px-2 py-1">Saldo</ThOrdenavel><ThOrdenavel {...props('anos')} className="text-left px-2 py-1">Anos</ThOrdenavel></tr></thead>
        <tbody>
          {ordenados.map((g) => (
            <tr key={g.grupo} className="border-t border-gray-100">
              <td className="px-2 py-1">{g.grupo}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(g.multas)}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(g.situacoes.Quitado ?? 0)}</td>
              <td className="px-2 py-1 text-right tabular-nums">{inteiro((g.situacoes.Devedor ?? 0) + (g.situacoes.Parcial ?? 0))}</td><td className="px-2 py-1 text-right tabular-nums">{reais(g.saldo)}</td>
              <td className="px-2 py-1">{g.primeiro_ano === g.ultimo_ano ? g.primeiro_ano : `${g.primeiro_ano}–${g.ultimo_ano}`}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-xs text-gray-500">Soma da matriz e das filiais (raiz do CNPJ {m.raiz}). <Link to="/regulatorio?aba=multas" className="text-primario-600 hover:underline">Regulatório</Link>.</p>
      <Nota2 m={m} />
    </div>
  )
}

function Nota2({ m }: { m: RegMeta }) {
  return <p className="text-xs text-gray-500">Anatel, dados abertos (arquivo de {m.data_arquivo ? new Date(m.data_arquivo).toLocaleDateString('pt-BR') : 'data não informada'}). {m.limites}</p>
}
