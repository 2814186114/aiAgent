import os
import re
import asyncio
from typing import Dict, Any, List, Optional

try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None

try:
    from .reading_history import add_reading_history
    READING_HISTORY_AVAILABLE = True
except ImportError:
    READING_HISTORY_AVAILABLE = False

SECTION_PATTERNS = {
    'abstract': [
        r'^abstract\s*$',
        r'^摘要\s*$',
        r'^abstract\s*[:\.]',
        r'^摘要\s*[:\.]',
    ],
    'introduction': [
        r'^1\.?\s*introduction\s*$',
        r'^1\.?\s*引言\s*$',
        r'^1\.?\s*introduction',
        r'^introduction\s*$',
    ],
    'method': [
        r'^\d+\.?\s*method(s)?\s*$',
        r'^\d+\.?\s*methodology\s*$',
        r'^\d+\.?\s*approach\s*$',
        r'^\d+\.?\s*方法\s*$',
        r'^\d+\.?\s*模型\s*$',
        r'^\d+\.?\s*method',
        r'^method\s*$',
    ],
    'experiment': [
        r'^\d+\.?\s*experiment(s)?\s*$',
        r'^\d+\.?\s*evaluation\s*$',
        r'^\d+\.?\s*实验\s*$',
        r'^\d+\.?\s*评估\s*$',
        r'^\d+\.?\s*experiment',
        r'^experiment\s*$',
    ],
    'result': [
        r'^\d+\.?\s*result(s)?\s*$',
        r'^\d+\.?\s*结果\s*$',
        r'^\d+\.?\s*result',
    ],
    'discussion': [
        r'^\d+\.?\s*discussion\s*$',
        r'^\d+\.?\s*讨论\s*$',
        r'^\d+\.?\s*analysis\s*$',
    ],
    'conclusion': [
        r'^\d+\.?\s*conclusion(s)?\s*$',
        r'^\d+\.?\s*结论\s*$',
        r'^\d+\.?\s*conclusion',
        r'^conclusion\s*$',
    ],
    'reference': [
        r'^\d+\.?\s*reference(s)?\s*$',
        r'^\d+\.?\s*参考文献\s*$',
        r'^references?\s*$',
    ],
}

def extract_title(text: str) -> Optional[str]:
    lines = text.strip().split('\n')
    for line in lines[:10]:
        line = line.strip()
        if line and len(line) > 5 and len(line) < 200:
            if not any(kw in line.lower() for kw in ['abstract', '摘要', 'arxiv', 'http', '©', 'copyright']):
                return line
    return None

def extract_authors(text: str) -> List[str]:
    authors = []
    lines = text.strip().split('\n')
    
    for i, line in enumerate(lines[:15]):
        line = line.strip()
        if not line or len(line) < 3:
            continue
            
        if re.search(r'[a-zA-Z]+\s+[A-Z]\.?\s+[a-zA-Z]+', line):
            potential_authors = re.findall(r'[A-Z][a-z]+\s+[A-Z]\.?\s+[A-Z][a-z]+|[A-Z][a-z]+\s+[A-Z][a-z]+', line)
            authors.extend(potential_authors)
            
        if re.search(r'[\u4e00-\u9fa5]{2,4}\s*[，,、]', line):
            potential_authors = re.findall(r'[\u4e00-\u9fa5]{2,4}', line)
            authors.extend(potential_authors)
    
    seen = set()
    unique_authors = []
    for a in authors:
        if a not in seen and len(a) > 1:
            seen.add(a)
            unique_authors.append(a)
    
    return unique_authors[:10]

def extract_section(text: str, section_type: str) -> Optional[str]:
    patterns = SECTION_PATTERNS.get(section_type, [])
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            start = match.end()
            
            next_section = None
            for other_patterns in SECTION_PATTERNS.values():
                for other_pattern in other_patterns:
                    other_match = re.search(other_pattern, text[start:], re.IGNORECASE | re.MULTILINE)
                    if other_match:
                        if next_section is None or other_match.start() < next_section:
                            next_section = other_match.start()
            
            if next_section:
                section_text = text[start:start + next_section]
            else:
                section_text = text[start:start + 3000]
            
            return section_text.strip()[:2000]
    
    return None

def extract_key_info(text: str) -> Dict[str, Any]:
    key_info = {
        'metrics': [],
        'datasets': [],
        'models': [],
        'key_numbers': [],
    }
    
    metric_patterns = [
        r'accuracy[:\s]+(\d+\.?\d*%?)',
        r'F1[:\s]+(\d+\.?\d*%?)',
        r'precision[:\s]+(\d+\.?\d*%?)',
        r'recall[:\s]+(\d+\.?\d*%?)',
        r'BLEU[:\s]+(\d+\.?\d*%?)',
        r'准确率[:\s]+(\d+\.?\d*%?)',
        r'(\d+\.?\d*)\s*%',
    ]
    
    for pattern in metric_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        key_info['metrics'].extend(matches[:5])
    
    dataset_keywords = ['ImageNet', 'COCO', 'SQuAD', 'GLUE', 'MNIST', 'CIFAR', 
                       'WikiText', 'Penn Treebank', 'SST-2', 'SST-2', 'CoNLL',
                       '数据集', 'dataset']
    for kw in dataset_keywords:
        if kw.lower() in text.lower():
            key_info['datasets'].append(kw)
    
    model_patterns = [
        r'\b(BERT|GPT[-\d]*|T5|RoBERTa|XLNet|ALBERT|ELECTRA|Transformer|ResNet|VGG|Inception|EfficientNet|YOLO|GAN|VAE|LSTM|GRU|CNN|RNN)\b'
    ]
    for pattern in model_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        key_info['models'].extend(list(set(matches))[:5])
    
    number_patterns = [
        r'(\d+\.?\d*)\s*(million|billion|M|B|parameters|params)',
        r'(\d+\.?\d*)\s*(layers|layer)',
        r'(\d+\.?\d*)\s*(epochs|epoch)',
    ]
    for pattern in number_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            key_info['key_numbers'].append(f"{match[0]} {match[1]}")
    
    key_info['datasets'] = list(set(key_info['datasets']))[:5]
    key_info['models'] = list(set(key_info['models']))[:5]
    key_info['metrics'] = list(set(key_info['metrics']))[:5]
    key_info['key_numbers'] = list(set(key_info['key_numbers']))[:5]
    
    return key_info

def parse_paper_structure(text: str) -> Dict[str, Any]:
    structure = {
        'title': extract_title(text),
        'authors': extract_authors(text),
        'abstract': extract_section(text, 'abstract'),
        'introduction': extract_section(text, 'introduction'),
        'method': extract_section(text, 'method'),
        'experiment': extract_section(text, 'experiment'),
        'result': extract_section(text, 'result'),
        'conclusion': extract_section(text, 'conclusion'),
        'key_info': extract_key_info(text),
    }
    
    return structure

async def read_pdf(file_path: str, max_chars: int = 5000, parse_structure: bool = True) -> Dict[str, Any]:
    if not PYMUPDF_AVAILABLE:
        return {
            "success": False,
            "error": "PyMuPDF 未安装，请运行: pip install pymupdf",
        }
    
    if not os.path.exists(file_path):
        return {
            "success": False,
            "error": f"文件不存在: {file_path}",
        }
    
    if not os.path.isfile(file_path):
        return {
            "success": False,
            "error": f"不是文件: {file_path}",
        }
    
    try:
        doc = fitz.open(file_path)
        total_pages = len(doc)
        full_text = ""
        
        for page_num in range(total_pages):
            page = doc[page_num]
            full_text += page.get_text()
        
        doc.close()
        
        result = {
            "success": True,
            "file_path": file_path,
            "total_pages": total_pages,
            "chars_extracted": len(full_text),
            "summary": full_text[:max_chars],
        }
        
        if parse_structure:
            structure = parse_paper_structure(full_text)
            result["structure"] = structure
            
            result["paper_summary"] = {
                "title": structure.get("title"),
                "authors": structure.get("authors", [])[:5],
                "has_abstract": bool(structure.get("abstract")),
                "has_method": bool(structure.get("method")),
                "has_experiment": bool(structure.get("experiment")),
                "key_metrics": structure.get("key_info", {}).get("metrics", [])[:3],
                "datasets": structure.get("key_info", {}).get("datasets", [])[:3],
                "models": structure.get("key_info", {}).get("models", [])[:3],
            }
            
            if structure.get("abstract"):
                result["abstract"] = structure["abstract"][:1000]
            
            if structure.get("method"):
                result["method_summary"] = structure["method"][:1500]
            
            if structure.get("conclusion"):
                result["conclusion"] = structure["conclusion"][:1000]
        
        if READING_HISTORY_AVAILABLE:
            try:
                title = result.get("paper_summary", {}).get("title") or os.path.basename(file_path)
                await add_reading_history(
                    file_path=file_path,
                    title=title,
                    summary=result.get("abstract", full_text[:500]),
                    total_pages=total_pages,
                    source="pdf"
                )
            except:
                pass
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"PDF读取失败: {str(e)}",
        }

async def analyze_paper(file_path: str) -> Dict[str, Any]:
    result = await read_pdf(file_path, max_chars=50000, parse_structure=True)
    
    if not result.get("success"):
        return result
    
    structure = result.get("structure", {})
    key_info = structure.get("key_info", {})
    
    analysis = {
        "success": True,
        "file_path": file_path,
        "title": structure.get("title"),
        "authors": structure.get("authors", [])[:10],
        "total_pages": result.get("total_pages"),
        
        "main_contributions": [],
        "methodology": None,
        "key_results": [],
        "limitations": [],
        
        "datasets_used": key_info.get("datasets", []),
        "models_mentioned": key_info.get("models", []),
        "metrics_reported": key_info.get("metrics", []),
    }
    
    if structure.get("abstract"):
        abstract = structure["abstract"]
        sentences = re.split(r'[.!?。！？]', abstract)
        for sentence in sentences:
            if any(kw in sentence.lower() for kw in ['propose', 'present', 'introduce', '提出', '介绍']):
                analysis["main_contributions"].append(sentence.strip())
        analysis["main_contributions"] = analysis["main_contributions"][:3]
    
    if structure.get("method"):
        analysis["methodology"] = structure["method"][:500]
    
    if structure.get("result"):
        result_text = structure["result"]
        for pattern in [r'(\d+\.?\d*)\s*%', r'achieve[s]?\s+(\d+\.?\d*)']:
            matches = re.findall(pattern, result_text)
            analysis["key_results"].extend(matches[:5])
    
    return analysis

async def download_pdf(url: str, save_path: str) -> Dict[str, Any]:
    try:
        import httpx
        
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, "wb") as f:
                f.write(response.content)
            
            return {
                "success": True,
                "url": url,
                "save_path": save_path,
                "file_size": os.path.getsize(save_path),
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"下载失败: {str(e)}",
        }
