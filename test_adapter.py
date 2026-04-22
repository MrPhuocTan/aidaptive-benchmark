import asyncio
from src.adapters.ollama_adapter import OllamaAdapter

async def main():
    adapter = OllamaAdapter(ollama_url="http://localhost:11434", model="llama3.2:1b")
    # Assume we don't have llama3.2:1b, let's just use whatever is there or it fails
    result = await adapter.run([{"prompt": "Hello"}])
    print(result)

asyncio.run(main())
