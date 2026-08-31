# 🍃 cluster-admin.py

A command-line tool for managing **MongoDB Atlas clusters** via the Atlas API.  
Supports creating, deleting, scaling, pausing, resuming, and updating cluster tags — with a live status display and automatic run logging.

---

## ✅ Requirements

- Python 3.9+
- [`uv`](https://github.com/astral-sh/uv) or a virtualenv with dependencies installed
- Atlas API credentials (public key, private key, group ID)

Install dependencies:

```bash
pip install requests rich
```

---

## ⚙️ Configuration

Edit the constants near the top of `cluster-admin.py` to set your defaults:

| Constant | Description | Default |
|---|---|---|
| `ATLAS_PUBLIC_KEY` | Atlas API public key | `<your-atlas-public-key>` |
| `ATLAS_PRIVATE_KEY` | Atlas API private key | `<your-atlas-private-key>` |
| `ATLAS_GROUP_ID` | Atlas project (group) ID | `658eee9170...` |
| `ATLAS_CLUSTER_NAME` | Default cluster name | `api-master-cluster` |
| `ATLAS_CLUSTER_TYPE` | Default cluster type (`REPLICASET` or `SHARDED`) | `REPLICASET` |
| `ATLAS_NUM_SHARDS` | Number of shards for sharded clusters | `1` |
| `ATLAS_MONGODB_VERSION` | MongoDB major version | `8.0` |
| `ATLAS_PROVIDER` | Cloud provider | `AWS` |
| `ATLAS_REGION` | Cloud region | `US_EAST_1` |
| `ATLAS_INSTANCE_SIZE` | Instance tier | `M10` |
| `ATLAS_NODE_COUNT` | Electable node count | `3` |
| `ATLAS_REGION_PRIORITY` | Region election priority | `7` |
| `ATLAS_TAG_OWNER` | `owner` resource tag | `dennis.spera` |
| `ATLAS_TAG_KEEP_UNTIL` | `keep_until` resource tag | `2026-07-14` |

---

## Additional Utilities

The following scripts load the same Atlas credentials from `config.json`. That
file is ignored by Git and must contain valid `ATLAS_PUBLIC_KEY`,
`ATLAS_PRIVATE_KEY`, and `ATLAS_GROUP_ID` values.

### `control_plane_ip.py`

Prints Atlas control-plane outbound IP addresses. Run without options for the
complete response, or select an AWS region and output format:

```bash
uv run python control_plane_ip.py
uv run python control_plane_ip.py --region US_EAST_1
uv run python control_plane_ip.py --region US_EAST_1 --count
uv run python control_plane_ip.py --region US_EAST_1 --md
```

### `create_alert_manual_scaling.py`

Creates a project alert for an explicitly supplied Atlas event type. Use
`--dry-run` to inspect the request before creating an alert:

```bash
uv run python create_alert_manual_scaling.py \
  --event-type CLUSTER_STATE_CHANGED --dry-run
uv run python create_alert_manual_scaling.py \
  --event-type CLUSTER_STATE_CHANGED
```

### `create_alert_space_utilization.py`

Creates an `OUTSIDE_METRIC_THRESHOLD` alert for cluster storage utilization. It
defaults to `DISK_PARTITION_SPACE_USED_DATA` at 85 percent:

```bash
uv run python create_alert_space_utilization.py \
  --cluster-name my-cluster --storage-threshold 85 --dry-run
uv run python create_alert_space_utilization.py \
  --cluster-name my-cluster --storage-threshold 85
```

Use `--metric-name`, `--operator`, `--units`, and `--mode` to customize the
Atlas metric threshold.

### `list_alerts.py`

Lists every alert configuration in the configured Atlas project as formatted
JSON:

```bash
uv run python list_alerts.py
```

---

## 🚀 Commands

### `create` — Create a cluster

```bash
uv run cluster-admin.py create
```

Waits for the cluster to reach `IDLE` and prints the SRV connection string.  
Use `--no-wait` to skip the readiness check.

**Override any config value at runtime:**

```bash
uv run cluster-admin.py create \
  --cluster-name YOUR_CLUSTER_NAME \
  --cluster-type REPLICASET \
  --mongodb-version 8.0 \
  --provider AWS \
  --region US_EAST_1 \
  --instance-size M10 \
  --node-count 3 \
  --region-priority 7 \
  --tag-keep-until 2026-08-01
```

```bash
uv run cluster-admin.py create \
  --cluster-name YOUR_SHARDED_CLUSTER_NAME \
  --cluster-type SHARDED \
  --num-shards 3 \
  --mongodb-version 8.0 \
  --provider AWS \
  --region US_EAST_1 \
  --instance-size M30 \
  --node-count 3 \
  --region-priority 7 \
  --tag-keep-until 2026-08-01
```

<table>
  <colgroup>
    <col width="30%">
    <col>
  </colgroup>
  <thead>
    <tr><th>Flag&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th><th>Description</th></tr>
  </thead>
  <tbody>
    <tr><td><code>--cluster-name</code></td><td>Cluster name</td></tr>
    <tr><td><code>--cluster-type</code></td><td>Atlas cluster type: <code>REPLICASET</code> or <code>SHARDED</code></td></tr>
    <tr><td><code>--num-shards</code></td><td>Number of shards for a sharded cluster; Atlas may reject this field on some API versions, in which case the script retries without it while still creating a sharded cluster</td></tr>
    <tr><td><code>--mongodb-version</code></td><td>MongoDB major version (for example, <code>8.0</code>; patch versions are auto-normalized)</td></tr>
    <tr><td><code>--provider</code></td><td>Cloud provider (<code>AWS</code>, <code>GCP</code>, <code>AZURE</code>)</td></tr>
    <tr><td><code>--region</code></td><td>Provider region (for example, <code>US_EAST_1</code>)</td></tr>
    <tr><td><code>--instance-size</code></td><td>Instance tier (for example, <code>M10</code>, <code>M30</code>)</td></tr>
    <tr><td><code>--node-count</code></td><td>Number of electable nodes</td></tr>
    <tr><td><code>--region-priority</code></td><td>Region priority (1-7)</td></tr>
    <tr><td><code>--tag-keep-until</code></td><td><code>keep_until</code> tag value (<code>YYYY-MM-DD</code>)</td></tr>
    <tr><td><code>--wait</code> / <code>--no-wait</code></td><td>Wait for readiness (default: <code>--wait</code>)</td></tr>
    <tr><td><code>--timeout</code></td><td>Readiness timeout in seconds (default: <code>2700</code>)</td></tr>
    <tr><td><code>--poll-interval</code></td><td>Poll interval in seconds (default: <code>20</code>)</td></tr>
  </tbody>
</table>

---

### `update-tag` — Update the `keep_until` tag

Updates the `keep_until` tag on an existing cluster through the Atlas API. The command retrieves the current tags first, so other cluster tags are preserved.

```bash
uv run cluster-admin.py update-tag \
  --tag-keep-until 2026-09-04
```

Use `--cluster-name` to override the configured cluster name:

```bash
uv run cluster-admin.py update-tag \
  --cluster-name my-cluster \
  --tag-keep-until 2026-09-04
```

The value must use the `YYYY-MM-DD` format. Changing `ATLAS_TAG_KEEP_UNTIL` in `config.json` affects future `create` operations; use `update-tag` for an existing cluster.

---

### `list-tags` — List cluster tags

Lists all tags on the configured Atlas cluster through the Atlas API:

```bash
uv run cluster-admin.py list-tags
```

Use `--cluster-name` to list tags for a different cluster:

```bash
uv run cluster-admin.py list-tags --cluster-name my-cluster
```

The results are displayed as a table and included in the generated log file.

---

### 🗑️ `delete` — Delete a cluster

```bash
uv run cluster-admin.py delete
uv run cluster-admin.py delete --cluster-name my-cluster
```

> Prints a clean message if the cluster does not exist — no error exit. ✨

---

### 📈 `scale-up` — Scale up one tier

Moves the cluster instance size **up one step** in the tier ladder.

```bash
uv run cluster-admin.py scale-up --cluster-name my-cluster
```

> Waits for the cluster to return to `IDLE` after scaling. 🕐

---

### 📉 `scale-down` — Scale down one tier

Moves the cluster instance size **down one step** in the tier ladder.

```bash
uv run cluster-admin.py scale-down --cluster-name my-cluster
```

**Instance size tier ladder:**

```
M10 → M20 → M30 → M40 → M50 → M60 → M80 → M140 → M200 → M300 → M400 → M700
```

> Already at min or max? A clean message is printed and no change is made. 🛑

---

### ⏸️ `pause` — Pause a cluster

```bash
uv run cluster-admin.py pause --cluster-name my-cluster
```

---

### ▶️ `resume` — Resume a paused cluster

```bash
uv run cluster-admin.py resume --cluster-name my-cluster
```

> Waits for the cluster to return to `IDLE` after resuming. 🕐

---

## 📄 Logging

Every command automatically writes a plain-text log file with timestamps.

**Default filename** (auto-generated per run):
```
cluster-admin-2026-07-07T10-31-02.log
```

**Custom log file:**
```bash
uv run cluster-admin.py --log-file my-run.log create --cluster-name my-cluster
```

**Sample log output:**
```
[10:31:02] Command : uv run cluster-admin.py create --cluster-name my-cluster
[10:31:02] Started : 2026-07-07T10:31:02.456789
[10:31:02] Log file: cluster-admin-2026-07-07T10-31-02.log
[10:31:02]
[10:31:03] Creating Atlas cluster: my-cluster
[10:31:04] HTTP 201
[10:31:04] Waiting for cluster to be ready for connections (timeout: 2700s, poll: 20s)...
[10:31:24] Current state: CREATING  elapsed: 20s
[10:32:44] Current state: CREATING  elapsed: 100s
[10:33:04] ✓ Cluster is ready to accept connections.  elapsed: 122s
[10:33:04] SRV connection string: mongodb+srv://my-cluster.xxxxx.mongodb.net
```

---

## 💡 Tips

- MongoDB version strings like `8.0.23` are **automatically normalized** to `8.0` — no manual trimming needed.
- Run with no arguments or `-h` to see full help including all override flags.
- The live terminal display updates **every second** during waits, showing current state and elapsed time on a single line.

---

## 📋 Full help

```bash
uv run cluster-admin.py -h
uv run cluster-admin.py create -h
uv run cluster-admin.py delete -h
uv run cluster-admin.py scale-up -h
uv run cluster-admin.py scale-down -h
uv run cluster-admin.py pause -h
uv run cluster-admin.py resume -h
```
