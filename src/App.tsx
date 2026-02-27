import { useState, useEffect, useRef, useCallback } from 'react'
import { PPTGenerator } from './PPTGenerator'
import { EnhancedStepCard } from './EnhancedStepCard'
import { TaskSidebar } from './TaskSidebar'
import { LiteratureManager } from './LiteratureManager'
import { LiteratureReview } from './LiteratureReview'
import { ResearchAssistant } from './ResearchAssistant'
import { ExperimentManager } from './ExperimentManager'
import { UnifiedAssistant } from './UnifiedAssistant'
import { VisualizationDashboard } from './VisualizationDashboard'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { LoginModal } from './components/LoginModal'

interface Paper {
    title: string
    authors: string[]
    year?: number
    abstract?: string
    url?: string
    pdf_url?: string
}

interface Experiment {
    id: number
    timestamp: string
    model?: string
    dataset?: string
    metric?: string
    value?: number
    notes?: string
}

interface ToolResult {
    success?: boolean
    papers?: Paper[]
    experiments?: Experiment[]
    message?: string
    error?: string
    total_pages?: number
    summary?: string
    save_path?: string
    file_size?: number
    data?: any
    id?: number
    total?: number
}

interface AgentStep {
    type: 'thought' | 'action' | 'observation' | 'error' | 'answer'
    content?: string
    tool?: string
    arguments?: Record<string, unknown>
    tool_result?: ToolResult
    iteration: number
}

interface Message {
    id: string
    content: string
    sender: 'user' | 'agent'
    timestamp: Date
    steps?: AgentStep[]
    isComplete?: boolean
    taskId?: string
}

type Tab = 'unified' | 'chat' | 'research' | 'literature' | 'review' | 'experiment' | 'ppt' | 'visualization'
type InputMode = 'chat' | 'record' | 'query'

interface QuickAction {
    id: string
    label: string
    icon: string
    mode: InputMode
    prefix: string
    placeholder: string
}

const QUICK_ACTIONS: QuickAction[] = [
    { id: 'chat', label: '对话', icon: '💬', mode: 'chat', prefix: '', placeholder: '提问、搜索论文、分析问题...' },
    { id: 'experiment', label: '记录实验', icon: '🧪', mode: 'record', prefix: '/实验 ', placeholder: '描述你的实验结果，如：BERT在SST-2上准确率92.3%' },
    { id: 'reminder', label: '添加日程', icon: '📅', mode: 'record', prefix: '/日程 ', placeholder: '描述你的日程，如：明天下午3点组会' },
    { id: 'query', label: '查询记录', icon: '🔍', mode: 'query', prefix: '/查询 ', placeholder: '查询历史，如：最近的BERT实验' },
]

function AppContent() {
    const { user, loading, logout } = useAuth()
    const [activeTab, setActiveTab] = useState<Tab>('unified')
    const [showSidebar, setShowSidebar] = useState(true)
    const [messages, setMessages] = useState<Message[]>([])
    const [inputValue, setInputValue] = useState('')
    const [inputMode, setInputMode] = useState<InputMode>('chat')
    const [showModeHint, setShowModeHint] = useState(false)
    const [detectedMode, setDetectedMode] = useState<{ mode: InputMode; hint: string } | null>(null)
    const [isConnected, setIsConnected] = useState(false)
    const [isProcessing, setIsProcessing] = useState(false)
    const [currentSteps, setCurrentSteps] = useState<AgentStep[]>([])
    const [currentAnswer, setCurrentAnswer] = useState<string | null>(null)
    const [selectedTaskId, setSelectedTaskId] = useState<string | undefined>()
    const [chatMode, setChatMode] = useState<'normal' | 'planning'>('normal')
    const [planTasks, setPlanTasks] = useState<any[]>([])
    const [expandedPlanTasks, setExpandedPlanTasks] = useState<Set<string>>(new Set())
    const [planningProgress, setPlanningProgress] = useState<any | null>(null)
    const [planningSteps, setPlanningSteps] = useState<any[]>([])
    const [planningLoading, setPlanningLoading] = useState(false)
    const [planningError, setPlanningError] = useState<string | null>(null)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const chatWsRef = useRef<WebSocket | null>(null)
    const planningWsRef = useRef<WebSocket | null>(null)
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

    const saveTask = async (taskId: string, task: string, answer: string | null, steps: AgentStep[]) => {
        try {
            await fetch('http://localhost:8000/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    task_id: taskId,
                    task,
                    answer,
                    steps
                })
            })
        } catch (e) {
            console.error('Failed to save task:', e)
        }
    }

    const loadTask = async (taskId: string) => {
        try {
            const response = await fetch(`http://localhost:8000/tasks/${taskId}`)
            const data = await response.json()
            if (data.success && data.task) {
                const task = data.task
                const message: Message = {
                    id: task.id,
                    content: task.task,
                    sender: 'user',
                    timestamp: new Date(task.created_at)
                }
                const answerMessage: Message = {
                    id: task.id + '-answer',
                    content: task.answer || '',
                    sender: 'agent',
                    timestamp: new Date(task.updated_at),
                    steps: task.steps,
                    isComplete: true,
                    taskId: task.id
                }
                setMessages([message, answerMessage])
                setSelectedTaskId(taskId)
            }
        } catch (e) {
            console.error('Failed to load task:', e)
        }
    }

    const connectSocket = useCallback(() => {
        if (chatWsRef.current?.readyState === WebSocket.OPEN) return

        const ws = new WebSocket('ws://localhost:8000/ws/chat')
        chatWsRef.current = ws

        ws.onopen = () => {
            console.log('Connected to Python WebSocket')
            setIsConnected(true)
        }

        ws.onclose = () => {
            console.log('Disconnected from Python WebSocket')
            setIsConnected(false)
            if (!reconnectTimeoutRef.current) {
                reconnectTimeoutRef.current = setTimeout(() => {
                    reconnectTimeoutRef.current = null
                    connectSocket()
                }, 3000)
            }
        }

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data)
                if (data.type === 'step') {
                    const step: AgentStep = {
                        type: data.step_type || 'observation',
                        content: data.content,
                        tool: data.tool,
                        arguments: data.arguments,
                        tool_result: data.tool_result,
                        iteration: currentSteps.length + 1
                    }
                    setCurrentSteps(prev => [...prev, step])
                } else if (data.type === 'complete') {
                    setCurrentAnswer(data.answer || data.result?.final_answer || '任务完成')
                    setIsProcessing(false)
                } else if (data.type === 'error') {
                    setCurrentSteps(prev => [...prev, {
                        type: 'error',
                        content: data.error || data.message,
                        iteration: prev.length + 1
                    }])
                    setIsProcessing(false)
                }
            } catch (err) {
                console.error('Error parsing WebSocket message:', err)
            }
        }

        ws.onerror = (err) => {
            console.error('WebSocket error:', err)
            setIsConnected(false)
        }
    }, [currentSteps.length])

    useEffect(() => {
        connectSocket()

        return () => {
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current)
            }
            chatWsRef.current?.close()
        }
    }, [connectSocket])

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages, currentSteps, currentAnswer])

    useEffect(() => {
        if (currentAnswer && currentSteps.length > 0 && !isProcessing) {
            const lastUserMessage = [...messages].reverse().find(m => m.sender === 'user')
            if (lastUserMessage) {
                const taskId = Date.now().toString()
                const agentMessage: Message = {
                    id: Date.now().toString(),
                    content: currentAnswer,
                    sender: 'agent',
                    timestamp: new Date(),
                    steps: currentSteps,
                    isComplete: true,
                    taskId
                }
                setMessages(prev => [...prev, agentMessage])
                setCurrentSteps([])
                setCurrentAnswer(null)

                saveTask(taskId, lastUserMessage.content, currentAnswer, currentSteps)
            }
        }
    }, [currentAnswer, currentSteps, isProcessing, messages])

    if (loading) {
        return (
            <div className="h-screen flex items-center justify-center bg-gray-900">
                <div className="text-center">
                    <div className="animate-spin w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full mx-auto mb-4"></div>
                    <p className="text-gray-400">加载中...</p>
                </div>
            </div>
        )
    }

    if (!user) {
        return <LoginModal onClose={() => { }} />
    }

    const detectInputMode = (text: string): { mode: InputMode; hint: string; processedText: string } => {
        const lowerText = text.toLowerCase().trim()

        if (lowerText.startsWith('/实验') || lowerText.startsWith('/experiment')) {
            return {
                mode: 'record',
                hint: '将记录为实验结果',
                processedText: text.replace(/^\/实验\s*/i, '').replace(/^\/experiment\s*/i, '')
            }
        }
        if (lowerText.startsWith('/日程') || lowerText.startsWith('/提醒') || lowerText.startsWith('/reminder')) {
            return {
                mode: 'record',
                hint: '将添加为日程提醒',
                processedText: text.replace(/^\/日程\s*/i, '').replace(/^\/提醒\s*/i, '').replace(/^\/reminder\s*/i, '')
            }
        }
        if (lowerText.startsWith('/查询') || lowerText.startsWith('/query')) {
            return {
                mode: 'query',
                hint: '将查询历史记录',
                processedText: text.replace(/^\/查询\s*/i, '').replace(/^\/query\s*/i, '')
            }
        }

        const experimentKeywords = ['跑了', '测试了', '实验结果', '准确率', 'loss', '精度', 'f1', 'recall', 'precision', '训练了', '模型在', '数据集上']
        const reminderKeywords = ['提醒我', '别忘了', '记得', '明天', '下周', '今天下午', '今天上午', '组会', '开会', '截止', '提交']
        const queryKeywords = ['查看', '查询', '最近', '历史', '所有实验', '所有日程', '找一下', '有没有']

        for (const keyword of experimentKeywords) {
            if (lowerText.includes(keyword)) {
                return { mode: 'record', hint: `检测到实验关键词"${keyword}"，将记录为实验`, processedText: text }
            }
        }

        for (const keyword of reminderKeywords) {
            if (lowerText.includes(keyword)) {
                return { mode: 'record', hint: `检测到日程关键词"${keyword}"，将添加为提醒`, processedText: text }
            }
        }

        for (const keyword of queryKeywords) {
            if (lowerText.includes(keyword)) {
                return { mode: 'query', hint: `检测到查询关键词"${keyword}"，将查询历史`, processedText: text }
            }
        }

        return { mode: 'chat', hint: '将作为对话处理', processedText: text }
    }

    const handleInputChange = (value: string) => {
        setInputValue(value)
        if (value.trim()) {
            const detected = detectInputMode(value)
            setDetectedMode(detected)
            setShowModeHint(true)
        } else {
            setShowModeHint(false)
            setDetectedMode(null)
        }
    }

    const handleQuickAction = (action: QuickAction) => {
        setInputMode(action.mode)
        if (!inputValue.startsWith(action.prefix)) {
            setInputValue(action.prefix)
        }
        setShowModeHint(false)
        setDetectedMode({ mode: action.mode, hint: action.label })
    }

    const handleSendMessage = async () => {
        if (!inputValue.trim() || isProcessing || planningLoading) return

        const detected = detectInputMode(inputValue)
        let finalMessage = inputValue.trim()

        if (detected.mode === 'record') {
            if (inputValue.toLowerCase().includes('实验') ||
                inputValue.toLowerCase().includes('准确率') ||
                inputValue.toLowerCase().includes('loss') ||
                inputValue.toLowerCase().includes('训练') ||
                inputValue.toLowerCase().includes('测试')) {
                finalMessage = `请帮我记录实验：${detected.processedText}`
            } else if (inputValue.toLowerCase().includes('提醒') ||
                inputValue.toLowerCase().includes('明天') ||
                inputValue.toLowerCase().includes('下周') ||
                inputValue.toLowerCase().includes('组会')) {
                finalMessage = `请帮我添加日程：${detected.processedText}`
            }
        } else if (detected.mode === 'query') {
            finalMessage = `请帮我查询：${detected.processedText}`
        }

        const userMessage: Message = {
            id: Date.now().toString(),
            content: inputValue.trim(),
            sender: 'user',
            timestamp: new Date(),
        }

        setMessages(prev => [...prev, userMessage])
        setShowModeHint(false)
        setDetectedMode(null)
        setPlanTasks([])
        setPlanningSteps([])
        setPlanningProgress(null)
        setPlanningError(null)
        setExpandedPlanTasks(new Set())

        if (chatMode === 'planning') {
            setPlanningLoading(true)
            setIsProcessing(true)

            try {
                const wsUrl = 'ws://localhost:8000/ws/planning'
                console.log('Connecting to:', wsUrl)

                const ws = new WebSocket(wsUrl)
                planningWsRef.current = ws

                ws.onopen = () => {
                    console.log('Planning WebSocket connected')
                    ws.send(JSON.stringify({
                        type: 'start_planning',
                        task: finalMessage
                    }))
                }

                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data)
                    if (data.type === 'progress') {
                        setPlanningProgress(data)
                    } else if (data.type === 'step') {
                        setPlanningSteps(prev => [...prev, {
                            type: data.step_type,
                            content: data.content,
                            iteration: prev.length + 1,
                            timestamp: new Date().toISOString()
                        }])
                    } else if (data.type === 'task_list') {
                        setPlanTasks(data.tasks)
                        setPlanningSteps(prev => [...prev, {
                            type: 'thought',
                            content: '已规划任务列表',
                            iteration: prev.length + 1,
                            timestamp: new Date().toISOString()
                        }])
                    } else if (data.type === 'task_update') {
                        setPlanTasks(prev => prev.map(task =>
                            task.task_id === data.task_id
                                ? { ...task, status: data.status }
                                : task
                        ))
                    } else if (data.type === 'task_step') {
                        setPlanTasks(prev => prev.map(task => {
                            if (task.task_id === data.task_id) {
                                return {
                                    ...task,
                                    steps: [...(task.steps || []), {
                                        step_type: data.step_type,
                                        content: data.content,
                                        timestamp: data.timestamp
                                    }]
                                }
                            }
                            return task
                        }))
                    } else if (data.type === 'complete') {
                        const result = data.result
                        if (result.plan) {
                            setPlanTasks(result.plan)
                        }

                        const agentMessage: Message = {
                            id: Date.now().toString(),
                            content: result.final_answer || '任务完成！',
                            sender: 'agent',
                            timestamp: new Date(),
                            steps: planningSteps,
                            isComplete: true,
                            taskId: Date.now().toString()
                        }
                        setMessages(prev => [...prev, agentMessage])
                        setPlanningLoading(false)
                        setIsProcessing(false)
                        setCurrentSteps([])
                        setCurrentAnswer(null)

                        saveTask(agentMessage.taskId!, userMessage.content, agentMessage.content, planningSteps)
                        ws.close()
                    } else if (data.type === 'error') {
                        setPlanningError(data.error)
                        setPlanningSteps(prev => [...prev, {
                            type: 'observation',
                            content: `错误: ${data.error}`,
                            iteration: prev.length + 1,
                            timestamp: new Date().toISOString()
                        }])
                        setPlanningLoading(false)
                        setIsProcessing(false)
                        const errorMessage: Message = {
                            id: Date.now().toString(),
                            content: `抱歉，处理您的请求时遇到了问题：${data.error}`,
                            sender: 'agent',
                            timestamp: new Date(),
                        }
                        setMessages(prev => [...prev, errorMessage])
                        ws.close()
                    }
                }

                ws.onerror = (event) => {
                    console.error('WebSocket error:', event)
                    setPlanningError('WebSocket连接失败，请检查后端服务是否启动')
                    setPlanningLoading(false)
                    setIsProcessing(false)
                }

                ws.onclose = (event) => {
                    console.log('WebSocket closed:', event.code, event.reason)
                }

            } catch (e: any) {
                console.error('Error:', e)
                setPlanningError(e.message || '连接错误')
                setPlanningLoading(false)
                setIsProcessing(false)
                const errorMessage: Message = {
                    id: Date.now().toString(),
                    content: '抱歉，处理您的请求时遇到了问题。请重试。',
                    sender: 'agent',
                    timestamp: new Date(),
                }
                setMessages(prev => [...prev, errorMessage])
            }
        } else {
            setIsProcessing(true)
            setCurrentSteps([])
            setCurrentAnswer(null)
            setSelectedTaskId(undefined)

            if (chatWsRef.current?.readyState === WebSocket.OPEN) {
                chatWsRef.current.send(JSON.stringify({
                    type: 'task',
                    message: finalMessage
                }))
            } else {
                setPlanningError('WebSocket 未连接，请检查后端服务')
                setIsProcessing(false)
            }
        }

        setInputValue('')
    }

    const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSendMessage()
        }
    }

    const getCurrentPlaceholder = () => {
        const action = QUICK_ACTIONS.find(a => a.mode === inputMode)
        return action?.placeholder || '输入你的学术任务...'
    }

    return (
        <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex">
            {showSidebar && activeTab === 'chat' && (
                <TaskSidebar
                    onSelectTask={loadTask}
                    selectedTaskId={selectedTaskId}
                />
            )}

            <div className="flex-1 flex flex-col">
                <div className="chat-container flex flex-col h-screen">
                    <header className="chat-header flex-shrink-0">
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-3">
                                {activeTab === 'chat' && (
                                    <button
                                        onClick={() => setShowSidebar(!showSidebar)}
                                        className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                                    >
                                        {showSidebar ? '◀️' : '▶️'}
                                    </button>
                                )}
                                <h1 className="text-2xl font-bold">Academic Assistant Agent</h1>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></span>
                                <span className="text-sm">{isConnected ? '已连接' : '未连接'}</span>
                            </div>
                            <div className="flex items-center gap-3 ml-4">
                                <div className="flex items-center gap-2">
                                    <span className="text-sm text-gray-600 dark:text-gray-300">
                                        👤 {user.username}
                                    </span>
                                    <button
                                        onClick={logout}
                                        className="px-3 py-1 text-sm bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                                    >
                                        登出
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div className="flex gap-2 border-b border-gray-200 dark:border-gray-700 flex-wrap">
                            <button
                                onClick={() => setActiveTab('unified')}
                                className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${activeTab === 'unified'
                                    ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t border-l border-r border-gray-200 dark:border-gray-700'
                                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                                    }`}
                            >
                                🤖 智能助手
                            </button>
                            <button
                                onClick={() => setActiveTab('chat')}
                                className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${activeTab === 'chat'
                                    ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t border-l border-r border-gray-200 dark:border-gray-700'
                                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                                    }`}
                            >
                                💬 聊天助手
                            </button>
                            {activeTab === 'chat' && (
                                <div className="flex items-center gap-2 ml-4">
                                    <button
                                        onClick={() => setChatMode('normal')}
                                        className={`px-3 py-1 text-sm rounded-full transition-all ${chatMode === 'normal'
                                            ? 'bg-blue-500 text-white shadow-md'
                                            : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                                            }`}
                                    >
                                        💬 普通聊天
                                    </button>
                                    <button
                                        onClick={() => setChatMode('planning')}
                                        className={`px-3 py-1 text-sm rounded-full transition-all ${chatMode === 'planning'
                                            ? 'bg-blue-500 text-white shadow-md'
                                            : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                                            }`}
                                    >
                                        📋 任务规划
                                    </button>
                                </div>
                            )}
                            <button
                                onClick={() => setActiveTab('literature')}
                                className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${activeTab === 'literature'
                                    ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t border-l border-r border-gray-200 dark:border-gray-700'
                                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                                    }`}
                            >
                                📚 文献搜索
                            </button>
                            <button
                                onClick={() => setActiveTab('research')}
                                className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${activeTab === 'research'
                                    ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t border-l border-r border-gray-200 dark:border-gray-700'
                                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                                    }`}
                            >
                                🔬 深度研究
                            </button>
                            <button
                                onClick={() => setActiveTab('review')}
                                className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${activeTab === 'review'
                                    ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t border-l border-r border-gray-200 dark:border-gray-700'
                                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                                    }`}
                            >
                                📝 文献综述
                            </button>
                            <button
                                onClick={() => setActiveTab('experiment')}
                                className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${activeTab === 'experiment'
                                    ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t border-l border-r border-gray-200 dark:border-gray-700'
                                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                                    }`}
                            >
                                🧪 实验记录
                            </button>
                            <button
                                onClick={() => setActiveTab('ppt')}
                                className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${activeTab === 'ppt'
                                    ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t border-l border-r border-gray-200 dark:border-gray-700'
                                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                                    }`}
                            >
                                📊 PPT 生成器
                            </button>
                            <button
                                onClick={() => setActiveTab('visualization')}
                                className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${activeTab === 'visualization'
                                    ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t border-l border-r border-gray-200 dark:border-gray-700'
                                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                                    }`}
                            >
                                📈 可视化
                            </button>
                        </div>
                    </header>

                    <main className={`chat-messages flex-1 ${activeTab === 'unified' ? 'overflow-y-auto' : 'overflow-hidden'}`}>
                        {activeTab === 'unified' ? (
                            <UnifiedAssistant />
                        ) : activeTab === 'chat' ? (
                            <div className="h-full overflow-y-auto">
                                {messages.length === 0 && !isProcessing && (
                                    <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                                        <div className="text-center max-w-lg">
                                            <div className="text-6xl mb-4">🎓</div>
                                            <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-2">学术助手智能体</h2>
                                            <p className="text-sm mb-6 text-gray-600 dark:text-gray-400">
                                                帮助你完成文献调研、实验记录、日程管理等学术任务
                                            </p>

                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
                                                <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
                                                    <div className="text-2xl mb-2">💬</div>
                                                    <h3 className="font-medium text-gray-800 dark:text-white text-sm">对话问答</h3>
                                                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">搜索论文、分析问题</p>
                                                </div>
                                                <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
                                                    <div className="text-2xl mb-2">🔬</div>
                                                    <h3 className="font-medium text-gray-800 dark:text-white text-sm">深度研究</h3>
                                                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">多源检索、聚类分析</p>
                                                </div>
                                                <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
                                                    <div className="text-2xl mb-2">🧪</div>
                                                    <h3 className="font-medium text-gray-800 dark:text-white text-sm">记录实验</h3>
                                                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">自动解析实验结果</p>
                                                </div>
                                            </div>

                                            <div className="text-left bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
                                                <p className="font-medium text-gray-800 dark:text-white mb-3 text-sm">💡 快速开始</p>
                                                <div className="space-y-2">
                                                    <button
                                                        onClick={() => handleInputChange('搜索Transformer相关的最新论文')}
                                                        className="w-full text-left px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 transition-colors"
                                                    >
                                                        🔍 搜索Transformer相关的最新论文
                                                    </button>
                                                    <button
                                                        onClick={() => handleInputChange('/实验 BERT在SST-2上准确率92.3%')}
                                                        className="w-full text-left px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 transition-colors"
                                                    >
                                                        🧪 记录实验：BERT在SST-2上准确率92.3%
                                                    </button>
                                                    <button
                                                        onClick={() => handleInputChange('/日程 明天下午3点组会')}
                                                        className="w-full text-left px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 transition-colors"
                                                    >
                                                        📅 添加日程：明天下午3点组会
                                                    </button>
                                                    <button
                                                        onClick={() => handleInputChange('/查询 最近的实验记录')}
                                                        className="w-full text-left px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 transition-colors"
                                                    >
                                                        📋 查询最近的实验记录
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {chatMode === 'planning' && (
                                    <div className="px-4 mb-4">
                                        {planningProgress && planningLoading && (
                                            <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800 mb-4">
                                                <div className="flex items-center justify-between mb-2">
                                                    <span className="font-medium text-blue-700 dark:text-blue-300">
                                                        {(() => {
                                                            const labels: Record<string, string> = {
                                                                'planning': '📋 规划任务',
                                                                'executing': '⚡ 执行中',
                                                                'completed': '✅ 完成',
                                                                'error': '❌ 错误'
                                                            }
                                                            return labels[planningProgress.state] || planningProgress.state
                                                        })()}
                                                    </span>
                                                    <span className="text-sm text-blue-600 dark:text-blue-400">
                                                        {planningProgress.progress}%
                                                    </span>
                                                </div>
                                                <div className="w-full bg-blue-200 dark:bg-blue-800 rounded-full h-2">
                                                    <div
                                                        className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                                                        style={{ width: `${planningProgress.progress}%` }}
                                                    />
                                                </div>
                                                <p className="text-sm text-blue-600 dark:text-blue-400 mt-2">
                                                    {planningProgress.task}
                                                </p>
                                            </div>
                                        )}

                                        {planningError && (
                                            <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg border border-red-200 dark:border-red-800 mb-4 text-red-700 dark:text-red-300">
                                                ❌ {planningError}
                                            </div>
                                        )}

                                        {planTasks.length > 0 && (
                                            <div className="bg-gray-800 dark:bg-gray-900 rounded-lg p-4 mb-4">
                                                <div className="flex items-center justify-between mb-4">
                                                    <h3 className="text-lg font-bold text-white">
                                                        📋 任务执行
                                                    </h3>
                                                    <span className="text-gray-400 text-sm">
                                                        {planTasks.filter(t => t.status === 'completed').length}/{planTasks.length} 已完成
                                                    </span>
                                                </div>
                                                <div className="space-y-3">
                                                    {planTasks.map((task, idx) => {
                                                        const getStatusIcon = (status: string) => {
                                                            switch (status) {
                                                                case 'pending': return '⭕';
                                                                case 'in_progress': return '🔄';
                                                                case 'completed': return '✅';
                                                                case 'failed': return '❌';
                                                                default: return '⭕';
                                                            }
                                                        }
                                                        return (
                                                            <div
                                                                key={task.task_id}
                                                                className={`flex items-center gap-3 p-3 rounded-lg ${task.status === 'completed'
                                                                    ? 'bg-green-900/30 border border-green-700'
                                                                    : task.status === 'in_progress'
                                                                        ? 'bg-yellow-900/30 border border-yellow-700'
                                                                        : 'bg-gray-700 border border-gray-600'
                                                                    }`}
                                                            >
                                                                <span className="text-xl">{getStatusIcon(task.status)}</span>
                                                                <div className="flex-1">
                                                                    <h4 className={`font-medium ${task.status === 'completed'
                                                                        ? 'text-green-300'
                                                                        : task.status === 'in_progress'
                                                                            ? 'text-yellow-300'
                                                                            : 'text-gray-300'
                                                                        }`}>
                                                                        {task.name}
                                                                    </h4>
                                                                </div>
                                                            </div>
                                                        )
                                                    })}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {messages.map((message) => (
                                    <div key={message.id} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'} px-4`}>
                                        <div className={`message-bubble ${message.sender === 'user' ? 'message-user' : 'message-agent'} max-w-[85%] my-2`}>
                                            {message.sender === 'user' ? (
                                                <p>{message.content}</p>
                                            ) : (
                                                <>
                                                    {message.steps && message.steps.length > 0 && (
                                                        <div className="mb-3">
                                                            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 font-medium">
                                                                思考过程：
                                                            </p>
                                                            {message.steps.map((step, index) => (
                                                                <div key={index}>
                                                                    <EnhancedStepCard
                                                                        step={step}
                                                                        status="success"
                                                                    />
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}
                                                    <div className="pt-2 border-t border-gray-200 dark:border-gray-600">
                                                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">最终答案：</p>
                                                        <p className="whitespace-pre-wrap">{message.content}</p>
                                                    </div>
                                                </>
                                            )}
                                            <p className="text-xs text-gray-400 mt-2 text-right">
                                                {message.timestamp.toLocaleTimeString()}
                                            </p>
                                        </div>
                                    </div>
                                ))}

                                {isProcessing && currentSteps.length > 0 && (
                                    <div className="flex justify-start px-4">
                                        <div className="message-bubble message-agent max-w-[85%] my-2">
                                            <div className="flex items-center gap-2 mb-2">
                                                <div className="animate-spin w-4 h-4 border-2 border-primary-500 border-t-transparent rounded-full"></div>
                                                <span className="text-sm text-gray-500 dark:text-gray-400">Agent 正在思考...</span>
                                            </div>
                                            {currentSteps.map((step, index) => (
                                                <EnhancedStepCard
                                                    key={index}
                                                    step={step}
                                                    status={index === currentSteps.length - 1 ? 'running' : 'success'}
                                                />
                                            ))}
                                        </div>
                                    </div>
                                )}

                                <div ref={messagesEndRef} />
                            </div>
                        ) : activeTab === 'literature' ? (
                            <div className="h-full overflow-auto p-4">
                                <LiteratureManager />
                            </div>
                        ) : activeTab === 'research' ? (
                            <div className="h-full overflow-auto p-4">
                                <ResearchAssistant />
                            </div>
                        ) : activeTab === 'review' ? (
                            <div className="h-full overflow-auto p-4">
                                <LiteratureReview />
                            </div>
                        ) : activeTab === 'experiment' ? (
                            <div className="h-full overflow-auto p-4">
                                <ExperimentManager />
                            </div>
                        ) : activeTab === 'ppt' ? (
                            <div className="h-full overflow-auto p-4">
                                <PPTGenerator />
                            </div>
                        ) : activeTab === 'visualization' ? (
                            <VisualizationDashboard />
                        ) : null}
                    </main>

                    {activeTab === 'chat' && (
                        <footer className="chat-input-container flex-shrink-0">
                            <div className="mb-3 flex gap-2 flex-wrap">
                                {QUICK_ACTIONS.map(action => (
                                    <button
                                        key={action.id}
                                        onClick={() => handleQuickAction(action)}
                                        className={`px-3 py-1.5 text-sm rounded-full transition-all ${inputMode === action.mode
                                            ? 'bg-primary-500 text-white shadow-md'
                                            : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                                            }`}
                                    >
                                        {action.icon} {action.label}
                                    </button>
                                ))}
                            </div>

                            {showModeHint && detectedMode && (
                                <div className={`mb-2 px-3 py-2 rounded-lg text-sm flex items-center gap-2 ${detectedMode.mode === 'record'
                                    ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800'
                                    : detectedMode.mode === 'query'
                                        ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800'
                                        : 'bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700'
                                    }`}>
                                    <span className="text-lg">
                                        {detectedMode.mode === 'record' ? '📝' : detectedMode.mode === 'query' ? '🔍' : '💬'}
                                    </span>
                                    <span>{detectedMode.hint}</span>
                                </div>
                            )}

                            <div className="flex gap-3">
                                <div className="flex-1 relative">
                                    <input
                                        type="text"
                                        value={inputValue}
                                        onChange={(e) => handleInputChange(e.target.value)}
                                        onKeyPress={handleKeyPress}
                                        placeholder={getCurrentPlaceholder()}
                                        className="chat-input w-full"
                                        disabled={!isConnected || isProcessing}
                                    />
                                </div>
                                <button
                                    onClick={handleSendMessage}
                                    disabled={!isConnected || isProcessing || !inputValue.trim()}
                                    className="send-button"
                                >
                                    {isProcessing ? '处理中...' : '发送'}
                                </button>
                            </div>

                            <div className="mt-2 text-xs text-gray-400 dark:text-gray-500">
                                💡 提示：使用 <code className="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">/实验</code>、<code className="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">/日程</code>、<code className="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">/查询</code> 快速切换模式，或直接输入内容自动识别
                            </div>
                        </footer>
                    )}
                </div>
            </div>
        </div>
    )
}

function App() {
    return (
        <AuthProvider>
            <AppContent />
        </AuthProvider>
    )
}

export default App