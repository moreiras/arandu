// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MetGroup, MetCell, PctCell, num } from '../ui'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'

export function IndicadoresV4Bloco({ dados }: BlocoProps<PttCtx>) {
  const { v4, v4idx } = dados
  return (
    <MetGroup title="IPv4" borderClass="border-primario-100" titleClass="text-primario-500">
      <MetCell
        label="Prefixos únicos"
        value={num(v4idx?.unique_prefixes ?? v4?.unique_prefixes)}
        tooltip="Número de prefixos IPv4 únicos visíveis neste IXP"
      />
      <MetCell
        label="Espaço (/24s)"
        value={num(v4idx?.ixp_space_units)}
        tooltip="Espaço IPv4 coberto por este IXP, expresso em blocos equivalentes /24"
      />
      <PctCell
        label="Cobertura full table"
        value={v4idx?.ixp_vs_fulltable_space_pct ?? v4?.ixp_vs_fulltable_space_pct}
        tooltip="% do espaço IPv4 da tabela de roteamento global coberto pelos prefixos deste IXP"
      />
      <PctCell
        label="Cobertura Registro.br"
        value={v4idx?.br_prefix_coverage_pct ?? v4?.br_prefix_coverage_pct}
        tooltip="% do espaço IPv4 declarado pelo Registro.br para ASNs brasileiros que é visível neste IXP"
      />
    </MetGroup>
  )
}
