import { useState, useEffect } from 'react'

interface TaskSummary {
    id: string
    task: string
    answer?: string
    created_at: string
    updated_at: string
}

interface TaskSidebarProps {
    onSelectTask: (taskId: string) => void
    selectedTaskId?: string
}

export function TaskSidebar({ onSelectTask, selectedTaskId }: TaskSidebarProps) {
    const [tasks, setTasks] = useState<TaskSummary[]>([])
    const [isLoading, setIsLoading] = useState(false)

    const fetchTasks = async () => {
        setIsLoading(true)
        try {
            const response = await fetch('http://localhost:8000/tasks')
            const data = await response.json()
            if (data.success) {
                setTasks(data.tasks)
            }
        } catch (e) {
            console.error('Failed to fetch tasks:', e)
        } finally {
            setIsLoading(false)
        }
    }

    const deleteTask = async (taskId: string, e: React.MouseEvent) => {
        e.stopPropagation()
        if (!confirm('确定要删除此任务吗？')) return
        
        try {
            const response = await fetch(`http://localhost:8000/tasks/${taskId}`, {
                method: 'DELETE'
            })
            const data = await response.json()
            if (data.success) {
                setTasks(tasks.filter(t => t.id !== taskId))
            }
        } catch (e) {
            console.error('Failed to delete task:', e)
        }
    }

    useEffect(() => {
        fetchTasks()
    }, [])

    return (
        <div className="w-72 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col h-full">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-bold text-gray-800 dark:text-white flex items-center gap-2">
                    📋 历史任务
                </h2>
                <button
                    onClick={fetchTasks}
                    className="mt-2 text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
                >
                    刷新
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-2">
                {isLoading ? (
                    <div className="text-center text-gray-500 dark:text-gray-400 py-4">
                        加载中...
                    </div>
                ) : tasks.length === 0 ? (
                    <div className="text-center text-gray-500 dark:text-gray-400 py-4">
                        暂无历史任务
                    </div>
                ) : (
                    <div className="space-y-2">
                        {tasks.map((task) => (
                            <div
                                key={task.id}
                                onClick={() => onSelectTask(task.id)}
                                className={`p-3 rounded-lg cursor-pointer transition-colors ${
                                    selectedTaskId === task.id
                                        ? 'bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800'
                                        : 'hover:bg-gray-50 dark:hover:bg-gray-700 border border-transparent'
                                }`}
                            >
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium text-gray-800 dark:text-white truncate">
                                            {task.task}
                                        </p>
                                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                            {new Date(task.created_at).toLocaleString()}
                                        </p>
                                    </div>
                                    <button
                                        onClick={(e) => deleteTask(task.id, e)}
                                        className="text-gray-400 hover:text-red-500 dark:hover:text-red-400 p-1"
                                        title="删除任务"
                                    >
                                        🗑️
                                    </button>
                                </div>
                                {task.answer && (
                                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-2 line-clamp-2">
                                        {task.answer}
                                    </p>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}