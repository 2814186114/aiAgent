import { useState } from 'react'

interface Paper {
    paper_id: string
    title: string
    authors: string[]
    year: number
    abstract: string
    citation_count: number
    venue: string
    url: string
}

interface ReviewResult {
    success: boolean
    query: string
    summary: string
    total_papers: number
    papers: Paper[]
    review_sections: Array<{
        title: string
        papers?: Paper[]
        timeline?: Array<{ year: string; paper_count: number; milestones: Array<{ title: string }> }>
        concepts?: string[]
    }>
    timeline: Array<{ year: string; paper_count: number }>
    key_concepts: string[]
    highly_cited_papers: Paper[]
}

interface TrendResult {
    success: boolean
    query: string
    year_range: string
    trend_data: Array<{ year: string; paper_count: number; total_citations: number }>
    key_concepts: string[]
    top_venues: Array<{ venue: string; count: number }>
}

interface GapResult {
    success: boolean
    query: string
    potential_gaps: Array<{ type: string; description: string }>
    popular_methods: Array<{ method: string; frequency: number }>
}

type ViewMode = 'review' | 'trends' | 'gaps'

export function LiteratureReview() {
    const [viewMode, setViewMode] = useState<ViewMode>('review')
    const [query, setQuery] = useState('')
    const [loading, setLoading] = useState(false)
    const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null)
    const [trendResult, setTrendResult] = useState<TrendResult | null>(null)
    const [gapResult, setGapResult] = useState<GapResult | null>(null)
    const [error, setError] = useState<string | null>(null)

    const handleGenerate = async () => {
        if (!query.trim()) return
        
        setLoading(true)
        setError(null)
        setReviewResult(null)
        setTrendResult(null)
        setGapResult(null)

        try {
            const endpoint = viewMode === 'review' 
                ? 'http://localhost:8000/literature/review'
                : viewMode === 'trends'
                ? 'http://localhost:8000/literature/trends'
                : 'http://localhost:8000/literature/gaps'

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query.trim() })
            })

            const data = await response.json()

            if (data.success) {
                if (viewMode === 'review') {
                    setReviewResult(data)
                } else if (viewMode === 'trends') {
                    setTrendResult(data)
                } else {
                    setGapResult(data)
                }
            } else {
                setError(data.error || '生成失败')
            }
        } catch (e: any) {
            setError(e.message || '网络错误')
        } finally {
            setLoading(false)
        }
    }

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleGenerate()
        }
    }

    return (
        <div className="h-full flex flex-col">
            <div className="mb-4">
                <h2 className="text-xl font-bold text-gray-800 dark:text-white mb-2">
                    📚 文献分析工具
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                    自动生成文献综述、分析研究趋势、识别研究空白
                </p>
            </div>

            <div className="flex gap-2 mb-4">
                <button
                    onClick={() => setViewMode('review')}
                    className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                        viewMode === 'review'
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                    }`}
                >
                    📝 文献综述
                </button>
                <button
                    onClick={() => setViewMode('trends')}
                    className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                        viewMode === 'trends'
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                    }`}
                >
                    📈 研究趋势
                </button>
                <button
                    onClick={() => setViewMode('gaps')}
                    className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                        viewMode === 'gaps'
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                    }`}
                >
                    🔍 研究空白
                </button>
            </div>

            <div className="flex gap-2 mb-4">
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder={
                        viewMode === 'review' 
                            ? '输入研究主题，如：Transformer attention mechanism'
                            : viewMode === 'trends'
                            ? '输入研究领域，如：large language model'
                            : '输入研究领域，如：machine learning'
                    }
                    className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                    disabled={loading}
                />
                <button
                    onClick={handleGenerate}
                    disabled={loading || !query.trim()}
                    className="px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {loading ? '分析中...' : '生成'}
                </button>
            </div>

            {error && (
                <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300">
                    ❌ {error}
                </div>
            )}

            <div className="flex-1 overflow-auto">
                {viewMode === 'review' && reviewResult && (
                    <div className="space-y-4">
                        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                            <h3 className="font-bold text-gray-800 dark:text-white mb-2">📊 综述摘要</h3>
                            <p className="text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
                                {reviewResult.summary}
                            </p>
                        </div>

                        {reviewResult.highly_cited_papers && reviewResult.highly_cited_papers.length > 0 && (
                            <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                                <h3 className="font-bold text-gray-800 dark:text-white mb-3">🏆 高影响力论文</h3>
                                <div className="space-y-2">
                                    {reviewResult.highly_cited_papers.slice(0, 5).map((paper, idx) => (
                                        <div key={idx} className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                                            <div className="font-medium text-gray-800 dark:text-white text-sm">
                                                {paper.title}
                                            </div>
                                            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                                {paper.authors?.slice(0, 3).join(', ')} · {paper.year} · 
                                                <span className="text-blue-500 ml-1">{paper.citation_count} 引用</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {reviewResult.key_concepts && reviewResult.key_concepts.length > 0 && (
                            <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                                <h3 className="font-bold text-gray-800 dark:text-white mb-3">💡 核心概念</h3>
                                <div className="flex flex-wrap gap-2">
                                    {reviewResult.key_concepts.slice(0, 10).map((concept, idx) => (
                                        <span
                                            key={idx}
                                            className="px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded-full text-sm"
                                        >
                                            {concept}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        {reviewResult.timeline && reviewResult.timeline.length > 0 && (
                            <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                                <h3 className="font-bold text-gray-800 dark:text-white mb-3">📅 发展时间线</h3>
                                <div className="space-y-2">
                                    {reviewResult.timeline.slice(-5).reverse().map((item, idx) => (
                                        <div key={idx} className="flex items-center gap-3">
                                            <span className="w-16 font-bold text-blue-500">{item.year}</span>
                                            <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-blue-500 rounded-full"
                                                    style={{ width: `${Math.min(100, item.paper_count * 5)}%` }}
                                                />
                                            </div>
                                            <span className="text-sm text-gray-500 dark:text-gray-400">
                                                {item.paper_count} 篇
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {viewMode === 'trends' && trendResult && (
                    <div className="space-y-4">
                        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                            <h3 className="font-bold text-gray-800 dark:text-white mb-2">📈 趋势分析</h3>
                            <p className="text-gray-600 dark:text-gray-300">
                                时间范围: {trendResult.year_range} · 论文总数: {trendResult.total_papers}
                            </p>
                        </div>

                        {trendResult.trend_data && trendResult.trend_data.length > 0 && (
                            <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                                <h3 className="font-bold text-gray-800 dark:text-white mb-3">📊 年度论文数量</h3>
                                <div className="space-y-2">
                                    {trendResult.trend_data.map((item, idx) => (
                                        <div key={idx} className="flex items-center gap-3">
                                            <span className="w-12 font-medium text-gray-600 dark:text-gray-300">{item.year}</span>
                                            <div className="flex-1 h-6 bg-gray-100 dark:bg-gray-700 rounded overflow-hidden">
                                                <div
                                                    className="h-full bg-gradient-to-r from-blue-400 to-blue-600 flex items-center justify-end pr-2"
                                                    style={{ width: `${Math.min(100, item.paper_count * 3)}%` }}
                                                >
                                                    <span className="text-xs text-white font-medium">{item.paper_count}</span>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {trendResult.top_venues && trendResult.top_venues.length > 0 && (
                            <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                                <h3 className="font-bold text-gray-800 dark:text-white mb-3">📰 主要发表期刊</h3>
                                <div className="flex flex-wrap gap-2">
                                    {trendResult.top_venues.slice(0, 8).map((venue, idx) => (
                                        <span
                                            key={idx}
                                            className="px-3 py-1 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded-full text-sm"
                                        >
                                            {venue.venue} ({venue.count})
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        {trendResult.key_concepts && trendResult.key_concepts.length > 0 && (
                            <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                                <h3 className="font-bold text-gray-800 dark:text-white mb-3">💡 热门概念</h3>
                                <div className="flex flex-wrap gap-2">
                                    {trendResult.key_concepts.slice(0, 10).map((concept, idx) => (
                                        <span
                                            key={idx}
                                            className="px-3 py-1 bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 rounded-full text-sm"
                                        >
                                            {concept}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {viewMode === 'gaps' && gapResult && (
                    <div className="space-y-4">
                        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                            <h3 className="font-bold text-gray-800 dark:text-white mb-2">🔍 研究空白分析</h3>
                            <p className="text-gray-600 dark:text-gray-300">
                                分析了 {gapResult.total_papers_analyzed} 篇论文
                            </p>
                        </div>

                        {gapResult.potential_gaps && gapResult.potential_gaps.length > 0 && (
                            <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                                <h3 className="font-bold text-gray-800 dark:text-white mb-3">⚠️ 潜在研究空白</h3>
                                <div className="space-y-3">
                                    {gapResult.potential_gaps.slice(0, 5).map((gap, idx) => (
                                        <div key={idx} className="p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg border border-orange-200 dark:border-orange-800">
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className="px-2 py-0.5 bg-orange-200 dark:bg-orange-800 text-orange-700 dark:text-orange-300 rounded text-xs font-medium">
                                                    {gap.type}
                                                </span>
                                            </div>
                                            <p className="text-sm text-gray-700 dark:text-gray-300">
                                                {gap.description}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {gapResult.popular_methods && gapResult.popular_methods.length > 0 && (
                            <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                                <h3 className="font-bold text-gray-800 dark:text-white mb-3">🔧 常用方法</h3>
                                <div className="flex flex-wrap gap-2">
                                    {gapResult.popular_methods.slice(0, 8).map((method, idx) => (
                                        <span
                                            key={idx}
                                            className="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full text-sm"
                                        >
                                            {method.method} ({method.frequency})
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {!reviewResult && !trendResult && !gapResult && !loading && (
                    <div className="flex items-center justify-center h-64 text-gray-400 dark:text-gray-500">
                        <div className="text-center">
                            <div className="text-4xl mb-2">📚</div>
                            <p>输入研究主题开始分析</p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
