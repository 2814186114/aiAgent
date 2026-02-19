import { useState } from 'react'
import { PaperList } from './PaperCard'

interface Paper {
    title: string
    authors: string[]
    year?: number
    abstract?: string
    url?: string
    pdf_url?: string
}

export function LiteratureSearch() {
    const [query, setQuery] = useState('')
    const [papers, setPapers] = useState<Paper[]>([])
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const handleSearch = async () => {
        if (!query.trim()) return
        
        setIsLoading(true)
        setError(null)
        setPapers([])
        
        try {
            const response = await fetch('http://localhost:8000/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: `搜索关于"${query.trim()}"的学术论文`,
                    sessionId: Date.now().toString()
                })
            })
            
            if (!response.ok) {
                throw new Error('搜索失败')
            }
            
            const data = await response.json()
            
            const foundPapers: Paper[] = []
            for (const step of data.steps || []) {
                if (step.type === 'observation' && step.tool_result?.papers) {
                    foundPapers.push(...step.tool_result.papers)
                }
            }
            
            setPapers(foundPapers)
            
            if (foundPapers.length === 0) {
                setError('未找到相关论文，请尝试其他关键词')
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : '搜索出错了')
        } finally {
            setIsLoading(false)
        }
    }

    const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            handleSearch()
        }
    }

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold mb-6 text-gray-800 dark:text-white">📚 文献搜索</h2>
            
            <div className="mb-6">
                <div className="flex gap-3">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="搜索论文关键词，例如：深度学习、Transformer..."
                        className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-white"
                        disabled={isLoading}
                    />
                    <button
                        onClick={handleSearch}
                        disabled={isLoading || !query.trim()}
                        className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
                    >
                        {isLoading ? '搜索中...' : '搜索'}
                    </button>
                </div>
            </div>

            {error && (
                <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300">
                    {error}
                </div>
            )}

            {papers.length > 0 && (
                <div>
                    <div className="flex items-center justify-between mb-4">
                        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            找到 {papers.length} 篇论文
                        </p>
                    </div>
                    <PaperList papers={papers} />
                </div>
            )}

            {!isLoading && !error && papers.length === 0 && query.trim() === '' && (
                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                    <p className="text-lg mb-2">输入关键词开始搜索论文</p>
                    <p className="text-sm">支持 Semantic Scholar 和 arXiv 双数据源</p>
                </div>
            )}
        </div>
    )
}