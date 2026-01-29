#!/bin/bash
# start.sh - ComfyUI Startup Script with Auto-Setup
set -e

echo "========================================"
echo "LTX-2 ComfyUI Startup"
echo "========================================"

COMFYUI_PATH="${COMFYUI_PATH:-/workspace/ComfyUI}"
COMFYUI_PORT="${COMFYUI_PORT:-8888}"

# Check if ComfyUI exists
if [ ! -d "$COMFYUI_PATH" ]; then
    echo "ComfyUI not found at $COMFYUI_PATH"
    echo "Cloning ComfyUI..."
    git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFYUI_PATH"
    cd "$COMFYUI_PATH"
    pip install -r requirements.txt
    pip install sqlalchemy reportlab GitPython
    
    # Install ComfyUI-Manager
    echo "Installing ComfyUI-Manager..."
    cd "$COMFYUI_PATH/custom_nodes"
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git comfyui-manager
    cd "$COMFYUI_PATH"
fi

# Ensure ComfyUI-Manager is installed (idempotent check)
if [ ! -d "$COMFYUI_PATH/custom_nodes/comfyui-manager" ]; then
    echo "Installing ComfyUI-Manager..."
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git "$COMFYUI_PATH/custom_nodes/comfyui-manager"
    cd "$COMFYUI_PATH/custom_nodes/comfyui-manager" && pip install -r requirements.txt
    cd "$COMFYUI_PATH"
fi

# Create model directories
echo "Ensuring model directories exist..."
mkdir -p "$COMFYUI_PATH/models/checkpoints"
mkdir -p "$COMFYUI_PATH/models/text_encoders"
mkdir -p "$COMFYUI_PATH/models/vae"
mkdir -p "$COMFYUI_PATH/models/latent_upscale_models"

# Run Automated Model Setup
if [ -f "/workspace/setup_models.py" ]; then
    echo "Starting automated model setup..."
    python3 /workspace/setup_models.py &
else
    echo "⚠️ setup_models.py not found in /workspace. Manual download required."
fi

# Start ComfyUI
echo ""
echo "Starting ComfyUI on port $COMFYUI_PORT..."

# Kill Jupyter if running (it hogs port 8888)
pkill -f jupyter || true


# --- FileBrowser Setup ---
echo "Checking/Installing FileBrowser..."
if ! command -v filebrowser &> /dev/null; then
    curl -fsSL https://raw.githubusercontent.com/filebrowser/get/master/get.sh | bash
fi

# Configure and start FileBrowser if not running
if ! pgrep -x "filebrowser" > /dev/null; then
    echo "Starting FileBrowser on port 3000..."
    # Create DB in workspace to persist users/settings
    filebrowser config init --database /workspace/filebrowser.db
    filebrowser config set --address 0.0.0.0 --port 3000 --root /workspace --database /workspace/filebrowser.db
    
    # Add admin user if not exists (checked via db)
    # We use a naive check or just try adding (it will fail if exists, which is fine)
    filebrowser users add admin nikhil-file-1234 --perm.admin --database /workspace/filebrowser.db || true
    
    nohup filebrowser --database /workspace/filebrowser.db > /workspace/filebrowser.log 2>&1 &
fi
# -------------------------

echo "========================================"
cd "$COMFYUI_PATH"
python3 main.py --listen 0.0.0.0 --port "$COMFYUI_PORT"
