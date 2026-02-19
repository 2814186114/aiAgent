import { useState, useEffect, useRef } from 'react'

interface Paper {
    paper_id: string
    title: string
    authors: string[]
    year: number
    abstract: string
    url: string
    pdf_url: string
    source: string
    citation_count: number
    analysis?: {
        contributions: string[]
        methods: string[]
        limitations: string[]
        keywords: string[]
    }
}

interface Cluster {
    name: string
    papers: Paper[]
    paper_count: number
    keywords: string[]
}

interface CrossPoint {
    name: string
    description: string
    related_clusters: string[]
    potential_methods: string[]
}

interface ReportSection {
    title: string
    content: string
    key_findings?: Array<{ finding: string; paper: string; paper_id: string }>
    references?: Array<{ title: string; year: number }>
}

interface ResearchResult {
    success: boolean
    topic: string
    papers: Paper[]
    clusters: Cluster[]
    cross_points: CrossPoint[]
    report: {
        title: string
        sections: ReportSection[]
    }
}

interface Progress {
    state: string
    progress: number
    task: string
}

interface Step {
    type: 'thought' | 'action' | 'observation'
    content: string
    iteration: number
    timestamp?: string
}

interface TaskStep {
    step_type: 'thought' | 'action' | 'observation'
    content: string
    timestamp: string
}

interface ResearchTask {
    task_id: string
    name: string
    description: string
    status: 'pending' | 'in_progress' | 'completed' | 'failed'
    steps?: TaskStep[]
    start_time?: string
    end_time?: string
}

export function ResearchAssistant() {
    const [topic, setTopic] = useState('')
    const [years, setYears] = useState(2)
    const [maxPapers, setMaxPapers] = useState(30)
    const [loading, setLoading] = useState(false)
    const [progress, setProgress] = useState<Progress | null>(null)
    const [steps, setSteps] = useState<Step[]>([])
    const [result, setResult] = useState<ResearchResult | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [tasks, setTasks] = useState<ResearchTask[]>([])
    const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set())

    const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null)
    const [pdfUrl, setPdfUrl] = useState<string | null>(null)

    const wsRef = useRef<WebSocket | null>(null)

    useEffect(() => {
        return () => {
            if (wsRef.current) {
                wsRef.current.close()
            }
        }
    }, [])

    const toggleTaskExpand = (taskId: string) => {
        setExpandedTasks(prev => {
            const newSet = new Set(prev)
            if (newSet.has(taskId)) {
                newSet.delete(taskId)
            } else {
                newSet.add(taskId)
            }
            return newSet
        })
    }

    const downloadReportAsText = (result: ResearchResult) => {
        let text = `${result.report?.title || '研究报告'}\n\n`

        result.report?.sections?.forEach(section => {
            text += `\n${section.title}\n${'='.repeat(section.title.length)}\n`
            text += `${section.content}\n`

            if (section.key_findings && section.key_findings.length > 0) {
                text += '\n主要发现:\n'
                section.key_findings.forEach(finding => {
                    text += `  - ${finding.finding} [${finding.paper}]\n`
                })
            }
        })

        const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${result.topic || 'research_report'}.txt`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }

    const downloadReportAsMarkdown = (result: ResearchResult) => {
        let md = `# ${result.report?.title || '研究报告'}\n\n`

        result.report?.sections?.forEach((section, idx) => {
            md += `\n## ${section.title}\n\n`
            md += `${section.content}\n`

            if (section.key_findings && section.key_findings.length > 0) {
                md += '\n### 主要发现\n\n'
                section.key_findings.forEach(finding => {
                    md += `- ${finding.finding} [${finding.paper}]\n`
                })
            }
        })

        md += '\n---\n\n## 参考文献\n\n'
        result.papers?.slice(0, 20).forEach((paper, idx) => {
            md += `${idx + 1}. ${paper.title}. ${paper.authors?.join(', ')}. (${paper.year}). ${paper.source}.\n`
        })

        const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${result.topic || 'research_report'}.md`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }

    const downloadReportAsHTML = (result: ResearchResult) => {
        let html = `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>${result.report?.title || '研究报告'}</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #1a5fb4; border-bottom: 2px solid #1a5fb4; padding-bottom: 10px; }
        h2 { color: #2c3e50; margin-top: 30px; }
        h3 { color: #34495e; }
        .finding { background: #f8f9fa; padding: 10px; border-left: 4px solid #1a5fb4; margin: 10px 0; }
        .reference { font-size: 0.9em; color: #666; margin: 5px 0; }
    </style>
</head>
<body>
    <h1>${result.report?.title || '研究报告'}</h1>`

        result.report?.sections?.forEach(section => {
            html += `
    <h2>${section.title}</h2>
    <p>${section.content.replace(/\n/g, '<br>')}</p>`

            if (section.key_findings && section.key_findings.length > 0) {
                html += `
    <h3>主要发现</h3>`
                section.key_findings.forEach(finding => {
                    html += `
    <div class="finding">${finding.finding} <span style="color: #1a5fb4;">[${finding.paper}]</span></div>`
                })
            }
        })

        html += `
    <h2>参考文献</h2>`
        result.papers?.slice(0, 20).forEach((paper, idx) => {
            html += `
    <div class="reference">${idx + 1}. ${paper.title}. ${paper.authors?.join(', ')}. (${paper.year}). ${paper.source}.</div>`
        })

        html += `
</body>
</html>`

        const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${result.topic || 'research_report'}.html`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }

    const startResearch = async () => {
        if (!topic.trim()) return

        setLoading(true)
        setError(null)
        setResult(null)
        setSteps([])
        setTasks([])
        setExpandedTasks(new Set())
        setProgress({ state: 'searching', progress: 0, task: '正在初始化...' })

        try {
            const wsUrl = 'ws://localhost:8000/ws/research'
            console.log('Connecting to:', wsUrl)

            const ws = new WebSocket(wsUrl)
            wsRef.current = ws

            ws.onopen = () => {
                console.log('WebSocket connected')
                ws.send(JSON.stringify({
                    type: 'start_research',
                    topic: topic.trim(),
                    years,
                    max_papers: maxPapers
                }))
            }

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data)
                if (data.type === 'progress') {
                    setProgress(data)
                } else if (data.type === 'step') {
                    setSteps(prev => [...prev, {
                        type: data.step_type,
                        content: data.content,
                        iteration: prev.length + 1,
                        timestamp: new Date().toISOString()
                    }])
                } else if (data.type === 'task_list') {
                    setTasks(data.tasks)
                    setSteps(prev => [...prev, {
                        type: 'thought',
                        content: '已规划研究任务列表',
                        iteration: prev.length + 1,
                        timestamp: new Date().toISOString()
                    }])
                } else if (data.type === 'task_update') {
                    setTasks(prev => prev.map(task =>
                        task.task_id === data.task_id
                            ? { ...task, status: data.status }
                            : task
                    ))
                } else if (data.type === 'task_step') {
                    setTasks(prev => prev.map(task => {
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
                    setResult(data.result)
                    setSteps(prev => [...prev, {
                        type: 'thought',
                        content: '研究完成！',
                        iteration: prev.length + 1,
                        timestamp: new Date().toISOString()
                    }])
                    setLoading(false)
                    ws.close()
                } else if (data.type === 'error') {
                    setError(data.error)
                    setSteps(prev => [...prev, {
                        type: 'observation',
                        content: `错误: ${data.error}`,
                        iteration: prev.length + 1,
                        timestamp: new Date().toISOString()
                    }])
                    setLoading(false)
                    ws.close()
                }
            }

            ws.onerror = (event) => {
                console.error('WebSocket error:', event)
                setError('WebSocket连接失败，请检查后端服务是否启动')
                setLoading(false)
            }

            ws.onclose = (event) => {
                console.log('WebSocket closed:', event.code, event.reason)
            }

        } catch (e: any) {
            console.error('Error:', e)
            setError(e.message || '连接错误')
            setLoading(false)
        }
    }

    const openPdf = (paper: Paper) => {
        if (paper.pdf_url) {
            setPdfUrl(paper.pdf_url)
            setSelectedPaper(paper)
        } else if (paper.url) {
            window.open(paper.url, '_blank')
        }
    }

    const getStateLabel = (state: string) => {
        const labels: Record<string, string> = {
            'planning': '📋 规划任务',
            'searching': '🔍 检索文献',
            'analyzing': '📊 分析论文',
            'clustering': '🗂️ 聚类分析',
            'synthesizing': '🔗 识别交叉点',
            'generating_report': '📝 生成报告',
            'completed': '✅ 完成',
            'error': '❌ 错误'
        }
        return labels[state] || state
    }

    const renderPapers = (papers: Paper[]) => (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
            {papers.map((paper, idx) => (
                <div
                    key={paper.paper_id || idx}
                    className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => setSelectedPaper(paper)}
                >
                    <div className="flex items-start justify-between">
                        <div className="flex-1">
                            <h3 className="font-medium text-gray-800 dark:text-white mb-1 text-sm">
                                {paper.title}
                            </h3>
                            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                                {paper.authors?.slice(0, 3).join(', ')}
                                {paper.authors && paper.authors.length > 3 && ' et al.'}
                                {' · '}{paper.year}{' · '}
                                <span className="text-blue-500">{paper.source}</span>
                            </p>
                            <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">
                                {paper.abstract?.substring(0, 150)}...
                            </p>
                        </div>
                        <div className="text-right ml-3">
                            <div className="text-lg font-bold text-blue-500">
                                {paper.citation_count}
                            </div>
                            <div className="text-xs text-gray-400">引用</div>
                            {paper.pdf_url && (
                                <button
                                    onClick={(e) => { e.stopPropagation(); openPdf(paper); }}
                                    className="mt-2 px-2 py-1 bg-red-100 dark:bg-red-900 text-red-600 dark:text-red-300 rounded text-xs hover:bg-red-200 dark:hover:bg-red-800"
                                >
                                    PDF
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            ))}
        </div>
    )

    return (
        <div className="h-full flex flex-col">
            <div className="mb-4">
                <h2 className="text-xl font-bold text-gray-800 dark:text-white mb-2">
                    🔬 深度研究助手
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                    全流程执行：任务规划 → 多源检索 → 论文分析 → 主题聚类 → 识别交叉点 → 生成报告
                </p>
            </div>

            <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 mb-4">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-3">
                    <div className="md:col-span-2">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            研究主题
                        </label>
                        <input
                            type="text"
                            value={topic}
                            onChange={(e) => setTopic(e.target.value)}
                            placeholder="如：AI for Climate Modeling"
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                            disabled={loading}
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            年限
                        </label>
                        <select
                            value={years}
                            onChange={(e) => setYears(Number(e.target.value))}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                            disabled={loading}
                        >
                            <option value={1}>最近1年</option>
                            <option value={2}>最近2年</option>
                            <option value={3}>最近3年</option>
                            <option value={5}>最近5年</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            论文数量
                        </label>
                        <select
                            value={maxPapers}
                            onChange={(e) => setMaxPapers(Number(e.target.value))}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                            disabled={loading}
                        >
                            <option value={20}>20篇</option>
                            <option value={30}>30篇</option>
                            <option value={50}>50篇</option>
                            <option value={80}>80篇</option>
                        </select>
                    </div>
                </div>

                <button
                    onClick={startResearch}
                    disabled={loading || !topic.trim()}
                    className="w-full py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                    {loading ? '研究进行中...' : '🚀 开始深度研究'}
                </button>
            </div>

            {progress && loading && (
                <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800 mb-4">
                    <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-blue-700 dark:text-blue-300">
                            {getStateLabel(progress.state)}
                        </span>
                        <span className="text-sm text-blue-600 dark:text-blue-400">
                            {progress.progress}%
                        </span>
                    </div>
                    <div className="w-full bg-blue-200 dark:bg-blue-800 rounded-full h-2">
                        <div
                            className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${progress.progress}%` }}
                        />
                    </div>
                    <p className="text-sm text-blue-600 dark:text-blue-400 mt-2">
                        {progress.task}
                    </p>
                </div>
            )}

            {error && (
                <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg border border-red-200 dark:border-red-800 mb-4 text-red-700 dark:text-red-300">
                    ❌ {error}
                </div>
            )}

            <div className="flex-1 overflow-auto">
                <div className="space-y-4">
                    {tasks.map((task, idx) => {
                        const isExpanded = expandedTasks.has(task.task_id) || task.status === 'in_progress' || task.status === 'completed'
                        const getStatusIcon = (status: string) => {
                            switch (status) {
                                case 'pending': return '⏸️'
                                case 'in_progress': return '🔄'
                                case 'completed': return '✅'
                                case 'failed': return '❌'
                                default: return '⏸️'
                            }
                        }
                        const getStatusColor = (status: string) => {
                            switch (status) {
                                case 'pending': return 'border-gray-300 bg-gray-50 dark:bg-gray-700 dark:border-gray-600'
                                case 'in_progress': return 'border-yellow-300 bg-yellow-50 dark:bg-yellow-900/20 dark:border-yellow-700'
                                case 'completed': return 'border-green-300 bg-green-50 dark:bg-green-900/20 dark:border-green-700'
                                case 'failed': return 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-700'
                                default: return 'border-gray-300 bg-gray-50 dark:bg-gray-700 dark:border-gray-600'
                            }
                        }
                        return (
                            <div key={task.task_id} className={`mb-4 border rounded-lg ${getStatusColor(task.status)}`}>
                                <div
                                    className="p-4 cursor-pointer hover:bg-opacity-90 flex items-center justify-between"
                                    onClick={() => toggleTaskExpand(task.task_id)}
                                >
                                    <div className="flex items-center gap-3 flex-1">
                                        <span className="text-xl">{getStatusIcon(task.status)}</span>
                                        <div className="flex-1">
                                            <h4 className="font-medium text-gray-800 dark:text-white text-lg">
                                                步骤 {idx + 1}: {task.name}
                                            </h4>
                                            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                                                {task.description}
                                            </p>
                                        </div>
                                    </div>
                                    <span className="text-gray-400 text-sm">
                                        {isExpanded ? '收起' : '展开'} {isExpanded ? '▲' : '▼'}
                                    </span>
                                </div>

                                {isExpanded && (
                                    <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-white dark:bg-gray-800">
                                        {task.steps && task.steps.length > 0 && (
                                            <div>
                                                <h5 className="font-medium text-gray-700 dark:text-gray-300 mb-3">
                                                    📝 思考链
                                                </h5>
                                                <div className="space-y-3">
                                                    {task.steps.map((step, stepIdx) => (
                                                        <div
                                                            key={stepIdx}
                                                            className={`p-4 rounded-lg border ${step.step_type === 'thought'
                                                                ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
                                                                : step.step_type === 'action'
                                                                    ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                                                                    : 'bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600'
                                                                }`}
                                                        >
                                                            <div className="flex items-center gap-2 mb-2">
                                                                <span className="text-sm font-medium px-3 py-1 rounded-full">
                                                                    {step.step_type === 'thought' ? '💭 思考' : step.step_type === 'action' ? '⚡ 行动' : '👁️ 观察'}
                                                                </span>
                                                                <span className="text-xs text-gray-500 dark:text-gray-400">
                                                                    步骤 {stepIdx + 1}
                                                                </span>
                                                            </div>
                                                            <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                                                                {step.content}
                                                            </p>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {task.status === 'completed' && task.task_id === 'search' && result && (
                                            <div className="mt-4">
                                                <h5 className="font-medium text-gray-700 dark:text-gray-300 mb-3">
                                                    📄 检索结果 ({result.papers.length} 篇论文)
                                                </h5>
                                                {renderPapers(result.papers.slice(0, 8))}
                                                {result.papers.length > 8 && (
                                                    <p className="text-center text-gray-500 dark:text-gray-400 mt-2 text-sm">
                                                        ... 还有 {result.papers.length - 8} 篇论文
                                                    </p>
                                                )}
                                            </div>
                                        )}

                                        {task.status === 'completed' && task.task_id === 'cluster' && result && (
                                            <div className="mt-4">
                                                <h5 className="font-medium text-gray-700 dark:text-gray-300 mb-3">
                                                    🗂️ 研究方向 ({result.clusters.length} 个)
                                                </h5>
                                                <div className="space-y-4">
                                                    {result.clusters.map((cluster, clusterIdx) => (
                                                        <div key={clusterIdx} className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                                                            <div className="flex items-center justify-between mb-3">
                                                                <h6 className="font-bold text-gray-800 dark:text-white">
                                                                    {cluster.name}
                                                                </h6>
                                                                <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded-full text-sm">
                                                                    {cluster.paper_count} 篇论文
                                                                </span>
                                                            </div>
                                                            <div className="flex flex-wrap gap-2 mb-3">
                                                                {cluster.keywords?.slice(0, 5).map((kw, i) => (
                                                                    <span key={i} className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded text-xs">
                                                                        {kw}
                                                                    </span>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {task.status === 'completed' && task.task_id === 'synthesis' && result && (
                                            <div className="mt-4">
                                                <h5 className="font-medium text-gray-700 dark:text-gray-300 mb-3">
                                                    🔗 研究交叉点 ({(result.cross_points || []).length} 个)
                                                </h5>
                                                {result.cross_points && result.cross_points.length > 0 ? (
                                                    <div className="bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 p-4 rounded-lg border border-purple-200 dark:border-purple-800">
                                                        {result.cross_points.map((cp, cpIdx) => (
                                                            <div key={cpIdx} className="mb-3 p-3 bg-white dark:bg-gray-800 rounded-lg last:mb-0">
                                                                <div className="font-medium text-gray-800 dark:text-white mb-1">
                                                                    {cp.name}
                                                                </div>
                                                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                                                    {cp.description}
                                                                </p>
                                                                <div className="mt-2 flex flex-wrap gap-1">
                                                                    {cp.related_clusters?.map((rc, i) => (
                                                                        <span key={i} className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 rounded text-xs">
                                                                            {rc}
                                                                        </span>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <p className="text-gray-500 dark:text-gray-400 text-sm">
                                                        未发现明显的研究交叉点
                                                    </p>
                                                )}
                                            </div>
                                        )}

                                        {task.status === 'completed' && task.task_id === 'report' && result && result.report && (
                                            <div className="mt-4">
                                                <div className="flex items-center justify-between mb-4">
                                                    <h5 className="text-xl font-bold text-gray-800 dark:text-white">
                                                        📝 {result.report.title}
                                                    </h5>
                                                    <div className="flex gap-2">
                                                        <button
                                                            onClick={() => downloadReportAsText(result)}
                                                            className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
                                                        >
                                                            📄 下载 TXT
                                                        </button>
                                                        <button
                                                            onClick={() => downloadReportAsMarkdown(result)}
                                                            className="px-3 py-1 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-900/50"
                                                        >
                                                            📝 下载 MD
                                                        </button>
                                                        <button
                                                            onClick={() => downloadReportAsHTML(result)}
                                                            className="px-3 py-1 text-sm bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded hover:bg-green-200 dark:hover:bg-green-900/50"
                                                        >
                                                            🌐 下载 HTML
                                                        </button>
                                                    </div>
                                                </div>

                                                {result.report.sections?.map((section, idx) => (
                                                    <div key={idx} className="mb-6">
                                                        <h6 className="text-lg font-bold text-gray-700 dark:text-gray-200 mb-2 border-b border-gray-200 dark:border-gray-700 pb-1">
                                                            {section.title}
                                                        </h6>
                                                        <p className="text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                                                            {section.content}
                                                        </p>

                                                        {section.key_findings && section.key_findings.length > 0 && (
                                                            <div className="mt-3 space-y-2">
                                                                {section.key_findings.map((finding, i) => (
                                                                    <div key={i} className="p-2 bg-gray-50 dark:bg-gray-700 rounded text-sm">
                                                                        <span className="text-gray-700 dark:text-gray-300">
                                                                            • {finding.finding}
                                                                        </span>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )
                    })}
                </div>
            </div>

            {!result && !loading && tasks.length === 0 && (
                <div className="flex-1 flex items-center justify-center text-gray-400 dark:text-gray-500">
                    <div className="text-center">
                        <div className="text-6xl mb-4">🔬</div>
                        <p className="text-lg mb-2">输入研究主题开始深度调研</p>
                        <p className="text-sm">
                            系统将自动执行完整研究流程：任务规划 → 多源检索 → 论文分析 → 聚类分析 → 识别交叉点 → 生成报告
                        </p>
                    </div>
                </div>
            )}

            {pdfUrl && selectedPaper && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                    <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-5xl h-5/6 flex flex-col">
                        <div className="flex items-center justify-between p-3 border-b border-gray-200 dark:border-gray-700">
                            <h3 className="font-medium text-gray-800 dark:text-white truncate">
                                {selectedPaper.title}
                            </h3>
                            <button
                                onClick={() => { setPdfUrl(null); setSelectedPaper(null); }}
                                className="px-3 py-1 bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
                            >
                                关闭
                            </button>
                        </div>
                        <div className="flex-1">
                            <iframe
                                src={pdfUrl}
                                className="w-full h-full"
                                title="PDF Preview"
                            />
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
