import { useState } from 'react'

interface Paper {
    title: string
    authors: string[]
    year?: number
    abstract?: string
    url?: string
    pdf_url?: string
}

interface PaperCardProps {
    paper: Paper
    index: number
}

export function PaperCard({ paper, index }: PaperCardProps) {
    const [showModal, setShowModal] = useState(false)
    const [isDownloading, setIsDownloading] = useState(false)

    const handleDownload = async (e: React.MouseEvent) => {
        e.stopPropagation()
        if (!paper.pdf_url) return

        setIsDownloading(true)
        try {
            const savePath = prompt('请输入保存路径（例如：C:\\papers\\paper.pdf）：', `paper_${index + 1}.pdf`)
            if (!savePath) return

            const response = await fetch('http://localhost:8000/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: `下载PDF：${paper.pdf_url} 保存到 ${savePath}`,
                    sessionId: Date.now().toString()
                })
            })

            await response.json()
            alert('下载请求已发送，请查看Agent回复确认')
        } catch (err) {
            alert('下载失败：' + (err instanceof Error ? err.message : '未知错误'))
        } finally {
            setIsDownloading(false)
        }
    }

    return (
        <>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow">
                <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center text-blue-600 dark:text-blue-400 font-semibold text-sm">
                        {index + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                        <h3
                            className="font-medium text-gray-900 dark:text-gray-100 text-sm leading-tight mb-1 line-clamp-2 cursor-pointer hover:text-blue-600 dark:hover:text-blue-400"
                            onClick={() => setShowModal(true)}
                        >
                            {paper.title}
                        </h3>
                        <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 line-clamp-1">
                            {paper.authors.join(', ')}
                        </p>
                        <div className="flex items-center gap-2">
                            {paper.year && (
                                <span className="inline-block px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-xs rounded">
                                    {paper.year}
                                </span>
                            )}
                            <div className="flex-1" />
                            {paper.url && (
                                <a
                                    href={paper.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    onClick={(e) => e.stopPropagation()}
                                    className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 text-xs rounded hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
                                >
                                    🔗 页面
                                </a>
                            )}
                            {paper.pdf_url && (
                                <button
                                    onClick={handleDownload}
                                    disabled={isDownloading}
                                    className="inline-flex items-center gap-1 px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 text-xs rounded hover:bg-green-200 dark:hover:bg-green-900/50 transition-colors disabled:opacity-50"
                                >
                                    {isDownloading ? '⏳' : '📥'} {isDownloading ? '下载中' : '下载'}
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {showModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
                    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
                        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                                论文详情
                            </h2>
                            <button
                                onClick={() => setShowModal(false)}
                                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                            >
                                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                        <div className="p-4 overflow-y-auto max-h-[60vh]">
                            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-3">
                                {paper.title}
                            </h3>
                            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                                <strong>作者：</strong>
                                {paper.authors.join(', ')}
                            </p>
                            {paper.year && (
                                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                                    <strong>年份：</strong>
                                    {paper.year}
                                </p>
                            )}
                            {paper.abstract && (
                                <div className="mb-4">
                                    <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                        摘要：
                                    </p>
                                    <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap leading-relaxed">
                                        {paper.abstract}
                                    </p>
                                </div>
                            )}
                            <div className="flex gap-3">
                                {paper.url && (
                                    <a
                                        href={paper.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors"
                                    >
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                        </svg>
                                        打开论文页面
                                    </a>
                                )}
                                {paper.pdf_url && (
                                    <a
                                        href={paper.pdf_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg transition-colors"
                                    >
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                        </svg>
                                        下载PDF
                                    </a>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    )
}

export function PaperList({ papers }: { papers: Paper[] }) {
    if (!papers || papers.length === 0) {
        return null
    }

    return (
        <div className="mt-3">
            <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                搜索到的论文：
            </p>
            <div className="grid gap-3">
                {papers.map((paper, index) => (
                    <PaperCard key={index} paper={paper} index={index} />
                ))}
            </div>
        </div>
    )
}
