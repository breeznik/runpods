#!/bin/bash
# start_wan2gp.sh - Wan2GP Video Generation (Hardened v2.0)
# Fail-proof deployment with auto-detection and zero manual intervention
set -e

echo "========================================"
echo "Wan2GP Video Generation - Hardened v2.0"
echo "========================================"

# Redirect all output to startup.log for visibility
exec > >(tee -a /workspace/startup.log) 2>&1

# 0. Cleanup any existing Wan2GP processes
echo "Cleaning up existing processes..."
pkill -f "wgp.py" || true

# 1. Install System Dependencies
echo "Installing System Dependencies..."
apt-get update && apt-get install -y \
    python3-venv python3-pip git build-essential \
    libgl1-mesa-glx libglib2.0-0 curl nano vim procps \
    || true

# 2. Setup Python Virtual Environment
VENV_PATH="/workspace/venv_wan2gp"
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating Python Virtual Environment..."
    python3 -m venv "$VENV_PATH"
fi

# Activate venv
source "$VENV_PATH/bin/activate"
pip install --upgrade pip --no-cache-dir

# 3. Clone repository
WAN2GP_DIR="/workspace/Wan2GP"
if [ ! -d "$WAN2GP_DIR" ]; then
    echo "Cloning Wan2GP repository..."
    git clone https://github.com/deepbeepmeep/Wan2GP.git "$WAN2GP_DIR"
else
    echo "Updating Wan2GP repository..."
    cd "$WAN2GP_DIR" && git pull || true
fi

cd "$WAN2GP_DIR"

# 4. Detect GPU and install appropriate PyTorch
echo "Detecting GPU architecture..."
GPU_NAME=$(nvidia-smi --query-gpu=gpu_name --format=csv,noheader 2>/dev/null | head -1 || echo "Unknown")
echo "Detected GPU: $GPU_NAME"

# Install PyTorch based on GPU
if echo "$GPU_NAME" | grep -qi "5090\|5080\|5070"; then
    echo "Blackwell GPU detected - using CUDA 12.6"
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
elif echo "$GPU_NAME" | grep -qi "4090\|4080\|4070\|A6000\|A40\|A100"; then
    echo "Ada/Ampere GPU detected - using CUDA 12.4"
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
else
    echo "Unknown GPU - using default CUDA 12.4"
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
fi

# 5. Install Triton
echo "Installing Triton..."
pip install --no-cache-dir -U triton

# 6. Fix requirements.txt issues and install
echo "Installing Wan2GP dependencies..."
sed -i 's/spacy==3.8.4/spacy/g' requirements.txt
pip install --no-cache-dir -r requirements.txt

# 7. Install optimized kernels (skip on Blackwell - no support yet)
echo "Installing optimized kernels..."
set +e
if ! echo "$GPU_NAME" | grep -qi "5090\|5080\|5070"; then
    # Only install Nunchaku on Ada/Ampere
    pip install --no-cache-dir https://github.com/deepbeepmeep/kernels/releases/download/v1.2.0_Nunchaku/nunchaku-1.2.0+torch2.7-cp310-cp310-linux_x86_64.whl || true
fi
set -e

echo "========================================"
echo "Wan2GP Setup Complete!"
echo "========================================"

# 8. Setup FileBrowser (Port 3000)
echo "Setting up FileBrowser..."
if ! command -v filebrowser &> /dev/null; then
    curl -fsSL https://raw.githubusercontent.com/filebrowser/get/master/get.sh | bash
fi

if [ ! -f "/workspace/filebrowser.db" ]; then
    filebrowser config init --database /workspace/filebrowser.db
    filebrowser config set --address 0.0.0.0 --port 3000 --root /workspace --database /workspace/filebrowser.db
    filebrowser users add admin nikhil-file-1234 --perm.admin --database /workspace/filebrowser.db || true
fi

# 9. Create keep-alive script
cat > /workspace/keep_wan2gp_alive.sh << 'EOF'
#!/bin/bash
VENV_PYTHON="/workspace/venv_wan2gp/bin/python"
WAN2GP_DIR="/workspace/Wan2GP"
LOG_FILE="/workspace/wan2gp_service.log"
FB_LOG="/workspace/filebrowser.log"

while true; do
  # Check Wan2GP (Port 8888)
  if ! pgrep -f "wgp.py" > /dev/null; then
    echo "$(date): Starting Wan2GP..." >> "$LOG_FILE"
    cd "$WAN2GP_DIR"
    nohup "$VENV_PYTHON" -u wgp.py --attention sdpa --server-port 8888 --listen >> "$LOG_FILE" 2>&1 &
  fi

  # Check FileBrowser (Port 3000)
  if ! pgrep -x "filebrowser" > /dev/null; then
    echo "$(date): Starting FileBrowser..." >> "$FB_LOG"
    nohup filebrowser --database /workspace/filebrowser.db >> "$FB_LOG" 2>&1 &
  fi

  sleep 30
done
EOF

chmod +x /workspace/keep_wan2gp_alive.sh

# 10. Hook into startup
if ! grep -q "keep_wan2gp_alive.sh" ~/.bashrc; then
    echo "nohup /workspace/keep_wan2gp_alive.sh > /dev/null 2>&1 &" >> ~/.bashrc
fi

# 11. Start services now
nohup /workspace/keep_wan2gp_alive.sh > /dev/null 2>&1 &

echo ""
echo "✅ Wan2GP Deployment Complete!"
echo "   GPU:   $GPU_NAME"
echo "   Port:  8888 (Wan2GP)"
echo "   Port:  3000 (FileBrowser)"
echo "   Logs:  tail -f /workspace/wan2gp_service.log"
