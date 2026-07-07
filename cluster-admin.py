#!/usr/bin/env python3
"""Usage:
    python cluster-admin.py create
    python cluster-admin.py create --no-wait
    python cluster-admin.py create --timeout 3600 --poll-interval 30
    python cluster-admin.py delete
"""

import argparse
import sys
import time
from urllib.parse import quote

import requests
from requests.auth import HTTPDigestAuth


ATLAS_PUBLIC_KEY = "ldccslle"
ATLAS_PRIVATE_KEY = "9fd730e2-4869-4f01-b553-195a9b807c60"
ATLAS_GROUP_ID = "658eee9170ea5353a4cd9041"

ATLAS_CLUSTER_NAME = "api-master-cluster"
ATLAS_MONGODB_VERSION = "8.0.23"
ATLAS_PROVIDER = "AWS"
ATLAS_REGION = "US_EAST_1"
ATLAS_INSTANCE_SIZE = "M10"
ATLAS_NODE_COUNT = 3
ATLAS_REGION_PRIORITY = 7
ATLAS_TAG_OWNER = "dennis.spera"
ATLAS_TAG_KEEP_UNTIL = "2026-07-14"
ATLAS_API_VERSION = "2025-03-12"

BASE_URL = f"https://cloud.mongodb.com/api/atlas/v2/groups/{ATLAS_GROUP_ID}/clusters"
HEADERS = {
    "Accept": f"application/vnd.atlas.{ATLAS_API_VERSION}+json",
    "Content-Type": "application/json",
}
AUTH = HTTPDigestAuth(ATLAS_PUBLIC_KEY, ATLAS_PRIVATE_KEY)
READY_TIMEOUT_SECONDS = 45 * 60
READY_POLL_INTERVAL_SECONDS = 20


def print_response(response: requests.Response) -> None:
    print(f"HTTP {response.status_code}")
    print(response.text)
    response.raise_for_status()


def create_cluster(
    wait: bool = True,
    timeout_seconds: int = READY_TIMEOUT_SECONDS,
    poll_interval_seconds: int = READY_POLL_INTERVAL_SECONDS,
) -> None:
    payload = {
        "name": ATLAS_CLUSTER_NAME,
        "clusterType": "REPLICASET",
        "mongoDBMajorVersion": ATLAS_MONGODB_VERSION,
        "tags": [
            {"key": "owner", "value": ATLAS_TAG_OWNER},
            {"key": "keep_until", "value": ATLAS_TAG_KEEP_UNTIL},
        ],
        "replicationSpecs": [
            {
                "regionConfigs": [
                    {
                        "providerName": ATLAS_PROVIDER,
                        "regionName": ATLAS_REGION,
                        "priority": ATLAS_REGION_PRIORITY,
                        "electableSpecs": {
                            "instanceSize": ATLAS_INSTANCE_SIZE,
                            "nodeCount": ATLAS_NODE_COUNT,
                        },
                    }
                ],
            }
        ],
    }

    print(f"Creating Atlas cluster: {ATLAS_CLUSTER_NAME}")
    response = requests.post(
        BASE_URL,
        headers=HEADERS,
        json=payload,
        auth=AUTH,
        timeout=60,
    )
    print_response(response)
    if wait:
        wait_for_cluster_ready(
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )


def wait_for_cluster_ready(
    timeout_seconds: int = READY_TIMEOUT_SECONDS,
    poll_interval_seconds: int = READY_POLL_INTERVAL_SECONDS,
) -> None:
    cluster_url = f"{BASE_URL}/{quote(ATLAS_CLUSTER_NAME, safe='')}"
    deadline = time.time() + timeout_seconds

    print(
        "Waiting for cluster to be ready for connections "
        f"(timeout: {timeout_seconds}s, poll: {poll_interval_seconds}s)..."
    )

    while time.time() < deadline:
        response = requests.get(
            cluster_url,
            headers=HEADERS,
            auth=AUTH,
            timeout=60,
        )
        response.raise_for_status()
        cluster_info = response.json()

        state_name = cluster_info.get("stateName", "UNKNOWN")
        connection_strings = cluster_info.get("connectionStrings", {})
        standard_srv = connection_strings.get("standardSrv")

        print(f"Current state: {state_name}")

        if state_name == "IDLE" and standard_srv:
            print("Cluster is ready to accept connections.")
            print(f"SRV connection string: {standard_srv}")
            return

        time.sleep(poll_interval_seconds)

    print(
        "Timed out waiting for cluster readiness. "
        "Check Atlas activity and cluster state manually.",
        file=sys.stderr,
    )
    sys.exit(1)


def delete_cluster() -> None:
    cluster_url = f"{BASE_URL}/{quote(ATLAS_CLUSTER_NAME, safe='')}"
    print(f"Deleting Atlas cluster: {ATLAS_CLUSTER_NAME}")
    response = requests.delete(
        cluster_url,
        headers=HEADERS,
        auth=AUTH,
        timeout=60,
    )
    if response.status_code == 404:
        print(f"Cluster '{ATLAS_CLUSTER_NAME}' does not exist; nothing to delete.")
        return

    print_response(response)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or delete an Atlas cluster")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser(
        "create", help="Create the configured Atlas cluster"
    )
    wait_group = create_parser.add_mutually_exclusive_group()
    wait_group.add_argument(
        "--wait",
        dest="wait",
        action="store_true",
        default=True,
        help="Wait for the cluster to be ready for connections (default: enabled)",
    )
    wait_group.add_argument(
        "--no-wait",
        dest="wait",
        action="store_false",
        help="Do not wait for cluster readiness after create",
    )
    create_parser.add_argument(
        "--timeout",
        type=int,
        default=READY_TIMEOUT_SECONDS,
        help=f"Readiness timeout in seconds (default: {READY_TIMEOUT_SECONDS})",
    )
    create_parser.add_argument(
        "--poll-interval",
        type=int,
        default=READY_POLL_INTERVAL_SECONDS,
        help=(
            "Readiness poll interval in seconds "
            f"(default: {READY_POLL_INTERVAL_SECONDS})"
        ),
    )

    subparsers.add_parser("delete", help="Delete the configured Atlas cluster")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.command == "create":
        if args.timeout <= 0:
            print("--timeout must be greater than 0", file=sys.stderr)
            sys.exit(1)
        if args.poll_interval <= 0:
            print("--poll-interval must be greater than 0", file=sys.stderr)
            sys.exit(1)

        create_cluster(
            wait=args.wait,
            timeout_seconds=args.timeout,
            poll_interval_seconds=args.poll_interval,
        )
    elif args.command == "delete":
        delete_cluster()
    else:
        print("Command must be either 'create' or 'delete'", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
