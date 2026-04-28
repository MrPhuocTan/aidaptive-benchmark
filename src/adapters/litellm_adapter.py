"""LiteLLM adapter - benchmark via litellm library"""

import logging
import time
from src.time_utils import get_local_time
from datetime import datetime
from typing import List

from src.adapters.base import BaseToolAdapter
from src.models import BenchmarkResult

logger = logging.getLogger(__name__)


class LiteLLMAdapter(BaseToolAdapter):
    tool_name = "litellm"

    def __init__(self, ollama_url: str, model: str):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model

    def is_available(self) -> bool:
        try:
            import litellm
            return True
        except ImportError:
            return False

    async def run(self, prompts: list) -> List[BenchmarkResult]:
        if not self.is_available():
            result = BenchmarkResult(
                timestamp=get_local_time(),
                tool=self.tool_name,
                model=self.model,
                error_rate=1.0,
            )
            return [result]

        import litellm
        litellm.api_key = "not-needed"

        results = []

        for item in prompts:
            prompt_text = item.get("prompt", "")
            result = await self._single_request(prompt_text)
            if result:
                results.append(result)

        return results

    async def _single_request(self, prompt: str) -> BenchmarkResult:
        import litellm

        result = BenchmarkResult(
            timestamp=get_local_time(),
            tool=self.tool_name,
            model=self.model,
        )

        try:
            start = time.perf_counter()

            response = await litellm.acompletion(
                model=f"ollama/{self.model}",
                messages=[{"role": "user", "content": prompt}],
                api_base=self.ollama_url,
                stream=True,
                timeout=600,
            )

            ttft_ms = None
            completion_tokens = 0
            
            async for chunk in response:
                if ttft_ms is None:
                    ttft_ms = (time.perf_counter() - start) * 1000
                if chunk.choices and chunk.choices[0].delta.content:
                    completion_tokens += 1

            end = time.perf_counter()
            total_time = end - start

            result.ttft_ms = ttft_ms if ttft_ms is not None else (total_time * 1000)
            if completion_tokens > 0:
                result.tpot_ms = ((total_time * 1000) - result.ttft_ms) / completion_tokens if completion_tokens > 1 else result.ttft_ms
                result.tps = completion_tokens / total_time

            result.prompt_tokens = 0 # Cannot easily get prompt tokens in streaming mode without token counting lib
            result.completion_tokens = completion_tokens
            result.total_tokens = completion_tokens
            result.total_requests = 1
            result.successful_requests = 1
            result.error_rate = 0.0

        except Exception as exc:
            logger.warning("litellm request failed for model %s: %s", self.model, exc)
            raise RuntimeError(f"litellm request failed: {exc}")

        return result
