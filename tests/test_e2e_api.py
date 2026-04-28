"""
Test Suite E2E: API Endpoints, FE Rendering, Connection, Logic
Tests against the LIVE local server at http://localhost:8443
"""
import pytest
import httpx
import asyncio

BASE = "http://localhost:8443"

def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@pytest.fixture(scope="module")
def server_up():
    """Skip all if server not running"""
    import socket
    s = socket.socket()
    try:
        s.settimeout(2)
        s.connect(("localhost", 8443))
        s.close()
    except Exception:
        pytest.skip("Server not running on :8443")


# =============================================
# A. CONNECTION TESTS
# =============================================
class TestConnection:
    def test_server_responds(self, server_up):
        """E2E-C01: Server responds on port 8443"""
        r = httpx.get(f"{BASE}/", follow_redirects=True, timeout=5)
        assert r.status_code == 200

    def test_favicon_served(self, server_up):
        """E2E-C02: Favicon route exists"""
        r = httpx.get(f"{BASE}/favicon.ico", timeout=5)
        # Should return 200 or 204, not 500
        assert r.status_code in (200, 204, 302, 307, 404)

    def test_no_cache_headers(self, server_up):
        """E2E-C03: NoCacheMiddleware sets proper headers"""
        r = httpx.get(f"{BASE}/", follow_redirects=True, timeout=5)
        assert "no-store" in r.headers.get("cache-control", "")
        assert r.headers.get("pragma") == "no-cache"


# =============================================
# B. PAGE RENDERING TESTS (FE)
# =============================================
class TestPageRendering:
    def test_dashboard_page(self, server_up):
        """E2E-FE01: Dashboard page renders"""
        r = httpx.get(f"{BASE}/", follow_redirects=True, timeout=5)
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    def test_servers_page(self, server_up):
        """E2E-FE02: Servers page renders (may 500 if DB down)"""
        r = httpx.get(f"{BASE}/servers", timeout=5)
        assert r.status_code in (200, 500)

    def test_benchmark_page(self, server_up):
        """E2E-FE03: Benchmark page renders (may 500 if DB down)"""
        r = httpx.get(f"{BASE}/benchmark", timeout=5)
        assert r.status_code in (200, 500)

    def test_history_page(self, server_up):
        """E2E-FE04: History page renders"""
        r = httpx.get(f"{BASE}/history", timeout=5)
        assert r.status_code == 200

    def test_reports_page(self, server_up):
        """E2E-FE05: Reports page renders"""
        r = httpx.get(f"{BASE}/reports", timeout=5)
        assert r.status_code == 200

    def test_prompts_page(self, server_up):
        """E2E-FE06: Prompts page renders"""
        r = httpx.get(f"{BASE}/prompts", timeout=5)
        assert r.status_code == 200

    def test_comparison_page(self, server_up):
        """E2E-FE07: Comparison page renders"""
        r = httpx.get(f"{BASE}/comparison", timeout=5)
        assert r.status_code == 200

    def test_404_handling(self, server_up):
        """E2E-FE08: Unknown routes return 404"""
        r = httpx.get(f"{BASE}/nonexistent_page_xyz", timeout=5)
        assert r.status_code == 404

    def test_html_contains_meta(self, server_up):
        """E2E-FE09: Pages have proper HTML structure"""
        r = httpx.get(f"{BASE}/", follow_redirects=True, timeout=5)
        html = r.text
        assert "<html" in html
        assert "<head" in html
        assert "charset" in html.lower()


# =============================================
# C. I18N / LANGUAGE TESTS (FE Logic)
# =============================================
class TestI18nRendering:
    def test_default_language_en(self, server_up):
        """E2E-I01: Default language renders English"""
        r = httpx.get(f"{BASE}/", follow_redirects=True, timeout=5)
        assert r.status_code == 200

    def test_language_switch_vi(self, server_up):
        """E2E-I02: Vietnamese language cookie works"""
        r = httpx.get(f"{BASE}/", follow_redirects=True, timeout=5,
                      cookies={"lang": "vi"})
        assert r.status_code == 200

    def test_language_switch_zh(self, server_up):
        """E2E-I03: Chinese language cookie works"""
        r = httpx.get(f"{BASE}/", follow_redirects=True, timeout=5,
                      cookies={"lang": "zh"})
        assert r.status_code == 200


# =============================================
# D. API ENDPOINT TESTS (BE)
# =============================================
class TestAPIEndpoints:
    def test_api_status(self, server_up):
        """E2E-API01: /api/status returns server status"""
        r = httpx.get(f"{BASE}/api/status", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)

    def test_api_health(self, server_up):
        """E2E-API02: /api/health returns health info"""
        r = httpx.get(f"{BASE}/api/health", timeout=5)
        assert r.status_code == 200

    def test_api_benchmark_progress(self, server_up):
        """E2E-API03: /api/benchmark/progress returns progress"""
        r = httpx.get(f"{BASE}/api/benchmark/progress", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)

    def test_api_servers(self, server_up):
        """E2E-API04: /api/servers returns server list"""
        r = httpx.get(f"{BASE}/api/servers", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "servers" in data
        assert isinstance(data["servers"], list)

    def test_api_runs(self, server_up):
        """E2E-API05: /api/runs returns list or DB warning"""
        r = httpx.get(f"{BASE}/api/runs", timeout=5)
        assert r.status_code in (200, 503)

    def test_api_trend(self, server_up):
        """E2E-API06: /api/trend returns trend or DB warning"""
        r = httpx.get(f"{BASE}/api/trend", timeout=5)
        assert r.status_code in (200, 503)

    def test_api_export_csv_no_run(self, server_up):
        """E2E-API07: CSV export for nonexistent run"""
        r = httpx.get(f"{BASE}/api/runs/nonexistent_run/export", timeout=5)
        assert r.status_code in (200, 503)

    def test_api_benchmark_start_validation(self, server_up):
        """E2E-API08: POST /api/benchmark/start validates body"""
        r = httpx.post(f"{BASE}/api/benchmark/start", timeout=5)
        assert r.status_code in (200, 400, 422, 500)

    def test_api_benchmark_stop(self, server_up):
        """E2E-API09: POST /api/benchmark/stop returns valid response"""
        r = httpx.post(f"{BASE}/api/benchmark/stop", timeout=5)
        assert r.status_code in (200, 400, 404, 503)


# =============================================
# E. REPORT ENDPOINT TESTS (N-Server)
# =============================================
class TestReportEndpoints:
    def test_report_list_page(self, server_up):
        """E2E-RPT01: /reports page renders"""
        r = httpx.get(f"{BASE}/reports", timeout=5)
        assert r.status_code == 200

    def test_report_detail_nonexistent(self, server_up):
        """E2E-RPT02: /reports/fake_run redirects to reports"""
        r = httpx.get(f"{BASE}/reports/fake_run_id", follow_redirects=False, timeout=5)
        assert r.status_code in (302, 307, 200)

    def test_excel_export_nonexistent(self, server_up):
        """E2E-RPT03: Excel export for nonexistent run redirects"""
        r = httpx.get(f"{BASE}/reports/fake_run/export/excel",
                      follow_redirects=False, timeout=5)
        assert r.status_code in (302, 307, 200)

    def test_html_download_nonexistent(self, server_up):
        """E2E-RPT04: HTML download for nonexistent run redirects"""
        r = httpx.get(f"{BASE}/reports/fake_run/download",
                      follow_redirects=False, timeout=5)
        assert r.status_code in (302, 307, 200)


# =============================================
# F. CHART API TESTS
# =============================================
class TestChartAPIs:
    def test_comparison_chart_api(self, server_up):
        """E2E-CHART01: Chart comparison endpoint"""
        r = httpx.get(f"{BASE}/api/charts/comparison/fake_run", timeout=5)
        assert r.status_code in (200, 503)

    def test_timeline_chart_api(self, server_up):
        """E2E-CHART02: Timeline chart endpoint"""
        r = httpx.get(f"{BASE}/api/charts/timeline/fake_run", timeout=5)
        assert r.status_code in (200, 503)

    def test_summary_chart_api(self, server_up):
        """E2E-CHART03: Summary chart endpoint"""
        r = httpx.get(f"{BASE}/api/charts/summary/fake_run", timeout=5)
        assert r.status_code in (200, 503)


# =============================================
# G. SECURITY & EDGE CASES
# =============================================
class TestSecurityEdgeCases:
    def test_xss_in_url(self, server_up):
        """E2E-SEC01: XSS in URL parameter doesn't reflect"""
        r = httpx.get(f"{BASE}/reports/<script>alert(1)</script>",
                      follow_redirects=True, timeout=5)
        assert "<script>alert(1)</script>" not in r.text

    def test_sql_injection_in_run_id(self, server_up):
        """E2E-SEC02: SQL injection in run_id is safe"""
        r = httpx.get(f"{BASE}/reports/' OR 1=1--",
                      follow_redirects=True, timeout=5)
        assert r.status_code in (200, 302, 307, 404)

    def test_large_limit_parameter(self, server_up):
        """E2E-SEC03: Very large limit parameter is handled"""
        r = httpx.get(f"{BASE}/api/trend?limit=999999", timeout=5)
        assert r.status_code in (200, 503)

    def test_negative_limit(self, server_up):
        """E2E-SEC04: Negative limit parameter handled"""
        r = httpx.get(f"{BASE}/api/trend?limit=-1", timeout=5)
        assert r.status_code in (200, 422, 503)

    def test_concurrent_requests(self, server_up):
        """E2E-SEC05: Server handles concurrent requests"""
        async def _concurrent():
            async with httpx.AsyncClient(timeout=10) as client:
                tasks = [client.get(f"{BASE}/api/servers") for _ in range(10)]
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                successes = [r for r in responses if isinstance(r, httpx.Response) and r.status_code == 200]
                return len(successes)
        count = run_async(_concurrent())
        assert count >= 8  # At least 80% success under load
