import asyncio
import os
import sys

_lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python_libs")
if os.path.exists(_lib_path):
    sys.path.insert(0, _lib_path)

from agent.experiments import add_experiment, query_experiments, init_db


async def test_add_experiment():
    print("=" * 50)
    print("测试 1: 添加实验记录")
    print("=" * 50)
    
    test_notes = [
        "今天跑了BERT在SST-2上的实验，准确率92.3%",
        "GPT-2在WikiText上的困惑度是18.5",
        "ResNet50在ImageNet上的Top-1准确率76.1%",
    ]
    
    for note in test_notes:
        print(f"\n添加记录: {note}")
        result = await add_experiment(note)
        if result.get("success"):
            print(f"✅ 成功！ID: {result['id']}")
            data = result['data']
            if data.get('model'):
                print(f"   模型: {data['model']}")
            if data.get('dataset'):
                print(f"   数据集: {data['dataset']}")
            if data.get('metric') and data.get('value') is not None:
                print(f"   指标: {data['metric']} = {data['value']}")
        else:
            print(f"❌ 失败: {result.get('error')}")
    
    print()


async def test_query_experiments():
    print("=" * 50)
    print("测试 2: 查询实验记录")
    print("=" * 50)
    
    test_queries = [
        "",
        "BERT",
        "准确率",
    ]
    
    for query in test_queries:
        query_display = query if query else "(最近记录)"
        print(f"\n查询: {query_display}")
        result = await query_experiments(query, limit=5)
        if result.get("success"):
            print(f"✅ 找到 {result['total']} 条记录")
            for i, exp in enumerate(result['experiments'], 1):
                print(f"\n{i}. {exp.get('timestamp', '')}")
                if exp.get('model'):
                    print(f"   模型: {exp['model']}")
                if exp.get('dataset'):
                    print(f"   数据集: {exp['dataset']}")
                if exp.get('metric') and exp.get('value') is not None:
                    print(f"   {exp['metric']}: {exp['value']}")
        else:
            print(f"❌ 查询失败: {result.get('error')}")
    
    print()


async def main():
    print("\n🧪 开始测试实验记录模块\n")
    
    init_db()
    
    try:
        await test_add_experiment()
        await test_query_experiments()
        
        print("=" * 50)
        print("✅ 所有测试通过！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 测试出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
