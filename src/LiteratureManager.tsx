import { useState, useEffect } from 'react'
import { PaperList } from './PaperCard'

interface Paper {
    id?: number
    paper_id: string
    title: string
    authors: string[]
    year?: number
    abstract?: string
    url?: string
    pdf_url?: string
    added_at?: string
    last_read_at?: string
    read_count?: number
    tags?: string[]
    folders?: Array<{ id: number; name: string }>
    notes?: Array<{ id: number; content: string; created_at: string; updated_at: string }>
}

interface Folder {
    id: number
    name: string
    description?: string
    created_at: string
    paper_count: number
}

interface Note {
    id: number
    content: string
    created_at: string
    updated_at: string
}

type ViewMode = 'search' | 'collection' | 'folders'

export function LiteratureManager() {
    const [viewMode, setViewMode] = useState<ViewMode>('search')
    const [query, setQuery] = useState('')
    const [searchPapers, setSearchPapers] = useState<Paper[]>([])
    const [collectionPapers, setCollectionPapers] = useState<Paper[]>([])
    const [folders, setFolders] = useState<Folder[]>([])
    const [tags, setTags] = useState<string[]>([])
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [selectedTag, setSelectedTag] = useState<string | null>(null)
    const [selectedFolder, setSelectedFolder] = useState<number | null>(null)
    const [expandedPaper, setExpandedPaper] = useState<string | null>(null)
    const [newNote, setNewNote] = useState('')
    const [editingNote, setEditingNote] = useState<Note | null>(null)
    const [newFolderName, setNewFolderName] = useState('')
    const [newFolderDesc, setNewFolderDesc] = useState('')

    const fetchCollection = async () => {
        try {
            const params = new URLSearchParams()
            if (selectedTag) params.append('tag', selectedTag)
            if (selectedFolder) params.append('folder', selectedFolder.toString())
            
            const response = await fetch(`http://localhost:8000/literature/papers?${params}`)
            const data = await response.json()
            if (data.success) {
                setCollectionPapers(data.papers || [])
            }
        } catch (err) {
            console.error('获取收藏失败:', err)
        }
    }

    const fetchFolders = async () => {
        try {
            const response = await fetch('http://localhost:8000/literature/folders')
            const data = await response.json()
            if (data.success) {
                setFolders(data.folders || [])
            }
        } catch (err) {
            console.error('获取文件夹失败:', err)
        }
    }

    const fetchTags = async () => {
        try {
            const response = await fetch('http://localhost:8000/literature/tags')
            const data = await response.json()
            if (data.success) {
                setTags(data.tags || [])
            }
        } catch (err) {
            console.error('获取标签失败:', err)
        }
    }

    useEffect(() => {
        if (viewMode === 'collection') {
            fetchCollection()
            fetchTags()
        } else if (viewMode === 'folders') {
            fetchFolders()
        }
    }, [viewMode, selectedTag, selectedFolder])

    const handleSearch = async () => {
        if (!query.trim()) return
        
        setIsLoading(true)
        setError(null)
        setSearchPapers([])
        
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
            
            setSearchPapers(foundPapers)
            
            if (foundPapers.length === 0) {
                setError('未找到相关论文，请尝试其他关键词')
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : '搜索出错了')
        } finally {
            setIsLoading(false)
        }
    }

    const handleSavePaper = async (paper: Paper) => {
        try {
            const response = await fetch('http://localhost:8000/literature/papers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    paper_id: paper.paper_id || paper.title,
                    title: paper.title,
                    authors: paper.authors,
                    year: paper.year,
                    abstract: paper.abstract,
                    url: paper.url,
                    pdf_url: paper.pdf_url
                })
            })
            
            const data = await response.json()
            if (data.success) {
                alert('论文已收藏！')
                if (viewMode === 'collection') {
                    fetchCollection()
                }
            }
        } catch (err) {
            alert('收藏失败')
        }
    }

    const handleRemovePaper = async (paperId: string) => {
        if (!confirm('确定要从收藏中移除这篇论文吗？')) return
        
        try {
            const response = await fetch(`http://localhost:8000/literature/papers/${paperId}`, {
                method: 'DELETE'
            })
            
            const data = await response.json()
            if (data.success) {
                fetchCollection()
            }
        } catch (err) {
            alert('移除失败')
        }
    }

    const handleAddTag = async (paperId: string, tagName: string) => {
        try {
            const response = await fetch('http://localhost:8000/literature/papers/tags', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ paper_id: paperId, tag_name: tagName })
            })
            
            const data = await response.json()
            if (data.success) {
                fetchCollection()
                fetchTags()
            }
        } catch (err) {
            alert('添加标签失败')
        }
    }

    const handleRemoveTag = async (paperId: string, tagName: string) => {
        try {
            const response = await fetch(`http://localhost:8000/literature/papers/${paperId}/tags/${tagName}`, {
                method: 'DELETE'
            })
            
            const data = await response.json()
            if (data.success) {
                fetchCollection()
            }
        } catch (err) {
            alert('移除标签失败')
        }
    }

    const handleAddNote = async (paperId: string) => {
        if (!newNote.trim()) return
        
        try {
            const response = await fetch('http://localhost:8000/literature/notes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ paper_id: paperId, content: newNote })
            })
            
            const data = await response.json()
            if (data.success) {
                setNewNote('')
                fetchCollection()
            }
        } catch (err) {
            alert('添加笔记失败')
        }
    }

    const handleUpdateNote = async (noteId: number) => {
        if (!editingNote || !editingNote.content.trim()) return
        
        try {
            const response = await fetch(`http://localhost:8000/literature/notes/${noteId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: editingNote.content })
            })
            
            const data = await response.json()
            if (data.success) {
                setEditingNote(null)
                fetchCollection()
            }
        } catch (err) {
            alert('更新笔记失败')
        }
    }

    const handleDeleteNote = async (noteId: number) => {
        if (!confirm('确定要删除这条笔记吗？')) return
        
        try {
            const response = await fetch(`http://localhost:8000/literature/notes/${noteId}`, {
                method: 'DELETE'
            })
            
            const data = await response.json()
            if (data.success) {
                fetchCollection()
            }
        } catch (err) {
            alert('删除笔记失败')
        }
    }

    const handleCreateFolder = async () => {
        if (!newFolderName.trim()) return
        
        try {
            const response = await fetch('http://localhost:8000/literature/folders', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: newFolderName, description: newFolderDesc })
            })
            
            const data = await response.json()
            if (data.success) {
                setNewFolderName('')
                setNewFolderDesc('')
                fetchFolders()
            }
        } catch (err) {
            alert('创建文件夹失败')
        }
    }

    const handleDeleteFolder = async (folderId: number) => {
        if (!confirm('确定要删除这个文件夹吗？里面的论文不会被删除。')) return
        
        try {
            const response = await fetch(`http://localhost:8000/literature/folders/${folderId}`, {
                method: 'DELETE'
            })
            
            const data = await response.json()
            if (data.success) {
                fetchFolders()
            }
        } catch (err) {
            alert('删除文件夹失败')
        }
    }

    const handleAddPaperToFolder = async (paperId: string, folderId: number) => {
        try {
            const response = await fetch('http://localhost:8000/literature/folders/papers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ paper_id: paperId, folder_id: folderId })
            })
            
            const data = await response.json()
            if (data.success) {
                fetchCollection()
            }
        } catch (err) {
            alert('添加到文件夹失败')
        }
    }

    const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            handleSearch()
        }
    }

    const formatDate = (timestamp: string) => {
        const date = new Date(timestamp)
        return date.toLocaleString('zh-CN')
    }

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <div className="flex gap-2 mb-6 border-b border-gray-200 dark:border-gray-700">
                <button
                    onClick={() => setViewMode('search')}
                    className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${viewMode === 'search'
                        ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t border-l border-r border-gray-200 dark:border-gray-700'
                        : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                    }`}
                >
                    🔍 搜索文献
                </button>
                <button
                    onClick={() => {
                        setViewMode('collection')
                        setSelectedTag(null)
                        setSelectedFolder(null)
                    }}
                    className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${viewMode === 'collection'
                        ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t border-l border-r border-gray-200 dark:border-gray-700'
                        : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                    }`}
                >
                    📚 我的收藏
                </button>
                <button
                    onClick={() => setViewMode('folders')}
                    className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${viewMode === 'folders'
                        ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t border-l border-r border-gray-200 dark:border-gray-700'
                        : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                    }`}
                >
                    📁 文件夹
                </button>
            </div>

            {viewMode === 'search' && (
                <div>
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

                    {searchPapers.length > 0 && (
                        <div>
                            <div className="flex items-center justify-between mb-4">
                                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                    找到 {searchPapers.length} 篇论文
                                </p>
                            </div>
                            <div className="space-y-4">
                                {searchPapers.map((paper, index) => (
                                    <div key={index} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                                        <PaperList papers={[paper]} />
                                        <button
                                            onClick={() => handleSavePaper(paper)}
                                            className="mt-2 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors text-sm"
                                        >
                                            ⭐ 收藏论文
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {!isLoading && !error && searchPapers.length === 0 && query.trim() === '' && (
                        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                            <p className="text-lg mb-2">输入关键词开始搜索论文</p>
                            <p className="text-sm">支持 Semantic Scholar 和 arXiv 双数据源</p>
                        </div>
                    )}
                </div>
            )}

            {viewMode === 'collection' && (
                <div>
                    <h2 className="text-2xl font-bold mb-6 text-gray-800 dark:text-white">📚 我的收藏</h2>
                    
                    {(tags.length > 0 || folders.length > 0) && (
                        <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                            {tags.length > 0 && (
                                <div className="mb-4">
                                    <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">标签筛选：</p>
                                    <div className="flex flex-wrap gap-2">
                                        <button
                                            onClick={() => setSelectedTag(null)}
                                            className={`px-3 py-1 rounded-full text-sm ${!selectedTag
                                                ? 'bg-blue-600 text-white'
                                                : 'bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300'
                                            }`}
                                        >
                                            全部
                                        </button>
                                        {tags.map((tag) => (
                                            <button
                                                key={tag}
                                                onClick={() => setSelectedTag(tag)}
                                                className={`px-3 py-1 rounded-full text-sm ${selectedTag === tag
                                                    ? 'bg-blue-600 text-white'
                                                    : 'bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300'
                                                }`}
                                            >
                                                {tag}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {collectionPapers.length === 0 ? (
                        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                            <p className="text-lg mb-2">暂无收藏的论文</p>
                            <p className="text-sm">在搜索页面收藏论文后，这里会显示</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {collectionPapers.map((paper) => (
                                <div key={paper.paper_id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                                    <div className="flex justify-between items-start mb-2">
                                        <div className="flex-1">
                                            <h3 className="text-lg font-medium text-gray-800 dark:text-white mb-1">
                                                {paper.title}
                                            </h3>
                                            {paper.authors && paper.authors.length > 0 && (
                                                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                                                    {paper.authors.join(', ')}
                                                </p>
                                            )}
                                            {paper.year && (
                                                <span className="text-xs text-gray-500 dark:text-gray-500">
                                                    {paper.year}
                                                </span>
                                            )}
                                        </div>
                                        <button
                                            onClick={() => handleRemovePaper(paper.paper_id)}
                                            className="ml-4 px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 transition-colors text-sm"
                                        >
                                            移除
                                        </button>
                                    </div>

                                    {paper.tags && paper.tags.length > 0 && (
                                        <div className="flex flex-wrap gap-2 mb-2">
                                            {paper.tags.map((tag) => (
                                                <span key={tag} className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full text-xs">
                                                    {tag}
                                                    <button
                                                        onClick={() => handleRemoveTag(paper.paper_id, tag)}
                                                        className="hover:text-blue-900 dark:hover:text-blue-100"
                                                    >
                                                        ×
                                                    </button>
                                                </span>
                                            ))}
                                        </div>
                                    )}

                                    <div className="flex flex-wrap gap-2 mb-3">
                                        {paper.url && (
                                            <a
                                                href={paper.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors text-sm"
                                            >
                                                打开页面
                                            </a>
                                        )}
                                        {paper.pdf_url && (
                                            <a
                                                href={paper.pdf_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 transition-colors text-sm"
                                            >
                                                下载 PDF
                                            </a>
                                        )}
                                        <button
                                            onClick={() => setExpandedPaper(expandedPaper === paper.paper_id ? null : paper.paper_id)}
                                            className="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors text-sm"
                                        >
                                            {expandedPaper === paper.paper_id ? '收起详情' : '展开详情'}
                                        </button>
                                    </div>

                                    {expandedPaper === paper.paper_id && (
                                        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                                            {paper.abstract && (
                                                <div className="mb-4">
                                                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">摘要：</h4>
                                                    <p className="text-sm text-gray-600 dark:text-gray-400">{paper.abstract}</p>
                                                </div>
                                            )}

                                            <div className="mb-4">
                                                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">添加标签：</h4>
                                                <div className="flex gap-2">
                                                    <input
                                                        type="text"
                                                        placeholder="输入标签名称"
                                                        className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-800 dark:text-white text-sm"
                                                        onKeyPress={(e) => {
                                                            if (e.key === 'Enter') {
                                                                const input = e.target as HTMLInputElement
                                                                if (input.value.trim()) {
                                                                    handleAddTag(paper.paper_id, input.value.trim())
                                                                    input.value = ''
                                                                }
                                                            }
                                                        }}
                                                    />
                                                </div>
                                            </div>

                                            {paper.folders && paper.folders.length > 0 && (
                                                <div className="mb-4">
                                                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">所在文件夹：</h4>
                                                    <div className="flex flex-wrap gap-2">
                                                        {paper.folders.map((folder) => (
                                                            <span key={folder.id} className="px-2 py-1 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 rounded-full text-xs">
                                                                📁 {folder.name}
                                                            </span>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            <div className="mb-4">
                                                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">笔记：</h4>
                                                <div className="space-y-2 mb-3">
                                                    {paper.notes && paper.notes.map((note) => (
                                                        <div key={note.id} className="p-3 bg-gray-50 dark:bg-gray-700 rounded">
                                                            {editingNote && editingNote.id === note.id ? (
                                                                <div>
                                                                    <textarea
                                                                        value={editingNote.content}
                                                                        onChange={(e) => setEditingNote({ ...editingNote, content: e.target.value })}
                                                                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-600 text-gray-800 dark:text-white text-sm resize-none"
                                                                        rows={3}
                                                                    />
                                                                    <div className="flex gap-2 mt-2">
                                                                        <button
                                                                            onClick={() => handleUpdateNote(note.id)}
                                                                            className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                                                                        >
                                                                            保存
                                                                        </button>
                                                                        <button
                                                                            onClick={() => setEditingNote(null)}
                                                                            className="px-3 py-1 bg-gray-500 text-white rounded text-sm hover:bg-gray-600"
                                                                        >
                                                                            取消
                                                                        </button>
                                                                    </div>
                                                                </div>
                                                            ) : (
                                                                <div>
                                                                    <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{note.content}</p>
                                                                    <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                                                                        {formatDate(note.created_at)}
                                                                    </p>
                                                                    <div className="flex gap-2 mt-2">
                                                                        <button
                                                                            onClick={() => setEditingNote(note)}
                                                                            className="px-2 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700"
                                                                        >
                                                                            编辑
                                                                        </button>
                                                                        <button
                                                                            onClick={() => handleDeleteNote(note.id)}
                                                                            className="px-2 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700"
                                                                        >
                                                                            删除
                                                                        </button>
                                                                    </div>
                                                                </div>
                                                            )}
                                                        </div>
                                                    ))}
                                                </div>
                                                <div className="flex gap-2">
                                                    <textarea
                                                        value={newNote}
                                                        onChange={(e) => setNewNote(e.target.value)}
                                                        placeholder="添加笔记..."
                                                        className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-800 dark:text-white text-sm resize-none"
                                                        rows={2}
                                                    />
                                                    <button
                                                        onClick={() => handleAddNote(paper.paper_id)}
                                                        disabled={!newNote.trim()}
                                                        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 transition-colors text-sm"
                                                    >
                                                        添加
                                                    </button>
                                                </div>
                                            </div>

                                            <div className="text-xs text-gray-500 dark:text-gray-500">
                                                添加于：{formatDate(paper.added_at || '')}
                                                {paper.read_count && paper.read_count > 0 && ` • 阅读 ${paper.read_count} 次`}
                                                {paper.last_read_at && ` • 最后阅读：${formatDate(paper.last_read_at)}`}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {viewMode === 'folders' && (
                <div>
                    <h2 className="text-2xl font-bold mb-6 text-gray-800 dark:text-white">📁 文件夹管理</h2>
                    
                    <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">创建新文件夹：</h3>
                        <div className="space-y-3">
                            <input
                                type="text"
                                value={newFolderName}
                                onChange={(e) => setNewFolderName(e.target.value)}
                                placeholder="文件夹名称"
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-800 dark:text-white"
                            />
                            <input
                                type="text"
                                value={newFolderDesc}
                                onChange={(e) => setNewFolderDesc(e.target.value)}
                                placeholder="描述（可选）"
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-800 dark:text-white"
                            />
                            <button
                                onClick={handleCreateFolder}
                                disabled={!newFolderName.trim()}
                                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 transition-colors"
                            >
                                创建文件夹
                            </button>
                        </div>
                    </div>

                    {folders.length === 0 ? (
                        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                            <p className="text-lg mb-2">暂无文件夹</p>
                            <p className="text-sm">创建文件夹来组织你的论文收藏</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {folders.map((folder) => (
                                <div key={folder.id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                                    <div className="flex justify-between items-start mb-2">
                                        <div>
                                            <h3 className="text-lg font-medium text-gray-800 dark:text-white">
                                                📁 {folder.name}
                                            </h3>
                                            {folder.description && (
                                                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                                                    {folder.description}
                                                </p>
                                            )}
                                        </div>
                                        <button
                                            onClick={() => handleDeleteFolder(folder.id)}
                                            className="px-2 py-1 bg-red-600 text-white rounded hover:bg-red-700 transition-colors text-sm"
                                        >
                                            删除
                                        </button>
                                    </div>
                                    <div className="text-sm text-gray-500 dark:text-gray-400">
                                        {folder.paper_count} 篇论文
                                    </div>
                                    <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                                        创建于：{formatDate(folder.created_at)}
                                    </div>
                                    <button
                                        onClick={() => {
                                            setSelectedFolder(folder.id)
                                            setViewMode('collection')
                                        }}
                                        className="mt-3 w-full px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-sm"
                                    >
                                        查看论文
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
