import { create } from 'zustand'
import type { IXPIndexEntry } from '../types/api'

interface AppState {
  activeDate: string | null
  latestSnapshot: string | null
  ixpIndex: IXPIndexEntry[] | null
  setActiveDate: (date: string | null) => void
  setLatestSnapshot: (date: string) => void
  setIxpIndex: (index: IXPIndexEntry[]) => void
}

export const useAppStore = create<AppState>((set) => ({
  activeDate: null,
  latestSnapshot: null,
  ixpIndex: null,

  setActiveDate: (date) => set({ activeDate: date }),

  setLatestSnapshot: (date) =>
    set((state) => ({
      latestSnapshot: date,
      activeDate: state.activeDate ?? date,
    })),

  setIxpIndex: (index) => set({ ixpIndex: index }),
}))
