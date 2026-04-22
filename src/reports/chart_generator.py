"""Generate comparison charts using matplotlib and plotly"""

from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np


# Color palette
COLOR_SERVER1 = "#6b7280"
COLOR_SERVER2 = "#a855f7"
COLOR_BG = "#ffffff"
COLOR_TEXT = "#0f172a"
COLOR_GRID = "#e2e8f0"


def setup_style():
    plt.rcParams.update({
        "figure.facecolor": COLOR_BG,
        "axes.facecolor": COLOR_BG,
        "axes.edgecolor": COLOR_GRID,
        "axes.labelcolor": COLOR_TEXT,
        "text.color": COLOR_TEXT,
        "xtick.color": COLOR_TEXT,
        "ytick.color": COLOR_TEXT,
        "grid.color": COLOR_GRID,
        "font.family": "sans-serif",
        "font.size": 11,
    })


def generate_comparison_bar_chart(
    metrics: dict,
    output_path: str,
    title: str = "Server Comparison",
):
    """
    Generate side-by-side bar chart.

    metrics format:
    {
        "TTFT (ms)": {"server1": 245, "server2": 198},
        "TPS": {"server1": 42, "server2": 51},
        ...
    }
    """
    setup_style()

    labels = list(metrics.keys())
    s1_values = [metrics[l].get("server1", 0) or 0 for l in labels]
    s2_values = [metrics[l].get("server2", 0) or 0 for l in labels]

    x = np.arange(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))
    bars1 = ax.bar(
        x - width / 2, s1_values, width,
        label="Server 1 (Native)",
        color=COLOR_SERVER1,
        edgecolor=COLOR_BG,
    )
    bars2 = ax.bar(
        x + width / 2, s2_values, width,
        label="Server 2 (+ aiDaptive)",
        color=COLOR_SERVER2,
        edgecolor=COLOR_BG,
    )

    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.legend(facecolor="#ffffff", edgecolor=COLOR_GRID)
    ax.grid(axis="y", alpha=0.3)

    # Value labels on bars
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(
            f"{height:.1f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            color=COLOR_SERVER1,
        )
    for bar in bars2:
        height = bar.get_height()
        ax.annotate(
            f"{height:.1f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            color=COLOR_SERVER2,
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def generate_radar_chart(
    metrics: dict,
    output_path: str,
    title: str = "Performance Radar",
):
    """
    Generate radar / spider chart.

    metrics format same as bar chart.
    Values should be normalized to 0-100 scale.
    """
    setup_style()

    labels = list(metrics.keys())
    s1_values = [metrics[l].get("server1", 0) or 0 for l in labels]
    s2_values = [metrics[l].get("server2", 0) or 0 for l in labels]

    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]
    s1_values += s1_values[:1]
    s2_values += s2_values[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.set_facecolor(COLOR_BG)
    fig.patch.set_facecolor(COLOR_BG)

    ax.plot(angles, s1_values, "o-", color=COLOR_SERVER1, linewidth=2, label="Server 1")
    ax.fill(angles, s1_values, alpha=0.15, color=COLOR_SERVER1)

    ax.plot(angles, s2_values, "o-", color=COLOR_SERVER2, linewidth=2, label="Server 2")
    ax.fill(angles, s2_values, alpha=0.15, color=COLOR_SERVER2)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=10)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=30, color=COLOR_TEXT)
    ax.legend(loc="upper right", facecolor="#ffffff", edgecolor=COLOR_GRID)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def generate_concurrency_line_chart(
    data: dict,
    output_path: str,
    metric_name: str = "TPS",
    title: str = "Performance vs Concurrency",
):
    """
    Generate line chart showing metric vs concurrency level.

    data format:
    {
        "server1": {1: 42, 5: 40, 10: 38, 25: 35, 50: 30},
        "server2": {1: 51, 5: 49, 10: 47, 25: 45, 50: 42},
    }
    """
    setup_style()

    fig, ax = plt.subplots(figsize=(10, 6))

    for server_key, color, label in [
        ("server1", COLOR_SERVER1, "Server 1 (Native)"),
        ("server2", COLOR_SERVER2, "Server 2 (+ aiDaptive)"),
    ]:
        if server_key in data:
            x = sorted(data[server_key].keys())
            y = [data[server_key][k] for k in x]
            ax.plot(x, y, "o-", color=color, linewidth=2, markersize=6, label=label)

    ax.set_xlabel("Concurrent Users")
    ax.set_ylabel(metric_name)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
    ax.legend(facecolor="#ffffff", edgecolor=COLOR_GRID)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

from datetime import datetime

def generate_timeline_chart(
    data: dict,
    output_path: str,
    metric_key: str,
    title: str,
    ylabel: str,
):
    """
    Generate timeline chart for hardware monitoring.
    
    data format:
    {
        "timestamps": ["2023-10-27T10:00:00", ...],
        "server_ip_1": {
            "gpu_util_pct": [10, 20, ...],
            "cpu_pct": [5, 10, ...],
            ...
        },
        ...
    }
    """
    setup_style()

    fig, ax = plt.subplots(figsize=(12, 6))

    timestamps_str = data.get("timestamps", [])
    if not timestamps_str:
        # Generate empty chart
        ax.set_title(title + " (No Data)", fontsize=14, fontweight="bold", pad=20)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()
        return

    try:
        x = [datetime.fromisoformat(ts) if ts else None for ts in timestamps_str]
    except Exception:
        x = np.arange(len(timestamps_str))

    # Predefined colors for dynamic servers
    colors = [COLOR_SERVER1, COLOR_SERVER2, "#3b82f6", "#10b981", "#f59e0b", "#ef4444"]

    color_idx = 0
    for server_id, server_data in data.items():
        if server_id == "timestamps":
            continue
        
        y = server_data.get(metric_key, [])
        if len(y) != len(x):
            continue
            
        color = colors[color_idx % len(colors)]
        color_idx += 1
        
        ax.plot(x, y, "-", color=color, linewidth=2, label=server_id)

    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
    
    import matplotlib.dates as mdates
    if isinstance(x[0], datetime):
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        fig.autofmt_xdate()

    ax.legend(facecolor="#ffffff", edgecolor=COLOR_GRID)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

