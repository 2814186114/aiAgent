import { useState, useEffect } from 'react'

interface Conversation {
    id: string
    user_id: number | null
    title: string | null
    created_at: string
    updated_at: string
    messages?: any[]
}

interface ConversationSidebarProps {
    onSelectConversation: (conversationId: string) => void
    selectedConversationId?: string
    refreshTrigger?: number
    currentConversationId?: string | null
    onCreateConversation: () => Promise<string | null>
    onDeleteConversation: (id: string) => void
}

export function ConversationSidebar({ 
    onSelectConversation, 
    selectedConversationId, 
    refreshTrigger,
    currentConversationId,
    onCreateConversation,
    onDeleteConversation
}: ConversationSidebarProps) {
    const [conversations, setConversations] = useState<Conversation[]>([])
    const [loading, setLoading] = useState(true)
    const [searchQuery, setSearchQuery] = useState('')

    const fetchConversations = async () => {
        setLoading(true)
        try {
            const response = await fetch('http://localhost:8000/conversations?limit=50')
            const data = await response.json()
            if (data.success) {
                setConversations(data.conversations)
            }
        } catch (e) {
            console.error('Failed to fetch conversations:', e)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchConversations()
    }, [refreshTrigger])

    const searchConversations = async (query: string) => {
        if (!query.trim()) {
            fetchConversations()
            return
        }
        setLoading(true)
        try {
            const response = await fetch('http://localhost:8000/conversations/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            })
            const data = await response.json()
            if (data.success) {
                setConversations(data.conversations)
            }
        } catch (e) {
            console.error('Failed to search conversations:', e)
        } finally {
            setLoading(false)
        }
    }

    const handleNewChat = async () => {
        await onCreateConversation()
        fetchConversations()
    }

    const formatDate = (dateStr: string) => {
        try {
            const date = new Date(dateStr)
            const now = new Date()
            const diff = now.getTime() - date.getTime()
            const days = Math.floor(diff / (1000 * 60 * 60 * 24))
            
            if (days === 0) {
                return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
            } else if (days === 1) {
                return '昨天'
            } else if (days < 7) {
                return `${days}天前`
            } else {
                return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
            }
        } catch {
            return ''
        }
    }

    const getTitle = (conv: Conversation) => {
        if (conv.title) return conv.title
        if (conv.messages && conv.messages.length > 0) {
            const firstUserMsg = conv.messages.find((m: any) => m.role === 'user')
            if (firstUserMsg) {
                return firstUserMsg.content.substring(0, 30) + (firstUserMsg.content.length > 30 ? '...' : '')
            }
        }
        return '新对话'
    }

    return (
        <div className="w-64 bg-gray-800 border-r border-gray-700 flex flex-col h-full">
            <div className="p-3 border-b border-gray-700">
                <button
                    onClick={handleNewChat}
                    className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium text-sm transition-colors flex items-center justify-center gap-2"
                >
                    <span>➕</span>
                    <span>新对话</span>
                </button>
            </div>

            <div className="p-3 border-b border-gray-700">
                <div className="relative">
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => {
                            setSearchQuery(e.target.value)
                            searchConversations(e.target.value)
                        }}
                        placeholder="搜索对话..."
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                    {searchQuery && (
                        <button
                            onClick={() => {
                                setSearchQuery('')
                                fetchConversations()
                            }}
                            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                        >
                            ✕
                        </button>
                    )}
                </div>
            </div>

            <div className="p-3 border-b border-gray-700">
                <h2 className="text-sm font-semibold text-gray-400">💬 对话历史</h2>
            </div>
            
            <div className="flex-1 overflow-y-auto">
                {loading ? (
                    <div className="p-4 text-gray-400 text-center">加载中...</div>
                ) : conversations.length === 0 ? (
                    <div className="p-4 text-gray-500 text-center text-sm">
                        暂无对话记录
                    </div>
                ) : (
                    <div className="divide-y divide-gray-700">
                        {conversations.map((conv) => (
                            <div
                                key={conv.id}
                                onClick={() => onSelectConversation(conv.id)}
                                className={`p-3 cursor-pointer hover:bg-gray-700 transition-colors group ${
                                    selectedConversationId === conv.id || currentConversationId === conv.id
                                        ? 'bg-blue-900/30 border-l-2 border-blue-500' 
                                        : ''
                                }`}
                            >
                                <div className="flex items-start gap-2">
                                    <span className="text-lg">💬</span>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-gray-200 text-sm truncate">
                                            {getTitle(conv)}
                                        </p>
                                        <p className="text-gray-500 text-xs mt-1">
                                            {formatDate(conv.updated_at)}
                                            {conv.messages && (
                                                <span className="ml-2">· {conv.messages.length}条消息</span>
                                            )}
                                        </p>
                                    </div>
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            if (confirm('确定要删除这个对话吗？')) {
                                                onDeleteConversation(conv.id)
                                            }
                                        }}
                                        className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 transition-all"
                                        title="删除"
                                    >
                                        ✕
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
            
            <div className="p-3 border-t border-gray-700">
                <button
                    onClick={fetchConversations}
                    className="w-full py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
                >
                    🔄 刷新
                </button>
            </div>
        </div>
    )
}
