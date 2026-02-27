---
name: "latex-helper"
description: "LaTeX公式、表格、排版问题解答和代码生成。当用户需要编写LaTeX代码、解决排版问题或生成数学公式时调用。"
---

# LaTeX 助手 (LaTeX Helper)

帮助硕博研究生解决LaTeX排版问题的专业技能。

## 主要功能

### 1. 数学公式
- 复杂公式编写
- 公式编号和引用
- 多行公式对齐
- 希腊字母和特殊符号

### 2. 表格制作
- 复杂表格设计
- 跨行跨列表格
- 表格美化
- 长表格处理

### 3. 图片插入
- 图片排版
- 子图排列
- 图片标注
- 浮动体控制

### 4. 文档结构
- 章节设置
- 目录生成
- 交叉引用
- 参考文献管理

## 常用公式模板

### 基础公式
```latex
% 行内公式
$E = mc^2$

% 行间公式
\begin{equation}
  f(x) = \int_{-\infty}^{\infty} e^{-x^2} dx
  \label{eq:gaussian}
\end{equation}

% 多行对齐
\begin{align}
  y &= x^2 + 2x + 1 \\
    &= (x+1)^2
\end{align}
```

### 矩阵
```latex
\begin{equation}
\mathbf{A} = \begin{bmatrix}
a_{11} & a_{12} & \cdots & a_{1n} \\
a_{21} & a_{22} & \cdots & a_{2n} \\
\vdots & \vdots & \ddots & \vdots \\
a_{m1} & a_{m2} & \cdots & a_{mn}
\end{bmatrix}
\end{equation}
```

### 分段函数
```latex
\begin{equation}
f(x) = \begin{cases}
  x^2, & x \geq 0 \\
  -x^2, & x < 0
\end{cases}
\end{equation}
```

## 常用表格模板

### 基础表格
```latex
\begin{table}[htbp]
  \centering
  \caption{实验结果对比}
  \label{tab:results}
  \begin{tabular}{lccc}
    \toprule
    方法 & 准确率 & 召回率 & F1值 \\
    \midrule
    方法A & 0.85 & 0.82 & 0.83 \\
    方法B & 0.88 & 0.86 & 0.87 \\
    本文方法 & \textbf{0.92} & \textbf{0.90} & \textbf{0.91} \\
    \bottomrule
  \end{tabular}
\end{table}
```

### 跨列表格
```latex
\begin{table}[htbp]
  \centering
  \begin{tabular}{l|cc|cc}
    \toprule
    & \multicolumn{2}{c|}{数据集A} & \multicolumn{2}{c}{数据集B} \\
    \cmidrule{2-5}
    方法 & 准确率 & F1值 & 准确率 & F1值 \\
    \midrule
    方法1 & 0.85 & 0.83 & 0.82 & 0.80 \\
    方法2 & 0.88 & 0.86 & 0.85 & 0.83 \\
    \bottomrule
  \end{tabular}
\end{table}
```

## 常用图片模板

### 单图
```latex
\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.8\textwidth]{figure1.pdf}
  \caption{实验结果示意图}
  \label{fig:result}
\end{figure}
```

### 子图排列
```latex
\begin{figure}[htbp]
  \centering
  \subfigure[子图标题1]{
    \includegraphics[width=0.45\textwidth]{fig1a.pdf}
  }
  \subfigure[子图标题2]{
    \includegraphics[width=0.45\textwidth]{fig1b.pdf}
  }
  \caption{总标题}
  \label{fig:subfigures}
\end{figure}
```

## 常用宏包

| 宏包 | 用途 |
|------|------|
| amsmath | 数学公式增强 |
| booktabs | 专业表格 |
| graphicx | 图片插入 |
| hyperref | 超链接 |
| xcolor | 颜色支持 |
| algorithm2e | 算法伪代码 |
| listings | 代码高亮 |

## 常见问题解决

### 浮动体位置
```latex
\usepackage{float}
% 使用 [H] 强制位置
\begin{figure}[H]
```

### 中文支持
```latex
\usepackage{ctex}  % 推荐使用
% 或
\usepackage{xeCJK}
```

## 适用场景

- 论文排版
- 公式编写
- 表格制作
- 学位论文模板
