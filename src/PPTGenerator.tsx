import { useState } from 'react'
import PptxGenJS from 'pptxgenjs'

interface PPTSection {
    title: string
    bullets: string[]
}

interface PPTOutline {
    title: string
    sections: PPTSection[]
}

export function PPTGenerator() {
    const [request, setRequest] = useState('生成本周组会汇报PPT')
    const [outline, setOutline] = useState<PPTOutline | null>(null)
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const generateOutline = async () => {
        if (!request.trim()) return

        setIsLoading(true)
        setError(null)

        try {
            const response = await fetch('http://localhost:8000/generate-ppt', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ user_request: request }),
            })

            if (!response.ok) {
                throw new Error('生成PPT大纲失败')
            }

            const data = await response.json()
            if (data.success) {
                setOutline(data.outline)
            } else {
                setError(data.error || '生成PPT大纲失败')
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : '网络错误')
        } finally {
            setIsLoading(false)
        }
    }

    const updateSectionTitle = (index: number, newTitle: string) => {
        if (!outline) return
        const newSections = [...outline.sections]
        newSections[index] = { ...newSections[index], title: newTitle }
        setOutline({ ...outline, sections: newSections })
    }

    const updateSectionBullet = (sectionIndex: number, bulletIndex: number, newBullet: string) => {
        if (!outline) return
        const newSections = [...outline.sections]
        const newBullets = [...newSections[sectionIndex].bullets]
        newBullets[bulletIndex] = newBullet
        newSections[sectionIndex] = { ...newSections[sectionIndex], bullets: newBullets }
        setOutline({ ...outline, sections: newSections })
    }

    const addBullet = (sectionIndex: number) => {
        if (!outline) return
        const newSections = [...outline.sections]
        newSections[sectionIndex].bullets.push('新要点')
        setOutline({ ...outline, sections: newSections })
    }

    const removeBullet = (sectionIndex: number, bulletIndex: number) => {
        if (!outline) return
        const newSections = [...outline.sections]
        newSections[sectionIndex].bullets.splice(bulletIndex, 1)
        setOutline({ ...outline, sections: newSections })
    }

    const downloadPPT = () => {
        if (!outline) return

        const pptx = new PptxGenJS()

        pptx.layout = 'LAYOUT_WIDE'

        const titleSlide = pptx.addSlide()
        titleSlide.addText(outline.title, {
            x: 0.5,
            y: 1.5,
            w: '90%',
            h: 1,
            fontSize: 44,
            bold: true,
            color: '363636',
            align: 'center'
        })
        titleSlide.addText('Academic Assistant Agent', {
            x: 0.5,
            y: 3.5,
            w: '90%',
            h: 0.5,
            fontSize: 18,
            color: '666666',
            align: 'center'
        })

        outline.sections.forEach((section) => {
            const slide = pptx.addSlide()

            slide.addText(section.title, {
                x: 0.5,
                y: 0.5,
                w: '90%',
                h: 0.8,
                fontSize: 32,
                bold: true,
                color: '363636'
            })

            if (section.bullets.length > 0) {
                slide.addText(section.bullets.map(bullet => ({ text: bullet })), {
                    x: 0.8,
                    y: 1.8,
                    w: '85%',
                    h: 4,
                    fontSize: 20,
                    color: '363636',
                    bullet: { indent: 15 }
                })
            }
        })

        pptx.writeFile({ fileName: `${outline.title}.pptx` })
    }

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold mb-4 text-gray-800 dark:text-white">📊 PPT 生成器</h2>

            <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    输入你的需求
                </label>
                <div className="flex gap-3">
                    <input
                        type="text"
                        value={request}
                        onChange={(e) => setRequest(e.target.value)}
                        placeholder="例如：生成本周组会汇报PPT"
                        className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-white"
                        disabled={isLoading}
                    />
                    <button
                        onClick={generateOutline}
                        disabled={isLoading || !request.trim()}
                        className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        {isLoading ? '生成中...' : '生成大纲'}
                    </button>
                </div>
            </div>

            {error && (
                <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300">
                    {error}
                </div>
            )}

            {outline && (
                <div className="space-y-6">
                    <div className="border-b border-gray-200 dark:border-gray-600 pb-4">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            PPT 标题
                        </label>
                        <input
                            type="text"
                            value={outline.title}
                            onChange={(e) => setOutline({ ...outline, title: e.target.value })}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-white font-medium"
                        />
                    </div>

                    <div className="space-y-4">
                        <h3 className="text-lg font-medium text-gray-800 dark:text-white">幻灯片内容</h3>
                        {outline.sections.map((section, sectionIndex) => (
                            <div key={sectionIndex} className="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
                                <div className="mb-4">
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                        第 {sectionIndex + 1} 页 - 标题
                                    </label>
                                    <input
                                        type="text"
                                        value={section.title}
                                        onChange={(e) => updateSectionTitle(sectionIndex, e.target.value)}
                                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-white"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                                        要点
                                    </label>
                                    {section.bullets.map((bullet, bulletIndex) => (
                                        <div key={bulletIndex} className="flex gap-2">
                                            <input
                                                type="text"
                                                value={bullet}
                                                onChange={(e) => updateSectionBullet(sectionIndex, bulletIndex, e.target.value)}
                                                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-white"
                                            />
                                            <button
                                                onClick={() => removeBullet(sectionIndex, bulletIndex)}
                                                className="px-3 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                                            >
                                                删除
                                            </button>
                                        </div>
                                    ))}
                                    <button
                                        onClick={() => addBullet(sectionIndex)}
                                        className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors text-sm"
                                    >
                                        + 添加要点
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="pt-6 border-t border-gray-200 dark:border-gray-600">
                        <button
                            onClick={downloadPPT}
                            className="w-full px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
                        >
                            📥 下载 PPT 文件
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}