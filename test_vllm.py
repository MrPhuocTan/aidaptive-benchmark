import asyncio
from src.adapters.vllm_bench_adapter import VLLMBenchAdapter

async def main():
    adapter = VLLMBenchAdapter("http://35.186.159.250:11434", "llama3.2-deterministic:latest", concurrency=10)
    prompts = [{"prompt": f"Hello {i}"} for i in range(10)]
    
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    results = await adapter.run(prompts)
    print(results)

asyncio.run(main())
