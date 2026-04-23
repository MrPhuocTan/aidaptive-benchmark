"""Orchestrator - controls entire benchmark flow"""

import asyncio
import json
from src.time_utils import get_local_time
from datetime import datetime
from pathlib import Path

from rich.console import Console

from src.config import Config, ServerConfig
from src.collectors.agent_client import AgentClient
from src.collectors.metric_collector import MetricCollector
from src.data.data_sink import DataSink

# Import all adapters
from src.adapters.ollama_adapter import OllamaAdapter
from src.adapters.oha_adapter import OhaAdapter
from src.adapters.litellm_adapter import LiteLLMAdapter
from src.adapters.locust_adapter import LocustAdapter
from src.adapters.llmperf_adapter import LLMPerfAdapter
from src.adapters.vllm_bench_adapter import VLLMBenchAdapter

console = Console()


class Orchestrator:
    """Main orchestrator that controls the entire benchmark process"""

    def __init__(self, config: Config, data_sink: DataSink):
        self.config = config
        self.data_sink = data_sink
        self._run_lock = asyncio.Lock()
        self._cancel_requested = False
        self._current_run_id = None
        self._live_metrics = {
            "last_tps": None,
            "last_ttft_ms": None,
            "current_server": None,
        }

        self._progress = {
            "status": "idle",
            "run_id": "",
            "current_phase": "",
            "current_test": "",
            "total_tests": 0,
            "completed_tests": 0,
            "percent": 0,
            "started_at": None,
            "errors": [],
            "elapsed_seconds": 0,
            "estimated_remaining_seconds": None,
            "live_metrics": self._live_metrics.copy(),
        }

        self.agent_clients = {}
        for server_id, server_cfg in config.servers.items():
            self.agent_clients[server_id] = AgentClient(
                agent_url=server_cfg.agent_url,
                ollama_url=server_cfg.ollama_url,
                server_id=server_id,
            )

    def generate_run_id(self) -> str:
        return f"run_{get_local_time().strftime('%Y%m%d_%H%M%S')}"

    def get_progress(self) -> dict:
        progress = self._progress.copy()
        if progress.get("started_at") and progress["status"] == "running":
            started_at = datetime.fromisoformat(progress["started_at"])
            elapsed = int((get_local_time() - started_at).total_seconds())
            progress["elapsed_seconds"] = max(elapsed, 0)
            completed = progress.get("completed_tests", 0)
            total = progress.get("total_tests", 0)
            if completed > 0 and total > completed:
                avg_time_per_test = elapsed / completed
                progress["estimated_remaining_seconds"] = int(
                    avg_time_per_test * (total - completed)
                )
            else:
                progress["estimated_remaining_seconds"] = None
        progress["live_metrics"] = self._live_metrics.copy()
        return progress

    def request_stop(self) -> dict:
        if not self.is_running():
            raise RuntimeError("No benchmark running")
        self._cancel_requested = True
        self._progress["status"] = "stopping"
        self._progress["current_phase"] = "Stopping"
        return {
            "run_id": self._current_run_id,
            "status": "stopping",
            "message": "Stop requested. Partial results will be saved.",
        }

    def _check_cancelled(self):
        if self._cancel_requested:
            raise asyncio.CancelledError("Benchmark stop requested")

    def _record_live_metrics(self, result, server_id: str):
        if result.tps is not None:
            self._live_metrics["last_tps"] = round(float(result.tps), 2)
        if result.ttft_ms is not None:
            self._live_metrics["last_ttft_ms"] = round(float(result.ttft_ms), 2)
        self._live_metrics["current_server"] = server_id

    def _get_enabled_tools(self, suite_name: str = None) -> list:
        """Get list of enabled tools with their adapter classes"""
        enabled_tools = []

        tool_mapping = {
            "ollama_native": OllamaAdapter,
            "oha": OhaAdapter,
            "litellm": LiteLLMAdapter,
            "locust": LocustAdapter,
            "llmperf": LLMPerfAdapter,
            "vllm_bench": VLLMBenchAdapter,
        }

        for tool_name, adapter_class in tool_mapping.items():
            tool_cfg = self.config.tools.get(tool_name)
            if tool_cfg and tool_cfg.enabled:
                if suite_name and tool_cfg.supported_suites:
                    if suite_name not in tool_cfg.supported_suites:
                        continue
                enabled_tools.append((tool_name, adapter_class, tool_cfg))

        return enabled_tools

    def _split_available_tools(
        self,
        enabled_tools: list,
        target_url: str,
        model: str,
    ) -> tuple[list, list[str]]:
        available_tools = []
        unavailable_tools = []

        for tool_name, adapter_class, tool_cfg in enabled_tools:
            adapter = self._create_adapter(
                tool_name,
                adapter_class,
                tool_cfg,
                target_url,
                model,
            )
            if adapter.is_available():
                available_tools.append((tool_name, adapter_class, tool_cfg))
            else:
                unavailable_tools.append(tool_name)

        return available_tools, unavailable_tools

    def _create_adapter(
        self,
        tool_name: str,
        adapter_class,
        tool_cfg,
        target_url: str,
        model: str,
        concurrency: int = 10,
        suite_cfg=None,
    ):
        """Create adapter instance based on tool type"""

        duration = suite_cfg.duration_seconds if suite_cfg else 60
        num_requests = suite_cfg.requests_per_scenario if suite_cfg else 200
        binary_path = tool_cfg.binary_path or None

        if tool_name == "ollama_native":
            return adapter_class(ollama_url=target_url, model=model)

        elif tool_name == "oha":
            kwargs = {
                "ollama_url": target_url,
                "model": model,
                "concurrency": concurrency,
                "num_requests": num_requests,
            }
            if binary_path:
                kwargs["binary_path"] = binary_path
            return adapter_class(**kwargs)


        elif tool_name == "litellm":
            return adapter_class(ollama_url=target_url, model=model)

        elif tool_name == "locust":
            kwargs = {
                "ollama_url": target_url,
                "model": model,
                "concurrency": concurrency,
                "duration": duration,
            }
            if binary_path:
                kwargs["binary_path"] = binary_path
            return adapter_class(**kwargs)

        elif tool_name == "llmperf":
            return adapter_class(ollama_url=target_url, model=model, concurrency=concurrency)

        elif tool_name == "vllm_bench":
            return adapter_class(
                ollama_url=target_url,
                model=model,
                concurrency=concurrency,
            )

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def is_running(self) -> bool:
        return self._progress["status"] == "running"

    async def _validate_run_targets(
        self,
        servers_to_test: list,
        environment: str,
        enabled_tools: list,
    ) -> dict:
        env_cfg = self.config.environments.get(environment)
        if not env_cfg:
            raise ValueError(f"Environment '{environment}' not found in config")

        resolved_targets = {}

        for server_id in servers_to_test:
            server_cfg = self.config.servers.get(server_id)
            if not server_cfg:
                raise ValueError(f"Server '{server_id}' not found in config")
            
            client = self.agent_clients.get(server_id)
            if not client:
                client = AgentClient(
                    agent_url=server_cfg.agent_url,
                    ollama_url=server_cfg.ollama_url,
                    server_id=server_id,
                )
                self.agent_clients[server_id] = client

            target_url = getattr(env_cfg, f"{server_id}_url", "") or server_cfg.ollama_url
            if not target_url:
                raise ValueError(f"No Ollama URL configured for server '{server_id}'")

            agent_ok = await client.check_agent_health()
            ollama_ok = await client.check_ollama_health(target_url)
            if not agent_ok:
                raise RuntimeError(f"Agent for '{server_id}' is offline")
            if not ollama_ok:
                raise RuntimeError(
                    f"Ollama for '{server_id}' is offline at target URL '{target_url}'"
                )

            models = await client.get_ollama_models(target_url)
            for model in self.config.models:
                if model not in models:
                    raise RuntimeError(
                        f"Model '{model}' not available on '{server_id}' at '{target_url}'"
                    )

            resolved_targets[server_id] = target_url

        available_tools, unavailable_tools = self._split_available_tools(
            enabled_tools,
            next(iter(resolved_targets.values())),
            self.config.models[0],
        )

        if not available_tools:
            raise RuntimeError(
                f"No benchmark tools are available in this environment. Missing: {', '.join(unavailable_tools)}"
            )

        return resolved_targets

    async def check_all_status(self) -> list:
        """Check status of all components"""
        results = []

        for server_id, client in self.agent_clients.items():
            server_cfg = self.config.servers[server_id]

            ollama_ok = await client.check_ollama_health()
            results.append((
                f"{server_cfg.name} - Ollama",
                server_cfg.ollama_url,
                ollama_ok,
            ))

            agent_ok = await client.check_agent_health()
            results.append((
                f"{server_cfg.name} - Agent",
                server_cfg.agent_url,
                agent_ok,
            ))

        pg_ok = self.data_sink.db.is_connected()
        results.append(("PostgreSQL", self.config.postgres.host, pg_ok))



        return results

    async def preflight_check(self) -> bool:
        """Run all preflight checks before benchmark"""
        console.print("  Running preflight checks...", style="white")
        all_ok = True

        statuses = await self.check_all_status()
        for component, endpoint, is_ok in statuses:
            mark = "[green]OK[/green]" if is_ok else "[red]FAIL[/red]"
            console.print(f"    {mark}  {component} ({endpoint})")
            if not is_ok:
                all_ok = False

        for server_id, client in self.agent_clients.items():
            models = await client.get_ollama_models()
            for model in self.config.models:
                found = any(model == m or model in m for m in models)
                mark = "[green]OK[/green]" if found else "[red]MISSING[/red]"
                console.print(f"    {mark}  Model {model} on {server_id}")
                if not found:
                    all_ok = False

        # Check enabled tools
        enabled_tools = self._get_enabled_tools()
        console.print(f"\n    Enabled tools: {[t[0] for t in enabled_tools]}", style="cyan")
        for tool_name, adapter_class, tool_cfg in enabled_tools:
            adapter = self._create_adapter(
                tool_name,
                adapter_class,
                tool_cfg,
                "http://localhost:11434",
                self.config.models[0] if self.config.models else "unknown",
            )
            available = adapter.is_available()
            mark = "[green]OK[/green]" if available else "[red]MISSING[/red]"
            console.print(f"    {mark}  Tool {tool_name}", style="white")
            if not available:
                all_ok = False

        if all_ok:
            console.print("\n  All checks passed.", style="green")
        else:
            console.print("\n  Some checks failed.", style="red")

        return all_ok

    def _load_prompts(self, scenario: str, prompt_set_id: int = None) -> list:
        """Load prompt dataset for a scenario from DB or JSON files"""
        if prompt_set_id:
            try:
                repo = self.data_sink.get_repository()
                db_prompts = repo.get_prompts_by_set_and_scenario(prompt_set_id, scenario)
                if db_prompts:
                    return [{"prompt": p.prompt_text} for p in db_prompts]
                else:
                    console.print(f"      ! No prompts found in DB for set {prompt_set_id} / {scenario}, falling back to default.", style="yellow")
            except Exception as e:
                console.print(f"      ! Error loading prompts from DB: {e}", style="yellow")

        prompts_dir = Path(__file__).parent.parent / "prompts"
        prompt_file = prompts_dir / f"{scenario}.json"

        if not prompt_file.exists():
            console.print(
                f"      ! Prompt file '{prompt_file.name}' not found, falling back to simple_chat.json",
                style="yellow",
            )
            prompt_file = prompts_dir / "simple_chat.json"

        try:
            with open(prompt_file, "r") as f:
                loaded_prompts = json.load(f)
            if isinstance(loaded_prompts, list) and loaded_prompts:
                return loaded_prompts
            console.print(
                f"      ! Prompt file '{prompt_file.name}' is empty, returning minimal default",
                style="yellow",
            )
        except Exception as exc:
            console.print(
                f"      ! Prompt file '{prompt_file.name}' is invalid ({exc}), returning minimal default",
                style="yellow",
            )

        return [{"prompt": "Hello!"}]

    async def _execute_single_test(
        self, run_id, server_id, environment, scenario, model, tool_name,
        adapter_class, tool_cfg, target_url, suite_cfg, prompts, completed, total, concurrency
    ) -> int:
        self._progress["current_test"] = f"{server_id}/{scenario}/{model}/{tool_name} (c={concurrency})"

        console.print(
            f"        [{completed + 1}/{total}] "
            f"{server_id} / {scenario} / {model} / [cyan]{tool_name}[/cyan] (c={concurrency})",
            style="white",
        )

        try:
            adapter = self._create_adapter(
                tool_name,
                adapter_class,
                tool_cfg,
                target_url,
                model,
                concurrency=concurrency,
                suite_cfg=suite_cfg,
            )

            if not adapter.is_available():
                console.print(
                    f"          ~ {tool_name}: SKIPPED (not installed/available)",
                    style="yellow",
                )
            else:
                results = await adapter.run(prompts)
                result_count = 0
                for result in results:
                    result.run_id = run_id
                    result.server = server_id
                    result.environment = environment
                    result.scenario = scenario
                    result.tool = tool_name
                    self.data_sink.write_benchmark_result(result, run_id)
                    self._record_live_metrics(result, server_id)
                    result_count += 1

                console.print(
                    f"          ✓ {tool_name}: {result_count} results "
                    f"(avg TPS: {self._calc_avg_tps(results):.1f})",
                    style="green",
                )

        except Exception as e:
            error_msg = f"{tool_name} on {server_id}: {str(e)}"
            console.print(f"          ✗ {error_msg}", style="red")
            self._progress["errors"].append(error_msg)
            results = []

        if 'results' in locals() and results and any(r.error_rate and r.error_rate >= 0.9 for r in results):
            client = self.agent_clients.get(server_id)
            if client:
                console.print(f"          ! High error rate detected on {server_id}. Checking health...", style="yellow")
                is_ok = await client.check_ollama_health(target_url)
                if not is_ok:
                    console.print(f"          ! Service offline/crashed. Attempting to restart...", style="yellow")
                    await client.control_ollama("restart")
                    await asyncio.sleep(15)
                    await client.warmup_model(model, 1, ollama_url=target_url)
                else:
                    console.print(f"          ! Service overloaded. Applying cooldown...", style="yellow")
                    await asyncio.sleep(10)

        completed += 1
        self._progress["completed_tests"] = completed
        self._progress["percent"] = int(completed / total * 100) if total > 0 else 0
        return completed

    def run_sync(
        self,
        run_id: str,
        suite: str = "all",
        server: str = "all",
        environment: str = "lan",
        notes: str = "",
        tags: list = None,
    ):
        """Run benchmark synchronously (for CLI)"""
        asyncio.run(
            self.run_async(
                run_id=run_id,
                suite=suite,
                server=server,
                environment=environment,
                notes=notes,
                tags=tags or [],
            )
        )

    async def run_async(
        self,
        run_id: str,
        suite: str = "all",
        target_servers: list[str] = None,
        environment: str = "lan",
        notes: str = "",
        tags: list[str] = None,
        resume_from_db: bool = False,
        prompt_set_id: int = None,
    ):
        """Run benchmark asynchronously"""
        async with self._run_lock:
            self._cancel_requested = False
            self._current_run_id = run_id
            self._live_metrics = {
                "last_tps": None,
                "last_ttft_ms": None,
                "current_server": None,
            }
            self._progress["status"] = "running"
            self._progress["run_id"] = run_id
            self._progress["current_phase"] = ""
            self._progress["current_test"] = ""
            self._progress["completed_tests"] = 0
            self._progress["total_tests"] = 0
            self._progress["percent"] = 0
            self._progress["started_at"] = get_local_time().isoformat()
            self._progress["errors"] = []
            self._progress["elapsed_seconds"] = 0
            self._progress["estimated_remaining_seconds"] = None
            self._progress["live_metrics"] = self._live_metrics.copy()

            repo = self.data_sink.get_repository()
            
            prompt_set_name = "Default (System)"
            if prompt_set_id:
                pset = repo.get_prompt_set_by_id(prompt_set_id)
                if pset:
                    prompt_set_name = pset.name
                    
            if not resume_from_db:
                repo.create_run(
                    run_id=run_id,
                    suite=suite,
                    environment=environment,
                    model=",".join(self.config.models),
                    config_snapshot={
                        "suite": suite,
                        "servers": target_servers,
                        "environment": environment,
                        "prompt_set": prompt_set_name,
                        "prompt_set_id": prompt_set_id,
                    },
                    notes=notes,
                    tags=tags or [],
                )

            collector = None

            try:
                repo.update_run_status(run_id, "running")

                self._progress["current_phase"] = "Preflight"
                console.print("  Phase 0: Preflight checks", style="purple")
                self._check_cancelled()

                runtime_servers = dict(self.config.servers)
                runtime_agent_clients = dict(self.agent_clients)
                
                # Default to all if empty
                if not target_servers:
                    servers_to_test = list(self.config.servers.keys())
                else:
                    # Filter valid ones
                    servers_to_test = [s for s in target_servers if s in runtime_servers]
                    if not servers_to_test:
                        raise ValueError("No valid target servers selected")

                suites_to_run = []
                if suite == "all":
                    for suite_name, suite_cfg in self.config.benchmark.test_suites.items():
                        if suite_cfg.enabled:
                            suites_to_run.append((suite_name, suite_cfg))
                else:
                    suite_cfg = self.config.benchmark.test_suites.get(suite)
                    if suite_cfg and suite_cfg.enabled:
                        suites_to_run.append((suite, suite_cfg))

                if not suites_to_run:
                    raise ValueError(f"No enabled test suite found for '{suite}'")

                enabled_tools = self._get_enabled_tools()
                if not enabled_tools:
                    raise ValueError("No benchmark tools are enabled")

                original_servers = self.config.servers
                original_clients = self.agent_clients
                self.config.servers = runtime_servers
                self.agent_clients = runtime_agent_clients
                try:
                    resolved_targets = await self._validate_run_targets(
                        servers_to_test,
                        environment,
                        enabled_tools,
                    )
                finally:
                    self.config.servers = original_servers
                    self.agent_clients = original_clients

                enabled_tools, unavailable_tools = self._split_available_tools(
                    enabled_tools,
                    next(iter(resolved_targets.values())),
                    self.config.models[0],
                )
                if unavailable_tools:
                    warning_msg = (
                        f"Skipping unavailable tools: {', '.join(unavailable_tools)}"
                    )
                    console.print(f"    ! {warning_msg}", style="yellow")
                    self._progress["errors"].append(warning_msg)
                if not enabled_tools:
                    raise RuntimeError("No benchmark tools are available after preflight")

                console.print(
                    f"    Enabled tools: {[t[0] for t in enabled_tools]}",
                    style="cyan",
                )
                console.print(f"    Servers: {servers_to_test}", style="cyan")
                console.print(f"    Models: {self.config.models}", style="cyan")

                self._progress["current_phase"] = "Warmup"
                console.print("\n  Phase 1: Warming up models", style="purple")

                for server_id in servers_to_test:
                    self._check_cancelled()
                    client = runtime_agent_clients[server_id]
                    target_url = resolved_targets[server_id]

                    for model in self.config.models:
                        self._check_cancelled()
                        console.print(
                            f"    Warming up {model} on {server_id} ({target_url})..."
                        )
                        warm_ok = await client.warmup_model(
                            model,
                            self.config.benchmark.warmup_requests,
                            ollama_url=target_url,
                        )
                        if not warm_ok:
                            raise RuntimeError(
                                f"Warmup failed for model '{model}' on '{server_id}'"
                            )
                        console.print(
                            f"    ✓ {model} on {server_id} ready",
                            style="green",
                        )

                self._progress["current_phase"] = "Monitoring"
                console.print("\n  Phase 2: Starting hardware monitors", style="purple")

                selected_clients = {
                    server_id: runtime_agent_clients[server_id]
                    for server_id in servers_to_test
                }
                collector = MetricCollector(
                    agent_clients=selected_clients,
                    data_sink=self.data_sink,
                    run_id=run_id,
                    gpu_interval=self.config.metrics.gpu_poll_interval_seconds,
                )
                collector.start()
                console.print("    ✓ Hardware monitors started", style="green")

                self._progress["current_phase"] = "Benchmarking"
                console.print("\n  Phase 3: Running benchmarks", style="purple")

                total = 0
                suite_tools_map = {}
                for suite_name, suite_cfg in suites_to_run:
                    scenarios = suite_cfg.scenarios if suite_cfg.scenarios else ["simple_chat"]
                    suite_tools = self._get_enabled_tools(suite_name)
                    suite_tools_map[suite_name] = suite_tools
                    concurrencies = suite_cfg.concurrency_levels if suite_cfg.concurrency_levels else [suite_cfg.concurrency]
                    total += (
                        len(scenarios)
                        * len(servers_to_test)
                        * len(self.config.models)
                        * len(suite_tools)
                        * len(concurrencies)
                    )

                self._progress["total_tests"] = total
                console.print(f"    Total tests: {total}", style="cyan")

                completed = 0
                
                existing_results = []
                if resume_from_db:
                    existing_results = await repo.get_results_by_run(run_id)
                
                for suite_name, suite_cfg in suites_to_run:
                    self._check_cancelled()
                    scenarios = suite_cfg.scenarios if suite_cfg.scenarios else ["simple_chat"]
                    console.print(f"\n    Suite: {suite_name}", style="yellow")

                    for scenario in scenarios:
                        self._check_cancelled()
                        prompts = self._load_prompts(scenario, prompt_set_id)
                        console.print(
                            f"      Scenario: {scenario} ({len(prompts)} unique prompts loaded)",
                            style="white",
                        )

                        for model in self.config.models:
                            self._check_cancelled()
                            for server_id in servers_to_test:
                                self._check_cancelled()
                                target_url = resolved_targets[server_id]

                                suite_tools = suite_tools_map[suite_name]
                                concurrencies = suite_cfg.concurrency_levels if suite_cfg.concurrency_levels else [suite_cfg.concurrency]
                                
                                for tool_name, adapter_class, tool_cfg in suite_tools:
                                    for concurrency in concurrencies:
                                        self._check_cancelled()
                                        
                                        # Ensure prompts list is at least as long as concurrency to properly test scaling
                                        # and at least as long as requests_per_scenario for volume
                                        current_prompts = prompts
                                        num_requests = suite_cfg.requests_per_scenario
                                        min_needed = max(num_requests, concurrency)
                                        if len(current_prompts) < min_needed:
                                            current_prompts = (current_prompts * (min_needed // len(current_prompts) + 1))[:min_needed]
                                        elif num_requests > 0 and len(current_prompts) > num_requests and len(current_prompts) > concurrency:
                                            # Slice but don't go below concurrency
                                            current_prompts = current_prompts[:max(num_requests, concurrency)]

                                        if resume_from_db:
                                            has_result = any(
                                                r.scenario == scenario and r.tool == tool_name and r.server == server_id and r.model == model and r.concurrency == concurrency
                                                for r in existing_results
                                            )
                                            if has_result:
                                                completed += 1
                                                self._progress["completed_tests"] = completed
                                                self._progress["percent"] = int(completed / total * 100) if total > 0 else 0
                                                console.print(f"        [{completed}/{total}] {server_id} / {scenario} / {model} / [cyan]{tool_name}[/cyan] (c={concurrency}) (Resumed)", style="dim")
                                                continue
                                                
                                        completed = await self._execute_single_test(
                                            run_id=run_id,
                                            server_id=server_id,
                                            environment=environment,
                                            scenario=scenario,
                                            model=model,
                                            tool_name=tool_name,
                                            adapter_class=adapter_class,
                                            tool_cfg=tool_cfg,
                                            target_url=target_url,
                                            suite_cfg=suite_cfg,
                                            prompts=current_prompts,
                                            completed=completed,
                                            total=total,
                                            concurrency=concurrency,
                                        )

                                    if self.config.benchmark.cooldown_seconds > 0:
                                        await asyncio.sleep(self.config.benchmark.cooldown_seconds)

                self._progress["current_phase"] = "Finalizing"
                console.print("\n  Phase 4: Stopping monitors", style="purple")
                if collector:
                    collector.stop()
                    collector = None
                console.print("    ✓ Hardware monitors stopped", style="green")

                console.print("\n  Phase 5: Generating comparisons", style="purple")
                self._generate_comparisons(run_id)
                console.print("    ✓ Comparisons generated", style="green")

                repo.update_run_status(
                    run_id,
                    "completed",
                    completed_tests=completed,
                    total_tests=total,
                    failed_tests=len(self._progress["errors"]),
                )
                self._progress["status"] = "completed"
                self._progress["current_phase"] = "Done"

                console.print("\n" + "=" * 50, style="green")
                console.print("  ✓ Benchmark completed successfully!", style="green bold")
                console.print("=" * 50, style="green")
                console.print(f"  Run ID: {run_id}", style="purple")
                console.print(f"  Total tests: {completed}", style="white")
                console.print(
                    f"  Errors: {len(self._progress['errors'])}",
                    style="yellow" if self._progress["errors"] else "white",
                )
                console.print(
                    f"  Results: http://localhost:{self.config.app.port}/history/{run_id}",
                    style="cyan",
                )

            except asyncio.CancelledError:
                console.print("\n  ! Benchmark stop requested, finalizing partial results", style="yellow")
                if collector:
                    collector.stop()
                    collector = None
                self._progress["status"] = "stopped"
                self._progress["current_phase"] = "Stopped"
                repo.update_run_status(
                    run_id,
                    "cancelled",
                    completed_tests=self._progress["completed_tests"],
                    total_tests=self._progress["total_tests"],
                    failed_tests=len(self._progress["errors"]),
                )
            except Exception as e:
                console.print(f"\n  ✗ Benchmark failed: {e}", style="red bold")
                import traceback

                traceback.print_exc()
                if collector:
                    collector.stop()
                repo.update_run_status(run_id, "failed")
                self._progress["status"] = "failed"
                self._progress["errors"].append(str(e))
            finally:
                self._cancel_requested = False
                self._current_run_id = None

    def _calc_avg_tps(self, results: list) -> float:
        """Calculate average TPS from results"""
        tps_values = [r.tps for r in results if r.tps and r.tps > 0]
        if tps_values:
            return sum(tps_values) / len(tps_values)
        return 0.0

    def _generate_comparisons(self, run_id: str):
        """Generate server comparison records"""
        repo = self.data_sink.get_repository()

        s1_data = repo.get_aggregated_results(run_id, "server1")
        s2_data = repo.get_aggregated_results(run_id, "server2")

        if s1_data["result_count"] == 0 or s2_data["result_count"] == 0:
            console.print("    ⚠ Not enough data for comparison", style="yellow")
            return

        def calc_delta(s1_val, s2_val, lower_is_better=False):
            if s1_val and s2_val and s1_val != 0:
                delta = ((s2_val - s1_val) / s1_val) * 100
                if lower_is_better:
                    delta = -delta
                return round(delta, 2)
            return None

        comparison_data = {
            "s1_ttft_ms": s1_data.get("avg_ttft_ms"),
            "s2_ttft_ms": s2_data.get("avg_ttft_ms"),
            "delta_ttft_pct": calc_delta(
                s1_data.get("avg_ttft_ms"),
                s2_data.get("avg_ttft_ms"),
                lower_is_better=True,
            ),
            "s1_tps": s1_data.get("avg_tps"),
            "s2_tps": s2_data.get("avg_tps"),
            "delta_tps_pct": calc_delta(
                s1_data.get("avg_tps"),
                s2_data.get("avg_tps"),
            ),
            "s1_rps": s1_data.get("avg_rps"),
            "s2_rps": s2_data.get("avg_rps"),
            "delta_rps_pct": calc_delta(
                s1_data.get("avg_rps"),
                s2_data.get("avg_rps"),
            ),
            "s1_p99_ms": s1_data.get("avg_p99_ms"),
            "s2_p99_ms": s2_data.get("avg_p99_ms"),
            "delta_p99_pct": calc_delta(
                s1_data.get("avg_p99_ms"),
                s2_data.get("avg_p99_ms"),
                lower_is_better=True,
            ),
        }

        self.data_sink.write_comparison(run_id, **comparison_data)
        
        # Print summary
        console.print(f"    Server1 avg TPS: {s1_data.get('avg_tps', 0):.2f}", style="white")
        console.print(f"    Server2 avg TPS: {s2_data.get('avg_tps', 0):.2f}", style="white")
        if comparison_data.get("delta_tps_pct"):
            delta = comparison_data["delta_tps_pct"]
            color = "green" if delta > 0 else "red"
            console.print(f"    Delta TPS: {delta:+.2f}%", style=color)
