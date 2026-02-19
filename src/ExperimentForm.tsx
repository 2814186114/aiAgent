import { useState } from 'react'

export function ExperimentForm() {
    const [note, setNote] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [result, setResult] = useState<{ success: boolean; message: string } | null>(null)

    const handleSubmit = async () => {
        if (!note.trim()) return
        
        setIsSubmitting(true)
        setResult(null)
        
        try {
            const response = await fetch('http://localhost:8000/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: `记录实验：${note.trim()}`,
                    sessionId: Date.now().toString()
                })
            })
            
            if (!response.ok) {
                throw new Error('提交失败')
            }
            
            await response.json()
            setResult({
                success: true,
                message: '实验记录已提交！'
            })
            setNote('')
        } catch (err) {
            setResult({
                success: false,
                message: err instanceof Error ? err.message : '提交出错了'
            })
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSubmit()
        }
    }

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold mb-6 text-gray-800 dark:text-white">📝 实验记录</h2>
            
            <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    描述你的实验
                </label>
                <textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="例如：今天跑了BERT在SST-2上的实验，准确率92.3%"
                    className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-white resize-none"
                    rows={4}
                    disabled={isSubmitting}
                />
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                    提示：可以包含模型名称、数据集、指标和数值，系统会自动解析
                </p>
            </div>

            {result && (
                <div className={`mb-6 p-4 rounded-lg ${
                    result.success 
                        ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-300'
                        : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300'
                }`}>
                    {result.message}
                </div>
            )}

            <div className="mb-6">
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    示例：
                </p>
                <div className="grid gap-2 text-sm">
                    <button
                        onClick={() => setNote('今天跑了BERT在SST-2上的实验，准确率92.3%')}
                        className="text-left px-3 py-2 bg-gray-50 dark:bg-gray-700 rounded hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-400 transition-colors"
                        disabled={isSubmitting}
                    >
                        BERT 在 SST-2 上准确率 92.3%
                    </button>
                    <button
                        onClick={() => setNote('GPT-2在WikiText上的困惑度是18.5')}
                        className="text-left px-3 py-2 bg-gray-50 dark:bg-gray-700 rounded hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-400 transition-colors"
                        disabled={isSubmitting}
                    >
                        GPT-2 在 WikiText 上困惑度 18.5
                    </button>
                    <button
                        onClick={() => setNote('ResNet50在ImageNet上的Top-1准确率76.1%')}
                        className="text-left px-3 py-2 bg-gray-50 dark:bg-gray-700 rounded hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-400 transition-colors"
                        disabled={isSubmitting}
                    >
                        ResNet50 在 ImageNet 上 Top-1 准确率 76.1%
                    </button>
                </div>
            </div>

            <button
                onClick={handleSubmit}
                disabled={isSubmitting || !note.trim()}
                className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            >
                {isSubmitting ? '提交中...' : '📝 记录实验'}
            </button>
        </div>
    )
}