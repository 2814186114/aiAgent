import sys
import os

_lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python_libs")
if os.path.exists(_lib_path):
    sys.path.insert(0, _lib_path)

from agent.experiments import simple_parse_experiment


def test_simple_parse():
    print("=" * 50)
    print("测试：简单规则解析测试")
    print("=" * 50)
    
    test_cases = [
        "今天跑了BERT在SST-2上的实验，准确率92.3%",
        "GPT-2在WikiText上的困惑度是18.5",
        "ResNet50在ImageNet上的Top-1准确率76.1%",
    ]
    
    for note in test_cases:
        print(f"\n输入: {note}")
        result = simple_parse_experiment(note)
        print(f"解析结果:")
        print(f"  模型: {result.get('model')}")
        print(f"  数据集: {result.get('dataset')}")
        print(f"  指标: {result.get('metric')}")
        print(f"  值: {result.get('value')}")
    
    print("\n✅ 测试完成！")


if __name__ == "__main__":
    test_simple_parse()
