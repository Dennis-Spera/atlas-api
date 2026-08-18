#!/bin/bash
uv run cluster-admin.py create \
  --cluster-name sharded-test \
  --cluster-type SHARDED \
  --num-shards 2 \
  --mongodb-version 8.0 \
  --provider AWS \
  --region US_EAST_1 \
  --instance-size M30 \
  --node-count 3 \
  --region-priority 7 \
  --tag-keep-until 2026-08-31