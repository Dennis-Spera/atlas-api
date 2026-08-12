#!/usr/bin/env python3
"""List all MongoDB Atlas alert configurations for the configured project."""

import importlib.util
import json
from pathlib import Path
from typing import Any

import requests
from requests.auth import HTTPDigestAuth


def load_cluster_admin_module() -> Any:
    module_path = Path(__file__).with_name("cluster-admin.py")
    spec = importlib.util.spec_from_file_location("cluster_admin", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load cluster admin module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cluster_admin = load_cluster_admin_module()
load_atlas_config = cluster_admin.load_atlas_config
validate_atlas_config = cluster_admin.validate_atlas_config
log = cluster_admin.log
resolve_accept_header = cluster_admin.resolve_accept_header


def build_headers() -> dict[str, str]:
    return {
        "Accept": resolve_accept_header(cluster_admin.ATLAS_API_VERSION),
        "Content-Type": "application/json",
    }


def build_auth() -> HTTPDigestAuth:
    return HTTPDigestAuth(cluster_admin.ATLAS_PUBLIC_KEY, cluster_admin.ATLAS_PRIVATE_KEY)


def list_alerts() -> list[dict[str, Any]]:
    base_url = (
        f"https://cloud.mongodb.com/api/atlas/v2/groups/{cluster_admin.ATLAS_GROUP_ID}/alertConfigs"
    )
    response = requests.get(base_url, headers=build_headers(), auth=build_auth(), timeout=60)
    response.raise_for_status()
    payload = response.json()
    return payload.get("results", [])


def main() -> None:
    load_atlas_config()
    validate_atlas_config()

    alerts = list_alerts()
    if not alerts:
        log("No alerts found.", style="yellow")
        return

    print(json.dumps(alerts, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
