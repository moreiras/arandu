// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../components/layout/LinkDatado'
import { ComoLer } from '../../components/ui/ComoLer'
import { LinhaProveniencia } from '../../components/ui/Kpi'
import { fmtKm } from '../../lib/geo'
import { UNIVERSOS } from '../../lib/universos'
import type { LinhaPtt, PresencaPtt } from './calculos'

const n = (v: number) => v.toLocaleString('pt-BR')
const MAX_LINHAS = 10

/**
 * Interconexão no IX.br das redes do raio (PT-25, localizador 5.1). O PTT de referência é o de mais membros entre as redes do raio; o mais próximo em linha
 * reta aparece ao lado, porque os dois podem ser diferentes (o mais próximo pode estar a centenas de km e não ter nenhuma rede da região). Denominador sempre
 * explícito. Membro = cadastro oficial de participantes; prefixo visto = origem de rota nos route servers, que pode chegar por um participante que dá trânsito.
 * Fato descritivo e sem veredito: a distância é inferida (cidade do PTT, linha reta).
 */
export function BlocoInterconexao({ presenca, pttLabel, snapshot }: {
  presenca: PresencaPtt
  pttLabel: (code: string) => string
  snapshot: string | null
}) {
  const { total, referencia, maisProximo } = presenca
  if (total === 0) return null
  const rede = (v: number) => `${n(v)} de ${n(total)} ${total === 1 ? 'rede' : 'redes'}`
  const membro = (v: number) => (v === 1 ? 'é membro' : 'são membros')
  const linhas = presenca.linhas.filter(l => l.membros > 0 || l.soOriginados > 0 || l.code === maisProximo?.code).slice(0, MAX_LINHAS)
  const item = (l: LinhaPtt) => <><Link to={`/ixp/${l.code}`} className="text-primario-700 underline">{pttLabel(l.code)}</Link>, {fmtKm(l.km)} em linha reta</>
  return (
    <section className="rounded-lg border border-gray-200 bg-white p-4 space-y-3" aria-labelledby="area-interconexao" data-testid="localizador-interconexao">
      <h2 id="area-interconexao" className="text-titulo-3 text-gray-800">Interconexão no IX.br das redes do raio</h2>
      <LinhaProveniencia selo="inferido" fonte="cadastro de participantes do IX.br e looking glass dos PTTs; redes no raio pela localização da sede ou do prefixo; distância em linha reta até a cidade do PTT" dataRef={snapshot} />
      <dl className="space-y-1 text-sm">
        <div data-testid="ptt-referencia">
          <dt className="inline font-medium text-gray-700">PTT onde as redes do raio mais participam: </dt>
          <dd className="inline">
            {referencia
              ? <>{item(referencia)}; {rede(referencia.membros)} {membro(referencia.membros)}</>
              : <>nenhuma rede do raio consta como participante de PTT do IX.br</>}
          </dd>
        </div>
        {maisProximo && (
          <div data-testid="ptt-mais-proximo">
            <dt className="inline font-medium text-gray-700">PTT mais próximo em linha reta: </dt>
            <dd className="inline">{item(maisProximo)}; {rede(maisProximo.membros)} {membro(maisProximo.membros)}</dd>
          </div>
        )}
        <div><dt className="inline font-medium text-gray-700">Participantes de algum PTT do IX.br: </dt><dd className="inline">{rede(presenca.algumMembro)}</dd></div>
        <div>
          <dt className="inline font-medium text-gray-700">Fora do cadastro de participantes, com prefixos vistos em route server (inferido; podem chegar por outro participante): </dt>
          <dd className="inline">{rede(presenca.semSessaoComPrefixos)}</dd>
        </div>
        <div><dt className="inline font-medium text-gray-700">Fora do cadastro e sem prefixos vistos: </dt><dd className="inline">{rede(presenca.semSessaoSemPrefixos)}</dd></div>
      </dl>
      {linhas.length > 0 && (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <caption className="sr-only">Redes do raio por PTT do IX.br: participantes do cadastro e redes só com prefixos vistos, com a distância em linha reta até a cidade do PTT</caption>
            <thead className="text-xs text-gray-600">
              <tr>
                <th scope="col" className="px-2 py-1 text-left">PTT</th>
                <th scope="col" className="px-2 py-1 text-right">Distância (km, linha reta)</th>
                <th scope="col" className="px-2 py-1 text-right">Membros daqui</th>
                <th scope="col" className="px-2 py-1 text-right">Só com prefixos vistos</th>
              </tr>
            </thead>
            <tbody>
              {linhas.map(l => (
                <tr key={l.code} className="border-t border-gray-100">
                  <th scope="row" className="px-2 py-1 text-left font-normal"><Link to={`/ixp/${l.code}`} className="text-primario-700 underline">{pttLabel(l.code)}</Link></th>
                  <td className="px-2 py-1 text-right tabular-nums">{Math.round(l.km).toLocaleString('pt-BR')}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{n(l.membros)}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{n(l.soOriginados)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <ComoLer>
        <p>Denominador: as {n(total)} {total === 1 ? 'rede' : 'redes'} (ASNs distintos) da lista do raio, com sede nele ou só com prefixos nele. Membro: ASN no cadastro oficial de participantes do PTT ({UNIVERSOS.membroCadastro.rotulo}), com ou sem sessão com o route server.</p>
        <p>Prefixo visto: o route server do PTT recebe rota com origem nesse ASN, o que pode ocorrer por um participante que lhe dá trânsito; o ASN não precisa estar no PTT. A contagem é por ASN, não por prefixo.</p>
        <p>Distância em linha reta do ponto escolhido até a cidade do PTT (coordenada aproximada, selo inferido); a distância de fibra é maior. A tabela lista até {MAX_LINHAS} PTTs, em ordem de membros e, no empate, de distância. O PTT de referência descreve onde as redes do raio participam; não é recomendação de onde interligar.</p>
      </ComoLer>
    </section>
  )
}
