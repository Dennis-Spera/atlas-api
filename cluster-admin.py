#!/usr/bin/env python3
"""Usage:
    python cluster-admin.py create
    python cluster-admin.py create --no-wait
    python cluster-admin.py create --timeout 3600 --poll-interval 30
    python cluster-admin.py delete

        # Override template (copy/paste)
        python cluster-admin.py create \
            --cluster-name YOUR_CLUSTER_NAME \
            --mongodb-version YOUR_MONGODB_VERSION \
            --provider YOUR_PROVIDER \
            --region YOUR_REGION \
            --instance-size YOUR_INSTANCE_SIZE \
            --node-count YOUR_NODE_COUNT \
            --region-priority YOUR_REGION_PRIORITY \
            --tag-keep-until YYYY-MM-DD

        python cluster-admin.py delete --cluster-name YOUR_CLUSTER_NAME
        python cluster-admin.py pause  --cluster-name YOUR_CLUSTER_NAME
        python cluster-admin.py resume --cluster-name YOUR_CLUSTER_NAME
"""

import argparse
import sys
import time
from urllib.parse import quote

import requests
from requests.auth import HTTPDigestAuth
import datetime
from rich.console import Console
from rich.live import Live
from rich.text import Text

# ATLAS_CLUSTER_NAME ATLAS_MONGODB_VERSION ATLAS_PROVIDER ATLAS_REGION ATLAS_INSTANCE_SIZE ATLAS_NODE_COUNT ATLAS_REGION_PRIORITY ATLAS_TAG_KEEP_UNTIL

_console = Console()
_file_console = None


def log(msg: str = "", style: str = "") -> None:
    _console.print(msg, style=style)
    if _file_console is not None:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        _file_console.out(f"[{ts}] {msg}")

ATLAS_PUBLIC_KEY = "ldccslle"
ATLAS_PRIVATE_KEY = "9fd730e2-4869-4f01-b553-195a9b807c60"
ATLAS_GROUP_ID = "658eee9170ea5353a4cd9041"

ATLAS_CLUSTER_NAME = "api-master-cluster"
ATLAS_MONGODB_VERSION = "8.0"
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

INSTANCE_SIZE_LADDER = [
    "M10", "M20", "M30", "M40", "M50",
    "M60", "M80", "M140", "M200", "M300", "M400", "M700",
]


def print_response(response: requests.Response) -> None:
    log(f"HTTP {response.status_code}", style="bold cyan")
    log(response.text)
    response.raise_for_status()


def normalize_mongodb_major_version(version: str) -> str:
    parts = version.split(".")
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[1]}"
    return version


def create_cluster(
    cluster_name: str = ATLAS_CLUSTER_NAME,
    mongodb_version: str = ATLAS_MONGODB_VERSION,
    provider: str = ATLAS_PROVIDER,
    region: str = ATLAS_REGION,
    instance_size: str = ATLAS_INSTANCE_SIZE,
    node_count: int = ATLAS_NODE_COUNT,
    region_priority: int = ATLAS_REGION_PRIORITY,
    tag_keep_until: str = ATLAS_TAG_KEEP_UNTIL,
    wait: bool = True,
    timeout_seconds: int = READY_TIMEOUT_SECONDS,
    poll_interval_seconds: int = READY_POLL_INTERVAL_SECONDS,
) -> None:
    normalized_mongodb_version = normalize_mongodb_major_version(mongodb_version)
    if normalized_mongodb_version != mongodb_version:
        log(
            f"Normalizing MongoDB version '{mongodb_version}' "
            f"to major version '{normalized_mongodb_version}'.",
            style="yellow",
        )

    payload = {
        "name": cluster_name,
        "clusterType": "REPLICASET",
        "mongoDBMajorVersion": normalized_mongodb_version,
        "tags": [
            {"key": "owner", "value": ATLAS_TAG_OWNER},
            {"key": "keep_until", "value": tag_keep_until},
        ],
        "replicationSpecs": [
            {
                "regionConfigs": [
                    {
                        "providerName": provider,
                        "regionName": region,
                        "priority": region_priority,
                        "electableSpecs": {
                            "instanceSize": instance_size,
                            "nodeCount": node_count,
                        },
                    }
                ],
            }
        ],
    }

    log(f"Creating Atlas cluster: {cluster_name}", style="bold")
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
            cluster_name=cluster_name,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )


def wait_for_cluster_ready(
    cluster_name: str = ATLAS_CLUSTER_NAME,
    timeout_seconds: int = READY_TIMEOUT_SECONDS,
    poll_interval_seconds: int = READY_POLL_INTERVAL_SECONDS,
) -> None:
    cluster_url = f"{BASE_URL}/{quote(cluster_name, safe='')}"
    deadline = time.time() + timeout_seconds

    log(
        f"Waiting for cluster to be ready for connections "
        f"(timeout: {timeout_seconds}s, poll: {poll_interval_seconds}s)...",
        style="bold",
    )

    start_time = time.time()
    state_name = "UNKNOWN"
    status = Text()

    with Live(status, refresh_per_second=2) as live:
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

            if _file_console is not None:
                elapsed_now = int(time.time() - start_time)
                _file_console.out(
                    f"[{datetime.datetime.now().strftime('%H:%M:%S')}] "
                    f"Current state: {state_name}  elapsed: {elapsed_now}s"
                )

            if state_name == "IDLE" and standard_srv:
                elapsed = int(time.time() - start_time)
                live.stop()
                log(f"✓ Cluster is ready to accept connections.  elapsed: {elapsed}s", style="bold green")
                log(f"SRV connection string: {standard_srv}", style="cyan")
                return

            poll_end = time.time() + poll_interval_seconds
            while time.time() < poll_end and time.time() < deadline:
                elapsed = int(time.time() - start_time)
                status.plain = ""
                status.append(f"Current state: {state_name}  elapsed: {elapsed}s")
                time.sleep(1)

    log(
        "✗ Timed out waiting for cluster readiness. "
        "Check Atlas activity and cluster state manually.",
        style="bold red",
    )
    sys.exit(1)
def scale_cluster(cluster_name: str, direction: str) -> None:
    cluster_url = f"{BASE_URL}/{quote(cluster_name, safe='')}"

    response = requests.get(cluster_url, headers=HEADERS, auth=AUTH, timeout=60)
    response.raise_for_status()
    cluster_info = response.json()

    try:
        current_size = (
            cluster_info["replicationSpecs"][0]["regionConfigs"][0]
            ["electableSpecs"]["instanceSize"]
        )
    except (KeyError, IndexError) as exc:
        log(f"Could not determine current instance size: {exc}", style="bold red")
        sys.exit(1)

    if current_size not in INSTANCE_SIZE_LADDER:
        log(
            f"Current instance size '{current_size}' is not in the known tier ladder.",
            style="bold red",
        )
        sys.exit(1)

    idx = INSTANCE_SIZE_LADDER.index(current_size)

    if direction == "up":
        if idx == len(INSTANCE_SIZE_LADDER) - 1:
            log(f"Cluster '{cluster_name}' is already at the maximum size ({current_size}).", style="yellow")
            return
        new_size = INSTANCE_SIZE_LADDER[idx + 1]
    else:
        if idx == 0:
            log(f"Cluster '{cluster_name}' is already at the minimum size ({current_size}).", style="yellow")
            return
        new_size = INSTANCE_SIZE_LADDER[idx - 1]

    log(f"Scaling cluster '{cluster_name}': {current_size} → {new_size}", style="bold")

    replication_specs = cluster_info.get("replicationSpecs", [])
    for spec in replication_specs:
        for region_config in spec.get("regionConfigs", []):
            if "electableSpecs" in region_config:
                region_config["electableSpecs"]["instanceSize"] = new_size

    payload = {"replicationSpecs": replication_specs}
    response = requests.patch(
        cluster_url,
        headers=HEADERS,
        json=payload,
        auth=AUTH,
        timeout=60,
    )
    print_response(response)
    wait_for_cluster_ready(cluster_name=cluster_name)


def pause_cluster(cluster_name: str, paused: bool) -> None:
    cluster_url = f"{BASE_URL}/{quote(cluster_name, safe='')}"
    action = "Pausing" if paused else "Resuming"
    log(f"{action} Atlas cluster: {cluster_name}", style="bold")
    response = requests.patch(
        cluster_url,
        headers=HEADERS,
        json={"paused": paused},
        auth=AUTH,
        timeout=60,
    )
    if response.status_code == 404:
        log(f"Cluster '{cluster_name}' does not exist.", style="bold red")
        sys.exit(1)
    print_response(response)
    if not paused:
        wait_for_cluster_ready(cluster_name=cluster_name)
    else:
        log(f"✓ Cluster '{cluster_name}' is now paused.", style="bold green")


def delete_cluster(cluster_name: str = ATLAS_CLUSTER_NAME) -> None:
    cluster_url = f"{BASE_URL}/{quote(cluster_name, safe='')}"
    log(f"Deleting Atlas cluster: {cluster_name}", style="bold")
    response = requests.delete(
        cluster_url,
        headers=HEADERS,
        auth=AUTH,
        timeout=60,
    )
    if response.status_code == 404:
        log(f"Cluster '{cluster_name}' does not exist; nothing to delete.", style="yellow")
        return

    print_response(response)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or delete an Atlas cluster",
        epilog=(
            "Override parameters are available on the create command:\n"
            "  --cluster-name --mongodb-version --provider --region\n"
            "  --instance-size --node-count --region-priority --tag-keep-until\n\n"
            "Show full command help:\n"
            "  cluster-admin.py create -h\n"
            "  cluster-admin.py delete -h"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--log-file",
        metavar="FILE",
        default=None,
        help="Save output to FILE (default: auto-generated timestamped filename)",
    )
    subparsers = parser.add_subparsers(dest="command")

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
        "--cluster-name",
        default=ATLAS_CLUSTER_NAME,
        help=f"Atlas cluster name (default: {ATLAS_CLUSTER_NAME})",
    )
    create_parser.add_argument(
        "--mongodb-version",
        default=ATLAS_MONGODB_VERSION,
        help=f"MongoDB major version (default: {ATLAS_MONGODB_VERSION})",
    )
    create_parser.add_argument(
        "--provider",
        default=ATLAS_PROVIDER,
        help=f"Cloud provider (default: {ATLAS_PROVIDER})",
    )
    create_parser.add_argument(
        "--region",
        default=ATLAS_REGION,
        help=f"Region name (default: {ATLAS_REGION})",
    )
    create_parser.add_argument(
        "--instance-size",
        default=ATLAS_INSTANCE_SIZE,
        help=f"Atlas instance size (default: {ATLAS_INSTANCE_SIZE})",
    )
    create_parser.add_argument(
        "--node-count",
        type=int,
        default=ATLAS_NODE_COUNT,
        help=f"Number of electable nodes (default: {ATLAS_NODE_COUNT})",
    )
    create_parser.add_argument(
        "--region-priority",
        type=int,
        default=ATLAS_REGION_PRIORITY,
        help=f"Region priority (default: {ATLAS_REGION_PRIORITY})",
    )
    create_parser.add_argument(
        "--tag-keep-until",
        default=ATLAS_TAG_KEEP_UNTIL,
        help=f"keep_until tag value (default: {ATLAS_TAG_KEEP_UNTIL})",
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

    delete_parser = subparsers.add_parser(
        "delete", help="Delete the configured Atlas cluster"
    )
    delete_parser.add_argument(
        "--cluster-name",
        default=ATLAS_CLUSTER_NAME,
        help=f"Atlas cluster name (default: {ATLAS_CLUSTER_NAME})",
    )

    for scale_cmd in ("scale-up", "scale-down"):
        scale_parser = subparsers.add_parser(
            scale_cmd,
            help=f"Scale the cluster instance size {'up' if scale_cmd == 'scale-up' else 'down'} one tier",
        )
        scale_parser.add_argument(
            "--cluster-name",
            default=ATLAS_CLUSTER_NAME,
            help=f"Atlas cluster name (default: {ATLAS_CLUSTER_NAME})",
        )

    for cmd in ("pause", "resume"):
        p = subparsers.add_parser(
            cmd,
            help=f"{'Pause' if cmd == 'pause' else 'Resume'} the configured Atlas cluster",
        )
        p.add_argument(
            "--cluster-name",
            default=ATLAS_CLUSTER_NAME,
            help=f"Atlas cluster name (default: {ATLAS_CLUSTER_NAME})",
        )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    if len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help"):
        parser.print_help()
        print("\nCreate command options:\n")
        create_parser.print_help()
        sys.exit(0)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    global _file_console
    log_path = (
        args.log_file
        if args.log_file
        else f"cluster-admin-{datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}.log"
    )
    _file_console = Console(
        file=open(log_path, "w"),
        no_color=True,
        highlight=False,
        width=120,
    )
    log(f"Command : {' '.join(sys.argv)}")
    log(f"Started : {datetime.datetime.now().isoformat()}")
    log(f"Log file: {log_path}")
    log()

    if args.command == "create":
        if args.timeout <= 0:
            log("--timeout must be greater than 0", style="bold red")
            sys.exit(1)
        if args.poll_interval <= 0:
            log("--poll-interval must be greater than 0", style="bold red")
            sys.exit(1)
        if args.node_count <= 0:
            log("--node-count must be greater than 0", style="bold red")
            sys.exit(1)

        create_cluster(
            cluster_name=args.cluster_name,
            mongodb_version=args.mongodb_version,
            provider=args.provider,
            region=args.region,
            instance_size=args.instance_size,
            node_count=args.node_count,
            region_priority=args.region_priority,
            tag_keep_until=args.tag_keep_until,
            wait=args.wait,
            timeout_seconds=args.timeout,
            poll_interval_seconds=args.poll_interval,
        )
    elif args.command == "delete":
        delete_cluster(cluster_name=args.cluster_name)
    elif args.command == "scale-up":
        scale_cluster(cluster_name=args.cluster_name, direction="up")
    elif args.command == "scale-down":
        scale_cluster(cluster_name=args.cluster_name, direction="down")
    elif args.command == "pause":
        pause_cluster(cluster_name=args.cluster_name, paused=True)
    elif args.command == "resume":
        pause_cluster(cluster_name=args.cluster_name, paused=False)
    else:
        log("Unknown command.", style="bold red")
        sys.exit(1)


if __name__ == "__main__":
    main()
