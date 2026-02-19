import os
import sys
import json
import re
from typing import Dict, Any, List, Optional
from collections import Counter

_lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python_libs")
if os.path.exists(_lib_path):
    sys.path.insert(0, _lib_path)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

def extract_keywords_from_papers(papers: List[Dict], top_n: int = 20) -> List[str]:
    all_text = ""
    for paper in papers:
        all_text += paper.get("title", "") + " "
        all_text += paper.get("abstract", "") + " "
    
    words = re.findall(r'\b[a-zA-Z]{3,}\b', all_text.lower())
    
    stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 
                  'had', 'her', 'was', 'one', 'our', 'out', 'has', 'have', 'been',
                  'this', 'that', 'with', 'from', 'they', 'will', 'would', 'there',
                  'their', 'what', 'about', 'which', 'when', 'make', 'like', 'into',
                  'than', 'them', 'these', 'some', 'such', 'only', 'also', 'more',
                  'very', 'over', 'after', 'most', 'other', 'then', 'were', 'being',
                  'through', 'where', 'while', 'using', 'used', 'use', 'may', 'can',
                  'could', 'should', 'must', 'might', 'shall'}
    
    filtered = [w for w in words if w not in stop_words and len(w) > 3]
    
    word_freq = Counter(filtered)
    return [w for w, _ in word_freq.most_common(top_n)]

def cluster_by_keywords(papers: List[Dict], num_clusters: int = 5) -> List[Dict]:
    if not papers:
        return []
    
    clusters = {}
    
    topic_keywords = {
        "方法创新": ["method", "approach", "algorithm", "framework", "model", "architecture", "novel", "new"],
        "实验评估": ["experiment", "evaluation", "benchmark", "dataset", "performance", "result", "accuracy"],
        "理论分析": ["theory", "theoretical", "analysis", "proof", "convergence", "bound", "guarantee"],
        "应用研究": ["application", "real-world", "practical", "system", "implementation", "deployment"],
        "数据驱动": ["data", "dataset", "training", "learning", "sample", "annotation", "label"],
        "深度学习": ["deep", "neural", "network", "learning", "transformer", "attention", "bert", "gpt"],
        "优化方法": ["optimization", "optimizer", "gradient", "loss", "training", "convergence"],
        "生成模型": ["generation", "generative", "synthesis", "gan", "vae", "diffusion"],
    }
    
    for paper in papers:
        text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
        
        best_cluster = "其他研究"
        best_score = 0
        
        for cluster_name, keywords in topic_keywords.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_cluster = cluster_name
        
        if best_cluster not in clusters:
            clusters[best_cluster] = {
                "name": best_cluster,
                "papers": [],
                "keywords": topic_keywords.get(best_cluster, [])
            }
        
        clusters[best_cluster]["papers"].append(paper)
    
    result = []
    for cluster_name, cluster_data in clusters.items():
        if cluster_data["papers"]:
            cluster_data["paper_count"] = len(cluster_data["papers"])
            result.append(cluster_data)
    
    result.sort(key=lambda x: x["paper_count"], reverse=True)
    
    return result[:num_clusters]

def cluster_by_tfidf(papers: List[Dict], num_clusters: int = 5) -> List[Dict]:
    if not SKLEARN_AVAILABLE or not NUMPY_AVAILABLE or len(papers) < num_clusters:
        return cluster_by_keywords(papers, num_clusters)
    
    try:
        documents = []
        for paper in papers:
            doc = paper.get("title", "") + " " + (paper.get("abstract", "") or "")
            documents.append(doc)
        
        vectorizer = TfidfVectorizer(
            max_features=100,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        tfidf_matrix = vectorizer.fit_transform(documents)
        
        kmeans = KMeans(n_clusters=min(num_clusters, len(papers)), random_state=42, n_init=10)
        clusters = kmeans.fit_predict(tfidf_matrix)
        
        feature_names = vectorizer.get_feature_names_out()
        
        cluster_papers = {i: [] for i in range(num_clusters)}
        for i, paper in enumerate(papers):
            cluster_id = clusters[i]
            cluster_papers[cluster_id].append(paper)
        
        result = []
        for cluster_id, cluster_paper_list in cluster_papers.items():
            if not cluster_paper_list:
                continue
            
            center = kmeans.cluster_centers_[cluster_id]
            top_indices = center.argsort()[-5:][::-1]
            keywords = [feature_names[i] for i in top_indices]
            
            cluster_name = " ".join(keywords[:3]).title()
            
            result.append({
                "name": cluster_name,
                "papers": cluster_paper_list,
                "paper_count": len(cluster_paper_list),
                "keywords": keywords
            })
        
        result.sort(key=lambda x: x["paper_count"], reverse=True)
        
        return result
        
    except Exception as e:
        print(f"TF-IDF clustering error: {e}")
        return cluster_by_keywords(papers, num_clusters)

async def cluster_papers(papers: List[Dict], llm_client=None, model=None) -> List[Dict]:
    if not papers:
        return []
    
    num_clusters = min(6, max(3, len(papers) // 8))
    
    clusters = cluster_by_tfidf(papers, num_clusters)
    
    if llm_client:
        try:
            clusters = await _refine_cluster_names(clusters, llm_client, model)
        except:
            pass
    
    return clusters

async def _refine_cluster_names(clusters: List[Dict], client, model: str) -> List[Dict]:
    if not client:
        return clusters
    
    for cluster in clusters:
        papers_sample = cluster.get("papers", [])[:3]
        titles = [p.get("title", "") for p in papers_sample]
        
        prompt = f"""基于以下论文标题，给出一个简洁的研究方向名称（5-10个字）：

{json.dumps(titles, ensure_ascii=False)}

只返回名称，不要其他内容。"""

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=20
            )
            new_name = response.choices[0].message.content.strip()
            if new_name and len(new_name) < 20:
                cluster["name"] = new_name
        except:
            pass
    
    return clusters

def build_citation_network(papers: List[Dict]) -> Dict[str, Any]:
    nodes = []
    edges = []
    
    for paper in papers:
        nodes.append({
            "id": paper.get("paper_id", ""),
            "title": paper.get("title", ""),
            "year": paper.get("year"),
            "citations": paper.get("citation_count", 0),
            "source": paper.get("source", "")
        })
    
    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_papers": len(papers),
            "total_citations": sum(p.get("citation_count", 0) for p in papers)
        }
    }

def build_concept_graph(papers: List[Dict]) -> Dict[str, Any]:
    concept_papers = {}
    
    for paper in papers:
        analysis = paper.get("analysis", {})
        keywords = analysis.get("keywords", [])
        methods = analysis.get("methods", [])
        
        all_concepts = keywords + methods
        
        for concept in all_concepts:
            if concept not in concept_papers:
                concept_papers[concept] = []
            concept_papers[concept].append(paper.get("paper_id", ""))
    
    nodes = []
    for concept, paper_ids in concept_papers.items():
        if len(paper_ids) >= 2:
            nodes.append({
                "id": concept,
                "label": concept,
                "weight": len(paper_ids),
                "papers": paper_ids
            })
    
    nodes.sort(key=lambda x: x["weight"], reverse=True)
    
    edges = []
    node_ids = {n["id"] for n in nodes[:30]}
    
    for i, node1 in enumerate(nodes[:30]):
        for node2 in nodes[i+1:30]:
            common = set(node1["papers"]) & set(node2["papers"])
            if common:
                edges.append({
                    "source": node1["id"],
                    "target": node2["id"],
                    "weight": len(common)
                })
    
    return {
        "nodes": nodes[:30],
        "edges": edges[:50]
    }
