"""Database seed - initial data and migration helpers"""

from src.time_utils import get_local_time
from datetime import datetime

from src.database.engine import Database
from src.database.tables import Base, ServerProfile


def run_seed(database: Database):
    """Run database seed on startup"""

    # Ensure all tables exist
    database.create_tables()

    session = database.get_sync_session()
    try:
        _seed_server_profiles(session)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"  Seed warning: {e}")
    finally:
        session.close()


def _seed_server_profiles(session):
    """Seed initial server profiles if not exist"""

    existing = session.query(ServerProfile).first()
    if existing:
        return

    profiles = [
        ServerProfile(
            server_id="server1",
            recorded_at=get_local_time(),
            name="Native High-End",
            description="High-end GPU Server - Native Hardware Only",
            gpu_name="",
            gpu_count=0,
            vram_total_gb=0,
            cpu_model="",
            cpu_cores=0,
            ram_total_gb=0,
            hardware_cost_usd=50000,
            monthly_power_usd=500,
            ollama_version="",
            models_available=[],
            aidaptive_version=None,
            aidaptive_firmware=None,
        ),
        ServerProfile(
            server_id="server2",
            recorded_at=get_local_time(),
            name="Standard + aiDaptive",
            description="Mid-range GPU Server with aiDaptive Solution",
            gpu_name="",
            gpu_count=0,
            vram_total_gb=0,
            cpu_model="",
            cpu_cores=0,
            ram_total_gb=0,
            hardware_cost_usd=15000,
            monthly_power_usd=200,
            ollama_version="",
            models_available=[],
            aidaptive_version="1.0.0",
            aidaptive_firmware="1.0.0",
        ),
    ]

    for profile in profiles:
        session.add(profile)


from sqlalchemy.future import select

async def update_server_profile_from_agent(
    database: Database,
    server_id: str,
    agent_data: dict,
):
    """Update server profile with real data from agent"""

    async with database.AsyncSession() as session:
        try:
            result = await session.execute(select(ServerProfile).filter_by(server_id=server_id))
            profile = result.scalars().first()
            if not profile:
                profile = ServerProfile(server_id=server_id)
                session.add(profile)
                
            profile.recorded_at = get_local_time()
            for key in ["name", "description", "gpu_name", "gpu_count", "vram_total_gb", 
                        "cpu_model", "cpu_cores", "ram_total_gb", "hardware_cost_usd", 
                        "monthly_power_usd", "ollama_version", "models_available", 
                        "aidaptive_version", "aidaptive_firmware"]:
                if key in agent_data:
                    setattr(profile, key, agent_data.get(key))
            
            await session.commit()
        except Exception as e:
            await session.rollback()
            print(f"  Profile update error: {e}")


def reset_database(database: Database):
    """Drop all tables and recreate (destructive)"""
    Base.metadata.drop_all(database.sync_engine)
    Base.metadata.create_all(database.sync_engine)
    run_seed(database)