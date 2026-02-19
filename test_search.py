import os
import sys
import asyncio

_lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python_libs")
if os.path.exists(_lib_path):
    sys.path.insert(0, _lib_path)

from agent.multi_source_search import search_all_sources, search_arxiv, search_semantic_scholar, search_pubmed

async def test_search():
    print("Testing search functions...")
    print("-" * 60)
    
    query = "agent context management"
    years = 2
    max_papers = 10
    
    print(f"Query: {query}")
    print(f"Years: {years}")
    print(f"Max papers: {max_papers}")
    print()
    
    print("Testing arXiv search...")
    try:
        arxiv_papers = await search_arxiv(query, max_papers, years)
        print(f"  arXiv found: {len(arxiv_papers)} papers")
        for i, p in enumerate(arxiv_papers[:3]):
            print(f"    {i+1}. {p.get('title', 'N/A')[:50]}...")
    except Exception as e:
        print(f"  arXiv error: {e}")
    
    print()
    print("Testing Semantic Scholar search...")
    try:
        ss_papers = await search_semantic_scholar(query, max_papers, years)
        print(f"  Semantic Scholar found: {len(ss_papers)} papers")
        for i, p in enumerate(ss_papers[:3]):
            print(f"    {i+1}. {p.get('title', 'N/A')[:50]}...")
    except Exception as e:
        print(f"  Semantic Scholar error: {e}")
    
    print()
    print("Testing PubMed search...")
    try:
        pubmed_papers = await search_pubmed(query, max_papers, years)
        print(f"  PubMed found: {len(pubmed_papers)} papers")
        for i, p in enumerate(pubmed_papers[:3]):
            print(f"    {i+1}. {p.get('title', 'N/A')[:50]}...")
    except Exception as e:
        print(f"  PubMed error: {e}")
    
    print()
    print("Testing all sources search...")
    try:
        all_papers = await search_all_sources(query, years, max_papers)
        print(f"  Total found: {len(all_papers)} papers")
        for i, p in enumerate(all_papers[:5]):
            print(f"    {i+1}. [{p.get('source', 'N/A')}] {p.get('title', 'N/A')[:60]}...")
    except Exception as e:
        print(f"  All sources error: {e}")
    
    print()
    print("-" * 60)
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(test_search())
