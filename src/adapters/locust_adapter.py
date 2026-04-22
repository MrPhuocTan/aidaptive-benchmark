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

        prompts_payload = [item.get("prompt", "Hello") for item in prompts] or ["Hello"]

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
from locust import HttpUser, task, between
import random

PROMPTS = {prompts_json}
MODEL = {json.dumps(self.model)}

class OllamaUser(HttpUser):
    host = {json.dumps(self.ollama_url)}
    wait_time = between(0.1, 0.5)

    @task
    def generate(self):
        prompt = random.choice(PROMPTS)
        self.client.post(
            "/api/generate",
            json={{
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
            }},
            timeout=120,
        )
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

        return result

    @staticmethod
    def _safe_float(value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
