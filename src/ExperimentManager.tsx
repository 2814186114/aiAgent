import { useState, useEffect } from 'react'

interface Experiment {
    id: number
    timestamp: string
    model: string | null
    dataset: string | null
    metric: string | null
    value: number | null
    notes: string
}

export function ExperimentManager() {
    const [experiments, setExperiments] = useState<Experiment[]>([])
    const [loading, setLoading] = useState(false)
    const [editingId, setEditingId] = useState<number | null>(null)
    const [editForm, setEditForm] = useState<Partial<Experiment>>({})
    const [note, setNote] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [result, setResult] = useState<{ success: boolean; message: string } | null>(null)
    const [modelFilter, setModelFilter] = useState('')
    const [datasetFilter, setDatasetFilter] = useState('')
    const [metricFilter, setMetricFilter] = useState('')

    const fetchExperiments = async () => {
        setLoading(true)
        try {
            const params = new URLSearchParams()
            if (modelFilter) params.append('model', modelFilter)
            if (datasetFilter) params.append('dataset', datasetFilter)
            if (metricFilter) params.append('metric', metricFilter)
            
            const response = await fetch(`http://localhost:8000/experiments?${params}`)
            const data = await response.json()
            if (data.success) {
                setExperiments(data.experiments)
            }
        } catch (err) {
            console.error('获取实验记录失败:', err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchExperiments()
    }, [modelFilter, datasetFilter, metricFilter])

    const handleSubmit = async () => {
        if (!note.trim()) return
        
        setIsSubmitting(true)
        setResult(null)
        
        try {
            const response = await fetch('http://localhost:8000/experiments', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ note: note.trim() })
            })
            
            const data = await response.json()
            if (data.success) {
                setResult({
                    success: true,
                    message: '实验记录已提交！'
                })
                setNote('')
                fetchExperiments()
            } else {
                setResult({
                    success: false,
                    message: data.error || '提交失败'
                })
            }
        } catch (err) {
            setResult({
                success: false,
                message: err instanceof Error ? err.message : '提交出错了'
            })
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleDelete = async (id: number) => {
        if (!confirm('确定要删除这条实验记录吗？')) return
        
        try {
            const response = await fetch(`http://localhost:8000/experiments/${id}`, {
                method: 'DELETE'
            })
            
            const data = await response.json()
            if (data.success) {
                fetchExperiments()
            } else {
                alert(data.error || '删除失败')
            }
        } catch (err) {
            alert('删除出错了')
        }
    }

    const handleEdit = (exp: Experiment) => {
        setEditingId(exp.id)
        setEditForm({ ...exp })
    }

    const handleSaveEdit = async () => {
        if (!editingId) return
        
        try {
            const response = await fetch(`http://localhost:8000/experiments/${editingId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(editForm)
            })
            
            const data = await response.json()
            if (data.success) {
                setEditingId(null)
                setEditForm({})
                fetchExperiments()
            } else {
                alert(data.error || '更新失败')
            }
        } catch (err) {
            alert('更新出错了')
        }
    }

    const formatDate = (timestamp: string) => {
        const date = new Date(timestamp)
        return date.toLocaleString('zh-CN')
    }

    return (
        <div className="space-y-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
                <h2 className="text-2xl font-bold mb-6 text-gray-800 dark:text-white">📝 添加实验记录</h2>
                
                <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        描述你的实验
                    </label>
                    <textarea
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
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

            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
                <h2 className="text-2xl font-bold mb-6 text-gray-800 dark:text-white">📊 实验记录管理</h2>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            模型筛选
                        </label>
                        <input
                            type="text"
                            value={modelFilter}
                            onChange={(e) => setModelFilter(e.target.value)}
                            placeholder="例如：BERT"
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-white"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            数据集筛选
                        </label>
                        <input
                            type="text"
                            value={datasetFilter}
                            onChange={(e) => setDatasetFilter(e.target.value)}
                            placeholder="例如：SST-2"
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-white"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            指标筛选
                        </label>
                        <input
                            type="text"
                            value={metricFilter}
                            onChange={(e) => setMetricFilter(e.target.value)}
                            placeholder="例如：准确率"
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-white"
                        />
                    </div>
                </div>

                {loading ? (
                    <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                        加载中...
                    </div>
                ) : experiments.length === 0 ? (
                    <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                        暂无实验记录
                    </div>
                ) : (
                    <div className="space-y-4">
                        {experiments.map((exp) => (
                            <div key={exp.id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                                {editingId === exp.id ? (
                                    <div className="space-y-4">
                                        <div className="grid grid-cols-2 gap-4">
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                                    模型
                                                </label>
                                                <input
                                                    type="text"
                                                    value={editForm.model || ''}
                                                    onChange={(e) => setEditForm({ ...editForm, model: e.target.value })}
                                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-800 dark:text-white"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                                    数据集
                                                </label>
                                                <input
                                                    type="text"
                                                    value={editForm.dataset || ''}
                                                    onChange={(e) => setEditForm({ ...editForm, dataset: e.target.value })}
                                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-800 dark:text-white"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                                    指标
                                                </label>
                                                <input
                                                    type="text"
                                                    value={editForm.metric || ''}
                                                    onChange={(e) => setEditForm({ ...editForm, metric: e.target.value })}
                                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-800 dark:text-white"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                                    数值
                                                </label>
                                                <input
                                                    type="number"
                                                    value={editForm.value || ''}
                                                    onChange={(e) => setEditForm({ ...editForm, value: e.target.value ? parseFloat(e.target.value) : null })}
                                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-800 dark:text-white"
                                                />
                                            </div>
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                                备注
                                            </label>
                                            <textarea
                                                value={editForm.notes || ''}
                                                onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-800 dark:text-white resize-none"
                                                rows={3}
                                            />
                                        </div>
                                        <div className="flex gap-2">
                                            <button
                                                onClick={handleSaveEdit}
                                                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
                                            >
                                                保存
                                            </button>
                                            <button
                                                onClick={() => {
                                                    setEditingId(null)
                                                    setEditForm({})
                                                }}
                                                className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
                                            >
                                                取消
                                            </button>
                                        </div>
                                    </div>
                                ) : (
                                    <div>
                                        <div className="flex justify-between items-start mb-2">
                                            <div className="text-sm text-gray-500 dark:text-gray-400">
                                                {formatDate(exp.timestamp)}
                                            </div>
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={() => handleEdit(exp)}
                                                    className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                                                >
                                                    编辑
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(exp.id)}
                                                    className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
                                                >
                                                    删除
                                                </button>
                                            </div>
                                        </div>
                                        <div className="flex flex-wrap gap-3 mb-3">
                                            {exp.model && (
                                                <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full text-sm">
                                                    🤖 {exp.model}
                                                </span>
                                            )}
                                            {exp.dataset && (
                                                <span className="px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full text-sm">
                                                    📊 {exp.dataset}
                                                </span>
                                            )}
                                            {exp.metric && exp.value !== null && (
                                                <span className="px-3 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full text-sm">
                                                    📈 {exp.metric}: {exp.value}
                                                </span>
                                            )}
                                        </div>
                                        <p className="text-gray-700 dark:text-gray-300">{exp.notes}</p>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}
