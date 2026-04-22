import asyncio
from src.config import load_config
from src.database.engine import Database
from src.database.repository import AsyncRepository

async def main():
    config = load_config("benchmark.yaml")
    db = Database(config.postgres)
    async with db.AsyncSession() as session:
        repo = AsyncRepository(session)
        runs = await repo.list_runs(limit=1)
        if not runs:
            print("No runs found")
            return
        run = runs[0]
        print(f"Run ID: {run.run_id}, Status: {run.status}")
        results = await repo.get_results_by_run(run.run_id)
        for r in results:
            if r.error_rate and r.error_rate > 0:
                print(f"Failed Result: Tool={r.tool}, Scenario={r.scenario}, Error Rate={r.error_rate}")
                print(f"Details: {r.raw_output}")

asyncio.run(main())
