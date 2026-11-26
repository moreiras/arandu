import { useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { AccessError } from '../services/api'
import type { ASNContact, ASNContactsResponse } from '../types/api'

function fmtPhone(phone: string | null | undefined): string | null {
  if (!phone) return null
  const digits = phone.replace(/\D/g, '')
  let local = digits
  if (local.startsWith('55') && local.length >= 12) local = local.slice(2)
  if (local.length === 11) return `+55 (${local.slice(0,2)}) ${local.slice(2,7)} ${local.slice(7)}`
  if (local.length === 10) return `+55 (${local.slice(0,2)}) ${local.slice(2,6)} ${local.slice(6)}`
  return phone
}

// Traduz a função (role) do contato — PeeringDB usa termos em inglês.
const _ROLE_PT: Record<string, string> = {
  abuse: 'abuse', technical: 'técnico', policy: 'roteamento/política',
  noc: 'NOC', sales: 'comercial', maintenance: 'manutenção',
  implementation: 'implementação', 'public relations': 'relações públicas',
  legal: 'jurídico', cadastral: 'cadastral', outorga: 'outorga',
}
function contactRole(role: string): string {
  return _ROLE_PT[role.trim().toLowerCase()] || role
}

export interface ContactsAvailable {
  peeringdb: number
  anatel: number
  receita: boolean
  total: number
  rdap?: number
}

/** Nota de proveniência do RDAP: data da leitura deste ASN e cobertura do rodízio. Vazia sem leitura. */
export function notaRdap(rdap: ASNContactsResponse['rdap']): string | null {
  if (!rdap) return null
  const c = rdap.cobertura
  const cob = c ? `${c.com_leitura_valida.toLocaleString('pt-BR')} de ${c.asns_no_universo.toLocaleString('pt-BR')} ASNs com contato lido` +
    (c.leitura_mais_antiga ? `; leitura mais antiga em ${c.leitura_mais_antiga}` : '') : null
  const este = rdap.leitura_em ? `RDAP (Registro.br): lido em ${rdap.leitura_em}` : rdap.tentou_em ? `RDAP (Registro.br): sem leitura completa (tentado em ${rdap.tentou_em})` : null
  return [este, cob].filter(Boolean).join(' · ') || null
}

/**
 * Bloco "revelar contatos" — login obrigatório + revelar ao clicar. Compartilhado
 * entre a página do AS e a da operadora: o documento público traz só a contagem
 * (`available`); os valores vêm de um endpoint protegido por login, passado via
 * `fetchContacts`, nunca em lote.
 */
export function ContactsReveal({
  available,
  fetchContacts,
}: {
  available?: ContactsAvailable
  fetchContacts: () => Promise<{ contacts: ASNContact[]; rdap?: ASNContactsResponse['rdap']; cota?: ASNContactsResponse['cota'] }>
}) {
  const { user } = useAuth()
  const [contacts, setContacts] = useState<ASNContact[] | null>(null)
  const [rdap, setRdap] = useState<ASNContactsResponse['rdap']>(undefined)
  const [restante, setRestante] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const total = available?.total ?? 0
  if (total === 0) return null

  if (!user) {
    return (
      <div className="text-xs text-gray-400 pt-0.5">
        🔒 {total} {total > 1 ? 'contatos disponíveis' : 'contato disponível'}.{' '}
        <a href="/login" className="text-primario-600 hover:underline">Entre para ver</a>
      </div>
    )
  }

  if (contacts === null) {
    return (
      <div className="pt-0.5">
        <button
          onClick={async () => {
            setLoading(true); setError(null)
            try { const r = await fetchContacts(); setContacts(r.contacts); setRdap(r.rdap); setRestante(r.cota?.restante_hoje ?? null) }
            catch (e) { setError(e instanceof AccessError && e.kind === 'taxa' ? e.message : 'falha ao carregar') }
            finally { setLoading(false) }
          }}
          disabled={loading}
          className="text-xs text-primario-600 hover:text-primario-800 border border-primario-200 hover:border-primario-400 rounded px-2 py-0.5 transition-colors disabled:opacity-50"
        >
          {loading ? 'Carregando…' : `Revelar contatos (${total})`}
        </button>
        {error && <span role="alert" className="text-xs text-perigo-500 ml-2">{error}</span>}
      </div>
    )
  }

  return (
    <div className="text-xs text-gray-500 leading-snug space-y-0.5 pt-0.5">
      {contacts.map((c, i) => (
        <div key={i} className="flex items-center gap-1.5 flex-wrap">
          <span className="inline-block bg-gray-100 text-gray-500 rounded px-1 py-0.5 text-xs">{c.source}</span>
          {c.role && <span className="text-gray-400">{contactRole(c.role)}</span>}
          {c.email && <a href={`mailto:${c.email}`} className="text-primario-600 hover:underline">{c.email}</a>}
          {c.phone && <span className="text-gray-500">{fmtPhone(c.phone) ?? c.phone}</span>}
          {c.name && <span className="text-gray-400 truncate max-w-[200px]">{c.name}</span>}
        </div>
      ))}
      {notaRdap(rdap) && <div className="text-xs text-gray-400 pt-0.5">{notaRdap(rdap)}</div>}
      {restante !== null && (
        <div className="text-xs text-gray-400">Consultas de contato restantes nas próximas 24 h: {restante.toLocaleString('pt-BR')}</div>
      )}
    </div>
  )
}
