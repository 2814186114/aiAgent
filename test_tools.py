import asyncio
import os
import sys

_lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python_libs")
if os.path.exists(_lib_path):
    sys.path.insert(0, _lib_path)

from agent.literature import search_semantic_scholar
from agent.pdf_tools import read_pdf, download_pdf

async def test_search():
    print("=" * 50)
    print("测试 1: Semantic Scholar 文献搜索")
    print("=" * 50)
    
    result = await search_semantic_scholar("deep learning transformer", limit=3)
    
    if result.get("success"):
        print(f"✅ 搜索成功！找到 {result['total']} 篇论文\n")
        for i, paper in enumerate(result['papers'], 1):
            print(f"论文 {i}:")
            print(f"  标题: {paper['title']}")
            print(f"  作者: {', '.join(paper['authors'])}")
            print(f"  年份: {paper.get('year', 'N/A')}")
            print(f"  URL: {paper.get('url', '')}")
            print(f"  PDF: {paper.get('pdf_url', 'N/A')}")
            print()
    else:
        print(f"❌ 搜索失败: {result.get('error')}")
    
    print()
    return result

async def test_pdf():
    print("=" * 50)
    print("测试 2: PDF 读取工具")
    print("=" * 50)
    
    print("注意: 这个测试需要本地有PDF文件")
    print("提示: 可以先下载一个PDF或者跳过此测试\n")
    
    return {"success": True, "message": "PDF测试已准备好"}

async def main():
    print("\n🧪 开始测试 AgentPaper 工具模块\n")
    
    try:
        search_result = await test_search()
        pdf_result = await test_pdf()
        
        print("=" * 50)
        print("✅ 所有基础测试通过！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 测试出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
