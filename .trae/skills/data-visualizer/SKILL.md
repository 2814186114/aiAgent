---
name: "data-visualizer"
description: "数据可视化、图表生成，支持Python/Matplotlib/ECharts等。当用户需要绑制图表、可视化数据或美化图形时调用。"
---

# 数据可视化助手 (Data Visualizer)

帮助硕博研究生创建专业、美观的数据可视化图表的技能。

## 主要功能

### 1. 图表类型选择
- 根据数据特点推荐合适的图表类型
- 考虑数据维度和展示目的
- 遵循可视化最佳实践

### 2. 代码生成
- Python Matplotlib/Seaborn 代码
- ECharts 配置代码
- R ggplot2 代码
- Origin 绘图指导

### 3. 图表美化
- 配色方案优化
- 字体和标签调整
- 布局优化

### 4. 学术规范
- 符合期刊要求的图表规格
- 分辨率和格式设置
- 图例和标注规范

## 常用图表类型

### 1. 比较类
| 图表类型 | 适用场景 | 数据特点 |
|----------|----------|----------|
| 柱状图 | 类别比较 | 离散数据 |
| 条形图 | 类别比较（类别多） | 离散数据 |
| 雷达图 | 多维比较 | 多指标对比 |
| 热力图 | 矩阵数据比较 | 二维数据 |

### 2. 趋势类
| 图表类型 | 适用场景 | 数据特点 |
|----------|----------|----------|
| 折线图 | 时间序列 | 连续数据 |
| 面积图 | 趋势+量 | 连续数据 |
| 散点图 | 相关性分析 | 双变量 |

### 3. 分布类
| 图表类型 | 适用场景 | 数据特点 |
|----------|----------|----------|
| 直方图 | 频率分布 | 单变量 |
| 箱线图 | 分布比较 | 多组数据 |
| 小提琴图 | 分布形态 | 多组数据 |
| 密度图 | 概率分布 | 连续数据 |

### 4. 关系类
| 图表类型 | 适用场景 | 数据特点 |
|----------|----------|----------|
| 散点图 | 相关性 | 双变量 |
| 气泡图 | 三维关系 | 三变量 |
| 相关矩阵 | 多变量相关 | 多变量 |

## Python 代码模板

### 基础折线图
```python
import matplotlib.pyplot as plt
import numpy as np

plt.figure(figsize=(10, 6))
plt.rcParams['font.family'] = ['SimHei']  # 中文支持
plt.rcParams['axes.unicode_minus'] = False

x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

plt.plot(x, y1, label='方法A', linewidth=2, color='#2E86AB')
plt.plot(x, y2, label='方法B', linewidth=2, color='#A23B72')

plt.xlabel('X轴标签', fontsize=12)
plt.ylabel('Y轴标签', fontsize=12)
plt.title('图表标题', fontsize=14)
plt.legend(loc='best', fontsize=10)
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('figure.pdf', dpi=300, bbox_inches='tight')
plt.show()
```

### 分组柱状图
```python
import matplotlib.pyplot as plt
import numpy as np

categories = ['类别1', '类别2', '类别3', '类别4']
method_a = [85, 78, 92, 88]
method_b = [72, 85, 80, 75]
method_c = [90, 82, 88, 92]

x = np.arange(len(categories))
width = 0.25

fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(x - width, method_a, width, label='方法A', color='#2E86AB')
ax.bar(x, method_b, width, label='方法B', color='#A23B72')
ax.bar(x + width, method_c, width, label='方法C', color='#F18F01')

ax.set_xlabel('类别', fontsize=12)
ax.set_ylabel('准确率 (%)', fontsize=12)
ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.legend()
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig('bar_chart.pdf', dpi=300)
plt.show()
```

### 热力图
```python
import seaborn as sns
import matplotlib.pyplot as plt

data = [[0.9, 0.7, 0.3],
        [0.7, 0.8, 0.5],
        [0.3, 0.5, 0.95]]

plt.figure(figsize=(8, 6))
sns.heatmap(data, annot=True, cmap='YlOrRd', 
            xticklabels=['A', 'B', 'C'],
            yticklabels=['X', 'Y', 'Z'])
plt.title('相关性热力图')
plt.tight_layout()
plt.savefig('heatmap.pdf', dpi=300)
plt.show()
```

## 学术图表规范

### 1. 尺寸要求
- 单栏图：宽度 3.5 英寸
- 双栏图：宽度 7 英寸
- 高度根据内容调整

### 2. 分辨率
- 矢量图：PDF、EPS、SVG（推荐）
- 位图：300 DPI 以上

### 3. 字体
- 建议使用无衬线字体（Arial、Helvetica）
- 字号不小于 8pt

### 4. 配色
- 避免使用红绿组合（色盲友好）
- 使用对比度高的配色
- 黑白打印时需可区分

## 适用场景

- 论文图表制作
- 实验结果展示
- 数据分析报告
- 学术海报制作
