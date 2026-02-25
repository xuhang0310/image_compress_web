#!/bin/bash

# Get the script directory and change to it
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Try to find uv in the system PATH
UV_BIN="uv"
if ! command -v uv &> /dev/null; then
    # 2. If not in PATH, install via pip
    echo "[INFO] uv not found, installing via pip..."
    pip install uv
    UV_BIN="$HOME/.local/bin/uv"
    if [ ! -f "$UV_BIN" ]; then
        UV_BIN="$(which uv)"
    fi
    if [ ! -f "$UV_BIN" ]; then
        echo "[ERROR] uv installation failed"
        exit 1
    fi
fi

# 3. Sync environment using the found uv binary
echo "[INFO] Syncing environment..."
"$UV_BIN" sync --link-mode copy --extra cpu

# 4. Run application in background
echo "[INFO] Starting..."
echo "---------------------------------------"
nohup "$UV_BIN" run python main.py > app.log 2>&1 &
echo "[INFO] Application running in background (PID: $!)"
echo "[INFO] Logs: app.log"
