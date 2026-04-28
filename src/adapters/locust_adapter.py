"""Locust adapter - HTTP load testing via isolated subprocess."""

import asyncio
import csv
import importlib.util
import json
import sys
import tempfile
from src.time_utils import get_local_time
from datetime import datetime
from pathlib import Path
from typing import List

from src.adapters.base import BaseToolAdapter
from src.models import BenchmarkResult


class LocustAdapter(BaseToolAdapter):
    tool_name = "locust"

    def __init__(
        self,
        ollama_url: str,
        model: str,
        concurrency: int = 10,
        duration: int = 60,
        binary_path: str = "",
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.concurrency = concurrency
        self.duration = duration
        self.binary_path = binary_path.strip()

    def is_available(self) -> bool:
        if self.binary_path:
            return self.check_binary(self.binary_path)
        return importlib.util.find_spec("locust") is not None

    async def run(self, prompts: list) -> List[BenchmarkResult]:
        if not self.is_available():
            result = BenchmarkResult(
                timestamp=get_local_time(),
                tool=self.tool_name,
                model=self.model,
                error_rate=1.0,
            )
            return [result]

        prompts_payload = [
            item.get("prompt", "Hello") if isinstance(item, dict) else str(item)
            for item in prompts
        ] or ["Hello"]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            locustfile_path = tmp_path / "locustfile.py"
            csv_prefix = tmp_path / "locust"

            locustfile_path.write_text(
                self._build_locustfile(prompts_payload),
                encoding="utf-8",
            )

            cmd = self._build_command(locustfile_path, csv_prefix)

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=str(tmp_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.duration + 180,
                )

                stats_file = Path(f"{csv_prefix}_stats.csv")
                if proc.returncode == 0 and stats_file.exists():
                    return [self._parse_stats_csv(stats_file)]
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                raise RuntimeError("Locust tool timed out")
            except Exception as e:
                raise RuntimeError(f"Locust tool failed: {e}")

        raise RuntimeError("Locust tool failed: No results generated")

    def _build_command(self, locustfile_path: Path, csv_prefix: Path) -> list[str]:
        if self.binary_path:
            launcher = [self.binary_path]
        else:
            launcher = [sys.executable, "-m", "locust"]

        return [
            *launcher,
            "-f",
            str(locustfile_path),
            "--headless",
            "-u",
            str(self.concurrency),
            "-r",
            str(max(self.concurrency, 1)),
            "-t",
            f"{self.duration}s",
            "--csv",
            str(csv_prefix),
            "--only-summary",
        ]

    def _build_locustfile(self, prompts: list[str]) -> str:
        prompts_json = json.dumps(prompts)
        return f"""
from locust import HttpUser, task, between, events
import random
import time
import json
import statistics

PROMPTS = {prompts_json}
MODEL = {json.dumps(self.model)}

custom_metrics = []

class OllamaUser(HttpUser):
    host = {json.dumps(self.ollama_url)}
    wait_time = between(0.1, 0.5)

    @task
    def generate(self):
        prompt = random.choice(PROMPTS)
        wall_start = time.perf_counter()
        
        with self.client.post(
            "/api/generate",
            json={{
                "model": MODEL,
                "prompt": prompt,
                "stream": True,
            }},
            stream=True,
            timeout=120,
            catch_response=True
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"HTTP {{resp.status_code}}")
                return
                
            ttft = None
            total_tokens = 0
            
            try:
                for line in resp.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        if not chunk.get("done", False):
                            total_tokens += 1
                            if ttft is None:
                                ttft = (time.perf_counter() - wall_start) * 1000
                        else:
                            # Use ollama native token counts if available
                            total_tokens = chunk.get("eval_count", total_tokens)
                
                wall_end = time.perf_counter()
                total_time = wall_end - wall_start
                
                if total_tokens > 0 and ttft is not None:
                    tpot = ((total_time * 1000) - ttft) / total_tokens if total_tokens > 1 else ttft
                    tps = total_tokens / total_time
                    
                    custom_metrics.append({{
                        "ttft": ttft,
                        "tpot": tpot,
                        "tps": tps
                    }})
                resp.success()
            except Exception as e:
                resp.failure(f"Stream parsing error: {{e}}")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    if custom_metrics:
        avg_ttft = statistics.mean([m["ttft"] for m in custom_metrics])
        avg_tpot = statistics.mean([m["tpot"] for m in custom_metrics])
        avg_tps = statistics.mean([m["tps"] for m in custom_metrics])
        
        with open("locust_custom.json", "w") as f:
            json.dump({{
                "ttft_ms": avg_ttft,
                "tpot_ms": avg_tpot,
                "tps": avg_tps
            }}, f)
"""

    def _parse_stats_csv(self, stats_file: Path) -> BenchmarkResult:
        row = None
        with open(stats_file, "r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for item in reader:
                if item.get("Name") == "Aggregated":
                    row = item
                    break

        result = BenchmarkResult(
            timestamp=get_local_time(),
            tool=self.tool_name,
            model=self.model,
            concurrency=self.concurrency,
        )

        if not row:
            result.total_requests = 1
            result.failed_requests = 1
            result.error_rate = 1.0
            return result

        total_requests = int(float(row.get("Request Count") or 0))
        failed_requests = int(float(row.get("Failure Count") or 0))

        result.rps = self._safe_float(row.get("Requests/s"))
        result.latency_p50_ms = self._safe_float(row.get("50%"))
        result.latency_p95_ms = self._safe_float(row.get("95%"))
        result.latency_p99_ms = self._safe_float(row.get("99%"))
        result.total_requests = total_requests
        result.failed_requests = failed_requests
        result.successful_requests = max(total_requests - failed_requests, 0)
        result.error_rate = (
            failed_requests / total_requests if total_requests > 0 else 1.0
        )

        custom_json_path = stats_file.parent / "locust_custom.json"
        if custom_json_path.exists():
            try:
                with open(custom_json_path, "r", encoding="utf-8") as f:
                    custom_stats = json.load(f)
                    result.ttft_ms = custom_stats.get("ttft_ms")
                    result.tpot_ms = custom_stats.get("tpot_ms")
                    result.tps = custom_stats.get("tps")
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("Failed to parse locust_custom.json: %s", e)

        return result

    @staticmethod
    def _safe_float(value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
