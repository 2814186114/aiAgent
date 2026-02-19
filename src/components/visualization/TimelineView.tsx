import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'

interface Paper {
    paper_id: string
    title: string
    authors: string[]
    year: number
    abstract: string
    citation_count: number
    keywords?: string[]
}

interface TimelineData {
    year: number
    count: number
    keywords: { keyword: string; count: number }[]
    papers: Paper[]
}

interface TimelineViewProps {
    papers: Paper[]
    height?: string
    onYearClick?: (year: number) => void
}

export function TimelineView({ papers, height = '600px', onYearClick }: TimelineViewProps) {
    const timelineData = useMemo(() => {
        const yearMap = new Map<number, { count: number; keywords: Map<string, number>; papers: Paper[] }>()

        papers.forEach(paper => {
            const year = paper.year || new Date().getFullYear()
            if (!yearMap.has(year)) {
                yearMap.set(year, { count: 0, keywords: new Map(), papers: [] })
            }
            const yearData = yearMap.get(year)!
            yearData.count++
            yearData.papers.push(paper)

            paper.keywords?.forEach(kw => {
                yearData.keywords.set(kw, (yearData.keywords.get(kw) || 0) + 1)
            })
        })

        const data: TimelineData[] = []
        yearMap.forEach((value, year) => {
            data.push({
                year,
                count: value.count,
                keywords: Array.from(value.keywords.entries())
                    .map(([keyword, count]) => ({ keyword, count }))
                    .sort((a, b) => b.count - a.count)
                    .slice(0, 5),
                papers: value.papers
            })
        })

        return data.sort((a, b) => a.year - b.year)
    }, [papers])

    const chartData = useMemo(() => {
        const years = timelineData.map(d => d.year)
        const counts = timelineData.map(d => d.count)
        const topKeywords = timelineData.map(d => d.keywords.slice(0, 3).map(k => k.keyword).join(', '))

        return { years, counts, topKeywords }
    }, [timelineData])

    const option = useMemo(() => ({
        title: {
            text: '论文发表时间线',
            subtext: `${papers.length} 篇论文`,
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
            trigger: 'axis',
            axisPointer: {
                type: 'shadow'
            },
            formatter: (params: any) => {
                const dataIndex = params[0].dataIndex
                const data = timelineData[dataIndex]
                const topKws = data.keywords.slice(0, 5)
                    .map(k => `${k.keyword} (${k.count})`)
                    .join('<br/>')
                
                return `
                    <div style="max-width: 300px;">
                        <strong>${data.year}年</strong><br/>
                        <span>发表论文: ${data.count} 篇</span><br/>
                        <br/>
                        <strong>热门关键词:</strong><br/>
                        ${topKws || '暂无'}
                    </div>
                `
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '15%',
            top: '15%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: chartData.years,
            axisLine: {
                lineStyle: { color: '#4b5563' }
            },
            axisLabel: {
                color: '#9ca3af',
                rotate: 45
            }
        },
        yAxis: {
            type: 'value',
            name: '论文数量',
            nameTextStyle: {
                color: '#9ca3af'
            },
            axisLine: {
                lineStyle: { color: '#4b5563' }
            },
            axisLabel: {
                color: '#9ca3af'
            },
            splitLine: {
                lineStyle: { color: '#374151' }
            }
        },
        series: [
            {
                name: '论文数量',
                type: 'bar',
                data: chartData.counts,
                itemStyle: {
                    color: {
                        type: 'linear',
                        x: 0,
                        y: 0,
                        x2: 0,
                        y2: 1,
                        colorStops: [
                            { offset: 0, color: '#3b82f6' },
                            { offset: 1, color: '#1d4ed8' }
                        ]
                    },
                    borderRadius: [4, 4, 0, 0]
                },
                emphasis: {
                    itemStyle: {
                        color: '#60a5fa'
                    }
                },
                markLine: {
                    data: [{ type: 'average', name: '平均值' }],
                    lineStyle: {
                        color: '#f59e0b',
                        type: 'dashed'
                    },
                    label: {
                        color: '#f59e0b'
                    }
                }
            },
            {
                name: '趋势线',
                type: 'line',
                data: chartData.counts,
                smooth: true,
                symbol: 'circle',
                symbolSize: 8,
                lineStyle: {
                    color: '#10b981',
                    width: 3
                },
                itemStyle: {
                    color: '#10b981',
                    borderColor: '#fff',
                    borderWidth: 2
                },
                areaStyle: {
                    color: {
                        type: 'linear',
                        x: 0,
                        y: 0,
                        x2: 0,
                        y2: 1,
                        colorStops: [
                            { offset: 0, color: 'rgba(16, 185, 129, 0.3)' },
                            { offset: 1, color: 'rgba(16, 185, 129, 0)' }
                        ]
                    }
                }
            }
        ],
        dataZoom: [
            {
                type: 'slider',
                show: true,
                xAxisIndex: [0],
                bottom: 10,
                height: 20,
                borderColor: '#4b5563',
                backgroundColor: '#1f2937',
                fillerColor: 'rgba(59, 130, 246, 0.2)',
                handleStyle: {
                    color: '#3b82f6'
                },
                textStyle: {
                    color: '#9ca3af'
                }
            }
        ],
        backgroundColor: 'transparent'
    }), [chartData, timelineData, papers.length])

    const keywordTrendOption = useMemo(() => {
        const allKeywords = new Map<string, Map<number, number>>()
        
        timelineData.forEach(d => {
            d.keywords.forEach(kw => {
                if (!allKeywords.has(kw.keyword)) {
                    allKeywords.set(kw.keyword, new Map())
                }
                allKeywords.get(kw.keyword)!.set(d.year, kw.count)
            })
        })

        const topKeywords = Array.from(allKeywords.entries())
            .map(([kw, yearMap]) => ({
                keyword: kw,
                total: Array.from(yearMap.values()).reduce((a, b) => a + b, 0)
            }))
            .sort((a, b) => b.total - a.total)
            .slice(0, 10)

        const series = topKeywords.map(({ keyword }) => ({
            name: keyword,
            type: 'line' as const,
            smooth: true,
            data: chartData.years.map(year => {
                const kwData = allKeywords.get(keyword)
                return kwData?.get(year) || 0
            }),
            symbol: 'circle',
            symbolSize: 6
        }))

        return {
            title: {
                text: '关键词演变趋势',
                left: 'center',
                textStyle: {
                    color: '#fff',
                    fontSize: 16
                }
            },
            tooltip: {
                trigger: 'axis'
            },
            legend: {
                data: topKeywords.map(k => k.keyword),
                top: 40,
                textStyle: {
                    color: '#9ca3af',
                    fontSize: 10
                },
                type: 'scroll'
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                top: 100,
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: chartData.years,
                axisLine: { lineStyle: { color: '#4b5563' } },
                axisLabel: { color: '#9ca3af' }
            },
            yAxis: {
                type: 'value',
                name: '出现次数',
                nameTextStyle: { color: '#9ca3af' },
                axisLine: { lineStyle: { color: '#4b5563' } },
                axisLabel: { color: '#9ca3af' },
                splitLine: { lineStyle: { color: '#374151' } }
            },
            series,
            backgroundColor: 'transparent'
        }
    }, [timelineData, chartData.years])

    const onEvents = {
        click: (params: any) => {
            if (params.componentType === 'series' && onYearClick) {
                const year = chartData.years[params.dataIndex]
                onYearClick(year)
            }
        }
    }

    if (!papers || papers.length === 0) {
        return (
            <div className="flex items-center justify-center h-full text-gray-400">
                <div className="text-center">
                    <div className="text-4xl mb-2">📅</div>
                    <p>暂无时间线数据</p>
                    <p className="text-sm">请先搜索或导入论文</p>
                </div>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                <ReactECharts
                    option={option}
                    style={{ height: '350px', width: '100%' }}
                    onEvents={onEvents}
                />
            </div>
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                <ReactECharts
                    option={keywordTrendOption}
                    style={{ height: '350px', width: '100%' }}
                />
            </div>
            <div className="text-xs text-gray-500 text-center">
                💡 点击柱状图查看该年份的论文详情
            </div>
        </div>
    )
}
