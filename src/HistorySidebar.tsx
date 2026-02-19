import { useState, useEffect } from 'react'

interface HistoryItem {
    id: string
    task: string
    task_type: string
    created_at: string
    answer?: string
}

interface TaskSidebarProps {
    onSelectTask: (taskId: string) => void
    selectedTaskId?: string
    refreshTrigger?: number
}

export function HistorySidebar({ onSelectTask, selectedTaskId, refreshTrigger }: TaskSidebarProps) {
    const [tasks, setTasks] = useState<HistoryItem[]>([])
    const [loading, setLoading] = useState(true)

    const fetchTasks = async () => {
        try {
            const response = await fetch('http://localhost:8000/tasks?limit=50')
            const data = await response.json()
            if (data.success && data.tasks) {
                setTasks(data.tasks)
            }
        } catch (e) {
            console.error('Failed to fetch tasks:', e)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchTasks()
    }, [refreshTrigger])

    const getTaskTypeIcon = (type: string) => {
        const icons: Record<string, string> = {
            'literature_research': '📚',
            'schedule_planning': '📅',
            'experiment_management': '🧪',
            'question_answering': '❓',
            'general': '🔧'
        }
        return icons[type] || '📋'
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

    const deleteTask = async (taskId: string, e: React.MouseEvent) => {
        e.stopPropagation()
        if (!confirm('确定要删除这条记录吗？')) return
        
        try {
            await fetch(`http://localhost:8000/tasks/${taskId}`, { method: 'DELETE' })
            setTasks(prev => prev.filter(t => t.id !== taskId))
        } catch (e) {
            console.error('Failed to delete task:', e)
        }
    }

    return (
        <div className="w-64 bg-gray-800 border-r border-gray-700 flex flex-col h-full">
            <div className="p-4 border-b border-gray-700">
                <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                    📜 历史记录
                </h2>
            </div>
            
            <div className="flex-1 overflow-y-auto">
                {loading ? (
                    <div className="p-4 text-gray-400 text-center">加载中...</div>
                ) : tasks.length === 0 ? (
                    <div className="p-4 text-gray-500 text-center text-sm">
                        暂无历史记录
                    </div>
                ) : (
                    <div className="divide-y divide-gray-700">
                        {tasks.map((task) => (
                            <div
                                key={task.id}
                                onClick={() => onSelectTask(task.id)}
                                className={`p-3 cursor-pointer hover:bg-gray-700 transition-colors group ${
                                    selectedTaskId === task.id ? 'bg-blue-900/30 border-l-2 border-blue-500' : ''
                                }`}
                            >
                                <div className="flex items-start gap-2">
                                    <span className="text-lg">{getTaskTypeIcon(task.task_type)}</span>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-gray-200 text-sm truncate">
                                            {task.task}
                                        </p>
                                        <p className="text-gray-500 text-xs mt-1">
                                            {formatDate(task.created_at)}
                                        </p>
                                    </div>
                                    <button
                                        onClick={(e) => deleteTask(task.id, e)}
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
                    onClick={fetchTasks}
                    className="w-full py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
                >
                    🔄 刷新
                </button>
            </div>
        </div>
    )
}