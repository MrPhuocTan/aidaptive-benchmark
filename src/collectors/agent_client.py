"""HTTP client for remote agents on AI servers"""

from typing import Optional

import httpx

from src.models import HardwareMetrics, ServerStatus


class AgentClient:
    def __init__(
        self,
        agent_url: str,
        ollama_url: str,
        server_id: str,
        timeout: float = 5.0,
    ):
        self.agent_url = agent_url.rstrip("/")
        self.ollama_url = ollama_url.rstrip("/")
        self.server_id = server_id
        self.timeout = timeout

    def _resolve_ollama_url(self, ollama_url: Optional[str] = None) -> str:
        return (ollama_url or self.ollama_url).rstrip("/")

    async def check_agent_health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.agent_url}/health")
                return resp.status_code == 200
        except Exception:
            return False

    async def check_ollama_health(self, ollama_url: Optional[str] = None) -> bool:
        target_url = self._resolve_ollama_url(ollama_url)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{target_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def get_ollama_models(self, ollama_url: Optional[str] = None) -> list:
        target_url = self._resolve_ollama_url(ollama_url)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{target_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return []

    async def get_ollama_version(self, ollama_url: Optional[str] = None) -> str:
        target_url = self._resolve_ollama_url(ollama_url)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{target_url}/api/version")
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("version", "unknown")
        except Exception:
            pass
        return "unknown"

    async def get_server_specs(self) -> dict:
        """Fetches detailed hardware specs from the agent's /info endpoint."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.agent_url}/info")
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return {}

    async def get_gpu_metrics(self) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.agent_url}/metrics/gpu")
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None

    async def get_system_metrics(self) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.agent_url}/metrics/system")
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None

    async def get_all_metrics(self) -> Optional[HardwareMetrics]:
        gpu = await self.get_gpu_metrics()
        sys_m = await self.get_system_metrics()

        if gpu is None and sys_m is None:
            return None

        metrics = HardwareMetrics(server=self.server_id)

        if gpu:
            metrics.gpu_util_pct = gpu.get("gpu_util_pct")
            metrics.vram_used_gb = gpu.get("vram_used_gb")
            metrics.vram_total_gb = gpu.get("vram_total_gb")
            metrics.gpu_power_watts = gpu.get("power_watts")
            metrics.gpu_temperature_c = gpu.get("temperature_c")
            metrics.gpu_memory_bandwidth_gbps = gpu.get("memory_bandwidth_gbps")
            metrics.gpu_name = gpu.get("gpu_name", "")

        if sys_m:
            metrics.cpu_pct = sys_m.get("cpu_usage_pct")
            
            # Agent returns memory in MB, convert to GB
            mem_used_mb = sys_m.get("memory_used_mb", 0)
            mem_total_mb = sys_m.get("memory_total_mb", 0)
            if mem_used_mb:
                metrics.ram_used_gb = mem_used_mb / 1024
            if mem_total_mb:
                metrics.ram_total_gb = mem_total_mb / 1024
                
            metrics.disk_read_mbps = sys_m.get("disk_read_mbps")
            metrics.disk_write_mbps = sys_m.get("disk_write_mbps")
            metrics.network_rx_mbps = sys_m.get("network_rx_mbps")
            metrics.network_tx_mbps = sys_m.get("network_tx_mbps")

        return metrics

    async def get_server_status(self, server_name: str = "") -> ServerStatus:
        status = ServerStatus(
            server_id=self.server_id,
            server_name=server_name,
        )

        status.agent_online = await self.check_agent_health()
        status.ollama_online = await self.check_ollama_health()

        if status.ollama_online:
            status.models_loaded = await self.get_ollama_models()
            status.ollama_version = await self.get_ollama_version()

        if status.agent_online:
            gpu = await self.get_gpu_metrics()
            if gpu:
                status.gpu_name = gpu.get("gpu_name", "")
                status.vram_total_gb = gpu.get("vram_total_gb", 0)

        return status

    async def warmup_model(
        self,
        model: str,
        num_requests: int = 3,
        ollama_url: Optional[str] = None,
    ) -> bool:
        target_url = self._resolve_ollama_url(ollama_url)
        success = False
        async with httpx.AsyncClient(timeout=120.0) as client:
            for _ in range(num_requests):
                try:
                    resp = await client.post(
                        f"{target_url}/api/generate",
                        json={
                            "model": model,
                            "prompt": "Hello",
                            "stream": False,
                        },
                    )
                    success = success or resp.status_code == 200
                except Exception:
                    pass
        return success

    async def control_ollama(self, action: str, **kwargs) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.agent_url}/control/ollama/{action}",
                    json=kwargs,
                )
                return resp.status_code == 200
        except Exception:
            return False
