#!/usr/bin/env bash
set -euo pipefail

sudo apt update
sudo apt install -y git python3 python3-venv python3-pip

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

echo "Copy .env.example to .env and edit local secrets before running."
