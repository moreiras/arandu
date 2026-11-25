// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../../components/layout/LinkDatado'
import { fmtKm } from '../../../lib/geo'
import { ComoLer } from '../../../components/ui/ComoLer'
import type { BlocoProps } from '../../entidade/registry'
import { InfraFisicaRaio } from '../../territorio/InfraFisicaRaio'
import { PARTICIPACAO_MINIMA_PCT, pttsEfetivos } from '../pttEfetivo'
import { RAIO_PTT_PROXIMO_KM, type MunicipioCtx } from '../contexto'

const MAX_PTTS = 5
const RAIO_INFRA_KM = 50
const pct = (v: number) => `${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`

/**
 * PTTs mais próximos (linha reta do centróide do município), PTT efetivo (onde as operadoras com 5% ou mais do fixo local têm sessão direta, PT-25 / município 5.4) e
 * infraestrutura física a até 50 km, consultada só quando o leitor abre o bloco. A tabela de PTT efetivo e a frase de CNPJ sem ASN ficam em blocos de texto
 * separados, para a ausência de ASN não ser lida como falha de nenhum programa.
 */
export function InfraBloco({ dados, snapshot }: BlocoProps<MunicipioCtx>) {
  const maximo = Math.max(RAIO_PTT_PROXIMO_KM, ...dados.proximos.map((p) => p.km))
  const ef = dados.fixo && dados.regiao ? pttsEfetivos(dados.fixo.operadores, dados.regiao, dados.centroide) : null
  const nomePtt = (c: string) => dados.regiao?.ptts_nomes?.[c] ?? c.toUpperCase()
  return (
    <div className="space-y-4">
      {ef && (
        <section aria-labelledby="ptt-efetivo" data-testid="ptt-efetivo" className="space-y-2">
          <h3 id="ptt-efetivo" className="text-sm font-medium text-gray-700">Onde as operadoras locais têm sessão direta em PTT</h3>
          {ef.linhas.length === 0
            ? <p className="text-sm">Nenhuma das {ef.consideradas} {ef.consideradas === 1 ? 'operadora' : 'operadoras'} com 5% ou mais do fixo local tem sessão direta em PTT do IX.br{ef.listaCortada ? ' entre os provedores listados' : ''}.</p>
            : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <caption className="sr-only">PTTs do IX.br onde operadoras com 5% ou mais do fixo local têm sessão direta, com distância em linha reta e parcela do fixo</caption>
                  <thead className="text-xs text-gray-600"><tr><th scope="col" className="px-2 py-1 text-left">PTT</th><th scope="col" className="px-2 py-1 text-right">Distância (km, linha reta)</th><th scope="col" className="px-2 py-1 text-left">Operadoras com sessão direta</th><th scope="col" className="px-2 py-1 text-right">Fixo local</th></tr></thead>
                  <tbody>
                    {ef.linhas.slice(0, MAX_PTTS).map((l) => (
                      <tr key={l.codigo} className="border-t border-gray-100 align-top">
                        <th scope="row" className="px-2 py-1 text-left font-normal"><Link to={`/ixp/${l.codigo}`} className="text-primario-700 underline">{nomePtt(l.codigo)}</Link></th>
                        <td className="px-2 py-1 text-right tabular-nums">{l.km == null ? '—' : Math.round(l.km).toLocaleString('pt-BR')}</td>
                        <td className="px-2 py-1">{l.operadoras.map((o) => `${o.empresa || o.cnpj} (${pct(o.share)})`).join(', ')}</td>
                        <td className="px-2 py-1 text-right tabular-nums">{pct(l.parcelaFixo)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          {ef.linhas.length > MAX_PTTS && <p className="text-xs text-gray-600">e mais {ef.linhas.length - MAX_PTTS} PTTs.</p>}
          <p className="text-sm" data-testid="ptt-sem-asn">CNPJs sem ASN ligado: {pct(ef.semAsnPct)} do fixo local declarado. O OBINT não vê a rede deles.</p>
          <ComoLer>
            <p>Entram as operadoras (CNPJ) com {PARTICIPACAO_MINIMA_PCT}% ou mais dos acessos fixos declarados ao SICI no município, pelos ASNs ligados ao CNPJ; a sessão direta vem do cadastro de participantes de cada PTT (selo inferido: o vínculo CNPJ e ASN). Cada operadora conta uma vez em cada PTT, mesmo com vários ASNs.</p>
            <p>Distância em linha reta do centróide do município até a cidade do PTT, sem estimativa de latência. PTT efetivo é onde a operadora tem sessão; a escolha por onde o tráfego sai depende de contrato de trânsito e de transporte, que o OBINT não vê.</p>
          </ComoLer>
        </section>
      )}
      <div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
            <th className="px-2 py-1">PTT</th><th className="px-2 py-1 w-1/2">Distância (a marca é {RAIO_PTT_PROXIMO_KM} km)</th><th className="px-2 py-1 text-right"> </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {dados.proximos.map((p) => (
            <tr key={`${p.codigo}-${p.lonlat.join()}`}>
              <td className="px-2 py-1"><Link to={`/ixp/${p.codigo}`} className="text-primario-600 hover:underline">{p.nome}</Link></td>
              <td className="px-2 py-1">
                <div className="relative h-2 rounded bg-gray-100" aria-hidden>
                  <div className={`h-2 rounded ${p.km <= RAIO_PTT_PROXIMO_KM ? 'bg-primario-500' : 'bg-gray-400'}`} style={{ width: `${(100 * p.km) / maximo}%` }} />
                  <div className="absolute top-[-2px] h-3 w-px bg-gray-500" style={{ left: `${(100 * RAIO_PTT_PROXIMO_KM) / maximo}%` }} />
                </div>
              </td>
              <td className="px-2 py-1 text-right tabular-nums">{fmtKm(p.km)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-gray-500">
        Distância em linha reta até o centróide do município{dados.conjunto ? ' central (não do conjunto)' : ''} — não é o trajeto de fibra. Linhas de transmissão, cabos submarinos e rodovias estão no{' '}
        <Link to="/mapa" className="text-primario-600 hover:underline">mapa</Link>.
      </p>
      </div>
      {dados.centroide && (
        <InfraFisicaRaio lat={dados.centroide[1]} lon={dados.centroide[0]} raioKm={RAIO_INFRA_KM} date={snapshot ?? undefined} titulo="Infraestrutura de transporte a até 50 km do centróide" />
      )}
    </div>
  )
}
