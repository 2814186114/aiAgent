import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'

interface KeywordNode {
    name: string
    value: number
    category?: string
}

interface KeywordLink {
    source: string
    target: string
    value: number
}

interface Cluster {
    name: string
    papers: any[]
    paper_count: number
    keywords: string[]
}

interface KnowledgeGraphProps {
    clusters?: Cluster[]
    keywords?: KeywordNode[]
    links?: KeywordLink[]
    height?: string
    onKeywordClick?: (keyword: string) => void
}

export function KnowledgeGraph({ 
    clusters, 
    keywords, 
    links, 
    height = '600px',
    onKeywordClick 
}: KnowledgeGraphProps) {
    const graphData = useMemo(() => {
        const nodes: any[] = []
        const graphLinks: any[] = []
        const categories: any[] = []
        const keywordSet = new Set<string>()

        if (clusters && clusters.length > 0) {
            clusters.forEach((cluster, clusterIndex) => {
                categories.push({
                    name: cluster.name,
                    itemStyle: {
                        color: getColorByIndex(clusterIndex)
                    }
                })

                cluster.keywords?.slice(0, 10).forEach((keyword, kwIndex) => {
                    if (!keywordSet.has(keyword)) {
                        keywordSet.add(keyword)
                        nodes.push({
                            id: keyword,
                            name: keyword,
                            symbolSize: 20 + (10 - kwIndex) * 2,
                            category: cluster.name,
                            value: cluster.paper_count,
                            itemStyle: {
                                color: getColorByIndex(clusterIndex)
                            },
                            label: {
                                show: true,
                                fontSize: 11
                            }
                        })
                    }
                })

                const clusterKeywords = cluster.keywords?.slice(0, 5) || []
                for (let i = 0; i < clusterKeywords.length - 1; i++) {
                    for (let j = i + 1; j < clusterKeywords.length; j++) {
                        graphLinks.push({
                            source: clusterKeywords[i],
                            target: clusterKeywords[j],
                            value: 1,
                            lineStyle: {
                                color: getColorByIndex(clusterIndex),
                                opacity: 0.3
                            }
                        })
                    }
                }
            })
        } else if (keywords && keywords.length > 0) {
            keywords.forEach(kw => {
                nodes.push({
                    id: kw.name,
                    name: kw.name,
                    symbolSize: Math.max(15, Math.min(50, 10 + kw.value * 2)),
                    value: kw.value,
                    category: kw.category || 'default',
                    label: {
                        show: kw.value > 3,
                        fontSize: 10
                    }
                })
            })

            if (links) {
                links.forEach(link => {
                    graphLinks.push({
                        source: link.source,
                        target: link.target,
                        value: link.value,
                        lineStyle: {
                            opacity: Math.min(0.8, link.value * 0.1)
                        }
                    })
                })
            }

            categories.push({
                name: 'default',
                itemStyle: { color: '#3b82f6' }
            })
        }

        return { nodes, links: graphLinks, categories }
    }, [clusters, keywords, links])

    const option = useMemo(() => ({
        title: {
            text: '研究领域知识图谱',
            subtext: clusters ? `${clusters.length} 个研究方向` : `${graphData.nodes.length} 个关键词`,
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
                    return `
                        <div>
                            <strong>${params.data.name}</strong><br/>
                            <span style="color: #9ca3af;">相关论文: ${params.data.value || 0} 篇</span>
                        </div>
                    `
                }
                return `${params.data.source} ↔ ${params.data.target}`
            }
        },
        legend: {
            data: graphData.categories.map(c => c.name),
            orient: 'vertical',
            right: 10,
            top: 80,
            textStyle: {
                color: '#9ca3af',
                fontSize: 11
            },
            type: 'scroll'
        },
        series: [{
            type: 'graph',
            layout: 'force',
            data: graphData.nodes,
            links: graphData.links,
            categories: graphData.categories,
            roam: true,
            draggable: true,
            focusNodeAdjacency: true,
            force: {
                repulsion: 150,
                edgeLength: [30, 100],
                gravity: 0.2
            },
            emphasis: {
                focus: 'adjacency',
                itemStyle: {
                    shadowBlur: 20,
                    shadowColor: 'rgba(255, 255, 255, 0.3)'
                },
                lineStyle: {
                    width: 3
                }
            },
            label: {
                position: 'inside',
                formatter: '{b}',
                color: '#fff',
                fontSize: 10
            },
            lineStyle: {
                curveness: 0.2,
                opacity: 0.5
            },
            autoCurveness: true
        }],
        backgroundColor: 'transparent'
    }), [graphData, clusters])

    const onEvents = {
        click: (params: any) => {
            if (params.dataType === 'node' && onKeywordClick) {
                onKeywordClick(params.data.name)
            }
        }
    }

    if (graphData.nodes.length === 0) {
        return (
            <div className="flex items-center justify-center h-full text-gray-400">
                <div className="text-center">
                    <div className="text-4xl mb-2">🧠</div>
                    <p>暂无知识图谱数据</p>
                    <p className="text-sm">请先进行论文聚类分析</p>
                </div>
            </div>
        )
    }

    return (
        <div className="relative">
            <ReactECharts
                option={option}
                style={{ height, width: '100%' }}
                onEvents={onEvents}
                opts={{ renderer: 'canvas' }}
            />
            <div className="absolute bottom-4 left-4 text-xs text-gray-500">
                💡 节点大小表示关键词重要性，颜色表示研究方向
            </div>
        </div>
    )
}

function getColorByIndex(index: number): string {
    const colors = [
        '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
        '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'
    ]
    return colors[index % colors.length]
}
