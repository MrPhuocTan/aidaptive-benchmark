"""k6 adapter - Grafana load testing tool"""

import asyncio
import json
import tempfile
from src.time_utils import get_local_time
from datetime import datetime
from pathlib import Path
from typing import List

from src.adapters.base import BaseToolAdapter
from src.models import BenchmarkResult


class K6Adapter(BaseToolAdapter):
    tool_name = "k6"

    def __init__(
        self,
        ollama_url: str,
        model: str,
        concurrency: int = 10,
        duration: int = 60,
        binary_path: str = "k6",
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.concurrency = concurrency
        self.duration = duration
        self.binary_path = binary_path

    def is_available(self) -> bool:
        return self.check_binary(self.binary_path)

    async def run(self, prompts: list) -> List[BenchmarkResult]:
        prompt_text = prompts[0].get("prompt", "Hello") if prompts else "Hello"

        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "k6_test.js"
            results_path = Path(tmpdir) / "results.json"

            script_content = self._generate_k6_script(prompt_text)
            script_path.write_text(script_content)

            cmd = [
                self.binary_path, "run",
                "--vus", str(self.concurrency),
                "--duration", f"{self.duration}s",
                "--summary-export", str(results_path),
                str(script_path),
            ]

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self.duration + 120
                )

                if results_path.exists():
                    with open(results_path, "r") as f:
                        data = json.load(f)
                    return [self._parse_results(data)]

            except asyncio.TimeoutError as e:
                import logging
                logging.getLogger(__name__).error(f"k6 timeout: {e}")
                if 'proc' in locals():
                    proc.kill()
                    await proc.communicate()
                raise RuntimeError("k6 tool timed out")
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"k6 execution failed: {e}")
                raise RuntimeError(f"k6 execution failed: {e}")

        raise RuntimeError("k6 tool failed: No results generated")

    def _generate_k6_script(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        payload_str = json.dumps(payload)
        js_payload = json.dumps(payload_str)  # Double encode to safely embed as a JS string literal

        return f"""
import http from 'k6/http';
import {{ check, sleep }} from 'k6';

export const options = {{
    vus: {self.concurrency},
    duration: '{self.duration}s',
}};

export default function () {{
    const url = '{self.ollama_url}/api/generate';
    const payloadStr = {js_payload};

    const params = {{
        headers: {{ 'Content-Type': 'application/json' }},
        timeout: '120s',
    }};

    const res = http.post(url, payloadStr, params);

    check(res, {{
        'status is 200': (r) => r.status === 200,
    }});

    sleep(0.1);
}}
"""

    def _parse_results(self, data: dict) -> BenchmarkResult:
        result = BenchmarkResult(
            timestamp=get_local_time(),
            tool=self.tool_name,
            model=self.model,
            concurrency=self.concurrency,
        )

        metrics = data.get("metrics", {})

        # Request count and rate
        http_reqs = metrics.get("http_reqs", {})
        result.rps = http_reqs.get("rate", 0)
        result.total_requests = int(http_reqs.get("count", 0))

        # Latency percentiles
        duration = metrics.get("http_req_duration", {})
        values = duration.get("values", {})
        result.latency_p50_ms = values.get("p(50)", 0)
        result.latency_p95_ms = values.get("p(95)", 0)
        result.latency_p99_ms = values.get("p(99)", 0)

        # Error rate
        failures = metrics.get("http_req_failed", {})
        fail_rate = failures.get("values", {}).get("rate", 0)
        result.error_rate = fail_rate
        result.failed_requests = int(result.total_requests * fail_rate)
        result.successful_requests = result.total_requests - result.failed_requests

        return result