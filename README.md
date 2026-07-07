# 🍃 cluster-admin.py

A command-line tool for managing **MongoDB Atlas clusters** via the Atlas API.  
Supports creating, deleting, scaling, pausing, and resuming clusters — with a live status display and automatic run logging.

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
| `ATLAS_PUBLIC_KEY` | Atlas API public key | `ldccslle` |
| `ATLAS_PRIVATE_KEY` | Atlas API private key | `9fd730e2-...` |
| `ATLAS_GROUP_ID` | Atlas project (group) ID | `658eee9170...` |
| `ATLAS_CLUSTER_NAME` | Default cluster name | `api-master-cluster` |
| `ATLAS_MONGODB_VERSION` | MongoDB major version | `8.0` |
| `ATLAS_PROVIDER` | Cloud provider | `AWS` |
| `ATLAS_REGION` | Cloud region | `US_EAST_1` |
| `ATLAS_INSTANCE_SIZE` | Instance tier | `M10` |
| `ATLAS_NODE_COUNT` | Electable node count | `3` |
| `ATLAS_REGION_PRIORITY` | Region election priority | `7` |
| `ATLAS_TAG_OWNER` | `owner` resource tag | `dennis.spera` |
| `ATLAS_TAG_KEEP_UNTIL` | `keep_until` resource tag | `2026-07-14` |

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
  --mongodb-version 8.0 \
  --provider AWS \
  --region US_EAST_1 \
  --instance-size M10 \
  --node-count 3 \
  --region-priority 7 \
  --tag-keep-until 2026-08-01
```

| Flag | Description |
|---|---|
| `--cluster-name` | Cluster name |
| `--mongodb-version` | MongoDB major version (e.g. `8.0`; patch versions auto-normalized) |
| `--provider` | Cloud provider (`AWS`, `GCP`, `AZURE`) |
| `--region` | Provider region (e.g. `US_EAST_1`) |
| `--instance-size` | Instance tier (e.g. `M10`, `M30`) |
| `--node-count` | Number of electable nodes |
| `--region-priority` | Region priority (1–7) |
| `--tag-keep-until` | `keep_until` tag value (`YYYY-MM-DD`) |
| `--wait` / `--no-wait` | Wait for readiness (default: `--wait`) |
| `--timeout` | Readiness timeout in seconds (default: `2700`) |
| `--poll-interval` | Poll interval in seconds (default: `20`) |

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
