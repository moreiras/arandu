// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../components/layout/LinkDatado'
import type { BlocoProps } from '../entidade/registry'
import type { AsnCtx } from '../asn/contexto'
import type { OperadoraCtx } from '../operadora/contexto'
import type { UfCtx } from '../uf/contexto'
import type { ClassePronto, PilarId, ProntidaoAgregado, ProntidaoMeta, ProntidaoPilar } from '../../types/api'

export const CLASSES: Record<ClassePronto, string> = { pronto: 'Pronto', em_progresso: 'Em progresso', atrasado: 'Atrasado', sem_dados: 'Sem dados suficientes' }
export const ORDEM_CLASSES: ClassePronto[] = ['pronto', 'em_progresso', 'atrasado', 'sem_dados']
const COR_CLASSE: Record<ClassePronto, string> = { pronto: 'bg-primario-700', em_progresso: 'bg-primario-400', atrasado: 'bg-gray-500', sem_dados: 'bg-gray-200' }
export const PILARES: PilarId[] = ['filtragem', 'anti_spoofing', 'coordenacao', 'validacao_global']
export const PORTE: Record<string, string> = { sem_usuarios: 'sem usuários estimados', ate_1000: 'até 1.000 usuários', de_1000_a_10000: '1.000 a 10.000 usuários', de_10000_a_100000: '10.000 a 100.000 usuários', de_100000_a_1000000: '100.000 a 1 milhão', acima_de_1000000: 'mais de 1 milhão de usuários' }
const num = (v: number | null | undefined, c = 1) => (v == null ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: c, maximumFractionDigits: c }))
const inteiro = (v?: number | null) => (v == null ? '—' : Math.round(v).toLocaleString('pt-BR'))

/** Barra com a distribuição dos ASNs por classe, em tons de azul e cinza (sem semáforo: o índice não é veredito). */
export function BarraClasses({ a, detalhe = false }: { a: ProntidaoAgregado; detalhe?: boolean }) {
  const total = a.asns || 1
  return (
    <div>
      <div className="flex h-3 rounded overflow-hidden bg-gray-100" role="img" aria-label={ORDEM_CLASSES.map((c) => `${CLASSES[c]} ${a.classes[c]}`).join(', ')}>
        {ORDEM_CLASSES.map((c) => a.classes[c] > 0 && <div key={c} className={COR_CLASSE[c]} style={{ width: `${(100 * a.classes[c]) / total}%` }} title={`${CLASSES[c]}: ${a.classes[c]}`} />)}
      </div>
      <ul className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-gray-600">
        {ORDEM_CLASSES.map((c) => <li key={c}><span className={`inline-block w-2 h-2 rounded-sm mr-1 ${COR_CLASSE[c]}`} />{CLASSES[c]} <span className="tabular-nums">{inteiro(a.classes[c])}</span></li>)}
      </ul>
      {detalhe && <ClassesPorRov a={a} />}
    </div>
  )
}

const soma = (c: Record<string, number>) => Object.values(c).reduce((x, y) => x + y, 0)

/** As mesmas classes em duas linhas, com e sem ROV medido (SEG-E5): "pronto" sem o pilar Filtragem usa o índice renormalizado sobre os pilares medidos. */
function ClassesPorRov({ a }: { a: ProntidaoAgregado }) {
  if (!a.classes_com_rov || !a.classes_sem_rov) return null
  const linhas: Array<[string, Record<ClassePronto, number>]> = [['com ROV medido', a.classes_com_rov], ['sem ROV medido', a.classes_sem_rov]]
  return (
    <div className="mt-2 space-y-1" data-testid="classes-por-rov">
      {linhas.map(([rotulo, c]) => {
        const n = soma(c)
        return (
          <div key={rotulo}>
            <div className="text-xs text-gray-600">{rotulo} <span className="tabular-nums">({inteiro(n)} ASNs)</span>: {ORDEM_CLASSES.map((k) => `${CLASSES[k]} ${inteiro(c[k])}`).join(' · ')}</div>
            <div className="flex h-2 rounded overflow-hidden bg-gray-100" role="img" aria-label={`${rotulo}: ${ORDEM_CLASSES.map((k) => `${CLASSES[k]} ${c[k]}`).join(', ')}`}>
              {ORDEM_CLASSES.map((k) => c[k] > 0 && <div key={k} className={COR_CLASSE[k]} style={{ width: `${(100 * c[k]) / (n || 1)}%` }} title={`${CLASSES[k]}: ${c[k]}`} />)}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function RodapeMetodo({ m }: { m: ProntidaoMeta }) {
  return (
    <p className="text-xs text-gray-500">
      Regras v{m.regras.versao} ({m.regras.hash}). {m.limites} <Link to="/seguranca-de-roteamento" className="text-primario-600 hover:underline">Metodologia e panorama</Link>.
    </p>
  )
}

function Pilar({ id, p, meta }: { id: PilarId; p: ProntidaoPilar; meta: ProntidaoMeta }) {
  const regra = meta.regras.pilares[id]
  return (
    <div className="border border-gray-100 rounded p-3 space-y-1.5">
      <div className="flex items-baseline justify-between">
        <h3 className="text-sm font-medium text-gray-800">{regra.nome}</h3>
        <span className="text-lg font-semibold tabular-nums">{num(p.score)}</span>
      </div>
      <p className="text-xs text-gray-500">{regra.descricao}</p>
      <ul className="text-xs divide-y divide-gray-50">
        {Object.entries(p.componentes).map(([c, v]) => (
          <li key={c} className="py-1 flex justify-between gap-3" title={regra.componentes[c]?.descricao}>
            <span>{c.replace(/_/g, ' ')} <span className="text-gray-400">peso {v.peso}</span></span>
            <span className="tabular-nums">{num(v.valor)}{v.detalhe ? <span className="text-gray-400"> · {Object.entries(v.detalhe).filter(([, x]) => x != null && x !== '').map(([k, x]) => `${k.replace(/_/g, ' ')} ${Array.isArray(x) ? x.join('/') : String(x)}`).join(', ')}</span> : null}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Índice de prontidão do ASN: total, classe, os pilares que entraram (com seus componentes) e os que ficaram sem dado. */
export function ProntidaoAsnBloco({ dados }: BlocoProps<AsnCtx>) {
  const p = dados.prontidao
  if (!p) return null
  const pilares = PILARES.filter((id) => p.pilares[id])
  return (
    <div className="space-y-3 text-sm" data-testid="prontidao">
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
        <div><span className="text-3xl font-semibold tabular-nums">{p.total == null ? '—' : num(p.total)}</span> <span className="text-gray-500">de 100 · {CLASSES[p.classe]}</span></div>
        {p.faixa_porte && <div className="text-gray-600">porte: {PORTE[p.faixa_porte] ?? p.faixa_porte}{p.usuarios ? <span className="tabular-nums"> ({inteiro(p.usuarios)} usuários estimados)</span> : null}</div>}
        {p.comparacao_uf && p.total != null && <div className="text-gray-600">mediana da UF: <span className="tabular-nums">{num(p.comparacao_uf.mediana)}</span> · país: <span className="tabular-nums">{num(p.brasil.mediana)}</span></div>}
      </div>
      {p.total == null && <p className="text-gray-600">Menos de {p.regras.minimos.pilares} pilares com dado: o ASN fica sem índice. Os componentes que existem aparecem abaixo.</p>}
      {p.pilares_sem_dado.length > 0 && (
        <p className="text-xs text-gray-600">Sem dado neste ASN (não entram na conta): {p.pilares_sem_dado.map((id) => p.regras.pilares[id].nome).join(', ')}.</p>
      )}
      <div className="grid md:grid-cols-2 gap-3">{pilares.map((id) => <Pilar key={id} id={id} p={p.pilares[id]!} meta={p} />)}</div>
      <RodapeMetodo m={p} />
    </div>
  )
}

function Agregado({ a, rotulo }: { a: ProntidaoAgregado; rotulo: string }) {
  return (
    <div className="space-y-2 text-sm">
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
        <div><span className="text-2xl font-semibold tabular-nums">{num(a.media_ponderada_usuarios)}</span> <span className="text-gray-500">média do índice ponderada pelos usuários estimados · {rotulo}</span></div>
        <div className="text-gray-600">mediana <span className="tabular-nums">{num(a.mediana)}</span> · {inteiro(a.asns_com_indice)} de {inteiro(a.asns)} ASNs com índice</div>
      </div>
      <BarraClasses a={a} detalhe />
      <p className="text-xs text-gray-500">ASNs com dado em cada pilar: {PILARES.map((id) => `${id.replace(/_/g, ' ')} ${inteiro(a.cobertura_pilares[id])}`).join(' · ')}.</p>
    </div>
  )
}

export function ProntidaoUfBloco({ dados }: BlocoProps<UfCtx>) {
  const p = dados.prontidao
  if (!p) return null
  return <div className="space-y-2"><Agregado a={p.agregado} rotulo={`UF ${p.uf}`} /><p className="text-xs text-gray-500">País: média {num(p.brasil.media_ponderada_usuarios)}, mediana {num(p.brasil.mediana)}.</p><RodapeMetodo m={p} /></div>
}

export function ProntidaoOperadoraBloco({ dados }: BlocoProps<OperadoraCtx>) {
  const p = dados.prontidao
  if (!p) return null
  return <div className="space-y-2"><Agregado a={p.agregado} rotulo={`ASNs da operadora (CNPJ ${p.raiz})`} /><p className="text-xs text-gray-500">País: média {num(p.brasil.media_ponderada_usuarios)}, mediana {num(p.brasil.mediana)}.</p><RodapeMetodo m={p} /></div>
}
