"""llmperf adapter - Anyscale LLM benchmark tool"""

import asyncio
import json
import os
import sys
import tempfile
from src.time_utils import get_local_time
from datetime import datetime
from pathlib import Path
from typing import List

from src.adapters.base import BaseToolAdapter
from src.models import BenchmarkResult


class LLMPerfAdapter(BaseToolAdapter):
    tool_name = "llmperf"

    def __init__(self, ollama_url: str, model: str, concurrency: int = 1):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.concurrency = concurrency

    def is_available(self) -> bool:
        try:
            import importlib
            importlib.import_module("llmperf")
            return True
        except ImportError:
            return False

    async def run(self, prompts: list) -> List[BenchmarkResult]:
        """Run llmperf benchmark against OpenAI-compatible endpoint"""

        if not self.is_available():
            result = BenchmarkResult(
                timestamp=get_local_time(),
                tool=self.tool_name,
                model=self.model,
                error_rate=1.0,
            )
            return [result]

        num_requests = len(prompts)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "results"

            env = {
                "OPENAI_API_KEY": "not-needed",
                "OPENAI_API_BASE": f"{self.ollama_url}/v1",
            }

            cmd = [
                sys.executable, "-m", "llmperf.token_benchmark_ray",
                "--model", self.model,
                "--mean-input-tokens", "100",
                "--stddev-input-tokens", "20",
                "--mean-output-tokens", "200",
                "--stddev-output-tokens", "40",
                "--num-concurrent-requests", str(self.concurrency),
                "--max-num-completed-requests", str(num_requests),
                "--timeout", "120",
                "--results-dir", str(output_dir),
            ]

            try:
                full_env = os.environ.copy()
                full_env.update(env)

                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    env=full_env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=300
                )

                # Parse results
                summary_files = list(output_dir.glob("*summary.json"))
                if summary_files:
                    with open(summary_files[0], "r") as f:
                        summary = json.load(f)

                    result = BenchmarkResult(
                        timestamp=get_local_time(),
                        tool=self.tool_name,
                        model=self.model,
                    )

                    result.ttft_ms = summary.get("results_ttft_s_mean", 0) * 1000
                    result.tpot_ms = summary.get("results_inter_token_latency_s_mean", 0) * 1000
                    result.itl_ms = result.tpot_ms
                    result.tps = summary.get("results_mean_output_throughput_token_per_s", 0)

                    result.latency_p50_ms = summary.get("results_ttft_s_p50", 0) * 1000
                    result.latency_p95_ms = summary.get("results_ttft_s_p95", 0) * 1000
                    result.latency_p99_ms = summary.get("results_ttft_s_p99", 0) * 1000

                    result.total_requests = summary.get("results_num_completed_requests", 0)
                    result.successful_requests = result.total_requests
                    result.error_rate = summary.get("results_error_rate", 0)

                    return [result]

            except asyncio.TimeoutError as e:
                import logging
                logging.getLogger(__name__).error(f"llmperf timeout: {e}")
                if 'proc' in locals():
                    proc.kill()
                    await proc.communicate()
                raise RuntimeError("llmperf tool timed out")
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"llmperf execution failed: {e}")
                raise RuntimeError(f"llmperf execution failed: {e}")

        raise RuntimeError("llmperf tool failed: No results generated")
