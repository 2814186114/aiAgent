---
name: "experiment-analyzer"
description: "实验数据分析、统计检验和结果解读。当用户需要分析实验数据、进行统计检验或解读实验结果时调用。"
---

# 实验分析助手 (Experiment Analyzer)

帮助硕博研究生进行实验数据分析和统计检验的技能。

## 主要功能

### 1. 描述性统计
- 均值、中位数、标准差
- 数据分布特征
- 异常值检测

### 2. 统计检验
- 参数检验（t检验、ANOVA）
- 非参数检验（Mann-Whitney、Kruskal-Wallis）
- 相关性分析

### 3. 效应量计算
- Cohen's d
- η² (Eta squared)
- 相关系数

### 4. 结果解读
- 统计显著性解释
- 实际意义评估
- 结果报告撰写

## 常用统计方法

### 1. 比较两组

| 数据类型 | 正态分布 | 检验方法 |
|----------|----------|----------|
| 连续数据 | 是 | 独立样本t检验 |
| 连续数据 | 否 | Mann-Whitney U检验 |
| 配对数据 | 是 | 配对t检验 |
| 配对数据 | 否 | Wilcoxon符号秩检验 |
| 分类数据 | - | 卡方检验 |

### 2. 比较多组

| 数据类型 | 正态分布 | 检验方法 |
|----------|----------|----------|
| 连续数据 | 是 | 单因素ANOVA |
| 连续数据 | 否 | Kruskal-Wallis检验 |
| 重复测量 | 是 | 重复测量ANOVA |
| 重复测量 | 否 | Friedman检验 |

### 3. 相关性分析

| 数据类型 | 检验方法 |
|----------|----------|
| 连续数据（正态） | Pearson相关 |
| 连续数据（非正态） | Spearman相关 |
| 有序分类数据 | Kendall's tau |

## Python 代码模板

### 正态性检验
```python
from scipy import stats
import numpy as np

data = np.array([...])

# Shapiro-Wilk检验
stat, p = stats.shapiro(data)
print(f'Shapiro-Wilk: W={stat:.4f}, p={p:.4f}')

# 如果 p > 0.05，不能拒绝正态分布假设
```

### 独立样本t检验
```python
from scipy import stats

group_a = [85, 78, 92, 88, 76]
group_b = [72, 85, 80, 75, 68]

# 方差齐性检验
levene_stat, levene_p = stats.levene(group_a, group_b)

# t检验
t_stat, p_value = stats.ttest_ind(group_a, group_b, 
                                   equal_var=(levene_p > 0.05))

# 效应量 (Cohen's d)
cohens_d = (np.mean(group_a) - np.mean(group_b)) / np.sqrt(
    (np.std(group_a, ddof=1)**2 + np.std(group_b, ddof=1)**2) / 2
)

print(f't={t_stat:.3f}, p={p_value:.4f}, Cohen\'s d={cohens_d:.3f}')
```

### 单因素ANOVA
```python
from scipy import stats
import numpy as np

group1 = [85, 78, 92, 88, 76]
group2 = [72, 85, 80, 75, 68]
group3 = [90, 82, 88, 92, 85]

# ANOVA
f_stat, p_value = stats.f_oneway(group1, group2, group3)

# 事后检验 (Tukey HSD)
from statsmodels.stats.multicomp import pairwise_tukeyhsd
data = group1 + group2 + group3
groups = ['A']*len(group1) + ['B']*len(group2) + ['C']*len(group3)
tukey = pairwise_tukeyhsd(data, groups)
print(tukey)
```

### 相关性分析
```python
from scipy import stats
import numpy as np

x = np.array([...])
y = np.array([...])

# Pearson相关
r, p = stats.pearsonr(x, y)
print(f'Pearson r={r:.3f}, p={p:.4f}')

# Spearman相关
rho, p = stats.spearmanr(x, y)
print(f'Spearman ρ={rho:.3f}, p={p:.4f}')
```

## 统计结果报告格式

### APA格式

**t检验**
```
结果显示，A组得分(M=83.8, SD=6.5)显著高于B组(M=76.0, SD=6.4)，
t(8)=2.15, p=0.046, Cohen's d=1.20。
```

**ANOVA**
```
单因素方差分析显示，三组之间存在显著差异，F(2, 12)=5.23, p=0.022, η²=0.47。
事后检验表明，A组显著高于B组(p=0.03)，其他比较不显著。
```

**相关分析**
```
X与Y之间存在显著正相关，r=0.78, p<0.001，表明X越高，Y也越高。
```

## 效应量解释

| Cohen's d | 解释 |
|-----------|------|
| 0.2 | 小效应 |
| 0.5 | 中等效应 |
| 0.8 | 大效应 |

| η² | 解释 |
|-----|------|
| 0.01 | 小效应 |
| 0.06 | 中等效应 |
| 0.14 | 大效应 |

| r | 解释 |
|-----|------|
| 0.1 | 小效应 |
| 0.3 | 中等效应 |
| 0.5 | 大效应 |

## 适用场景

- 实验数据分析
- 统计检验选择
- 结果报告撰写
- 论文方法部分
