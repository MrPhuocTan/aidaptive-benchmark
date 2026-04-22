"""Server discovery helpers for dynamic benchmark targets."""

import asyncio
import getpass
import os
from typing import Optional

import httpx


class ServerDiscovery:
    """Probe a remote AI server through the predefined agent and Ollama ports."""

    def __init__(
        self,
        timeout: float = 5.0,
        agent_port: int = 9100,
        ollama_port: int = 11434,
        ssh_port: int = 22,
        use_ssh_fallback: bool = False,
    ):
        self.timeout = timeout
        self.agent_port = agent_port
        self.ollama_port = ollama_port
        self.ssh_port = ssh_port
        self.use_ssh_fallback = use_ssh_fallback

    async def discover(self, ip: str, ssh_user: Optional[str] = None) -> dict:
        ip = (ip or "").strip()
        if not ip:
            raise ValueError("IP address is required")

        agent_url = f"http://{ip}:{self.agent_port}"
        ollama_url = f"http://{ip}:{self.ollama_port}"

        result = {
            "server_id": f"custom_{ip.replace('.', '_')}",
            "ip": ip,
            "name": f"Discovered AI Server ({ip})",
            "description": "Dynamically discovered from Benchmark UI",
            "agent_url": agent_url,
            "ollama_url": ollama_url,
            "hardware_cost_usd": 0,
            "monthly_power_usd": 0,
            "ollama_online": False,
            "agent_online": False,
            "models_available": [],
            "ollama_version": "unknown",
            "gpu_name": "",
            "vram_total_gb": 0,
            "cpu_model": "",
            "cpu_cores": 0,
            "ram_total_gb": 0,
            "ssh_user": "",
            "discovery_sources": [],
            "errors": [],
        }

        await self._probe_agent(result)
        await self._probe_ollama(result)

        if self.use_ssh_fallback and self._needs_ssh_enrichment(result):
            ssh_data = await self._probe_ssh(ip, ssh_user=ssh_user)
            if ssh_data:
                result["discovery_sources"].append("ssh")
                for key, value in ssh_data.items():
                    if value not in (None, "", 0, 0.0, []):
                        result[key] = value

        return result

    async def _probe_agent(self, result: dict):
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                health = await client.get(f"{result['agent_url']}/health")
                result["agent_online"] = health.status_code == 200
            except Exception:
                result["agent_online"] = False

            if not result["agent_online"]:
                result["errors"].append("Agent is unreachable")
                return

            result["discovery_sources"].append("agent")

            # Try explicit profile-like endpoints first, then fall back to metrics.
            for path in ("/profile", "/server-profile", "/info", "/config"):
                try:
                    resp = await client.get(f"{result['agent_url']}{path}")
                    if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application/json"):
                        data = resp.json()
                        self._merge_agent_data(result, data)
                        break
                except Exception:
                    continue

            try:
                gpu_resp = await client.get(f"{result['agent_url']}/metrics/gpu")
                if gpu_resp.status_code == 200:
                    gpu = gpu_resp.json()
                    result["gpu_name"] = result["gpu_name"] or gpu.get("gpu_name", "")
                    result["vram_total_gb"] = result["vram_total_gb"] or gpu.get("vram_total_gb", 0)
            except Exception:
                pass

            try:
                sys_resp = await client.get(f"{result['agent_url']}/metrics/system")
                if sys_resp.status_code == 200:
                    system = sys_resp.json()
                    result["cpu_cores"] = result["cpu_cores"] or system.get("cpu_cores", 0)
                    result["ram_total_gb"] = result["ram_total_gb"] or system.get("ram_total_gb", 0)
                    result["cpu_model"] = result["cpu_model"] or system.get("cpu_model", "")
            except Exception:
                pass

    async def _probe_ollama(self, result: dict):
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                tags = await client.get(f"{result['ollama_url']}/api/tags")
                result["ollama_online"] = tags.status_code == 200
                if tags.status_code == 200:
                    data = tags.json()
                    result["models_available"] = [m["name"] for m in data.get("models", [])]
                    if "ollama" not in result["discovery_sources"]:
                        result["discovery_sources"].append("ollama")
            except Exception:
                result["ollama_online"] = False

            if not result["ollama_online"]:
                result["errors"].append("Ollama is unreachable")
                return

            try:
                version = await client.get(f"{result['ollama_url']}/api/version")
                if version.status_code == 200:
                    result["ollama_version"] = version.json().get("version", "unknown")
            except Exception:
                pass

    def _merge_agent_data(self, result: dict, data: dict):
        result["name"] = data.get("name") or result["name"]
        result["description"] = data.get("description") or result["description"]
        result["gpu_name"] = data.get("gpu_name") or result["gpu_name"]
        result["vram_total_gb"] = data.get("vram_total_gb") or result["vram_total_gb"]
        result["cpu_model"] = data.get("cpu_model") or result["cpu_model"]
        result["cpu_cores"] = data.get("cpu_cores") or result["cpu_cores"]
        result["ram_total_gb"] = data.get("ram_total_gb") or result["ram_total_gb"]
        result["ollama_version"] = data.get("ollama_version") or result["ollama_version"]
        models = data.get("models_available") or data.get("models_loaded") or []
        if models:
            result["models_available"] = models

    def _needs_ssh_enrichment(self, result: dict) -> bool:
        return not all([
            result["gpu_name"],
            result["cpu_model"],
            result["cpu_cores"],
            result["ram_total_gb"],
        ])

    async def _probe_ssh(self, ip: str, ssh_user: Optional[str] = None) -> Optional[dict]:
        ssh_candidates = self._candidate_ssh_users(ssh_user)
        for user in ssh_candidates:
            ssh_data = await self._run_ssh_probe(ip, user)
            if ssh_data:
                ssh_data["ssh_user"] = user
                return ssh_data
        return None

    def _candidate_ssh_users(self, ssh_user: Optional[str]) -> list[str]:
        if ssh_user:
            return [ssh_user]

        env_users = os.getenv("AIDAPTIVE_DISCOVERY_SSH_USERS", "")
        candidates = [item.strip() for item in env_users.split(",") if item.strip()]
        candidates.extend(
            [
                os.getenv("AIDAPTIVE_DISCOVERY_SSH_USER", "").strip(),
                getpass.getuser(),
                "ubuntu",
                "root",
                "ec2-user",
                "admin",
            ]
        )

        seen = []
        for candidate in candidates:
            if candidate and candidate not in seen:
                seen.append(candidate)
        return seen

    async def _run_ssh_probe(self, ip: str, user: str) -> Optional[dict]:
        probe_script = (
            "hostname=$(hostname 2>/dev/null); "
            "cpu_model=$( (lscpu 2>/dev/null | awk -F: '/Model name/ {print $2}' | sed 's/^ *//') || true ); "
            "cpu_cores=$(nproc 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || echo 0); "
            "ram_kb=$(awk '/MemTotal/ {print $2}' /proc/meminfo 2>/dev/null || echo 0); "
            "gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n 1); "
            "vram_mb=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -n 1); "
            "printf 'hostname=%s\ncpu_model=%s\ncpu_cores=%s\nram_kb=%s\ngpu_name=%s\nvram_mb=%s\n' "
            "\"$hostname\" \"$cpu_model\" \"$cpu_cores\" \"$ram_kb\" \"$gpu_name\" \"$vram_mb\""
        )

        cmd = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            f"ConnectTimeout={int(self.timeout)}",
            "-p",
            str(self.ssh_port),
            f"{user}@{ip}",
            "sh",
            "-lc",
            probe_script,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=self.timeout + 2)
            if proc.returncode != 0 or not stdout:
                return None
            return self._parse_ssh_output(stdout.decode())
        except Exception:
            return None

    def _parse_ssh_output(self, raw_output: str) -> dict:
        parsed = {}
        for line in raw_output.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            parsed[key.strip()] = value.strip()

        ram_kb = self._safe_float(parsed.get("ram_kb"))
        vram_mb = self._safe_float(parsed.get("vram_mb"))

        return {
            "name": parsed.get("hostname", "") or "",
            "cpu_model": parsed.get("cpu_model", "") or "",
            "cpu_cores": int(self._safe_float(parsed.get("cpu_cores")) or 0),
            "ram_total_gb": round(ram_kb / (1024 * 1024), 2) if ram_kb else 0,
            "gpu_name": parsed.get("gpu_name", "") or "",
            "vram_total_gb": round(vram_mb / 1024, 2) if vram_mb else 0,
        }

    @staticmethod
    def _safe_float(value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
