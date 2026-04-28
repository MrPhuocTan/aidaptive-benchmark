"""LiteLLM adapter - benchmark via litellm library"""

import logging
import time
from src.time_utils import get_local_time
from datetime import datetime
from typing import List, Tuple, Optional

from src.adapters.base import BaseToolAdapter
from src.models import BenchmarkResult, PromptLogEntry, ToolEvidence

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

    async def run(self, prompts: list) -> Tuple[List[BenchmarkResult], List[PromptLogEntry], Optional[ToolEvidence]]:
        if not self.is_available():
            result = BenchmarkResult(
                timestamp=get_local_time(),
                tool=self.tool_name,
                model=self.model,
                error_rate=1.0,
            )
            return [result], [], None

        import litellm
        litellm.api_key = "not-needed"

        results = []
        prompt_logs = []
        raw_outputs = []

        for i, item in enumerate(prompts):
            prompt_text = item.get("prompt", "")
            result, p_log, raw_resp = await self._single_request(prompt_text, i)
            if result:
                results.append(result)
            if p_log:
                prompt_logs.append(p_log)
            if raw_resp:
                raw_outputs.append(raw_resp)

        import json
        evidence = ToolEvidence(
            tool_name=self.tool_name,
            tool_version=litellm.__version__ if hasattr(litellm, "__version__") else "unknown",
            command_line="litellm.acompletion",
            raw_output=json.dumps(raw_outputs, indent=2),
            output_format="json",
        ) if raw_outputs else None

        return results, prompt_logs, evidence

    async def _single_request(self, prompt: str, index: int) -> Tuple[BenchmarkResult, PromptLogEntry, dict]:
        import litellm

        result = BenchmarkResult(
            timestamp=get_local_time(),
            tool=self.tool_name,
            model=self.model,
        )
        p_log = PromptLogEntry(
            prompt_index=index,
            prompt_text=prompt,
        )
        raw_data = {"prompt": prompt, "chunks": []}

        try:
            start = time.perf_counter()
            p_log.sent_at = get_local_time()

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
                raw_data["chunks"].append(chunk.model_dump() if hasattr(chunk, "model_dump") else str(chunk))
                if ttft_ms is None:
                    ttft_ms = (time.perf_counter() - start) * 1000
                    p_log.first_token_at = get_local_time()
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    p_log.response_text += content
                    completion_tokens += 1

            end = time.perf_counter()
            p_log.completed_at = get_local_time()
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

            p_log.ttft_ms = result.ttft_ms
            p_log.tps = result.tps
            p_log.tpot_ms = result.tpot_ms
            p_log.tokens_generated = completion_tokens

        except Exception as exc:
            p_log.status = "error"
            p_log.error_message = str(exc)
            logger.warning("litellm request failed for model %s: %s", self.model, exc)

        return result, p_log, raw_data
