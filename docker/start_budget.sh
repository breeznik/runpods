#!/bin/bash
# start_budget.sh - Budget Pod Startup (Hunyuan + A5000)
set -e

echo "========================================"
echo "Hunyuan (Budget) ComfyUI Startup"
echo "========================================"

COMFYUI_PATH="${COMFYUI_PATH:-/workspace/ComfyUI}"
COMFYUI_PORT="${COMFYUI_PORT:-8888}"

# Redirect stdout/stderr to a log file for 'rpa watch'
exec > >(tee -a /workspace/startup.log) 2>&1

# Load .env variables if present
if [ -f "/workspace/.env" ]; then
    echo "Loading .env variables..."
    set -a
    source /workspace/.env
    set +a
fi

# 1. Install ComfyUI
if [ ! -d "$COMFYUI_PATH" ]; then
    echo "Cloning ComfyUI..."
    git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFYUI_PATH"
    cd "$COMFYUI_PATH"
    pip install -r requirements.txt
    
    # Install Manager
    cd "$COMFYUI_PATH/custom_nodes"
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git comfyui-manager
    
    # Install GGUF Support (Crucial for Budget Mode)
    echo "Installing ComfyUI-GGUF..."
    git clone https://github.com/city96/ComfyUI-GGUF.git comfyui-gguf
    cd comfyui-gguf
    pip install -r requirements.txt
    
    cd "$COMFYUI_PATH"
fi

# 2. Ensure Directories
mkdir -p "$COMFYUI_PATH/models/unet"
mkdir -p "$COMFYUI_PATH/models/clip"
mkdir -p "$COMFYUI_PATH/models/vae"
mkdir -p "$COMFYUI_PATH/models/LLM"

# 3. Model Setup
if [ -f "/workspace/setup_hunyuan.py" ]; then
    echo "Starting Hunyuan Model Setup..."
    python3 /workspace/setup_hunyuan.py &
else
    echo "⚠️ setup_hunyuan.py not found in /workspace."
fi

# 4. FileBrowser (Optional but helpful)
if ! pgrep -x "filebrowser" > /dev/null; then
    if ! command -v filebrowser &> /dev/null; then
        curl -fsSL https://raw.githubusercontent.com/filebrowser/get/master/get.sh | bash
    fi
    filebrowser config init --database /workspace/filebrowser.db || true
    filebrowser config set --address 0.0.0.0 --port 3000 --root /workspace --database /workspace/filebrowser.db || true
    filebrowser users add admin nikhil-file-1234 --perm.admin --database /workspace/filebrowser.db || true
    nohup filebrowser --database /workspace/filebrowser.db > /workspace/filebrowser.log 2>&1 &
fi

# 5. Start ComfyUI
echo "Starting ComfyUI on port $COMFYUI_PORT..."
cd "$COMFYUI_PATH"
python3 main.py --listen 0.0.0.0 --port "$COMFYUI_PORT"
