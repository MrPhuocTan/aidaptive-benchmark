"""Grafana dashboard auto-provisioning"""

import json
from pathlib import Path
from typing import Optional

import httpx

from src.config import GrafanaConfig, InfluxDBConfig


class GrafanaProvisioner:
    """Auto-create and update Grafana dashboards and datasources"""

    def __init__(
        self,
        grafana_config: GrafanaConfig,
        influxdb_config: InfluxDBConfig,
    ):
        self.grafana_url = grafana_config.url.rstrip("/")
        self.auth = (grafana_config.admin_user, grafana_config.admin_password)
        self.influxdb_config = influxdb_config

    def is_available(self) -> bool:
        try:
            resp = httpx.get(
                f"{self.grafana_url}/api/health",
                timeout=5.0,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def setup_datasource(self):
        """Create InfluxDB datasource in Grafana"""

        datasource = {
            "name": "aidaptive-influxdb",
            "type": "influxdb",
            "access": "proxy",
            "url": self.influxdb_config.url,
            "jsonData": {
                "version": "Flux",
                "organization": self.influxdb_config.org,
                "defaultBucket": self.influxdb_config.bucket,
            },
            "secureJsonData": {
                "token": self.influxdb_config.token,
            },
            "isDefault": True,
        }

        try:
            resp = httpx.post(
                f"{self.grafana_url}/api/datasources",
                json=datasource,
                auth=self.auth,
                timeout=10.0,
            )
            if resp.status_code in (200, 409):
                return True
        except Exception as e:
            print(f"  Grafana datasource setup error: {e}")

        return False

    def upload_dashboard(self, dashboard_json: dict) -> bool:
        """Upload a dashboard to Grafana"""

        payload = {
            "dashboard": dashboard_json,
            "overwrite": True,
            "folderId": 0,
        }

        try:
            resp = httpx.post(
                f"{self.grafana_url}/api/dashboards/db",
                json=payload,
                auth=self.auth,
                timeout=10.0,
            )
            return resp.status_code == 200
        except Exception as e:
            print(f"  Grafana dashboard upload error: {e}")
            return False

    def upload_all_dashboards(self, dashboards_dir: str):
        """Upload all dashboard JSON files from a directory"""

        dashboards_path = Path(dashboards_dir)
        if not dashboards_path.exists():
            return

        for json_file in dashboards_path.glob("*.json"):
            try:
                with open(json_file, "r") as f:
                    dashboard = json.load(f)
                success = self.upload_dashboard(dashboard)
                status = "OK" if success else "FAIL"
                print(f"  Grafana dashboard [{status}]: {json_file.name}")
            except Exception as e:
                print(f"  Grafana dashboard error ({json_file.name}): {e}")

    def provision_all(self, dashboards_dir: str):
        """Full provisioning: datasource + all dashboards"""

        if not self.is_available():
            print("  Grafana not available, skipping provisioning")
            return

        print("  Setting up Grafana datasource...")
        self.setup_datasource()

        print("  Uploading dashboards...")
        self.upload_all_dashboards(dashboards_dir)