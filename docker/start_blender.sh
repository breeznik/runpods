#!/bin/bash
# start_blender.sh - Blender Rendering Workstation (Standalone)
# GPU-accelerated Blender + VNC Desktop + FileBrowser. No AI dependencies.

echo "========================================"
echo "Blender Rendering Workstation - v1.0"
echo "========================================"

BLENDER_URL="https://download.blender.org/release/Blender5.0/blender-5.0.0-linux-x64.tar.xz"
INSTALL_DIR="/workspace/blender"
VNC_PASS="runpod"

# 0. Cleanup
echo "Cleaning up existing processes..."
pkill -f "blender" || true
vncserver -kill :1 2>/dev/null || true
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1

# 1. Install System Dependencies
echo "Installing System Dependencies (this takes 2-3 min)..."
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    wget curl nano vim procps htop \
    xfce4 xfce4-goodies \
    tigervnc-standalone-server tigervnc-common dbus-x11 \
    libgl1-mesa-glx libglib2.0-0 libxrender1 libxkbcommon0
echo "System dependencies installed."

# 2. Install Blender
if [ ! -d "$INSTALL_DIR" ]; then
    echo "Downloading Blender 5.0..."
    mkdir -p "$INSTALL_DIR"
    wget -q --show-progress -O /workspace/blender.tar.xz "$BLENDER_URL"
    echo "Extracting..."
    tar -xf /workspace/blender.tar.xz -C "$INSTALL_DIR" --strip-components=1
    rm /workspace/blender.tar.xz
    echo "Blender installed to $INSTALL_DIR"
else
    echo "Blender already installed."
fi

export PATH="$INSTALL_DIR:$PATH"
echo "Blender Version: $($INSTALL_DIR/blender --version 2>/dev/null | head -1 || echo 'check manually')"

# 3. Configure VNC
echo "Configuring VNC..."
mkdir -p ~/.vnc
echo "$VNC_PASS" | vncpasswd -f > ~/.vnc/passwd
chmod 600 ~/.vnc/passwd

cat > ~/.vnc/xstartup << 'XSTARTUP'
#!/bin/sh
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
exec startxfce4
XSTARTUP
chmod +x ~/.vnc/xstartup

# 4. Desktop Shortcut
mkdir -p /root/Desktop
cat > /root/Desktop/Blender.desktop << 'DESKTOP'
[Desktop Entry]
Version=1.0
Name=Blender 5.0
Comment=Launch Blender
Exec=/workspace/blender/blender
Icon=blender
Terminal=false
Type=Application
Categories=Graphics;
DESKTOP
chmod +x /root/Desktop/Blender.desktop

# 5. FileBrowser (Port 3000)
echo "Setting up FileBrowser..."
if ! command -v filebrowser > /dev/null 2>&1; then
    curl -fsSL https://raw.githubusercontent.com/filebrowser/get/master/get.sh | bash
fi

if [ ! -f "/workspace/filebrowser.db" ]; then
    filebrowser config init --database /workspace/filebrowser.db
    filebrowser config set --address 0.0.0.0 --port 3000 --root /workspace --database /workspace/filebrowser.db
    filebrowser users add admin nikhil-file-1234 --perm.admin --database /workspace/filebrowser.db 2>/dev/null || true
fi

# 6. Render output dir
mkdir -p /workspace/renders

# 7. Start VNC
echo "Starting VNC Server..."
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1
vncserver :1 -geometry 1920x1080 -depth 24
echo "VNC started on :1 (Port 5901)"

# 8. Start FileBrowser
echo "Starting FileBrowser..."
nohup filebrowser --database /workspace/filebrowser.db > /workspace/filebrowser.log 2>&1 &
echo "FileBrowser started on port 3000"

# 9. Keep-alive watchdog
cat > /workspace/keep_blender_alive.sh << 'KEEPALIVE'
#!/bin/bash
while true; do
  if ! pgrep -x "Xtigervnc" > /dev/null; then
    rm -f /tmp/.X1-lock /tmp/.X11-unix/X1
    vncserver :1 -geometry 1920x1080 -depth 24
  fi
  if ! pgrep -x "filebrowser" > /dev/null; then
    nohup filebrowser --database /workspace/filebrowser.db >> /workspace/filebrowser.log 2>&1 &
  fi
  sleep 30
done
KEEPALIVE
chmod +x /workspace/keep_blender_alive.sh

if ! grep -q "keep_blender_alive.sh" ~/.bashrc 2>/dev/null; then
    echo "nohup /workspace/keep_blender_alive.sh > /dev/null 2>&1 &" >> ~/.bashrc
fi
nohup /workspace/keep_blender_alive.sh > /dev/null 2>&1 &

GPU_NAME=$(nvidia-smi --query-gpu=gpu_name --format=csv,noheader 2>/dev/null | head -1 || echo "Unknown")
echo ""
echo "========================================"
echo "BLENDER WORKSTATION READY"
echo "   GPU:     $GPU_NAME"
echo "   VNC:     Port 5901 (Password: $VNC_PASS)"
echo "   Files:   Port 3000 (admin / nikhil-file-1234)"
echo "   Renders: /workspace/renders"
echo "   CLI:     /workspace/blender/blender -b file.blend -a"
echo "========================================"
