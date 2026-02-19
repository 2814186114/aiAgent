import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'

interface Paper {
    paper_id: string
    title: string
    authors: string[]
    year: number
    citation_count: number
}

interface AuthorNode {
    name: string
    paperCount: number
    citationSum: number
    papers: string[]
}

interface AuthorNetworkProps {
    papers: Paper[]
    height?: string
    onAuthorClick?: (author: string) => void
}

export function AuthorNetwork({ papers, height = '600px', onAuthorClick }: AuthorNetworkProps) {
    const graphData = useMemo(() => {
        const authorMap = new Map<string, AuthorNode>()
        const collaborationMap = new Map<string, number>()

        papers.forEach(paper => {
            const authors = paper.authors || []
            
            authors.forEach(author => {
                if (!authorMap.has(author)) {
                    authorMap.set(author, {
                        name: author,
                        paperCount: 0,
                        citationSum: 0,
                        papers: []
                    })
                }
                const authorData = authorMap.get(author)!
                authorData.paperCount++
                authorData.citationSum += paper.citation_count || 0
                authorData.papers.push(paper.title)
            })

            for (let i = 0; i < authors.length; i++) {
                for (let j = i + 1; j < authors.length; j++) {
                    const key = [authors[i], authors[j]].sort().join('|||')
                    collaborationMap.set(key, (collaborationMap.get(key) || 0) + 1)
                }
            }
        })

        const topAuthors = Array.from(authorMap.values())
            .sort((a, b) => b.paperCount - a.paperCount)
            .slice(0, 50)

        const topAuthorSet = new Set(topAuthors.map(a => a.name))

        const nodes = topAuthors.map(author => ({
            id: author.name,
            name: author.name,
            symbolSize: Math.max(15, Math.min(50, 10 + author.paperCount * 3)),
            value: author.paperCount,
            citationSum: author.citationSum,
            papers: author.papers,
            category: getAuthorCategory(author.paperCount),
            label: {
                show: author.paperCount > 3,
                fontSize: 10
            },
            itemStyle: {
                color: getAuthorColor(author.paperCount)
            }
        }))

        const links: any[] = []
        collaborationMap.forEach((count, key) => {
            const [author1, author2] = key.split('|||')
            if (topAuthorSet.has(author1) && topAuthorSet.has(author2)) {
                links.push({
                    source: author1,
                    target: author2,
                    value: count,
                    lineStyle: {
                        width: Math.min(5, count),
                        opacity: Math.min(0.8, count * 0.2)
                    }
                })
            }
        })

        return { nodes, links }
    }, [papers])

    const statistics = useMemo(() => {
        const authorMap = new Map<string, number>()
        papers.forEach(paper => {
            (paper.authors || []).forEach(author => {
                authorMap.set(author, (authorMap.get(author) || 0) + 1)
            })
        })

        const sortedAuthors = Array.from(authorMap.entries())
            .sort((a, b) => b[1] - a[1])

        return {
            totalAuthors: authorMap.size,
            topAuthors: sortedAuthors.slice(0, 5),
            avgCollaborators: papers.length > 0 
                ? (papers.reduce((sum, p) => sum + (p.authors?.length || 0), 0) / papers.length).toFixed(1)
                : '0'
        }
    }, [papers])

    const option = useMemo(() => ({
        title: {
            text: '作者合作网络',
            subtext: `${statistics.totalAuthors} 位作者`,
            top: 'top',
            left: 'center',
            textStyle: {
                color: '#fff',
                fontSize: 18
            },
            subtextStyle: {
                color: '#9ca3af'
            }
        },
        tooltip: {
            trigger: 'item',
            formatter: (params: any) => {
                if (params.dataType === 'node') {
                    const data = params.data
                    return `
                        <div style="max-width: 300px;">
                            <strong>${data.name}</strong><br/>
                            <span style="color: #9ca3af;">发表论文: ${data.value} 篇</span><br/>
                            <span style="color: #9ca3af;">总引用: ${data.citationSum || 0}</span><br/>
                            <br/>
                            <span style="font-size: 11px; color: #6b7280;">
                                近期论文: ${data.papers?.slice(0, 2).join('<br/>') || '暂无'}
                            </span>
                        </div>
                    `
                }
                return `合作 ${params.data.value} 次`
            }
        },
        legend: [{
            data: ['核心作者', '活跃作者', '一般作者'],
            orient: 'vertical',
            right: 10,
            top: 80,
            textStyle: {
                color: '#9ca3af'
            }
        }],
        series: [{
            type: 'graph',
            layout: 'force',
            data: graphData.nodes,
            links: graphData.links,
            roam: true,
            draggable: true,
            focusNodeAdjacency: true,
            force: {
                repulsion: 300,
                edgeLength: [50, 200],
                gravity: 0.1,
                friction: 0.6
            },
            emphasis: {
                focus: 'adjacency',
                itemStyle: {
                    shadowBlur: 20,
                    shadowColor: 'rgba(255, 255, 255, 0.3)'
                },
                lineStyle: {
                    width: 4
                }
            },
            label: {
                position: 'right',
                formatter: '{b}',
                color: '#fff',
                fontSize: 10
            },
            lineStyle: {
                curveness: 0.2,
                color: '#4b5563'
            },
            categories: [
                { name: '核心作者', itemStyle: { color: '#ef4444' } },
                { name: '活跃作者', itemStyle: { color: '#f59e0b' } },
                { name: '一般作者', itemStyle: { color: '#3b82f6' } }
            ]
        }],
        backgroundColor: 'transparent'
    }), [graphData, statistics.totalAuthors])

    const onEvents = {
        click: (params: any) => {
            if (params.dataType === 'node' && onAuthorClick) {
                onAuthorClick(params.data.name)
            }
        }
    }

    if (!papers || papers.length === 0) {
        return (
            <div className="flex items-center justify-center h-full text-gray-400">
                <div className="text-center">
                    <div className="text-4xl mb-2">👥</div>
                    <p>暂无作者网络数据</p>
                    <p className="text-sm">请先搜索或导入论文</p>
                </div>
            </div>
        )
    }

    return (
        <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="bg-gray-800 rounded-lg p-4 text-center border border-gray-700">
                    <div className="text-2xl font-bold text-blue-400">{statistics.totalAuthors}</div>
                    <div className="text-sm text-gray-400">总作者数</div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 text-center border border-gray-700">
                    <div className="text-2xl font-bold text-green-400">{statistics.avgCollaborators}</div>
                    <div className="text-sm text-gray-400">平均合作人数</div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 text-center border border-gray-700">
                    <div className="text-2xl font-bold text-purple-400">{papers.length}</div>
                    <div className="text-sm text-gray-400">论文总数</div>
                </div>
            </div>

            <div className="bg-gray-800 rounded-xl border border-gray-700">
                <ReactECharts
                    option={option}
                    style={{ height, width: '100%' }}
                    onEvents={onEvents}
                    opts={{ renderer: 'canvas' }}
                />
            </div>

            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                <h3 className="text-white font-semibold mb-3">🏆 高产作者 TOP 5</h3>
                <div className="space-y-2">
                    {statistics.topAuthors.map(([author, count], index) => (
                        <div key={author} className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                                    index === 0 ? 'bg-yellow-500 text-black' :
                                    index === 1 ? 'bg-gray-400 text-black' :
                                    index === 2 ? 'bg-amber-700 text-white' :
                                    'bg-gray-600 text-white'
                                }`}>
                                    {index + 1}
                                </span>
                                <span className="text-gray-200">{author}</span>
                            </div>
                            <span className="text-blue-400 font-medium">{count} 篇</span>
                        </div>
                    ))}
                </div>
            </div>

            <div className="text-xs text-gray-500 text-center">
                💡 节点大小表示论文数量，连线粗细表示合作次数
            </div>
        </div>
    )
}

function getAuthorCategory(paperCount: number): string {
    if (paperCount >= 5) return '核心作者'
    if (paperCount >= 3) return '活跃作者'
    return '一般作者'
}

function getAuthorColor(paperCount: number): string {
    if (paperCount >= 5) return '#ef4444'
    if (paperCount >= 3) return '#f59e0b'
    return '#3b82f6'
}
