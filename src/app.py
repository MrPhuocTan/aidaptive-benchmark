"""FastAPI Web Application - Controller UI"""

import asyncio
import ipaddress
from pathlib import Path
from src.time_utils import get_local_time
from datetime import datetime
import anyio

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------------------------------
# Import config first to check for errors
# --------------------------------------------------
from src.config import load_config

config = load_config(str(BASE_DIR / "benchmark.yaml"))

# --------------------------------------------------
# Import database
# --------------------------------------------------
from src.database.engine import Database
from src.database.repository import AsyncRepository

database = Database(config.postgres)

# --------------------------------------------------
# Import data sink (may fail if influx not ready, thats ok)
# --------------------------------------------------
try:
    from src.data.data_sink import DataSink
    data_sink = DataSink(config)
except Exception as e:
    print(f"  Warning: DataSink init error (will retry): {e}")
    data_sink = None

# --------------------------------------------------
# Import orchestrator
# --------------------------------------------------
try:
    from src.orchestrator import Orchestrator
    if data_sink:
        orchestrator = Orchestrator(config, data_sink)
    else:
        orchestrator = None
except Exception as e:
    print(f"  Warning: Orchestrator init error: {e}")
    orchestrator = None

# --------------------------------------------------
# Import agent client
# --------------------------------------------------
from src.collectors.agent_client import AgentClient
from src.collectors.server_discovery import ServerDiscovery
from src.i18n import SUPPORTED_LANGUAGES, get_client_translations, normalize_lang, translate

# --------------------------------------------------
# Create FastAPI app
# --------------------------------------------------
app = FastAPI(title="Benchmark AI Server System", version="1.0.0")
STATIC_VERSION = str(int(get_local_time().timestamp()))


class NoCacheMiddleware(BaseHTTPMiddleware):
    """Force no-cache on all routes (templates and static) to ensure code updates are immediately visible."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


app.add_middleware(NoCacheMiddleware)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["static_version"] = STATIC_VERSION


def _derive_aidaptive_enabled(server_id: str, server_cfg) -> bool:
    name = (getattr(server_cfg, "name", "") or "").lower()
    description = (getattr(server_cfg, "description", "") or "").lower()
    return server_id == "server2" or "aidaptive" in name or "aidaptive" in description


async def _build_server_payload(server_id: str, server_cfg) -> dict:
    client = AgentClient(
        agent_url=server_cfg.agent_url,
        ollama_url=server_cfg.ollama_url,
        server_id=server_id,
    )
    status = await client.get_server_status(server_cfg.name)
    system_metrics = await client.get_system_metrics() if status.agent_online else None
    return {
        "server_id": status.server_id,
        "name": status.server_name or server_cfg.name,
        "description": server_cfg.description,
        "aidaptive_enabled": _derive_aidaptive_enabled(server_id, server_cfg),
        "ollama_online": status.ollama_online,
        "agent_online": status.agent_online,
        "models_loaded": status.models_loaded,
        "hardware": {
            "gpu_name": status.gpu_name,
            "gpu_vram_gb": status.vram_total_gb,
            "cpu_name": system_metrics.get("cpu_model") if system_metrics else None,
            "ram_total_gb": system_metrics.get("ram_total_gb") if system_metrics else None,
        },
        "agent_url": server_cfg.agent_url,
        "ollama_url": server_cfg.ollama_url,
        "ip_address": getattr(server_cfg, 'ip_address', None) or server_id,
    }


def _resolve_lang(request: Request) -> str:
    query_lang = request.query_params.get("lang")
    if query_lang:
        return normalize_lang(query_lang)
    cookie_lang = request.cookies.get("aidaptive_lang")
    if cookie_lang:
        return normalize_lang(cookie_lang)
    accept_language = request.headers.get("accept-language", "")
    if accept_language:
        return normalize_lang(accept_language.split(",")[0])
    return "en"


def _t_for_request(request: Request, key: str, **kwargs) -> str:
    return translate(_resolve_lang(request), key, **kwargs)


def _template_context(request: Request, **context) -> dict:
    lang = _resolve_lang(request)
    return {
        **context,
        "lang": lang,
        "languages": SUPPORTED_LANGUAGES,
        "t": lambda key, **kwargs: translate(lang, key, **kwargs),
        "js_translations": get_client_translations(lang),
    }


def _render(request: Request, name: str, context: dict):
    lang = _resolve_lang(request)
    response = templates.TemplateResponse(
        request=request,
        name=name,
        context=_template_context(request, **context),
    )
    if request.query_params.get("lang"):
        response.set_cookie(
            "aidaptive_lang",
            lang,
            max_age=60 * 60 * 24 * 365,
            samesite="lax",
        )
    return response


def _database_ready() -> bool:
    return database.is_connected()


def _db_warning_payload() -> dict:
    return {
        "db_available": False,
        "db_warning": "PostgreSQL is unavailable. Start the database services, then refresh.",
    }


def _empty_run_summary() -> dict:
    return {
        "server1": {},
        "server2": {},
    }


def _database_unavailable_json() -> JSONResponse:
    return JSONResponse(
        {
            "error": "service_unavailable",
            "message": "PostgreSQL is unavailable. Start the database services, then retry.",
        },
        status_code=503,
    )


# --------------------------------------------------
# Dependencies
# --------------------------------------------------
async def get_db():
    async with database.AsyncSession() as session:
        yield session


# --------------------------------------------------
# Lifecycle
# --------------------------------------------------
# Extracted to src/background.py

@app.on_event("startup")
async def startup():
    try:
        database.create_tables()
        from src.database.seed import run_seed
        run_seed(database)
        print("  Database tables created and seeded.")
        
        async with database.AsyncSession() as session:
            from sqlalchemy import text
            from sqlalchemy.future import select
            from src.database.tables import ServerProfile
            from src.config import ServerConfig
            try:
                await session.execute(text("ALTER TABLE server_profiles ADD COLUMN ip_address VARCHAR(50);"))
                await session.execute(text("ALTER TABLE server_profiles ADD COLUMN status VARCHAR(50);"))
                await session.commit()
            except Exception:
                await session.rollback()
                
            result = await session.execute(select(ServerProfile))
            profiles = result.scalars().all()
            config.servers.clear()
            for p in profiles:
                if p.ip_address:
                    config.servers[p.server_id] = ServerConfig(
                        name=p.name or p.server_id,
                        description=p.description or "",
                        ollama_url=f"http://{p.ip_address}:11434",
                        agent_url=f"http://{p.ip_address}:9100",
                    )
                else:
                    # Fallback for old records without ip_address
                    config.servers[p.server_id] = ServerConfig(
                        name=p.name or p.server_id,
                        description=p.description or "",
                        ollama_url="",
                        agent_url="",
                    )
        
        from src.background import sync_server_profiles_loop
        asyncio.create_task(sync_server_profiles_loop(config, database))
        
        # Auto-resume zombie runs
        if orchestrator:
            async def resume_zombie():
                async with database.AsyncSession() as session:
                    repo = AsyncRepository(session)
                    running_run = await repo.get_current_running_run()
                    if running_run:
                        print(f"  Found interrupted run {running_run.run_id}. Resuming...")
                        snapshot = running_run.config_snapshot or {}
                        suite = snapshot.get("suite", "all")
                        server = snapshot.get("server", "all")
                        env = snapshot.get("environment", "lan")
                        
                        # Trigger resume asynchronously
                        asyncio.create_task(
                            orchestrator.run_async(
                                run_id=running_run.run_id,
                                suite=suite,
                                server=server,
                                environment=env,
                                notes=running_run.notes or "",
                                tags=running_run.tags or [],
                                resume_from_db=True
                            )
                        )
            asyncio.create_task(resume_zombie())
            
    except Exception as e:
        print(f"  Database startup error: {e}")


@app.on_event("shutdown")
async def shutdown():
    if data_sink:
        data_sink.close()
    await database.close()


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return RedirectResponse(url=f"/static/favicon.svg?v={STATIC_VERSION}", status_code=307)


# --------------------------------------------------
# Page: Dashboard
# --------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def page_dashboard(request: Request, session: AsyncSession = Depends(get_db)):
    db_ok = _database_ready()
    recent_runs, total_runs, trend = [], 0, []

    if db_ok:
        repo = AsyncRepository(session)
        try:
            recent_runs = await repo.list_runs(limit=5)
            total_runs = await repo.count_runs()
            chart_runs = [r for r in recent_runs if r.status == "completed"][:5]
            for run in reversed(chart_runs):
                summary = await repo.get_run_summary_stats(run.run_id)
                trend.append({
                    "run_id": run.run_id,
                    "server1_tps": summary.get("server1", {}).get("avg_tps"),
                    "server2_tps": summary.get("server2", {}).get("avg_tps"),
                })
        except SQLAlchemyError:
            db_ok = False

    statuses = []
    async def fetch_status(server_id, server_cfg):
        client = AgentClient(
            agent_url=server_cfg.agent_url,
            ollama_url=server_cfg.ollama_url,
            server_id=server_id,
            timeout=1.0,
        )
        return await client.get_server_status(server_cfg.name)

    tasks = [fetch_status(sid, cfg) for sid, cfg in config.servers.items()]
    statuses = await asyncio.gather(*tasks) if tasks else []

    return _render(
        request,
        "dashboard.html",
        {
            "page": "dashboard",
            "config": config,
            "recent_runs": recent_runs,
            "total_runs": total_runs,
            "trend": trend,
            "db_available": db_ok,
            "statuses": statuses,
            **(_db_warning_payload() if not db_ok else {}),
        },
    )


# --------------------------------------------------
# Page: Servers
# --------------------------------------------------
@app.get("/servers", response_class=HTMLResponse)
async def page_servers(request: Request, session: AsyncSession = Depends(get_db)):
    from sqlalchemy.future import select
    from src.database.tables import ServerProfile
    
    result = await session.execute(select(ServerProfile).order_by(ServerProfile.recorded_at.desc()))
    profiles = result.scalars().all()
    
    async def fetch_status(p):
        client = AgentClient(
            agent_url=f"http://{p.ip_address}:9100",
            ollama_url=f"http://{p.ip_address}:11434",
            server_id=p.server_id,
            timeout=1.0,
        )
        status = await client.get_server_status(p.name)
        return {
            "profile": p,
            "status": status,
        }

    tasks = [fetch_status(p) for p in profiles]
    servers_data = await asyncio.gather(*tasks) if tasks else []

    return _render(
        request,
        "servers.html",
        {
            "page": "servers",
            "servers_data": servers_data,
            "config": config,
        },
    )


# --------------------------------------------------
# Page: Benchmark
# --------------------------------------------------
@app.get("/benchmark", response_class=HTMLResponse)
async def page_benchmark(request: Request):
    return _render(
        request,
        "benchmark.html",
        {
            "page": "benchmark",
            "config": config,
        },
    )


# --------------------------------------------------
# Page: History
# --------------------------------------------------
@app.get("/history", response_class=HTMLResponse)
async def page_history(
    request: Request,
    page_num: int = 1,
    session: AsyncSession = Depends(get_db),
):
    db_ok = _database_ready()
    runs, total, total_pages = [], 0, 1

    if db_ok:
        repo = AsyncRepository(session)
        per_page = 20
        offset = (page_num - 1) * per_page
        try:
            runs = await repo.list_runs(limit=per_page, offset=offset)
            total = await repo.count_runs()
            total_pages = max(1, (total + per_page - 1) // per_page)
        except SQLAlchemyError:
            db_ok = False

    return _render(
        request,
        "history.html",
        {
            "page": "history",
            "config": config,
            "runs": runs,
            "current_page": page_num,
            "total_pages": total_pages,
            "total_runs": total,
            "db_available": db_ok,
            **(_db_warning_payload() if not db_ok else {}),
        },
    )


# --------------------------------------------------
# Page: Run Detail
# --------------------------------------------------
@app.get("/history/{run_id}", response_class=HTMLResponse)
async def page_run_detail(
    request: Request,
    run_id: str,
    session: AsyncSession = Depends(get_db),
):
    if not _database_ready():
        return HTMLResponse(content="Database unavailable", status_code=503)

    repo = AsyncRepository(session)
    try:
        run = await repo.get_run(run_id)
    except SQLAlchemyError:
        return HTMLResponse(content="Database unavailable", status_code=503)

    if not run:
        return HTMLResponse(content=_t_for_request(request, "api.run_not_found"), status_code=404)

    try:
        results = await repo.get_results_by_run(run_id)
        comparisons = await repo.get_comparisons_by_run(run_id)
        summary = await repo.get_run_summary_stats(run_id)
        comparison_chart = await repo.get_comparison_chart_data(run_id)
        timeline_chart = await repo.get_timeline_chart_data(run_id)
    except SQLAlchemyError:
        results = []
        comparisons = []
        summary = _empty_run_summary()
        comparison_chart = {}
        timeline_chart = {}

    return _render(
        request,
        "run_detail.html",
        {
            "page": "history",
            "config": config,
            "run": run,
            "results": results,
            "comparisons": comparisons,
            "summary": summary,
            "comparison_chart": comparison_chart,
            "timeline_chart": timeline_chart,
            "db_available": _database_ready(),
        },
    )


# --------------------------------------------------
# Page: Comparison
# --------------------------------------------------
@app.get("/comparison", response_class=HTMLResponse)
async def page_comparison(
    request: Request,
    run1: str = "",
    run2: str = "",
    session: AsyncSession = Depends(get_db),
):
    db_ok = _database_ready()
    all_runs, data_run1, data_run2 = [], None, None

    if db_ok:
        repo = AsyncRepository(session)
        try:
            all_runs = await repo.list_runs(limit=100)
            if run1:
                data_run1 = await repo.get_run_summary_stats(run1)
            if run2:
                data_run2 = await repo.get_run_summary_stats(run2)
        except SQLAlchemyError:
            db_ok = False

    return _render(
        request,
        "comparison.html",
        {
            "page": "comparison",
            "config": config,
            "all_runs": all_runs,
            "selected_run1": run1,
            "selected_run2": run2,
            "data_run1": data_run1,
            "data_run2": data_run2,
            "db_available": db_ok,
            **(_db_warning_payload() if not db_ok else {}),
        },
    )


# --------------------------------------------------
# Page: Settings
# --------------------------------------------------
@app.get("/settings", response_class=HTMLResponse)
async def page_settings(request: Request):
    return _render(
        request,
        "settings.html",
        {
            "page": "settings",
            "config": config,
        },
    )


# --------------------------------------------------
# API: Status
# --------------------------------------------------
@app.get("/api/status")
async def api_status():
    server_statuses = []
    for server_id, server_cfg in config.servers.items():
        server_statuses.append(await _build_server_payload(server_id, server_cfg))

    pg_ok = database.is_connected()
    influx_ok = False
    if data_sink:
        try:
            influx_ok = data_sink.influx.is_connected()
        except Exception:
            pass

    return {
        "status": "ok",
        "timestamp": get_local_time().isoformat(),
        "servers": server_statuses,
        "database": {
            "postgres": pg_ok,
            "influxdb": influx_ok,
        },
        "postgres": pg_ok,
        "influxdb": influx_ok,
        "benchmark": {
            "is_running": orchestrator.is_running() if orchestrator else False,
            "current_run_id": orchestrator.get_progress().get("run_id") if orchestrator and orchestrator.is_running() else None,
        },
    }


@app.get("/api/health")
async def api_health():
    return {
        "status": "ok",
        "timestamp": get_local_time().isoformat(),
        "app": config.app.name,
        "version": config.app.version,
    }


# --------------------------------------------------
# API: Server Specs
# --------------------------------------------------
@app.get("/api/servers/{server_id}/specs")
async def api_server_specs(server_id: str):
    if server_id not in config.servers:
        return JSONResponse({"error": "Server not found"}, status_code=404)
        
    server_cfg = config.servers[server_id]
    client = AgentClient(
        agent_url=server_cfg.agent_url,
        ollama_url=server_cfg.ollama_url,
        server_id=server_id,
        timeout=3.0,
    )
    
    specs = await client.get_server_specs()
    return {"specs": specs}

# --------------------------------------------------
# API: Start benchmark
# --------------------------------------------------
@app.post("/api/benchmark/start")
async def api_benchmark_start(request: Request):
    if not orchestrator:
        return JSONResponse({"error": _t_for_request(request, "api.orchestrator_not_initialized")}, status_code=500)
    if orchestrator.is_running():
        return JSONResponse(
            {"error": _t_for_request(request, "api.benchmark_in_progress")},
            status_code=409,
        )

    body = await request.json()
    suite = body.get("suite", "all")
    servers = body.get("servers", [])
    environment = body.get("environment", "lan")
    notes = body.get("notes", "")
    tags = body.get("tags", [])

    advanced_options = body.get("advanced_options")
    if advanced_options:
        if "warmup_requests" in advanced_options:
            config.benchmark.warmup_requests = advanced_options["warmup_requests"]
        if "cooldown_seconds" in advanced_options:
            config.benchmark.cooldown_seconds = advanced_options["cooldown_seconds"]
        if "concurrency_levels" in advanced_options:
            try:
                levels = [int(x.strip()) for x in advanced_options["concurrency_levels"].split(",")]
                config.benchmark.concurrency_levels = levels
            except ValueError:
                pass # fallback to default if parsing fails

    run_id = orchestrator.generate_run_id()

    asyncio.create_task(
        orchestrator.run_async(
            run_id=run_id,
            suite=suite,
            target_servers=servers,
            environment=environment,
            notes=notes,
            tags=tags,
        )
    )

    return {
        "run_id": run_id,
        "status": "started",
        "message": _t_for_request(request, "api.benchmark_started"),
    }


@app.post("/api/benchmark/stop")
async def api_benchmark_stop(request: Request, session: AsyncSession = Depends(get_db)):
    if not orchestrator:
        return JSONResponse(
            {
                "error": "service_unavailable",
                "message": _t_for_request(request, "api.service_unavailable"),
            },
            status_code=503,
        )

    # Check if orchestrator is running
    if orchestrator.is_running():
        try:
            result = orchestrator.request_stop()
            progress = orchestrator.get_progress()
            return {
                "run_id": result["run_id"],
                "status": "stopped",
                "message": result["message"],
                "progress": progress,
            }
        except Exception as e:
            return JSONResponse(
                {"error": _t_for_request(request, "api.stop_failed", error=str(e))},
                status_code=500,
            )
            
    # If orchestrator is NOT running, but DB has a zombie run, stop it in DB!
    if _database_ready():
        repo = AsyncRepository(session)
        running_run = await repo.get_current_running_run()
        if running_run:
            await repo.stop_run(running_run.run_id, status="failed", error_message="Run was interrupted by server restart and stopped manually.")
            return {
                "run_id": running_run.run_id,
                "status": "stopped",
                "message": "Zombie run stopped successfully.",
                "progress": {"status": "idle"}
            }
            
    return JSONResponse(
        {"error": "No running benchmark found to stop."},
        status_code=400,
    )


@app.post("/api/server/discover")
async def api_server_discover(request: Request):
    body = await request.json()
    ip = (body.get("ip") or "").strip()
    if not ip:
        return JSONResponse({"error": _t_for_request(request, "api.ip_required")}, status_code=400)
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        return JSONResponse({"error": _t_for_request(request, "api.invalid_ip")}, status_code=400)

    discovery = ServerDiscovery()

    try:
        result = await discovery.discover(ip)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse(
            {"error": _t_for_request(request, "api.discovery_failed", error=str(e))},
            status_code=500,
        )

    return {"server": result}


# --------------------------------------------------
# API: Progress
# --------------------------------------------------
@app.get("/api/benchmark/progress")
async def api_benchmark_progress(session: AsyncSession = Depends(get_db)):
    if orchestrator and orchestrator.is_running():
        return orchestrator.get_progress()
        
    # Check for zombie runs in DB after server restart
    if _database_ready():
        repo = AsyncRepository(session)
        try:
            running_run = await repo.get_current_running_run()
            if running_run:
                from src.time_utils import get_local_time
                elapsed = int((get_local_time() - running_run.started_at).total_seconds())
                # Return a mock progress object to satisfy the UI requirement
                return {
                    "status": "running",
                    "run_id": running_run.run_id,
                    "current_phase": "Interrupted by Restart",
                    "current_test": "Please click Stop to terminate this run",
                    "total_tests": 100,
                    "completed_tests": 99,
                    "percent": 99,
                    "started_at": running_run.started_at.isoformat(),
                    "errors": [],
                    "elapsed_seconds": elapsed,
                    "estimated_remaining_seconds": None,
                    "live_metrics": {
                        "last_tps": None,
                        "last_ttft_ms": None,
                        "current_server": "Lost Connection"
                    }
                }
        except Exception:
            pass

    return {"status": "idle"}


@app.get("/api/servers")
async def api_servers():
    payload = []
    for server_id, server_cfg in config.servers.items():
        payload.append(await _build_server_payload(server_id, server_cfg))
    return {"servers": payload}

from pydantic import BaseModel

class VerifyServerRequest(BaseModel):
    ip: str

@app.post("/api/servers/verify")
async def api_verify_server(req: VerifyServerRequest):
    ip = req.ip.strip()
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        return JSONResponse({"error": "Invalid IP address"}, status_code=400)
    
    client = AgentClient(
        agent_url=f"http://{ip}:9100",
        ollama_url=f"http://{ip}:11434",
        server_id=ip,
    )
    
    agent_ok = await client.check_agent_health()
    ollama_ok = await client.check_ollama_health()
    
    return {
        "ip": ip,
        "agent_ok": agent_ok,
        "ollama_ok": ollama_ok,
    }

class AddServerRequest(BaseModel):
    ip: str
    name: str

@app.post("/api/servers")
async def api_add_server(req: AddServerRequest, session: AsyncSession = Depends(get_db)):
    ip = req.ip.strip()
    name = req.name.strip()
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        return JSONResponse({"error": "Invalid IP address"}, status_code=400)
    
    from src.database.tables import ServerProfile
    from sqlalchemy.future import select
    from src.config import ServerConfig
    
    # Check if exists
    result = await session.execute(select(ServerProfile).filter_by(server_id=ip))
    profile = result.scalars().first()
    
    if profile:
        profile.name = name
        profile.ip_address = ip
    else:
        profile = ServerProfile(
            server_id=ip,
            name=name,
            ip_address=ip,
            status="active"
        )
        session.add(profile)
        
    await session.commit()
    
    # Update memory
    config.servers[ip] = ServerConfig(
        name=name,
        description="",
        ollama_url=f"http://{ip}:11434",
        agent_url=f"http://{ip}:9100",
    )
    
    return {"status": "ok", "server": await _build_server_payload(ip, config.servers[ip])}

@app.delete("/api/servers/{ip}")
async def api_delete_server(ip: str, session: AsyncSession = Depends(get_db)):
    from src.database.tables import ServerProfile
    from sqlalchemy.future import select
    
    result = await session.execute(select(ServerProfile).filter_by(server_id=ip))
    profile = result.scalars().first()
    
    if profile:
        await session.delete(profile)
        await session.commit()
        
    if ip in config.servers:
        del config.servers[ip]
        
    return {"status": "ok"}



@app.get("/api/servers/{server_id}/metrics")
async def api_server_metrics(server_id: str, request: Request):
    server_cfg = config.servers.get(server_id)
    if not server_cfg:
        return JSONResponse({"error": _t_for_request(request, "api.server_not_found")}, status_code=404)

    client = AgentClient(
        agent_url=server_cfg.agent_url,
        ollama_url=server_cfg.ollama_url,
        server_id=server_id,
    )
    metrics = await client.get_all_metrics()
    if metrics is None:
        return JSONResponse({"error": _t_for_request(request, "api.metrics_unavailable")}, status_code=503)

    return {
        "server_id": server_id,
        "timestamp": metrics.timestamp.isoformat() if metrics.timestamp else None,
        "metrics": {
            "gpu_util_pct": metrics.gpu_util_pct,
            "vram_used_gb": metrics.vram_used_gb,
            "vram_total_gb": metrics.vram_total_gb,
            "gpu_power_watts": metrics.gpu_power_watts,
            "gpu_temperature_c": metrics.gpu_temperature_c,
            "cpu_pct": metrics.cpu_pct,
            "ram_used_gb": metrics.ram_used_gb,
            "ram_total_gb": metrics.ram_total_gb,
            "network_rx_mbps": metrics.network_rx_mbps,
            "network_tx_mbps": metrics.network_tx_mbps,
        },
    }


# --------------------------------------------------
# API: List runs
# --------------------------------------------------
@app.get("/api/runs")
async def api_list_runs(
    limit: int = 20,
    offset: int = 0,
    status: str = "",
    session: AsyncSession = Depends(get_db),
):
    if not _database_ready():
        return _database_unavailable_json()

    repo = AsyncRepository(session)
    try:
        runs = await repo.list_runs(limit=limit, offset=offset)
        if status:
            runs = [run for run in runs if run.status == status]
        total = await repo.count_runs(status=status)

        run_winners = {}
        for run in runs:
            run_winners[run.run_id] = await repo.get_run_winner(run.run_id)
    except SQLAlchemyError:
        return _database_unavailable_json()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "runs": [
            {
                "run_id": r.run_id,
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "duration_seconds": r.duration_seconds,
                "suite": r.suite,
                "environment": r.environment,
                "model": r.model,
                "total_tests": r.total_tests,
                "completed_tests": r.completed_tests,
                "notes": r.notes,
                "tags": r.tags,
                "winner": run_winners.get(r.run_id),
            }
            for r in runs
        ],
    }


# --------------------------------------------------
# API: Run detail
# --------------------------------------------------
@app.get("/api/runs/{run_id}")
async def api_run_detail(
    request: Request,
    run_id: str,
    session: AsyncSession = Depends(get_db),
):
    if not _database_ready():
        return _database_unavailable_json()

    repo = AsyncRepository(session)
    try:
        run = await repo.get_run(run_id)
    except SQLAlchemyError:
        return _database_unavailable_json()

    if not run:
        return JSONResponse({"error": _t_for_request(request, "api.run_not_found")}, status_code=404)

    try:
        results = await repo.get_results_by_run(run_id)
        comparisons = await repo.get_comparisons_by_run(run_id)
        summary = await repo.get_run_summary_stats(run_id)
    except SQLAlchemyError:
        return _database_unavailable_json()

    return {
        "run": {
            "run_id": run.run_id,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "duration_seconds": run.duration_seconds,
            "suite": run.suite,
            "environment": run.environment,
            "model": run.model,
            "notes": run.notes,
            "tags": run.tags,
            "total_tests": run.total_tests,
            "completed_tests": run.completed_tests,
            "config_snapshot": run.config_snapshot,
        },
        "summary": summary,
        "results_count": len(results),
        "comparisons": [
            {
                "environment": c.environment,
                "scenario": c.scenario,
                "tool": c.tool,
                "s1_tps": c.s1_tps,
                "s2_tps": c.s2_tps,
                "delta_tps_pct": c.delta_tps_pct,
                "s1_ttft_ms": c.s1_ttft_ms,
                "s2_ttft_ms": c.s2_ttft_ms,
                "delta_ttft_pct": c.delta_ttft_pct,
                "overall_winner": c.overall_winner,
                "cost_savings_pct": c.cost_savings_pct,
            }
            for c in comparisons
        ],
    }


@app.get("/api/charts/comparison/{run_id}")
async def api_chart_comparison(
    request: Request,
    run_id: str,
    session: AsyncSession = Depends(get_db),
):
    if not _database_ready():
        return _database_unavailable_json()

    repo = AsyncRepository(session)
    try:
        run = await repo.get_run(run_id)
    except SQLAlchemyError:
        return _database_unavailable_json()
    if not run:
        return JSONResponse({"error": _t_for_request(request, "api.run_not_found")}, status_code=404)
    try:
        return await repo.get_comparison_chart_data(run_id)
    except SQLAlchemyError:
        return _database_unavailable_json()


@app.get("/api/charts/timeline/{run_id}")
async def api_chart_timeline(
    request: Request,
    run_id: str,
    session: AsyncSession = Depends(get_db),
):
    if not _database_ready():
        return _database_unavailable_json()

    repo = AsyncRepository(session)
    try:
        run = await repo.get_run(run_id)
    except SQLAlchemyError:
        return _database_unavailable_json()
    if not run:
        return JSONResponse({"error": _t_for_request(request, "api.run_not_found")}, status_code=404)
    try:
        return await repo.get_timeline_chart_data(run_id)
    except SQLAlchemyError:
        return _database_unavailable_json()


@app.get("/api/charts/summary/{run_id}")
async def api_chart_summary(
    request: Request,
    run_id: str,
    session: AsyncSession = Depends(get_db),
):
    if not _database_ready():
        return _database_unavailable_json()

    repo = AsyncRepository(session)
    try:
        run = await repo.get_run(run_id)
    except SQLAlchemyError:
        return _database_unavailable_json()
    if not run:
        return JSONResponse({"error": _t_for_request(request, "api.run_not_found")}, status_code=404)
    try:
        summary = await repo.get_run_summary_stats(run_id)
        winner = await repo.get_run_winner(run_id)
    except SQLAlchemyError:
        return _database_unavailable_json()
    return {
        "run_id": run_id,
        "winner": winner,
        "server1": summary.get("server1", {}),
        "server2": summary.get("server2", {}),
    }


# --------------------------------------------------
# API: Delete run
# --------------------------------------------------
@app.delete("/api/runs/{run_id}")
async def api_delete_run(
    request: Request,
    run_id: str,
    session: AsyncSession = Depends(get_db),
):
    if not _database_ready():
        return _database_unavailable_json()

    repo = AsyncRepository(session)
    try:
        run = await repo.get_run(run_id)
    except SQLAlchemyError:
        return _database_unavailable_json()
    if not run:
        return JSONResponse({"error": _t_for_request(request, "api.run_not_found")}, status_code=404)

    try:
        await session.delete(run)
        await session.commit()
    except SQLAlchemyError:
        return _database_unavailable_json()
    return {"deleted": run_id}


# --------------------------------------------------
# API: Export CSV
# --------------------------------------------------
@app.get("/api/runs/{run_id}/export")
async def api_export_csv(
    run_id: str,
    session: AsyncSession = Depends(get_db),
):
    if not _database_ready():
        return _database_unavailable_json()

    import csv
    import io

    repo = AsyncRepository(session)
    try:
        results = await repo.get_results_by_run(run_id)
    except SQLAlchemyError:
        return _database_unavailable_json()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "server", "tool", "environment", "scenario", "model",
        "concurrency", "ttft_ms", "tpot_ms", "itl_ms", "tps",
        "rps", "p50_ms", "p95_ms", "p99_ms", "error_rate",
        "total_tokens", "goodput",
    ])

    for r in results:
        writer.writerow([
            r.server, r.tool, r.environment, r.scenario, r.model,
            r.concurrency, r.ttft_ms, r.tpot_ms, r.itl_ms, r.tps,
            r.rps, r.latency_p50_ms, r.latency_p95_ms,
            r.latency_p99_ms, r.error_rate,
            r.total_tokens, r.goodput,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={run_id}.csv"
        },
    )


# --------------------------------------------------
# API: Trend
# --------------------------------------------------
@app.get("/api/trend")
async def api_trend(
    limit: int = 20,
    session: AsyncSession = Depends(get_db),
):
    if not _database_ready():
        return _database_unavailable_json()

    repo = AsyncRepository(session)
    try:
        runs = await repo.list_runs(limit=limit)

        trend = []
        for run in runs:
            if run.status == "completed":
                summary = await repo.get_run_summary_stats(run.run_id)
                trend.append({
                    "run_id": run.run_id,
                    "date": run.started_at.isoformat() if run.started_at else None,
                    "tags": run.tags,
                    "server1": summary.get("server1", {}),
                    "server2": summary.get("server2", {}),
                })
    except SQLAlchemyError:
        return _database_unavailable_json()

    return {"trend": list(reversed(trend))}

# --------------------------------------------------
# Include Routers
# --------------------------------------------------
from src.routers.reports import router as reports_router
app.include_router(reports_router)

