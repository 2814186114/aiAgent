

interface Experiment {
    id: number
    timestamp: string
    model?: string
    dataset?: string
    metric?: string
    value?: number
    notes?: string
}

interface ExperimentTableProps {
    experiments: Experiment[]
}

export function ExperimentTable({ experiments }: ExperimentTableProps) {
    if (!experiments || experiments.length === 0) {
        return (
            <div className="text-center py-4 text-gray-500 dark:text-gray-400">
                暂无实验记录
            </div>
        )
    }

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b border-gray-200 dark:border-gray-700">
                        <th className="py-2 px-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            时间
                        </th>
                        <th className="py-2 px-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            模型
                        </th>
                        <th className="py-2 px-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            数据集
                        </th>
                        <th className="py-2 px-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            指标
                        </th>
                        <th className="py-2 px-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            值
                        </th>
                        <th className="py-2 px-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            备注
                        </th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {experiments.map((exp) => (
                        <tr key={exp.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                            <td className="py-2 px-3 text-xs text-gray-600 dark:text-gray-400">
                                {new Date(exp.timestamp).toLocaleString()}
                            </td>
                            <td className="py-2 px-3 text-sm text-gray-900 dark:text-gray-100">
                                {exp.model || '-'}
                            </td>
                            <td className="py-2 px-3 text-sm text-gray-900 dark:text-gray-100">
                                {exp.dataset || '-'}
                            </td>
                            <td className="py-2 px-3 text-sm text-gray-900 dark:text-gray-100">
                                {exp.metric || '-'}
                            </td>
                            <td className="py-2 px-3 text-sm font-medium text-blue-600 dark:text-blue-400">
                                {exp.value !== undefined ? exp.value : '-'}
                            </td>
                            <td className="py-2 px-3 text-sm text-gray-600 dark:text-gray-400 truncate max-w-xs">
                                {exp.notes || '-'}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

export function ExperimentList({ experiments }: ExperimentTableProps) {
    if (!experiments || experiments.length === 0) {
        return null
    }

    return (
        <div className="mt-3">
            <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                实验记录 ({experiments.length} 条)：
            </p>
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                <ExperimentTable experiments={experiments} />
            </div>
        </div>
    )
}
