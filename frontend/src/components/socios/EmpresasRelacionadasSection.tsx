import { Link } from '../layout/LinkDatado'
import { useQuery } from '@tanstack/react-query'
import { fetchEmpresasRelacionadas } from '../../services/api'
import { useActiveDate } from '../../hooks/useSnapshot'
import { OutorgaBadges } from '../OutorgaBadge'
import type { EmpresaRelacionada, TipoRelacaoSocietaria } from '../../types/api'

function fmtCnpj(c: string): string {
  const d = (c ?? '').replace(/\D/g, '')
  if (d.length !== 14) return c
  return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8,12)}-${d.slice(12)}`
}

const TIPO_LABEL: Record<TipoRelacaoSocietaria, string> = {
  quadro_identico: 'Mesmo quadro societário',
  controle_exclusivo_exercido: 'Controla exclusivamente',
  controle_exclusivo_recebido: 'Controlada exclusivamente por',
  socios_em_comum: 'Sócio em comum',
  controle_parcial_exercido: 'Um dos sócios de',
  controle_parcial_recebido: 'Tem como um dos sócios',
}

/**
 * Cruzamento de quadro societário (Receita Federal): sócios em comum e
 * propriedade cruzada entre operadoras. Usa `enrich.socios_grupos` via
 * GET /grupos/empresa/{cnpj} — relações sempre DIRETAS, nunca por
 * transitividade (ver caveats na collection `socios`/api/query.py).
 */
export function EmpresasRelacionadasSection({
  cnpj,
  title = 'Empresas relacionadas',
  compact = false,
}: {
  cnpj: string | undefined
  title?: string
  compact?: boolean
}) {
  const date = useActiveDate()
  const query = useQuery({
    queryKey: ['empresas-relacionadas', cnpj, date],
    queryFn: () => fetchEmpresasRelacionadas(cnpj!, date ?? undefined),
    enabled: !!cnpj,
    retry: false,
  })

  const mesmoGrupo = query.data?.mesmo_grupo ?? []
  const parcial = query.data?.relacionadas_parcial ?? []
  if (!query.isLoading && mesmoGrupo.length === 0 && parcial.length === 0) return null

  if (compact) {
    const todas = [...mesmoGrupo, ...parcial]
    if (todas.length === 0) return null
    return (
      <div className="text-xs text-gray-500">
        {title}:{' '}
        {todas.map((r, i) => (
          <span key={r.cnpj}>
            {i > 0 && ', '}
            <Link to={`/operadora/${r.cnpj}`} className="text-primario-600 underline underline-offset-2"
                  title={`${TIPO_LABEL[r.tipo_relacao]} — ${fmtCnpj(r.cnpj)}`}>
              {r.empresa || fmtCnpj(r.cnpj)}
            </Link>{' '}
            <OutorgaBadges flags={r} />
            {r.asns.length > 0 && (
              <>
                {' ('}
                {r.asns.map((asn, j) => (
                  <span key={asn}>
                    {j > 0 && ', '}
                    <Link to={`/asn/${asn}`} className="text-primario-600 underline underline-offset-2">AS{asn}</Link>
                  </span>
                ))}
                {')'}
              </>
            )}
          </span>
        ))}
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h2 className="text-base font-semibold text-gray-800 mb-1">{title}</h2>
      <p className="text-xs text-gray-400 mb-3">
        Cruzamento de quadro societário (dados abertos de CNPJ da Receita Federal).
        Sem percentual de participação — a Receita não divulga isso publicamente.
      </p>

      {mesmoGrupo.length > 0 && (
        <div className="mb-3">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
            Coincidência total ou controle exclusivo
          </h3>
          <ul className="space-y-1">
            {mesmoGrupo.map(r => <RelacaoItem key={r.cnpj} r={r} />)}
          </ul>
        </div>
      )}

      {parcial.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
            Correspondência parcial
          </h3>
          <ul className="space-y-1">
            {parcial.map(r => <RelacaoItem key={r.cnpj} r={r} />)}
          </ul>
        </div>
      )}
    </div>
  )
}

function RelacaoItem({ r }: { r: EmpresaRelacionada }) {
  return (
    <li className="flex items-center gap-2 text-sm flex-wrap">
      <Link to={`/operadora/${r.cnpj}`} className="text-primario-600 underline underline-offset-2 font-medium">
        {r.empresa || fmtCnpj(r.cnpj)}
      </Link>
      <span className="text-xs text-gray-400 font-mono">{fmtCnpj(r.cnpj)}</span>
      <OutorgaBadges flags={r} />
      {r.asns.length > 0 && (
        <span className="text-xs text-gray-500">
          {r.asns.map((asn, i) => (
            <span key={asn}>
              {i > 0 && ', '}
              <Link to={`/asn/${asn}`} className="text-primario-600 underline underline-offset-2">AS{asn}</Link>
            </span>
          ))}
        </span>
      )}
      <span className="text-xs bg-gray-100 text-gray-600 rounded px-1.5 py-0.5">
        {TIPO_LABEL[r.tipo_relacao]}
      </span>
      {typeof r.socios_em_comum === 'number' && r.tipo_relacao === 'socios_em_comum' && (
        <span className="text-xs text-gray-400" title={r.nomes_em_comum?.join(', ')}>
          {r.socios_em_comum} sócio{r.socios_em_comum !== 1 ? 's' : ''} em comum
        </span>
      )}
      {typeof r.total_socios_da_controlada === 'number' && (
        <span className="text-xs text-gray-400">
          ({r.total_socios_da_controlada} sócios no total)
        </span>
      )}
    </li>
  )
}
