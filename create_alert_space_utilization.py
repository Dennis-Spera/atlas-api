#!/usr/bin/env python3
"""Create a MongoDB Atlas alert configuration for the configured cluster.

Examples:
    uv run python create_alert.py
    uv run python create_alert.py --cluster-name api-master-cluster --storage-threshold 85
    uv run python create_alert.py --dry-run
"""

import argparse
import importlib.util
import json
import sys
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
print_response = cluster_admin.print_response
resolve_accept_header = cluster_admin.resolve_accept_header


def build_headers() -> dict[str, str]:
    return {
        "Accept": resolve_accept_header(cluster_admin.ATLAS_API_VERSION),
        "Content-Type": "application/json",
    }


def build_auth() -> HTTPDigestAuth:
    return HTTPDigestAuth(cluster_admin.ATLAS_PUBLIC_KEY, cluster_admin.ATLAS_PRIVATE_KEY)


def find_existing_alert(alerts: list[dict[str, Any]], metric_name: str) -> dict[str, Any] | None:
    for alert in alerts:
        if alert.get("eventTypeName") != "OUTSIDE_METRIC_THRESHOLD":
            continue

        metric_threshold = alert.get("metricThreshold", {}) or {}
        if metric_threshold.get("metricName") != metric_name:
            continue

        return alert

    return None


def create_alert_config(
    cluster_name: str,
    metric_name: str = "DISK_PARTITION_SPACE_USED_DATA",
    threshold: float = 85.0,
    operator: str = "GREATER_THAN",
    units: str = "RAW",
    mode: str = "AVERAGE",
) -> dict[str, Any]:
    base_url = (
        f"https://cloud.mongodb.com/api/atlas/v2/groups/{cluster_admin.ATLAS_GROUP_ID}/alertConfigs"
    )
    headers = build_headers()
    auth = build_auth()

    existing_alerts = requests.get(base_url, headers=headers, auth=auth, timeout=60).json().get("results", [])
    existing_match = find_existing_alert(existing_alerts, metric_name)
    if existing_match is not None:
        log(
            f"Alert already exists for metric '{metric_name}' (id: {existing_match.get('id')}).",
            style="yellow",
        )
        return existing_match

    payload = {
        "enabled": True,
        "eventTypeName": "OUTSIDE_METRIC_THRESHOLD",
        "notifications": [
            {
                "typeName": "GROUP",
                "delayMin": 0,
                "emailEnabled": True,
                "intervalMin": 60,
                "roles": ["GROUP_OWNER"],
                "smsEnabled": False,
            }
        ],
        "metricThreshold": {
            "metricName": metric_name,
            "mode": mode,
            "operator": operator,
            "threshold": threshold,
            "units": units,
        },
    }

    response = requests.post(base_url, headers=headers, json=payload, auth=auth, timeout=60)
    print_response(response)
    return response.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an Atlas alert for the configured cluster")
    parser.add_argument("--cluster-name", default=cluster_admin.ATLAS_CLUSTER_NAME, help="Target Atlas cluster name")
    parser.add_argument("--storage-threshold", type=float, default=85.0, help="Storage usage threshold percent")
    parser.add_argument("--metric-name", default="DISK_PARTITION_SPACE_USED_DATA", help="Atlas metric to alert on")
    parser.add_argument("--operator", default="GREATER_THAN", help="Metric threshold operator")
    parser.add_argument("--units", default="RAW", help="Metric units")
    parser.add_argument("--mode", default="AVERAGE", help="Aggregation mode")
    parser.add_argument("--dry-run", action="store_true", help="Print the payload and exit without sending the request")
    return parser.parse_args()


def main() -> None:
    load_atlas_config()
    validate_atlas_config()
    args = parse_args()

    if args.dry_run:
        payload = {
            "enabled": True,
            "eventTypeName": "OUTSIDE_METRIC_THRESHOLD",
            "notifications": [
                {
                    "typeName": "GROUP",
                    "delayMin": 0,
                    "emailEnabled": True,
                    "intervalMin": 60,
                    "roles": ["GROUP_OWNER"],
                    "smsEnabled": False,
                }
            ],
            "metricThreshold": {
                "metricName": args.metric_name,
                "mode": args.mode,
                "operator": args.operator,
                "threshold": args.storage_threshold,
                "units": args.units,
            },
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    created_alert = create_alert_config(
        cluster_name=args.cluster_name,
        metric_name=args.metric_name,
        threshold=args.storage_threshold,
        operator=args.operator,
        units=args.units,
        mode=args.mode,
    )
    log(f"Alert created successfully: {json.dumps(created_alert, indent=2, sort_keys=True)}", style="bold green")


if __name__ == "__main__":
    main()
