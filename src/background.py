"""Background tasks for the web application"""

import asyncio
from src.collectors.agent_client import AgentClient
from src.database.seed import update_server_profile_from_agent

async def sync_server_profiles_loop(config, database):
    """Periodically fetches hardware/status info from remote agents and updates DB"""
    while True:
        try:
            for server_id, server_cfg in config.servers.items():
                client = AgentClient(
                    agent_url=server_cfg.agent_url,
                    ollama_url=server_cfg.ollama_url,
                    server_id=server_id,
                )
                status = await client.get_server_status(server_cfg.name)
                if status.agent_online:
                    system_metrics = await client.get_system_metrics()
                    server_info = await client.get_server_specs()  # /info endpoint
                    if system_metrics or server_info:
                        # /info returns: cpu_model, cpu_cores, ram_gb (string), gpu_name, ...
                        # /metrics/system returns: cpu_usage_pct, memory_total_mb, ...
                        ram_total_gb = None
                        if server_info and server_info.get("ram_gb"):
                            try:
                                ram_total_gb = float(server_info["ram_gb"])
                            except (ValueError, TypeError):
                                pass
                        if ram_total_gb is None and system_metrics:
                            mem_total_mb = system_metrics.get("memory_total_mb", 0)
                            if mem_total_mb:
                                ram_total_gb = mem_total_mb / 1024

                        agent_data = {
                            "name": status.server_name or server_cfg.name,
                            "description": server_cfg.description,
                            "gpu_name": status.gpu_name,
                            "vram_total_gb": status.vram_total_gb,
                            "cpu_model": server_info.get("cpu_model") if server_info else None,
                            "cpu_cores": int(server_info.get("cpu_cores", 0)) if server_info and server_info.get("cpu_cores") else None,
                            "ram_total_gb": ram_total_gb,
                            "ollama_version": status.ollama_version,
                            "models_available": status.models_loaded,
                        }
                        await update_server_profile_from_agent(
                            database,
                            server_id,
                            agent_data
                        )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Profile sync error: %s", e)
        
        await asyncio.sleep(60)
