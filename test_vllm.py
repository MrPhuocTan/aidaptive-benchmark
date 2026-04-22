import asyncio
import httpx

async def test_vllm():
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                "http://35.186.159.250:11434/v1/chat/completions",
                json={
                    "model": "llama3.2-deterministic:latest",
                    "messages": [{"role": "user", "content": "Tell me a joke."}],
                    "stream": False,
                },
            )
            print(f"Status: {resp.status_code}")
            print(resp.text)
        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(test_vllm())
