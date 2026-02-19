import os
import sys
import asyncio
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

_lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python_libs")
if os.path.exists(_lib_path):
    sys.path.insert(0, _lib_path)

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"

async def search_papers_for_review(
    query: str, 
    limit: int = 20,
    year_range: Optional[str] = None
) -> Dict[str, Any]:
    try:
        from .multi_source_search import get_sample_papers
        papers = get_sample_papers(query, min(limit, 10))
        
        return {
            "success": True,
            "papers": papers,
            "total": len(papers),
            "query": query
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "success": False,
            "error": f"搜索失败: {str(e)}",
            "papers": []
        }

async def get_paper_citations(paper_id: str, limit: int = 50) -> Dict[str, Any]:
    if not HTTPX_AVAILABLE:
        return {
            "success": False,
            "error": "httpx 未安装",
            "citations": []
        }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{SEMANTIC_SCHOLAR_API}/paper/{paper_id}/citations",
                params={
                    "fields": "paperId,title,authors,year,abstract,citationCount",
                    "limit": limit
                }
            )
            response.raise_for_status()
            data = response.json()
            
            citations = []
            for item in data.get("data", []):
                paper = item.get("citingPaper", {})
                authors = [a.get("name", "") for a in paper.get("authors", [])]
                citations.append({
                    "paper_id": paper.get("paperId"),
                    "title": paper.get("title"),
                    "authors": authors,
                    "year": paper.get("year"),
                    "abstract": paper.get("abstract"),
                    "citation_count": paper.get("citationCount", 0)
                })
            
            return {
                "success": True,
                "citations": citations,
                "total": len(citations)
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"获取引用失败: {str(e)}",
            "citations": []
        }

async def get_paper_references(paper_id: str, limit: int = 50) -> Dict[str, Any]:
    if not HTTPX_AVAILABLE:
        return {
            "success": False,
            "error": "httpx 未安装",
            "references": []
        }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{SEMANTIC_SCHOLAR_API}/paper/{paper_id}/references",
                params={
                    "fields": "paperId,title,authors,year,abstract,citationCount",
                    "limit": limit
                }
            )
            response.raise_for_status()
            data = response.json()
            
            references = []
            for item in data.get("data", []):
                paper = item.get("citedPaper", {})
                if paper.get("paperId"):
                    authors = [a.get("name", "") for a in paper.get("authors", [])]
                    references.append({
                        "paper_id": paper.get("paperId"),
                        "title": paper.get("title"),
                        "authors": authors,
                        "year": paper.get("year"),
                        "abstract": paper.get("abstract"),
                        "citation_count": paper.get("citationCount", 0)
                    })
            
            return {
                "success": True,
                "references": references,
                "total": len(references)
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"获取参考文献失败: {str(e)}",
            "references": []
        }

def extract_key_concepts(abstracts: List[str]) -> List[str]:
    concepts = []
    
    concept_patterns = [
        r'\b([A-Z][a-z]+(?:\s+[a-z]+)?)\s+(?:model|method|approach|framework|network|architecture)\b',
        r'\b(?:propose|present|introduce|develop)\s+(?:a\s+)?([a-zA-Z-]+)',
        r'\b([A-Z]{2,})\b',
    ]
    
    for abstract in abstracts:
        if not abstract:
            continue
        for pattern in concept_patterns:
            matches = re.findall(pattern, abstract)
            concepts.extend(matches)
    
    concept_count = {}
    for c in concepts:
        c_lower = c.lower()
        if len(c_lower) > 2:
            concept_count[c_lower] = concept_count.get(c_lower, 0) + 1
    
    sorted_concepts = sorted(concept_count.items(), key=lambda x: -x[1])
    return [c[0] for c in sorted_concepts[:20]]

def categorize_papers_by_year(papers: List[Dict]) -> Dict[str, List[Dict]]:
    by_year = {}
    for paper in papers:
        year = paper.get("year")
        if year:
            year_str = str(year)
            if year_str not in by_year:
                by_year[year_str] = []
            by_year[year_str].append(paper)
    return dict(sorted(by_year.items()))

def find_highly_cited_papers(papers: List[Dict], threshold: int = 100) -> List[Dict]:
    highly_cited = []
    for paper in papers:
        if paper.get("citation_count", 0) >= threshold:
            highly_cited.append(paper)
    return sorted(highly_cited, key=lambda x: -x.get("citation_count", 0))

def generate_timeline(papers: List[Dict]) -> List[Dict]:
    by_year = categorize_papers_by_year(papers)
    timeline = []
    
    for year, year_papers in by_year.items():
        milestones = []
        for paper in year_papers[:3]:
            if paper.get("title"):
                milestones.append({
                    "title": paper["title"],
                    "authors": paper.get("authors", [])[:2],
                    "citations": paper.get("citation_count", 0)
                })
        
        timeline.append({
            "year": year,
            "paper_count": len(year_papers),
            "milestones": milestones
        })
    
    return timeline

async def generate_literature_review(
    query: str,
    paper_limit: int = 15,
    include_citations: bool = False
) -> Dict[str, Any]:
    search_result = await search_papers_for_review(query, limit=paper_limit)
    
    if not search_result.get("success"):
        return search_result
    
    papers = search_result.get("papers", [])
    
    if not papers:
        return {
            "success": False,
            "error": "未找到相关论文",
            "query": query
        }
    
    abstracts = [p.get("abstract", "") for p in papers if p.get("abstract")]
    key_concepts = extract_key_concepts(abstracts)
    
    timeline = generate_timeline(papers)
    
    highly_cited = find_highly_cited_papers(papers, threshold=50)
    
    citation_network = {}
    if include_citations and highly_cited:
        top_paper = highly_cited[0]
        if top_paper.get("paper_id"):
            citations = await get_paper_citations(top_paper["paper_id"], limit=20)
            if citations.get("success"):
                citation_network["top_paper"] = top_paper.get("title")
                citation_network["citation_count"] = len(citations.get("citations", []))
                citation_network["recent_citations"] = [
                    {"title": c["title"], "year": c.get("year")}
                    for c in citations.get("citations", [])[:5]
                ]
    
    review_sections = []
    
    if highly_cited:
        section = {
            "title": "高影响力论文",
            "papers": [
                {
                    "title": p.get("title"),
                    "authors": p.get("authors", [])[:3],
                    "year": p.get("year"),
                    "citations": p.get("citation_count", 0),
                    "venue": p.get("venue")
                }
                for p in highly_cited[:5]
            ]
        }
        review_sections.append(section)
    
    if timeline:
        recent_years = timeline[-3:] if len(timeline) > 3 else timeline
        section = {
            "title": "最新进展",
            "timeline": recent_years
        }
        review_sections.append(section)
    
    if key_concepts:
        section = {
            "title": "核心概念与方法",
            "concepts": key_concepts[:10]
        }
        review_sections.append(section)
    
    summary = f"基于「{query}」主题，共检索到 {len(papers)} 篇相关论文。\n\n"
    
    if highly_cited:
        summary += f"**高影响力论文**: {len(highly_cited)} 篇引用超过50次的论文。\n"
    
    if timeline:
        years = [t["year"] for t in timeline]
        summary += f"**时间跨度**: {min(years)} - {max(years)}\n"
    
    if key_concepts:
        summary += f"**核心概念**: {', '.join(key_concepts[:5])}\n"
    
    return {
        "success": True,
        "query": query,
        "summary": summary,
        "total_papers": len(papers),
        "papers": papers,
        "review_sections": review_sections,
        "timeline": timeline,
        "key_concepts": key_concepts,
        "highly_cited_papers": highly_cited,
        "citation_network": citation_network if include_citations else None,
        "generated_at": datetime.now().isoformat()
    }

async def analyze_research_trends(query: str, years: int = 5) -> Dict[str, Any]:
    current_year = datetime.now().year
    year_range = f"{current_year - years}-{current_year}"
    
    search_result = await search_papers_for_review(query, limit=50, year_range=year_range)
    
    if not search_result.get("success"):
        return search_result
    
    papers = search_result.get("papers", [])
    
    by_year = categorize_papers_by_year(papers)
    
    trend_data = []
    for year, year_papers in sorted(by_year.items()):
        total_citations = sum(p.get("citation_count", 0) for p in year_papers)
        trend_data.append({
            "year": year,
            "paper_count": len(year_papers),
            "total_citations": total_citations,
            "avg_citations": total_citations / len(year_papers) if year_papers else 0
        })
    
    abstracts = [p.get("abstract", "") for p in papers if p.get("abstract")]
    key_concepts = extract_key_concepts(abstracts)
    
    venues = {}
    for paper in papers:
        venue = paper.get("venue")
        if venue:
            venues[venue] = venues.get(venue, 0) + 1
    
    top_venues = sorted(venues.items(), key=lambda x: -x[1])[:10]
    
    return {
        "success": True,
        "query": query,
        "year_range": year_range,
        "trend_data": trend_data,
        "key_concepts": key_concepts[:15],
        "top_venues": [{"venue": v[0], "count": v[1]} for v in top_venues],
        "total_papers": len(papers),
        "generated_at": datetime.now().isoformat()
    }

async def find_research_gaps(query: str) -> Dict[str, Any]:
    search_result = await search_papers_for_review(query, limit=30)
    
    if not search_result.get("success"):
        return search_result
    
    papers = search_result.get("papers", [])
    
    abstracts = [p.get("abstract", "") for p in papers if p.get("abstract")]
    
    gap_indicators = [
        (r'however,?\s+([^.]+(?:limitation|challenge|problem|gap|lack|need)[^.]*)', '局限性'),
        (r'(?:remain|remains)\s+([^.]+(?:open|unsolved|unclear|unknown)[^.]*)', '未解决问题'),
        (r'future\s+(?:work|research|study)[^.]*(?:should|could|need|may)\s+([^.]+)', '未来方向'),
        (r'(?:lack|lacking|limited)\s+(?:of\s+)?([^.]+)', '研究不足'),
    ]
    
    potential_gaps = []
    
    for abstract in abstracts:
        for pattern, gap_type in gap_indicators:
            matches = re.findall(pattern, abstract, re.IGNORECASE)
            for match in matches:
                potential_gaps.append({
                    "type": gap_type,
                    "description": match.strip()[:200],
                    "source_abstract": abstract[:100] + "..."
                })
    
    unique_gaps = []
    seen = set()
    for gap in potential_gaps:
        key = gap["description"][:50]
        if key not in seen:
            seen.add(key)
            unique_gaps.append(gap)
    
    abstracts_text = " ".join(abstracts)
    
    common_methods = re.findall(
        r'\b(?:using|with|by|via|through)\s+([a-zA-Z-]+(?:\s+[a-zA-Z-]+)?)\s+(?:method|approach|model|framework|technique)',
        abstracts_text,
        re.IGNORECASE
    )
    
    method_freq = {}
    for m in common_methods:
        m_lower = m.lower()
        method_freq[m_lower] = method_freq.get(m_lower, 0) + 1
    
    popular_methods = sorted(method_freq.items(), key=lambda x: -x[1])[:10]
    
    return {
        "success": True,
        "query": query,
        "potential_gaps": unique_gaps[:10],
        "popular_methods": [{"method": m[0], "frequency": m[1]} for m in popular_methods],
        "total_papers_analyzed": len(papers),
        "generated_at": datetime.now().isoformat()
    }
