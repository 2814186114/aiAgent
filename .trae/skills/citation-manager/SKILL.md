---
name: "citation-manager"
description: "参考文献格式化，支持BibTeX、APA、MLA等多种格式。当用户需要管理参考文献、格式化引用或生成文献列表时调用。"
---

# 参考文献管理助手 (Citation Manager)

帮助硕博研究生规范管理参考文献的技能。

## 主要功能

### 1. 格式转换
- BibTeX格式生成
- APA格式转换
- MLA格式转换
- GB/T 7714格式（中文标准）

### 2. 引用生成
- 文内引用格式
- 参考文献列表
- 引用格式检查

### 3. 文献信息提取
- 从DOI获取文献信息
- 从标题搜索文献
- 自动补全信息

## 常用引用格式

### APA 格式 (第7版)

**期刊论文**
```
作者姓, 名首字母. (年份). 文章标题. 期刊名称(斜体), 卷号(期号), 页码. DOI

示例：
Zhang, Y., & Li, M. (2023). Deep learning for image recognition. 
Nature Machine Intelligence, 5(2), 123-135. https://doi.org/10.1038/xxx
```

**会议论文**
```
作者姓, 名首字母. (年份, 月份). 文章标题. 会议名称, 页码.

示例：
Wang, L., et al. (2023, June). A novel approach to NLP. 
Proceedings of ACL 2023, 456-465.
```

**书籍**
```
作者姓, 名首字母. (年份). 书名(斜体). 出版社.

示例：
Goodfellow, I., Bengio, Y., & Courville, A. (2016). 
Deep learning. MIT Press.
```

### GB/T 7714 格式（中文标准）

**期刊论文**
```
[序号] 作者. 文章标题[J]. 期刊名, 年, 卷(期): 起止页码.

示例：
[1] 张三, 李四. 深度学习研究进展[J]. 计算机学报, 2023, 46(2): 123-135.
```

**学位论文**
```
[序号] 作者. 论文标题[D]. 保存地: 保存单位, 年份.

示例：
[2] 王五. 自然语言处理方法研究[D]. 北京: 清华大学, 2023.
```

### BibTeX 格式

**期刊论文**
```bibtex
@article{zhang2023deep,
  author = {Zhang, Yu and Li, Ming},
  title = {Deep Learning for Image Recognition},
  journal = {Nature Machine Intelligence},
  year = {2023},
  volume = {5},
  number = {2},
  pages = {123--135},
  doi = {10.1038/xxx}
}
```

**会议论文**
```bibtex
@inproceedings{wang2023novel,
  author = {Wang, Lei and Chen, Wei and Zhang, Hua},
  title = {A Novel Approach to NLP},
  booktitle = {Proceedings of ACL 2023},
  year = {2023},
  month = {June},
  pages = {456--465}
}
```

**书籍**
```bibtex
@book{goodfellow2016deep,
  author = {Goodfellow, Ian and Bengio, Yoshua and Courville, Aaron},
  title = {Deep Learning},
  publisher = {MIT Press},
  year = {2016}
}
```

## 文内引用格式

### APA 格式
```
单作者：(Zhang, 2023)
双作者：(Zhang & Li, 2023)
三位及以上：(Zhang et al., 2023)
直接引用：(Zhang, 2023, p. 45)
```

### GB/T 7714 格式
```
单篇：[1]
多篇：[1, 3, 5]
连续：[1-5]
```

## 引用规范要点

### 1. 作者姓名
- 英文：姓在前，名用首字母
- 中文：保持原顺序
- 多作者：使用 et al. 或 等

### 2. 标题格式
- 英文：句首大写，其余小写（专有名词除外）
- 中文：正常书写

### 3. 期刊名称
- 英文：使用全称或标准缩写
- 中文：使用全称

### 4. DOI/URL
- 优先提供DOI
- 无DOI时提供URL
- 确保链接可访问

## 常见问题处理

| 问题 | 解决方案 |
|------|----------|
| 作者过多 | 列前几位作者 + et al. |
| 无年份 | 使用 n.d. (no date) |
| 无作者 | 使用标题替代 |
| 在线优先 | 标注 "Advance online publication" |

## 适用场景

- 论文投稿准备
- 学位论文撰写
- 文献管理
- 参考文献格式检查
