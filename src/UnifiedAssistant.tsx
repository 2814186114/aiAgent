import { useState, useRef, useEffect } from 'react'
import { HistorySidebar } from './HistorySidebar'

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

interface PlanTask {
    task_id: string
    name: string
    description: string
    output_type: string
    status: 'pending' | 'in_progress' | 'completed' | 'failed'
    output?: any
    result?: string
}

interface Progress {
    state: string
    progress: number
    task: string
}

interface SavedTask {
    id: string
    task: string
    task_type?: string
    answer?: string
    plan?: PlanTask[]
    created_at: string
}

interface ConversationMessage {
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp: string
    result?: any
    papers?: Paper[]
    plan?: PlanTask[]
    taskType?: string
}

interface ConversationContext {
    messages: ConversationMessage[]
    currentPapers: Paper[]
    selectedPaperIndex: number | null
    sessionId: string
}

function PaperCard({ paper, onClick }: { paper: Paper, onClick: () => void }) {
    return (
        <div
            onClick={onClick}
            className="bg-gray-700 rounded-lg p-4 border border-gray-600 hover:border-blue-500 transition-all cursor-pointer hover:shadow-lg hover:-translate-y-1"
        >
            <div className="flex justify-between items-start mb-2">
                <h4 className="font-semibold text-white text-sm flex-1 pr-2">{paper.title}</h4>
                <span className="text-blue-400 font-bold text-sm">{paper.citation_count} 引用</span>
            </div>
            <p className="text-gray-400 text-xs mb-2">
                {paper.authors?.slice(0, 3).join(', ')}{paper.authors && paper.authors.length > 3 && ' et al.'} · {paper.year}
            </p>
            <p className="text-gray-300 text-xs line-clamp-2 mb-3">{paper.abstract?.substring(0, 150)}...</p>
            <div className="flex gap-2">
                <a
                    href={paper.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded transition-colors"
                    onClick={(e) => e.stopPropagation()}
                >
                    🔗 查看详情
                </a>
                <a
                    href={paper.pdf_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-xs rounded transition-colors"
                    onClick={(e) => e.stopPropagation()}
                >
                    📄 PDF
                </a>
            </div>
        </div>
    )
}

function PDFViewer({ paper, onClose }: { paper: Paper, onClose: () => void }) {
    return (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4" onClick={onClose}>
            <div className="bg-gray-800 rounded-xl w-full max-w-6xl h-[90vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
                <div className="p-4 border-b border-gray-700 flex justify-between items-center">
                    <div>
                        <h3 className="text-white font-semibold">{paper.title}</h3>
                        <p className="text-gray-400 text-sm">{paper.authors?.join(', ')}</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-700 rounded-lg text-gray-400"
                    >
                        ✕
                    </button>
                </div>
                <div className="flex-1 bg-white">
                    <iframe
                        src={paper.pdf_url}
                        className="w-full h-full"
                        title={paper.title}
                    />
                </div>
            </div>
        </div>
    )
}

function downloadReportAsText(result: ResearchResult) {
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

function downloadReportAsMarkdown(result: ResearchResult) {
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

function downloadReportAsHTML(result: ResearchResult) {
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

function renderPapers(papers: Paper[], onPaperClick: (paper: Paper) => void) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
            {papers.map((paper, idx) => (
                <div
                    key={paper.paper_id || idx}
                    className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => onPaperClick(paper)}
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
                                    onClick={(e) => { e.stopPropagation(); }}
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
}

function ResearchResultDisplay({ result, onPaperClick }: { result: ResearchResult, onPaperClick: (paper: Paper) => void }) {
    return (
        <div className="space-y-6">
            {result.report && (
                <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 shadow-lg">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-xl font-bold text-white flex items-center gap-2">
                            📝 {result.report.title}
                        </h3>
                        <div className="flex gap-2">
                            <button
                                onClick={() => downloadReportAsText(result)}
                                className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors"
                            >
                                📄 TXT
                            </button>
                            <button
                                onClick={() => downloadReportAsMarkdown(result)}
                                className="px-3 py-1 text-sm bg-blue-900/30 hover:bg-blue-900/50 text-blue-300 rounded transition-colors"
                            >
                                📝 MD
                            </button>
                            <button
                                onClick={() => downloadReportAsHTML(result)}
                                className="px-3 py-1 text-sm bg-green-900/30 hover:bg-green-900/50 text-green-300 rounded transition-colors"
                            >
                                🌐 HTML
                            </button>
                        </div>
                    </div>

                    {result.report.sections?.map((section, idx) => (
                        <div key={idx} className="mb-6">
                            <h4 className="text-lg font-bold text-gray-200 mb-2 border-b border-gray-700 pb-1">
                                {section.title}
                            </h4>
                            <p className="text-gray-400 whitespace-pre-wrap leading-relaxed">
                                {section.content}
                            </p>

                            {section.key_findings && section.key_findings.length > 0 && (
                                <div className="mt-3 space-y-2">
                                    {section.key_findings.map((finding, i) => (
                                        <div key={i} className="p-3 bg-gray-700 rounded text-sm">
                                            <span className="text-gray-300">
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

            {result.clusters && result.clusters.length > 0 && (
                <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 shadow-lg">
                    <h4 className="text-lg font-bold text-gray-200 mb-4">
                        🗂️ 研究方向 ({result.clusters.length} 个)
                    </h4>
                    <div className="space-y-4">
                        {result.clusters.map((cluster, clusterIdx) => (
                            <div key={clusterIdx} className="bg-gray-700 p-4 rounded-lg border border-gray-600">
                                <div className="flex items-center justify-between mb-3">
                                    <h5 className="font-bold text-white">
                                        {cluster.name}
                                    </h5>
                                    <span className="px-3 py-1 bg-blue-900/30 text-blue-300 rounded-full text-sm">
                                        {cluster.paper_count} 篇论文
                                    </span>
                                </div>
                                <div className="flex flex-wrap gap-2 mb-3">
                                    {cluster.keywords?.slice(0, 5).map((kw, i) => (
                                        <span key={i} className="px-2 py-1 bg-gray-600 text-gray-300 rounded text-xs">
                                            {kw}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {result.cross_points && result.cross_points.length > 0 && (
                <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 shadow-lg">
                    <h4 className="text-lg font-bold text-gray-200 mb-4">
                        🔗 研究交叉点 ({result.cross_points.length} 个)
                    </h4>
                    <div className="bg-gradient-to-r from-purple-900/20 to-blue-900/20 p-4 rounded-lg border border-purple-700">
                        {result.cross_points.map((cp, cpIdx) => (
                            <div key={cpIdx} className="mb-3 p-3 bg-gray-700 rounded-lg last:mb-0">
                                <div className="font-medium text-white mb-1">
                                    {cp.name}
                                </div>
                                <p className="text-sm text-gray-400">
                                    {cp.description}
                                </p>
                                <div className="mt-2 flex flex-wrap gap-1">
                                    {cp.related_clusters?.map((rc, i) => (
                                        <span key={i} className="px-2 py-0.5 bg-purple-900/30 text-purple-300 rounded text-xs">
                                            {rc}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {result.papers && result.papers.length > 0 && (
                <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 shadow-lg">
                    <h4 className="text-lg font-bold text-gray-200 mb-4">
                        📄 检索结果 ({result.papers.length} 篇论文)
                    </h4>
                    {renderPapers(result.papers.slice(0, 8), onPaperClick)}
                    {result.papers.length > 8 && (
                        <p className="text-center text-gray-500 mt-2 text-sm">
                            ... 还有 {result.papers.length - 8} 篇论文
                        </p>
                    )}
                </div>
            )}
        </div>
    )
}

function StepOutput({ output, onPaperClick }: { output: any, onPaperClick: (paper: Paper) => void }) {
    if (!output) return null

    const { output_type } = output

    if (output_type === 'research_papers' || output_type === 'research_analysis') {
        const papers = output.papers || []
        return (
            <div className="mt-4">
                <h4 className="text-lg font-bold text-gray-200 mb-3">
                    📄 论文列表 ({papers.length} 篇)
                </h4>
                {renderPapers(papers.slice(0, 8), onPaperClick)}
                {papers.length > 8 && (
                    <p className="text-center text-gray-500 mt-2 text-sm">
                        ... 还有 {papers.length - 8} 篇论文
                    </p>
                )}
            </div>
        )
    }

    if (output_type === 'research_clusters') {
        const clusters = output.clusters || []
        return (
            <div className="mt-4">
                <h4 className="text-lg font-bold text-gray-200 mb-3">
                    🗂️ 研究方向 ({clusters.length} 个)
                </h4>
                <div className="space-y-4">
                    {clusters.map((cluster: Cluster, clusterIdx: number) => (
                        <div key={clusterIdx} className="bg-gray-700 p-4 rounded-lg border border-gray-600">
                            <div className="flex items-center justify-between mb-3">
                                <h5 className="font-bold text-white">
                                    {cluster.name}
                                </h5>
                                <span className="px-3 py-1 bg-blue-900/30 text-blue-300 rounded-full text-sm">
                                    {cluster.paper_count} 篇论文
                                </span>
                            </div>
                            <div className="flex flex-wrap gap-2 mb-3">
                                {cluster.keywords?.slice(0, 5).map((kw: string, i: number) => (
                                    <span key={i} className="px-2 py-1 bg-gray-600 text-gray-300 rounded text-xs">
                                        {kw}
                                    </span>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        )
    }

    if (output_type === 'research_crosspoints') {
        const crossPoints = output.cross_points || []
        return (
            <div className="mt-4">
                <h4 className="text-lg font-bold text-gray-200 mb-3">
                    🔗 研究交叉点 ({crossPoints.length} 个)
                </h4>
                {crossPoints.length > 0 ? (
                    <div className="bg-gradient-to-r from-purple-900/20 to-blue-900/20 p-4 rounded-lg border border-purple-700">
                        {crossPoints.map((cp: CrossPoint, cpIdx: number) => (
                            <div key={cpIdx} className="mb-3 p-3 bg-gray-700 rounded-lg last:mb-0">
                                <div className="font-medium text-white mb-1">
                                    {cp.name}
                                </div>
                                <p className="text-sm text-gray-400">
                                    {cp.description}
                                </p>
                                <div className="mt-2 flex flex-wrap gap-1">
                                    {cp.related_clusters?.map((rc: string, i: number) => (
                                        <span key={i} className="px-2 py-0.5 bg-purple-900/30 text-purple-300 rounded text-xs">
                                            {rc}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p className="text-gray-500 text-sm">未发现明显的研究交叉点</p>
                )}
            </div>
        )
    }

    if (output_type === 'research_report') {
        const report = output.report
        return (
            <div className="mt-4">
                {report && (
                    <div className="bg-gray-700 rounded-xl p-6 border border-gray-600">
                        <div className="flex items-center justify-between mb-4">
                            <h4 className="text-xl font-bold text-white flex items-center gap-2">
                                📝 {report.title}
                            </h4>
                        </div>

                        {report.sections?.map((section: ReportSection, idx: number) => (
                            <div key={idx} className="mb-6">
                                <h5 className="text-lg font-bold text-gray-200 mb-2 border-b border-gray-600 pb-1">
                                    {section.title}
                                </h5>
                                <p className="text-gray-400 whitespace-pre-wrap leading-relaxed">
                                    {section.content}
                                </p>

                                {section.key_findings && section.key_findings.length > 0 && (
                                    <div className="mt-3 space-y-2">
                                        {section.key_findings.map((finding: any, i: number) => (
                                            <div key={i} className="p-3 bg-gray-600 rounded text-sm">
                                                <span className="text-gray-300">
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
        )
    }

    if (output_type === 'paper_list') {
        const papers = output.papers || []
        return (
            <div className="mt-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {papers.map((paper: Paper) => (
                        <PaperCard key={paper.paper_id} paper={paper} onClick={() => onPaperClick(paper)} />
                    ))}
                </div>
            </div>
        )
    }

    if (output_type === 'analysis') {
        const analysis = output.analysis
        return (
            <div className="mt-4 bg-blue-900/30 rounded-lg p-5 border border-blue-700">
                <div className="space-y-3">
                    {analysis.key_topics && (
                        <div>
                            <span className="text-blue-300 font-medium">🔑 关键主题：</span>
                            <span className="text-gray-300 ml-2">{analysis.key_topics.join('、')}</span>
                        </div>
                    )}
                    {analysis.trends && (
                        <div>
                            <span className="text-blue-300 font-medium">📈 研究趋势：</span>
                            <span className="text-gray-300 ml-2">{analysis.trends}</span>
                        </div>
                    )}
                    {analysis.methods && (
                        <div>
                            <span className="text-blue-300 font-medium">🛠️ 主要方法：</span>
                            <span className="text-gray-300 ml-2">{analysis.methods.join('、')}</span>
                        </div>
                    )}
                    {analysis.summary && (
                        <div>
                            <span className="text-blue-300 font-medium">📝 总结：</span>
                            <span className="text-gray-300 ml-2">{analysis.summary}</span>
                        </div>
                    )}
                </div>
            </div>
        )
    }

    if (output_type === 'report') {
        return (
            <div className="mt-4 bg-gray-700 rounded-lg p-5 border border-gray-600">
                <div className="text-gray-200 whitespace-pre-wrap text-sm leading-relaxed">{output.report}</div>
            </div>
        )
    }

    if (output_type === 'schedule_info') {
        const info = output.schedule_info
        return (
            <div className="mt-4 bg-green-900/30 rounded-lg p-5 border border-green-700">
                <div className="space-y-2">
                    <div className="text-green-300 font-medium text-lg">{info.title}</div>
                    {info.date && <div className="text-gray-300">📅 日期：{info.date}</div>}
                    {info.time && <div className="text-gray-300">⏰ 时间：{info.time}</div>}
                    {info.participants && info.participants.length > 0 && <div className="text-gray-300">👥 参与者：{info.participants.join('、')}</div>}
                    {info.location && <div className="text-gray-300">📍 地点：{info.location}</div>}
                    {info.description && <div className="text-gray-300">📝 描述：{info.description}</div>}
                </div>
            </div>
        )
    }

    if (output_type === 'schedule') {
        const schedule = output.schedule
        return (
            <div className="mt-4 bg-green-900/30 rounded-lg p-5 border border-green-700">
                <div className="flex items-center gap-3 mb-4">
                    <span className="text-3xl">📅</span>
                    <span className="text-green-300 font-semibold text-xl">{schedule.title}</span>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                    <div className="text-gray-300">🗓️ 日期：{schedule.date}</div>
                    <div className="text-gray-300">⏰ 时间：{schedule.time}</div>
                    <div className="text-gray-300">📍 地点：{schedule.location}</div>
                    <div className="text-gray-300">🆔 ID：{schedule.id}</div>
                </div>
                {schedule.participants && schedule.participants.length > 0 && (
                    <div className="mt-4 text-gray-300 text-sm">
                        👥 参与者：{schedule.participants.join('、')}
                    </div>
                )}
                {schedule.description && (
                    <div className="mt-4 text-gray-300 text-sm">
                        📝 {schedule.description}
                    </div>
                )}
            </div>
        )
    }

    if (output_type === 'statistics') {
        const stats = output.statistics
        return (
            <div className="mt-4 bg-purple-900/30 rounded-lg p-5 border border-purple-700">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
                    <div className="text-center">
                        <div className="text-purple-300 text-sm mb-1">📊 总样本</div>
                        <div className="text-white text-3xl font-bold">{stats.total_samples}</div>
                    </div>
                    <div className="text-center">
                        <div className="text-purple-300 text-sm mb-1">📈 实验组</div>
                        <div className="text-white text-3xl font-bold">{stats.groups}</div>
                    </div>
                    <div className="text-center">
                        <div className="text-purple-300 text-sm mb-1">🎯 平均准确率</div>
                        <div className="text-white text-3xl font-bold">{(stats.mean_accuracy * 100).toFixed(1)}%</div>
                    </div>
                    <div className="text-center">
                        <div className="text-purple-300 text-sm mb-1">🏆 最佳组</div>
                        <div className="text-white text-3xl font-bold">{stats.best_group}</div>
                    </div>
                </div>
                {stats.summary && (
                    <div className="mt-5 text-gray-300 text-sm">
                        📝 {stats.summary}
                    </div>
                )}
            </div>
        )
    }

    if (output_type === 'data_preview') {
        const preview = output.data_preview
        return (
            <div className="mt-4 bg-gray-700 rounded-lg p-5 border border-gray-600 overflow-x-auto">
                <div className="text-gray-300 text-sm mb-3">📊 数据预览 ({preview.rows} 行)</div>
                <table className="w-full text-xs">
                    <thead>
                        <tr className="border-b border-gray-600">
                            {preview.columns.map((col: string, i: number) => (
                                <th key={i} className="text-left text-gray-400 p-3 font-semibold">{col}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {preview.sample.map((row: string[], i: number) => (
                            <tr key={i} className="border-b border-gray-700 hover:bg-gray-600">
                                {row.map((cell, j) => (
                                    <td key={j} className="text-gray-300 p-3">{cell}</td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        )
    }

    if (output_type === 'answer') {
        return (
            <div className="mt-4 bg-blue-900/30 rounded-lg p-5 border border-blue-700">
                <div className="text-gray-200 whitespace-pre-wrap leading-relaxed">{output.answer}</div>
            </div>
        )
    }

    if (output_type === 'references') {
        const references = output.references || []
        return (
            <div className="mt-4">
                <h4 className="text-gray-300 mb-3 font-medium">📚 参考资料</h4>
                {references.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {references.map((paper: Paper) => (
                            <PaperCard key={paper.paper_id} paper={paper} onClick={() => onPaperClick(paper)} />
                        ))}
                    </div>
                ) : (
                    <p className="text-gray-500">暂无参考资料</p>
                )}
            </div>
        )
    }

    if (output_type === 'charts') {
        const charts = output.charts || []
        return (
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-5">
                {charts.map((chart: any, i: number) => (
                    <div key={i} className="bg-gray-700 rounded-lg p-5 border border-gray-600">
                        <div className="text-gray-300 text-sm mb-3 font-medium">{chart.title}</div>
                        <div className="h-32 bg-gray-800 rounded flex items-center justify-center text-gray-500">
                            📊 图表区域
                        </div>
                    </div>
                ))}
            </div>
        )
    }

    if (output_type === 'result') {
        return (
            <div className="mt-4 bg-gray-700 rounded-lg p-5 border border-gray-600">
                <div className="text-gray-200 whitespace-pre-wrap">{output.result}</div>
            </div>
        )
    }

    return (
        <div className="mt-4 text-gray-400 text-sm">
            {output.result || '步骤完成'}
        </div>
    )
}

interface AgentStep {
    step_type: string
    content: string
    timestamp: string
}

interface TaskStep {
    task_id: string
    step_type: string
    content: string
    timestamp: string
}

export function UnifiedAssistant() {
    const [task, setTask] = useState('')
    const [loading, setLoading] = useState(false)
    const [progress, setProgress] = useState<Progress | null>(null)
    const [tasks, setTasks] = useState<PlanTask[]>([])
    const [stepOutputs, setStepOutputs] = useState<Record<string, any>>({})
    const [error, setError] = useState<string | null>(null)
    const [result, setResult] = useState<any>(null)
    const [taskType, setTaskType] = useState<string | null>(null)
    const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
    const [refreshTrigger, setRefreshTrigger] = useState(0)
    const [showSidebar, setShowSidebar] = useState(true)
    const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set())
    const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null)
    const [agentSteps, setAgentSteps] = useState<AgentStep[]>([])
    const [taskSteps, setTaskSteps] = useState<Record<string, TaskStep[]>>({})
    const [streamingContent, setStreamingContent] = useState<string>("")
    const wsRef = useRef<WebSocket | null>(null)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const stepOutputsRef = useRef<Record<string, any>>({})

    const [conversation, setConversation] = useState<ConversationContext>({
        messages: [],
        currentPapers: [],
        selectedPaperIndex: null,
        sessionId: Date.now().toString()
    })
    const [currentMessageId, setCurrentMessageId] = useState<string | null>(null)

    useEffect(() => {
        return () => {
            if (wsRef.current) {
                wsRef.current.close()
            }
        }
    }, [])

    useEffect(() => {
        stepOutputsRef.current = stepOutputs
    }, [stepOutputs])

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [tasks, stepOutputs, progress, expandedSteps])

    const toggleStepExpansion = (stepId: string) => {
        const newExpanded = new Set(expandedSteps)
        if (newExpanded.has(stepId)) {
            newExpanded.delete(stepId)
        } else {
            newExpanded.add(stepId)
        }
        setExpandedSteps(newExpanded)
    }

    const saveTask = async (taskId: string, taskText: string, taskTypeValue: string, answer: string, plan: PlanTask[]) => {
        try {
            await fetch('http://localhost:8000/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    task_id: taskId,
                    task: taskText,
                    answer: answer,
                    steps: [],
                    task_type: taskTypeValue,
                    plan: plan
                })
            })
            setRefreshTrigger(prev => prev + 1)
        } catch (e) {
            console.error('Failed to save task:', e)
        }
    }

    const loadTask = async (taskId: string) => {
        try {
            const response = await fetch(`http://localhost:8000/tasks/${taskId}`)
            const data = await response.json()
            if (data.success && data.task) {
                const savedTask: SavedTask = data.task
                setTask(savedTask.task)
                setTaskType(savedTask.task_type || null)
                setResult({
                    final_answer: savedTask.answer,
                    plan: savedTask.plan || []
                })
                setTasks(savedTask.plan || [])
                setCurrentTaskId(taskId)

                if (savedTask.plan) {
                    const newExpanded = new Set<string>()
                    savedTask.plan.forEach((t: PlanTask) => {
                        if (t.output) {
                            newExpanded.add(t.task_id)
                        }
                    })
                    setExpandedSteps(newExpanded)
                }
            }
        } catch (e) {
            console.error('Failed to load task:', e)
        }
    }

    const startTask = async () => {
        if (!task.trim() || loading) return

        const userMessageId = Date.now().toString()
        const userMessage: ConversationMessage = {
            id: userMessageId,
            role: 'user',
            content: task.trim(),
            timestamp: new Date().toISOString()
        }

        setConversation(prev => ({
            ...prev,
            messages: [...prev.messages, userMessage]
        }))

        setLoading(true)
        setError(null)
        setResult(null)
        setTasks([])
        setStepOutputs({})
        setProgress(null)
        setTaskType(null)
        setCurrentTaskId(null)
        setExpandedSteps(new Set())
        setAgentSteps([])
        setTaskSteps({})
        setStreamingContent('')
        setCurrentMessageId(userMessageId)

        try {
            const wsUrl = 'ws://localhost:8000/ws/planning'
            console.log('Connecting to:', wsUrl)

            const ws = new WebSocket(wsUrl)
            wsRef.current = ws

            ws.onopen = () => {
                console.log('WebSocket connected')
                ws.send(JSON.stringify({
                    type: 'start_planning',
                    task: task.trim(),
                    context: {
                        messages: conversation.messages.slice(-10),
                        currentPapers: conversation.currentPapers,
                        selectedPaperIndex: conversation.selectedPaperIndex,
                        sessionId: conversation.sessionId
                    }
                }))
            }

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data)
                console.log('WebSocket message received:', data.type)
                if (data.type === 'progress') {
                    setProgress(data)
                } else if (data.type === 'stream') {
                    setStreamingContent(data.full_content || '')
                } else if (data.type === 'step') {
                    setAgentSteps(prev => [...prev, {
                        step_type: data.step_type,
                        content: data.content,
                        timestamp: data.timestamp
                    }])
                } else if (data.type === 'task_step') {
                    setTaskSteps(prev => {
                        const taskId = data.task_id
                        return {
                            ...prev,
                            [taskId]: [...(prev[taskId] || []), {
                                task_id: taskId,
                                step_type: data.step_type,
                                content: data.content,
                                timestamp: data.timestamp
                            }]
                        }
                    })
                } else if (data.type === 'task_list') {
                    setTasks(data.tasks.map((t: any) => ({
                        ...t,
                        output: null
                    })))
                } else if (data.type === 'task_update') {
                    setTasks(prev => prev.map(t =>
                        t.task_id === data.task_id
                            ? { ...t, status: data.status }
                            : t
                    ))
                } else if (data.type === 'step_output') {
                    setStepOutputs(prev => ({
                        ...prev,
                        [data.task_id]: data.output
                    }))
                    setTasks(prev => prev.map(t =>
                        t.task_id === data.task_id
                            ? { ...t, output: data.output }
                            : t
                    ))
                    setExpandedSteps(prev => {
                        const newSet = new Set(prev)
                        newSet.add(data.task_id)
                        return newSet
                    })

                    if (data.output?.papers) {
                        setConversation(prev => ({
                            ...prev,
                            currentPapers: data.output.papers
                        }))
                    }
                } else if (data.type === 'complete') {
                    const res = data.result
                    setResult(res)
                    if (res.task_type) {
                        setTaskType(res.task_type)
                    }
                    setLoading(false)
                    setStreamingContent('')

                    const planWithOutputs = res.plan ? res.plan.map((t: any) => ({
                        ...t,
                        output: stepOutputsRef.current[t.task_id] || t.output
                    })) : []

                    const assistantMessage: ConversationMessage = {
                        id: Date.now().toString(),
                        role: 'assistant',
                        content: res.final_answer || '任务完成',
                        timestamp: new Date().toISOString(),
                        result: res,
                        papers: res.research_result?.papers || res.extracted_params?.papers,
                        plan: planWithOutputs,
                        taskType: res.task_type
                    }

                    setConversation(prev => ({
                        ...prev,
                        messages: [...prev.messages, assistantMessage]
                    }))

                    const taskId = Date.now().toString()
                    setCurrentTaskId(taskId)
                    saveTask(taskId, task.trim(), res.task_type, res.final_answer, res.plan)

                    setTask('')
                    ws.close()
                } else if (data.type === 'error') {
                    setError(data.error)
                    setLoading(false)
                    ws.close()
                }
            }

            ws.onerror = (event) => {
                console.error('[WS] Error:', event)
                setError('WebSocket连接失败，请检查后端服务是否启动 (端口 8000)')
                setLoading(false)
            }

            ws.onclose = (event) => {
                console.log('[WS] Closed:', event.code, event.reason, event.wasClean)
                if (event.code === 1005 && loading) {
                    setError('连接异常关闭，请检查后端日志')
                    setLoading(false)
                }
            }

        } catch (e: any) {
            console.error('[WS] Exception:', e)
            setError(e.message || '连接错误')
            setLoading(false)
        }
    }

    const clearConversation = () => {
        setConversation({
            messages: [],
            currentPapers: [],
            selectedPaperIndex: null,
            sessionId: Date.now().toString()
        })
        setTask('')
        setResult(null)
        setTasks([])
        setTaskType(null)
        setError(null)
    }

    const selectPaperFromHistory = (messageIndex: number, paperIndex: number) => {
        const msg = conversation.messages[messageIndex]
        if (msg?.papers && msg.papers[paperIndex]) {
            setConversation(prev => ({
                ...prev,
                selectedPaperIndex: paperIndex
            }))
            setSelectedPaper(msg.papers[paperIndex])
        }
    }

    const getTaskTypeLabel = (type: string | null) => {
        const labels: Record<string, string> = {
            'literature_research': '📚 文献调研',
            'schedule_planning': '📅 日程规划',
            'experiment_management': '🧪 实验管理',
            'question_answering': '❓ 问题解答',
            'general': '🔧 通用任务'
        }
        return type ? labels[type] || type : null
    }

    return (
        <div className="h-full flex bg-gray-900">
            {showSidebar && (
                <HistorySidebar
                    onSelectTask={loadTask}
                    selectedTaskId={currentTaskId || undefined}
                    refreshTrigger={refreshTrigger}
                />
            )}

            <div className="flex-1 flex flex-col h-full overflow-hidden">
                <div className="p-3 border-b border-gray-700 flex items-center justify-between bg-gray-800">
                    <button
                        onClick={() => setShowSidebar(!showSidebar)}
                        className="p-2 rounded-lg hover:bg-gray-700 text-gray-400 transition-colors"
                    >
                        {showSidebar ? '◀' : '▶'}
                    </button>
                    <h1 className="text-lg font-bold text-white">🤖 智能学术助手</h1>
                    <button
                        onClick={clearConversation}
                        className="p-2 rounded-lg hover:bg-gray-700 text-gray-400 transition-colors"
                        title="清空对话"
                    >
                        🗑️
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-6">
                    <div className="w-full max-w-4xl mx-auto">
                        {conversation.messages.map((msg, msgIdx) => (
                            <div key={msg.id} className={`mb-4 ${msg.role === 'user' ? 'flex justify-end' : ''}`}>
                                {msg.role === 'user' ? (
                                    <div className="max-w-[80%] bg-blue-600 rounded-2xl rounded-tr-sm px-4 py-3">
                                        <p className="text-white text-sm">{msg.content}</p>
                                    </div>
                                ) : (
                                    <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden w-full">
                                        <div className="p-3 border-b border-gray-700 bg-gray-800/50 flex items-center gap-2">
                                            <span className="text-lg">🤖</span>
                                            <span className="text-gray-300 font-medium text-sm">智能助手</span>
                                            {msg.taskType && (
                                                <span className="px-2 py-0.5 bg-blue-900/30 text-blue-300 rounded text-xs">
                                                    {getTaskTypeLabel(msg.taskType)}
                                                </span>
                                            )}
                                        </div>

                                        {msg.papers && msg.papers.length > 0 && (
                                            <div className="p-3 border-b border-gray-700">
                                                <h4 className="text-xs font-medium text-gray-400 mb-2">
                                                    📄 相关论文 ({msg.papers.length} 篇)
                                                </h4>
                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                                    {msg.papers.slice(0, 4).map((paper, paperIdx) => (
                                                        <div
                                                            key={paper.paper_id || paperIdx}
                                                            className="bg-gray-700 p-2 rounded border border-gray-600 hover:border-blue-500 cursor-pointer transition-all"
                                                            onClick={() => {
                                                                selectPaperFromHistory(msgIdx, paperIdx)
                                                                setSelectedPaper(paper)
                                                            }}
                                                        >
                                                            <div className="flex justify-between items-start mb-1">
                                                                <span className="text-xs text-gray-500">#{paperIdx + 1}</span>
                                                                <span className="text-xs text-blue-400">{paper.citation_count} 引用</span>
                                                            </div>
                                                            <h5 className="text-xs text-white font-medium line-clamp-2">
                                                                {paper.title}
                                                            </h5>
                                                        </div>
                                                    ))}
                                                </div>
                                                {msg.papers.length > 4 && (
                                                    <p className="text-center text-gray-500 text-xs mt-2">
                                                        还有 {msg.papers.length - 4} 篇...
                                                    </p>
                                                )}
                                            </div>
                                        )}

                                        {msg.plan && msg.plan.length > 0 && (
                                            <div className="p-3 border-b border-gray-700">
                                                <div className="space-y-2">
                                                    {msg.plan.map((step, stepIdx) => (
                                                        <div key={step.task_id || stepIdx} className="bg-gray-700/50 rounded-lg overflow-hidden">
                                                            <div
                                                                className={`p-2 flex items-center justify-between cursor-pointer ${step.output ? 'hover:bg-gray-700' : ''}`}
                                                                onClick={() => step.output && toggleStepExpansion(step.task_id)}
                                                            >
                                                                <div className="flex items-center gap-2">
                                                                    <span className={`text-lg ${step.status === 'completed' ? 'text-green-400' :
                                                                        step.status === 'in_progress' ? 'text-yellow-400' :
                                                                            'text-gray-500'
                                                                        }`}>
                                                                        {step.status === 'completed' ? '✅' : step.status === 'in_progress' ? '🔄' : '⭕'}
                                                                    </span>
                                                                    <span className={`text-sm ${step.status === 'completed' ? 'text-green-300' :
                                                                        step.status === 'in_progress' ? 'text-yellow-300' :
                                                                            'text-gray-400'
                                                                        }`}>
                                                                        {step.name}
                                                                    </span>
                                                                </div>
                                                                {step.output && (
                                                                    <span className={`text-gray-400 text-xs transition-transform ${expandedSteps.has(step.task_id) ? 'rotate-180' : ''}`}>
                                                                        ▼
                                                                    </span>
                                                                )}
                                                            </div>

                                                            {expandedSteps.has(step.task_id) && step.output && (
                                                                <div className="p-3 border-t border-gray-600 bg-gray-700/30">
                                                                    {step.output.papers && step.output.papers.length > 0 && (
                                                                        <div>
                                                                            <h5 className="text-xs font-medium text-gray-400 mb-2">
                                                                                📄 找到 {step.output.papers.length} 篇论文
                                                                            </h5>
                                                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                                                                {step.output.papers.slice(0, 4).map((paper: Paper, paperIdx: number) => (
                                                                                    <div
                                                                                        key={paper.paper_id || paperIdx}
                                                                                        className="bg-gray-800 p-2 rounded border border-gray-600 hover:border-blue-500 cursor-pointer transition-all"
                                                                                        onClick={() => {
                                                                                            selectPaperFromHistory(msgIdx, paperIdx)
                                                                                            setSelectedPaper(paper)
                                                                                        }}
                                                                                    >
                                                                                        <div className="flex justify-between items-start mb-1">
                                                                                            <span className="text-xs text-gray-500">#{paperIdx + 1}</span>
                                                                                            <span className="text-xs text-blue-400">{paper.citation_count} 引用</span>
                                                                                        </div>
                                                                                        <h6 className="text-xs text-white font-medium line-clamp-2">
                                                                                            {paper.title}
                                                                                        </h6>
                                                                                    </div>
                                                                                ))}
                                                                            </div>
                                                                            {step.output.papers.length > 4 && (
                                                                                <p className="text-center text-gray-500 text-xs mt-2">
                                                                                    还有 {step.output.papers.length - 4} 篇...
                                                                                </p>
                                                                            )}
                                                                        </div>
                                                                    )}

                                                                    {step.output.analysis && (
                                                                        <div>
                                                                            <h5 className="text-xs font-medium text-gray-400 mb-2">
                                                                                📊 分析结果
                                                                            </h5>
                                                                            <div className="text-xs text-gray-300 whitespace-pre-wrap">
                                                                                {typeof step.output.analysis === 'string'
                                                                                    ? step.output.analysis
                                                                                    : JSON.stringify(step.output.analysis, null, 2)}
                                                                            </div>
                                                                        </div>
                                                                    )}

                                                                    {step.output.report && (
                                                                        <div>
                                                                            <h5 className="text-xs font-medium text-gray-400 mb-2">
                                                                                📝 报告
                                                                            </h5>
                                                                            <div className="text-xs text-gray-300 whitespace-pre-wrap">
                                                                                {step.output.report}
                                                                            </div>
                                                                        </div>
                                                                    )}

                                                                    {step.output.answer && (
                                                                        <div>
                                                                            <h5 className="text-xs font-medium text-gray-400 mb-2">
                                                                                💡 答案
                                                                            </h5>
                                                                            <div className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed">
                                                                                {step.output.answer}
                                                                            </div>
                                                                        </div>
                                                                    )}

                                                                    {step.output.result && !step.output.papers && !step.output.analysis && !step.output.report && !step.output.answer && (
                                                                        <div className="text-xs text-gray-300">
                                                                            {step.output.result}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            )}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        <div className="p-3">
                                            <p className="text-gray-300 text-sm whitespace-pre-wrap">{msg.content}</p>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}

                        {loading && (
                            <div className="mb-4">
                                <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
                                    <div className="p-3 border-b border-gray-700 bg-gray-800/50 flex items-center gap-2">
                                        <span className="text-lg">🤖</span>
                                        <span className="text-gray-300 font-medium text-sm">智能助手</span>
                                        <span className="px-2 py-0.5 bg-yellow-900/30 text-yellow-300 rounded text-xs animate-pulse">
                                            处理中...
                                        </span>
                                    </div>

                                    {progress && (
                                        <div className="p-3 border-b border-gray-700">
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-xs text-blue-300">
                                                    {(() => {
                                                        const labels: Record<string, string> = {
                                                            'planning': '📋 规划任务',
                                                            'executing': '⚡ 执行中',
                                                            'completed': '✅ 完成',
                                                            'error': '❌ 错误'
                                                        }
                                                        return labels[progress.state] || progress.state
                                                    })()}
                                                </span>
                                                <span className="text-blue-400 font-bold text-xs">
                                                    {progress.progress}%
                                                </span>
                                            </div>
                                            <div className="w-full bg-gray-700 rounded-full h-1.5 overflow-hidden">
                                                <div
                                                    className="bg-gradient-to-r from-blue-500 to-blue-400 h-full rounded-full transition-all duration-300"
                                                    style={{ width: `${progress.progress}%` }}
                                                />
                                            </div>
                                            <p className="text-gray-400 text-xs mt-1">{progress.task}</p>
                                        </div>
                                    )}

                                    {streamingContent && (
                                        <div className="p-3 border-b border-gray-700">
                                            <h5 className="text-xs font-medium text-gray-400 mb-2">💡 正在生成回答...</h5>
                                            <div className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed">
                                                {streamingContent}
                                                <span className="animate-pulse">▌</span>
                                            </div>
                                        </div>
                                    )}

                                    {tasks.length > 0 && (
                                        <div className="p-3">
                                            <div className="flex flex-wrap gap-2">
                                                {tasks.map((t, idx) => (
                                                    <span key={t.task_id} className={`px-2 py-1 rounded text-xs ${t.status === 'completed' ? 'bg-green-900/30 text-green-300' :
                                                        t.status === 'in_progress' ? 'bg-yellow-900/30 text-yellow-300 animate-pulse' :
                                                            'bg-gray-700 text-gray-400'
                                                        }`}>
                                                        {t.status === 'completed' ? '✅' : t.status === 'in_progress' ? '🔄' : '⭕'} {t.name}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {agentSteps.length > 0 && (
                                        <div className="p-3 border-b border-gray-700">
                                            <h5 className="text-xs font-medium text-gray-400 mb-2">🔍 执行过程</h5>
                                            <div className="space-y-1">
                                                {agentSteps.map((step, idx) => (
                                                    <div key={idx} className="text-xs text-gray-300 flex gap-2">
                                                        <span className="text-blue-400 font-medium">{step.step_type === 'thought' ? '💭' : '📝'}</span>
                                                        <span>{step.content}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {tasks.length > 0 && (
                                        <div className="p-3 border-b border-gray-700">
                                            <div className="space-y-2">
                                                {tasks.map((t, idx) => {
                                                    const stepDetails = taskSteps[t.task_id] || []
                                                    return (
                                                        <div key={t.task_id} className="bg-gray-700/50 rounded-lg p-2">
                                                            <div className="flex items-center gap-2 mb-1">
                                                                <span className={`text-sm ${t.status === 'completed' ? 'text-green-400' :
                                                                    t.status === 'in_progress' ? 'text-yellow-400' :
                                                                        'text-gray-500'
                                                                    }`}>
                                                                    {t.status === 'completed' ? '✅' : t.status === 'in_progress' ? '🔄' : '⭕'}
                                                                </span>
                                                                <span className={`text-xs ${t.status === 'completed' ? 'text-green-300' :
                                                                    t.status === 'in_progress' ? 'text-yellow-300' :
                                                                        'text-gray-400'
                                                                    }`}>
                                                                    {t.name}
                                                                </span>
                                                            </div>
                                                            {stepDetails.length > 0 && (
                                                                <div className="ml-6 mt-1 space-y-1">
                                                                    {stepDetails.map((s, i) => (
                                                                        <div key={i} className="text-xs text-gray-400 flex gap-2">
                                                                            <span>{s.step_type === 'thought' ? '💭' : '📝'}</span>
                                                                            <span>{s.content}</span>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            )}
                                                        </div>
                                                    )
                                                })}
                                            </div>
                                        </div>
                                    )}

                                    {error && (
                                        <div className="p-3 bg-red-900/20 text-red-300 text-xs">
                                            ❌ {error}
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {conversation.messages.length === 0 && !loading && (
                            <div className="text-center py-16">
                                <div className="text-5xl mb-4">📚</div>
                                <h2 className="text-xl font-bold text-white mb-2">智能学术助手</h2>
                                <p className="text-gray-400 mb-6 text-sm">我可以帮你进行文献调研、论文分析、问题解答等</p>
                                <div className="flex flex-wrap justify-center gap-2">
                                    {['搜索AI医疗领域的论文', '分析这篇论文的核心贡献', '帮我找深度学习相关的综述'].map(example => (
                                        <button
                                            key={example}
                                            onClick={() => setTask(example)}
                                            className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-xs transition-colors border border-gray-700"
                                        >
                                            {example}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>
                </div>

                <div className="p-4 border-t border-gray-700 bg-gray-800">
                    <div className="w-full max-w-4xl mx-auto">
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={task}
                                onChange={(e) => setTask(e.target.value)}
                                placeholder="输入问题，如：搜索AI医疗领域的论文，或分析第3篇论文..."
                                className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                                disabled={loading}
                                onKeyPress={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault()
                                        startTask()
                                    }
                                }}
                            />
                            <button
                                onClick={startTask}
                                disabled={loading || !task.trim()}
                                className="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-lg font-medium text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {loading ? (
                                    <span className="animate-spin">⚡</span>
                                ) : (
                                    '发送'
                                )}
                            </button>
                        </div>
                        {conversation.currentPapers.length > 0 && (
                            <div className="mt-2 text-xs text-gray-500">
                                💡 当前有 {conversation.currentPapers.length} 篇论文，可以说"分析第N篇"或"找类似的论文"
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {selectedPaper && (
                <PDFViewer paper={selectedPaper} onClose={() => setSelectedPaper(null)} />
            )}
        </div>
    )
}