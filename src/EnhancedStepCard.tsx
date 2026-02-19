import { useState } from 'react'

interface AgentStep {
    type: 'thought' | 'action' | 'observation' | 'error' | 'answer'
    content?: string
    tool?: string
    arguments?: Record<string, unknown>
    tool_result?: any
    iteration: number
}

interface EnhancedStepCardProps {
    step: AgentStep
    onEdit?: (newArgs: Record<string, unknown>) => void
    onRetry?: () => void
    onSkip?: () => void
    status?: 'pending' | 'running' | 'success' | 'failed'
}

export function EnhancedStepCard({ 
    step, 
    onEdit, 
    onRetry, 
    onSkip, 
    status = 'success' 
}: EnhancedStepCardProps) {
    const [isEditMode, setIsEditMode] = useState(false)
    const [editArgs, setEditArgs] = useState(JSON.stringify(step.arguments || {}, null, 2))

    const getStepStyle = () => {
        switch (step.type) {
            case 'thought':
                return 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-400'
            case 'action':
                return 'bg-purple-50 dark:bg-purple-900/20 border-l-4 border-purple-400'
            case 'observation':
                return 'bg-green-50 dark:bg-green-900/20 border-l-4 border-green-400'
            case 'error':
                return 'bg-red-50 dark:bg-red-900/20 border-l-4 border-red-400'
            case 'answer':
                return 'bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-400'
            default:
                return 'bg-gray-50 dark:bg-gray-800 border-l-4 border-gray-400'
        }
    }

    const getStepIcon = () => {
        switch (step.type) {
            case 'thought':
                return '💭'
            case 'action':
                return '⚡'
            case 'observation':
                return '👁️'
            case 'error':
                return '❌'
            case 'answer':
                return '✅'
            default:
                return '📌'
        }
    }

    const getStepTitle = () => {
        switch (step.type) {
            case 'thought':
                return '思考'
            case 'action':
                return `行动: ${step.tool || '未知工具'}`
            case 'observation':
                return '观察'
            case 'error':
                return '错误'
            case 'answer':
                return '答案'
            default:
                return '步骤'
        }
    }

    const getStatusBadge = () => {
        switch (status) {
            case 'pending':
                return <span className="px-2 py-1 text-xs rounded bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300">等待中</span>
            case 'running':
                return <span className="px-2 py-1 text-xs rounded bg-yellow-200 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300 animate-pulse">执行中</span>
            case 'success':
                return <span className="px-2 py-1 text-xs rounded bg-green-200 dark:bg-green-900 text-green-700 dark:text-green-300">成功</span>
            case 'failed':
                return <span className="px-2 py-1 text-xs rounded bg-red-200 dark:bg-red-900 text-red-700 dark:text-red-300">失败</span>
            default:
                return null
        }
    }

    const handleSaveEdit = () => {
        try {
            const newArgs = JSON.parse(editArgs)
            onEdit?.(newArgs)
            setIsEditMode(false)
        } catch (e) {
            alert('JSON 格式错误')
        }
    }

    return (
        <div className={`rounded-r-lg p-4 mb-3 ${getStepStyle()} animate-fadeIn relative`}>
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                    <span className="text-lg">{getStepIcon()}</span>
                    <span className="font-medium text-sm text-gray-700 dark:text-gray-300">
                        {getStepTitle()}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                        步骤 {step.iteration}
                    </span>
                </div>
                <div className="flex items-center gap-2">
                    {getStatusBadge()}
                    {step.type === 'action' && (onRetry || onSkip || onEdit) && (
                        <div className="flex gap-1">
                            {onEdit && (
                                <button
                                    onClick={() => setIsEditMode(!isEditMode)}
                                    className="px-2 py-1 text-xs rounded bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-800"
                                >
                                    编辑
                                </button>
                            )}
                            {onRetry && (
                                <button
                                    onClick={onRetry}
                                    className="px-2 py-1 text-xs rounded bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-800"
                                >
                                    重试
                                </button>
                            )}
                            {onSkip && (
                                <button
                                    onClick={onSkip}
                                    className="px-2 py-1 text-xs rounded bg-orange-100 dark:bg-orange-900 text-orange-600 dark:text-orange-300 hover:bg-orange-200 dark:hover:bg-orange-800"
                                    title="跳过此步骤（可能导致任务失败）"
                                >
                                    跳过
                                </button>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {step.type === 'action' && step.arguments && !isEditMode && (
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-2 font-mono bg-white/50 dark:bg-gray-800/50 p-2 rounded">
                    <pre className="whitespace-pre-wrap">{JSON.stringify(step.arguments, null, 2)}</pre>
                </div>
            )}

            {isEditMode && (
                <div className="mb-2">
                    <textarea
                        value={editArgs}
                        onChange={(e) => setEditArgs(e.target.value)}
                        className="w-full p-2 text-xs font-mono rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-white"
                        rows={6}
                    />
                    <div className="flex gap-2 mt-2">
                        <button
                            onClick={handleSaveEdit}
                            className="px-3 py-1 text-xs rounded bg-blue-500 text-white hover:bg-blue-600"
                        >
                            保存
                        </button>
                        <button
                            onClick={() => {
                                setIsEditMode(false)
                                setEditArgs(JSON.stringify(step.arguments || {}, null, 2))
                            }}
                            className="px-3 py-1 text-xs rounded bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-400 dark:hover:bg-gray-500"
                        >
                            取消
                        </button>
                    </div>
                </div>
            )}

            {step.content && (
                <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
                    {step.content}
                </p>
            )}

            {step.type === 'observation' && step.tool_result && (
                <div className="mt-2 text-xs">
                    <details className="cursor-pointer">
                        <summary className="font-medium text-gray-700 dark:text-gray-300 mb-1">
                            工具结果详情
                        </summary>
                        <pre className="whitespace-pre-wrap bg-white/50 dark:bg-gray-800/50 p-2 rounded text-gray-600 dark:text-gray-400">
                            {JSON.stringify(step.tool_result, null, 2)}
                        </pre>
                    </details>
                </div>
            )}
        </div>
    )
}