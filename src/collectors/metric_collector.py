"""Background metric collector - polls agents periodically"""

import asyncio
import threading
from src.time_utils import get_local_time
from datetime import datetime

from src.collectors.agent_client import AgentClient
from src.data.data_sink import DataSink


class MetricCollector:
    """Runs in background thread, polls hardware metrics from agents"""

    def __init__(
        self,
        agent_clients: dict,
        data_sink: DataSink,
        run_id: str,
        gpu_interval: int = 1,
    ):
        self.agent_clients = agent_clients
        self.data_sink = data_sink
        self.run_id = run_id
        self.gpu_interval = gpu_interval
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True
        )
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)

    def _run_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_loop())
        finally:
            loop.close()

    async def _async_loop(self):
        while self._running:
            for server_id, client in self.agent_clients.items():
                try:
                    metrics = await client.get_all_metrics()
                    if metrics:
                        metrics.server = server_id
                        metrics.timestamp = get_local_time()
                        self.data_sink.write_hardware_metrics(
                            metrics, self.run_id
                        )
                except Exception:
                    pass

            await asyncio.sleep(self.gpu_interval)
