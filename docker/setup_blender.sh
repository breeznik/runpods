#!/bin/bash
# setup_blender.sh - Installs Blender 4.3 and XFCE Desktop (VNC)
set -e

BLENDER_URL="https://download.blender.org/release/Blender4.3/blender-4.3.0-linux-x64.tar.xz"
INSTALL_DIR="/workspace/blender"
VNC_PASS="runpod"

echo "========================================"
echo "Blender & Desktop Setup"
echo "========================================"

# --- 1. Install Blender (Headless) ---
if [ ! -d "$INSTALL_DIR" ]; then
    echo "Installing Blender 4.3..."
    mkdir -p "$INSTALL_DIR"
    wget -qO /workspace/blender.tar.xz "$BLENDER_URL"
    tar -xf /workspace/blender.tar.xz -C "$INSTALL_DIR" --strip-components=1
    rm /workspace/blender.tar.xz
    echo "Blender installed to $INSTALL_DIR"
else
    echo "Blender already installed."
fi

# Add to PATH temporarily for this session or user
export PATH="$INSTALL_DIR:$PATH"
echo "Blender Version: $(blender --version | head -1)"

# --- 2. Install Desktop (GUI/VNC) ---
if ! command -v vncserver &> /dev/null; then
    echo "Installing XFCE4 & TigerVNC (This takes 2-3 mins)..."
    apt-get update > /dev/null
    DEBIAN_FRONTEND=noninteractive apt-get install -y xfce4 xfce4-goodies tigervnc-standalone-server tigervnc-common dbus-x11 > /dev/null
    
    # Clean up
    rm -rf /var/lib/apt/lists/*
    
    # Setup VNC Password
    mkdir -p ~/.vnc
    echo "$VNC_PASS" | vncpasswd -f > ~/.vnc/passwd
    chmod 600 ~/.vnc/passwd
    
    # Create Startup Script
    cat <<EOF > ~/.vnc/xstartup
#!/bin/sh
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
exec startxfce4
EOF
    chmod +x ~/.vnc/xstartup
    
    echo "Desktop Environment Installed."
else
    echo "VNC Server already installed."
fi

# --- 3. Start VNC (if requested via env or just always check) ---
# We check if vncserver is running on :1
if ! pgrep -x "Xtigervnc" > /dev/null; then
    echo "Starting VNC Server on :1 (Port 5901)..."
    # Kill any stale locks
    rm -f /tmp/.X1-lock
    rm -f /tmp/.X11-unix/X1
    
    vncserver :1 -geometry 1920x1080 -depth 24
    echo "VNC Started."
else
    echo "VNC is running."
fi

echo "========================================"
echo "Ready. "
echo "CLI Render: /workspace/blender/blender -b file.blend -a"
echo "GUI Access: Connect VNC to Port 5901 (Password: $VNC_PASS)"
echo "========================================"
