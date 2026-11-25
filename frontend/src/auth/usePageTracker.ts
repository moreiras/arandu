import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'
import { postAuthLog } from '../services/api'

export function usePageTracker() {
  const location = useLocation()
  const { user } = useAuth()

  useEffect(() => {
    // Só sessão de conta é registrada (a API ignora o resto). O "Visitante" da allowlist (`provider: 'ip'`) não tem conta: chamar a cada
    // página só gastava o limite de 30/min por IP de /auth/log e dava 429 a quem divide o IP (escritório, NAT).
    if (!user || user.provider === 'ip') return
    postAuthLog(location.pathname + location.search)
  }, [location.pathname, location.search, user])
}
