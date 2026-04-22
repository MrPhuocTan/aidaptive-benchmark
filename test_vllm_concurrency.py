import asyncio
import httpx

async def run_concurrent():
    url = "http://35.186.159.250:11434/v1/chat/completions"
    model = "llama3:8b" # A faster model to test concurrency
    
    async with httpx.AsyncClient(timeout=600.0) as client:
        async def send(i):
            print(f"Sending request {i}...")
            try:
                resp = await client.post(
                    url,
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": f"Reply with a single word: hello {i}"}],
                        "stream": False,
                    }
                )
                print(f"Request {i} done: {resp.status_code}")
                if resp.status_code != 200:
                    print(f"Error {i}: {resp.text}")
            except Exception as e:
                print(f"Request {i} failed: {e}")

        tasks = [send(i) for i in range(10)]
        await asyncio.gather(*tasks)

asyncio.run(run_concurrent())
