/**
 * aiDaptive Benchmark Suite - Frontend JavaScript
 */

let discoveredServerConfig = null;

function t(key, vars = {}) {
    const catalog = window.APP_I18N || {};
    let text = catalog[key] || key;
    Object.entries(vars).forEach(([name, value]) => {
        text = text.replaceAll(`{${name}}`, String(value));
    });
    return text;
}

// --------------------------------------------------
// Clock
// --------------------------------------------------
function updateClock() {
    const el = document.getElementById("clock");
    if (el) {
        const now = new Date();
        el.textContent = now.toLocaleTimeString(window.APP_LANG || undefined);
    }
}
setInterval(updateClock, 1000);
updateClock();

// --------------------------------------------------
// Status polling
// --------------------------------------------------
async function pollStatus() {
    try {
        const resp = await fetch("/api/status");
        const data = await resp.json();

        // Server statuses
        if (data.servers) {
            data.servers.forEach(s => {
                const dot = document.getElementById(`status-${s.server_id}`);
                if (dot) {
                    dot.className = s.ollama_online
                        ? "status-dot status-online"
                        : "status-dot status-offline";
                }
            });
        }

        // Infrastructure
        const pgDot = document.getElementById("pg-status");
        if (pgDot) {
            pgDot.className = data.postgres
                ? "w-2 h-2 rounded-full bg-green-500"
                : "w-2 h-2 rounded-full bg-red-500";
        }

        const influxDot = document.getElementById("influx-status");
        if (influxDot) {
            influxDot.className = data.influxdb
                ? "w-2 h-2 rounded-full bg-green-500"
                : "w-2 h-2 rounded-full bg-red-500";
        }

    } catch (e) {
        console.error(t("js.status_poll_error"), e);
    }
}

setInterval(pollStatus, 10000);
pollStatus();

// --------------------------------------------------
// Tool filtering by suite
// --------------------------------------------------
document.addEventListener("DOMContentLoaded", function() {
    const suiteSelect = document.getElementById("bench-suite");
    if (suiteSelect) {
        suiteSelect.addEventListener("change", function() {
            const selectedSuite = this.value;
            const toolItems = document.querySelectorAll(".tool-item");

            toolItems.forEach(item => {
                const isEnabledGlobal = item.dataset.enabled === "true";
                const supportedSuitesStr = item.dataset.suites;
                
                let isApplicable = false;
                if (!isEnabledGlobal) {
                    isApplicable = false;
                } else if (!supportedSuitesStr || selectedSuite === "all") {
                    isApplicable = true;
                } else {
                    const supportedSuites = supportedSuitesStr.split(",");
                    isApplicable = supportedSuites.includes(selectedSuite);
                }

                if (isApplicable) {
                    item.classList.remove("opacity-40", "grayscale", "border-slate-200", "bg-slate-50", "text-slate-400");
                    item.classList.add("border-violet-100/80", "bg-violet-50", "text-violet-700");
                    const statusEl = item.querySelector(".tool-status");
                    if (statusEl) statusEl.classList.replace("text-slate-400", "text-green-600");
                } else {
                    item.classList.remove("border-violet-100/80", "bg-violet-50", "text-violet-700");
                    item.classList.add("opacity-40", "grayscale", "border-slate-200", "bg-slate-50", "text-slate-400");
                    const statusEl = item.querySelector(".tool-status");
                    if (statusEl) statusEl.classList.replace("text-green-600", "text-slate-400");
                }
            });
        });
        
        // Trigger once on load
        suiteSelect.dispatchEvent(new Event("change"));
    }

    // --------------------------------------------------
    // Global progress polling — works on EVERY page
    // --------------------------------------------------
    (function startGlobalProgressPoll() {
        let _globalPollActive = false;

        function formatDuration(seconds) {
            if (seconds === null || seconds === undefined) return "--:--";
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = seconds % 60;
            return h > 0
                ? `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
                : `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        }

        function updateGlobalBanner(data) {
            const banner = document.getElementById("global-progress-banner");
            if (!banner) return;

            const isActive = (data.status === "running" || data.status === "stopping");

            if (isActive) {
                banner.style.display = "block";
                setText("gp-runid", data.run_id || "");
                setText("gp-phase", data.current_phase || "");
                setText("gp-percent-label", `${data.percent || 0}%`);
                setText("gp-current-test", data.current_test || "");
                setText("gp-elapsed", formatDuration(data.elapsed_seconds));

                const fill = document.getElementById("gp-fill");
                if (fill) fill.style.width = `${data.percent || 0}%`;

                if (data.estimated_remaining_seconds != null) {
                    const etaDate = new Date(Date.now() + data.estimated_remaining_seconds * 1000);
                    setText("gp-eta", etaDate.toLocaleTimeString(window.APP_LANG || undefined));
                } else {
                    setText("gp-eta", "--:--");
                }

                // Also update the page-specific progress-container if it exists
                const pageProgress = document.getElementById("progress-container");
                if (pageProgress) {
                    pageProgress.style.display = "block";
                    const progressFill = document.getElementById("progress-fill");
                    if (progressFill) progressFill.style.width = `${data.percent || 0}%`;
                    setText("progress-text", `${data.completed_tests || 0} / ${data.total_tests || 0}`);
                    setText("progress-phase", data.current_phase || "");
                    setText("progress-runid", data.run_id || "--");
                    setText("progress-status", data.status || "Running");
                    setText("progress-current-test", data.current_test || "--");
                    setText("progress-percent", data.percent || "0");
                    setText("progress-elapsed", formatDuration(data.elapsed_seconds));
                    setText("progress-remaining", formatDuration(data.estimated_remaining_seconds));

                    if (data.estimated_remaining_seconds != null) {
                        const etaDate = new Date(Date.now() + data.estimated_remaining_seconds * 1000);
                        setText("progress-eta", etaDate.toLocaleTimeString(window.APP_LANG || undefined));
                    } else {
                        setText("progress-eta", "--:--");
                    }

                    const progressExtra = document.getElementById("progress-extra");
                    if (progressExtra) {
                        const live = data.live_metrics || {};
                        if (live.current_server || live.last_tps || live.last_ttft_ms) {
                            progressExtra.textContent =
                                t("js.live_metrics", {
                                    server: live.current_server || "--",
                                    tps: live.last_tps ?? "--",
                                    ttft: live.last_ttft_ms ?? "--",
                                });
                        } else {
                            progressExtra.textContent = t("js.waiting_live_metrics");
                        }
                    }
                }

                // Update inline history progress bars if they exist
                if (data.run_id) {
                    const rowBar = document.querySelector(`.run-progress-bar[data-run-id="${data.run_id}"]`);
                    if (rowBar) rowBar.style.width = `${data.percent || 0}%`;
                    
                    const rowText = document.querySelector(`.run-progress-text[data-run-id="${data.run_id}"]`);
                    if (rowText) rowText.textContent = `${data.completed_tests || 0} / ${data.total_tests || 0}`;
                    
                    const rowPct = document.querySelector(`.run-progress-pct[data-run-id="${data.run_id}"]`);
                    if (rowPct) rowPct.textContent = `${data.percent || 0}%`;
                }

                // Disable start button if present
                const btn = document.getElementById("btn-start-benchmark");
                if (btn) {
                    btn.disabled = true;
                    btn.textContent = t("js.starting");
                }
            } else {
                // Hide global banner when idle/completed/failed
                if (banner.style.display !== "none" && _globalPollActive) {
                    // Was running, now done — show notification
                    if (data.status === "completed") {
                        showNotification(t("js.benchmark_completed"));
                    } else if (data.status === "stopped") {
                        showNotification(t("js.benchmark_stopped"), "error");
                    } else if (data.status === "failed") {
                        showNotification(t("js.benchmark_failed"), "error");
                    }

                    // Hide page-specific container too
                    const pageProgress = document.getElementById("progress-container");
                    if (pageProgress) pageProgress.style.display = "none";

                    // Re-enable start button
                    const btn = document.getElementById("btn-start-benchmark");
                    if (btn) {
                        btn.disabled = false;
                        btn.textContent = t("benchmark.start_button");
                    }
                }
                banner.style.display = "none";
                _globalPollActive = false;
            }

            if (isActive) _globalPollActive = true;
        }

        // Poll every 3 seconds on ALL pages
        async function pollGlobal() {
            try {
                const resp = await fetch("/api/benchmark/progress");
                const data = await resp.json();
                updateGlobalBanner(data);
            } catch (e) {
                // silent — server might be restarting
            }
        }

        // Initial check + interval
        pollGlobal();
        setInterval(pollGlobal, 3000);
    })();
});

// --------------------------------------------------
// Benchmark control
// --------------------------------------------------
async function startBenchmark() {
    const suite = document.getElementById("bench-suite")?.value || "all";
    const server = document.getElementById("bench-server")?.value || "all";
    const env = document.getElementById("bench-env")?.value || "lan";
    const notes = document.getElementById("bench-notes")?.value || "";
    
    // Advanced options & Tags
    const tagsInput = document.getElementById("bench-tags")?.value || "";
    const tags = tagsInput.split(',').map(t => t.trim()).filter(t => t.length > 0);
    
    const advancedOptions = {
        warmup_requests: parseInt(document.getElementById("bench-warmup")?.value) || 3,
        repeat_count: parseInt(document.getElementById("bench-repeat")?.value) || 1,
        concurrency_levels: document.getElementById("bench-concurrency")?.value || "1, 5, 10, 25, 50",
        request_timeout_seconds: parseInt(document.getElementById("bench-timeout")?.value) || 120,
        cooldown_seconds: parseInt(document.getElementById("bench-cooldown")?.value) || 10
    };

    const btn = document.getElementById("btn-start-benchmark");
    const stopBtn = document.getElementById("btn-stop-benchmark");
    if (btn) {
        btn.disabled = true;
        btn.textContent = t("js.starting");
    }
    if (stopBtn) {
        stopBtn.disabled = false;
    }

    try {
        const payload = { suite, server, environment: env, notes, tags, advanced_options: advancedOptions };
        if (server === "custom") {
            if (!discoveredServerConfig) {
                showNotification(t("js.discover_first"), "error");
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = t("benchmark.start_button");
                }
                return;
            }
            payload.custom_server = discoveredServerConfig;
        }

        const resp = await fetch("/api/benchmark/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const data = await resp.json();

        if (data.run_id) {
            showNotification(data.message || `Benchmark started: ${data.run_id}`);
            pollProgress(data.run_id);
        } else if (data.error) {
            showNotification(data.error, "error");
        }

    } catch (e) {
        showNotification(t("js.failed_to_start"), "error");
    }

    if (btn) {
        btn.disabled = false;
        btn.textContent = t("benchmark.start_button");
    }
}

async function discoverServerConfig() {
    const ip = document.getElementById("discover-server-ip")?.value?.trim() || "";
    const btn = document.getElementById("btn-discover-server");

    if (!ip) {
        showNotification(t("js.enter_server_ip"), "error");
        return;
    }

    if (btn) {
        btn.disabled = true;
        btn.textContent = t("js.discovering");
    }

    try {
        const resp = await fetch("/api/server/discover", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ip }),
        });
        const data = await resp.json();

        if (!resp.ok) {
            throw new Error(data.error || t("js.discovery_failed"));
        }

        discoveredServerConfig = data.server;
        renderDiscoveredServer(data.server);

        const serverSelect = document.getElementById("bench-server");
        if (serverSelect) {
            serverSelect.value = "custom";
        }

        showNotification(t("js.discovered_server_toast", { name: data.server.name }));
    } catch (e) {
        showNotification(e.message || t("js.failed_to_discover"), "error");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = t("benchmark.discover_button");
        }
    }
}

function renderDiscoveredServer(server) {
    const result = document.getElementById("discover-server-result");
    const errors = document.getElementById("discover-server-errors");

    if (result) {
        result.classList.remove("hidden");
    }

    setText("discover-server-name", server.name || `${t("benchmark.discovered_server")} (${server.ip})`);
    setText("discover-server-sources", t("js.sources_label", { sources: (server.discovery_sources || []).join(", ") || "--" }));
    setText("discover-agent-url", server.agent_url || "--");
    setText("discover-ollama-url", server.ollama_url || "--");
    setText("discover-gpu-name", server.gpu_name || "--");
    setText("discover-vram", server.vram_total_gb ? `${server.vram_total_gb} GB` : "--");
    setText("discover-cpu-model", server.cpu_model || "--");
    setText("discover-cpu-cores", server.cpu_cores || "--");
    setText("discover-ram", server.ram_total_gb ? `${server.ram_total_gb} GB` : "--");
    setText("discover-models", (server.models_available || []).join(", ") || "--");

    if (errors) {
        const messages = server.errors || [];
        if (messages.length > 0) {
            errors.classList.remove("hidden");
            errors.textContent = messages.join(" | ");
        } else {
            errors.classList.add("hidden");
            errors.textContent = "";
        }
    }
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) {
        el.textContent = value;
    }
}

async function pollProgress(runId) {
    // The global progress poll (in DOMContentLoaded) handles all UI updates.
    // This function only handles the redirect after completion.
    const interval = setInterval(async () => {
        try {
            const resp = await fetch("/api/benchmark/progress");
            const data = await resp.json();

            if (data.status === "completed" || data.status === "failed" || data.status === "stopped") {
                clearInterval(interval);

                if (data.status === "completed" || data.status === "stopped") {
                    setTimeout(() => {
                        window.location.href = `/history/${data.run_id}`;
                    }, 1500);
                }
            }
        } catch (e) {
            // handled by global poll
        }
    }, 3000);
}

async function stopBenchmark() {
    const stopBtn = document.getElementById("btn-stop-benchmark");
    if (stopBtn) {
        stopBtn.disabled = true;
        stopBtn.textContent = t("js.stopping");
    }

    try {
        const resp = await fetch("/api/benchmark/stop", { method: "POST" });
        const data = await resp.json();
        if (!resp.ok) {
            throw new Error(data.message || data.error || t("js.stop_failed"));
        }
        showNotification(data.message || t("js.stop_requested"));
    } catch (e) {
        showNotification(e.message || t("js.stop_failed"), "error");
        if (stopBtn) {
            stopBtn.disabled = false;
            stopBtn.textContent = t("benchmark.stop_button");
        }
    }
}

// --------------------------------------------------
// Delete run
// --------------------------------------------------
async function deleteRun(runId) {
    if (!confirm(t("js.delete_confirm", { run_id: runId }))) {
        return;
    }

    try {
        const resp = await fetch(`/api/runs/${runId}`, { method: "DELETE" });
        if (resp.ok) {
            showNotification(t("js.deleted", { run_id: runId }));
            const row = document.getElementById(`row-${runId}`);
            if (row) {
                row.style.opacity = "0";
                setTimeout(() => row.remove(), 300);
            }
        }
    } catch (e) {
        showNotification(t("js.delete_failed"), "error");
    }
}

// --------------------------------------------------
// Export CSV
// --------------------------------------------------
function exportCSV(runId) {
    window.location.href = `/api/runs/${runId}/export`;
}

// --------------------------------------------------
// Notifications
// --------------------------------------------------
function showNotification(message, type = "success") {
    const container = document.getElementById("notifications") || document.body;

    const div = document.createElement("div");
    div.className = `fixed top-4 right-4 z-50 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-300 ${
        type === "error"
            ? "bg-white/95 text-red-600 border border-red-200 shadow-xl shadow-red-100"
            : "bg-white/95 text-violet-700 border border-violet-200 shadow-xl shadow-violet-100"
    }`;
    div.textContent = message;
    div.style.opacity = "0";
    div.style.transform = "translateY(-10px)";

    container.appendChild(div);

    requestAnimationFrame(() => {
        div.style.opacity = "1";
        div.style.transform = "translateY(0)";
    });

    setTimeout(() => {
        div.style.opacity = "0";
        div.style.transform = "translateY(-10px)";
        setTimeout(() => div.remove(), 300);
    }, 4000);
}

// --------------------------------------------------
// Comparison page - run selector
// --------------------------------------------------
function updateComparison() {
    const run1 = document.getElementById("compare-run1")?.value || "";
    const run2 = document.getElementById("compare-run2")?.value || "";

    if (run1 || run2) {
        window.location.href = `/comparison?run1=${run1}&run2=${run2}`;
    }
}

// --------------------------------------------------
// Tab switching
// --------------------------------------------------
function switchTab(tabName) {
    document.querySelectorAll("[data-tab-content]").forEach(el => {
        el.style.display = el.dataset.tabContent === tabName ? "block" : "none";
    });

    document.querySelectorAll("[data-tab-btn]").forEach(el => {
        if (el.dataset.tabBtn === tabName) {
            el.classList.add("text-purple-400", "border-purple-400");
            el.classList.remove("text-gray-500", "border-transparent");
        } else {
            el.classList.remove("text-purple-400", "border-purple-400");
            el.classList.add("text-gray-500", "border-transparent");
        }
    });
}
