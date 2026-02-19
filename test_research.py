import sys
import asyncio
sys.path.insert(0, '.')
from agent.research_agent import ResearchAgent

async def test():
    agent = ResearchAgent()
    
    results = []
    async def callback(data):
        results.append(data)
        print(f"Progress: {data.get('state')} - {data.get('task', data.get('content', ''))}")
    
    result = await agent.conduct_research(
        topic="AI for Climate Modeling",
        years=2,
        max_papers=10,
        callback=callback
    )
    
    print(f"\n=== Final Result ===")
    print(f"Success: {result.get('success')}")
    print(f"Papers: {len(result.get('papers', []))}")
    print(f"Clusters: {len(result.get('clusters', []))}")
    print(f"Cross Points: {len(result.get('cross_points', []))}")
    print(f"Report: {'Yes' if result.get('report') else 'No'}")

asyncio.run(test())
