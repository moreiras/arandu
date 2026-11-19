// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { lazy, Suspense, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AccessMunicipioMap, type AccessMunicipioMapRow } from '../../components/acessos/AccessMunicipioMap'
import { LegendaQuebras } from '../../components/maps/LegendaQuebras'
import { coresDasClasses, expressaoCor } from '../../components/maps/coresCoropletico'
import { calcularQuebras, rotulosDasClasses } from '../../lib/quebras'

const Coropletico = lazy(() => import('../../components/maps/Coropletico').then((m) => ({ default: m.Coropletico })))

const f1 = (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })

/**
 * Onde a operadora está, como **parcela do município**: coroplético sobre a malha do IBGE, pintado pela parcela dos acessos declarados do município que são
 * da operadora (valor normalizado: um município pequeno com parcela alta aparece, o que as bolhas absolutas escondiam). Município sem acessos da operadora fica cinza.
 * As bolhas de acessos absolutos continuam a um clique (`mostrarBolhas`).
 */
export function MapaShareOperadora({ municipios }: { municipios: AccessMunicipioMapRow[] }) {
  const navigate = useNavigate()
  const [bolhas, setBolhas] = useState(false)
  const com = municipios.filter((m) => m.share != null)
  const mapa = useMemo(() => {
    const valores = Object.fromEntries(com.map((m) => [m.ibge, m.share as number]))
    const quebras = calcularQuebras(Object.values(valores), 5, 'quantis')
    const cores = coresDasClasses(quebras.length + 1)
    return { valores, cor: expressaoCor(valores, quebras, cores), legenda: { rotulos: rotulosDasClasses(quebras, f1), cores } }
  }, [municipios]) // eslint-disable-line react-hooks/exhaustive-deps
  if (com.length === 0 || bolhas) {
    return (
      <div className="space-y-2">
        <AccessMunicipioMap municipios={municipios} height={420} />
        {com.length > 0 && <button type="button" className="text-xs text-primario-600 hover:underline" onClick={() => setBolhas(false)}>Ver a parcela por município</button>}
      </div>
    )
  }
  return (
    <div className="space-y-2" data-testid="mapa-share">
      <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1fr)_14rem] items-start">
        <Suspense fallback={<p className="text-sm text-gray-400" role="status">Carregando o mapa…</p>}>
          <Coropletico cor={mapa.cor} nivel="municipio" altura={420}
            descricao="Mapa dos municípios do Brasil colorido pela parcela dos acessos declarados do município que são desta operadora."
            rotulo={(ibge, nome, uf) => { const v = mapa.valores[ibge]; return `${nome}/${uf}: ${v == null ? 'sem acessos desta operadora' : `${f1(v)}% dos acessos do município`}` }}
            aoClicar={(codigo, nivel) => navigate(nivel === 'uf' ? `/uf/${codigo}` : `/municipio/${codigo}`)} />
        </Suspense>
        <div className="space-y-2">
          <LegendaQuebras titulo="Parcela do município" unidade="% dos acessos do município" rotulos={mapa.legenda.rotulos} cores={mapa.legenda.cores} metodo="quantis" rotuloSemDado="sem acessos desta operadora" />
          <p className="text-xs text-gray-600"><span className="font-medium">Normalização:</span> acessos declarados da operadora no município ÷ acessos declarados de todas as operadoras no município × 100.</p>
          <button type="button" className="text-xs text-primario-600 hover:underline" onClick={() => setBolhas(true)}>Ver acessos absolutos (bolhas)</button>
        </div>
      </div>
      <p className="text-xs text-gray-500">Limites municipais: Fonte: IBGE (Malha Municipal 2024), simplificados. Parcela sobre acessos declarados ao SICI, não sobre receita nem domicílios.</p>
    </div>
  )
}
