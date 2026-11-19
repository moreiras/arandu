// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MetGroup, MetCell, PctCell, num } from '../ui'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'

export function IndicadoresV6Bloco({ dados }: BlocoProps<PttCtx>) {
  const { v6, v6idx } = dados
  return (
    <MetGroup title="IPv6" borderClass="border-v6-100" titleClass="text-v6-500">
      <MetCell
        label="Prefixos únicos"
        value={num(v6idx?.unique_prefixes ?? v6?.unique_prefixes)}
        tooltip="Número de prefixos IPv6 únicos visíveis neste IXP"
      />
      <MetCell
        label="Espaço (/48s)"
        value={v6idx?.ixp_space_units != null ? num(v6idx.ixp_space_units, 0) : '—'}
        tooltip="Espaço IPv6 coberto por este IXP, expresso em blocos equivalentes /48"
      />
      <PctCell
        label="Cobertura full table"
        value={v6idx?.ixp_vs_fulltable_space_pct ?? v6?.ixp_vs_fulltable_space_pct}
        tooltip="% do espaço IPv6 da tabela de roteamento global coberto pelos prefixos deste IXP"
      />
      <PctCell
        label="Cobertura Registro.br"
        value={v6idx?.br_prefix_coverage_pct ?? v6?.br_prefix_coverage_pct}
        tooltip="% do espaço IPv6 declarado pelo Registro.br para ASNs brasileiros que é visível neste IXP"
      />
    </MetGroup>
  )
}
