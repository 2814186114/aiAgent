import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../contexts/AuthContext'

export function LoginModal({ onClose }: { onClose: () => void }) {
    const { login, register } = useAuth()
    const [isLogin, setIsLogin] = useState(true)
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [email, setEmail] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const canvasRef = useRef<HTMLCanvasElement>(null)

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        
        const ctx = canvas.getContext('2d')
        if (!ctx) return

        canvas.width = canvas.offsetWidth
        canvas.height = canvas.offsetHeight

        const chars = 'AGENTPAPER01アイウエオカキクケコサシスセソ'
        const fontSize = 14
        const columns = Math.floor(canvas.width / fontSize)
        const drops: number[] = Array(columns).fill(1)

        const draw = () => {
            ctx.fillStyle = 'rgba(10, 15, 25, 0.05)'
            ctx.fillRect(0, 0, canvas.width, canvas.height)
            
            ctx.fillStyle = '#0ff'
            ctx.font = `${fontSize}px monospace`
            
            for (let i = 0; i < drops.length; i++) {
                const text = chars[Math.floor(Math.random() * chars.length)]
                const x = i * fontSize
                const y = drops[i] * fontSize
                
                if (Math.random() > 0.98) {
                    ctx.fillStyle = '#f0f'
                } else if (Math.random() > 0.95) {
                    ctx.fillStyle = '#0f0'
                } else {
                    ctx.fillStyle = `rgba(0, 255, 255, ${Math.random() * 0.5 + 0.3})`
                }
                
                ctx.fillText(text, x, y)
                
                if (y > canvas.height && Math.random() > 0.975) {
                    drops[i] = 0
                }
                drops[i]++
            }
        }

        const interval = setInterval(draw, 50)

        return () => clearInterval(interval)
    }, [])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            if (isLogin) {
                const result = await login(username, password)
                if (result.success) {
                    onClose()
                } else {
                    setError(result.error || 'ACCESS DENIED')
                }
            } else {
                const result = await register(username, password, email || undefined)
                if (result.success) {
                    const loginResult = await login(username, password)
                    if (loginResult.success) {
                        onClose()
                    } else {
                        setError('REGISTRATION COMPLETE // AUTO-AUTH FAILED')
                    }
                } else {
                    setError(result.error || 'REGISTRATION FAILED')
                }
            }
        } catch (e: any) {
            setError('SYSTEM ERROR // CONNECTION LOST')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center overflow-hidden">
            <canvas 
                ref={canvasRef}
                className="absolute inset-0 w-full h-full"
                style={{ background: 'linear-gradient(135deg, #0a0f19 0%, #1a1a2e 50%, #0f0f23 100%)' }}
            />
            
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-0 left-1/4 w-px h-full bg-gradient-to-b from-transparent via-cyan-500/30 to-transparent animate-pulse" />
                <div className="absolute top-0 left-2/4 w-px h-full bg-gradient-to-b from-transparent via-purple-500/30 to-transparent animate-pulse" style={{ animationDelay: '0.5s' }} />
                <div className="absolute top-0 left-3/4 w-px h-full bg-gradient-to-b from-transparent via-cyan-500/30 to-transparent animate-pulse" style={{ animationDelay: '1s' }} />
            </div>

            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500 to-transparent opacity-50" />
            <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-purple-500 to-transparent opacity-50" />

            <div className="relative z-10 w-full max-w-md mx-4">
                <div className="relative">
                    <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500 via-purple-500 to-cyan-500 rounded-lg blur opacity-30 animate-pulse" />
                    
                    <div className="relative bg-gray-900/95 backdrop-blur-xl border border-cyan-500/30 rounded-lg overflow-hidden">
                        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-400 to-transparent" />
                        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-purple-400 to-transparent" />
                        
                        <div className="absolute top-0 left-0 w-16 h-16 border-l-2 border-t-2 border-cyan-500/50" />
                        <div className="absolute top-0 right-0 w-16 h-16 border-r-2 border-t-2 border-cyan-500/50" />
                        <div className="absolute bottom-0 left-0 w-16 h-16 border-l-2 border-b-2 border-purple-500/50" />
                        <div className="absolute bottom-0 right-0 w-16 h-16 border-r-2 border-b-2 border-purple-500/50" />

                        <div className="p-8">
                            <div className="text-center mb-8">
                                <div className="inline-flex items-center gap-2 mb-4">
                                    <div className="w-3 h-3 bg-cyan-400 rounded-full animate-pulse" />
                                    <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }} />
                                    <div className="w-1 h-1 bg-cyan-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }} />
                                </div>
                                
                                <h1 className="text-2xl font-bold tracking-widest mb-2" style={{
                                    background: 'linear-gradient(90deg, #0ff, #f0f, #0ff)',
                                    backgroundSize: '200% auto',
                                    WebkitBackgroundClip: 'text',
                                    WebkitTextFillColor: 'transparent',
                                    animation: 'gradient 3s linear infinite'
                                }}>
                                    AGENT PAPER
                                </h1>
                                
                                <div className="flex items-center justify-center gap-2 text-xs text-cyan-400/70 font-mono">
                                    <span>{'<'}</span>
                                    <span className="uppercase tracking-wider">{isLogin ? 'AUTHENTICATION' : 'REGISTRATION'}</span>
                                    <span>{'/>'}</span>
                                </div>
                            </div>

                            <form onSubmit={handleSubmit} className="space-y-5">
                                <div className="space-y-1">
                                    <label className="block text-xs text-cyan-400/70 font-mono uppercase tracking-wider">
                                        Username
                                    </label>
                                    <div className="relative">
                                        <input
                                            type="text"
                                            value={username}
                                            onChange={e => setUsername(e.target.value)}
                                            className="w-full px-4 py-3 bg-gray-800/50 border border-cyan-500/30 rounded text-cyan-100 font-mono placeholder-cyan-700 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/50 transition-all"
                                            placeholder="ENTER_USERNAME"
                                            required
                                            autoComplete="off"
                                        />
                                        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-cyan-500/30">{'>'}</div>
                                    </div>
                                </div>

                                {!isLogin && (
                                    <div className="space-y-1">
                                        <label className="block text-xs text-cyan-400/70 font-mono uppercase tracking-wider">
                                            Email [OPTIONAL]
                                        </label>
                                        <div className="relative">
                                            <input
                                                type="email"
                                                value={email}
                                                onChange={e => setEmail(e.target.value)}
                                                className="w-full px-4 py-3 bg-gray-800/50 border border-cyan-500/30 rounded text-cyan-100 font-mono placeholder-cyan-700 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/50 transition-all"
                                                placeholder="ENTER_EMAIL"
                                                autoComplete="off"
                                            />
                                            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-cyan-500/30">{'>'}</div>
                                        </div>
                                    </div>
                                )}

                                <div className="space-y-1">
                                    <label className="block text-xs text-cyan-400/70 font-mono uppercase tracking-wider">
                                        Password
                                    </label>
                                    <div className="relative">
                                        <input
                                            type="password"
                                            value={password}
                                            onChange={e => setPassword(e.target.value)}
                                            className="w-full px-4 py-3 bg-gray-800/50 border border-cyan-500/30 rounded text-cyan-100 font-mono placeholder-cyan-700 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/50 transition-all"
                                            placeholder="ENTER_PASSWORD"
                                            required
                                            autoComplete="off"
                                        />
                                        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-cyan-500/30">{'>'}</div>
                                    </div>
                                </div>

                                {error && (
                                    <div className="px-4 py-2 bg-red-500/10 border border-red-500/30 rounded text-red-400 text-xs font-mono">
                                        <span className="text-red-500">[ERROR]</span> {error}
                                    </div>
                                )}

                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="w-full py-3 relative group overflow-hidden"
                                >
                                    <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/20 via-purple-500/20 to-cyan-500/20 border border-cyan-500/50 rounded transition-all group-hover:border-cyan-400 group-hover:from-cyan-500/30 group-hover:via-purple-500/30 group-hover:to-cyan-500/30" />
                                    <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-400/20 to-transparent animate-pulse" />
                                    </div>
                                    <span className="relative z-10 text-cyan-100 font-mono uppercase tracking-widest text-sm">
                                        {loading ? (
                                            <span className="flex items-center justify-center gap-2">
                                                <span className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
                                                <span>PROCESSING</span>
                                                <span className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
                                            </span>
                                        ) : (
                                            isLogin ? '[ EXECUTE_LOGIN ]' : '[ EXECUTE_REGISTER ]'
                                        )}
                                    </span>
                                </button>
                            </form>

                            <div className="mt-6 pt-6 border-t border-cyan-500/20 text-center">
                                <button
                                    onClick={() => { setIsLogin(!isLogin); setError('') }}
                                    className="text-xs font-mono text-cyan-400/60 hover:text-cyan-400 transition-colors"
                                >
                                    {isLogin ? '[ NEW_USER? REGISTER ]' : '[ HAVE_ACCOUNT? LOGIN ]'}
                                </button>
                            </div>

                            <div className="mt-4 pt-4 border-t border-cyan-500/20 text-center">
                                <button
                                    onClick={onClose}
                                    className="text-xs font-mono text-gray-500 hover:text-gray-400 transition-colors"
                                >
                                    [ SKIP_AUTH // CONTINUE_AS_GUEST ]
                                </button>
                            </div>
                        </div>

                        <div className="px-8 py-3 bg-gray-800/30 border-t border-cyan-500/10">
                            <div className="flex items-center justify-between text-xs font-mono text-cyan-500/40">
                                <span>v1.0.0</span>
                                <span className="flex items-center gap-1">
                                    <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
                                    SYSTEM_ONLINE
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <style>{`
                @keyframes gradient {
                    0% { background-position: 0% center; }
                    100% { background-position: 200% center; }
                }
            `}</style>
        </div>
    )
}
