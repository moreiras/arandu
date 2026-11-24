// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import { IX_TAG_CLASS, SCM_SELO, SICI_COLOR, V4_STRONG, V6_STRONG, asnsDoRaio, fmtBR } from './tipos'
import type { Entity, TagIx } from './tipos'

/** Painel direito: resumo do raio, participação em IXes e a lista de entidades (ASes e SCMs deduplicados por CNPJ). */
export function PainelEntidades({ className, entities, entityCounts, markerPos, stats, filteredAsnsCount, nearestIx, ixLabel, ixCounts,
  copied, onCopy, onCsv, temPresenca, tagsDoAs }: {
  className: string
  entities: Entity[]
  entityCounts: { asns: number; cnpjsComAsn: number; scms: number }
  markerPos: [number, number] | null
  stats: { sedesAsn: number; asnsComPrefixo: number; sedesScm: number; scmsComUsuarios: number }
  filteredAsnsCount: number
  nearestIx: string | null
  ixLabel: (code: string) => string
  ixCounts: { nearMember: number; nearOrigin: number; anyMember: number; otherNotNear: number }
  copied: boolean
  onCopy: () => void
  onCsv: () => void
  /** há índice de presença em IXes carregado (sem ele as tags não aparecem) */
  temPresenca: boolean
  tagsDoAs: (asn: number) => TagIx[]
}) {
  return (
    <div className={className}>
      <div className="px-3 py-2 border-b border-gray-100 flex-shrink-0 space-y-1.5">
        <div className="flex items-start justify-between">
          <span className="text-sm font-semibold text-gray-700">
            {entities.length > 0 ? `${entities.length} entidade${entities.length !== 1 ? 's' : ''} (CNPJ ou AS sem CNPJ)` : 'Entidades'}
            {entities.length > 0 && (
              <span className="block text-xs font-normal text-gray-500">
                {entityCounts.asns} ASN{entityCounts.asns !== 1 ? 's' : ''} no raio, em {entityCounts.cnpjsComAsn} entidade{entityCounts.cnpjsComAsn !== 1 ? 's' : ''}; {entityCounts.scms} com SCM
              </span>
            )}
          </span>
          {entities.length > 0 && (
            <div className="flex items-center gap-2">
              <button
                onClick={onCopy}
                className="text-xs text-primario-600 hover:text-primario-800 transition-colors"
              >
                {copied ? 'Copiado!' : 'Copiar'}
              </button>
              <button
                onClick={onCsv}
                className="text-xs text-primario-600 hover:text-primario-800 transition-colors"
                title="Baixar CSV com participação em IXes"
              >
                CSV
              </button>
            </div>
          )}
        </div>
        {markerPos && (stats.sedesAsn > 0 || stats.asnsComPrefixo > 0 || stats.sedesScm > 0 || stats.scmsComUsuarios > 0) && (
          <div className="text-xs text-gray-500 leading-tight space-y-0.5">
            {stats.sedesAsn > 0 && (
              <p>{stats.sedesAsn} sede{stats.sedesAsn !== 1 ? 's' : ''} de Sistema{stats.sedesAsn !== 1 ? 's' : ''} Autônomo{stats.sedesAsn !== 1 ? 's' : ''}</p>
            )}
            {stats.asnsComPrefixo > 0 && (
              <p>{stats.asnsComPrefixo} Sistema{stats.asnsComPrefixo !== 1 ? 's' : ''} Autônomo{stats.asnsComPrefixo !== 1 ? 's' : ''} com prefixos</p>
            )}
            {stats.sedesScm > 0 && (
              <p>{stats.sedesScm} sede{stats.sedesScm !== 1 ? 's' : ''} de SCM{stats.sedesScm !== 1 ? 's' : ''}</p>
            )}
            {stats.scmsComUsuarios > 0 && (
              <p>{stats.scmsComUsuarios} SCM{stats.scmsComUsuarios !== 1 ? 's' : ''} com usuários</p>
            )}
          </div>
        )}
        {filteredAsnsCount > 0 && nearestIx && (
          <div className="text-xs text-gray-500 leading-snug space-y-0.5 pt-0.5 border-t border-gray-100">
            <div>
              <span className="font-semibold text-gray-700">{ixCounts.nearMember}</span> participam de{' '}
              <span className="font-medium">{ixLabel(nearestIx)}</span>
            </div>
            <div>
              <span className="font-semibold text-gray-700">{ixCounts.nearOrigin}</span> têm prefixos vistos nos route servers de{' '}
              {ixLabel(nearestIx)} (anunciados pelo próprio AS ou por terceiros)
            </div>
            <div>
              <span className="font-semibold text-gray-700">{ixCounts.anyMember}</span> participam de algum IX do IX.br
            </div>
            <div>
              <span className="font-semibold text-gray-700">{ixCounts.otherNotNear}</span> participam de outro IX, mas não de{' '}
              {ixLabel(nearestIx)}
            </div>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {entities.length === 0 ? (
          <p className="text-xs text-gray-400 p-3 leading-relaxed">
            {markerPos
              ? 'Nenhuma entidade encontrada neste raio.'
              : 'Clique no mapa ou busque por nome de município para definir um ponto de referência.'}
          </p>
        ) : (
          <ul className="divide-y divide-gray-50">
            {entities.map(e => {
              const hasAsn = e.asns.length > 0
              // ASNs do mesmo CNPJ fora do raio ficam recolhidos e fora das etiquetas (LOC-E3)
              const doRaio = asnsDoRaio(e)
              const fora = e.asnsNoRaio.length ? e.asns.length - e.asnsNoRaio.length : 0
              // CNPJ → página da operadora (todos os ASNs dele); AS sem CNPJ → página do ASN.
              const to = e.cnpj ? `/operadora/${e.cnpj}` : `/asn/${e.asns[0]}`
              const tags = hasAsn && temPresenca
                ? [...new Map(doRaio.flatMap(a => tagsDoAs(a)).map(t => [`${t.kind}|${t.code}|${t.label}`, t])).values()]
                    .filter((t, _, arr) => t.kind !== 'none' || arr.every(x => x.kind === 'none'))
                : []
              return (
                <li key={e.key}>
                  <Link
                    to={to}
                    className="flex flex-col px-3 py-2 hover:bg-primario-50 transition-colors group"
                  >
                    <div className="flex items-start gap-1.5">
                      {hasAsn ? (
                        <span className="font-mono text-xs font-semibold text-primario-700 group-hover:text-primario-900 break-all">
                          {doRaio.map(a => `AS${a}`).join(', ')}
                          {fora > 0 && <span className="block font-sans font-normal text-gray-500">mais {fora} ASN{fora !== 1 ? 's' : ''} do mesmo CNPJ fora do raio</span>}
                        </span>
                      ) : (
                        <span className="font-mono text-xs text-v6-600 leading-tight pt-0.5">{e.cnpj}</span>
                      )}
                      {hasAsn && !e.fromHq && (e.v4 || e.v6) && (
                        <span className="text-xs text-gray-600" title="Sem sede no raio — presente via prefixo">
                          <span aria-hidden="true">⬡</span><span className="sr-only">Sem sede no raio, presente via prefixo</span>
                        </span>
                      )}
                      <span className="ml-auto flex items-center gap-1 flex-shrink-0">
                        {hasAsn && (
                          <span className="text-xs px-1.5 rounded-full text-white bg-primario-600" title="Possui ASN">ASN</span>
                        )}
                        {e.scm && (
                          <span className="text-xs px-1.5 rounded-full text-white" style={{ background: SCM_SELO }} title="Possui outorga SCM">SCM</span>
                        )}
                        {e.v6 && (
                          <span className="text-xs font-mono px-1 rounded text-white" style={{ background: V6_STRONG }} title="Prefixos IPv6 na região">v6</span>
                        )}
                        {e.v4 && (
                          <span className="text-xs font-mono px-1 rounded text-white" style={{ background: V4_STRONG }} title="Prefixos IPv4 na região">v4</span>
                        )}
                      </span>
                    </div>
                    {e.name && <span className="text-xs text-gray-600 truncate leading-tight">{e.name}</span>}
                    {hasAsn && e.cnpj && <span className="text-xs text-gray-600 font-mono leading-tight">{e.cnpj}</span>}
                    {(e.city || e.uf) && (
                      <span className="text-xs text-gray-600 leading-tight">{[e.city, e.uf].filter(Boolean).join(', ')}</span>
                    )}
                    {e.sici && (
                      <span className="text-xs leading-tight" style={{ color: SICI_COLOR }}>
                        {fmtBR(e.sici.acessos)} acessos · {e.sici.municipios} município{e.sici.municipios !== 1 ? 's' : ''} no raio
                      </span>
                    )}
                    {tags.length > 0 && (
                      <span className="flex flex-wrap gap-1 mt-1">
                        {tags.map((t, i) => (
                          <span key={`${t.kind}-${t.code}-${i}`} className={IX_TAG_CLASS[t.kind]}>{t.label}</span>
                        ))}
                      </span>
                    )}
                  </Link>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
