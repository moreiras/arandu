import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'
import { postAuthLog } from '../services/api'

export function usePageTracker() {
  const location = useLocation()
  const { user } = useAuth()

  useEffect(() => {
    if (!user) return
    postAuthLog(location.pathname + location.search)
  }, [location.pathname, location.search, user])
}
