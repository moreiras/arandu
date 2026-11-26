// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MetricCard } from '../ui'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'

export function UsuariosBloco({ dados }: BlocoProps<AsnCtx>) {
  const { doc } = dados
  return (
    <div>
      <h2 className="text-base font-semibold text-gray-800 mb-2 flex items-center gap-2">
        Usuários estimados
        <span className="text-xs font-normal text-gray-400">APNIC Labs · janela 60 dias</span>
      </h2>
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
        <MetricCard
          label="Total de usuários"
          value={doc.apnic_users!.toLocaleString('pt-BR')}
          sub={doc.apnic_users_pct_cc != null
            ? `${doc.apnic_users_pct_cc.toFixed(1).replace('.', ',')}% dos usuários de Internet do Brasil`
            : undefined}
          accent="violet"
        />
        <MetricCard
          label="Usuários IPv6"
          value={doc.apnic_v6_users != null
            ? doc.apnic_v6_users.toLocaleString('pt-BR')
            : '—'}
          accent="orange"
        />
        <MetricCard
          label="Adoção de IPv6"
          value={doc.apnic_v6_pct_as != null
            ? `${doc.apnic_v6_pct_as.toFixed(1).replace('.', ',')}%`
            : '—'}
          sub="dos usuários deste AS"
          accent="orange"
        />
        <MetricCard
          label="Usuários por /48 anunciado"
          value={doc.users_per_v6_48 != null
            ? doc.users_per_v6_48.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
            : '—'}
          sub={doc.announced_ipv6_48s != null
            ? `${doc.announced_ipv6_48s.toLocaleString('pt-BR')} /48s anunciados`
            : undefined}
          accent="orange"
        />
        <MetricCard
          label="Usuários por IPv4 anunciado"
          value={doc.users_per_ip != null
            ? doc.users_per_ip.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 2 })
            : '—'}
          sub={doc.announced_ipv4_addresses != null
            ? `${(doc.announced_ipv4_addresses / 1_000_000).toFixed(2).replace('.', ',')} M IPs anunciados`
            : undefined}
          accent="violet"
        />
      </div>
    </div>
  )
}
