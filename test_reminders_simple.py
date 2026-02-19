import sys
import os

_lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python_libs")
if os.path.exists(_lib_path):
    sys.path.insert(0, _lib_path)

from agent.reminders import simple_parse_reminder


def test_simple_parse():
    print("=" * 50)
    print("测试：简单规则解析提醒")
    print("=" * 50)
    
    test_cases = [
        "明天下午3点组会",
        "今天上午10点开会",
        "后天早上9点提交报告",
        "2月16日下午2点答辩",
    ]
    
    for note in test_cases:
        print(f"\n输入: {note}")
        result = simple_parse_reminder(note)
        print(f"解析结果:")
        print(f"  标题: {result.get('title')}")
        print(f"  时间: {result.get('datetime')}")
        print(f"  重复: {result.get('recurring')}")
    
    print("\n✅ 测试完成！")


if __name__ == "__main__":
    test_simple_parse()
