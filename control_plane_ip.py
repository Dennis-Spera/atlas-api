#!/usr/bin/env python3
"""Print Atlas control-plane IP information for the current project.

Equivalent to the curl output without any jq filtering.
"""

import argparse
import json
from pathlib import Path
from typing import Any

import requests
from requests.auth import HTTPDigestAuth

ATLAS_PUBLIC_KEY = ""
ATLAS_PRIVATE_KEY = ""
ATLAS_API_VERSION = "latest"
CONFIG_PATH = Path(__file__).with_name("config.json")


def resolve_accept_header(api_version: str) -> str:
    normalized = str(api_version or "").strip().lower()
    if normalized in {"latest", "auto"}:
        return "application/vnd.atlas.2025-03-12+json"
    return f"application/vnd.atlas.{api_version}+json"


def load_atlas_config(config_path: Path = CONFIG_PATH) -> None:
    global ATLAS_PUBLIC_KEY, ATLAS_PRIVATE_KEY, ATLAS_API_VERSION

    if not config_path.exists():
        raise FileNotFoundError(f"Missing Atlas config file: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError(f"Atlas config file must contain a JSON object: {config_path}")

    ATLAS_PUBLIC_KEY = str(payload.get("ATLAS_PUBLIC_KEY", "")).strip()
    ATLAS_PRIVATE_KEY = str(payload.get("ATLAS_PRIVATE_KEY", "")).strip()
    ATLAS_API_VERSION = str(payload.get("ATLAS_API_VERSION", "latest")).strip()


def validate_atlas_config() -> None:
    if not ATLAS_PUBLIC_KEY or not ATLAS_PRIVATE_KEY:
        raise SystemExit("Missing ATLAS_PUBLIC_KEY or ATLAS_PRIVATE_KEY in config.json")


def format_region_table(region: str, values: list[str]) -> str:
    headers = ("region", "ip")
    rows = [(region, value) for value in values]
    widths = [len(header) for header in headers]
    for row in rows:
        widths[0] = max(widths[0], len(str(row[0])))
        widths[1] = max(widths[1], len(str(row[1])))

    header_line = f"{headers[0]:<{widths[0]}}  {headers[1]:<{widths[1]}}"
    separator = f"{'-' * widths[0]}  {'-' * widths[1]}"
    lines = [header_line, separator]
    for row in rows:
        lines.append(f"{row[0]:<{widths[0]}}  {row[1]:<{widths[1]}}")
    return "\n".join(lines)


def format_full_table(payload: dict[str, Any]) -> str:
    gateways = payload.get("gateways", [])
    if not gateways:
        return "No gateway data available."

    outbound = gateways[0].get("ips", {}).get("outbound", {})
    rows: list[tuple[str, str, str]] = []
    for provider, region_map in outbound.items():
        if not isinstance(region_map, dict):
            continue
        for region, values in region_map.items():
            if not isinstance(values, list):
                continue
            for value in values:
                rows.append((provider, region, str(value)))

    if not rows:
        return "No outbound IP data available."

    headers = ("provider", "region", "ip")
    widths = [len(header) for header in headers]
    for row in rows:
        widths[0] = max(widths[0], len(str(row[0])))
        widths[1] = max(widths[1], len(str(row[1])))
        widths[2] = max(widths[2], len(str(row[2])))

    header_line = f"{headers[0]:<{widths[0]}}  {headers[1]:<{widths[1]}}  {headers[2]:<{widths[2]}}"
    separator = f"{'-' * widths[0]}  {'-' * widths[1]}  {'-' * widths[2]}"
    lines = [header_line, separator]
    for provider, region, value in rows:
        lines.append(f"{provider:<{widths[0]}}  {region:<{widths[1]}}  {value:<{widths[2]}}")
    return "\n".join(lines)


def format_region_md_table(region: str, values: list[str]) -> str:
    rows = ["| region | ip |", "| --- | --- |"]
    for value in values:
        rows.append(f"| {region} | {value} |")
    return "\n".join(rows)


def format_full_md_table(payload: dict[str, Any]) -> str:
    gateways = payload.get("gateways", [])
    if not gateways:
        return "No gateway data available."

    outbound = gateways[0].get("ips", {}).get("outbound", {})
    rows: list[tuple[str, str, str]] = []
    for provider, region_map in outbound.items():
        if not isinstance(region_map, dict):
            continue
        for region, values in region_map.items():
            if not isinstance(values, list):
                continue
            for value in values:
                rows.append((provider, region, str(value)))

    if not rows:
        return "No outbound IP data available."

    md_rows = ["| provider | region | ip |", "| --- | --- | --- |"]
    for provider, region, value in rows:
        md_rows.append(f"| {provider} | {region} | {value} |")
    return "\n".join(md_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print Atlas control-plane IP data or a count for a selected AWS region"
    )
    parser.add_argument(
        "--region",
        default=None,
        help="Optional AWS region to inspect; if omitted, print the full response",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="Print only the number of IP addresses for the selected region",
    )
    parser.add_argument(
        "--md",
        action="store_true",
        help="Render the output as Markdown table markup instead of plain text",
    )
    return parser.parse_args()


def main() -> None:
    load_atlas_config()
    validate_atlas_config()
    args = parse_args()

    url = "https://cloud.mongodb.com/api/atlas/v2/unauth/controlPlaneIPAddresses?pretty=true"
    headers = {
        "Accept": resolve_accept_header(ATLAS_API_VERSION),
    }
    auth = HTTPDigestAuth(ATLAS_PUBLIC_KEY, ATLAS_PRIVATE_KEY)

    response = requests.get(url, headers=headers, auth=auth, timeout=60)
    response.raise_for_status()

    payload = response.json()
    if args.region:
        gateways = payload.get("gateways", [])
        if not gateways:
            raise SystemExit("No Atlas control-plane gateway data returned.")
        outbound = gateways[0].get("ips", {}).get("outbound", {})
        aws = outbound.get("aws", {})
        region_ips = aws.get(args.region, [])
        if args.count:
            print(len(region_ips))
            return
        if not region_ips:
            print(f"No outbound IPs found for region: {args.region}")
            return
        if args.md:
            print(format_region_md_table(args.region, region_ips))
            return
        print(format_region_table(args.region, region_ips))
        return

    if args.md:
        print(format_full_md_table(payload))
        return
    print(format_full_table(payload))


if __name__ == "__main__":
    main()
