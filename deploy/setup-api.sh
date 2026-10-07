#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -un)" != "ubuntu" ]; then
  echo "Run this script in the EC2 terminal as ubuntu."
  exit 1
fi

if [ ! -x /home/ubuntu/venv/bin/python ]; then
  echo "Install the API dependencies in /home/ubuntu/venv first."
  exit 1
fi

mkdir -p /home/ubuntu/src /home/ubuntu/models
/home/ubuntu/venv/bin/python - <<'PY'
import boto3
import fastapi
import joblib
import pandas
import sklearn
import uvicorn

boto3.client("s3", region_name="us-east-1").download_file(
    "income-lab21-257719179516-us-east-1",
    "artifacts/setup/serve.py",
    "/home/ubuntu/src/serve.py",
)
print("API code downloaded.")
PY

sudo tee /etc/systemd/system/income-api.service > /dev/null <<'SERVICE'
[Unit]
Description=Income Model API
After=network-online.target
Wants=network-online.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu
Environment=ARTIFACT_BUCKET=income-lab21-257719179516-us-east-1
Environment=AWS_DEFAULT_REGION=us-east-1
ExecStart=/home/ubuntu/venv/bin/python /home/ubuntu/src/serve.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable income-api
sudo systemctl restart income-api

if ! curl --fail --silent --show-error --retry 12 --retry-connrefused --retry-delay 5 --max-time 10 http://127.0.0.1:8080/healthz; then
  sudo journalctl -u income-api -n 40 --no-pager
  exit 1
fi
printf '\n'
curl --fail --silent --show-error http://127.0.0.1:8080/score \
  -H 'Content-Type: application/json' \
  -d '{"features": [28, 2, 14, 2, 11, 0, 1, 0, 0, 45]}'
printf '\n'
