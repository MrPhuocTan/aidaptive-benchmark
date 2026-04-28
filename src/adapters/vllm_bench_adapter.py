"""vLLM benchmark adapter - works with OpenAI-compatible API"""

import asyncio
import time
from src.time_utils import get_local_time
from datetime import datetime
from typing import List, Tuple, Optional

import httpx

from src.adapters.base import BaseToolAdapter
from src.models import BenchmarkResult, PromptLogEntry, ToolEvidence


class VLLMBenchAdapter(BaseToolAdapter):
    tool_name = "vllm_bench"

    def __init__(
        self,
        ollama_url: str,
        model: str,
        concurrency: int = 1,
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.concurrency = concurrency

    def is_available(self) -> bool:
        return True

    async def run(self, prompts: list) -> Tuple[List[BenchmarkResult], List[PromptLogEntry], Optional[ToolEvidence]]:
        """
        Simulate vLLM-style benchmark against OpenAI-compatible API.
        Sends concurrent requests and measures throughput.
        """

        prompt_texts = [p.get("prompt", "Hello") for p in prompts]
        if not prompt_texts:
            return [], [], None

        all_latencies = []
        all_ttft = []
        all_tps = []
        total_output_tokens = 0
        total_successes = 0
        total_failures = 0

        start_time = time.perf_counter()
        
        prompt_logs = []
        raw_outputs = []

        semaphore = asyncio.Semaphore(self.concurrency)
        
        limits = httpx.Limits(max_keepalive_connections=self.concurrency + 10, max_connections=self.concurrency + 10)
        async with httpx.AsyncClient(timeout=1200.0, limits=limits) as client:
            async def send_one(prompt_text: str, index: int):
                nonlocal total_output_tokens, total_successes, total_failures

                p_log = PromptLogEntry(
                    prompt_index=index,
                    prompt_text=prompt_text,
                    sent_at=get_local_time(),
                )
                raw_response = {"prompt": prompt_text, "chunks": []}
                
                async with semaphore:
                    req_start = time.perf_counter()
                    try:
                        import json
                        ttft = None
                        output_tokens = 0
                        
                        async with client.stream(
                            "POST",
                            f"{self.ollama_url}/v1/chat/completions",
                            json={
                                "model": self.model,
                                "messages": [
                                    {"role": "user", "content": prompt_text}
                                ],
                                "stream": True,
                            },
                        ) as resp:
                            if resp.status_code != 200:
                                total_failures += 1
                                import logging
                                logging.getLogger(__name__).warning(
                                    "vLLM API returned HTTP %s", resp.status_code
                                )
                                return
                                
                            async for line in resp.aiter_lines():
                                if not line or not line.startswith("data: "):
                                    continue
                                
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    break
                                    
                                try:
                                    chunk = json.loads(data_str)
                                    raw_response["chunks"].append(chunk)
                                    choices = chunk.get("choices", [])
                                    if choices and choices[0].get("delta", {}).get("content"):
                                        content = choices[0]["delta"]["content"]
                                        p_log.response_text += content
                                        output_tokens += 1
                                        if ttft is None:
                                            ttft = (time.perf_counter() - req_start) * 1000
                                            p_log.first_token_at = get_local_time()
                                except json.JSONDecodeError:
                                    pass

                        req_end = time.perf_counter()
                        p_log.completed_at = get_local_time()
                        latency = (req_end - req_start) * 1000


                        all_latencies.append(latency)
                        if ttft is not None:
                            all_ttft.append(ttft)
                            
                        total_output_tokens += output_tokens
                        total_successes += 1

                        if output_tokens > 0 and latency > 0:
                            tps = output_tokens / (latency / 1000)
                            all_tps.append(tps)
                            p_log.tps = tps
                            
                        p_log.ttft_ms = ttft
                        if output_tokens > 0:
                            p_log.tpot_ms = (latency - (ttft or 0)) / output_tokens
                        p_log.tokens_generated = output_tokens

                    except Exception as e:
                        total_failures += 1
                        p_log.status = "error"
                        p_log.error_message = str(e)
                        import logging
                        logging.getLogger(__name__).warning("vLLM request failed: %s", e)
                        
                    prompt_logs.append(p_log)
                    raw_outputs.append(raw_response)

            tasks = [send_one(p, i) for i, p in enumerate(prompt_texts)]
            await asyncio.gather(*tasks, return_exceptions=True)


        end_time = time.perf_counter()
        total_time = end_time - start_time

        result = BenchmarkResult(
            timestamp=get_local_time(),
            tool=self.tool_name,
            model=self.model,
            concurrency=self.concurrency,
        )

        if all_ttft:
            result.ttft_ms = sum(all_ttft) / len(all_ttft)

        if all_tps:
            result.tps = sum(all_tps) / len(all_tps)

        if all_latencies:
            all_latencies_sorted = sorted(all_latencies)
            n = len(all_latencies_sorted)
            result.latency_p50_ms = all_latencies_sorted[int(n * 0.50)]
            result.latency_p95_ms = all_latencies_sorted[min(int(n * 0.95), n - 1)]
            result.latency_p99_ms = all_latencies_sorted[min(int(n * 0.99), n - 1)]

        result.total_requests = total_successes + total_failures
        result.successful_requests = total_successes
        result.failed_requests = total_failures
        result.total_tokens = total_output_tokens
        result.rps = result.total_requests / max(total_time, 0.001)

        if result.total_requests > 0:
            result.error_rate = total_failures / result.total_requests

        evidence = ToolEvidence(
            tool_name=self.tool_name,
            tool_version="native",
            command_line="vLLM stream simulation API",
            raw_output=__import__("json").dumps(raw_outputs, indent=2),
            output_format="json",
        )

        return [result], prompt_logs, evidence
