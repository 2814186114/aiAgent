import { useState, useEffect, useCallback } from 'react'

interface Message {
    id: string
    role: 'user' | 'assistant'
    content: string
    metadata?: any
    created_at: string
}

interface Conversation {
    id: string
    user_id: number | null
    title: string | null
    created_at: string
    updated_at: string
    messages?: Message[]
}

export function useConversation() {
    const [currentConversationId, setCurrentConversationId] = useState<string | null>(null)
    const [conversations, setConversations] = useState<Conversation[]>([])
    const [loading, setLoading] = useState(false)

    const loadConversations = useCallback(async () => {
        try {
            const response = await fetch('http://localhost:8000/conversations?limit=50')
            const data = await response.json()
            if (data.success) {
                setConversations(data.conversations)
            }
        } catch (e) {
            console.error('Failed to load conversations:', e)
        }
    }, [])

    const createConversation = useCallback(async (title?: string) => {
        try {
            const response = await fetch('http://localhost:8000/conversations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title })
            })
            const data = await response.json()
            if (data.success) {
                setCurrentConversationId(data.conversation.id)
                await loadConversations()
                return data.conversation.id
            }
        } catch (e) {
            console.error('Failed to create conversation:', e)
        }
        return null
    }, [loadConversations])

    const loadConversation = useCallback(async (conversationId: string) => {
        try {
            const response = await fetch(`http://localhost:8000/conversations/${conversationId}`)
            const data = await response.json()
            if (data.success) {
                setCurrentConversationId(conversationId)
                return data.conversation
            }
        } catch (e) {
            console.error('Failed to load conversation:', e)
        }
        return null
    }, [])

    const saveMessage = useCallback(async (conversationId: string, role: 'user' | 'assistant', content: string, metadata?: any) => {
        try {
            await fetch('http://localhost:8000/messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    conversation_id: conversationId,
                    role,
                    content,
                    metadata
                })
            })
        } catch (e) {
            console.error('Failed to save message:', e)
        }
    }, [])

    const deleteConversation = useCallback(async (conversationId: string) => {
        try {
            await fetch(`http://localhost:8000/conversations/${conversationId}`, {
                method: 'DELETE'
            })
            await loadConversations()
            if (currentConversationId === conversationId) {
                setCurrentConversationId(null)
            }
        } catch (e) {
            console.error('Failed to delete conversation:', e)
        }
    }, [loadConversations, currentConversationId])

    const searchConversations = useCallback(async (query: string) => {
        try {
            const response = await fetch('http://localhost:8000/conversations/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            })
            const data = await response.json()
            if (data.success) {
                return data.conversations
            }
        } catch (e) {
            console.error('Failed to search conversations:', e)
        }
        return []
    }, [])

    useEffect(() => {
        loadConversations()
    }, [loadConversations])

    return {
        currentConversationId,
        setCurrentConversationId,
        conversations,
        loading,
        loadConversations,
        createConversation,
        loadConversation,
        saveMessage,
        deleteConversation,
        searchConversations
    }
}
