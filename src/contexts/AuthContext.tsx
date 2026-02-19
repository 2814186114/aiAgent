import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface User {
    id: number
    username: string
    email?: string
    created_at?: string
    last_login?: string
}

interface AuthContextType {
    user: User | null
    loading: boolean
    login: (username: string, password: string) => Promise<{ success: boolean; error?: string }>
    register: (username: string, password: string, email?: string) => Promise<{ success: boolean; error?: string }>
    logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const savedUser = localStorage.getItem('user')
        if (savedUser) {
            try {
                setUser(JSON.parse(savedUser))
            } catch {
                localStorage.removeItem('user')
            }
        }
        setLoading(false)
    }, [])

    const login = async (username: string, password: string) => {
        try {
            const response = await fetch('http://localhost:8000/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            })
            const data = await response.json()
            
            if (data.success) {
                setUser(data.user)
                localStorage.setItem('user', JSON.stringify(data.user))
                return { success: true }
            } else {
                return { success: false, error: data.error }
            }
        } catch (e: any) {
            return { success: false, error: e.message || '登录失败' }
        }
    }

    const register = async (username: string, password: string, email?: string) => {
        try {
            const response = await fetch('http://localhost:8000/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password, email })
            })
            const data = await response.json()
            
            if (data.success) {
                return { success: true }
            } else {
                return { success: false, error: data.error }
            }
        } catch (e: any) {
            return { success: false, error: e.message || '注册失败' }
        }
    }

    const logout = () => {
        setUser(null)
        localStorage.removeItem('user')
    }

    return (
        <AuthContext.Provider value={{ user, loading, login, register, logout }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}
