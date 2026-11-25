// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { registrarBloco, type BlocoDef } from '../entidade/registry'
import type { PrefixoCtx } from './contexto'
import { GeoBloco } from './blocks/GeoBloco'
import { MoasBloco } from './blocks/MoasBloco'
import { OrigemBloco } from './blocks/OrigemBloco'
import { PttsBloco } from './blocks/PttsBloco'
import { RegistroBloco } from './blocks/RegistroBloco'
import { RpkiBloco } from './blocks/RpkiBloco'
import { CicloDeVidaBloco } from './blocks/CicloDeVidaBloco'

/** Blocos da página de prefixo: detentor e origem → RPKI → PTTs → Registro.br → geolocalização → MOAS → ciclo de vida. */
const base = { entidade: 'prefixo' as const }
const def = (b: Omit<BlocoDef<PrefixoCtx>, 'entidade'>) => registrarBloco<PrefixoCtx>({ ...base, ...b })

def({ id: 'origem', titulo: 'Detentor e origem', ordem: 10, depende: ['usePrefixo'], fontes: ['registro_br', 'fulltable_routeviews', 'lg_ixbr'], selo: 'fato', nota: 'detentor pelo Registro.br; origem observada na tabela global coletada (uma origem por prefixo)', Componente: OrigemBloco })
def({ id: 'rpki', titulo: 'RPKI', ordem: 20, depende: ['usePrefixo'], fontes: ['rpki_collector', 'fulltable_routeviews'], selo: 'fato', nota: 'validação da origem observada contra os ROAs publicados; sem anúncio, não avaliado', Componente: RpkiBloco })
def({ id: 'ptts', titulo: 'PTTs onde aparece', ordem: 30, depende: ['useAsn'], fontes: ['lg_ixbr'], selo: 'fato', Componente: PttsBloco })
def({ id: 'registro', titulo: 'Registro.br e tabela global', ordem: 40, depende: ['usePrefixo'], fontes: ['registro_br', 'fulltable_routeviews'], selo: 'fato', Componente: RegistroBloco })
def({ id: 'geo', titulo: 'Geolocalização', ordem: 50, depende: ['usePrefixo'], fontes: ['prefix_geo'], selo: 'inferido', nota: 'DB-IP City Lite (IP Geolocation by DB-IP) e cadastro da organização; a posição do prefixo não é servida, só estado e país', Componente: GeoBloco })
def({ id: 'moas', titulo: 'Origem múltipla (MOAS)', ordem: 60, depende: [], fontes: ['fulltable_routeviews'], nota: 'não medida: a coleta da tabela global guarda uma origem por prefixo', Componente: MoasBloco })
def({ id: 'ciclo-de-vida', titulo: 'Ciclo de vida do bloco IPv4', ordem: 70, depende: ['ipv4-ciclo-de-vida'], fontes: ['ipv4_delegated', 'ipv4_listas'], selo: 'fato', nota: 'diferenças observadas no delegated diário e o que as listas declaram, sem causa nem intenção', aplicavel: (c) => !c.prefix.includes(':'), Componente: CicloDeVidaBloco })
