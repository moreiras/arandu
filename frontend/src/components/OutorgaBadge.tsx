import { Link } from 'react-router-dom'

/** Badge de outorga Anatel (SCM/SMP/STFC/SeAC) — usado em qualquer lista/detalhe
 *  que precise sinalizar quais outorgas um CNPJ possui. */
export function OutorgaBadge({ label }: { label: string }) {
  return (
    <span className="text-xs font-semibold bg-v6-100 text-v6-700 rounded px-1.5 py-0.5">{label}</span>
  )
}

/** Badge "ASN" — o CNPJ tem ao menos um sistema autônomo associado. O título
 *  lista os números; com um único ASN, o badge leva à página do AS. */
export function AsnBadge({ asns }: { asns?: number[] | null }) {
  if (!asns || asns.length === 0) return null
  const cls = 'text-xs font-semibold bg-mercado-100 text-mercado-700 rounded px-1.5 py-0.5'
  const title = asns.map(a => `AS${a}`).join(', ')
  if (asns.length === 1) {
    return (
      <Link to={`/asn/${asns[0]}`} title={title} onClick={e => e.stopPropagation()} className={`${cls} hover:bg-mercado-200`}>
        ASN
      </Link>
    )
  }
  return <span title={title} className={cls}>ASN ×{asns.length}</span>
}

export interface OutorgaFlags {
  has_scm?: boolean | null
  has_smp?: boolean | null
  has_stfc?: boolean | null
  has_seac?: boolean | null
}

/** Renderiza um badge para cada outorga presente em `flags`. Nada é renderizado
 *  se nenhuma flag for true (evita <div> vazio poluindo o layout). */
export function OutorgaBadges({ flags }: { flags: OutorgaFlags }) {
  if (!flags.has_scm && !flags.has_smp && !flags.has_stfc && !flags.has_seac) return null
  return (
    <span className="inline-flex items-center gap-1">
      {flags.has_scm && <OutorgaBadge label="SCM" />}
      {flags.has_smp && <OutorgaBadge label="SMP" />}
      {flags.has_stfc && <OutorgaBadge label="STFC" />}
      {flags.has_seac && <OutorgaBadge label="SeAC" />}
    </span>
  )
}
