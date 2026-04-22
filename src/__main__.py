"""
aiDaptive Benchmark Suite - Entry Point

Usage:
    python -m src                         Start Web UI
    python -m src run                     Run benchmark (CLI)
    python -m src run --suite all         Run all suites
    python -m src status                  Check server status
    python -m src preflight               Preflight checks
"""

import click
import os
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.config import load_config
from src.data.data_sink import DataSink
from src.orchestrator import Orchestrator

console = Console()


def print_banner():
    banner = (
        "\n"
        "    +----------------------------------------------+\n"
        "    |       aiDaptive Benchmark Suite v1.0.0       |\n"
        "    +----------------------------------------------+\n"
    )
    console.print(banner, style="bold purple")


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("--config", "-c", default="benchmark.yaml", help="Config file path")
def cli(ctx, config):
    """aiDaptive Benchmark Suite"""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config

    if ctx.invoked_subcommand is None:
        print_banner()
        cfg = load_config(config)
        host = os.getenv("AIDAPTIVE_APP_HOST", cfg.app.host)
        port = int(os.getenv("AIDAPTIVE_APP_PORT", str(cfg.app.port)))
        console.print(f"  Web UI:  http://localhost:{port}", style="white")
        console.print(f"  Grafana: http://localhost:3000", style="white")
        console.print("")
        uvicorn.run(
            "src.app:app",
            host=host,
            port=port,
            reload=False,
        )


@cli.command()
@click.option("--suite", "-s", default="all", help="Test suite name")
@click.option("--server", default="all", help="server1 / server2 / all")
@click.option("--environment", "-e", default="lan", help="Network environment")
@click.option("--notes", "-n", default="", help="Run notes")
@click.pass_context
def run(ctx, suite, server, environment, notes):
    """Run benchmark from CLI"""
    print_banner()
    cfg = load_config(ctx.obj["config_path"])
    data_sink = DataSink(cfg)
    orchestrator = Orchestrator(cfg, data_sink)

    console.print(
        Panel(
            f"Suite: {suite}\nServer: {server}\nEnvironment: {environment}",
            title="Benchmark Configuration",
            border_style="purple",
        )
    )

    run_id = orchestrator.generate_run_id()
    console.print(f"  Run ID: {run_id}", style="purple")
    console.print("")

    orchestrator.run_sync(
        run_id=run_id,
        suite=suite,
        server=server,
        environment=environment,
        notes=notes,
    )

    data_sink.close()


@cli.command()
@click.pass_context
def status(ctx):
    """Check all server and service status"""
    import asyncio

    print_banner()
    cfg = load_config(ctx.obj["config_path"])
    data_sink = DataSink(cfg)
    orchestrator = Orchestrator(cfg, data_sink)

    table = Table(title="System Status", border_style="purple")
    table.add_column("Component", style="white")
    table.add_column("Endpoint", style="white")
    table.add_column("Status", style="white")

    statuses = asyncio.run(orchestrator.check_all_status())

    for component, endpoint, is_ok in statuses:
        status_text = "[green]ONLINE[/green]" if is_ok else "[red]OFFLINE[/red]"
        table.add_row(component, endpoint, status_text)

    console.print(table)
    data_sink.close()


@cli.command()
@click.pass_context
def preflight(ctx):
    """Run preflight checks"""
    import asyncio

    print_banner()
    cfg = load_config(ctx.obj["config_path"])
    data_sink = DataSink(cfg)
    orchestrator = Orchestrator(cfg, data_sink)
    asyncio.run(orchestrator.preflight_check())
    data_sink.close()


if __name__ == "__main__":
    cli()
