// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'
import { AtribuicaoPeeringDb, LinkInstalacao, SeloCadastro, dataCurta, fmtMbps, localDe, n } from '../../instalacoes/comum'
import { SITE } from '../../../lib/site'
import { useOrdenacao } from '../../../lib/ordenacao'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'

const sim = (v: boolean | undefined) => (v == null ? '—' : v ? 'sim' : 'não')
/** URL de looking glass ou route server informada pela rede: só http(s) vira link; telnet e ssh aparecem como texto (o navegador não os abre). */
function UrlDeclarada({ url }: { url?: string }) {
  if (!url) return <span>—</span>
  return /^https?:\/\//i.test(url)
    ? <a href={url} target="_blank" rel="noreferrer nofollow" className="text-primario-600 hover:underline break-all">{url}</a>
    : <span className="font-mono break-all">{url}</span>
}

/**
 * Instalações do Brasil em que a rede declara estar, atributos de peering e portas nos PTTs externos, do PeeringDB.
 * Tudo autodeclarado; o selo de cadastro é inferência pelas datas de atualização e não diz nada sobre a operação da rede.
 */
export function InstalacoesAsnBloco({ dados }: BlocoProps<AsnCtx>) {
  const fac = dados.facilities
  const pe = dados.peering
  const { ordenados, props } = useOrdenacao(fac?.items, {
    nome: (f) => f.nome,
    local: (f) => localDe(f),
    ptts: (f) => f.ptts.length,
    redes: (f) => f.n_redes,
    desde: { valor: (f) => f.no_vinculo_desde, primeiro: 'asc' },
    cadastro: (f) => f.cadastro?.dias,
  })
  return (
    <div className="space-y-4 text-sm" data-testid="instalacoes-asn">
      {pe && (
        <div className="space-y-2" data-testid="peering-asn">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">Atributos de peering declarados</span>
            <SeloCadastro c={pe.cadastro} />
          </div>
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1 text-xs">
            <div><dt className="text-gray-500">Escopo</dt><dd>{pe.escopo ?? '—'}</dd></div>
            <div><dt className="text-gray-500">IPv6</dt><dd>{sim(pe.ipv6)}</dd></div>
            <div><dt className="text-gray-500">Multicast</dt><dd>{sim(pe.multicast)}</dd></div>
            <div><dt className="text-gray-500">Nunca via route server</dt><dd>{sim(pe.nunca_via_route_server)}</dd></div>
            <div className="sm:col-span-2"><dt className="text-gray-500">Looking glass</dt><dd><UrlDeclarada url={pe.looking_glass} /></dd></div>
            <div className="sm:col-span-2"><dt className="text-gray-500">Route server</dt><dd><UrlDeclarada url={pe.route_server} /></dd></div>
            <div><dt className="text-gray-500">Registro criado</dt><dd>{dataCurta(pe.criado)}</dd></div>
            <div><dt className="text-gray-500">Registro atualizado</dt><dd>{dataCurta(pe.atualizado)}</dd></div>
          </dl>
          <p className="text-xs text-gray-400">As URLs são as informadas pela rede; o {SITE.nome} não verifica que respondem.</p>
          {pe.portas_externas && pe.portas_externas.ptts.length > 0 && (
            <div data-testid="portas-asn">
              <p className="text-xs font-medium text-gray-600 mt-2">Portas em PTTs externos (velocidade declarada)</p>
              <ul className="text-xs text-gray-700 space-y-0.5">
                {pe.portas_externas.ptts.map((p) => (
                  <li key={p.ixp}>
                    <Link to={`/ixp-externo/${p.ixp}`} className="text-primario-600 hover:underline">{p.ixp}</Link>: {n(p.portas)} porta(s), {p.velocidades_mbps.map(fmtMbps).join(' + ')}
                    {p.portas > 1 ? ` (soma ${fmtMbps(p.capacidade_mbps)})` : ''}
                  </li>
                ))}
              </ul>
              <p className="text-xs text-gray-400">Capacidade declarada, não tráfego.</p>
            </div>
          )}
          <AtribuicaoPeeringDb meta={pe} />
        </div>
      )}
      {fac && (
        <div className="space-y-2" data-testid="facilities-asn">
          <p>
            <span className="font-medium">{n(fac.total)} instalação(ões) do Brasil</span> em que a rede declara estar
            {pe ? <span className="text-xs text-gray-500"> (o cadastro informa {n(pe.instalacoes_declaradas)}, no Brasil e no exterior)</span> : null}
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-100">
                  <ThOrdenavel {...props('nome')} className="py-1 pr-3 font-medium">Instalação</ThOrdenavel><ThOrdenavel {...props('local')} className="py-1 pr-3 font-medium">Local</ThOrdenavel><ThOrdenavel {...props('ptts')} className="py-1 pr-3 font-medium">PTTs</ThOrdenavel>
                  <ThOrdenavel {...props('redes')} alinhar="right" className="py-1 pr-3 font-medium text-right">Redes</ThOrdenavel><ThOrdenavel {...props('desde')} className="py-1 pr-3 font-medium">Vínculo desde</ThOrdenavel><ThOrdenavel {...props('cadastro')} className="py-1 font-medium">Cadastro</ThOrdenavel>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {ordenados.map((f) => (
                  <tr key={f.id}>
                    <td className="py-1 pr-3"><LinkInstalacao f={f} /></td>
                    <td className="py-1 pr-3 text-gray-600">{localDe(f)}</td>
                    <td className="py-1 pr-3 text-gray-600">{f.ptts.length ? f.ptts.join(', ') : '—'}</td>
                    <td className="py-1 pr-3 text-right tabular-nums">{n(f.n_redes)}</td>
                    <td className="py-1 pr-3 tabular-nums">{dataCurta(f.no_vinculo_desde)}</td>
                    <td className="py-1"><SeloCadastro c={f.cadastro} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-gray-500">{fac.nota}</p>
          <AtribuicaoPeeringDb meta={fac} />
        </div>
      )}
    </div>
  )
}
