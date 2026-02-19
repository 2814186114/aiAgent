import ReactECharts from 'echarts-for-react'
import { useState, useMemo } from 'react'

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
    references?: string[]
    cited_by?: string[]
}

interface CitationGraphProps {
    papers: Paper[]
    onPaperClick?: (paper: Paper) => void
    height?: string
}

export function CitationGraph({ papers, onPaperClick, height = '600px' }: CitationGraphProps) {
    const [selectedNode, setSelectedNode] = useState<string | null>(null)

    const graphData = useMemo(() => {
        const nodes: any[] = []
        const links: any[] = []
        const nodeMap = new Map<string, number>()

        papers.forEach((paper, index) => {
            nodeMap.set(paper.paper_id, index)
            const nodeSize = Math.max(20, Math.min(60, 10 + (paper.citation_count || 0) * 2))
            
            nodes.push({
                id: paper.paper_id,
                name: paper.title.length > 30 ? paper.title.substring(0, 30) + '...' : paper.title,
                fullName: paper.title,
                symbolSize: nodeSize,
                category: paper.year >= 2023 ? 'recent' : paper.year >= 2020 ? 'mid' : 'old',
                value: paper.citation_count || 0,
                itemStyle: {
                    color: paper.year >= 2023 ? '#10b981' : paper.year >= 2020 ? '#3b82f6' : '#6b7280'
                },
                label: {
                    show: nodeSize > 30,
                    fontSize: 10
                },
                paper: paper
            })
        })

        papers.forEach(paper => {
            if (paper.references) {
                paper.references.forEach(refId => {
                    if (nodeMap.has(refId)) {
                        links.push({
                            source: paper.paper_id,
                            target: refId,
                            value: 1,
                            lineStyle: {
                                color: '#aaa',
                                curveness: 0.2
                            }
                        })
                    }
                })
            }
            if (paper.cited_by) {
                paper.cited_by.forEach(citerId => {
                    if (nodeMap.has(citerId) && !links.find(l => l.source === citerId && l.target === paper.paper_id)) {
                        links.push({
                            source: citerId,
                            target: paper.paper_id,
                            value: 1,
                            lineStyle: {
                                color: '#aaa',
                                curveness: 0.2
                            }
                        })
                    }
                })
            }
        })

        if (links.length === 0 && papers.length > 1) {
            for (let i = 1; i < Math.min(papers.length, 10); i++) {
                links.push({
                    source: papers[0].paper_id,
                    target: papers[i].paper_id,
                    value: 0.5,
                    lineStyle: {
                        color: '#ddd',
                        curveness: 0.1,
                        type: 'dashed'
                    }
                })
            }
        }

        return { nodes, links }
    }, [papers])

    const option = useMemo(() => ({
        title: {
            text: '引用关系图谱',
            subtext: `共 ${papers.length} 篇论文`,
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
                    const paper = params.data.paper
                    return `
                        <div style="max-width: 300px;">
                            <strong>${paper.title}</strong><br/>
                            <span style="color: #9ca3af;">${paper.authors?.slice(0, 3).join(', ')}${paper.authors?.length > 3 ? ' et al.' : ''}</span><br/>
                            <span>年份: ${paper.year}</span><br/>
                            <span>引用数: ${paper.citation_count || 0}</span>
                        </div>
                    `
                }
                return `${params.data.source} → ${params.data.target}`
            }
        },
        legend: [{
            data: ['recent', 'mid', 'old'],
            orient: 'vertical',
            right: 10,
            top: 80,
            textStyle: {
                color: '#9ca3af'
            },
            formatter: (name: string) => {
                const labels: Record<string, string> = {
                    'recent': '2023年后',
                    'mid': '2020-2022',
                    'old': '2020年前'
                }
                return labels[name] || name
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
                repulsion: 200,
                edgeLength: [50, 150],
                gravity: 0.1
            },
            emphasis: {
                focus: 'adjacency',
                lineStyle: {
                    width: 3
                }
            },
            label: {
                position: 'right',
                formatter: '{b}',
                color: '#fff'
            },
            lineStyle: {
                curveness: 0.3
            },
            categories: [
                { name: 'recent', itemStyle: { color: '#10b981' } },
                { name: 'mid', itemStyle: { color: '#3b82f6' } },
                { name: 'old', itemStyle: { color: '#6b7280' } }
            ]
        }],
        backgroundColor: 'transparent'
    }), [graphData, papers.length])

    const onEvents = {
        click: (params: any) => {
            if (params.dataType === 'node' && onPaperClick) {
                setSelectedNode(params.data.id)
                onPaperClick(params.data.paper)
            }
        }
    }

    if (!papers || papers.length === 0) {
        return (
            <div className="flex items-center justify-center h-full text-gray-400">
                <div className="text-center">
                    <div className="text-4xl mb-2">📊</div>
                    <p>暂无论文数据</p>
                    <p className="text-sm">请先搜索或导入论文</p>
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
                💡 点击节点查看详情，拖拽移动，滚轮缩放
            </div>
        </div>
    )
}
