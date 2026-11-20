// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useAcoesPerfil, usePerfil } from '../features/perfil/api'
import { SITE } from '../lib/site'

const dataBr = (d: string) => d.split('-').reverse().join('/')

/** Comandos de uso por cliente MCP (a chave aparece só aqui, uma vez, no navegador de quem a pediu). */
function Instrucoes({ chave }: { chave: string }) {
  const url = `${window.location.origin}/mcp`
  const linhas = [
    ['Claude Code', `claude mcp add --transport http ${SITE.mcp} ${url} --header "Authorization: Bearer ${chave}"`],
    ['Outros clientes MCP (Streamable HTTP)', `URL: ${url}\nCabeçalho: Authorization: Bearer ${chave}`],
  ]
  return (
    <div className="space-y-2">
      {linhas.map(([nome, cmd]) => (
        <div key={nome}>
          <h4 className="text-xs font-medium text-gray-600">{nome}</h4>
          <pre className="mt-1 whitespace-pre-wrap break-all rounded bg-gray-50 border border-gray-200 p-2 text-xs">{cmd}</pre>
        </div>
      ))}
    </div>
  )
}

function ChaveMcp({ perfil }: { perfil: NonNullable<ReturnType<typeof usePerfil>['data']> }) {
  const { gerarChave, revogarChave } = useAcoesPerfil()
  const [rotulo, setRotulo] = useState('')
  const [copiada, setCopiada] = useState(false)
  const nova = gerarChave.data?.chave
  const k = perfil.chave_mcp
  if (!k.disponivel) return <p className="text-sm text-gray-600">A chave de MCP ainda não está disponível. Quando for liberada, você a gera aqui, sem custo.</p>
  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-600">Com a chave, o seu cliente MCP (Claude e outros) acessa o {SITE.nome} com o seu login gratuito. A chave é pessoal: guardamos só um código de verificação dela e ela aparece <strong>uma única vez</strong>.</p>
      {nova && (
        <div role="alert" className="rounded border border-aviso-300 bg-aviso-50 p-3 space-y-2" data-testid="chave-nova">
          <p className="text-sm font-medium text-aviso-800">Guarde a chave agora: ela não será mostrada de novo.</p>
          <code className="block break-all rounded bg-white border border-gray-200 p-2 text-xs select-all">{nova}</code>
          <button type="button" className="rounded border border-gray-300 bg-white px-2 py-1 text-xs hover:bg-gray-50" onClick={() => navigator.clipboard?.writeText(nova).then(() => setCopiada(true))}>{copiada ? 'Copiada' : 'Copiar'}</button>
          <Instrucoes chave={nova} />
        </div>
      )}
      {k.ativa && !nova && (
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="text-gray-500">Chave ativa</dt><dd className="font-mono text-xs">{SITE.mcp.toLowerCase()}_mcp_{k.ativa.id}_…</dd>
          {k.ativa.rotulo && <><dt className="text-gray-500">Rótulo</dt><dd>{k.ativa.rotulo}</dd></>}
          <dt className="text-gray-500">Criada em</dt><dd>{dataBr(k.ativa.criada_em.slice(0, 10))}</dd>
          <dt className="text-gray-500">Último uso</dt><dd>{k.ativa.ultimo_uso_dia ? dataBr(k.ativa.ultimo_uso_dia) : 'ainda não usada'}</dd>
        </dl>
      )}
      {!k.ativa && <p className="text-sm text-gray-600">Você ainda não tem uma chave ativa.</p>}
      <div className="flex flex-wrap items-end gap-2">
        <label className="flex flex-col text-xs text-gray-500">Rótulo (opcional)
          <input value={rotulo} maxLength={40} onChange={(e) => setRotulo(e.target.value)} placeholder="ex.: meu notebook" className="mt-0.5 rounded border border-gray-300 px-2 py-1 text-sm" />
        </label>
        <button type="button" disabled={gerarChave.isPending} onClick={() => { setCopiada(false); gerarChave.mutate(rotulo) }}
          className="rounded-md bg-primario-600 px-3 py-1.5 text-sm text-white hover:bg-primario-700 disabled:opacity-50">{k.ativa ? 'Gerar nova chave (revoga a atual)' : 'Gerar chave'}</button>
        {k.ativa && <button type="button" disabled={revogarChave.isPending} onClick={() => { if (window.confirm('Revogar a chave? Os clientes que a usam deixam de funcionar na hora.')) revogarChave.mutate(undefined, { onSuccess: () => gerarChave.reset() }) }}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50">Revogar</button>}
      </div>
      {gerarChave.isError && <p className="text-sm text-perigo-600" role="status">Não foi possível gerar a chave agora.</p>}
    </div>
  )
}

/** `/perfil` — dados mínimos da conta, uso, chave de MCP, "sair de todos os dispositivos" e pedido de exclusão (30 dias). */
export function Perfil() {
  const { user, loading } = useAuth()
  const q = usePerfil(!loading && !!user)
  const { sairDeTodos, excluir } = useAcoesPerfil()
  if (loading) return <p className="text-sm text-gray-400" role="status">Carregando…</p>
  if (!user || q.isError) return (
    <div className="max-w-xl space-y-2">
      <h1 className="text-titulo-1 text-gray-900">Perfil</h1>
      <p className="text-sm text-gray-600">{user ? 'O perfil só existe para contas com login (não para acessos por rede autorizada).' : 'Entre com a sua conta para ver o perfil.'} {!user && <Link to="/login?next=/perfil" className="text-primario-600 underline">Entrar</Link>}</p>
    </div>
  )
  const p = q.data
  if (!p) return <p className="text-sm text-gray-400" role="status">Carregando…</p>
  const total = p.uso.reduce((s, d) => s + d.chamadas, 0)
  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Perfil</h1>
        <p className="text-sm text-gray-500 mt-1">Sua conta é gratuita. Veja a <Link to="/privacidade" className="text-primario-600 hover:underline">Política de Privacidade</Link> e a <Link to="/uso-aceitavel" className="text-primario-600 hover:underline">Política de Uso Aceitável</Link>.</p>
      </div>
      <section className="rounded-lg border border-gray-200 bg-white p-4 space-y-2">
        <h2 className="text-base font-semibold text-gray-800">Conta</h2>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="text-gray-500">E-mail</dt><dd className="break-all">{p.email}</dd>
          {p.nome && <><dt className="text-gray-500">Nome</dt><dd>{p.nome}</dd></>}
          <dt className="text-gray-500">Entrou com</dt><dd>{p.provedor}</dd>
          <dt className="text-gray-500">Conta criada em</dt><dd>{dataBr(p.criada_em)}</dd>
          <dt className="text-gray-500">Último acesso</dt><dd>{dataBr(p.ultimo_acesso)}</dd>
        </dl>
      </section>
      <section className="rounded-lg border border-gray-200 bg-white p-4 space-y-2" aria-labelledby="chave-titulo">
        <h2 id="chave-titulo" className="text-base font-semibold text-gray-800">Chave de MCP</h2>
        <ChaveMcp perfil={p} />
      </section>
      <section className="rounded-lg border border-gray-200 bg-white p-4 space-y-2">
        <h2 className="text-base font-semibold text-gray-800">Seu uso nos últimos 30 dias</h2>
        <p className="text-sm text-gray-600">{total.toLocaleString('pt-BR')} chamadas ao site, à API e ao MCP com a sua conta. O registro serve ao controle de acesso e à prevenção de abuso (Política de Privacidade, seção 2.3).</p>
        {p.uso.length > 0 && (
          <details className="text-sm"><summary className="cursor-pointer text-primario-600 hover:underline">Ver por dia</summary>
            <table className="mt-2 text-xs"><thead><tr><th className="text-left pr-6">Dia</th><th className="text-right">Chamadas</th></tr></thead>
              <tbody>{p.uso.map((d) => <tr key={d.dia}><td className="pr-6">{dataBr(d.dia)}</td><td className="text-right tabular-nums">{d.chamadas.toLocaleString('pt-BR')}</td></tr>)}</tbody></table>
          </details>
        )}
      </section>
      <section className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
        <h2 className="text-base font-semibold text-gray-800">Segurança da conta</h2>
        <div className="space-y-1">
          <button type="button" disabled={sairDeTodos.isPending} onClick={() => sairDeTodos.mutate(undefined, { onSuccess: () => { window.location.href = '/login' } })}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50">Sair de todos os dispositivos</button>
          <p className="text-xs text-gray-500">Encerra todas as sessões abertas desta conta, inclusive esta.</p>
        </div>
        <div className="space-y-1">
          {excluir.data ? (
            <p className="text-sm text-aviso-800 bg-aviso-50 border border-aviso-200 rounded px-3 py-2" role="status">Pedido registrado. A conta foi desativada e os dados serão apagados em {dataBr(excluir.data.exclusao_efetiva_em)} ({excluir.data.prazo_dias} dias). Para cancelar, use antes dessa data o contato indicado na <a href="/privacidade" className="underline">Política de Privacidade</a>.</p>
          ) : (
            <button type="button" disabled={excluir.isPending} onClick={() => { if (window.confirm('Solicitar a exclusão da conta? Ela é desativada agora (sem login e sem chave) e os dados são apagados em 30 dias.')) excluir.mutate() }}
              className="rounded-md border border-perigo-300 px-3 py-1.5 text-sm text-perigo-700 hover:bg-perigo-50">Solicitar exclusão da conta</button>
          )}
          <p className="text-xs text-gray-500">A exclusão não é imediata: a conta fica desativada e os dados são apagados em até 30 dias do pedido.</p>
        </div>
      </section>
    </div>
  )
}
