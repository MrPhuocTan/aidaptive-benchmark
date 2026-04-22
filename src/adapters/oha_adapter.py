"""oha adapter - HTTP load generator written in Rust"""

import asyncio
import json
import logging
from src.time_utils import get_local_time
from datetime import datetime
from typing import List

from src.adapters.base import BaseToolAdapter
from src.models import BenchmarkResult

logger = logging.getLogger(__name__)


class OhaAdapter(BaseToolAdapter):
    tool_name = "oha"

    def __init__(
        self,
        ollama_url: str,
        model: str,
        concurrency: int = 10,
        num_requests: int = 200,
        binary_path: str = "oha",
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.concurrency = concurrency
        self.num_requests = num_requests
        self.binary_path = binary_path

    def is_available(self) -> bool:
        return self.check_binary(self.binary_path)

    async def run(self, prompts: list) -> List[BenchmarkResult]:
        prompt_text = prompts[0].get("prompt", "Hello") if prompts else "Hello"

        payload = json.dumps({
            "model": self.model,
            "prompt": prompt_text,
            "stream": False,
        })

        cmd = [
            self.binary_path,
            "-n", str(self.num_requests),
            "-c", str(self.concurrency),
            "--no-tui",
            "-m", "POST",
            "-H", "Content-Type: application/json",
            "-d", payload,
            "-T", "application/json",
            "--output-format", "json",
            f"{self.ollama_url}/api/generate",
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=600
            )

            if proc.returncode == 0 and stdout:
                data = json.loads(stdout.decode())
                return [self._parse_results(data)]

            stderr_text = stderr.decode(errors="ignore").strip()
            if stderr_text:
                logger.warning("oha command failed: %s", stderr_text)
            else:
                logger.warning("oha command failed with exit code %s", proc.returncode)
                
            raise RuntimeError(f"oha command failed: {stderr_text or proc.returncode}")

        except asyncio.TimeoutError:
            logger.warning("oha timed out after 600 seconds")
            raise RuntimeError("oha timed out after 600 seconds")
        except json.JSONDecodeError as exc:
            logger.warning("oha returned non-JSON output: %s", exc)
            raise RuntimeError(f"oha returned non-JSON output: {exc}")
        except Exception as exc:
            logger.exception("oha adapter failed: %s", exc)
            raise RuntimeError(f"oha adapter failed: {exc}")

    def _parse_results(self, data: dict) -> BenchmarkResult:
        result = BenchmarkResult(
            timestamp=get_local_time(),
            tool=self.tool_name,
            model=self.model,
            concurrency=self.concurrency,
        )

        summary = data.get("summary", {})

        # RPS
        result.rps = (
            summary.get("requestsPerSec")
            or summary.get("requests_per_sec")
            or data.get("rps")
            or 0
        )

        # Total requests: oha summary.total is total TIME, not count.
        # We use the responseTimeHistogram values to count, or fall back to self.num_requests.
        hist = data.get("responseTimeHistogram", {})
        counted = sum(int(v) for v in hist.values()) if hist else 0
        result.total_requests = counted if counted > 0 else self.num_requests

        # Success rate
        success_rate = summary.get("successRate")
        if success_rate is None:
            success_rate = summary.get("success_rate")

        if success_rate is not None:
            result.successful_requests = int(success_rate * result.total_requests)
            result.failed_requests = result.total_requests - result.successful_requests
        else:
            result.successful_requests = result.total_requests
            result.failed_requests = 0

        if result.total_requests > 0:
            result.error_rate = result.failed_requests / result.total_requests
        else:
            result.error_rate = 0.0

        # Parse latency percentiles (values are in seconds, convert to ms)
        percentiles = data.get("latencyPercentiles", {})
        if percentiles:
            result.latency_p50_ms = percentiles.get("p50", 0) * 1000
            result.latency_p95_ms = percentiles.get("p95", 0) * 1000
            result.latency_p99_ms = percentiles.get("p99", 0) * 1000

        return result
