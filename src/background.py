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
                    if system_metrics:
                        agent_data = {
                            "name": status.server_name or server_cfg.name,
                            "description": server_cfg.description,
                            "gpu_name": status.gpu_name,
                            "vram_total_gb": status.vram_total_gb,
                            "cpu_model": system_metrics.get("cpu_model"),
                            "cpu_cores": system_metrics.get("cpu_cores"),
                            "ram_total_gb": system_metrics.get("ram_total_gb"),
                            "hardware_cost_usd": server_cfg.hardware_cost_usd,
                            "monthly_power_usd": server_cfg.monthly_power_usd,
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
