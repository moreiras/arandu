// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { BlocoProps } from '../entidade/registry'
import type { RedeIpv6, RedeRov, RedeTransito } from '../../types/api'
import type { MunicipioCtx } from '../municipio/contexto'
import type { UfCtx } from '../uf/contexto'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR', { maximumFractionDigits: 0 }))
const p = (v: number | null | undefined) => (v == null ? '—' : `${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`)

export function CelulaIpv6({ v }: { v: RedeIpv6 }) {
  return <div><dt className="text-xs text-gray-500">Acessos em IPv6 <span className="text-gray-400">(estimativa)</span></dt><dd className="text-lg font-semibold tabular-nums">{p(v.pct_v6)}</dd>
    <dd className="text-xs text-gray-500">≈ {n(v.v6_estimado)} de {n(v.acessos)} acessos · cobertura {p(v.cobertura)}</dd></div>
}

export function CelulaTransito({ v }: { v: RedeTransito }) {
  return <div><dt className="text-xs text-gray-500">Acessos com um só provedor de trânsito <span className="text-gray-400">(inferido)</span></dt><dd className="text-lg font-semibold tabular-nums">{p(v.pct_provedor_unico)}</dd>
    <dd className="text-xs text-gray-500">cobertura {p(v.cobertura)}{v.provedor_principal && <> · mais comum: {v.provedor_principal.nome || `AS${v.provedor_principal.asn}`} ({p(v.provedor_principal.pct_dos_acessos)} dos acessos)</>}</dd></div>
}

export function CelulaRov({ v }: { v: RedeRov }) {
  return <div><dt className="text-xs text-gray-500">Usuários atrás de ASNs que validam ROV <span className="text-gray-400">(estimativa)</span></dt><dd className="text-lg font-semibold tabular-nums">{p(v.pct_atras_rov)}</dd>
    <dd className="text-xs text-gray-500">≈ {n(v.usuarios_atras_rov)} de {n(v.usuarios_com_medida)} usuários com medida · cobertura {p(v.cobertura)} dos {n(v.usuarios)}</dd></div>
}

const Aviso = ({ limites }: { limites: string }) => <p className="mt-2 text-xs text-gray-500">{limites}</p>

/** IPv6 estimado e dependência de trânsito do município. Estimativa e inferência: a cobertura diz que parcela dos acessos entrou. */
export function RedeTerritorioMunicipioBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const r = dados.redeTerritorio!
  return <div data-testid="rede-territorio"><dl className="grid grid-cols-1 gap-4 md:grid-cols-2">{r.ipv6 && <CelulaIpv6 v={r.ipv6} />}{r.transito && <CelulaTransito v={r.transito} />}</dl><Aviso limites={r.limites} /></div>
}

/** IPv6 estimado, usuários atrás de ROV e dependência de trânsito da UF. */
export function RedeTerritorioUfBloco({ dados }: BlocoProps<UfCtx>) {
  const r = dados.redeTerritorio!
  return <div data-testid="rede-territorio"><dl className="grid grid-cols-1 gap-4 md:grid-cols-3">{r.ipv6 && <CelulaIpv6 v={r.ipv6} />}{r.rov && <CelulaRov v={r.rov} />}{r.transito && <CelulaTransito v={r.transito} />}</dl><Aviso limites={r.limites} /></div>
}
