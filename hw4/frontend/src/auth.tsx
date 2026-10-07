import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  name: string
}

export interface SignupInput {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

interface AuthState {
  user: User | null
  token: string | null
  ready: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (input: SignupInput) => Promise<void>
  logout: () => void
}

const TOKEN_KEY = 'cc_token'
const AuthContext = createContext<AuthState | null>(null)

// Turn FastAPI error bodies (string or validation list) into one readable message.
async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail))
      return body.detail.map((d: { msg: string }) => d.msg.replace(/^Value error, /, '')).join(' ')
  } catch {
    /* fall through */
  }
  return `Something went wrong (${res.status}).`
}

async function postJson(url: string, body: unknown) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await errorMessage(res))
  return res.json() as Promise<{ token: string; user: User }>
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  // Restore the session on page load.
  useEffect(() => {
    if (!token) {
      setReady(true)
      return
    }
    fetch('/api/auth/me', { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then(setUser)
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY)
        setToken(null)
      })
      .finally(() => setReady(true))
    // Only on first load; login/signup set the user directly.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function startSession(data: { token: string; user: User }) {
    localStorage.setItem(TOKEN_KEY, data.token)
    setToken(data.token)
    setUser(data.user)
  }

  const value: AuthState = {
    user,
    token,
    ready,
    login: async (email, password) => startSession(await postJson('/api/auth/login', { email, password })),
    signup: async (input) => startSession(await postJson('/api/auth/signup', input)),
    logout: () => {
      localStorage.removeItem(TOKEN_KEY)
      setToken(null)
      setUser(null)
    },
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
