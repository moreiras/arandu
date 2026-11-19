import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { useQueries } from '@tanstack/react-query'
import { fetchAsnNames, fetchAsnNomes } from '../services/api'

/** Busca e cacheia o dicionário completo {str(asn): nome} para um snapshot. */
export function useAsnNames(date?: string | null) {
  return useQuery({
    queryKey: ['asn-names', date ?? null],
    queryFn: () => fetchAsnNames(date ?? undefined),
    staleTime: Infinity, gcTime: Infinity,
    placeholderData: (prev) => prev,
  })
}

const LOTE_NOMES = 500   // máximo por chamada de /asns/names?asns=

/**
 * Nomes só dos ASNs pedidos, em lotes de 500: a página deixa de baixar o dicionário inteiro (~1,5 MB comprimido).
 * Devolve `{ "asn": nome }`; ASNs sem nome simplesmente não aparecem. A chave do cache é o próprio lote.
 */
export function useAsnNomes(asns: number[], date?: string | null): Record<string, string> {
  const unicos = useMemo(() => [...new Set(asns)].sort((a, b) => a - b), [asns])
  const lotes = useMemo(() => {
    const out: number[][] = []
    for (let i = 0; i < unicos.length; i += LOTE_NOMES) out.push(unicos.slice(i, i + LOTE_NOMES))
    return out
  }, [unicos])
  const resultados = useQueries({
    queries: lotes.map((lote) => ({
      queryKey: ['asn-nomes', date ?? null, lote[0], lote[lote.length - 1], lote.length],
      queryFn: () => fetchAsnNomes(lote, date ?? undefined),
      enabled: !!date,
      staleTime: Infinity, gcTime: Infinity,
    })),
  })
  return useMemo(() => Object.assign({}, ...resultados.map((r) => r.data?.names ?? {})), [resultados])   // eslint-disable-line react-hooks/exhaustive-deps
}
