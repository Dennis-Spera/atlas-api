README.md:# 🍃 cluster-admin.py
README.md:Edit the constants near the top of `cluster-admin.py` to set your defaults:
README.md:uv run cluster-admin.py create
README.md:uv run cluster-admin.py create \
README.md:uv run cluster-admin.py delete
README.md:uv run cluster-admin.py delete --cluster-name my-cluster
README.md:uv run cluster-admin.py scale-up --cluster-name my-cluster
README.md:uv run cluster-admin.py scale-down --cluster-name my-cluster
README.md:uv run cluster-admin.py pause --cluster-name my-cluster
README.md:uv run cluster-admin.py resume --cluster-name my-cluster
README.md:uv run cluster-admin.py --log-file my-run.log create --cluster-name my-cluster
README.md:[10:31:02] Command : uv run cluster-admin.py create --cluster-name my-cluster
README.md:uv run cluster-admin.py -h
README.md:uv run cluster-admin.py create -h
README.md:uv run cluster-admin.py delete -h
README.md:uv run cluster-admin.py scale-up -h
README.md:uv run cluster-admin.py scale-down -h
README.md:uv run cluster-admin.py pause -h
README.md:uv run cluster-admin.py resume -h
cluster-admin-2026-07-07T18-52-19.log:[18:52:19] Command : cluster-admin.py pause --cluster-name test-api
cluster-admin-2026-07-07T18-54-16.log:[18:54:16] Command : cluster-admin.py pause --cluster-name test-api
cluster-admin-2026-07-08T17-13-54.log:[17:13:54] Command : cluster-admin.py list
cluster-admin-2026-07-08T17-14-59.log:[17:14:59] Command : cluster-admin.py delete --cluster-name test-api
cluster-admin.py:    python cluster-admin.py create
cluster-admin.py:    python cluster-admin.py create --no-wait
cluster-admin.py:    python cluster-admin.py create --timeout 3600 --poll-interval 30
cluster-admin.py:    python cluster-admin.py delete
cluster-admin.py:        python cluster-admin.py create \
cluster-admin.py:        python cluster-admin.py delete --cluster-name YOUR_CLUSTER_NAME
cluster-admin.py:        python cluster-admin.py pause  --cluster-name YOUR_CLUSTER_NAME
cluster-admin.py:        python cluster-admin.py resume --cluster-name YOUR_CLUSTER_NAME
cluster-admin.py:        python cluster-admin.py list
cluster-admin.py:            "  cluster-admin.py create -h\n"
cluster-admin.py:            "  cluster-admin.py delete -h"
