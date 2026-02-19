import { useState, useEffect } from 'react'
import { CitationGraph, KnowledgeGraph, TimelineView, AuthorNetwork } from './components/visualization'

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
    keywords?: string[]
    references?: string[]
    cited_by?: string[]
}

interface Cluster {
    name: string
    papers: Paper[]
    paper_count: number
    keywords: string[]
}

type ViewType = 'citation' | 'knowledge' | 'timeline' | 'author'

interface VisualizationDashboardProps {
    externalPapers?: Paper[]
    compact?: boolean
    defaultView?: ViewType
    onViewChange?: (view: ViewType) => void
}

export function VisualizationDashboard({ 
    externalPapers, 
    compact = false, 
    defaultView = 'timeline',
    onViewChange 
}: VisualizationDashboardProps) {
    const [papers, setPapers] = useState<Paper[]>([])
    const [clusters, setClusters] = useState<Cluster[]>([])
    const [loading, setLoading] = useState(true)
    const [activeView, setActiveView] = useState<ViewType>(defaultView)
    const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null)

    useEffect(() => {
        if (externalPapers && externalPapers.length > 0) {
            setPapers(externalPapers)
            generateMockClusters(externalPapers)
            setLoading(false)
        } else {
            loadVisualizationData()
        }
    }, [externalPapers])

    useEffect(() => {
        if (onViewChange) {
            onViewChange(activeView)
        }
    }, [activeView, onViewChange])

    const loadVisualizationData = async () => {
        setLoading(true)
        try {
            const papersRes = await fetch('http://localhost:8000/literature/papers?limit=100')
            const papersData = await papersRes.json()
            
            if (papersData.success && papersData.papers && papersData.papers.length > 0) {
                const formattedPapers: Paper[] = papersData.papers.map((p: any) => ({
                    paper_id: p.paper_id,
                    title: p.title,
                    authors: p.authors || [],
                    year: p.year || new Date().getFullYear(),
                    abstract: p.abstract || '',
                    url: p.url || '',
                    pdf_url: p.pdf_url || '',
                    source: p.source || 'Unknown',
                    citation_count: p.citation_count || Math.floor(Math.random() * 100),
                    keywords: p.keywords || [],
                    references: p.references || [],
                    cited_by: p.cited_by || []
                }))
                setPapers(formattedPapers)
                generateMockClusters(formattedPapers)
            } else {
                generateDemoData()
            }
        } catch (error) {
            console.error('Failed to load visualization data:', error)
            generateDemoData()
        } finally {
            setLoading(false)
        }
    }

    const generateMockClusters = (paperList: Paper[]) => {
        const clusterMap = new Map<string, Paper[]>()
        
        paperList.forEach(paper => {
            const keywords = paper.keywords || []
            if (keywords.length > 0) {
                const mainKeyword = keywords[0]
                if (!clusterMap.has(mainKeyword)) {
                    clusterMap.set(mainKeyword, [])
                }
                clusterMap.get(mainKeyword)!.push(paper)
            }
        })

        const mockClusters: Cluster[] = Array.from(clusterMap.entries())
            .filter(([_, papers]) => papers.length >= 1)
            .map(([name, papers], index) => ({
                name: name || `研究方向 ${index + 1}`,
                papers,
                paper_count: papers.length,
                keywords: [...new Set(papers.flatMap(p => p.keywords || []))].slice(0, 10)
            }))
            .slice(0, 10)

        setClusters(mockClusters)
    }

    const generateDemoData = () => {
        const demoPapers: Paper[] = []
        const topics = [
            'Deep Learning', 'Natural Language Processing', 'Computer Vision',
            'Reinforcement Learning', 'Graph Neural Networks', 'Transformer',
            'Attention Mechanism', 'Generative Models', 'Large Language Models',
            'Neural Architecture Search'
        ]
        
        const authors = [
            'Yann LeCun', 'Geoffrey Hinton', 'Yoshua Bengio', 'Andrew Ng',
            'Ian Goodfellow', 'Fei-Fei Li', 'Jitendra Malik', 'Pieter Abbeel',
            'Sergey Levine', 'Chelsea Finn', 'Percy Liang', 'Christopher Manning'
        ]

        for (let i = 0; i < 50; i++) {
            const year = 2019 + Math.floor(Math.random() * 6)
            const topic = topics[Math.floor(Math.random() * topics.length)]
            const authorCount = 2 + Math.floor(Math.random() * 4)
            const paperAuthors = []
            
            for (let j = 0; j < authorCount; j++) {
                paperAuthors.push(authors[Math.floor(Math.random() * authors.length)])
            }

            demoPapers.push({
                paper_id: `demo_${i}`,
                title: `${topic}: A Novel Approach to ${['Understanding', 'Improving', 'Analyzing', 'Optimizing'][Math.floor(Math.random() * 4)]} ${['Performance', 'Accuracy', 'Efficiency', 'Scalability'][Math.floor(Math.random() * 4)]}`,
                authors: [...new Set(paperAuthors)],
                year,
                abstract: `This paper presents a novel approach to ${topic.toLowerCase()}...`,
                url: `https://arxiv.org/abs/${2300 + i}`,
                pdf_url: `https://arxiv.org/pdf/${2300 + i}`,
                source: 'arXiv',
                citation_count: Math.floor(Math.random() * 200),
                keywords: [topic, ...topics.filter(t => t !== topic).slice(0, 2 + Math.floor(Math.random() * 3))]
            })
        }

        setPapers(demoPapers)

        const demoClusters: Cluster[] = topics.slice(0, 6).map((topic, index) => ({
            name: topic,
            papers: demoPapers.filter(p => p.keywords?.includes(topic)).slice(0, 10),
            paper_count: 5 + Math.floor(Math.random() * 15),
            keywords: [topic, ...topics.filter(t => t !== topic).slice(0, 4)]
        }))

        setClusters(demoClusters)
    }

    const views: { id: ViewType; label: string; icon: string }[] = [
        { id: 'timeline', label: '时间线', icon: '📅' },
        { id: 'citation', label: '引用图谱', icon: '📊' },
        { id: 'knowledge', label: '知识图谱', icon: '🧠' },
        { id: 'author', label: '作者网络', icon: '👥' }
    ]

    const handlePaperClick = (paper: Paper) => {
        setSelectedPaper(paper)
    }

    if (loading) {
        return (
            <div className="h-full flex items-center justify-center bg-gray-900">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                    <p className="text-gray-400">加载可视化数据...</p>
                </div>
            </div>
        )
    }

    if (compact) {
        return (
            <div className="h-full flex flex-col bg-gray-900 rounded-xl border border-gray-700">
                <div className="p-3 border-b border-gray-700 bg-gray-800 rounded-t-xl">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <span className="text-lg">📊</span>
                            <span className="text-white font-medium">可视化分析</span>
                            <span className="text-xs text-gray-400">({papers.length} 篇论文)</span>
                        </div>
                        <div className="flex gap-1">
                            {views.map(view => (
                                <button
                                    key={view.id}
                                    onClick={() => setActiveView(view.id)}
                                    className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all text-sm ${
                                        activeView === view.id
                                            ? 'bg-blue-600 text-white'
                                            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                                    }`}
                                >
                                    <span>{view.icon}</span>
                                    <span className="hidden sm:inline">{view.label}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="flex-1 overflow-auto p-3">
                    {activeView === 'timeline' && (
                        <TimelineView 
                            papers={papers} 
                            height="400px"
                        />
                    )}
                    {activeView === 'citation' && (
                        <CitationGraph 
                            papers={papers} 
                            onPaperClick={handlePaperClick}
                            height="400px"
                        />
                    )}
                    {activeView === 'knowledge' && (
                        <KnowledgeGraph 
                            clusters={clusters}
                            height="400px"
                        />
                    )}
                    {activeView === 'author' && (
                        <AuthorNetwork 
                            papers={papers}
                            height="400px"
                        />
                    )}
                </div>

                {selectedPaper && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedPaper(null)}>
                        <div className="bg-gray-800 rounded-xl max-w-2xl w-full max-h-[80vh] overflow-auto" onClick={e => e.stopPropagation()}>
                            <div className="p-6">
                                <div className="flex justify-between items-start mb-4">
                                    <h2 className="text-lg font-bold text-white flex-1 pr-4">{selectedPaper.title}</h2>
                                    <button 
                                        onClick={() => setSelectedPaper(null)}
                                        className="text-gray-400 hover:text-white"
                                    >
                                        ✕
                                    </button>
                                </div>
                                <div className="space-y-3">
                                    <div>
                                        <span className="text-gray-400 text-sm">作者：</span>
                                        <span className="text-gray-200">{selectedPaper.authors?.join(', ')}</span>
                                    </div>
                                    <div className="flex gap-4">
                                        <div>
                                            <span className="text-gray-400 text-sm">年份：</span>
                                            <span className="text-blue-400">{selectedPaper.year}</span>
                                        </div>
                                        <div>
                                            <span className="text-gray-400 text-sm">引用数：</span>
                                            <span className="text-green-400">{selectedPaper.citation_count}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        )
    }

    return (
        <div className="h-full flex flex-col bg-gray-900">
            <div className="p-4 border-b border-gray-700 bg-gray-800">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-xl font-bold text-white">📊 论文可视化分析</h1>
                        <p className="text-sm text-gray-400 mt-1">
                            共 {papers.length} 篇论文 · {clusters.length} 个研究方向
                        </p>
                    </div>
                    <div className="flex gap-2">
                        {views.map(view => (
                            <button
                                key={view.id}
                                onClick={() => setActiveView(view.id)}
                                className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-all ${
                                    activeView === view.id
                                        ? 'bg-blue-600 text-white'
                                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                                }`}
                            >
                                <span>{view.icon}</span>
                                <span>{view.label}</span>
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            <div className="flex-1 overflow-auto p-4">
                {activeView === 'timeline' && (
                    <TimelineView 
                        papers={papers} 
                        onYearClick={(year) => {
                            console.log('Selected year:', year)
                        }}
                    />
                )}
                {activeView === 'citation' && (
                    <div className="bg-gray-800 rounded-xl border border-gray-700 h-full">
                        <CitationGraph 
                            papers={papers} 
                            onPaperClick={handlePaperClick}
                            height="calc(100vh - 200px)"
                        />
                    </div>
                )}
                {activeView === 'knowledge' && (
                    <div className="bg-gray-800 rounded-xl border border-gray-700 h-full">
                        <KnowledgeGraph 
                            clusters={clusters}
                            height="calc(100vh - 200px)"
                            onKeywordClick={(keyword) => {
                                console.log('Selected keyword:', keyword)
                            }}
                        />
                    </div>
                )}
                {activeView === 'author' && (
                    <AuthorNetwork 
                        papers={papers}
                        onAuthorClick={(author) => {
                            console.log('Selected author:', author)
                        }}
                    />
                )}
            </div>

            {selectedPaper && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedPaper(null)}>
                    <div className="bg-gray-800 rounded-xl max-w-2xl w-full max-h-[80vh] overflow-auto" onClick={e => e.stopPropagation()}>
                        <div className="p-6">
                            <div className="flex justify-between items-start mb-4">
                                <h2 className="text-lg font-bold text-white flex-1 pr-4">{selectedPaper.title}</h2>
                                <button 
                                    onClick={() => setSelectedPaper(null)}
                                    className="text-gray-400 hover:text-white"
                                >
                                    ✕
                                </button>
                            </div>
                            <div className="space-y-3">
                                <div>
                                    <span className="text-gray-400 text-sm">作者：</span>
                                    <span className="text-gray-200">{selectedPaper.authors?.join(', ')}</span>
                                </div>
                                <div className="flex gap-4">
                                    <div>
                                        <span className="text-gray-400 text-sm">年份：</span>
                                        <span className="text-blue-400">{selectedPaper.year}</span>
                                    </div>
                                    <div>
                                        <span className="text-gray-400 text-sm">引用数：</span>
                                        <span className="text-green-400">{selectedPaper.citation_count}</span>
                                    </div>
                                    <div>
                                        <span className="text-gray-400 text-sm">来源：</span>
                                        <span className="text-purple-400">{selectedPaper.source}</span>
                                    </div>
                                </div>
                                {selectedPaper.keywords && selectedPaper.keywords.length > 0 && (
                                    <div>
                                        <span className="text-gray-400 text-sm">关键词：</span>
                                        <div className="flex flex-wrap gap-2 mt-1">
                                            {selectedPaper.keywords.map((kw, i) => (
                                                <span key={i} className="px-2 py-1 bg-gray-700 text-gray-300 rounded text-xs">
                                                    {kw}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                <div>
                                    <span className="text-gray-400 text-sm">摘要：</span>
                                    <p className="text-gray-300 text-sm mt-1">{selectedPaper.abstract}</p>
                                </div>
                                <div className="flex gap-3 pt-4 border-t border-gray-700">
                                    {selectedPaper.url && (
                                        <a
                                            href={selectedPaper.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors"
                                        >
                                            🔗 查看详情
                                        </a>
                                    )}
                                    {selectedPaper.pdf_url && (
                                        <a
                                            href={selectedPaper.pdf_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm transition-colors"
                                        >
                                            📄 PDF
                                        </a>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export type { Paper, ViewType }
