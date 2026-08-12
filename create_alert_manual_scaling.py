#!/usr/bin/env python3
"""Create an Atlas alert for a manual scaling-related event on the configured project.

MongoDB Atlas does not expose a universally supported manual-scaling alert enum in
all projects. This script therefore requires an explicit event type and validates
against the Atlas API before creating the alert.

Examples:
    uv run python create_alert_manual_scaling.py --event-type OUTSIDE_METRIC_THRESHOLD --dry-run
    uv run python create_alert_manual_scaling.py --event-type CLUSTER_STATE_CHANGED
"""

import argparse
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
print_response = cluster_admin.print_response
resolve_accept_header = cluster_admin.resolve_accept_header


def build_headers() -> dict[str, str]:
    return {
        "Accept": resolve_accept_header(cluster_admin.ATLAS_API_VERSION),
        "Content-Type": "application/json",
    }


def build_auth() -> HTTPDigestAuth:
    return HTTPDigestAuth(cluster_admin.ATLAS_PUBLIC_KEY, cluster_admin.ATLAS_PRIVATE_KEY)


def find_existing_alert(alerts: list[dict[str, Any]], event_type_name: str) -> dict[str, Any] | None:
    for alert in alerts:
        if alert.get("eventTypeName") == event_type_name:
            return alert
    return None


def create_alert_config(event_type_name: str = "CLUSTER_MANUAL_SCALING") -> dict[str, Any]:
    base_url = (
        f"https://cloud.mongodb.com/api/atlas/v2/groups/{cluster_admin.ATLAS_GROUP_ID}/alertConfigs"
    )
    headers = build_headers()
    auth = build_auth()

    existing_alerts = requests.get(base_url, headers=headers, auth=auth, timeout=60).json().get("results", [])
    existing_match = find_existing_alert(existing_alerts, event_type_name)
    if existing_match is not None:
        log(
            f"Alert already exists for event '{event_type_name}' (id: {existing_match.get('id')}).",
            style="yellow",
        )
        return existing_match

    payload = {
        "enabled": True,
        "eventTypeName": event_type_name,
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
    }

    response = requests.post(base_url, headers=headers, json=payload, auth=auth, timeout=60)
    print_response(response)
    return response.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a manual-scaling alert for the configured Atlas project"
    )
    parser.add_argument(
        "--event-type",
        default="",
        help="Explicit Atlas event type to monitor (for example: OUTSIDE_METRIC_THRESHOLD or a supported project event)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the payload and exit without sending a request",
    )
    return parser.parse_args()


def main() -> None:
    load_atlas_config()
    validate_atlas_config()
    args = parse_args()

    if not args.event_type.strip():
        raise SystemExit(
            "Missing --event-type. Atlas does not expose a reliable built-in 'manual scaling' enum; "
            "provide a supported event name from your project and re-run."
        )

    if args.dry_run:
        payload = {
            "enabled": True,
            "eventTypeName": args.event_type,
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
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    created_alert = create_alert_config(event_type_name=args.event_type)
    log(
        f"Manual scaling alert created successfully: {json.dumps(created_alert, indent=2, sort_keys=True)}",
        style="bold green",
    )


if __name__ == "__main__":
    main()
