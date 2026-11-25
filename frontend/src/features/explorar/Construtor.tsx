// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { CampoSchema, Condicao, EstadoConsulta, Operador, SchemaConsulta } from './consulta'
import { LIMITES, ROTULO_OP, chavesDeOrdemNaAgregacao, familia, operadoresDoCampo } from './consulta'

const CAMPO = 'border border-gray-300 rounded-md px-2 py-1 text-sm bg-white'

function EntradaValor({ campo, op, valor, onChange }: { campo?: CampoSchema; op: Operador; valor: string; onChange: (v: string) => void }) {
  if (op === 'exists') return (
    <select aria-label="Valor" className={CAMPO} value={valor || 'true'} onChange={(e) => onChange(e.target.value)}><option value="true">sim</option><option value="false">não</option></select>
  )
  if (campo && familia(campo.type) === 'bool') return (
    <select aria-label="Valor" className={CAMPO} value={valor || 'true'} onChange={(e) => onChange(e.target.value)}><option value="true">verdadeiro</option><option value="false">falso</option></select>
  )
  if (campo?.enum && op !== 'in' && op !== 'nin') return (
    <select aria-label="Valor" className={CAMPO} value={valor} onChange={(e) => onChange(e.target.value)}>
      <option value="">escolha…</option>{campo.enum.map((v) => <option key={String(v)} value={String(v)}>{String(v)}</option>)}
    </select>
  )
  return (
    <input aria-label="Valor" className={`${CAMPO} w-56`} value={valor} onChange={(e) => onChange(e.target.value)}
      placeholder={op === 'in' || op === 'nin' ? 'a, b, c' : campo?.example != null ? `ex.: ${String(campo.example)}` : ''} />
  )
}

/** Construtor visual da consulta: coleção, condições (campo · operador · valor), colunas, ordem, limite e, quando a coleção tem coordenadas, "perto de". */
export function Construtor({ schema, estado, onChange, onExecutar, executando }: {
  schema: SchemaConsulta
  estado: EstadoConsulta
  onChange: (e: EstadoConsulta) => void
  onExecutar: () => void
  executando: boolean
}) {
  const col = schema.collections[estado.colecao]
  const campos = col?.fields ?? []
  const achar = (n: string) => campos.find((f) => f.name === n)
  const set = (p: Partial<EstadoConsulta>) => onChange({ ...estado, ...p, pagina: p.pagina ?? 1 })
  const setCond = (i: number, c: Partial<Condicao>) => set({ condicoes: estado.condicoes.map((x, j) => {
    if (j !== i) return x
    const novo = { ...x, ...c }
    if (c.campo !== undefined && c.campo !== x.campo) { const ops = operadoresDoCampo(achar(c.campo)); novo.op = ops.includes(novo.op) ? novo.op : ops[0]; novo.valor = '' }
    return novo
  }) })
  const toggle = (lista: string[], n: string) => (lista.includes(n) ? lista.filter((x) => x !== n) : [...lista, n])

  return (
    <form className="space-y-4 bg-white rounded-lg border border-gray-200 p-4" onSubmit={(e) => { e.preventDefault(); onExecutar() }} aria-label="Construtor de consulta">
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm text-gray-600">Coleção{' '}
          <select className={CAMPO} value={estado.colecao} onChange={(e) => onChange({ ...estado, colecao: e.target.value, condicoes: [], colunas: [], ordem: null, agrupar: [], agregados: [{ fn: 'count', campo: '' }], perto: null, pagina: 1 })}>
            {Object.keys(schema.collections).map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <fieldset className="text-sm text-gray-600 flex gap-3"><legend className="sr-only">Modo</legend>
          <label><input type="radio" name="modo" checked={estado.modo === 'lista'} onChange={() => set({ modo: 'lista' })} /> Lista</label>
          <label><input type="radio" name="modo" checked={estado.modo === 'agregar'} onChange={() => set({ modo: 'agregar' })} /> Agrupar e calcular</label>
        </fieldset>
      </div>
      {col && <p className="text-xs text-gray-500">{col.description}</p>}

      <div className="space-y-2">
        <div className="flex items-center gap-2 text-sm text-gray-700">
          <strong>Condições</strong>
          {estado.condicoes.length > 1 && (
            <select aria-label="Juntar condições" className={CAMPO} value={estado.juncao} onChange={(e) => set({ juncao: e.target.value as 'and' | 'or' })}>
              <option value="and">todas valem (E)</option><option value="or">qualquer vale (OU)</option>
            </select>
          )}
          <button type="button" className="ml-auto text-primario-600 hover:underline" onClick={() => set({ condicoes: [...estado.condicoes, { campo: campos[0]?.name ?? '', op: operadoresDoCampo(campos[0])[0], valor: '' }] })}>+ condição</button>
        </div>
        {estado.condicoes.length === 0 && <p className="text-xs text-gray-400">Sem condições: todas as linhas da coleção.</p>}
        {estado.condicoes.map((c, i) => {
          const f = achar(c.campo)
          return (
            <div key={i} className="flex flex-wrap items-center gap-2" role="group" aria-label={`Condição ${i + 1}`}>
              <select aria-label="Campo" className={CAMPO} value={c.campo} onChange={(e) => setCond(i, { campo: e.target.value })}>
                {campos.map((x) => <option key={x.name} value={x.name}>{x.name}</option>)}
              </select>
              <select aria-label="Operador" className={CAMPO} value={c.op} onChange={(e) => setCond(i, { op: e.target.value as Operador })}>
                {operadoresDoCampo(f).map((o) => <option key={o} value={o}>{ROTULO_OP[o]}</option>)}
              </select>
              <EntradaValor campo={f} op={c.op} valor={c.valor} onChange={(v) => setCond(i, { valor: v })} />
              <button type="button" aria-label={`Remover condição ${i + 1}`} className="text-gray-400 hover:text-perigo-600" onClick={() => set({ condicoes: estado.condicoes.filter((_, j) => j !== i) })}>×</button>
              {f?.description && <span className="text-xs text-gray-400 max-w-md truncate" title={f.description}>{f.description}</span>}
            </div>
          )
        })}
      </div>

      {col?.geo && (
        <div className="flex flex-wrap items-center gap-2 text-sm text-gray-700">
          <strong>Perto de</strong>
          <input aria-label="Lugar" className={`${CAMPO} w-48`} placeholder="município (ex.: Vitória)" value={estado.perto?.lugar ?? ''}
            onChange={(e) => set({ perto: e.target.value ? { lugar: e.target.value, raio: estado.perto?.raio ?? 20 } : null })} />
          {estado.perto && <label>raio <input aria-label="Raio em km" type="number" min={1} max={500} className={`${CAMPO} w-20`} value={estado.perto.raio}
            onChange={(e) => set({ perto: { lugar: estado.perto!.lugar, raio: Number(e.target.value) || 20 } })} /> km</label>}
        </div>
      )}

      {estado.modo === 'lista' ? (
        <details className="text-sm">
          <summary className="cursor-pointer text-gray-700"><strong>Colunas</strong> <span className="text-gray-400">({estado.colunas.length ? estado.colunas.length : 'todas'})</span></summary>
          <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-1">
            {campos.map((f) => <label key={f.name} className="text-xs text-gray-600"><input type="checkbox" checked={estado.colunas.includes(f.name)} onChange={() => set({ colunas: toggle(estado.colunas, f.name) })} /> {f.name}</label>)}
          </div>
        </details>
      ) : (
        <div className="space-y-2 text-sm text-gray-700">
          <details open>
            <summary className="cursor-pointer"><strong>Agrupar por</strong> <span className="text-gray-400">({estado.agrupar.length || 'tudo junto'})</span></summary>
            <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-1">
              {campos.filter((f) => familia(f.type) !== 'objeto').map((f) => <label key={f.name} className="text-xs text-gray-600"><input type="checkbox" checked={estado.agrupar.includes(f.name)} onChange={() => set({ agrupar: toggle(estado.agrupar, f.name) })} /> {f.name}</label>)}
            </div>
          </details>
          <div className="space-y-1">
            <strong>Calcular</strong>
            {estado.agregados.map((a, i) => (
              <div key={i} className="flex items-center gap-2" role="group" aria-label={`Cálculo ${i + 1}`}>
                <select aria-label="Função" className={CAMPO} value={a.fn} onChange={(e) => set({ agregados: estado.agregados.map((x, j) => (j === i ? { ...x, fn: e.target.value } : x)) })}>
                  {schema.aggregate_functions.map((fn) => <option key={fn} value={fn}>{fn}</option>)}
                </select>
                <select aria-label="Campo do cálculo" className={CAMPO} value={a.campo} onChange={(e) => set({ agregados: estado.agregados.map((x, j) => (j === i ? { ...x, campo: e.target.value } : x)) })}>
                  <option value="">{a.fn === 'count' ? '(linhas)' : 'escolha o campo…'}</option>
                  {campos.filter((f) => familia(f.type) === 'numero' || a.fn === 'count' || a.fn === 'distinct').map((f) => <option key={f.name} value={f.name}>{f.name}</option>)}
                </select>
                {estado.agregados.length > 1 && <button type="button" aria-label={`Remover cálculo ${i + 1}`} className="text-gray-400 hover:text-perigo-600" onClick={() => set({ agregados: estado.agregados.filter((_, j) => j !== i) })}>×</button>}
              </div>
            ))}
            <button type="button" className="text-xs text-primario-600 hover:underline" onClick={() => set({ agregados: [...estado.agregados, { fn: 'sum', campo: '' }] })}>+ cálculo</button>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 text-sm text-gray-700">
        <label>Ordenar por{' '}
          <select aria-label="Ordenar por" className={CAMPO} value={estado.ordem?.campo ?? ''} onChange={(e) => set({ ordem: e.target.value ? { campo: e.target.value, dir: estado.ordem?.dir ?? 'desc' } : null })}>
            <option value="">(sem ordem)</option>
            {(estado.modo === 'agregar' ? chavesDeOrdemNaAgregacao(estado) : campos.map((f) => f.name)).map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
        {estado.ordem && (
          <select aria-label="Sentido" className={CAMPO} value={estado.ordem.dir} onChange={(e) => set({ ordem: { campo: estado.ordem!.campo, dir: e.target.value as 'asc' | 'desc' } })}>
            <option value="desc">maior primeiro</option><option value="asc">menor primeiro</option>
          </select>
        )}
        <label>Linhas{' '}
          <select aria-label="Linhas por página" className={CAMPO} value={estado.limite} onChange={(e) => set({ limite: Number(e.target.value) })}>{LIMITES.map((l) => <option key={l} value={l}>{l}</option>)}</select>
        </label>
        <button type="submit" disabled={executando} className="ml-auto bg-primario-600 text-white rounded-md px-4 py-1.5 text-sm font-medium hover:bg-primario-700 disabled:opacity-50">{executando ? 'Consultando…' : 'Executar'}</button>
      </div>
    </form>
  )
}
