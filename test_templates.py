import asyncio
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from src.config import load_config
from src.i18n import translate

templates = Jinja2Templates(directory="templates")
config = load_config()

scope = {
    "type": "http",
    "method": "GET",
    "url": "http://testserver/",
    "headers": [],
    "state": {"lang": "en"}
}
request = Request(scope)

class DummyRun:
    run_id = 'abc'
    started_at = None
    duration_seconds = 10
    status = 'completed'
    suite = 'suite'
    environment = 'env'
    model = 'model'
    completed_tests = 1
    total_tests = 1
    notes = ''
    tags = []

ctx = {
    "request": request,
    "t": lambda k, **kw: translate("en", k, **kw),
    "config": config,
    "run": DummyRun(),
    "summary": {'server1': {}, 'server2': {}},
    "results": [],
    "comparisons": [],
    "comparison_chart": {},
    "timeline_chart": {},
    "trend": [],
    "recent_runs": [],
    "report_data": {
        "metadata": {"servers": [], "tools": [], "scenarios": [], "total_requests": 0},
        "breakdown": {}
    },
    "chart_data": {
        "concurrencies": [1,2],
        "ttft": {"server1": {"p50": [1,2]}, "server2": {"p50": [1,2]}},
        "itl": {"server1": {"p50": [1,2]}, "server2": {"p50": [1,2]}},
        "tps": {"server1": {"p50": [1,2]}, "server2": {"p50": [1,2]}},
        "latency": {"server1": {"p50": [1,2]}, "server2": {"p50": [1,2]}}
    },
}

import os
for f in os.listdir("templates"):
    if f.endswith(".html"):
        try:
            templates.env.get_template(f)
            print(f"{f} OK")
        except Exception as e:
            import traceback
            traceback.print_exc()
            break
            print(f"ERROR in {f}: {e}")
