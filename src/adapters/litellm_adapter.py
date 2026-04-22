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
                stream=False,
                timeout=600,
            )

            end = time.perf_counter()
            total_time = end - start

            usage = getattr(response, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

            result.ttft_ms = total_time * 1000
            if completion_tokens > 0:
                result.tpot_ms = (total_time * 1000) / completion_tokens
                result.tps = completion_tokens / total_time

            result.prompt_tokens = prompt_tokens
            result.completion_tokens = completion_tokens
            result.total_tokens = prompt_tokens + completion_tokens
            result.total_requests = 1
            result.successful_requests = 1
            result.error_rate = 0.0

        except Exception as exc:
            logger.warning("litellm request failed for model %s: %s", self.model, exc)
            raise RuntimeError(f"litellm request failed: {exc}")

        return result
