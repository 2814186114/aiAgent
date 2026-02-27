---
name: "code-reviewer"
description: "代码审查、优化建议和最佳实践指导。当用户需要审查代码、优化性能或改进代码质量时调用。"
---

# 代码审查助手 (Code Reviewer)

帮助硕博研究生审查和优化研究代码的技能。

## 主要功能

### 1. 代码质量检查
- 代码风格和规范
- 命名规范
- 代码结构

### 2. 性能优化
- 算法效率分析
- 内存使用优化
- 并行化建议

### 3. 错误检测
- 潜在bug识别
- 边界条件检查
- 异常处理建议

### 4. 最佳实践
- 设计模式建议
- 代码复用
- 文档和注释

## 代码审查清单

### 1. 正确性
- [ ] 逻辑是否正确
- [ ] 边界条件是否处理
- [ ] 异常情况是否考虑
- [ ] 数据类型是否匹配

### 2. 可读性
- [ ] 变量命名是否有意义
- [ ] 函数是否职责单一
- [ ] 是否有必要的注释
- [ ] 代码缩进是否一致

### 3. 效率
- [ ] 是否有不必要的循环
- [ ] 数据结构是否合适
- [ ] 是否可以并行化
- [ ] 内存是否高效使用

### 4. 可维护性
- [ ] 是否有重复代码
- [ ] 是否易于修改
- [ ] 是否有测试用例
- [ ] 依赖是否清晰

## Python 代码优化示例

### 列表操作优化
```python
# 不推荐
result = []
for item in items:
    if condition(item):
        result.append(transform(item))

# 推荐：列表推导式
result = [transform(item) for item in items if condition(item)]
```

### 避免重复计算
```python
# 不推荐
for i in range(len(data)):
    if expensive_function(data[i]) > threshold:
        process(data[i])

# 推荐：缓存结果
results = [expensive_function(d) for d in data]
for i, r in enumerate(results):
    if r > threshold:
        process(data[i])
```

### 使用生成器
```python
# 不推荐：占用大量内存
def read_large_file(file_path):
    with open(file_path) as f:
        return f.readlines()

# 推荐：生成器
def read_large_file(file_path):
    with open(file_path) as f:
        for line in f:
            yield line.strip()
```

### 向量化操作
```python
# 不推荐
result = []
for x in data:
    result.append(x ** 2 + 2 * x + 1)

# 推荐：NumPy向量化
import numpy as np
result = np.array(data) ** 2 + 2 * np.array(data) + 1
```

## 常见问题模式

### 1. 硬编码
```python
# 问题
threshold = 0.85
if accuracy > 0.85:
    print("Good")

# 建议
THRESHOLD = 0.85  # 常量命名
if accuracy > THRESHOLD:
    print("Good")
```

### 2. 魔法数字
```python
# 问题
result = data[::2] * 3.14159

# 建议
PI = 3.14159
STEP = 2
result = data[::STEP] * PI
```

### 3. 过长函数
```python
# 问题：一个函数做太多事
def process_data(data):
    # 100行代码...
    pass

# 建议：拆分职责
def load_data(path):
    pass

def clean_data(data):
    pass

def analyze_data(data):
    pass
```

### 4. 缺少错误处理
```python
# 问题
result = data[key]

# 建议
try:
    result = data[key]
except KeyError:
    result = default_value
    logging.warning(f"Key {key} not found")
```

## 性能分析工具

### 时间分析
```python
import time

start = time.time()
# 你的代码
end = time.time()
print(f"耗时: {end - start:.2f}秒")
```

### 性能分析器
```python
import cProfile

cProfile.run('your_function()')
```

### 内存分析
```python
import tracemalloc

tracemalloc.start()
# 你的代码
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

## 代码风格指南

### Python (PEP 8)
- 缩进：4空格
- 行长：最多79字符
- 命名：snake_case（函数/变量）、PascalCase（类）
- 导入：标准库 → 第三方库 → 本地模块

### 注释规范
```python
def calculate_accuracy(y_true, y_pred):
    """
    计算分类准确率。
    
    Args:
        y_true: 真实标签，形状为(n_samples,)
        y_pred: 预测标签，形状为(n_samples,)
    
    Returns:
        float: 准确率，范围[0, 1]
    
    Example:
        >>> calculate_accuracy([1,0,1], [1,0,0])
        0.6667
    """
    return sum(t == p for t, p in zip(y_true, y_pred)) / len(y_true)
```

## 适用场景

- 实验代码审查
- 性能优化
- 代码重构
- 研究代码规范化
